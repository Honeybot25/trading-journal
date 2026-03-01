# How GEX Terminal Pro Works

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ GEX      │ │ Signal   │ │ Key      │ │ Performance│          │
│  │ Profile  │ │ Panel    │ │ Levels   │ │ Dashboard │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Polygon.io   │  │ Yahoo Finance│  │ SQLite DB    │          │
│  │ (Primary)    │  │ (Fallback)   │  │ (Signals)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL ENGINE                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ GEX          │  │ RSI          │  │ Signal       │          │
│  │ Calculator   │  │ Analysis     │  │ Generator    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Signal Generation Flow

### Step 1: Data Fetching
```
1. Request ticker data
2. Try Polygon.io first (premium options data with Greeks)
3. Fallback to Yahoo Finance if rate limited
4. Fallback to simulated data if both fail
5. Cache data for 60 seconds
```

### Step 2: GEX Calculation
```
For each strike in options chain:
  - Get call gamma × open_interest × 100 × spot_price
  - Get put gamma × open_interest × 100 × spot_price
  - Calculate net GEX per strike
  - Find zero gamma crossing point
  - Identify max gamma strikes

Output:
  - Total GEX (positive = stabilizing, negative = trending)
  - Zero gamma level (regime flip point)
  - Support/resistance levels from GEX concentrations
```

### Step 3: Technical Analysis
```
RSI Calculation:
  - Fetch 15 days of price history
  - Calculate price changes
  - Average gains / average losses
  - RSI = 100 - (100 / (1 + RS))

Trend Detection:
  - 5-period SMA vs 20-period SMA
  - Bullish: Short SMA > Long SMA × 1.02
  - Bearish: Short SMA < Long SMA × 0.98
```

### Step 4: Signal Logic

#### BUY CALL Signal
```python
conditions_met = 0
total_weight = 0

# Condition 1: Near positive GEX
for strike, gex in zip(strikes, net_gex):
    if gex > 2.0 and spot_price > strike:
        distance = abs(spot_price - strike) / spot_price
        if distance < 0.02:  # Within 2%
            conditions_met += 1
            total_weight += 3

# Condition 2: RSI oversold
if rsi < 35:
    conditions_met += 1
    total_weight += 2

# Condition 3: Bullish trend
if sma_5 > sma_20 * 1.02:
    conditions_met += 1
    total_weight += 2

# Generate signal if score >= 60%
confidence = 50 + (conditions_met * 20)
if confidence >= 60:
    generate_buy_call_signal()
```

#### BUY PUT Signal
```python
# Similar logic but:
# - Look for negative GEX strikes above price
# - RSI > 65 (overbought)
# - Bearish trend
```

### Step 5: Signal Parameters
```
Entry Price = Current spot price
Stop Loss = Entry × 0.98 (CALL) or Entry × 1.02 (PUT)
Take Profit = Entry ± Expected Move
Expected Move = Spot × (1% + |Total GEX| / 100)
```

---

## Signal Tracking Flow

### When Signal Generated:
```
1. Log to SQLite database:
   - ticker, direction, entry_price
   - signal_time, confidence
   - stop_loss, take_profit
   - expected_move, gex_level, rsi_value
   - status = 'OPEN'

2. Log conditions:
   - Which conditions were met
   - Individual weights
   - Condition values

3. Send Discord alert (if configured):
   - Embed with signal details
   - Entry/SL/TP levels
   - Confidence score
```

### Position Monitoring:
```
Every 60 seconds:
  1. Fetch current prices for all tickers
  2. Check open signals against current price:
     
     IF CALL and price <= stop_loss:
        Close with SL_HIT
     
     IF CALL and price >= take_profit:
        Close with TP_HIT
     
     IF PUT and price >= stop_loss:
        Close with SL_HIT
     
     IF PUT and price <= take_profit:
        Close with TP_HIT
     
     IF signal_age > 24 hours:
        Close with TIME_EXIT
  
  3. Calculate P&L:
     CALL: P&L = exit_price - entry_price
     PUT: P&L = entry_price - exit_price
     
  4. Update database:
     - status = 'CLOSED'
     - exit_price, exit_time
     - exit_reason, pnl, pnl_percent
  
  5. Send Discord exit alert (if configured)
```

---

## Performance Calculation

### Win Rate
```
win_rate = (winning_signals / closed_signals) × 100

Winning signal: pnl > 0
Losing signal: pnl < 0
```

### Average P&L
```
avg_pnl = SUM(all_pnl) / total_signals
avg_win = SUM(winning_pnl) / count(wins)
avg_loss = SUM(losing_pnl) / count(losses)
```

