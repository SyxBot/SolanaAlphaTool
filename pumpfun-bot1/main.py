#!/usr/bin/env python3
"""
Main entry point for the Solana Signal Alert Bot on Replit
Validates environment and starts the webhook alert system
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv


def check_dependencies():
    """Check if all required dependencies are installed."""
    required_modules = [
        'solana',
        'base58',
        'websockets',
        'aiohttp',
        'construct',
        'borsh_construct',
        'solders'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("❌ Missing required dependencies:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\n💡 Install dependencies with:")
        print("   pip install base58 borsh-construct construct construct-typing solana==0.36.6 solders websockets python-dotenv aiohttp")
        return False
    
    print("✅ All dependencies are installed")
    return True


def check_environment():
    """Check environment configuration for webhook alert bot."""
    load_dotenv()
    
    # Check required API key
    helius_api_key = os.getenv('HELIUS_API_KEY')
    if not helius_api_key:
        print("❌ Missing required secret: HELIUS_API_KEY")
        print("   Add your Helius API key in Replit Secrets tab")
        print("   Get one from: https://www.helius.dev/")
        return False
    
    # Check webhook configuration
    webhook_type = os.getenv('WEBHOOK_TYPE')
    if not webhook_type:
        print("⚠️  No webhook type configured")
        print("   Set WEBHOOK_TYPE to 'telegram', 'discord', or 'generic' in Secrets")
        print("   Run: python setup_webhook.py for interactive setup")
        return False
    
    # Validate webhook-specific configuration
    if webhook_type == 'telegram':
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("❌ Missing Telegram configuration")
            print("   Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to Secrets")
            return False
    elif webhook_type == 'discord':
        if not os.getenv('DISCORD_WEBHOOK_URL'):
            print("❌ Missing Discord webhook URL")
            print("   Add DISCORD_WEBHOOK_URL to Secrets")
            return False
    elif webhook_type == 'generic':
        if not os.getenv('WEBHOOK_URL'):
            print("❌ Missing generic webhook URL")
            print("   Add WEBHOOK_URL to Secrets")
            return False
    
    print("✅ Environment configuration is valid")
    print(f"📡 Webhook type: {webhook_type}")
    return True


async def start_webhook_bot():
    """Start the webhook alert bot."""
    try:
        from webhook_alert_bot import main as webhook_main
        await webhook_main()
    except ImportError:
        print("❌ Cannot import webhook_alert_bot.py")
        print("   Ensure webhook_alert_bot.py is in the project directory")
        return False
    except Exception as e:
        print(f"❌ Error starting webhook bot: {e}")
        return False


def main():
    """Main function to validate setup and start webhook alert bot."""
    print("🚀 Solana Signal Alert Bot - Replit Deployment")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        print(f"   Current version: {sys.version}")
        return 1
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check environment
    if not check_environment():
        return 1
    
    print("\n🎉 Setup validation completed successfully!")
    print("\n🚀 Starting Solana Signal Alert Bot...")
    print("   This bot will run continuously and send webhook alerts for new pump.fun tokens")
    print("   Press Ctrl+C to stop and view statistics")
    print("\n⚠️  NOTE: This monitors blockchain data in real-time.")
    print("   Webhook alerts will be sent when tokens are detected.")
    
    # Start the webhook alert bot
    try:
        print("\n" + "=" * 50)
        asyncio.run(start_webhook_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        print("   Thank you for using the Solana Signal Alert Bot!")
    except Exception as e:
        print(f"\n❌ Error running webhook bot: {e}")
        print("   Check your configuration and try again")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
