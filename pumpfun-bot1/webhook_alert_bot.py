#!/usr/bin/env python3
"""
Pump.fun Webhook Alert Bot
Real-time webhook alerts for pump.fun token launches using authentic detection logic.
Sends structured alerts to Telegram, Discord, or any webhook endpoint.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

import aiohttp
from dotenv import load_dotenv

from pump_monitor import PumpMonitor, TokenInfo

# Load environment variables
load_dotenv()

@dataclass
class WebhookConfig:
    """Configuration for webhook alerts."""
    webhook_url: str
    webhook_type: str = "generic"  # "telegram", "discord", "generic"
    rate_limit_seconds: float = 1.0
    timeout_seconds: int = 10
    retry_attempts: int = 3
    
    # Telegram-specific
    telegram_chat_id: Optional[str] = None
    telegram_parse_mode: str = "HTML"
    
    # Discord-specific  
    discord_username: Optional[str] = "Pump.fun Alert Bot"
    discord_avatar_url: Optional[str] = None

class WebhookAlertBot:
    """Webhook alert bot for pump.fun token launches."""
    
    def __init__(self, wss_endpoint: str, config: WebhookConfig):
        self.wss_endpoint = wss_endpoint
        self.config = config
        self.monitor = PumpMonitor(wss_endpoint)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.last_alert_time = 0
        
        # Statistics
        self.stats = {
            "tokens_detected": 0,
            "webhooks_sent": 0,
            "webhook_failures": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the webhook alert bot."""
        self.logger.info("Starting Pump.fun Webhook Alert Bot")
        self.logger.info(f"Webhook Type: {self.config.webhook_type}")
        self.logger.info(f"Webhook URL: {self.config.webhook_url}")
        
        # Initialize HTTP session
        self.session = aiohttp.ClientSession()
        
        try:
            await self.monitor.listen_for_tokens(
                token_callback=self._handle_token_detection
            )
        finally:
            if self.session:
                await self.session.close()

    async def _handle_token_detection(self, token_info: TokenInfo):
        """Handle detected token and send webhook alert."""
        self.stats["tokens_detected"] += 1
        
        # Rate limiting check
        current_time = time.time()
        if current_time - self.last_alert_time < self.config.rate_limit_seconds:
            self.logger.debug(f"Rate limited alert for: {token_info.name}")
            return
        
        self.last_alert_time = current_time
        
        # Log detection
        self.logger.info(f"🎯 Token detected: {token_info.name} ({token_info.symbol})")
        self.logger.info(f"   Mint: {token_info.mint}")
        self.logger.info(f"   Creator: {token_info.creator}")
        self.logger.info(f"   TX: {token_info.signature}")
        
        # Send webhook alert
        await self._send_webhook_alert(token_info)

    def _generate_pump_fun_url(self, mint_address: str) -> str:
        """Generate pump.fun URL for the token."""
        return f"https://pump.fun/{mint_address}"

    def _generate_solscan_url(self, signature: str) -> str:
        """Generate Solscan URL for the transaction."""
        return f"https://solscan.io/tx/{signature}"

    def _format_telegram_message(self, token_info: TokenInfo) -> Dict[str, Any]:
        """Format message for Telegram webhook."""
        launch_time = datetime.now().strftime("%H:%M:%S UTC")
        pump_url = self._generate_pump_fun_url(str(token_info.mint))
        solscan_url = self._generate_solscan_url(token_info.signature)
        
        message = f"""🚀 <b>NEW PUMP.FUN TOKEN LAUNCH</b>

📛 <b>Name:</b> {token_info.name}
🏷️ <b>Symbol:</b> {token_info.symbol}
🆔 <b>Mint:</b> <code>{token_info.mint}</code>
👤 <b>Creator:</b> <code>{token_info.creator}</code>
⏰ <b>Launch Time:</b> {launch_time}

🔗 <b>Links:</b>
• <a href="{pump_url}">View on Pump.fun</a>
• <a href="{solscan_url}">Transaction on Solscan</a>

💎 <b>Bonding Curve:</b> <code>{token_info.bonding_curve}</code>
📊 <b>Associated Curve:</b> <code>{token_info.associated_bonding_curve}</code>"""

        return {
            "chat_id": self.config.telegram_chat_id,
            "text": message,
            "parse_mode": self.config.telegram_parse_mode,
            "disable_web_page_preview": False
        }

    def _format_discord_message(self, token_info: TokenInfo) -> Dict[str, Any]:
        """Format message for Discord webhook."""
        launch_time = datetime.now().strftime("%H:%M:%S UTC")
        pump_url = self._generate_pump_fun_url(str(token_info.mint))
        solscan_url = self._generate_solscan_url(token_info.signature)
        
        embed = {
            "title": "🚀 NEW PUMP.FUN TOKEN LAUNCH",
            "color": 0x00FF00,  # Green color
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📛 Token Name",
                    "value": token_info.name,
                    "inline": True
                },
                {
                    "name": "🏷️ Symbol", 
                    "value": token_info.symbol,
                    "inline": True
                },
                {
                    "name": "⏰ Launch Time",
                    "value": launch_time,
                    "inline": True
                },
                {
                    "name": "🆔 Mint Address",
                    "value": f"`{token_info.mint}`",
                    "inline": False
                },
                {
                    "name": "👤 Creator",
                    "value": f"`{token_info.creator}`",
                    "inline": False
                },
                {
                    "name": "🔗 Quick Links",
                    "value": f"[View on Pump.fun]({pump_url}) • [Transaction]({solscan_url})",
                    "inline": False
                }
            ],
            "footer": {
                "text": "Pump.fun Alert Bot",
                "icon_url": self.config.discord_avatar_url
            }
        }

        payload = {
            "embeds": [embed]
        }
        
        if self.config.discord_username:
            payload["username"] = self.config.discord_username
            
        if self.config.discord_avatar_url:
            payload["avatar_url"] = self.config.discord_avatar_url

        return payload

    def _format_generic_message(self, token_info: TokenInfo) -> Dict[str, Any]:
        """Format message for generic webhook."""
        launch_time = datetime.now().isoformat()
        pump_url = self._generate_pump_fun_url(str(token_info.mint))
        solscan_url = self._generate_solscan_url(token_info.signature)
        
        return {
            "alert_type": "pump_fun_token_launch",
            "timestamp": launch_time,
            "token": {
                "name": token_info.name,
                "symbol": token_info.symbol,
                "mint_address": str(token_info.mint),
                "creator_address": str(token_info.creator),
                "bonding_curve": str(token_info.bonding_curve),
                "associated_bonding_curve": str(token_info.associated_bonding_curve),
                "metadata_uri": token_info.uri,
                "transaction_signature": token_info.signature,
                "launch_time": launch_time,
                "pump_fun_url": pump_url,
                "solscan_url": solscan_url
            },
            "stats": self.stats.copy()
        }

    async def _send_webhook_alert(self, token_info: TokenInfo):
        """Send webhook alert with retry logic."""
        if not self.session:
            self.logger.error("HTTP session not initialized")
            return

        # Format message based on webhook type
        if self.config.webhook_type == "telegram":
            payload = self._format_telegram_message(token_info)
            headers = {"Content-Type": "application/json"}
        elif self.config.webhook_type == "discord":
            payload = self._format_discord_message(token_info)
            headers = {"Content-Type": "application/json"}
        else:
            payload = self._format_generic_message(token_info)
            headers = {"Content-Type": "application/json"}

        # Retry logic
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.post(
                    self.config.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status < 400:
                        self.stats["webhooks_sent"] += 1
                        self.logger.info(f"✅ Webhook sent successfully for {token_info.name}")
                        return
                    else:
                        error_text = await response.text()
                        self.logger.warning(
                            f"❌ Webhook failed (attempt {attempt + 1}): "
                            f"Status {response.status} - {error_text[:200]}"
                        )
                        
            except asyncio.TimeoutError:
                self.logger.warning(f"⏱️ Webhook timeout (attempt {attempt + 1})")
            except Exception as e:
                self.logger.warning(f"❌ Webhook error (attempt {attempt + 1}): {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(2 ** attempt)
        
        self.stats["webhook_failures"] += 1
        self.logger.error(f"❌ Failed to send webhook after {self.config.retry_attempts} attempts")

    def get_stats(self) -> Dict[str, Any]:
        """Get current bot statistics."""
        runtime = datetime.now() - datetime.fromisoformat(self.stats["start_time"])
        
        return {
            **self.stats,
            "runtime_seconds": int(runtime.total_seconds()),
            "success_rate": (
                self.stats["webhooks_sent"] / max(self.stats["tokens_detected"], 1) * 100
            ),
            "failure_rate": (
                self.stats["webhook_failures"] / max(self.stats["tokens_detected"], 1) * 100
            )
        }


def create_telegram_config(bot_token: str, chat_id: str, rate_limit: float = 1.0) -> WebhookConfig:
    """Create Telegram webhook configuration."""
    webhook_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    return WebhookConfig(
        webhook_url=webhook_url,
        webhook_type="telegram",
        telegram_chat_id=chat_id,
        rate_limit_seconds=rate_limit
    )


def create_discord_config(webhook_url: str, username: str = "Pump.fun Bot", rate_limit: float = 1.0) -> WebhookConfig:
    """Create Discord webhook configuration."""
    return WebhookConfig(
        webhook_url=webhook_url,
        webhook_type="discord", 
        discord_username=username,
        rate_limit_seconds=rate_limit
    )


def create_generic_config(webhook_url: str, rate_limit: float = 1.0) -> WebhookConfig:
    """Create generic webhook configuration."""
    return WebhookConfig(
        webhook_url=webhook_url,
        webhook_type="generic",
        rate_limit_seconds=rate_limit
    )


async def main():
    """Main function to run the webhook alert bot."""
    # Get configuration from environment
    helius_api_key = os.getenv("HELIUS_API_KEY")
    if not helius_api_key:
        print("❌ HELIUS_API_KEY not found in environment variables")
        print("Add your Helius API key to the .env file")
        return

    # Webhook configuration - customize based on your needs
    webhook_type = os.getenv("WEBHOOK_TYPE", "telegram")  # telegram, discord, or generic
    
    if webhook_type == "telegram":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("❌ For Telegram alerts, set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            print("Get bot token from @BotFather on Telegram")
            print("Get chat ID by messaging your bot and checking: https://api.telegram.org/bot<TOKEN>/getUpdates")
            return
            
        config = create_telegram_config(bot_token, chat_id)
        
    elif webhook_type == "discord":
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        
        if not webhook_url:
            print("❌ For Discord alerts, set DISCORD_WEBHOOK_URL")
            print("Create webhook in Discord: Server Settings > Integrations > Webhooks")
            return
            
        config = create_discord_config(webhook_url)
        
    else:
        webhook_url = os.getenv("WEBHOOK_URL")
        
        if not webhook_url:
            print("❌ For generic webhooks, set WEBHOOK_URL")
            return
            
        config = create_generic_config(webhook_url)

    # Initialize WebSocket endpoint
    wss_endpoint = f"wss://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    
    # Initialize and start the bot
    bot = WebhookAlertBot(wss_endpoint, config)
    
    print("🚀 Starting Pump.fun Webhook Alert Bot...")
    print(f"📡 Webhook Type: {webhook_type}")
    print(f"🔗 Endpoint: {config.webhook_url}")
    print("⏹️  Press Ctrl+C to stop and show statistics")
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        stats = bot.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   Tokens detected: {stats['tokens_detected']}")
        print(f"   Webhooks sent: {stats['webhooks_sent']}")
        print(f"   Webhook failures: {stats['webhook_failures']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Runtime: {stats['runtime_seconds']} seconds")


if __name__ == "__main__":
    asyncio.run(main())