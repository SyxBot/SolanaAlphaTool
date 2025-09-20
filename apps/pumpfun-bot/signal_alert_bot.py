#!/usr/bin/env python3
"""
Solana Signal Alert Bot
Production-ready alert system for pump.fun token launches using real detection logic.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
from dotenv import load_dotenv

from pump_monitor import PumpMonitor, TokenInfo

# Load environment variables
load_dotenv()

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    CONSOLE = "console"
    WEBHOOK = "webhook"
    FILE = "file"
    API = "api"

@dataclass
class AlertConfig:
    """Configuration for alert filtering and notification settings."""
    # Token filters
    name_contains: Optional[List[str]] = None
    symbol_contains: Optional[List[str]] = None
    creator_addresses: Optional[List[str]] = None
    min_name_length: int = 1
    max_name_length: int = 100
    blocked_words: Optional[List[str]] = None
    
    # Alert settings
    notification_channels: List[NotificationChannel] = None
    alert_level: AlertLevel = AlertLevel.INFO
    rate_limit_seconds: int = 1
    max_alerts_per_minute: int = 60
    
    # Webhook settings
    webhook_url: Optional[str] = None
    webhook_headers: Optional[Dict[str, str]] = None
    
    # File logging
    log_file: str = "token_alerts.log"
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = [NotificationChannel.CONSOLE]
        if self.name_contains:
            self.name_contains = [name.lower() for name in self.name_contains]
        if self.symbol_contains:
            self.symbol_contains = [symbol.lower() for symbol in self.symbol_contains]
        if self.blocked_words:
            self.blocked_words = [word.lower() for word in self.blocked_words]

@dataclass
class TokenAlert:
    """Structured alert data for a detected token."""
    timestamp: str
    token_info: TokenInfo
    alert_level: AlertLevel
    trigger_reason: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "alert_level": self.alert_level.value,
            "trigger_reason": self.trigger_reason,
            "token": {
                "name": self.token_info.name,
                "symbol": self.token_info.symbol,
                "mint": str(self.token_info.mint),
                "creator": str(self.token_info.creator),
                "bonding_curve": str(self.token_info.bonding_curve),
                "associated_curve": str(self.token_info.associated_bonding_curve),
                "metadata_uri": self.token_info.uri,
                "transaction": self.token_info.signature
            },
            "metadata": self.metadata or {}
        }

class SignalAlertBot:
    """Advanced Signal Alert Bot for pump.fun token launches."""
    
    def __init__(self, wss_endpoint: str, config: AlertConfig):
        """Initialize the alert bot.
        
        Args:
            wss_endpoint: WebSocket endpoint for Solana RPC
            config: Alert configuration settings
        """
        self.wss_endpoint = wss_endpoint
        self.config = config
        self.monitor = PumpMonitor(wss_endpoint)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.last_alert_time = 0
        self.alerts_this_minute = 0
        self.minute_start = time.time()
        
        # Statistics
        self.stats = {
            "total_tokens_detected": 0,
            "alerts_sent": 0,
            "filtered_out": 0,
            "rate_limited": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup file logging for alerts."""
        if NotificationChannel.FILE in self.config.notification_channels:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(file_handler)

    async def start(self):
        """Start the Signal Alert Bot."""
        self.logger.info("Starting Solana Signal Alert Bot")
        self.logger.info(f"Configuration: {self._get_config_summary()}")
        
        # Initialize HTTP session for webhooks
        if NotificationChannel.WEBHOOK in self.config.notification_channels:
            self.session = aiohttp.ClientSession()
        
        try:
            await self.monitor.listen_for_tokens(
                token_callback=self._handle_token_detection,
                match_string=None,  # We'll do filtering in _handle_token_detection
                creator_address=None
            )
        finally:
            if self.session:
                await self.session.close()

    def _get_config_summary(self) -> str:
        """Get a summary of the current configuration."""
        summary = []
        if self.config.name_contains:
            summary.append(f"Name filters: {self.config.name_contains}")
        if self.config.symbol_contains:
            summary.append(f"Symbol filters: {self.config.symbol_contains}")
        if self.config.creator_addresses:
            summary.append(f"Creator filters: {len(self.config.creator_addresses)} addresses")
        if self.config.blocked_words:
            summary.append(f"Blocked words: {self.config.blocked_words}")
        
        summary.append(f"Channels: {[ch.value for ch in self.config.notification_channels]}")
        summary.append(f"Rate limit: {self.config.max_alerts_per_minute}/min")
        
        return " | ".join(summary) if summary else "No filters active"

    async def _handle_token_detection(self, token_info: TokenInfo):
        """Handle a detected token and process alerts."""
        self.stats["total_tokens_detected"] += 1
        
        # Apply filters
        filter_result = self._apply_filters(token_info)
        if not filter_result["passes"]:
            self.stats["filtered_out"] += 1
            self.logger.debug(f"Token filtered out: {token_info.name} - {filter_result['reason']}")
            return
        
        # Check rate limits
        if not self._check_rate_limit():
            self.stats["rate_limited"] += 1
            self.logger.debug(f"Rate limited alert for: {token_info.name}")
            return
        
        # Create alert
        alert = TokenAlert(
            timestamp=datetime.now().isoformat(),
            token_info=token_info,
            alert_level=self.config.alert_level,
            trigger_reason=filter_result["trigger_reason"],
            metadata={
                "detection_time_ms": int(time.time() * 1000),
                "stats": self.stats.copy()
            }
        )
        
        # Send notifications
        await self._send_alert(alert)
        self.stats["alerts_sent"] += 1

    def _apply_filters(self, token_info: TokenInfo) -> Dict[str, Any]:
        """Apply all configured filters to a token."""
        name = token_info.name.lower()
        symbol = token_info.symbol.lower()
        
        # Check blocked words first
        if self.config.blocked_words:
            for blocked_word in self.config.blocked_words:
                if blocked_word in name or blocked_word in symbol:
                    return {
                        "passes": False,
                        "reason": f"Contains blocked word: {blocked_word}"
                    }
        
        # Check name length
        if len(token_info.name) < self.config.min_name_length:
            return {
                "passes": False,
                "reason": f"Name too short: {len(token_info.name)} < {self.config.min_name_length}"
            }
        
        if len(token_info.name) > self.config.max_name_length:
            return {
                "passes": False,
                "reason": f"Name too long: {len(token_info.name)} > {self.config.max_name_length}"
            }
        
        # Check creator filter
        if self.config.creator_addresses:
            if str(token_info.creator) not in self.config.creator_addresses:
                return {
                    "passes": False,
                    "reason": f"Creator not in whitelist: {token_info.creator}"
                }
        
        # Check name contains filter
        trigger_reasons = []
        if self.config.name_contains:
            name_match = any(filter_word in name for filter_word in self.config.name_contains)
            if name_match:
                matching_words = [word for word in self.config.name_contains if word in name]
                trigger_reasons.append(f"Name contains: {matching_words}")
            elif self.config.name_contains:  # If we have name filters, they must match
                return {
                    "passes": False,
                    "reason": f"Name does not contain required words: {self.config.name_contains}"
                }
        
        # Check symbol contains filter
        if self.config.symbol_contains:
            symbol_match = any(filter_word in symbol for filter_word in self.config.symbol_contains)
            if symbol_match:
                matching_words = [word for word in self.config.symbol_contains if word in symbol]
                trigger_reasons.append(f"Symbol contains: {matching_words}")
            elif self.config.symbol_contains:  # If we have symbol filters, they must match
                return {
                    "passes": False,
                    "reason": f"Symbol does not contain required words: {self.config.symbol_contains}"
                }
        
        # If no specific filters triggered, it's a general detection
        if not trigger_reasons:
            trigger_reasons.append("New token detected")
        
        return {
            "passes": True,
            "trigger_reason": " | ".join(trigger_reasons)
        }

    def _check_rate_limit(self) -> bool:
        """Check if we can send another alert based on rate limits."""
        current_time = time.time()
        
        # Reset minute counter if needed
        if current_time - self.minute_start >= 60:
            self.alerts_this_minute = 0
            self.minute_start = current_time
        
        # Check per-minute limit
        if self.alerts_this_minute >= self.config.max_alerts_per_minute:
            return False
        
        # Check minimum time between alerts
        if current_time - self.last_alert_time < self.config.rate_limit_seconds:
            return False
        
        self.last_alert_time = current_time
        self.alerts_this_minute += 1
        return True

    async def _send_alert(self, alert: TokenAlert):
        """Send alert through all configured notification channels."""
        for channel in self.config.notification_channels:
            try:
                if channel == NotificationChannel.CONSOLE:
                    await self._send_console_alert(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook_alert(alert)
                elif channel == NotificationChannel.FILE:
                    await self._send_file_alert(alert)
                elif channel == NotificationChannel.API:
                    await self._send_api_alert(alert)
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel.value}: {e}")

    async def _send_console_alert(self, alert: TokenAlert):
        """Send alert to console."""
        print(f"\n🚨 TOKEN ALERT - {alert.alert_level.value.upper()}")
        print(f"🎯 {alert.trigger_reason}")
        print(f"📛 Name: {alert.token_info.name}")
        print(f"🏷️  Symbol: {alert.token_info.symbol}")
        print(f"🆔 Mint: {alert.token_info.mint}")
        print(f"👤 Creator: {alert.token_info.creator}")
        print(f"🔗 Transaction: {alert.token_info.signature}")
        print(f"⏰ Time: {alert.timestamp}")
        print("=" * 60)

    async def _send_webhook_alert(self, alert: TokenAlert):
        """Send alert via webhook."""
        if not self.config.webhook_url or not self.session:
            return
        
        payload = {
            "alert_type": "pump_fun_token_detection",
            "data": alert.to_dict()
        }
        
        headers = self.config.webhook_headers or {"Content-Type": "application/json"}
        
        async with self.session.post(
            self.config.webhook_url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status >= 400:
                self.logger.warning(f"Webhook failed with status {response.status}")

    async def _send_file_alert(self, alert: TokenAlert):
        """Send alert to log file."""
        alert_msg = (
            f"ALERT: {alert.trigger_reason} | "
            f"Token: {alert.token_info.name} ({alert.token_info.symbol}) | "
            f"Mint: {alert.token_info.mint} | "
            f"Creator: {alert.token_info.creator} | "
            f"TX: {alert.token_info.signature}"
        )
        
        if alert.alert_level == AlertLevel.CRITICAL:
            self.logger.critical(alert_msg)
        elif alert.alert_level == AlertLevel.WARNING:
            self.logger.warning(alert_msg)
        else:
            self.logger.info(alert_msg)

    async def _send_api_alert(self, alert: TokenAlert):
        """Send alert via custom API endpoint."""
        # This would be implemented based on specific API requirements
        self.logger.info(f"API alert would be sent: {alert.token_info.name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current bot statistics."""
        runtime = datetime.now() - datetime.fromisoformat(self.stats["start_time"])
        
        return {
            **self.stats,
            "runtime_seconds": int(runtime.total_seconds()),
            "alerts_per_minute": self.stats["alerts_sent"] / max(runtime.total_seconds() / 60, 1),
            "filter_efficiency": (
                self.stats["filtered_out"] / max(self.stats["total_tokens_detected"], 1) * 100
            )
        }


def load_config_from_file(config_file: str = "alert_config.json") -> AlertConfig:
    """Load alert configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        # Convert notification channels from strings to enums
        if "notification_channels" in data:
            data["notification_channels"] = [
                NotificationChannel(ch) for ch in data["notification_channels"]
            ]
        
        # Convert alert level from string to enum
        if "alert_level" in data:
            data["alert_level"] = AlertLevel(data["alert_level"])
        
        return AlertConfig(**data)
    
    except FileNotFoundError:
        print(f"Config file {config_file} not found, using default configuration")
        return AlertConfig()
    except Exception as e:
        print(f"Error loading config: {e}, using default configuration")
        return AlertConfig()


async def main():
    """Main function to run the Signal Alert Bot."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load configuration
    config = load_config_from_file()
    
    # Get WebSocket endpoint from environment
    helius_api_key = os.getenv("HELIUS_API_KEY")
    if not helius_api_key:
        print("❌ HELIUS_API_KEY not found in environment variables")
        return

    wss_endpoint = f"wss://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    
    # Initialize and start the bot
    bot = SignalAlertBot(wss_endpoint, config)
    
    print("🚀 Starting Solana Signal Alert Bot...")
    print(f"📊 Configuration: {bot._get_config_summary()}")
    print("⏹️  Press Ctrl+C to stop and show statistics")
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        stats = bot.get_stats()
        print(f"\n📊 Final Statistics:")
        print(f"   Total tokens detected: {stats['total_tokens_detected']}")
        print(f"   Alerts sent: {stats['alerts_sent']}")
        print(f"   Filtered out: {stats['filtered_out']}")
        print(f"   Rate limited: {stats['rate_limited']}")
        print(f"   Runtime: {stats['runtime_seconds']} seconds")
        print(f"   Filter efficiency: {stats['filter_efficiency']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())