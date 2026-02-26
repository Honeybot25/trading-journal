#!/usr/bin/env python3
"""
Simple Vectorized Dual MA Crossover Backtest
Uses pandas and numpy for speed and simplicity
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import json

def download_data(ticker='SPY', start='2022-01-01', end='2025-01-01'):
    """Download historical data from Yahoo Finance"""
    print(f"Downloading {ticker} data...")
    df = yf.download(ticker, start=start, end=end, progress=False)
    df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() 
                  for col in df.columns]
    return df

def add_indicators(df):
    """Add technical indicators"""
    # Moving averages
    df['ema_fast'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_trend'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df

def generate_signals(df):
    """Generate buy/sell signals"""
    df['signal'] = 0
    
    # Buy: Fast EMA crosses above Slow EMA + RSI > 50 + Price > 200 EMA
    bullish_cross = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
    rsi_filter = df['rsi'] > 50
    trend_filter = df['close'] > df['ema_trend']
    
    df.loc[bullish_cross & rsi_filter & trend_filter, 'signal'] = 1
    
    # Sell: Fast EMA crosses below Slow EMA
    bearish_cross = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
    df.loc[bearish_cross, 'signal'] = -1
    
    return df

def backtest_strategy(df, initial_capital=100000, risk_per_trade=0.01, 
                      stop_loss=0.02, trail_stop=0.05):
    """Run backtest simulation"""
    
    capital = initial_capital
    position = 0
    entry_price = 0
    highest_price = 0
    trades = []
    equity_curve = []
    
    for i in range(200, len(df)):  # Skip first 200 bars for indicator warmup
        date = df.index[i]
        price = df['close'].iloc[i]
        signal = df['signal'].iloc[i]
        
        # Update trailing stop if in position
        if position > 0:
            if price > highest_price:
                highest_price = price
            
            # Check exits
            stop_hit = price <= entry_price * (1 - stop_loss)
            trail_hit = price <= highest_price * (1 - trail_stop)
            signal_exit = signal == -1
            
            if stop_hit or trail_hit or signal_exit:
                # Close position
                exit_reason = 'Stop Loss' if stop_hit else ('Trailing Stop' if trail_hit else 'Signal')
                pnl = (price - entry_price) * position
                pnl_pct = (price / entry_price - 1) * 100
                
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': date.strftime('%Y-%m-%d'),
                    'entry_price': round(entry_price, 2),
                    'exit_price': round(price, 2),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'exit_reason': exit_reason
                })
                
                capital += pnl
                position = 0
                entry_price = 0
                highest_price = 0
        
        # Check entry
        elif signal == 1 and position == 0:
            # Calculate position size
            stop_price = price * (1 - stop_loss)
            risk_amount = capital * risk_per_trade
            risk_per_share = price - stop_price
            
            if risk_per_share > 0:
                shares = int(risk_amount / risk_per_share)
                cost = shares * price
                
                if cost <= capital and shares > 0:
                    position = shares
                    entry_price = price
                    highest_price = price
                    entry_date = date.strftime('%Y-%m-%d')
        
        # Track equity
        position_value = position * price if position > 0 else 0
        equity_curve.append({
            'date': date,
            'equity': capital + position_value
        })
    
    # Close any open position at the end
    if position > 0:
        final_price = df['close'].iloc[-1]
        pnl = (final_price - entry_price) * position
        trades.append({
            'entry_date': entry_date,
            'exit_date': df.index[-1].strftime('%Y-%m-%d'),
            'entry_price': round(entry_price, 2),
            'exit_price': round(final_price, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round((final_price / entry_price - 1) * 100, 2),
            'exit_reason': 'End of Period'
        })
        capital += pnl
    
    return trades, equity_curve, capital

def calculate_metrics(trades, equity_curve, initial_capital):
    """Calculate performance metrics"""
    
    if not trades:
        return {"error": "No trades executed"}
    
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve).set_index('date')
    
    # Basic metrics
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['pnl'] > 0])
    losing_trades = len(trades_df[trades_df['pnl'] <= 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = trades_df['pnl'].sum()
    avg_trade = trades_df['pnl'].mean()
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['pnl'] <= 0]['pnl'].mean() if losing_trades > 0 else 0
    
    profit_factor = (abs(trades_df[trades_df['pnl'] > 0]['pnl'].sum()) / 
                     abs(trades_df[trades_df['pnl'] <= 0]['pnl'].sum())) if losing_trades > 0 else float('inf')
    
    # Returns
    final_equity = equity_df['equity'].iloc[-1]
    total_return = (final_equity / initial_capital - 1) * 100
    
    # Calculate annualized return (assume ~252 trading days per year)
    days = (equity_df.index[-1] - equity_df.index[0]).days
    years = days / 365.25
    annualized_return = ((final_equity / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    
    # Max drawdown
    equity_df['peak'] = equity_df['equity'].cummax()
    equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
    max_drawdown = equity_df['drawdown'].min()
    
    # Sharpe ratio (simplified - using daily returns)
    equity_df['returns'] = equity_df['equity'].pct_change()
    sharpe = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252) if equity_df['returns'].std() != 0 else 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),
        'total_pnl': round(total_pnl, 2),
        'total_return_pct': round(total_return, 2),
        'annualized_return_pct': round(annualized_return, 2),
        'avg_trade': round(avg_trade, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown_pct': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe, 2),
        'final_equity': round(final_equity, 2)
    }

def main():
    print("=" * 60)
    print("DUAL MA CROSSOVER STRATEGY BACKTEST")
    print("=" * 60)
    
    # Download data
    df = download_data('SPY', '2022-01-01', '2025-01-01')
    print(f"Data loaded: {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")
    
    # Add indicators
    df = add_indicators(df)
    print("Indicators calculated: EMA(20,50,200), RSI(14)")
    
    # Generate signals
    df = generate_signals(df)
    signals = df[df['signal'] != 0]
    print(f"Signals generated: {len(signals)} total ({len(signals[signals['signal']==1])} buy, {len(signals[signals['signal']==-1])} sell)")
    
    # Run backtest
    print("\nRunning backtest simulation...")
    trades, equity_curve, final_capital = backtest_strategy(df)
    
    # Calculate metrics
    metrics = calculate_metrics(trades, equity_curve, 100000)
    
    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    print(f"\nInitial Capital: $100,000")
    print(f"Final Equity: ${metrics['final_equity']:,.2f}")
    print(f"Total Return: {metrics['total_return_pct']:.2f}%")
    print(f"Annualized Return: {metrics['annualized_return_pct']:.2f}%")
    print(f"\nTotal Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.1f}%")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"\nAverage Trade: ${metrics['avg_trade']:.2f}")
    print(f"Average Win: ${metrics['avg_win']:.2f}")
    print(f"Average Loss: ${metrics['avg_loss']:.2f}")
    
    # Save results
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv('trades_log.csv', index=False)
    print(f"\nTrade log saved to trades_log.csv")
    
    equity_df = pd.DataFrame(equity_curve)
    equity_df.to_csv('equity_curve.csv', index=False)
    print("Equity curve saved to equity_curve.csv")
    
    # Save metrics
    with open('backtest_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print("Metrics saved to backtest_metrics.json")
    
    # Print recent trades
    print("\n" + "=" * 60)
    print("RECENT TRADES (Last 5)")
    print("=" * 60)
    recent = trades[-5:] if len(trades) >= 5 else trades
    for trade in recent:
        emoji = "🟢" if trade['pnl'] > 0 else "🔴"
        print(f"{emoji} {trade['exit_date']}: ${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%) - {trade['exit_reason']}")
    
    print("\n" + "=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)
    
    return metrics

if __name__ == '__main__':
    metrics = main()
