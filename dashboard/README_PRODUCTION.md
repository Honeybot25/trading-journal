# GEX Terminal Pro - Production Deployment Documentation

## Overview

The GEX Terminal Pro is a production-ready Bloomberg-style Gamma Exposure dashboard deployed on Vercel with advanced signal tracking capabilities.

**Live URL:** `https://gex-terminal-pro.vercel.app` (will be provided after deployment)

## Features

### 1. Vercel Serverless Deployment
- **Entry Point:** `wsgi.py` - WSGI wrapper for Dash app
- **Configuration:** `vercel.json` - Serverless function settings
- **Auto-scaling:** Handles traffic spikes automatically
- **Global CDN:** Fast access from anywhere

### 2. Auto-Refresh System
- **Update Interval:** 60 seconds during market hours
- **Countdown Timer:** Shows seconds until next refresh
- **Manual Refresh:** Button to force immediate update
- **Rate Limiting:** Respects Polygon.io 5 req/min limit

### 3. BUY CALL / BUY PUT Signal System

#### Signal Generation Logic

**🟢 BUY CALL Generated When:**
1. Price near positive GEX strike (within 2%)
2. RSI < 35 (oversold condition)
3. Bullish trend detected (5 SMA > 20 SMA)

**🔴 BUY PUT Generated When:**
1. Price near negative GEX strike (within 2%)
2. RSI > 65 (overbought condition)
3. Bearish trend detected (5 SMA < 20 SMA)

#### Signal Components
- **Entry Price:** Current spot price at signal time
- **Stop Loss:** 2% below entry (CALL) / above entry (PUT)
- **Take Profit:** Based on expected move calculation
- **Confidence Score:** 0-100% based on conditions met
- **Expected Move:** Calculated from GEX magnitude
- **Condition Breakdown:** Shows which conditions are met

### 4. Signal Tracking Database (SQLite)

#### Database Schema

**signals table:**
```sql
- id: INTEGER PRIMARY KEY
- ticker: TEXT
- direction: TEXT (CALL/PUT)
- entry_price: REAL
- signal_time: TIMESTAMP
- confidence: INTEGER
- signal_type: TEXT
- stop_loss: REAL
- take_profit: REAL
- expected_move: REAL
- gex_level: REAL
- rsi_value: REAL
- trend_direction: TEXT
- status: TEXT (OPEN/CLOSED/EXPIRED)
- exit_price: REAL
- exit_time: TIMESTAMP
- exit_reason: TEXT (SL_HIT/TP_HIT/TIME_EXIT/MANUAL)
- pnl: REAL
- pnl_percent: REAL
```

**signal_conditions table:**
- Tracks individual conditions that made up the signal

**price_history table:**
- Tracks price movements for exit detection

#### Auto-Exit Rules
1. **Stop Loss Hit:** Price reaches SL level
2. **Take Profit Hit:** Price reaches TP level
3. **Time Exit:** 24 hours from signal generation

### 5. Performance Tracking

#### Dashboard Metrics
- **Total Signals:** Lifetime signal count
- **Win Rate:** Percentage of profitable signals
- **Total P&L:** Cumulative profit/loss
- **Average P&L:** Per-signal average
- **Best Trade:** Largest profit
- **Worst Trade:** Largest loss
- **Performance by Ticker:** Breakdown per symbol
- **Performance by Direction:** CALL vs PUT stats
- **Equity Curve:** Cumulative P&L over time

### 6. Discord Integration

#### Webhook Alerts
- **New Signal Alert:** Sent when BUY CALL/PUT generated
- **Exit Alert:** Sent when position closed
- **Daily Summary:** End-of-day performance report

#### Setup
1. Create Discord webhook URL
2. Set environment variable: `DISCORD_WEBHOOK_URL`
3. Alerts automatically sent for all signals

### 7. Alert System

#### Browser Notifications
- Flashing modal for new signals
- Audio notification option (browser dependent)
- Visual signal strength meter
- Color-coded signals (Green=CALL, Red=PUT)

