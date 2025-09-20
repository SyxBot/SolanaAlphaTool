"""
Should Alert Decision Module for Pump.fun Signal Alert Bot
Combines all filtering components to determine if a token should trigger webhook alerts.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from solana.rpc.async_api import AsyncClient

# Import our filtering modules
from wallet_analyzer import is_wallet_suspicious_async
from symbol_validator import is_symbol_valid
from liquidity_analyzer import get_initial_liquidity_async
from utils import (
    log_event,
    get_config, 
    get_filtering_config,
    get_blocked_creators,
    calculate_quality_score
)

logger = logging.getLogger(__name__)


def is_blocked_creator(creator_address: str) -> bool:
    """
    Check if a creator address is in the blocked list.
    
    Args:
        creator_address: The creator wallet address as string
        
    Returns:
        bool: True if creator is blocked, False otherwise
    """
    blocked_creators = get_blocked_creators()
    return creator_address in blocked_creators


async def should_alert(token_metadata: Dict[str, Any], client: AsyncClient) -> bool:
    """
    Determine if a token should trigger a webhook alert based on all filtering criteria.
    
    Args:
        token_metadata: Dictionary containing token information with keys:
            - 'symbol': Token symbol (string)
            - 'creator': Creator wallet address (string)
            - 'mint': Token mint address (string)
            - 'name': Token name (optional, for logging)
        client: Solana RPC client for wallet analysis
        
    Returns:
        bool: True if token should trigger alert, False if it should be skipped
    """
    # Extract required fields
    symbol = token_metadata.get('symbol', '')
    creator = token_metadata.get('creator', '')
    mint = token_metadata.get('mint', '')
    name = token_metadata.get('name', 'Unknown')
    
    # Get filtering configuration
    config = get_filtering_config()
    
    log_event(f"Evaluating alert criteria for: {name} ({symbol})")
    
    try:
        # FAST CHECKS FIRST (no API calls) - reordered for efficiency
        
        # Check 1: Symbol validation (if enabled) - instant check
        if config['enable_symbol_filter']:
            if not is_symbol_valid(symbol):
                log_event(f"Skipping {name}: Invalid symbol '{symbol}'", 'warning')
                return False
            log_event(f"Symbol check passed: {symbol}", 'debug')
        
        # Check 2: Blocked creator (if enabled) - instant check
        if config['enable_blocked_creator_filter']:
            if is_blocked_creator(creator):
                log_event(f"Skipping {name}: Blocked creator {creator}", 'warning')
                return False
            log_event(f"Creator not blocked: {creator}", 'debug')
        
        # SLOW CHECKS (API calls) - only if fast checks pass
        
        # Check 3: Wallet suspicious check (if enabled) - requires API calls
        if config['enable_wallet_filter']:
            if await is_wallet_suspicious_async(creator, client):
                log_event(f"Skipping {name}: Suspicious wallet {creator}", 'warning')
                return False
            log_event(f"Wallet check passed: {creator}", 'debug')
        
        # Check 4: Liquidity check (if enabled) - requires API calls
        if config['enable_liquidity_filter']:
            liquidity_sol = await get_initial_liquidity_async(mint)
            if liquidity_sol < config['min_liquidity_sol']:
                log_event(f"Skipping {name}: Low liquidity {liquidity_sol:.4f} SOL", 'warning')
                return False
            log_event(f"Liquidity check passed: {liquidity_sol:.4f} SOL", 'debug')
        
        # All checks passed
        log_event(f"ALERT APPROVED: {name} ({symbol}) passed all filters")
        return True
        
    except Exception as e:
        log_event(f"Error evaluating {name}: {e}", 'error')
        # In case of error, default to not alerting to avoid spam
        return False


async def should_alert_with_details(token_metadata: Dict[str, Any], client: AsyncClient) -> Dict[str, Any]:
    """
    Enhanced version that returns detailed results for each check.
    
    Args:
        token_metadata: Dictionary containing token information
        client: Solana RPC client
        
    Returns:
        dict: Detailed results including pass/fail for each check
    """
    symbol = token_metadata.get('symbol', '')
    creator = token_metadata.get('creator', '')
    mint = token_metadata.get('mint', '')
    name = token_metadata.get('name', 'Unknown')
    
    result = {
        'should_alert': False,
        'token_name': name,
        'token_symbol': symbol,
        'checks': {
            'symbol_valid': False,
            'creator_not_blocked': False,
            'wallet_not_suspicious': False,
            'liquidity_sufficient': False
        },
        'details': {},
        'rejection_reasons': []
    }
    
    try:
        # Symbol validation
        result['checks']['symbol_valid'] = is_symbol_valid(symbol)
        if not result['checks']['symbol_valid']:
            result['rejection_reasons'].append(f"Invalid symbol: {symbol}")
        
        # Blocked creator check
        result['checks']['creator_not_blocked'] = not is_blocked_creator(creator)
        if not result['checks']['creator_not_blocked']:
            result['rejection_reasons'].append(f"Blocked creator: {creator}")
        
        # Wallet analysis
        result['checks']['wallet_not_suspicious'] = not await is_wallet_suspicious_async(creator, client)
        if not result['checks']['wallet_not_suspicious']:
            result['rejection_reasons'].append(f"Suspicious wallet: {creator}")
        
        # Liquidity check
        liquidity_sol = await get_initial_liquidity_async(mint)
        result['details']['liquidity_sol'] = liquidity_sol
        result['checks']['liquidity_sufficient'] = liquidity_sol >= 0.1
        if not result['checks']['liquidity_sufficient']:
            result['rejection_reasons'].append(f"Low liquidity: {liquidity_sol:.4f} SOL")
        
        # Overall decision
        result['should_alert'] = all(result['checks'].values())
        
        return result
        
    except Exception as e:
        logger.error(f"Error in detailed evaluation for {name}: {e}")
        result['rejection_reasons'].append(f"Evaluation error: {str(e)}")
        return result


# Synchronous wrapper for compatibility
def should_alert_sync(token_metadata: Dict[str, Any], client: AsyncClient) -> bool:
    """
    Synchronous wrapper for should_alert function.
    
    Note: This creates a new event loop if none exists.
    For async contexts, use should_alert() directly.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run_until_complete
            logger.warning("Cannot run sync version in async context - use should_alert() instead")
            return False
        else:
            return loop.run_until_complete(should_alert(token_metadata, client))
    except Exception as e:
        logger.error(f"Error in should_alert_sync: {e}")
        return False


