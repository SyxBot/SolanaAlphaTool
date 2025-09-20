"""
Wallet Analysis Module for Pump.fun Signal Alert Bot
Analyzes wallet behavior to identify potentially suspicious token creators.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey
import logging

logger = logging.getLogger(__name__)

# In-memory cache for wallet analysis results
_wallet_cache = {}
_cache_ttl = 300  # 5 minutes cache TTL


def is_wallet_suspicious(
    creator_pubkey: str, 
    client: AsyncClient, 
    min_age_minutes: int = 15, 
    min_txs: int = 3
) -> bool:
    """
    Analyze a wallet to determine if it's suspicious based on age and transaction count.
    
    Args:
        creator_pubkey: The wallet address to analyze
        client: Solana AsyncClient instance
        min_age_minutes: Minimum wallet age in minutes (default: 15)
        min_txs: Minimum transaction count (default: 3)
        
    Returns:
        bool: True if wallet is suspicious, False if safe
              Defaults to True (suspicious) on any errors
    """
    # Run the async analysis in a synchronous context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to handle this differently
            return True  # Default to suspicious if we can't analyze
        else:
            return loop.run_until_complete(
                _analyze_wallet_async(creator_pubkey, client, min_age_minutes, min_txs)
            )
    except Exception as e:
        logger.warning(f"Error analyzing wallet {creator_pubkey}: {e}")
        return True  # Default to suspicious on error


async def is_wallet_suspicious_async(
    creator_pubkey: str, 
    client: AsyncClient, 
    min_age_minutes: int = 15, 
    min_txs: int = 3
) -> bool:
    """
    Async version: Analyze a wallet to determine if it's suspicious.
    
    Args:
        creator_pubkey: The wallet address to analyze
        client: Solana AsyncClient instance
        min_age_minutes: Minimum wallet age in minutes (default: 15)
        min_txs: Minimum transaction count (default: 3)
        
    Returns:
        bool: True if wallet is suspicious, False if safe
              Defaults to True (suspicious) on any errors
    """
    # Check cache first to avoid API calls
    cache_key = f"{creator_pubkey}_{min_age_minutes}_{min_txs}"
    current_time = time.time()
    
    if cache_key in _wallet_cache:
        cached_result, cached_time = _wallet_cache[cache_key]
        if current_time - cached_time < _cache_ttl:
            logger.debug(f"Using cached wallet analysis for {creator_pubkey}")
            return cached_result
    
    # Add throttling to reduce API load (300ms delay)
    await asyncio.sleep(0.3)
    
    # Perform analysis
    result = await _analyze_wallet_async(creator_pubkey, client, min_age_minutes, min_txs)
    
    # Cache the result
    _wallet_cache[cache_key] = (result, current_time)
    
    # Clean old cache entries (keep only last 100 entries)
    if len(_wallet_cache) > 100:
        oldest_key = min(_wallet_cache.keys(), key=lambda k: _wallet_cache[k][1])
        del _wallet_cache[oldest_key]
    
    return result


async def _analyze_wallet_async(
    creator_pubkey: str, 
    client: AsyncClient, 
    min_age_minutes: int, 
    min_txs: int
) -> bool:
    """
    Internal async function to perform wallet analysis.
    
    Returns True if wallet is suspicious, False if safe.
    Defaults to True (suspicious) on any errors.
    """
    try:
        # Convert string to Pubkey
        pubkey = Pubkey.from_string(creator_pubkey)
        
        # Get the last 10 transaction signatures
        response = await client.get_signatures_for_address(
            pubkey, 
            limit=10,
            commitment="confirmed"
        )
        
        if not response.value:
            logger.info(f"No transactions found for wallet {creator_pubkey} - marking as suspicious")
            return True  # No transactions = suspicious
            
        signatures = response.value
        total_txs = len(signatures)
        
        # Check minimum transaction count
        if total_txs < min_txs:
            logger.info(f"Wallet {creator_pubkey} has only {total_txs} transactions (min: {min_txs}) - suspicious")
            return True
            
        # Get the oldest transaction to calculate wallet age
        oldest_tx = signatures[-1]  # Signatures are ordered newest to oldest
        oldest_timestamp = oldest_tx.block_time
        
        if oldest_timestamp is None:
            logger.warning(f"Could not get timestamp for oldest transaction of {creator_pubkey} - marking as suspicious")
            return True
            
        # Calculate wallet age in minutes
        current_time = datetime.now(timezone.utc).timestamp()
        wallet_age_seconds = current_time - oldest_timestamp
        wallet_age_minutes = wallet_age_seconds / 60
        
        # Check minimum age
        if wallet_age_minutes < min_age_minutes:
            logger.info(f"Wallet {creator_pubkey} is only {wallet_age_minutes:.1f} minutes old (min: {min_age_minutes}) - suspicious")
            return True
            
        # Wallet passes all checks
        logger.info(f"Wallet {creator_pubkey} analysis: {total_txs} txs, {wallet_age_minutes:.1f} min old - safe")
        return False
        
    except Exception as e:
        logger.error(f"Error analyzing wallet {creator_pubkey}: {e}")
        return True  # Default to suspicious on any error


async def get_wallet_details(creator_pubkey: str, client: AsyncClient) -> Dict[str, Any]:
    """
    Get detailed wallet information for analysis and logging.
    
    Args:
        creator_pubkey: The wallet address to analyze
        client: Solana AsyncClient instance
        
    Returns:
        dict: Wallet details including age, transaction count, and analysis
    """
    try:
        pubkey = Pubkey.from_string(creator_pubkey)
        
        # Get transaction signatures
        response = await client.get_signatures_for_address(
            pubkey, 
            limit=10,
            commitment="confirmed"
        )
        
        if not response.value:
            return {
                "address": creator_pubkey,
                "transaction_count": 0,
                "age_minutes": 0,
                "age_hours": 0,
                "oldest_tx_signature": None,
                "newest_tx_signature": None,
                "is_suspicious": True,
                "reason": "No transactions found"
            }
            
        signatures = response.value
        total_txs = len(signatures)
        
        # Calculate age from oldest transaction
        oldest_tx = signatures[-1]
        newest_tx = signatures[0]
        
        wallet_age_minutes = 0
        wallet_age_hours = 0
        
        if oldest_tx.block_time:
            current_time = datetime.now(timezone.utc).timestamp()
            wallet_age_seconds = current_time - oldest_tx.block_time
            wallet_age_minutes = wallet_age_seconds / 60
            wallet_age_hours = wallet_age_minutes / 60
            
        # Perform suspicion analysis
        is_suspicious = await is_wallet_suspicious_async(creator_pubkey, client)
        
        return {
            "address": creator_pubkey,
            "transaction_count": total_txs,
            "age_minutes": round(wallet_age_minutes, 1),
            "age_hours": round(wallet_age_hours, 1),
            "oldest_tx_signature": str(oldest_tx.signature) if oldest_tx else None,
            "newest_tx_signature": str(newest_tx.signature) if newest_tx else None,
            "is_suspicious": is_suspicious,
            "reason": _get_suspicion_reason(total_txs, wallet_age_minutes)
        }
        
    except Exception as e:
        logger.error(f"Error getting wallet details for {creator_pubkey}: {e}")
        return {
            "address": creator_pubkey,
            "transaction_count": 0,
            "age_minutes": 0,
            "age_hours": 0,
            "oldest_tx_signature": None,
            "newest_tx_signature": None,
            "is_suspicious": True,
            "reason": f"Analysis error: {str(e)}"
        }


def _get_suspicion_reason(tx_count: int, age_minutes: float, min_age: int = 15, min_txs: int = 3) -> str:
    """Get human-readable reason for suspicion classification."""
    if tx_count == 0:
        return "No transactions found"
    elif tx_count < min_txs:
        return f"Only {tx_count} transactions (minimum: {min_txs})"
    elif age_minutes < min_age:
        return f"Wallet too new: {age_minutes:.1f} minutes old (minimum: {min_age})"
    else:
        return "Wallet appears safe"


# Example usage and testing
async def test_wallet_analysis():
    """Test function to demonstrate wallet analysis."""
    import os
    from solana.rpc.async_api import AsyncClient
    
    # Use Helius if available, otherwise mainnet
    helius_key = os.getenv("HELIUS_API_KEY")
    if helius_key:
        rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    else:
        rpc_url = "https://api.mainnet-beta.solana.com"
        
    client = AsyncClient(rpc_url)
    
    # Test with some known addresses from recent token creations
    test_addresses = [
        "3MdqCFJePediedd6gFG3gcBKBW55a3PzVJfEGg1fUFfG",  # Orange Mocha Frappucino creator
        "GTB9KMuhtq9Xg9cYDxmH6Q7fqvVwnexucJjzmaYnMNDt",  # PokeBonk creator
        "98yDYZddQZnh3BvnfGFb3LkMNiRMPJDzk6UKvWpkBpNc",  # Tokenized Meow creator
    ]
    
    for address in test_addresses:
        print(f"\nAnalyzing wallet: {address}")
        
        try:
            # Get detailed analysis
            details = await get_wallet_details(address, client)
            print(f"  Transactions: {details['transaction_count']}")
            print(f"  Age: {details['age_hours']:.1f} hours ({details['age_minutes']:.1f} minutes)")
            print(f"  Suspicious: {details['is_suspicious']}")
            print(f"  Reason: {details['reason']}")
            
            # Test the main function
            is_suspicious = await is_wallet_suspicious_async(address, client)
            print(f"  Quick check result: {'SUSPICIOUS' if is_suspicious else 'SAFE'}")
            
        except Exception as e:
            print(f"  Error analyzing {address}: {e}")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(test_wallet_analysis())