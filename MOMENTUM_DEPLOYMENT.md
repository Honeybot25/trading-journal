# Momentum Scanner Deployment
# Deployed: 2026-02-26 06:14 PST for market open

## Status: ✅ DEPLOYED

### Components
1. **momentum_scanner.py** - Main scanner with Alpaca integration
2. **alert_system.py** - Discord alerts and Mission Control logging
3. **signals.db** - SQLite database for signals and trade tracking

### Configuration
- **Tickers:** NVDA, SPY, QQQ, TSLA
- **Timeframe:** 5-minute candles
- **Indicators:**
  - Volume spike >150% of 20-period average
  - Price breakout above 20-period high
  - RSI between 50-70 (strong but not overbought)
  - MACD bullish crossover
- **Risk Management:**
  - Max 2% account risk per trade
  - Stop loss: -3%
  - Take profit: +6% (2:1 risk/reward)
  - Max 4 concurrent positions

### Alerts
- Discord webhook: #trading-alerts channel
- Mission Control dashboard logging
- Real-time signal notifications

### Paper Trading
- Account: Alpaca Paper
- Status: Connected (requires valid API keys for orders)

### Usage
```bash
# Single scan
cd /Users/Honeybot/.openclaw/workspace/trading && source venv/bin/activate && python3 momentum_scanner.py --scan

# Continuous scanning (market hours)
python3 momentum_scanner.py --continuous --duration 390  # 6.5 hours

# With alerts
python3 alert_system.py --watch
```

### Files
- Scanner: `/Users/Honeybot/.openclaw/workspace/trading/momentum_scanner.py`
- Alerts: `/Users/Honeybot/.openclaw/workspace/trading/alert_system.py`
- DB: `/Users/Honeybot/.openclaw/workspace/trading/signals.db`
- Logs: `/Users/Honeybot/.openclaw/workspace/trading/logs/momentum_scanner.log`

### Next Steps
1. Set Alpaca API keys as env vars:
   - ALPACA_API_KEY
   - ALPACA_API_SECRET
2. Run continuous scanner during market hours
3. Monitor Discord #trading-alerts for signals
