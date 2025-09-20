#!/usr/bin/env python3
"""
Direct bot runner for Replit - Alternative to main.py
Use this if you want to skip validation and run the webhook bot directly
"""

import asyncio
import sys

async def main():
    """Run the webhook alert bot directly."""
    try:
        from webhook_alert_bot import main as webhook_main
        await webhook_main()
    except ImportError:
        print("❌ Cannot import webhook_alert_bot.py")
        print("   Ensure all files are in the project directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting Webhook Alert Bot directly...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)