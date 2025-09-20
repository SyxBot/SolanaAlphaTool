# Replit Deployment Guide - Solana Signal Alert Bot

This guide covers deploying the Solana Signal Alert Bot on Replit for continuous monitoring of pump.fun token launches.

## Folder Structure

Your Replit project should have this structure:

```
/
├── .env                          # Secret keys and configuration
├── .replit                       # Replit configuration (auto-generated)
├── main.py                       # Main entry point for Replit
├── replit.md                     # Project documentation
├── README.md                     # General project info
├── pyproject.toml               # Python dependencies
├── uv.lock                      # Dependency lock file
│
├── pump_monitor.py              # Core token detection logic
├── webhook_alert_bot.py         # Main webhook alert system
├── signal_alert_bot.py          # Advanced alert system with filtering
├── setup_webhook.py             # Interactive webhook configuration
├── test_webhook.py              # Webhook testing utility
├── test_monitor.py              # Monitor testing utility
│
├── alert_config.json            # Alert filtering configuration
├── progress_log.md              # Development progress tracking
├── WEBHOOK_SETUP_GUIDE.md       # Complete webhook setup guide
├── REPLIT_DEPLOYMENT.md         # This deployment guide
├── MONITOR_ANALYSIS.md          # Technical analysis of detection logic
│
└── attached_assets/             # Original pump-fun-bot files
    ├── .env_1752363114863.example
    ├── LICENSE_1752363114863
    ├── MAINTAINERS_1752363114863.md
    ├── README_1752363114863.md
    ├── _1752363114863.gitignore
    └── pyproject_1752363114863.toml
```

## Entry Points

### Primary Entry Point: `main.py` (Recommended for Replit)
This validates the environment and automatically starts the webhook alert bot.

```bash
# Replit automatically runs this when you click "Run"
python main.py
```
**What it does:**
1. Validates Python version and dependencies
2. Checks required secrets in Replit
3. Automatically starts the webhook alert bot
4. Runs continuously until stopped with Ctrl+C

### Alternative Entry Points:
```bash
# Direct webhook bot (skip validation)
python run_bot.py

# Original webhook bot (for debugging)
python webhook_alert_bot.py

# Test webhook delivery
python test_webhook.py

# Test token detection  
python test_monitor.py

# Interactive webhook setup
python setup_webhook.py
```

## Secrets Configuration

### Required Secrets (Add in Replit Secrets tab)

1. **HELIUS_API_KEY** (Required)
   - Value: Your Helius API key for Solana RPC access
   - Get from: https://www.helius.dev/
   - Used for: WebSocket connection to Solana blockchain

2. **Choose ONE webhook type:**

#### Option A: Telegram Bot
   - **WEBHOOK_TYPE**: `telegram`
   - **TELEGRAM_BOT_TOKEN**: Your bot token from @BotFather
   - **TELEGRAM_CHAT_ID**: Your chat ID (number)

#### Option B: Discord Webhook
   - **WEBHOOK_TYPE**: `discord`
   - **DISCORD_WEBHOOK_URL**: Your Discord webhook URL

#### Option C: Generic Webhook
   - **WEBHOOK_TYPE**: `generic`
   - **WEBHOOK_URL**: Your custom webhook endpoint

### Optional Secrets
   - **RATE_LIMIT_SECONDS**: `1.0` (minimum seconds between alerts)
   - **LOG_LEVEL**: `INFO` (logging verbosity)

### How to Add Secrets in Replit

1. Click the "Secrets" tab in the left sidebar (lock icon)
2. Click "New Secret"
3. Enter the secret name (e.g., `HELIUS_API_KEY`)
4. Enter the secret value
5. Click "Add Secret"
6. Repeat for each required secret

**Important**: Never put real API keys in `.env` file or your code. Only use Replit Secrets.

## Continuous Execution

### How the Bot Runs

The bot runs **continuously** with these characteristics:

1. **WebSocket Connection**: Maintains persistent connection to Solana RPC
2. **Event-Driven**: Responds to real-time token creation events
3. **No Sleep/Polling**: Uses WebSocket events, not periodic checking
4. **Auto-Reconnect**: Handles connection drops automatically
5. **Graceful Shutdown**: Stops cleanly with Ctrl+C

### Runtime Behavior

```python
# The bot runs in an infinite loop like this:
async def main():
    while True:  # Automatic in WebSocket listener
        # Wait for token creation event
        # Parse token data
        # Send webhook alert
        # Continue listening...
```

### Replit-Specific Considerations

- **Always On**: Replit keeps the bot running continuously
- **Memory Management**: Bot handles long-running sessions efficiently
- **Automatic Restart**: Replit restarts if the process crashes
- **Console Output**: View real-time logs in the Replit console

