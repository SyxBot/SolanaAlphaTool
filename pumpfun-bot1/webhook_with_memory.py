"""
Enhanced Webhook Alert Bot with Memory Integration
Combines webhook alerts with shared memory reporting and comprehensive filtering.
"""

import asyncio
import sys
import time
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from solana.rpc.async_api import AsyncClient
from collections import deque

# Import the pump monitor and filtering components
from pump_monitor import PumpMonitor, TokenInfo
from should_alert import should_alert, should_alert_with_details
from memory_reporter import enhanced_token_handler_with_memory
from rollingNew import get_stats
from filters.pumpNew import passes_hard_filters, launch_score, track_launch_seen, track_alert_sent
from utils import (
    log_event, 
    get_config, 
    get_rpc_endpoints,
    validate_environment,
    get_bot_info,
    format_token_data,
    ping_memory_server
)

class EnhancedWebhookAlertBot:
    """
    Enhanced webhook alert bot with memory integration and comprehensive filtering.
    """
    
    def __init__(self):
        """Initialize the enhanced webhook alert bot."""
        self.stats = {
            'tokens_detected': 0,
            'tokens_alerted': 0,
            'tokens_filtered': 0,
            'memory_reports_sent': 0,
            'memory_reports_failed': 0,
            'start_time': datetime.now(timezone.utc)
        }
        
        self.client = None
        self.webhook_config = None
        self.monitor = None
        
        # Per-mint cooldown tracking
        self.last_alert = {}  # mint -> {'size_usd': float, 'buyers': int, 'timestamp': float}
        
        # Global rate limiting (token bucket: 6 alerts per 10 minutes)
        self.alert_bucket = deque()
        self.bucket_capacity = 6
        self.bucket_window = 600  # 10 minutes
        
        # Load denylist
        self.denylist = self._load_denylist()
        
        # Load bot configuration
        bot_info = get_bot_info()
        log_event(f"Enhanced Webhook Bot {bot_info['identifier']} v{bot_info['version']} initializing")
    
    async def initialize(self):
        """Initialize RPC client and validate configuration."""
        try:
            # Validate environment
            if not validate_environment():
                log_event("Environment validation failed", 'error')
                return False
            
            # Initialize Solana RPC client
            rpc_endpoints = get_rpc_endpoints()
            self.client = AsyncClient(rpc_endpoints['http'])
            
            # Initialize pump monitor
            self.monitor = PumpMonitor(rpc_endpoints['ws'])
            
            # Test RPC connection
            try:
                health = await self.client.get_health()
                log_event(f"RPC client initialized: {rpc_endpoints['http']}")
            except Exception as e:
                log_event(f"RPC connection test failed: {e}", 'warning')
            
            # Test memory server connection
            if ping_memory_server():
                log_event("Memory server connection verified")
            else:
                log_event("Memory server unreachable - continuing without memory features", 'warning')
            
            # Load webhook configuration
            self.webhook_config = self._load_webhook_config()
            if self.webhook_config:
                log_event(f"Webhook configured: {self.webhook_config['type']}")
            else:
                log_event("No webhook configured - alerts will be logged only", 'warning')
            
            return True
            
        except Exception as e:
            log_event(f"Initialization failed: {e}", 'error')
            return False
    
    def _load_webhook_config(self) -> Optional[Dict[str, Any]]:
        """Load webhook configuration from environment."""
        webhook_type = get_config('WEBHOOK_TYPE')
        
        if not webhook_type:
            return None
        
        config = {'type': webhook_type}
        
        if webhook_type == 'telegram':
            bot_token = get_config('TELEGRAM_BOT_TOKEN')
            chat_id = get_config('TELEGRAM_CHAT_ID')
            if bot_token and chat_id:
                config.update({
                    'bot_token': bot_token,
                    'chat_id': chat_id,
                    'url': f"https://api.telegram.org/bot{bot_token}/sendMessage"
                })
                return config
                
        elif webhook_type == 'discord':
            webhook_url = get_config('DISCORD_WEBHOOK_URL')
            if webhook_url:
                config['url'] = webhook_url
                return config
                
        elif webhook_type == 'generic':
            webhook_url = get_config('WEBHOOK_URL')
            if webhook_url:
                config['url'] = webhook_url
                return config
        
        log_event(f"Incomplete webhook configuration for type: {webhook_type}", 'warning')
        return None
    
    async def enhanced_token_handler(self, token_info: TokenInfo):
        """
        Enhanced token handler with filtering, alerting, and memory integration.
        
        Args:
            token_info: Token information from pump monitor
        """
        try:
            self.stats['tokens_detected'] += 1
            track_launch_seen()  # Track launch for auto-tighten feature
            
            # Convert TokenInfo to metadata dict for should_alert
            token_metadata = {
                'symbol': token_info.symbol,
                'creator': str(token_info.creator),
                'mint': str(token_info.mint),
                'name': token_info.name
            }
            
            log_event(f"Processing token: {token_info.name} ({token_info.symbol})")
            
            # Check denylist first
            if self._is_denylisted(str(token_info.creator), str(token_info.mint)):
                log_event(f"FILTERED: {token_info.name} - Denylisted creator/mint", 'warning')
                return
            
            # Get detailed filtering results
            if self.client:
                filter_details = await should_alert_with_details(token_metadata, self.client)
                should_alert_result = filter_details.get('should_alert', False)
                
                # CRITICAL: Block alerts when pump.fun API is broken (530 errors = incomplete data)
                liquidity = filter_details.get('liquidity_sol', 0)
                if liquidity == 0:
                    log_event(f"BLOCKED: {token_info.name} - Pump.fun API error or zero liquidity", 'warning')
                    return
            else:
                log_event("No Solana client available - skipping token", 'warning')
                return
                
            # Apply rolling stats filtering if initial filters pass
            rolling_stats_pass = False
            rolling_score = 0
            stats = None
            if should_alert_result:
                try:
                    stats = get_stats(str(token_info.mint))
                    if stats:
                        passes, reasons = passes_hard_filters(stats)
                        score = launch_score(stats)
                        if passes and score >= 70:
                            # Check per-mint cooldown
                            if self._check_mint_cooldown(str(token_info.mint), stats):
                                # Check global rate limit
                                if self._check_global_rate_limit():
                                    rolling_stats_pass = True
                                    rolling_score = score
                                    log_event(f"Rolling stats passed for {token_info.symbol}: score {rolling_score}")
                                else:
                                    log_event(f"Rolling stats failed for {token_info.symbol}: global rate limit exceeded")
                            else:
                                log_event(f"Rolling stats failed for {token_info.symbol}: cooldown active")
                        else:
                            rejection_info = f"score {score}, filters: {', '.join(reasons) if reasons else 'passed'}"
                            log_event(f"Rolling stats failed for {token_info.symbol}: {rejection_info}")
                    else:
                        log_event(f"Rolling stats failed for {token_info.symbol}: no data available")
                except Exception as e:
                    log_event(f"Rolling stats error for {token_info.symbol}: {e}", 'warning')
            
            # Final alert decision: both filters must pass
            final_alert_decision = should_alert_result and rolling_stats_pass
                
            # Log the decision
            if final_alert_decision:
                self.stats['tokens_alerted'] += 1
                track_alert_sent()  # Track alert for auto-tighten feature
                if stats:
                    self._update_mint_alert_record(str(token_info.mint), stats)  # Update cooldown tracking
                self._add_to_bucket()  # Add to rate limit bucket
                log_event(f"ALERT APPROVED: {token_info.name} ({token_info.symbol}) - Score: {rolling_score}")
                
                # Send webhook alert if configured
                if self.webhook_config:
                    await self._send_webhook_alert(token_info)
                else:
                    log_event("No webhook configured - alert logged only", 'info')
            else:
                self.stats['tokens_filtered'] += 1
                if should_alert_result and not rolling_stats_pass:
                    log_event(f"FILTERED: {token_info.name} - Failed rolling stats filter (score: {rolling_score})", 'warning')
                else:
                    reasons = ', '.join(filter_details.get('rejection_reasons', ['Unknown']))
                    log_event(f"FILTERED: {token_info.name} - {reasons}", 'warning')
                
            # Report to memory regardless of alert decision
            try:
                token_data = format_token_data(token_info, final_alert_decision, filter_details)
                
                # Use the memory reporter function
                from memory_reporter import report_token_to_memory
                success = report_token_to_memory(token_data)
                
                if success:
                    self.stats['memory_reports_sent'] += 1
                    log_event(f"Memory report sent for {token_info.symbol}", 'debug')
                else:
                    self.stats['memory_reports_failed'] += 1
                    log_event(f"Memory report failed for {token_info.symbol}", 'warning')
                    
            except Exception as memory_error:
                self.stats['memory_reports_failed'] += 1
                log_event(f"Memory reporting error for {token_info.symbol}: {memory_error}", 'error')
                
        except Exception as main_error:
            log_event(f"Token processing error for {token_info.name}: {main_error}", 'error')
    
    def _check_mint_cooldown(self, mint: str, stats: dict) -> bool:
        """
        Check if mint passes cooldown requirements.
        
        Args:
            mint: Token mint address
            stats: Current token stats
            
        Returns:
            bool: True if alert should be sent (no cooldown or escalation threshold met)
        """
        now = time.time()
        
        # If no previous alert for this mint, allow
        if mint not in self.last_alert:
            return True
        
        last_record = self.last_alert[mint]
        time_since_last = now - last_record['timestamp']
        
        # 15 minute cooldown
        if time_since_last < 900:  # 15 minutes in seconds
            # Check escalation conditions
            current_size = stats.get('net_buy_usd', 0)
            current_buyers = stats.get('unique_buyers', 0)
            
            # Allow if net_buy_usd >= 2x last alerted value
            if current_size >= last_record['size_usd'] * 2:
                log_event(f"Mint {mint} escalation: size {current_size} >= 2x {last_record['size_usd']}")
                return True
            
            # Allow if unique_buyers increased by 40%
            if current_buyers >= last_record['buyers'] * 1.4:
                log_event(f"Mint {mint} escalation: buyers {current_buyers} >= 1.4x {last_record['buyers']}")
                return True
            
            # Otherwise, suppress during cooldown
            return False
        
        # Cooldown expired, allow alert
        return True
    
    def _update_mint_alert_record(self, mint: str, stats: dict):
        """Update the last alert record for a mint."""
        if stats:
            self.last_alert[mint] = {
                'size_usd': stats.get('net_buy_usd', 0),
                'buyers': stats.get('unique_buyers', 0),
                'timestamp': time.time()
            }
    
    def _load_denylist(self) -> dict:
        """Load the denylist from JSON file."""
        try:
            denylist_path = os.path.join('filters', 'denylist.json')
            if os.path.exists(denylist_path):
                with open(denylist_path, 'r') as f:
                    return json.load(f)
            return {"creators": [], "mints": []}
        except Exception as e:
            log_event(f"Failed to load denylist: {e}", 'warning')
            return {"creators": [], "mints": []}
    
    def _is_denylisted(self, creator: str, mint: str) -> bool:
        """Check if creator or mint is in the denylist."""
        return (creator in self.denylist.get("creators", []) or 
                mint in self.denylist.get("mints", []))
    
    def _check_global_rate_limit(self) -> bool:
        """
        Check global rate limiting using token bucket algorithm.
        Allows 6 alerts per 10 minutes.
        """
        now = time.time()
        
        # Remove old entries from bucket
        while self.alert_bucket and now - self.alert_bucket[0] > self.bucket_window:
            self.alert_bucket.popleft()
        
        # Check if bucket has capacity
        return len(self.alert_bucket) < self.bucket_capacity
    
    def _add_to_bucket(self):
        """Add current timestamp to rate limit bucket."""
        self.alert_bucket.append(time.time())
    
    async def _send_webhook_alert(self, token_info: TokenInfo):
        """Send webhook alert for approved token."""
        try:
            import aiohttp
            
            # Additional validation before sending alert
            if not token_info.mint or not token_info.name or not token_info.symbol:
                log_event(f"BLOCKED: Incomplete token data - mint: {token_info.mint}, name: {token_info.name}, symbol: {token_info.symbol}", 'error')
                return
            
            # Format the alert message
            message = self._format_alert_message(token_info)
            
            if self.webhook_config['type'] == 'telegram':
                payload = {
                    'chat_id': self.webhook_config['chat_id'],
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True
                }
            else:
                # Discord or generic webhook
                payload = {
                    'content': message
                }
            
            # Send the webhook
            timeout = get_config('DEFAULT_REQUEST_TIMEOUT', 10, int)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_config['url'],
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        log_event(f"Webhook sent successfully for {token_info.name}")
                    else:
                        log_event(f"Webhook failed: {response.status} - {await response.text()}", 'error')
                        
        except Exception as e:
            log_event(f"Webhook error for {token_info.name}: {e}", 'error')
    
    def _format_alert_message(self, token_info: TokenInfo) -> str:
        """Format alert message for webhook."""
        # Validate mint address before creating URLs
        mint_str = str(token_info.mint)
        if not mint_str or len(mint_str) < 30:  # Basic mint address validation
            log_event(f"Invalid mint address for {token_info.name}: {mint_str}", 'error')
            raise ValueError(f"Invalid mint address: {mint_str}")
            
        pump_url = f"https://pump.fun/{mint_str}"
        dexscreener_url = f"https://dexscreener.com/solana/{mint_str}"
        
        if self.webhook_config['type'] == 'telegram':
            return f"""🚀 *New Token Alert*

📛 **{token_info.name}** `({token_info.symbol})`
🏭 **Creator:** `{token_info.creator}`
🪙 **Mint:** `{token_info.mint}`
⏰ **Time:** {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}

🔗 [View on Pump.fun]({pump_url})
📊 [View on DexScreener]({dexscreener_url})

✅ *Passed all quality filters*"""
        else:
            return f"""🚀 New Token Alert

📛 {token_info.name} ({token_info.symbol})
🏭 Creator: {token_info.creator}
🪙 Mint: {token_info.mint}
⏰ Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}

🔗 Pump.fun: {pump_url}
📊 DexScreener: {dexscreener_url}

✅ Passed all quality filters"""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bot statistics."""
        runtime = datetime.now(timezone.utc) - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_minutes': runtime.total_seconds() / 60,
            'tokens_per_minute': self.stats['tokens_detected'] / max(runtime.total_seconds() / 60, 1),
            'filter_rate': (self.stats['tokens_filtered'] / max(self.stats['tokens_detected'], 1)) * 100,
            'alert_rate': (self.stats['tokens_alerted'] / max(self.stats['tokens_detected'], 1)) * 100,
            'memory_success_rate': (self.stats['memory_reports_sent'] / max(
                self.stats['memory_reports_sent'] + self.stats['memory_reports_failed'], 1
            )) * 100
        }
    
    def print_statistics(self):
        """Print formatted statistics."""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("🤖 ENHANCED WEBHOOK BOT STATISTICS")
        print("="*60)
        print(f"⏰ Runtime: {stats['runtime_minutes']:.1f} minutes")
        print(f"🔍 Tokens Detected: {stats['tokens_detected']}")
        print(f"🚀 Tokens Alerted: {stats['tokens_alerted']}")
        print(f"🛡️  Tokens Filtered: {stats['tokens_filtered']}")
        print(f"📈 Detection Rate: {stats['tokens_per_minute']:.1f} tokens/min")
        print(f"✅ Alert Rate: {stats['alert_rate']:.1f}%")
        print(f"🛡️  Filter Rate: {stats['filter_rate']:.1f}%")
        print("\n📊 Memory Integration:")
        print(f"✅ Reports Sent: {stats['memory_reports_sent']}")
        print(f"❌ Reports Failed: {stats['memory_reports_failed']}")
        print(f"📈 Success Rate: {stats['memory_success_rate']:.1f}%")
        print("="*60)


async def main():
    """Main entry point for enhanced webhook bot."""
    try:
        log_event("Enhanced Webhook Alert Bot starting")
        
        # Create and initialize bot
        bot = EnhancedWebhookAlertBot()
        
        if not await bot.initialize():
            log_event("Bot initialization failed", 'error')
            sys.exit(1)
        
        log_event("Bot initialization completed successfully")
        print("\n🚀 Enhanced Webhook Alert Bot - Ready")
        print("="*50)
        print("🔍 Monitoring pump.fun for new tokens")
        print("🛡️  Applying comprehensive quality filters")
        print("📊 Reporting to shared memory system")
        print("🚨 Sending webhook alerts for approved tokens")
        print("⏹️  Press Ctrl+C to stop and view statistics")
        print("="*50)
        
        # Start monitoring with enhanced handler
        await bot.monitor.listen_for_tokens(bot.enhanced_token_handler)
        
    except KeyboardInterrupt:
        log_event("Bot stopped by user")
        if 'bot' in locals():
            bot.print_statistics()
        print("\n👋 Enhanced Webhook Alert Bot stopped")
        
    except Exception as e:
        log_event(f"Unexpected error: {e}", 'error')
        sys.exit(1)


if __name__ == "__main__":
    # Run the enhanced webhook bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Enhanced Webhook Alert Bot stopped")