"""
Comprehensive Token Filter for Pump.fun Signal Alert Bot
Combines wallet analysis and symbol validation to filter high-quality tokens.
"""

import asyncio
import os
from solana.rpc.async_api import AsyncClient
from wallet_analyzer import is_wallet_suspicious_async, get_wallet_details
from symbol_validator import is_symbol_valid, validate_symbol_with_details
from pump_monitor import TokenInfo
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def comprehensive_token_filter(token_info: TokenInfo) -> bool:
    """
    Comprehensive token filter that validates both symbol and creator wallet.
    
    Args:
        token_info: Token information from pump.fun detection
        
    Returns:
        bool: True if token passes all filters, False if it should be rejected
    """
    logger.info(f"🔍 Filtering token: {token_info.name} ({token_info.symbol})")
    
    # Step 1: Validate symbol format
    symbol_validation = validate_symbol_with_details(token_info.symbol)
    
    if not symbol_validation["is_valid"]:
        logger.warning(f"❌ Symbol validation failed for {token_info.name}")
        logger.warning(f"   Symbol: '{token_info.symbol}' - {symbol_validation['reason']}")
        return False
    
    logger.info(f"✅ Symbol validation passed: {token_info.symbol}")
    
    # Step 2: Analyze creator wallet
    helius_key = os.getenv("HELIUS_API_KEY")
    if not helius_key:
        logger.warning("HELIUS_API_KEY not found, using public RPC")
        rpc_url = "https://api.mainnet-beta.solana.com"
    else:
        rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    
    client = AsyncClient(rpc_url)
    
    try:
        creator_address = str(token_info.creator)
        wallet_details = await get_wallet_details(creator_address, client)
        
        if wallet_details["is_suspicious"]:
            logger.warning(f"❌ Wallet analysis failed for {token_info.name}")
            logger.warning(f"   Creator: {creator_address}")
            logger.warning(f"   Reason: {wallet_details['reason']}")
            return False
        
        logger.info(f"✅ Wallet analysis passed: {wallet_details['age_minutes']:.1f} min old, {wallet_details['transaction_count']} txs")
        
        # All filters passed
        logger.info(f"🎯 Token {token_info.name} passed all filters - APPROVED for alert")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during wallet analysis for {token_info.name}: {e}")
        return False  # Default to rejecting on error
        
    finally:
        await client.close()


async def enhanced_token_handler_with_filters(token_info: TokenInfo) -> None:
    """
    Enhanced token handler that applies comprehensive filtering before sending alerts.
    """
    try:
        # Apply comprehensive filters
        should_alert = await comprehensive_token_filter(token_info)
        
        if not should_alert:
            logger.info(f"🚫 Skipping alert for {token_info.name} - failed filters")
            return
        
        # Token passed all filters - send webhook alert
        logger.info(f"🚀 Sending webhook alert for filtered token: {token_info.name}")
        
        # Here you would integrate with your webhook_alert_bot
        # Example: await webhook_bot._send_webhook_alert(token_info)
        
        # For demonstration, we'll print the alert details
        print(f"\n🎉 FILTERED TOKEN ALERT:")
        print(f"   Name: {token_info.name}")
        print(f"   Symbol: {token_info.symbol}")
        print(f"   Mint: {token_info.mint}")
        print(f"   Creator: {token_info.creator}")
        print(f"   ✅ Passed symbol validation")
        print(f"   ✅ Passed wallet analysis")
        print(f"   Ready for webhook delivery\n")
        
    except Exception as e:
        logger.error(f"Error in enhanced token handler: {e}")


def get_filter_statistics(tokens_processed: list, tokens_approved: list) -> dict:
    """
    Get statistics about filtering performance.
    
    Args:
        tokens_processed: List of all tokens that were processed
        tokens_approved: List of tokens that passed all filters
        
    Returns:
        dict: Statistics about filtering performance
    """
    total_processed = len(tokens_processed)
    total_approved = len(tokens_approved)
    total_rejected = total_processed - total_approved
    
    approval_rate = (total_approved / total_processed * 100) if total_processed > 0 else 0
    
    return {
        "total_processed": total_processed,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "approval_rate_percent": round(approval_rate, 1),
        "rejection_rate_percent": round(100 - approval_rate, 1)
    }


