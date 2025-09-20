#!/usr/bin/env python3
"""
Test script for the pump.fun token monitor using real Helius API configuration.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from pump_monitor import PumpMonitor, TokenInfo

# Load environment variables
load_dotenv()

async def token_handler(token_info: TokenInfo) -> None:
    """Handle detected tokens by logging their information."""
    print(f"\n🎯 NEW PUMP.FUN TOKEN DETECTED!")
    print(f"📛 Name: {token_info.name}")
    print(f"🏷️  Symbol: {token_info.symbol}")
    print(f"🆔 Mint Address: {token_info.mint}")
    print(f"👤 Creator: {token_info.creator}")
    print(f"🔗 Bonding Curve: {token_info.bonding_curve}")
    print(f"📊 Associated Curve: {token_info.associated_bonding_curve}")
    print(f"📜 Transaction: {token_info.signature}")
    print(f"🌐 Metadata URI: {token_info.uri}")
    print("=" * 80)

async def main():
    """Main function to test the monitor with Helius API."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Get WebSocket endpoint from environment
    helius_api_key = os.getenv("HELIUS_API_KEY")
    if not helius_api_key:
        print("❌ HELIUS_API_KEY not found in environment variables")
        return

    wss_endpoint = f"wss://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    
    print("🚀 Starting pump.fun token monitor...")
    print(f"🔗 Connecting to: {wss_endpoint[:50]}...")  # Don't log full API key
    print("📡 Monitoring for new token launches...")
    print("⏹️  Press Ctrl+C to stop")
    print("=" * 80)

    monitor = PumpMonitor(wss_endpoint)
    
    try:
        await monitor.listen_for_tokens(
            token_callback=token_handler,
            # Uncomment to filter by token name/symbol:
            # match_string="test",
            
            # Uncomment to filter by creator address:
            # creator_address="CREATOR_PUBKEY_HERE",
        )
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")
        logging.exception("Monitor failed")

if __name__ == "__main__":
    asyncio.run(main())