#!/usr/bin/env python3
"""
Pump.fun Token Launch Monitor
Extracted from: https://github.com/chainstacklabs/pump-fun-bot

This module monitors Solana for new pump.fun token launches using WebSocket connections.
It does NOT execute trades - only detects and logs new token creation events.
"""

import asyncio
import json
import logging
import base64
import struct
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

import websockets
import base58
from solders.pubkey import Pubkey

# Pump.fun program constants from the official repository
PUMP_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

# Create instruction discriminator from official bot
CREATE_DISCRIMINATOR = 8530921459188068891

logger = logging.getLogger(__name__)

@dataclass
class TokenInfo:
    """Token information extracted from pump.fun creation events."""
    name: str
    symbol: str
    uri: str
    mint: Pubkey
    bonding_curve: Pubkey
    associated_bonding_curve: Pubkey
    user: Pubkey
    creator: Pubkey
    creator_vault: Pubkey
    signature: str

    def __str__(self):
        return f"{self.name} ({self.symbol}) - Mint: {self.mint}"

class PumpMonitor:
    """Monitors pump.fun for new token launches using logsSubscribe."""

    def __init__(self, wss_endpoint: str):
        """Initialize the monitor.
        
        Args:
            wss_endpoint: WebSocket endpoint URL for Solana RPC
        """
        self.wss_endpoint = wss_endpoint
        self.ping_interval = 20

    async def listen_for_tokens(
        self,
        token_callback: Callable[[TokenInfo], Awaitable[None]],
        match_string: Optional[str] = None,
        creator_address: Optional[str] = None,
    ) -> None:
        """Listen for new token creations using logsSubscribe.

        Args:
            token_callback: Async callback function for new tokens
            match_string: Optional string to match in token name/symbol
            creator_address: Optional creator address to filter by
        """
        while True:
            try:
                async with websockets.connect(self.wss_endpoint) as websocket:
                    await self._subscribe_to_logs(websocket)
                    ping_task = asyncio.create_task(self._ping_loop(websocket))

                    try:
                        while True:
                            token_info = await self._wait_for_token_creation(websocket)
                            if not token_info:
                                continue

                            logger.info(f"New token detected: {token_info}")

                            # Apply filters
                            if match_string and not self._matches_filter(token_info, match_string):
                                logger.info(f"Token does not match filter '{match_string}'. Skipping...")
                                continue

                            if creator_address and str(token_info.user) != creator_address:
                                logger.info(f"Token not created by {creator_address}. Skipping...")
                                continue

                            await token_callback(token_info)

                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed. Reconnecting...")
                        ping_task.cancel()

            except Exception as e:
                logger.error(f"WebSocket connection error: {str(e)}")
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    def _matches_filter(self, token_info: TokenInfo, match_string: str) -> bool:
        """Check if token matches the filter string."""
        return (
            match_string.lower() in token_info.name.lower() or
            match_string.lower() in token_info.symbol.lower()
        )

    async def _subscribe_to_logs(self, websocket) -> None:
        """Subscribe to logs mentioning the pump.fun program."""
        subscription_message = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [str(PUMP_PROGRAM)]},
                {"commitment": "processed"},
            ],
        })

        await websocket.send(subscription_message)
        logger.info(f"Subscribed to logs mentioning program: {PUMP_PROGRAM}")

        # Wait for subscription confirmation
        response = await websocket.recv()
        response_data = json.loads(response)
        if "result" in response_data:
            logger.info(f"Subscription confirmed with ID: {response_data['result']}")
        else:
            logger.warning(f"Unexpected subscription response: {response}")

    async def _ping_loop(self, websocket) -> None:
        """Keep connection alive with pings."""
        try:
            while True:
                await asyncio.sleep(self.ping_interval)
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                except asyncio.TimeoutError:
                    logger.warning("Ping timeout - server not responding")
                    await websocket.close()
                    return
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ping error: {str(e)}")

    async def _wait_for_token_creation(self, websocket) -> Optional[TokenInfo]:
        """Wait for token creation event from logs."""
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=30)
            data = json.loads(response)

            if "method" not in data or data["method"] != "logsNotification":
                return None

            log_data = data["params"]["result"]["value"]
            logs = log_data.get("logs", [])
            signature = log_data.get("signature", "unknown")

            return self._process_program_logs(logs, signature)

        except asyncio.TimeoutError:
            logger.debug("No data received for 30 seconds")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            raise
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")

        return None

    def _process_program_logs(self, logs: list[str], signature: str) -> Optional[TokenInfo]:
        """Process program logs and extract token info."""
        # Check if this is a token creation
        if not any("Program log: Instruction: Create" in log for log in logs):
            return None

        # Skip swaps as the first condition may pass them
        if any("Program log: Instruction: CreateTokenAccount" in log for log in logs):
            return None

        # Find and process program data
        for log in logs:
            if "Program data:" in log:
                try:
                    encoded_data = log.split(": ")[1]
                    decoded_data = base64.b64decode(encoded_data)
                    parsed_data = self._parse_create_instruction(decoded_data)

                    if parsed_data and "name" in parsed_data:
                        mint = Pubkey.from_string(parsed_data["mint"])
                        bonding_curve = Pubkey.from_string(parsed_data["bondingCurve"])
                        associated_curve = self._find_associated_bonding_curve(mint, bonding_curve)
                        creator = Pubkey.from_string(parsed_data["creator"])
                        creator_vault = self._find_creator_vault(creator)

                        return TokenInfo(
                            name=parsed_data["name"],
                            symbol=parsed_data["symbol"],
                            uri=parsed_data["uri"],
                            mint=mint,
                            bonding_curve=bonding_curve,
                            associated_bonding_curve=associated_curve,
                            user=Pubkey.from_string(parsed_data["user"]),
                            creator=creator,
                            creator_vault=creator_vault,
                            signature=signature,
                        )
                except Exception as e:
                    logger.error(f"Failed to process log data: {e}")

        return None

    def _parse_create_instruction(self, data: bytes) -> Optional[dict]:
        """Parse the create instruction data from pump.fun."""
        if len(data) < 8:
            return None

        # Check for the correct instruction discriminator
        discriminator = struct.unpack("<Q", data[:8])[0]
        if discriminator != CREATE_DISCRIMINATOR:
            logger.debug(f"Skipping non-Create instruction with discriminator: {discriminator}")
            return None

        offset = 8
        parsed_data = {}

        # Parse fields based on CreateEvent structure from official bot
        fields = [
            ("name", "string"),
            ("symbol", "string"),
            ("uri", "string"),
            ("mint", "publicKey"),
            ("bondingCurve", "publicKey"),
            ("user", "publicKey"),
            ("creator", "publicKey"),
        ]

        try:
            for field_name, field_type in fields:
                if field_type == "string":
                    length = struct.unpack("<I", data[offset : offset + 4])[0]
                    offset += 4
                    value = data[offset : offset + length].decode("utf-8")
                    offset += length
                elif field_type == "publicKey":
                    value = base58.b58encode(data[offset : offset + 32]).decode("utf-8")
                    offset += 32

                parsed_data[field_name] = value

            return parsed_data
        except Exception as e:
            logger.error(f"Failed to parse create instruction: {e}")
            return None

    def _find_associated_bonding_curve(self, mint: Pubkey, bonding_curve: Pubkey) -> Pubkey:
        """Find the associated bonding curve using standard ATA derivation."""
        derived_address, _ = Pubkey.find_program_address(
            [
                bytes(bonding_curve),
                bytes(TOKEN_PROGRAM),
                bytes(mint),
            ],
            ASSOCIATED_TOKEN_PROGRAM,
        )
        return derived_address

    def _find_creator_vault(self, creator: Pubkey) -> Pubkey:
        """Find the creator vault for a creator."""
        derived_address, _ = Pubkey.find_program_address(
            [
                b"creator-vault",
                bytes(creator)
            ],
            PUMP_PROGRAM,
        )
        return derived_address


# Example usage functions
async def log_new_tokens(token_info: TokenInfo) -> None:
    """Example callback that logs new token information."""
    print(f"\n🚀 NEW TOKEN DETECTED:")
    print(f"  Name: {token_info.name}")
    print(f"  Symbol: {token_info.symbol}")
    print(f"  Mint: {token_info.mint}")
    print(f"  Creator: {token_info.creator}")
    print(f"  Bonding Curve: {token_info.bonding_curve}")
    print(f"  Transaction: {token_info.signature}")
    print(f"  Metadata URI: {token_info.uri}")
    print("-" * 60)


async def main():
    """Example main function demonstrating how to use the monitor."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Use your Helius WebSocket endpoint
    wss_endpoint = "wss://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY"
    
    monitor = PumpMonitor(wss_endpoint)
    
    print("🔍 Starting pump.fun token monitor...")
    print("Press Ctrl+C to stop")
    
    try:
        await monitor.listen_for_tokens(
            token_callback=log_new_tokens,
            # match_string="doge",  # Optional: only tokens containing "doge"
            # creator_address="CREATOR_PUBKEY_HERE",  # Optional: only from specific creator
        )
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")


if __name__ == "__main__":
    asyncio.run(main())