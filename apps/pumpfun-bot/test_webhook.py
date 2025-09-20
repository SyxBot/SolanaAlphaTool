#!/usr/bin/env python3
"""
Test script for webhook functionality using real token detection.
This script validates webhook delivery without waiting for real tokens.
"""

import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from solders.pubkey import Pubkey

from webhook_alert_bot import WebhookAlertBot, WebhookConfig
from pump_monitor import TokenInfo

# Load environment variables
load_dotenv()

def create_test_token_info() -> TokenInfo:
    """Create a realistic test token based on actual pump.fun structure."""
    # Use realistic Solana addresses (these are example addresses, not real tokens)
    return TokenInfo(
        name="TestDoge",
        symbol="TDOGE", 
        uri="https://pump.fun/meta/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU.json",
        mint=Pubkey.from_string("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"),
        bonding_curve=Pubkey.from_string("CebN5uJmj6F7vG2jNjbbCs5DXksJgNpGPq4q9DGoPWd1"),
        associated_bonding_curve=Pubkey.from_string("5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"),
        user=Pubkey.from_string("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"),
        creator=Pubkey.from_string("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"),
        creator_vault=Pubkey.from_string("8VoNJ8yFTcNLmAhQNGjVpB2pGhfHzYmQ7FkJgPxG3nYW"),
        signature="5J8YU7v4gW2KgjsXP1uFYEjyG3jKGN4w9L4z8YVyXzLmK3NJxP6Dx9TcRbGFfMsW8xYu7V6kN1mL2FhZq5P4wQ8T"
    )

async def test_webhook_delivery():
    """Test webhook delivery with different configurations."""
    logging.basicConfig(level=logging.INFO)
    
    # Get webhook configuration from environment
    webhook_type = os.getenv("WEBHOOK_TYPE", "generic")
    
    print(f"🧪 Testing webhook delivery...")
    print(f"📡 Webhook type: {webhook_type}")
    
    # Create appropriate config based on type
    if webhook_type == "telegram":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("❌ Missing Telegram configuration. Run: python setup_webhook.py")
            return
            
        webhook_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        config = WebhookConfig(
            webhook_url=webhook_url,
            webhook_type="telegram",
            telegram_chat_id=chat_id
        )
        
    elif webhook_type == "discord":
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        
        if not webhook_url:
            print("❌ Missing Discord webhook URL. Run: python setup_webhook.py")
            return
            
        config = WebhookConfig(
            webhook_url=webhook_url,
            webhook_type="discord"
        )
        
    else:
        webhook_url = os.getenv("WEBHOOK_URL")
        
        if not webhook_url:
            print("❌ Missing webhook URL. Run: python setup_webhook.py")
            return
            
        config = WebhookConfig(
            webhook_url=webhook_url,
            webhook_type="generic"
        )
    
    print(f"🔗 Webhook URL: {config.webhook_url}")
    
    # Create test bot (no need for real WebSocket endpoint for testing)
    bot = WebhookAlertBot("wss://test.endpoint", config)
    
    # Initialize session
    import aiohttp
    bot.session = aiohttp.ClientSession()
    
    try:
        # Create test token info
        test_token = create_test_token_info()
        
        print(f"\n📝 Test token details:")
        print(f"   Name: {test_token.name}")
        print(f"   Symbol: {test_token.symbol}")
        print(f"   Mint: {test_token.mint}")
        print(f"   Creator: {test_token.creator}")
        
        # Send test webhook
        print(f"\n📤 Sending test webhook...")
        await bot._send_webhook_alert(test_token)
        
        # Check results
        stats = bot.get_stats()
        if stats["webhooks_sent"] > 0:
            print(f"✅ Webhook test successful!")
            print(f"📊 Webhooks sent: {stats['webhooks_sent']}")
        else:
            print(f"❌ Webhook test failed!")
            print(f"📊 Failures: {stats['webhook_failures']}")
    
    finally:
        await bot.session.close()

async def test_webhook_formats():
    """Test different webhook message formats."""
    print("\n🎨 Testing webhook message formats...")
    
    test_token = create_test_token_info()
    
    # Test Telegram format
    dummy_config = WebhookConfig(
        webhook_url="https://test.url",
        webhook_type="telegram",
        telegram_chat_id="123456789"
    )
    bot = WebhookAlertBot("wss://test", dummy_config)
    telegram_msg = bot._format_telegram_message(test_token)
    
    print("\n📱 Telegram message format:")
    print(telegram_msg["text"])
    
    # Test Discord format
    dummy_config.webhook_type = "discord"
    discord_msg = bot._format_discord_message(test_token)
    
    print("\n💬 Discord embed format:")
    print(f"Title: {discord_msg['embeds'][0]['title']}")
    for field in discord_msg['embeds'][0]['fields']:
        print(f"  {field['name']}: {field['value']}")
    
    # Test Generic format
    dummy_config.webhook_type = "generic"
    generic_msg = bot._format_generic_message(test_token)
    
    print("\n🌐 Generic JSON format:")
    import json
    print(json.dumps(generic_msg, indent=2))

async def main():
    """Main test function."""
    print("🧪 Pump.fun Webhook Test Suite")
    print("=" * 50)
    
    # Test message formats
    await test_webhook_formats()
    
    print("\n" + "=" * 50)
    
    # Test actual webhook delivery if configured
    webhook_type = os.getenv("WEBHOOK_TYPE")
    if webhook_type:
        await test_webhook_delivery()
    else:
        print("⚙️  No webhook configured. Run: python setup_webhook.py")
        print("   Then run this test again to validate delivery")

if __name__ == "__main__":
    asyncio.run(main())