## Running the Bot

### Method 1: Click "Run" Button (Recommended)
1. Open your Replit project
2. Ensure secrets are configured in the Secrets tab
3. Click the green "Run" button
4. The bot will automatically:
   - Validate dependencies and environment
   - Start monitoring pump.fun tokens
   - Send webhook alerts when tokens are detected
   - Run continuously until stopped

### Method 2: Shell Commands
```bash
# In the Replit shell tab:
python main.py          # Full validation + start bot
python run_bot.py       # Direct start (skip validation)
python webhook_alert_bot.py  # Original bot file
```

### Method 3: Interactive Setup
```bash
# If you need to configure webhooks:
python setup_webhook.py

# Then run the bot:
python main.py
```

### Stopping the Bot
- Press `Ctrl+C` in the console to stop
- The bot will show final statistics
- Replit will automatically restart if needed

## Expected Console Output

When running successfully, you'll see:

```
🚀 Starting Pump.fun Webhook Alert Bot...
📡 Webhook Type: telegram
🔗 Endpoint: https://api.telegram.org/bot123456789:ABC.../sendMessage
⏹️  Press Ctrl+C to stop and show statistics

2025-07-12 23:45:00 - INFO - Starting Pump.fun Webhook Alert Bot
2025-07-12 23:45:00 - INFO - WebSocket connected to Helius endpoint
2025-07-12 23:45:00 - INFO - Listening for pump.fun token creations...

# When tokens are detected:
2025-07-12 23:45:30 - INFO - 🎯 Token detected: DogeCoin2.0 (DOGE2)
2025-07-12 23:45:30 - INFO -    Mint: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
2025-07-12 23:45:30 - INFO -    Creator: 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM
2025-07-12 23:45:30 - INFO - ✅ Webhook sent successfully for DogeCoin2.0
```

## Testing Your Deployment

### 1. Test Webhook Configuration
```bash
python test_webhook.py
```
Expected output:
```
🧪 Pump.fun Webhook Test Suite
📱 Telegram message format: [formatted message]
💬 Discord embed format: [structured fields]
🌐 Generic JSON format: [JSON payload]
✅ Webhook test successful!
```

### 2. Test Token Detection
```bash
python test_monitor.py
```
This connects to live Solana data and should detect real tokens within seconds.

### 3. Validate Environment
```bash
python main.py
```
Should start without errors if all secrets are configured.

## Troubleshooting

### Common Issues

**Bot won't start:**
- Check that `HELIUS_API_KEY` is set in Secrets
- Verify webhook configuration (WEBHOOK_TYPE and related secrets)
- Check console for specific error messages

**No token alerts:**
- Verify Helius API key is valid and has RPC access
- Check webhook delivery with `python test_webhook.py`
- Monitor console logs for WebSocket connection status

**Webhook failures:**
- Verify webhook URL and credentials
- Test with `python test_webhook.py`
- Check rate limiting settings

**Memory/Performance:**
- The bot is designed for 24/7 operation
- WebSocket connections are efficient
- Monitor Replit resource usage

### Debug Commands

```bash
# Check environment configuration
python -c "import os; print('HELIUS_API_KEY:', 'SET' if os.getenv('HELIUS_API_KEY') else 'MISSING')"

# Test webhook formatting only
python test_webhook.py

# Test real-time detection
python test_monitor.py

# Interactive setup
python setup_webhook.py
```

## Production Deployment

### Recommended Settings for 24/7 Operation

1. **Replit Plan**: Use Replit Core or Teams for guaranteed uptime
2. **Always On**: Enable "Always On" feature for continuous operation
3. **Monitoring**: Check console logs periodically
4. **Rate Limits**: Set `RATE_LIMIT_SECONDS=2.0` to avoid overwhelming webhooks

### Security Best Practices

1. **Never commit secrets** to your repository
2. **Use Replit Secrets** for all API keys and tokens
3. **Monitor webhook URLs** for unauthorized access
4. **Regularly rotate API keys** for security

### Expected Resource Usage

- **CPU**: Low (event-driven, not polling)
- **Memory**: ~50-100MB for continuous operation
- **Network**: WebSocket connection + HTTP webhooks
- **Storage**: Minimal (logs only)

## Next Steps After Deployment

1. **Monitor Performance**: Check console logs for successful detections
2. **Verify Alerts**: Ensure webhook messages arrive as expected
3. **Adjust Settings**: Modify rate limits or filters in `alert_config.json`
4. **Scale Up**: Add multiple webhook endpoints if needed

The bot will run continuously, detecting real pump.fun token launches and sending immediate webhook alerts with authentic blockchain data.