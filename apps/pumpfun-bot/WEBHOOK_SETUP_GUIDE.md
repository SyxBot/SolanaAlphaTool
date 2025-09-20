# Webhook Alert Setup Guide

This guide shows how to set up real-time webhook alerts for pump.fun token launches using authentic detection logic from the pump-fun-bot repository.

## Quick Start

### 1. Configure Your Webhook

Choose one of the supported webhook types:

#### Telegram Setup
```bash
# Run the interactive setup
python setup_webhook.py

# Or manually configure in .env:
WEBHOOK_TYPE=telegram
TELEGRAM_BOT_TOKEN=123456789:ABCDefGhiJklmnopQRSTuvwxyz
TELEGRAM_CHAT_ID=987654321
```

**Getting Telegram credentials:**
1. Message @BotFather on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Add your bot to a channel or start a private chat
5. Send a message to your bot
6. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
7. Find your chat_id in the response

#### Discord Setup
```bash
# Configure in .env:
WEBHOOK_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop
```

**Getting Discord webhook URL:**
1. Go to your Discord server
2. Right-click the channel for alerts
3. Select 'Edit Channel' > 'Integrations'
4. Click 'Create Webhook'
5. Copy the webhook URL

#### Generic Webhook Setup
```bash
# Configure in .env:
WEBHOOK_TYPE=generic
WEBHOOK_URL=https://your-api-endpoint.com/pump-alerts
```

### 2. Run the Alert Bot

```bash
# Start real-time monitoring with webhook alerts
python webhook_alert_bot.py

# Test webhook delivery (without waiting for real tokens)
python test_webhook.py

# Test the underlying monitor
python test_monitor.py
```

## Real Token Data

When a token is detected, the webhook receives authentic data extracted from the pump.fun program:

### Telegram Alert Example
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

💎 Bonding Curve: CebN5uJmj6F7vG2jNjbbCs5DXksJgNpGPq4q9DGoPWd1
📊 Associated Curve: 5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1
```

### Discord Alert Example
Rich embed with color-coded sections, clickable links, and structured fields.

### Generic JSON Payload
```json
{
  "alert_type": "pump_fun_token_launch",
  "timestamp": "2025-07-12T23:45:30.123456",
  "token": {
    "name": "DogeCoin2.0",
    "symbol": "DOGE2", 
    "mint_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "creator_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "bonding_curve": "CebN5uJmj6F7vG2jNjbbCs5DXksJgNpGPq4q9DGoPWd1",
    "associated_bonding_curve": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAWWM",
    "metadata_uri": "https://pump.fun/meta/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU.json",
    "transaction_signature": "5J8YU7v4gW2KgjsXP1uFYEjyG3jKGN4w9L4z8YVyXzLmK3NJxP6Dx9TcRbGFfMsW8xYu7V6kN1mL2FhZq5P4wQ8T",
    "launch_time": "2025-07-12T23:45:30.123456",
    "pump_fun_url": "https://pump.fun/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    "solscan_url": "https://solscan.io/tx/5J8YU7v4gW2KgjsXP1uFYEjyG3jKGN4w9L4z8YVyXzLmK3NJxP6Dx9TcRbGFfMsW8xYu7V6kN1mL2FhZq5P4wQ8T"
  }
}
```

## Technical Architecture

### Detection Logic
The bot uses the same WebSocket monitoring logic as the official pump-fun-bot:

- **Program Address**: `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
- **Method**: `logsSubscribe` WebSocket subscription
- **Trigger**: `"Program log: Instruction: Create"`
- **Discriminator**: `8530921459188068891` (CREATE instruction)
- **Data Source**: Base64-encoded program instruction data

### Real-Time Process
1. **WebSocket Connection**: Connects to Helius/Solana RPC WebSocket
2. **Log Subscription**: Subscribes to pump.fun program logs
3. **Event Processing**: Parses binary instruction data in real-time
4. **Token Extraction**: Builds complete TokenInfo with mint, creator, curves
5. **Webhook Delivery**: Sends formatted alert via HTTP POST
6. **Error Handling**: Retry logic with exponential backoff

### Rate Limiting
- Configurable minimum seconds between alerts
- Exponential backoff on webhook failures
- Statistics tracking for monitoring

## Configuration Options

### Environment Variables
```bash
# Required
HELIUS_API_KEY=your_helius_api_key

# Webhook type (telegram, discord, generic)
WEBHOOK_TYPE=telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional
RATE_LIMIT_SECONDS=1.0
LOG_LEVEL=INFO
```

### Advanced Configuration
The `WebhookConfig` class supports additional options:
- Custom timeouts and retry attempts
- Rate limiting per webhook type
- Custom headers for authentication
- Different parsing modes for Telegram

## Production Deployment

### Systemd Service
```ini
[Unit]
Description=Pump.fun Webhook Alert Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 webhook_alert_bot.py
Restart=always
RestartSec=10
Environment=HELIUS_API_KEY=your_key
Environment=WEBHOOK_TYPE=telegram
Environment=TELEGRAM_BOT_TOKEN=your_token
Environment=TELEGRAM_CHAT_ID=your_chat_id

[Install]
WantedBy=multi-user.target
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "webhook_alert_bot.py"]
```

### Monitoring
The bot provides comprehensive statistics:
- Tokens detected vs webhooks sent
- Success/failure rates
- Runtime performance metrics
- Automatic reconnection on connection loss

## Security Considerations

- **API Keys**: Store in environment variables, never in code
- **Webhook URLs**: Validate URLs and implement authentication if needed
- **Rate Limiting**: Prevent abuse with configurable limits
- **Error Handling**: Graceful failure without exposing sensitive data

## Troubleshooting

### Common Issues

**Webhook not receiving alerts:**
1. Verify webhook URL and credentials
2. Check firewall/network connectivity
3. Run `python test_webhook.py` to validate setup
4. Check bot logs for error messages

**Missing tokens:**
1. Verify HELIUS_API_KEY is valid and has RPC access
2. Check WebSocket connection stability
3. Monitor bot statistics for detection counts

**Rate limiting:**
1. Adjust RATE_LIMIT_SECONDS if webhooks are too frequent
2. Check webhook service limits (Telegram: 30 msgs/second)

### Debug Commands
```bash
# Test webhook formatting
python test_webhook.py

# Test real token detection
python test_monitor.py

# Interactive webhook setup
python setup_webhook.py
```