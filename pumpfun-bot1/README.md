# Solana Signal Alert Bot

A production-ready alert system for pump.fun token launches using real detection logic from the [pump-fun-bot repository](https://github.com/chainstacklabs/pump-fun-bot).

## Features

- **Real-time Detection**: Uses authentic WebSocket monitoring logic from the official pump.fun trading bot
- **Advanced Filtering**: Filter tokens by name, symbol, creator, length, and blocked words
- **Multiple Notification Channels**: Console, file logging, webhooks, and custom API endpoints
- **Rate Limiting**: Configurable rate limits to prevent spam
- **Statistics Tracking**: Monitor detection efficiency and performance
- **Production Ready**: Error handling, reconnection logic, and comprehensive logging

## Quick Start

### 1. Environment Setup
Ensure you have the required API keys in your environment:

```bash
# Required: Helius API key for Solana RPC access
HELIUS_API_KEY=your_helius_api_key_here
```

### 2. Configuration
Edit `alert_config.json` to customize your alert settings:

```json
{
  "name_contains": ["doge", "pepe", "moon"],
  "blocked_words": ["scam", "fake", "rug"],
  "notification_channels": ["console", "file"],
  "rate_limit_seconds": 2,
  "max_alerts_per_minute": 30
}
```

### 3. Run the Bot

```bash
# Basic monitoring with console output
python signal_alert_bot.py

# Test the underlying monitor
python test_monitor.py

# Test just the pump monitor
python pump_monitor.py
```

## Configuration Options

### Token Filters
- `name_contains`: Array of strings that must appear in token name
- `symbol_contains`: Array of strings that must appear in token symbol  
- `creator_addresses`: Array of creator addresses to monitor
- `min_name_length` / `max_name_length`: Length constraints
- `blocked_words`: Array of words that will filter out tokens

### Alert Settings
- `notification_channels`: `["console", "file", "webhook", "api"]`
- `alert_level`: `"info"`, `"warning"`, or `"critical"`
- `rate_limit_seconds`: Minimum seconds between alerts
- `max_alerts_per_minute`: Maximum alerts per minute

### Webhook Configuration
- `webhook_url`: URL to send webhook notifications
- `webhook_headers`: Custom headers for webhook requests

## Notification Channels

### Console Output
Real-time alerts printed to the terminal with emoji formatting.

### File Logging
Structured logging to `token_alerts.log` with configurable log levels.

### Webhook Notifications
POST requests to custom endpoints with JSON payload:

```json
{
  "alert_type": "pump_fun_token_detection",
  "data": {
    "timestamp": "2025-07-12T23:45:00",
    "alert_level": "info",
    "trigger_reason": "Name contains: [doge]",
    "token": {
      "name": "DogeCoin2.0",
      "symbol": "DOGE2",
      "mint": "...",
      "creator": "...",
      "transaction": "..."
    }
  }
}
```

## Technical Architecture

### Core Components

1. **`pump_monitor.py`**: WebSocket listener using real pump.fun detection logic
2. **`signal_alert_bot.py`**: Alert processing, filtering, and notification system
3. **`test_monitor.py`**: Test script for validation

### Detection Logic
- Uses `logsSubscribe` WebSocket method to monitor pump.fun program logs
- Parses binary instruction data with discriminator `8530921459188068891`
- Extracts token metadata from base64-encoded program data
- Calculates derived addresses for bonding curves and creator vaults

### Filtering Pipeline
1. **Blocked Words Check**: Immediately filter out unwanted tokens
2. **Length Validation**: Ensure token names meet length requirements
3. **Creator Filtering**: Optional whitelist of creator addresses
4. **Content Matching**: Check name/symbol against required keywords
5. **Rate Limiting**: Prevent notification spam

## Statistics and Monitoring

The bot tracks comprehensive statistics:
- Total tokens detected
- Alerts sent vs filtered out
- Rate limiting effectiveness
- Runtime and performance metrics

Access statistics with `bot.get_stats()` or view them when stopping the bot with Ctrl+C.

## Production Deployment

### Environment Variables
```bash
HELIUS_API_KEY=your_api_key
WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
LOG_LEVEL=INFO
```

### Systemd Service (Linux)
```ini
[Unit]
Description=Solana Signal Alert Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 signal_alert_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "signal_alert_bot.py"]
```

## Error Handling

The bot includes comprehensive error handling:
- **WebSocket Reconnection**: Automatic reconnection on connection loss
- **Rate Limiting**: Graceful handling of API rate limits
- **Webhook Failures**: Logging and continuation on webhook errors
- **Invalid Data**: Filtering and logging of malformed token data

## Security Considerations

- **API Keys**: Never log or expose API keys in output
- **Webhook Validation**: Validate webhook URLs and implement authentication
- **Rate Limiting**: Prevent abuse with configurable rate limits
- **Input Validation**: Sanitize all configuration inputs

## Dependencies

All dependencies are sourced from the official pump-fun-bot repository:
- `solana==0.36.6`: Solana blockchain interaction
- `websockets>=15.0`: WebSocket client for real-time data
- `aiohttp>=3.11.13`: HTTP client for webhooks
- `base58>=2.1.1`: Address encoding/decoding
- Additional dependencies for data parsing and async operations

## Support

For issues related to the underlying detection logic, refer to the original [pump-fun-bot repository](https://github.com/chainstacklabs/pump-fun-bot).

For Signal Alert Bot specific issues, check the logs and verify your configuration settings.