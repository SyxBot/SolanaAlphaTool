"""
Liquidity Analysis Module for Pump.fun Signal Alert Bot
Retrieves initial liquidity or bonding pool value for pump.fun tokens.
"""

import asyncio
import json
import os
import time
from typing import Optional, Dict, Any
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
import aiohttp
import logging

logger = logging.getLogger(__name__)

# In-memory cache for liquidity analysis results
_liquidity_cache = {}
_liquidity_cache_ttl = 180  # 3 minutes cache TTL for liquidity


def get_initial_liquidity(token_mint: str) -> float:
    """
    Get the initial liquidity or bonding pool value for a pump.fun token.
    
    Args:
        token_mint: The token mint address as string
        
    Returns:
        float: Liquidity in SOL, 0.0 on error or if not available
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, return 0.0 to avoid blocking
            logger.warning(f"Cannot get liquidity for {token_mint} - already in async context")
            return 0.0
        else:
            return loop.run_until_complete(get_initial_liquidity_async(token_mint))
    except Exception as e:
        logger.error(f"Error getting liquidity for {token_mint}: {e}")
        return 0.0


async def get_initial_liquidity_async(token_mint: str) -> float:
    """
    Async version: Get the initial liquidity or bonding pool value for a pump.fun token.
    
    Args:
        token_mint: The token mint address as string
        
    Returns:
        float: Liquidity in SOL, 0.0 on error or if not available
    """
    # Check cache first to avoid API calls
    current_time = time.time()
    if token_mint in _liquidity_cache:
        cached_result, cached_time = _liquidity_cache[token_mint]
        if current_time - cached_time < _liquidity_cache_ttl:
            logger.debug(f"Using cached liquidity for {token_mint}: {cached_result} SOL")
            return cached_result
    
    try:
        # Method 1: Try pump.fun API first (most accurate)
        liquidity = await _get_liquidity_from_pumpfun_api(token_mint)
        if liquidity > 0:
            # Cache the result
            _liquidity_cache[token_mint] = (liquidity, current_time)
            return liquidity
            
        # Method 2: Try to estimate from bonding curve account
        liquidity = await _get_liquidity_from_bonding_curve(token_mint)
        if liquidity > 0:
            # Cache the result
            _liquidity_cache[token_mint] = (liquidity, current_time)
            return liquidity
            
        # Method 3: Use Helius API for token account analysis
        liquidity = await _get_liquidity_from_helius(token_mint)
        
        # Cache even zero results for a short time to avoid repeated failed calls
        _liquidity_cache[token_mint] = (liquidity, current_time)
        
        # Clean old cache entries (keep only last 50 entries)
        if len(_liquidity_cache) > 50:
            oldest_key = min(_liquidity_cache.keys(), key=lambda k: _liquidity_cache[k][1])
            del _liquidity_cache[oldest_key]
        
        return liquidity
        
    except Exception as e:
        logger.error(f"Error in get_initial_liquidity_async for {token_mint}: {e}")
        return 0.0


async def _get_liquidity_from_pumpfun_api(token_mint: str, retry_count: int = 0) -> float:
    """
    Try to get liquidity data from pump.fun API with exponential backoff.
    
    Returns:
        float: Liquidity in SOL, 0.0 if not available
    """
    try:
        # Add throttling to reduce API load
        await asyncio.sleep(0.2)  # 200ms delay between API calls
        
        # Pump.fun has an undocumented API endpoint for token data
        api_url = f"https://frontend-api.pump.fun/coins/{token_mint}"
        
        timeout = aiohttp.ClientTimeout(total=3.0)  # Reduced timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract relevant liquidity fields from pump.fun response
                    # These field names are based on observed API responses
                    virtual_sol_reserves = data.get('virtual_sol_reserves', 0)
                    virtual_token_reserves = data.get('virtual_token_reserves', 0)
                    
                    if virtual_sol_reserves:
                        # Convert from lamports to SOL
                        liquidity_sol = virtual_sol_reserves / 1_000_000_000
                        logger.info(f"Pump.fun API liquidity for {token_mint}: {liquidity_sol} SOL")
                        return liquidity_sol
                        
                elif response.status == 404:
                    logger.debug(f"Token {token_mint} not found in pump.fun API")
                elif response.status == 530 and retry_count < 2:
                    # Exponential backoff for 530 errors
                    backoff_delay = 2 ** retry_count  # 1s, 2s, 4s
                    logger.warning(f"Pump.fun API overloaded (530), retrying in {backoff_delay}s")
                    await asyncio.sleep(backoff_delay)
                    return await _get_liquidity_from_pumpfun_api(token_mint, retry_count + 1)
                else:
                    logger.warning(f"Pump.fun API returned status {response.status} for {token_mint}")
                    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout accessing pump.fun API for {token_mint}")
    except Exception as e:
        logger.debug(f"Error accessing pump.fun API for {token_mint}: {e}")
        
    return 0.0


async def _get_liquidity_from_bonding_curve(token_mint: str) -> float:
    """
    Estimate liquidity from bonding curve account data.
    
    Returns:
        float: Estimated liquidity in SOL, 0.0 if not available
    """
    try:
        # Get RPC client
        helius_key = os.getenv("HELIUS_API_KEY")
        if helius_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            rpc_url = "https://api.mainnet-beta.solana.com"
            
        client = AsyncClient(rpc_url)
        
        try:
            # Derive bonding curve address using pump.fun's standard derivation
            mint_pubkey = Pubkey.from_string(token_mint)
            bonding_curve_seed = b"bonding-curve"
            pump_program = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
            
            bonding_curve_pubkey, _ = Pubkey.find_program_address(
                [bonding_curve_seed, bytes(mint_pubkey)],
                pump_program
            )
            
            # Get bonding curve account data
            response = await client.get_account_info(bonding_curve_pubkey)
            
            if response.value and response.value.data:
                # Parse bonding curve data (this is a simplified estimation)
                account_data = response.value.data
                
                # Bonding curves typically store SOL reserves at specific offsets
                # This is a rough estimation - actual parsing would need the full account layout
                if len(account_data) >= 64:
                    # Estimate from account lamports (SOL balance)
                    account_lamports = response.value.lamports
                    liquidity_sol = account_lamports / 1_000_000_000
                    
                    logger.info(f"Bonding curve estimated liquidity for {token_mint}: {liquidity_sol} SOL")
                    return liquidity_sol
                    
        finally:
            await client.close()
            
    except Exception as e:
        logger.debug(f"Error getting bonding curve liquidity for {token_mint}: {e}")
        
    return 0.0


async def _get_liquidity_from_helius(token_mint: str) -> float:
    """
    Use Helius API to analyze token accounts and estimate liquidity.
    
    Returns:
        float: Estimated liquidity in SOL, 0.0 if not available
    """
    try:
        helius_key = os.getenv("HELIUS_API_KEY")
        if not helius_key:
            return 0.0
            
        # Use Helius DAS API to get token information
        helius_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "getAsset",
            "params": {
                "id": token_mint
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(helius_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "result" in data and data["result"]:
                        # Extract supply and other metadata that might indicate liquidity
                        supply = data["result"].get("supply", {}).get("print_current_supply", 0)
                        
                        # This is a very rough estimation - pump.fun tokens typically start
                        # with standardized liquidity amounts
                        if supply > 0:
                            # Standard pump.fun initial liquidity is often around 1-5 SOL
                            estimated_liquidity = 2.0  # Default estimate
                            logger.info(f"Helius estimated liquidity for {token_mint}: {estimated_liquidity} SOL")
                            return estimated_liquidity
                            
    except Exception as e:
        logger.debug(f"Error getting Helius liquidity data for {token_mint}: {e}")
        
    return 0.0


async def get_detailed_liquidity_info(token_mint: str) -> Dict[str, Any]:
    """
    Get detailed liquidity information including multiple data sources.
    
    Args:
        token_mint: The token mint address as string
        
    Returns:
        dict: Detailed liquidity information from various sources
    """
    result = {
        "token_mint": token_mint,
        "liquidity_sol": 0.0,
        "data_source": "none",
        "pumpfun_api": None,
        "bonding_curve": None,
        "helius_data": None,
        "timestamp": None
    }
    
    try:
        # Try pump.fun API
        pumpfun_liquidity = await _get_liquidity_from_pumpfun_api(token_mint)
        if pumpfun_liquidity > 0:
            result["liquidity_sol"] = pumpfun_liquidity
            result["data_source"] = "pumpfun_api"
            result["pumpfun_api"] = {"liquidity": pumpfun_liquidity}
            
        # Try bonding curve analysis
        curve_liquidity = await _get_liquidity_from_bonding_curve(token_mint)
        if curve_liquidity > 0 and result["liquidity_sol"] == 0:
            result["liquidity_sol"] = curve_liquidity
            result["data_source"] = "bonding_curve"
            result["bonding_curve"] = {"estimated_liquidity": curve_liquidity}
            
        # Try Helius as fallback
        helius_liquidity = await _get_liquidity_from_helius(token_mint)
        if helius_liquidity > 0 and result["liquidity_sol"] == 0:
            result["liquidity_sol"] = helius_liquidity
            result["data_source"] = "helius_estimate"
            result["helius_data"] = {"estimated_liquidity": helius_liquidity}
            
        from datetime import datetime
        result["timestamp"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Error in get_detailed_liquidity_info for {token_mint}: {e}")
        
    return result


# Test function
async def test_liquidity_analysis():
    """Test liquidity analysis with recent tokens from your bot."""
    
    # Test with recent tokens from your logs
    test_tokens = [
        "Ad9YVnJSJVFsaqBh1EN7xawnLTuD5HpBotphXVu85zFF",  # Gobbe
        "DJUQHswBxPkPHxJh2HhpCmw7W3GAWXpvBTFgKLH7pump",  # PYSOP
        "5FGXdHPuTUHsu8U4wa9q9hKZXF59Ftt55JDHoVu5pump",  # LABUBU
        "7emaTkEHPpiEFvpcWF5KFBSK2zy8Uo7tcKHERmJzpump",  # EDGE
    ]
    
    print("🧪 Liquidity Analysis Test")
    print("=" * 50)
    
    for token_mint in test_tokens:
        print(f"\n📍 Testing token: {token_mint}")
        
        # Get basic liquidity
        liquidity = await get_initial_liquidity_async(token_mint)
        print(f"   Basic liquidity: {liquidity} SOL")
        
        # Get detailed info
        details = await get_detailed_liquidity_info(token_mint)
        print(f"   Data source: {details['data_source']}")
        print(f"   Detailed liquidity: {details['liquidity_sol']} SOL")
        
        if details['pumpfun_api']:
            print(f"   Pump.fun API: {details['pumpfun_api']}")
        if details['bonding_curve']:
            print(f"   Bonding curve: {details['bonding_curve']}")
        if details['helius_data']:
            print(f"   Helius estimate: {details['helius_data']}")


if __name__ == "__main__":
    asyncio.run(test_liquidity_analysis())