#### Alert Modal
- Appears when high-confidence signal generated (>80%)
- Shows signal details and entry levels
- Dismiss button to close

## File Structure

```
trading/dashboard/
├── app.py                 # Main Dash application
├── wsgi.py               # Vercel WSGI entry point
├── vercel.json           # Vercel deployment config
├── signal_tracker.py     # SQLite signal database
├── discord_alerts.py     # Discord webhook integration
├── data_fetcher.py       # Market data (Polygon/yfinance)
├── gex_calculator.py     # GEX calculations
├── polygon_fetcher.py    # Polygon.io API client
├── layouts.py            # UI components
├── gex_education.py      # Educational content
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Environment Variables

```bash
# Required for Polygon.io data
POLYGON_API_KEY=your_polygon_api_key

# Optional for Discord alerts
DISCORD_WEBHOOK_URL=your_discord_webhook_url

# Vercel deployment flag (set automatically)
VERCEL=1
```

## Deployment Instructions

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Deploy
```bash
cd trading/dashboard
vercel --prod
```

### 4. Set Environment Variables
```bash
vercel env add POLYGON_API_KEY
vercel env add DISCORD_WEBHOOK_URL
```

### 5. Redeploy
```bash
vercel --prod
```

## API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "service": "gex-terminal"}
```

### Get All Signals
```
GET /api/signals
Response: {"signals": [...]}
```

## Local Development

### Run Locally
```bash
cd trading/dashboard
python app.py
```

Access at: `http://localhost:8050`

### Run with WSGI (like production)
```bash
cd trading/dashboard
gunicorn wsgi:app_for_vercel -b 0.0.0.0:8050
```

## Data Sources

### Primary: Polygon.io
- Real-time options data
- Rate limit: 5 requests/minute (free tier)
- Premium data with Greeks

### Fallback: Yahoo Finance (yfinance)
- Free options data
- No rate limits
- Less accurate Greeks

### Fallback: Simulated Data
- Used when both sources fail
- Realistic GEX patterns
- For demo/testing only

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1 | Help |
| F2 | GEX Profile |
| F3 | Heatmap |
| F4 | Key Levels |
| F5 | Signals |
| F6 | Performance |
| F7 | Export Data |
| F8 | Refresh |
| F9-F12 | Quick Tickers (SPY, QQQ, NVDA, TSLA) |

## Command Line

Enter commands in the command bar:
- `<TICKER>` - Load ticker data (e.g., "SPY")
- `GEX <T>` - Show GEX for ticker T
- `REFRESH` - Force data refresh
- `HELP` - Show help

## Signal Export

Click the "EXPORT" button to download signal history as CSV.

## Troubleshooting

### No Data Loading
1. Check POLYGON_API_KEY is set
2. Verify rate limit hasn't been exceeded
3. Check browser console for errors

### Signals Not Generating
1. Check market is open (signals only during market hours)
2. Verify GEX data is loading
3. Check RSI calculation needs price history

### Discord Alerts Not Working
1. Verify DISCORD_WEBHOOK_URL is set correctly
2. Check webhook URL is valid in Discord
3. Test webhook manually

## Performance Considerations

- SQLite database stored in `/tmp/` on Vercel (ephemeral)
- For persistent storage, use external database (Supabase, etc.)
- Rate limiting prevents API abuse
- Caching reduces redundant data fetches

## Future Enhancements

- [ ] WebSocket real-time updates
- [ ] External database for persistence
- [ ] Multi-timeframe analysis
- [ ] Options flow integration
- [ ] Backtesting engine
- [ ] Mobile app

## Support

For issues or questions:
1. Check logs in Vercel dashboard
2. Review browser console
3. Verify environment variables
4. Test locally first

---

**Version:** 2.0.0  
**Last Updated:** 2026-02-27  
**Built with:** Dash, Plotly, SQLite, Vercel
