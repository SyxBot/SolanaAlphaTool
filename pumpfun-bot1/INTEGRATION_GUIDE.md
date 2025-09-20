# Integration Guide - Your Existing Node.js Agent

## 🟢 Successfully Deployed on Replit
Your Node.js crypto signal agent is running on port 5000 with:
- ✅ Express server (required for Replit)
- ✅ Telegram integration (test message sent successfully)
- ✅ Memory API configuration (ready for your endpoint)
- ✅ Auto keep-alive (prevents sleeping)

## Quick Integration Steps

### 1. Replace Signal Processing Logic
In `src/index.js`, replace the `processSignals()` method with your existing Birdeye/pump.fun logic:

```javascript
async processSignals() {
  // Replace this with your existing signal fetching logic
  const signals = await yourExistingBirdeyeFunction();
  // OR
  const signals = await yourExistingPumpFunFunction();
  
  for (const signal of signals) {
    // Send to Memory API
    await this.memoryAPI.sendSignal(signal);
    
    // Send Telegram alert  
    await this.telegram.sendAlert(signal);
  }
}
```

### 2. Set Your Memory API Endpoint
Update `.env` file:
```bash
MEMORY_API_URL=https://your-actual-memory-api.replit.app
MEMORY_API_KEY=your_actual_api_key
```

### 3. Update API Keys
In `.env`, add your real API keys:
```bash
BIRDEYE_API_KEY=your_actual_birdeye_key
PUMP_FUN_API_KEY=your_actual_pump_fun_key
```

## Memory API Integration

Your Memory API class supports:
```javascript
// Send signals
await memoryAPI.sendSignal({
  symbol: 'SOL',
  action: 'BUY',
  price: 100.50,
  timestamp: Date.now()
});

// Update signals
await memoryAPI.updateSignal(signalId, { status: 'completed' });

// Get signals with filters
const signals = await memoryAPI.getSignals({ symbol: 'SOL' });

// Send logs
await memoryAPI.sendLog({
  level: 'info',
  message: 'Signal processed',
  data: signalData
});
```

## Telegram Integration

Your Telegram class handles:
```javascript
// Formatted signal alerts
await telegram.sendAlert({
  type: 'signal',
  symbol: 'SOL',
  action: 'BUY',
  price: '100.50',
  change: '+5.2%',
  description: 'Strong momentum detected'
});

// Error notifications
await telegram.sendError(error, 'Signal Processing');

// Custom messages
await telegram.sendAlert('🚀 Custom message here');
```

## Server Endpoints (Auto-created)

Your app includes these endpoints:
- `GET /` - Status and uptime info
- `GET /health` - Health check for monitoring
- `GET /status` - Detailed system info
- `POST /webhook` - For external integrations

## Deployment Status

✅ **Running**: https://your-repl-name.your-username.repl.co
✅ **Health Check**: Accessible at /health endpoint
✅ **Keep-Alive**: Prevents Replit sleeping with 5-minute pings
✅ **Error Handling**: Automatic retries and Telegram error alerts
✅ **ES Modules**: Configured for modern JavaScript imports

## Next Steps

1. Replace the placeholder `processSignals()` with your existing logic
2. Update the Memory API URL to your actual endpoint
3. Add your real Birdeye/pump.fun API keys
4. Test with your actual signal sources
5. Monitor via Telegram alerts and health endpoints

The foundation is ready - just plug in your existing signal logic!