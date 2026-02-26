# 📓 Comprehensive Trading Journal

A full-featured trading journal system for tracking positions, P&L, and performance analytics.

## Features

| Feature | Description |
|---------|-------------|
| 📝 Trade Logging | Record entries, exits, stops, targets |
| 📊 P&L Tracking | Realized/unrealized P&L with analytics |
| 🎯 Performance Stats | Win rate, profit factor, expectancy |
| 📈 Strategy Analysis | Compare performance by strategy |
| 🕐 Journal Entries | Daily notes, mood, lessons learned |
| 🤖 GEX Integration | Auto-log GEX scanner signals |
| ⚡ Auto Exits | Time-based and level-based exits |
| 📤 Export | CSV export for external analysis |

## File Structure

```
trading/
├── journal.py              # Main journal system
├── gex_bridge.py           # GEX scanner integration
├── daily_report.py         # Daily report generator
├── journal/                # Journal data directory
│   ├── trading_journal.db  # SQLite database
│   ├── journal.log         # Activity log
│   └── trades_export_*.csv # Export files
└── gex_scanner.py          # GEX scanner (separate)
```

## Quick Start

### 1. Add a Manual Trade

```bash
cd /Users/Honeybot/.openclaw/workspace/trading
source venv/bin/activate

python journal.py add \
  --ticker NVDA \
  --direction long \
  --price 195.50 \
  --quantity 2 \
  --size 2000 \
  --stop 190.00 \
  --target 210.00 \
  --strategy "breakout" \
  --confidence 75 \
  --notes "AI conference catalyst"
```

### 2. Close a Trade

```bash
python journal.py close \
  --id 1 \
  --price 205.00 \
  --reason "target_hit" \
  --notes "Took profits at resistance"
```

### 3. View Dashboard

```bash
python journal.py dashboard
```

Output:
```
======================================================================
📊 TRADING JOURNAL DASHBOARD
======================================================================

🟢 OPEN POSITIONS: 2
   NVDA  | long  | $  195.50 | gex        | 2026-02-25
   TSLA  | short | $  417.40 | momentum   | 2026-02-26

📈 TODAY'S PERFORMANCE (2026-02-25)
   Trades: 3
   Win Rate: 66.7%
   P&L: $1,245.00
   Best: $890.00 | Worst: -$120.00

📊 7-DAY PERFORMANCE
   Total Trades: 12
   Win Rate: 58.3%
   Total P&L: $3,420.00
   Avg Return: 2.4%

🎯 BY STRATEGY:
   gex          |   5 trades | 60.0% WR | $   1,850.00
   momentum     |   4 trades | 50.0% WR | $     890.00
   breakout     |   3 trades | 66.7% WR | $     680.00

📈 TOP TICKERS:
   NVDA   |   4 trades | $   1,450.00
   TSLA   |   3 trades | $     890.00
   SPY    |   2 trades | $     680.00

======================================================================
```

### 4. Add Journal Entry

```bash
python journal.py journal \
  --title "Choppy Market Day" \
  --content "Range-bound action, waited for GEX levels" \
  --mood "patient" \
  --market "choppy" \
  --lessons "Don't force trades in low volatility"
```

### 5. View Statistics

```bash
# Last 30 days
python journal.py stats --days 30

# List all trades
python journal.py list --limit 50

# List open positions only
python journal.py list --status open

# Export to CSV
python journal.py export --output my_trades.csv
```

## GEX Integration

### Auto-Log GEX Signals

```bash
# Run scanner and convert signals to journal trades
python gex_bridge.py --scan
```

This will:
1. Scan all tickers for GEX signals
2. Create journal entries for BUY/SELL signals
3. Set stop loss at 2% from GEX level
4. Set take profit at 5% target

### Auto-Check Exits

```bash
# Check stop loss / take profit levels
python gex_bridge.py --check-exits
```

### Time-Based Exits

```bash
# Exit positions held > 24 hours
python gex_bridge.py --time-exit 24
```

## Database Schema

### Trades Table
- `id` - Trade ID
- `timestamp` - Entry time
- `ticker` - Symbol
- `direction` - long/short
- `entry_price` - Entry price
- `exit_price` - Exit price (if closed)
- `quantity` - Number of contracts
- `position_size` - Dollar amount
- `stop_loss` - Stop price
- `take_profit` - Target price
- `status` - open/closed/cancelled
- `pnl_absolute` - Dollar P&L
- `pnl_percent` - Percentage return
- `strategy` - Strategy name
- `confidence` - Signal confidence (0-100)
- `notes` - Trade notes
- `tags` - Comma-separated tags

### Journal Entries Table
- Daily notes, mood, lessons

### Daily Summary Table
- Aggregated daily performance metrics

### Strategy Stats Table
- Performance by strategy

## Cron Jobs

### Auto-Scan and Log (Every 30 min)
```bash
*/30 9-16 * * 1-5 cd /Users/Honeybot/.openclaw/workspace/trading && source venv/bin/activate && python gex_bridge.py --scan
```

### Auto-Check Exits (Every hour)
```bash
0 * * * 1-5 cd /Users/Honeybot/.openclaw/workspace/trading && source venv/bin/activate && python gex_bridge.py --check-exits
```

### Daily Report (5 PM EST)
```bash
0 17 * * 1-5 cd /Users/Honeybot/.openclaw/workspace/trading && source venv/bin/activate && python daily_report.py
```

## Key Metrics Calculated

| Metric | Formula |
|--------|---------|
| Win Rate | Wins / Total Trades |
| Profit Factor | Gross Profit / Gross Loss |
| Avg Win | Sum of winning trades / # wins |
| Avg Loss | Sum of losing trades / # losses |
| Expectancy | (Win% × Avg Win) - (Loss% × Avg Loss) |
| Max Drawdown | Largest peak-to-trough decline |

## Tips

1. **Tag everything** - Use tags like "gex,earnings, breakout" for filtering
2. **Journal daily** - Notes on mood/market conditions improve self-awareness
3. **Review weekly** - Export CSV and analyze in Excel/sheets
4. **Set stops** - Always use --stop and --target for auto-exits
5. **Track confidence** - See if high-confidence signals perform better

## Future Enhancements

- [ ] Equity curve chart generation
- [ ] Trade screenshots attachment
- [ ] Risk:Reward ratio tracking
- [ ] Monte Carlo simulation
- [ ] Trade review checklists
- [ ] Integration with broker APIs

---

*Track. Analyze. Improve.* 🚀
