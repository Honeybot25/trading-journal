#!/usr/bin/env python3
"""
NVDA Momentum Trading Strategy Backtest
Strategy: Dual Momentum (RSI + EMA Trend Filter)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import requests

# Configuration
SYMBOL = "NVDA"
PERIOD_DAYS = 60
RSI_PERIOD = 14
EMA_PERIOD = 20
RSI_ENTRY = 40
RSI_EXIT_PROFIT = 70
RSI_EXIT_STOP = 35
INITIAL_CAPITAL = 10000

print(f"📊 NVDA Momentum Backtest - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Strategy: RSI({RSI_PERIOD}) + EMA({EMA_PERIOD})")
print("-" * 50)

# Calculate date range
end_date = datetime.now()
start_date = end_date - timedelta(days=PERIOD_DAYS + 30)  # Extra for indicator calc

# Download data
print(f"Fetching {SYMBOL} data from {start_date.date()} to {end_date.date()}...")
df = yf.download(SYMBOL, start=start_date, end=end_date, progress=False)

if df.empty:
    print("❌ Failed to fetch data")
    exit(1)

# Handle multi-level columns if present
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# Calculate indicators
def calculate_rsi(prices, period=14):
    """Calculate RSI using Wilder's formula"""
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, period=20):
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()

# Apply indicators
df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
df['EMA'] = calculate_ema(df['Close'], EMA_PERIOD)
df['Position'] = 0
df['Signal'] = 0

# Drop NaN values from indicator calculations
df = df.dropna()

# Slice to actual backtest period (last 30 days with full indicators)
df = df.tail(PERIOD_DAYS + 5)  # Get a bit extra for signal detection
df = df.dropna()

# Generate trading signals
position = 0
entry_price = 0
entry_date = None

for i in range(1, len(df)):
    current_rsi = df['RSI'].iloc[i]
    prev_rsi = df['RSI'].iloc[i-1]
    current_price = df['Close'].iloc[i]
    ema_line = df['EMA'].iloc[i]
    
    if position == 0:
        # Entry condition: RSI crosses above RSI_ENTRY and price > EMA
        if prev_rsi < RSI_ENTRY and current_rsi >= RSI_ENTRY and current_price > ema_line:
            position = 1
            entry_price = current_price
            entry_date = df.index[i]
            df.loc[df.index[i], 'Signal'] = 1  # Buy signal
    else:
        # Exit conditions
        exit_signal = False
        exit_reason = ""
        
        if current_rsi >= RSI_EXIT_PROFIT:
            exit_signal = True
            exit_reason = "profit"
        elif current_rsi < RSI_EXIT_STOP:
            exit_signal = True
            exit_reason = "stop_loss"
        
        if exit_signal:
            exit_price = current_price
            returns = (exit_price - entry_price) / entry_price
            df.loc[df.index[i], 'Signal'] = -1  # Sell signal
            df.loc[df.index[i], 'Trade_Return'] = returns
            df.loc[df.index[i], 'Trade_Duration'] = (df.index[i] - entry_date).days
            position = 0
            entry_price = 0

# Close any open position at the end
if position == 1:
    final_price = df['Close'].iloc[-1]
    returns = (final_price - entry_price) / entry_price
    df.loc[df.index[-1], 'Signal'] = -1
    df.loc[df.index[-1], 'Trade_Return'] = returns
    if entry_date:
        df.loc[df.index[-1], 'Trade_Duration'] = (df.index[-1] - entry_date).days

# Backtest calculation
trades = df[df['Signal'] == -1].copy()

if len(trades) == 0:
    print("⚠️ No trades executed in the backtest period")
    
    # Log to Mission Control
    log_data = {
        "agent": "TraderBot",
        "project": "momentum-strategy",
        "status": "completed",
        "description": f"NVDA Dual Momentum backtest - No trades generated in {PERIOD_DAYS} days",
        "estimated_impact": "low",
        "duration": 0,
        "results": {
            "trades": 0,
            "total_return": 0,
            "win_rate": 0,
            "max_drawdown": 0
        }
    }
    
    try:
        requests.post("https://mission-control-lovat-rho.vercel.app/api/logs", 
                     json=log_data, timeout=10)
        print("✅ Logged to Mission Control")
    except Exception as e:
        print(f"⚠️ Failed to log to Mission Control: {e}")
    
    print(f"\n📈 BACKTEST RESULTS")
    print(f"Total Trades: 0")
    print(f"Recommendation: Market conditions didn't produce signals. Consider wider parameters or different timeframe.")
    exit(0)

