# Trading Strategy Backtest Report

## Strategy: Dual Moving Average Crossover with RSI Filter

### Overview
A classic momentum strategy enhanced with RSI overbought/oversold filtering to reduce false signals.

### Rules

**Entry Long:**
- Fast EMA (20) crosses above Slow EMA (50)
- RSI (14) > 50 (avoid oversold bounces)
- Price > 200 EMA (trend confirmation)

**Exit Long:**
- Fast EMA crosses below Slow EMA
- OR Stop loss hit (-2% from entry)
- OR Trailing stop (-5% from highest price)

**Position Sizing:**
- Risk 1% of portfolio per trade
- Calculate position size based on stop distance

### Backtest Parameters
- Instrument: SPY (S&P 500 ETF)
- Timeframe: Daily
- Period: 2022-01-01 to 2025-01-01 (3 years)
- Initial Capital: $100,000
- Commission: $0 (typical for modern brokers)

### Results

| Metric | Value |
|--------|-------|
| Total Return | TBD |
| Annualized Return | TBD |
| Sharpe Ratio | TBD |
| Max Drawdown | TBD |
| Win Rate | TBD |
| Profit Factor | TBD |
| Number of Trades | TBD |
| Avg Trade | TBD |

### Files
- `backtest_dual_ma.py` - Main backtest script
- `spy_backtest_results.csv` - Trade log
- `equity_curve.png` - Visual performance chart

### Next Steps
1. Run backtest
2. Analyze results
3. Optimize parameters if edge exists
4. Prepare for paper trading
