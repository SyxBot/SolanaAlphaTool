# Node.js Crypto Signal Agent - Replit Deployment Guide

## Quick Setup for Existing Codebase

### 1. Environment Configuration

Copy `.env.example` to `.env` and set your values:

```bash
# Memory API Configuration
MEMORY_API_URL=https://your-memory-api.replit.app
MEMORY_API_KEY=your_memory_api_key_here

# Telegram Bot Configuration  
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# API Keys
BIRDEYE_API_KEY=your_birdeye_api_key_here
PUMP_FUN_API_KEY=your_pump_fun_api_key_here

# Server Configuration
PORT=5000
NODE_ENV=production
```

### 2. Memory API Integration

Replace your existing memory API calls with:

```javascript
// Import the Memory API class
import { MemoryAPI } from './src/config/memory-api.js';

// Initialize in your main file
const memoryAPI = new MemoryAPI();

// Send signals
await memoryAPI.sendSignal({
  symbol: 'SOL',
  action: 'BUY',
  price: 100.50,
  timestamp: Date.now()
});

// Send logs
await memoryAPI.sendLog({
  level: 'info',
  message: 'Signal processed',
  data: signalData
});
```

### 3. Telegram Alerts Integration

Replace your existing Telegram logic with:

```javascript
// Import the Telegram class
import { TelegramAlerts } from './src/config/telegram.js';

// Initialize
const telegram = new TelegramAlerts();

// Send formatted signal alerts
await telegram.sendAlert({
  type: 'signal',
  symbol: 'SOL',
  action: 'BUY',
  price: '100.50',
  change: '+5.2%',
  description: 'Strong momentum detected'
});

// Send error alerts
await telegram.sendError(error, 'Signal Processing');
```

### 4. Server Integration (Required for Replit)

Add this to your main file for keep-alive functionality:

```javascript
import { Server } from './src/server.js';

const server = new Server();
await server.start(); // Required for Replit deployment
```

### 5. Replace Your Signal Processing

In `src/index.js`, replace the `processSignals()` method with your existing logic:

```javascript
async processSignals() {
  // YOUR EXISTING BIRDEYE/PUMP.FUN FETCHING LOGIC HERE
  const signals = await yourExistingFetchFunction();
  
  for (const signal of signals) {
    // Send to Memory API
    await this.memoryAPI.sendSignal(signal);
    
    // Send Telegram alert
    await this.telegram.sendAlert(signal);
  }
}
```

## Deployment Steps

### 1. Set Environment Variables in Replit Secrets
- Go to Replit Secrets (lock icon in sidebar)
- Add each environment variable from your `.env` file

### 2. Run the Application
```bash
npm start
```

### 3. Keep It Alive
The server runs on port 5000 and includes:
- Health check endpoint: `/health`
- Status endpoint: `/status`
- Auto keep-alive pings every 5 minutes

### 4. Monitor
- Check logs in Replit console
- Access health endpoint at your Replit URL
- Telegram will receive test message on startup

## Deployment URL Structure
Your Replit app will be available at:
- `https://your-repl-name.your-username.repl.co`
- Health check: `https://your-repl-name.your-username.repl.co/health`

## Integration Points

### Memory API Endpoints Used:
- `POST /signals` - Send new signals
- `PUT /signals/:id` - Update signals  
- `GET /signals` - Fetch signals
- `POST /logs` - Send logs
- `GET /health` - Health check

### Error Handling:
- Automatic retries with exponential backoff
- Telegram error notifications
- Memory API connection recovery
- Graceful shutdown handling

## Production Notes:
- Server must run on port 5000 (only unfirewalled port)
- Uses `0.0.0.0` binding for external access
- Includes compression and security headers
- Automatic keep-alive prevents sleeping
