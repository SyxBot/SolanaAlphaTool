#!/usr/bin/env python3
"""
Main entry point for the Solana Signal Alert Bot.

This script validates your environment configuration and starts the
webhook alert system.  Previously this project expected you to
configure API keys and webhook tokens via Replit Secrets.  It has
since been updated to read its configuration from a local ``.env``
file using ``python-dotenv``.  Ensure you create a ``.env`` file in
the project root with the required environment variables before
running the bot.
"""

import os
import sys
import asyncio
import logging
import json
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
        print("❌ Missing required environment variable: HELIUS_API_KEY")
        print("   Add your Helius API key to the .env file (see .env.example)")
        print("   You can obtain a key from: https://www.helius.dev/")
        return False
    
    # Check webhook configuration
    webhook_type = os.getenv('WEBHOOK_TYPE')
    if not webhook_type:
        print("⚠️  No webhook type configured")
        print("   Set WEBHOOK_TYPE to 'telegram', 'discord', or 'generic' in your .env file")
        print("   You can run: python setup_webhook.py for an interactive setup")
        return False
    
    # Validate webhook-specific configuration
    if webhook_type == 'telegram':
        if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("❌ Missing Telegram configuration")
            print("   Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your .env file")
            return False
    elif webhook_type == 'discord':
        if not os.getenv('DISCORD_WEBHOOK_URL'):
            print("❌ Missing Discord webhook URL")
            print("   Add DISCORD_WEBHOOK_URL to your .env file")
            return False
    elif webhook_type == 'generic':
        if not os.getenv('WEBHOOK_URL'):
            print("❌ Missing generic webhook URL")
            print("   Add WEBHOOK_URL to your .env file")
            return False
    
    print("✅ Environment configuration is valid")
    print(f"📡 Webhook type: {webhook_type}")
    return True


# Load rules from config/rules.json
try:
    with open("config/rules.json") as f:
        rules = json.load(f)
except Exception as e:
    print(f"⚠️  Could not load config/rules.json: {e}")
    rules = {}

async def process_events(batch):
    """Process a batch of events through rpc_prefilter and security_gate."""
    # -- begin rpc/security hook (guarded) --
    from filters.rpc_prefilter import rpc_prefilter  # idempotent if already present
    from filters.security_gate import security_gate  # idempotent if already present

    if rules.get("enable_rpc_prefilter", False):
        survivors, drop_stats = rpc_prefilter(batch, rules)
        try:
            import logging
            logging.info(f"[RPC] batched {len(batch)} mints → {len(survivors)} pass, {len(batch) - len(survivors)} drop ({drop_stats})")
        except Exception:
            print(f"[RPC] batched {len(batch)} mints → {len(survivors)} pass, {len(batch) - len(survivors)} drop ({drop_stats})")
    else:
        survivors = batch

    if rules.get("enable_security_gate", False):
        finals, sec_drops = security_gate(survivors, rules)
        if sec_drops:
            try:
                import logging
                logging.info(f"[SECURITY drop] {sec_drops}")
            except Exception:
                print(f"[SECURITY drop] {sec_drops}")
    else:
        finals = survivors
    # -- end rpc/security hook --

    return finals


async def start_webhook_bot():
    """Start the webhook alert bot."""
    MAX_BATCH_SIZE = 50
    try:
        from webhook_alert_bot import main as webhook_main
        from bridge.to_eliza import send_to_eliza

        # Example: Fetch a batch of events (replace with actual event fetching logic)
        batch = []  # Replace with actual batch fetching logic

        # Process the batch through the pipeline
        finals = await process_events(batch)

        # Cap the batch size to prevent overloading
        finals = finals[:MAX_BATCH_SIZE]

        # Forward finals to the next stage (e.g., bridge/alerts)
        if os.getenv("ELIZA_INGEST_URL") or rules.get("ELIZA_INGEST_URL"):
            for ev in finals:
                send_to_eliza(ev, rules)
                await asyncio.sleep(0.05)  # Add a micro-delay per send

        await webhook_main()
        await asyncio.sleep(1)  # Add a backoff after processing each batch

        # Add a minimal backoff to prevent tight loop crashes
        await asyncio.sleep(0.1)
    except ImportError:
        print("❌ Cannot import webhook_alert_bot.py")
        print("   Ensure webhook_alert_bot.py is in the project directory")
        return False
    except Exception as e:
        print(f"❌ Error starting webhook bot: {e}")
        return False


def main():
    """Main function to validate setup and start webhook alert bot.

    This function validates your local environment configuration and starts
    the webhook alert bot.  It no longer references Replit at all –
    instead, configuration should be provided via a local ``.env`` file.
    """
    # Print a friendly header to signal startup without mentioning Replit
    print("🚀 Solana Signal Alert Bot")
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