async def test_comprehensive_filtering():
    """
    Test the comprehensive filtering system with real token data from your bot.
    """
    from solders.pubkey import Pubkey
    
    # Test tokens from your recent bot detections
    test_tokens = [
        # These should PASS (valid symbol + good wallet)
        {
            "name": "PokeBonk", 
            "symbol": "PokeBonk",  # Will fail symbol validation (too long)
            "creator": "GTB9KMuhtq9Xg9cYDxmH6Q7fqvVwnexucJjzmaYnMNDt",  # Should pass wallet
            "mint": "GGvYfJ1f6rF7Fp1uSkDBHdHSRbZuGrwZmqJuFHZVpump"
        },
        {
            "name": "Apu Apustaja",
            "symbol": "APU",  # Should pass symbol validation
            "creator": "Ez2jp3rwXUbaTx7XwiHGaWVgTPFdzJoSg8TopqbxfaJN", 
            "mint": "4id8joiG8ppv6pD5LqJrRKuiQ23pL6qt28uRaKJ3pump"
        },
        {
            "name": "Trump",
            "symbol": "TRUMP",  # Should pass symbol validation
            "creator": "F3w7uZRM5N7gvC62LF4KCkxYqF2vFuP4pXsYAYNQkMav",
            "mint": "C2QxfGzU8xatS7yhtKxJ11DkZ4XsvagSpJdz76bu8wiu"
        },
        
        # These should FAIL
        {
            "name": "Orange Mocha Frappucino",
            "symbol": "Frappucino",  # Will fail symbol validation (too long + lowercase)
            "creator": "3MdqCFJePediedd6gFG3gcBKBW55a3PzVJfEGg1fUFfG",  # Should fail wallet (too new)
            "mint": "74y88sSgd7jE41MrWRKGoXLncEX65Q2gYay7s9qypump"
        },
        {
            "name": "Tokenized Meow",
            "symbol": "MEOW",  # Should pass symbol validation
            "creator": "98yDYZddQZnh3BvnfGFb3LkMNiRMPJDzk6UKvWpkBpNc",  # Should fail wallet (too new)
            "mint": "H24Sjvsnt6YQ9sUY2Z3TTuBVNzATmsEXaC7uM4wfpump"
        },
        {
            "name": "URINAL3000",
            "symbol": "URINAL3000",  # Will fail symbol validation (too long + numbers)
            "creator": "9S8DqU5WPYib5MMrfqmjYjMNcAyAh8xqEHQDVGrjhZ3s",
            "mint": "9UM3vXDdu5kUWv9bxANHQqphQWVoQ4XszDLphL6upump"
        }
    ]
    
    print("🧪 Comprehensive Token Filtering Test")
    print("=" * 60)
    
    tokens_processed = []
    tokens_approved = []
    
    for token_data in test_tokens:
        print(f"\n📍 Testing: {token_data['name']} ({token_data['symbol']})")
        
        # Create TokenInfo object
        token_info = TokenInfo(
            name=token_data["name"],
            symbol=token_data["symbol"],
            uri="https://example.com/metadata.json",
            mint=Pubkey.from_string(token_data["mint"]),
            bonding_curve=Pubkey.from_string("11111111111111111111111111111111"),
            associated_bonding_curve=Pubkey.from_string("11111111111111111111111111111111"),
            user=Pubkey.from_string(token_data["creator"]),
            creator=Pubkey.from_string(token_data["creator"]),
            creator_vault=Pubkey.from_string("11111111111111111111111111111111"),
            signature="dummy_signature"
        )
        
        tokens_processed.append(token_info)
        
        # Test comprehensive filtering
        passed_filters = await comprehensive_token_filter(token_info)
        
        if passed_filters:
            tokens_approved.append(token_info)
            print(f"   🎉 APPROVED - Ready for webhook alert")
        else:
            print(f"   🚫 REJECTED - Filters failed")
        
        print("-" * 40)
    
    # Print statistics
    stats = get_filter_statistics(tokens_processed, tokens_approved)
    print(f"\n📊 FILTERING STATISTICS:")
    print(f"   Total Processed: {stats['total_processed']}")
    print(f"   Approved: {stats['total_approved']}")
    print(f"   Rejected: {stats['total_rejected']}")
    print(f"   Approval Rate: {stats['approval_rate_percent']}%")
    print(f"   Rejection Rate: {stats['rejection_rate_percent']}%")


if __name__ == "__main__":
    asyncio.run(test_comprehensive_filtering())