# Calculate metrics
total_return_pct = trades['Trade_Return'].sum() * 100
winning_trades = len(trades[trades['Trade_Return'] > 0])
losing_trades = len(trades[trades['Trade_Return'] <= 0])
win_rate = (winning_trades / len(trades)) * 100 if len(trades) > 0 else 0

# Calculate max drawdown
portfolio_values = [INITIAL_CAPITAL]
for ret in trades['Trade_Return']:
    portfolio_values.append(portfolio_values[-1] * (1 + ret))

running_max = np.maximum.accumulate(portfolio_values)
drawdowns = (portfolio_values - running_max) / running_max
max_drawdown = drawdowns.min() * 100

avg_trade_return = trades['Trade_Return'].mean() * 100
avg_win = trades[trades['Trade_Return'] > 0]['Trade_Return'].mean() * 100 if winning_trades > 0 else 0
avg_loss = trades[trades['Trade_Return'] <= 0]['Trade_Return'].mean() * 100 if losing_trades > 0 else 0

# Print results
print(f"\n📈 BACKTEST RESULTS - NVDA Dual Momentum Strategy")
print(f"Period: {PERIOD_DAYS} days")
print(f"-" * 50)
print(f"Total Trades: {len(trades)}")
print(f"Winning Trades: {winning_trades}")
print(f"Losing Trades: {losing_trades}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"Total Return: {total_return_pct:.2f}%")
print(f"Max Drawdown: {max_drawdown:.2f}%")
print(f"Avg Trade Return: {avg_trade_return:.2f}%")
print(f"Avg Win: {avg_win:.2f}%")
print(f"Avg Loss: {avg_loss:.2f}%")

# Trade log
print(f"\n📋 Individual Trades:")
for idx, (date, row) in enumerate(trades.iterrows()):
    ret = row['Trade_Return'] * 100
    emoji = "✅" if ret > 0 else "❌"
    print(f"  {emoji} Trade {idx+1}: {date.strftime('%Y-%m-%d')} | Return: {ret:+.2f}%")

# Calculate duration
duration_seconds = 0  # Would need timer in real scenario

# Log to Mission Control
log_data = {
    "agent": "TraderBot",
    "project": "momentum-strategy",
    "status": "completed",
    "description": f"NVDA Dual Momentum backtest complete. RSI({RSI_PERIOD}) + EMA({EMA_PERIOD}) strategy. {len(trades)} trades, {win_rate:.1f}% win rate, {total_return_pct:.2f}% total return.",
    "estimated_impact": "high",
    "duration": duration_seconds,
    "results": {
        "symbol": SYMBOL,
        "strategy": "RSI+EMA Dual Momentum",
        "period_days": PERIOD_DAYS,
        "total_trades": int(len(trades)),
        "winning_trades": int(winning_trades),
        "losing_trades": int(losing_trades),
        "win_rate_pct": round(win_rate, 2),
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "avg_trade_return_pct": round(avg_trade_return, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "parameters": {
            "rsi_period": RSI_PERIOD,
            "ema_period": EMA_PERIOD,
            "rsi_entry": RSI_ENTRY,
            "rsi_exit_profit": RSI_EXIT_PROFIT,
            "rsi_exit_stop": RSI_EXIT_STOP
        }
    }
}

try:
    response = requests.post("https://mission-control-lovat-rho.vercel.app/api/logs", 
                           json=log_data, timeout=10)
    if response.status_code == 200:
        print("\n✅ Successfully logged to Mission Control")
    else:
        print(f"\n⚠️ Mission Control returned status {response.status_code}")
except Exception as e:
    print(f"\n⚠️ Failed to log to Mission Control: {e}")

# Recommendation
print("\n🎯 PAPER TRADING RECOMMENDATION")
print("-" * 50)
if win_rate >= 50 and total_return_pct > 0 and abs(max_drawdown) < 10:
    print("✅ APPROVED for paper trading")
    print("   - Positive equity curve with acceptable drawdown")
    print("   - Win rate supports edge")
    print("   - Suggested position size: 5-10% of account per trade")
    print("   - Run paper trading for 2 weeks before considering live")
elif win_rate >= 40 and total_return_pct > 0:
    print("⚠️ CONDITIONAL APPROVAL")
    print("   - Strategy shows promise but needs refinement")
    print("   - Consider widening stop loss or adjusting entry timing")
    print("   - Run longer backtest (90 days) before paper trading")
else:
    print("❌ NOT RECOMMENDED for paper trading")
    print("   - Negative or poor risk-adjusted returns")
    print("   - Strategy needs optimization")
    print("   - Consider: longer/slower signals, ADX filter, or different asset")

print("\n" + "=" * 50)
