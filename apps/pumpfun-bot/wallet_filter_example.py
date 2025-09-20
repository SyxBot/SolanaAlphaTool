"""
Example integration of wallet analysis with the webhook alert bot.
Shows how to filter suspicious token creators before sending alerts.
"""

import asyncio
import os
from solana.rpc.async_api import AsyncClient
from wallet_analyzer import is_wallet_suspicious_async, get_wallet_details
from pump_monitor import TokenInfo
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def enhanced_token_handler(token_info: TokenInfo) -> None:
    """
    Enhanced token handler that analyzes creator wallet before sending alerts.
    Only sends alerts for tokens from "safe" wallets.
    """
    # Get Helius endpoint
    helius_key = os.getenv("HELIUS_API_KEY")
    if not helius_key:
        logger.warning("HELIUS_API_KEY not found, using public RPC")
        rpc_url = "https://api.mainnet-beta.solana.com"
    else:
        rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    
    client = AsyncClient(rpc_url)
    
    try:
        # Analyze creator wallet
        creator_address = str(token_info.creator)
        
        # Get detailed wallet analysis
        wallet_details = await get_wallet_details(creator_address, client)
        
        logger.info(f"🔍 Analyzing creator {creator_address} for token {token_info.name}")
        logger.info(f"   Wallet age: {wallet_details['age_minutes']:.1f} minutes")
        logger.info(f"   Transaction count: {wallet_details['transaction_count']}")
        logger.info(f"   Analysis: {'SUSPICIOUS' if wallet_details['is_suspicious'] else 'SAFE'}")
        logger.info(f"   Reason: {wallet_details['reason']}")
        
        if wallet_details['is_suspicious']:
            logger.warning(f"⚠️  Skipping alert for {token_info.name} - suspicious creator wallet")
            logger.warning(f"   Creator: {creator_address}")
            logger.warning(f"   Reason: {wallet_details['reason']}")
            return
        
        # If we reach here, the wallet is considered safe
        logger.info(f"✅ Wallet analysis passed for {token_info.name}")
        logger.info(f"   Proceeding with webhook alert...")
        
        # Here you would call your normal webhook alert function
        # Example: await send_webhook_alert(token_info)
        print(f"🚀 WOULD SEND ALERT: {token_info.name} ({token_info.symbol})")
        print(f"   Creator: {creator_address} (VERIFIED SAFE)")
        print(f"   Mint: {token_info.mint}")
        
    except Exception as e:
        logger.error(f"Error analyzing wallet for {token_info.name}: {e}")
        logger.warning(f"Defaulting to NOT sending alert due to analysis error")
        
    finally:
        await client.close()


async def test_wallet_filtering():
    """
    Test the wallet filtering with recent token creators from your logs.
    """
    from solders.pubkey import Pubkey
    
    # Create test token info objects from your recent detections
    test_tokens = [
        {
            "name": "Orange Mocha Frappucino",
            "symbol": "Frappucino", 
            "creator": "3MdqCFJePediedd6gFG3gcBKBW55a3PzVJfEGg1fUFfG",
            "mint": "74y88sSgd7jE41MrWRKGoXLncEX65Q2gYay7s9qypump"
        },
        {
            "name": "PokeBonk",
            "symbol": "PokeBonk",
            "creator": "GTB9KMuhtq9Xg9cYDxmH6Q7fqvVwnexucJjzmaYnMNDt", 
            "mint": "GGvYfJ1f6rF7Fp1uSkDBHdHSRbZuGrwZmqJuFHZVpump"
        },
        {
            "name": "Tokenized Meow",
            "symbol": "MEOW",
            "creator": "98yDYZddQZnh3BvnfGFb3LkMNiRMPJDzk6UKvWpkBpNc",
            "mint": "H24Sjvsnt6YQ9sUY2Z3TTuBVNzATmsEXaC7uM4wfpump"
        }
    ]
    
    print("🧪 Testing Wallet Filtering System")
    print("=" * 50)
    
    for token_data in test_tokens:
        print(f"\n📍 Testing token: {token_data['name']}")
        
        # Create a TokenInfo object
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
        
        # Test the enhanced handler
        await enhanced_token_handler(token_info)
        print()


if __name__ == "__main__":
    asyncio.run(test_wallet_filtering())