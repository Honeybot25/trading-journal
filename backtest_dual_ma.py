#!/usr/bin/env python3
"""
Dual Moving Average Crossover Strategy with RSI Filter
Backtest using Backtrader
"""

import backtrader as bt
import backtrader.feeds as btfeeds
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

class DualMACrossover(bt.Strategy):
    params = (
        ('fast_ema', 20),
        ('slow_ema', 50),
        ('trend_ema', 200),
        ('rsi_period', 14),
        ('rsi_mid', 50),
        ('stop_loss', 0.02),  # 2% stop loss
        ('trail_stop', 0.05),  # 5% trailing stop
        ('risk_per_trade', 0.01),  # 1% risk per trade
    )
    
    def __init__(self):
        # Indicators
        self.fast_ema = bt.indicators.EMA(period=self.p.fast_ema)
        self.slow_ema = bt.indicators.EMA(period=self.p.slow_ema)
        self.trend_ema = bt.indicators.EMA(period=self.p.trend_ema)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        
        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.fast_ema, self.slow_ema)
        
        # Tracking
        self.order = None
        self.entry_price = None
        self.highest_price = None
        self.trades = []
        
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}')
                self.entry_price = order.executed.price
                self.highest_price = order.executed.price
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}')
                
                # Record trade
                pnl = order.executed.price - self.entry_price if self.entry_price else 0
                self.trades.append({
                    'exit_date': self.datas[0].datetime.date(0).isoformat(),
                    'exit_price': order.executed.price,
                    'pnl': pnl,
                    'pnl_pct': (pnl / self.entry_price * 100) if self.entry_price else 0
                })
                self.entry_price = None
                self.highest_price = None
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            
        self.order = None
        
    def next(self):
        # Skip if order pending
        if self.order:
            return
            
        # Get current values
        close = self.data.close[0]
        fast_val = self.fast_ema[0]
        slow_val = self.slow_ema[0]
        trend_val = self.trend_ema[0]
        rsi_val = self.rsi[0]
        
        # Check if in position
        if not self.position:
            # Entry logic: Bullish crossover + RSI > 50 + Price > trend EMA
            if (self.crossover > 0 and 
                rsi_val > self.p.rsi_mid and 
                close > trend_val):
                
                # Calculate position size based on risk
                stop_price = close * (1 - self.p.stop_loss)
                risk_amount = self.broker.getvalue() * self.p.risk_per_trade
                risk_per_share = close - stop_price
                
                if risk_per_share > 0:
                    size = int(risk_amount / risk_per_share)
                    size = min(size, int(self.broker.getvalue() / close))  # Don't exceed cash
                    
                    if size > 0:
                        self.log(f'BUY CREATE, Price: {close:.2f}, Size: {size}')
                        self.order = self.buy(size=size)
                        
        else:
            # Update highest price for trailing stop
            if close > self.highest_price:
                self.highest_price = close
                
            # Exit logic
            stop_hit = close <= self.entry_price * (1 - self.p.stop_loss)
            trail_hit = close <= self.highest_price * (1 - self.p.trail_stop)
            crossover_exit = self.crossover < 0
            
            if stop_hit or trail_hit or crossover_exit:
                reason = 'STOP' if stop_hit else ('TRAIL' if trail_hit else 'CROSSOVER')
                self.log(f'SELL CREATE ({reason}), Price: {close:.2f}')
                self.order = self.sell(size=self.position.size)


def run_backtest():
    # Create cerebro engine
    cerebro = bt.Cerebro()
    
    # Download data
    print("Downloading SPY data...")
    spy = yf.download('SPY', start='2022-01-01', end='2025-01-01', progress=False)
    spy.reset_index(inplace=True)
    spy.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    
    # Ensure proper column types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        spy[col] = spy[col].astype(float)
    
    # Create data feed
    data = bt.feeds.PandasData(
        dataname=spy,
        datetime='date',
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )
    
    cerebro.adddata(data)
    
    # Add strategy
    cerebro.addstrategy(DualMACrossover)
    
    # Set initial cash
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    print(f'Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    strat = results[0]
    
    # Get final value
    final_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value: ${final_value:.2f}')
    print(f'Total Return: {((final_value / 100000.0) - 1) * 100:.2f}%')
    
    # Extract analyzers
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    # Print results
    print('\n' + '='*50)
    print('BACKTEST RESULTS')
    print('='*50)
    print(f"Sharpe Ratio: {sharpe.get('sharperatio', 'N/A')}")
    print(f"Max Drawdown: {drawdown.get('max', {}).get('drawdown', 'N/A'):.2f}%")
    print(f"Annual Return: {returns.get('rnorm100', 'N/A'):.2f}%")
    
    if trades:
        total_trades = trades.get('total', {}).get('total', 0)
        won_trades = trades.get('won', {}).get('total', 0)
        lost_trades = trades.get('lost', {}).get('total', 0)
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Won: {won_trades}, Lost: {lost_trades}")
    
    # Save equity curve
    cerebro.plot(style='candlestick', savefig=True, figfilename='equity_curve.png')
    print('\nEquity curve saved to equity_curve.png')
    
    # Save trades to CSV
    if hasattr(strat, 'trades') and strat.trades:
        trades_df = pd.DataFrame(strat.trades)
        trades_df.to_csv('trades_log.csv', index=False)
        print('Trade log saved to trades_log.csv')
    
    return strat, final_value


if __name__ == '__main__':
    run_backtest()
