# Options Discord Alerts

TypeScript-based Discord alert system for high-confidence options trading signals.

## Features

- ✅ **Confidence Filtering**: Only alerts with >75% confidence are sent
- ✅ **Duplicate Prevention**: 1-hour cooldown per symbol to avoid spam
- ✅ **Rich Discord Embeds**: Beautiful alerts with Greeks, volume data, and more
- ✅ **Mission Control Integration**: Direct links to dashboard for details
- ✅ **Test Mode**: Prefixes alerts with "TEST" for safe verification
- ✅ **TypeScript**: Full type safety and modern JavaScript features

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/Honeybot/.openclaw/workspace/trading
npm install
```

### 2. Configure Discord Webhook

Create a `.env` file:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
DISCORD_CHANNEL_NAME=trading-alerts
CONFIDENCE_THRESHOLD=75
DUPLICATE_COOLDOWN_MS=3600000
MISSION_CONTROL_URL=https://mission-control-lovat-rho.vercel.app
TEST_MODE=false
```

To get a webhook URL:
1. In Discord, go to Server Settings → Integrations → Webhooks
2. Create a webhook for the #trading-alerts channel
3. Copy the webhook URL

### 3. Send Test Alert

```bash
npx tsx test/send-test-alert.ts
```

Or with environment variable:

```bash
DISCORD_WEBHOOK_URL=<your_webhook> npx tsx test/send-test-alert.ts
```

## Usage in Code

### TypeScript/JavaScript

```typescript
import { DiscordOptionsAlerts, OptionsSignal } from './src/lib/discord-alerts';

const alerts = new DiscordOptionsAlerts({
  webhookUrl: 'https://discord.com/api/webhooks/...',
  confidenceThreshold: 75,
  duplicateCooldownMs: 3600000, // 1 hour
});

const signal: OptionsSignal = {
  symbol: 'NVDA',
  type: 'CALL',
  confidence: 85,
  expirationDate: '2026-03-15',
  strikePrice: 875.00,
  premium: 12.50,
  underlyingPrice: 860.25,
  unusualVolume: true,
  timestamp: new Date().toISOString(),
};

const result = await alerts.sendOptionsAlert(signal);
if (result.success) {
  console.log('Alert sent!');
} else if (result.filtered) {
  console.log('Filtered:', result.reason);
} else {
  console.error('Error:', result.error);
}
```

### Python Integration

Use the provided Python bridge:

```python
from options_alerts_bridge import send_options_alert

signal = {
    "symbol": "NVDA",
    "type": "CALL",
    "confidence": 85,
    "expirationDate": "2026-03-15",
    "strikePrice": 875.00,
    "premium": 12.50,
    "underlyingPrice": 860.25,
    "unusualVolume": True,
    "timestamp": datetime.now().isoformat(),
}

result = send_options_alert(signal)
print(result)  # {'success': True} or {'error': '...'}
```

## Alert Format

Alerts appear in Discord with this format:

```
🚨 OPTIONS ALERT: $NVDA
CALL | Confidence: 85% | Unusual Volume Detected

📋 Contract: NVDA CALL $875.00 Mar 15, 2026
🎯 Confidence: 85% ████████░░
🔥 Premium: $12.50 per contract
📈 Underlying: $860.25
⏱️ DTE: 14 days
📊 Volume: Unusual Activity 🔥

📐 Greeks: Delta: 0.520 | Gamma: 0.012 | Theta: -0.350 | Vega: 0.850 | IV: 42.0%

🔍 Signal Source: Unusual Volume + Momentum Breakout

[View in Mission Control] [Button]
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `webhookUrl` | required | Discord webhook URL |
| `confidenceThreshold` | 75 | Minimum confidence % to send alert |
| `duplicateCooldownMs` | 3600000 | Cooldown between same-symbol alerts (ms) |
| `missionControlUrl` | - | Base URL for Mission Control dashboard links |
| `testMode` | false | Prefix alerts with "TEST" |

## Architecture

```
src/lib/discord-alerts.ts
├── OptionsSignal interface
├── DiscordOptionsAlerts class
│   ├── sendOptionsAlert() - Main entry point
│   ├── sendTestAlert() - Test helper
│   ├── buildWebhookPayload() - Create Discord embed
│   └── AlertCache - Deduplication logic
└── Helper functions

Python Bridge (optional)
└── options_alerts_bridge.py - HTTP API wrapper
```

## Files

| File | Description |
|------|-------------|
| `src/lib/discord-alerts.ts` | Core alert module |
| `test/send-test-alert.ts` | Test script |
| `options_alerts_bridge.py` | Python integration |
| `package.json` | Node.js dependencies |
| `tsconfig.json` | TypeScript configuration |

## Integration with Existing System

The module integrates with the existing trading dashboard:

1. Python signal generators create signals
2. Call the TypeScript module via HTTP API or subprocess
3. Alerts sent to Discord #trading-alerts
4. Links back to Mission Control dashboard

## Testing

```bash
# Run all tests
npm test

# Send live test alert (requires webhook URL)
DISCORD_WEBHOOK_URL=<url> npx tsx test/send-test-alert.ts

# Type checking
npm run typecheck

# Build for production
npm run build
```

## Troubleshooting

### Webhook 404 Error
The webhook URL is invalid or deleted. Create a new webhook in Discord server settings.

### Duplicate Alerts
The cache is working correctly. Wait 1 hour or call `alerts.clearCache()` for testing.

### Low Confidence Alerts Not Sent
Alerts below 75% confidence are filtered. Adjust `confidenceThreshold` if needed.

## License

MIT