# Test function using real token data from logs
async def test_should_alert():
    """Test the should_alert function with real tokens from your bot logs."""
    import os
    from solders.pubkey import Pubkey
    
    # Get RPC client
    helius_key = os.getenv("HELIUS_API_KEY")
    if helius_key:
        rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    else:
        rpc_url = "https://api.mainnet-beta.solana.com"
    
    client = AsyncClient(rpc_url)
    
    try:
        # Test with recent real tokens from your logs
        test_tokens = [
            # Good symbols but likely new wallets
            {
                'name': 'WAM',
                'symbol': 'WAM',
                'creator': 'ArEhrpdiHoNJCTiuwHPLdvknoshmhKs25ozpmf2hEUr1',
                'mint': '9RSu97yfR6bjdLYgz7oSeYxZKqVRJfTgw18sYobpump'
            },
            {
                'name': 'PutinRidingBear',
                'symbol': 'PRB',
                'creator': '5E3UKwJBpegcBS45LiLw5T6np34ooKvGg4pviJ4Drsn',
                'mint': '3vF5hcm2kkVns3xiwRwQJTDCPVtd9vVuRd9zoKDmpump'
            },
            {
                'name': 'Token the cat',
                'symbol': 'TOKEN',
                'creator': 'BQh86WWzyezfv8b7dnidPxq8KZVnLQ5FH2F5iC24Dq59',
                'mint': 'JdvSphNs7AMASkLWCfjcPJzMUbUj3E1MRnUexbtpump'
            },
            {
                'name': 'The Nod',
                'symbol': 'NOD',
                'creator': '3Q8pv2siaFafFCvpPSrpMthXAynge4wqBaYStzdzMnpE',
                'mint': '6msmSVRqAHNpED9QXQQn7reYWt4UKUc2mvNydyo5pump'
            },
            # Bad symbols (should be rejected)
            {
                'name': 'Farting Ticker',
                'symbol': '~4°',  # Invalid characters
                'creator': 'Ehdjyn3uS6cwBQ7wXnLSaG6Q9eXG4c53pvkAYiFte4MM',
                'mint': '2MzosmPbCZM7H47qn6TezyYuWPxjzpQN9Pxm5zBYpump'
            }
        ]
        
        print("🧪 Should Alert Function Test")
        print("=" * 50)
        
        approved_count = 0
        rejected_count = 0
        
        for token in test_tokens:
            print(f"\n📍 Testing: {token['name']} ({token['symbol']})")
            
            # Test basic function
            should_send_alert = await should_alert(token, client)
            
            # Test detailed function
            detailed_result = await should_alert_with_details(token, client)
            
            if should_send_alert:
                approved_count += 1
                print(f"   ✅ APPROVED - Alert would be sent")
                print(f"   Liquidity: {detailed_result['details'].get('liquidity_sol', 'N/A')} SOL")
            else:
                rejected_count += 1
                print(f"   ❌ REJECTED - Alert skipped")
                print(f"   Reasons: {'; '.join(detailed_result['rejection_reasons'])}")
        
        print(f"\n📊 SUMMARY")
        print(f"Approved: {approved_count}")
        print(f"Rejected: {rejected_count}")
        print(f"Filter Rate: {rejected_count/(approved_count+rejected_count)*100:.1f}% filtered out")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_should_alert())