#!/usr/bin/env python3
"""
Active Swing Trading Backtest
Bollinger Band Squeeze + Volume Breakout
4H timeframe, 2-week max hold
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

# Parameters
INITIAL_CAPITAL = 50000
TICKER = "SPY"
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
BB_PERIOD = 20
BB_STD = 2
VOLUME_MULT = 1.5
MAX_HOLD_DAYS = 14
TRAILING_STOP = 0.10  # 10%

print(f"📊 Swing Trading Backtest: {TICKER}")
print(f"Strategy: Bollinger Band Squeeze + Volume Breakout")
print(f"Period: {START_DATE} to {END_DATE}")
print(f"Max Hold: {MAX_HOLD_DAYS} days | Trailing Stop: {TRAILING_STOP*100}%")
print("=" * 60)

# Download data
print("\n📥 Downloading 4H data...")
df = yf.download(TICKER, start=START_DATE, end=END_DATE, interval="1h", progress=False)

if df.empty:
    print("⚠️  No 4H data available, falling back to 1H and resampling...")
    # Resample to 4H
    df = df.resample('4H').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

# Calculate indicators
df['BB_Middle'] = df['Close'].rolling(window=BB_PERIOD).mean()
df['BB_Std'] = df['Close'].rolling(window=BB_PERIOD).std()
df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * BB_STD)
df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * BB_STD)
df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
df['Vol_MA20'] = df['Volume'].rolling(window=BB_PERIOD).mean()
df['Vol_Ratio'] = df['Volume'] / df['Vol_MA20']

# Squeeze detection (low volatility period)
df['Squeeze'] = df['BB_Width'] < df['BB_Width'].rolling(window=BB_PERIOD).mean()

# Trading logic
position = 0
entry_price = 0
entry_date = None
highest_price = 0
trades = []
capital = INITIAL_CAPITAL

print("\n🔍 Running backtest...")

for i in range(BB_PERIOD + 20, len(df)):
    current = df.iloc[i]
    date = df.index[i]
    
    # Entry logic
    if position == 0:
        # Breakout above upper BB with high volume after squeeze
        squeeze_period = df['Squeeze'].iloc[i-5:i].any()  # Squeeze in last 5 bars
        breakout = current['Close'] > current['BB_Upper']
        high_volume = current['Vol_Ratio'] > VOLUME_MULT
        
        if squeeze_period and breakout and high_volume:
            position = 1
            entry_price = float(current['Close'])
            entry_date = date
            highest_price = entry_price
            shares = int(capital / entry_price)
            
            print(f"🟢 ENTRY {date.strftime('%Y-%m-%d %H:%M')} | ${entry_price:.2f} | Vol: {current['Vol_Ratio']:.2f}x")
    
    # Exit logic
    elif position == 1:
        current_price = float(current['Close'])
        highest_price = max(highest_price, current_price)
        days_held = (date - entry_date).days
        
        # Trailing stop
        trailing_exit = current_price < highest_price * (1 - TRAILING_STOP)
        # Max hold
        time_exit = days_held >= MAX_HOLD_DAYS
        
        if trailing_exit or time_exit:
            exit_reason = "Trailing Stop" if trailing_exit else "Max Hold"
            pnl = (current_price - entry_price) * shares
            pnl_pct = ((current_price / entry_price) - 1) * 100
            
            trades.append({
                'entry_date': entry_date,
                'exit_date': date,
                'entry_price': entry_price,
                'exit_price': current_price,
                'days_held': days_held,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'shares': shares
            })
            
            capital += pnl
            emoji = "🟢" if pnl > 0 else "🔴"
            print(f"{emoji} EXIT  {date.strftime('%Y-%m-%d %H:%M')} | ${current_price:.2f} | {exit_reason} | P&L: ${pnl:,.0f} ({pnl_pct:+.1f}%)")
            
            position = 0

# Calculate metrics
if len(trades) == 0:
    print("\n❌ No trades generated")
else:
    df_trades = pd.DataFrame(trades)
    total_pnl = df_trades['pnl'].sum()
    total_return = (total_pnl / INITIAL_CAPITAL) * 100
    win_rate = (df_trades['pnl'] > 0).mean() * 100
    avg_trade = df_trades['pnl'].mean()
    avg_hold = df_trades['days_held'].mean()
    max_drawdown = df_trades['pnl_pct'].min()
    best_trade = df_trades['pnl_pct'].max()
    
    print("\n" + "=" * 60)
    print("📈 RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Trades:      {len(trades)}")
    print(f"Win Rate:          {win_rate:.1f}%")
    print(f"Total Return:      ${total_pnl:,.0f} ({total_return:+.1f}%)")
    print(f"Avg Trade:         ${avg_trade:,.0f}")
    print(f"Avg Hold Time:     {avg_hold:.1f} days")
    print(f"Best Trade:        +{best_trade:.1f}%")
    print(f"Worst Trade:       {max_drawdown:.1f}%")
    print(f"Final Capital:     ${INITIAL_CAPITAL + total_pnl:,.0f}")
    
    print("\n📋 EXIT REASONS:")
    print(df_trades['exit_reason'].value_counts())

print("\n✅ Backtest complete")