### Equity Curve
```
cumulative_pnl = 0
equity_points = []

for signal in signals_ordered_by_time:
    if signal.status == 'CLOSED':
        cumulative_pnl += signal.pnl
        equity_points.append({
            'time': signal.exit_time,
            'pnl': signal.pnl,
            'cumulative': cumulative_pnl
        })
```

---

## Auto-Refresh System

### Client-Side (Browser)
```javascript
// Two intervals:
1. Data refresh: 60 seconds
   - Triggers callback to fetch new data
   - Updates all charts and panels
   - Checks for new signals

2. Countdown timer: 1 second
   - Updates "NEXT: Xs" display
   - Shows time until next refresh
```

### Server-Side (Vercel)
```python
# Each request:
1. Check cache (60s TTL)
2. If cache valid, return cached data
3. If cache expired:
   - Fetch new data from Polygon/Yahoo
   - Calculate GEX
   - Generate signals
   - Update cache
   - Return fresh data
```

---

## Database Operations

### Schema
```sql
-- Main signals table
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL,  -- 'CALL' or 'PUT'
    entry_price REAL NOT NULL,
    signal_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence INTEGER,
    stop_loss REAL,
    take_profit REAL,
    expected_move REAL,
    status TEXT DEFAULT 'OPEN',  -- 'OPEN', 'CLOSED'
    exit_price REAL,
    exit_time TIMESTAMP,
    exit_reason TEXT,
    pnl REAL,
    pnl_percent REAL
);

-- Conditions breakdown
CREATE TABLE signal_conditions (
    id INTEGER PRIMARY KEY,
    signal_id INTEGER,
    condition_name TEXT,
    condition_met BOOLEAN,
    weight INTEGER,
    FOREIGN KEY (signal_id) REFERENCES signals(id)
);
```

### Key Queries

**Get all signals:**
```sql
SELECT * FROM signals 
ORDER BY signal_time DESC 
LIMIT 100;
```

**Get performance stats:**
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl
FROM signals
WHERE status = 'CLOSED';
```

**Get open signals:**
```sql
SELECT * FROM signals 
WHERE status = 'OPEN';
```

**Performance by ticker:**
```sql
SELECT 
    ticker,
    COUNT(*) as count,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(pnl) as total_pnl
FROM signals
WHERE status = 'CLOSED'
GROUP BY ticker
ORDER BY total_pnl DESC;
```

---

## Discord Integration

### New Signal Webhook
```json
{
  "embeds": [{
    "title": "🟢 BUY CALL SIGNAL",
    "color": 65280,
    "fields": [
      {"name": "📊 Entry", "value": "$590.50", "inline": true},
      {"name": "🛑 Stop", "value": "$578.69", "inline": true},
      {"name": "🎯 Target", "value": "$602.31", "inline": true}
    ],
    "footer": {"text": "GEX Terminal Pro"}
  }]
}
```

### Exit Alert Webhook
```json
{
  "embeds": [{
    "title": "✅ SIGNAL CLOSED",
    "color": 65280,
    "fields": [
      {"name": "💰 P&L", "value": "$4.50 (0.76%)", "inline": true},
      {"name": "📤 Reason", "value": "TP_HIT", "inline": true}
    ]
  }]
}
```

---

## Key Formulas

### GEX Calculation
```
GEX = Gamma × Open_Interest × 100 × Spot_Price / 1e9

Where:
- Gamma: Option Greek (change in delta per $1 move)
- Open_Interest: Number of open contracts
- 100: Shares per contract
- 1e9: Convert to billions
```

### Zero Gamma Level
```
Find where Net_GEX crosses zero:
- Linear interpolation between strikes
- Sign change indicates crossing point
- Market structure changes at this level
```

### Expected Move
```
Expected_Move = Spot × (0.01 + |Total_GEX| / 100)

Higher GEX = Larger expected move
```

### RSI
```
RS = Average_Gain / Average_Loss
RSI = 100 - (100 / (1 + RS))

Oversold: RSI < 30
Overbought: RSI > 70
```

---

## Data Flow Summary

```
User Opens Dashboard
        │
        ▼
┌───────────────┐
│  Vercel       │
│  Serverless   │
│  Function     │
└───────────────┘
        │
        ├──► Check Cache (60s TTL)
        │         │
        │    Cache Hit ──► Return Data
        │         │
        │    Cache Miss
        │         │
        │         ▼
        │    Fetch from Polygon/Yahoo
        │         │
        │         ▼
        │    Calculate GEX
        │         │
        │         ▼
        │    Generate Signals
        │         │
        │         ▼
        │    Log to SQLite
        │         │
        │         ▼
        │    Update Cache
        │         │
        └────────► Return Fresh Data
                        │
                        ▼
                   Render Dashboard
                   (Charts, Signals, Performance)
```

---

**Last Updated:** 2026-02-27  
**Version:** 2.0.0
