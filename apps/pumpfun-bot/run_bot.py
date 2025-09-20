#!/usr/bin/env python3
"""
Direct webhook alert bot runner.

This script provides a simplified entry point that runs the webhook
alert bot directly without performing environment validation.  It is
useful for local development or situations where you are confident
that all required environment variables are already set via a ``.env``
file.  Previously this helper was intended for Replit deployments,
but it has been generalized and now reads configuration from the
standard ``.env`` file when run.
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