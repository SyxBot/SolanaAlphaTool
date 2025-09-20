# Quick Start Guide - Replit Deployment

## 🚀 Deploy in 3 Steps

### Step 1: Add Required Secrets
In Replit Secrets tab (lock icon), add:

```
HELIUS_API_KEY = your_helius_api_key_here
```

### Step 2: Choose Webhook Type
Add ONE of these webhook configurations:

**For Telegram:**
```
WEBHOOK_TYPE = telegram
TELEGRAM_BOT_TOKEN = your_bot_token_from_botfather
TELEGRAM_CHAT_ID = your_chat_id_number
```

**For Discord:**
```
WEBHOOK_TYPE = discord
DISCORD_WEBHOOK_URL = your_discord_webhook_url
```

**For Custom Webhook:**
```
WEBHOOK_TYPE = generic
WEBHOOK_URL = your_webhook_endpoint_url
```

### Step 3: Run the Bot
Click the green "Run" button in Replit.

## ✅ Expected Output

```
🚀 Solana Signal Alert Bot - Replit Deployment
==================================================
✅ Python version: 3.11.10
✅ All dependencies are installed
✅ Environment configuration is valid
📡 Webhook type: telegram

🎉 Setup validation completed successfully!

🚀 Starting Solana Signal Alert Bot...
   This bot will run continuously and send webhook alerts for new pump.fun tokens
   Press Ctrl+C to stop and view statistics

⚠️  NOTE: This monitors blockchain data in real-time.
   Webhook alerts will be sent when tokens are detected.

==================================================
🚀 Starting Pump.fun Webhook Alert Bot...
📡 Webhook Type: telegram
🔗 Endpoint: https://api.telegram.org/bot123456.../sendMessage
⏹️  Press Ctrl+C to stop and show statistics

2025-07-12 23:45:00 - INFO - Starting Pump.fun Webhook Alert Bot
2025-07-12 23:45:00 - INFO - WebSocket connected to Helius endpoint
2025-07-12 23:45:00 - INFO - Listening for pump.fun token creations...

# When tokens are detected:
2025-07-12 23:45:30 - INFO - 🎯 Token detected: DogeCoin2.0 (DOGE2)
2025-07-12 23:45:30 - INFO - ✅ Webhook sent successfully for DogeCoin2.0
```

## 🔧 Troubleshooting

**Bot won't start:**
- Check Secrets tab has HELIUS_API_KEY
- Verify webhook configuration
- Check console for error messages

**No alerts received:**
- Test with: `python test_webhook.py`
- Verify webhook URL and credentials
- Check bot is detecting tokens in console

**Quick test commands:**
```bash
python test_webhook.py    # Test webhook delivery
python test_monitor.py    # Test token detection
python setup_webhook.py  # Interactive setup
```

## 📱 Webhook Examples

**Telegram Alert:**
```
🚀 NEW PUMP.FUN TOKEN LAUNCH

📛 Name: DogeCoin2.0
🏷️ Symbol: DOGE2
🆔 Mint: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
👤 Creator: 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM
⏰ Launch Time: 23:45:30 UTC

🔗 Links:
• View on Pump.fun
• Transaction on Solscan
```

**Discord Alert:**
Rich embed with structured fields and clickable links.

**JSON Webhook:**
Complete token data in structured JSON format.

## ⚡ Production Tips

- Use Replit Core for 24/7 uptime
- Enable "Always On" feature  
- Set RATE_LIMIT_SECONDS=2.0 for webhook rate limiting
- Monitor console logs for performance

The bot runs continuously and sends real-time alerts for every new pump.fun token launch!