#!/usr/bin/env python3
"""
GEX Signal to Journal Bridge
Automatically converts GEX scanner signals to journal trades
"""

import sys
sys.path.insert(0, '/Users/Honeybot/.openclaw/workspace/trading')

from journal import TradingJournal, Trade, TradeDirection, TradeStatus
from gex_scanner import MultiTickerGEXScanner, WATCHLIST
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GEXJournalBridge:
    """Bridge between GEX scanner and trading journal"""
    
    def __init__(self):
        self.journal = TradingJournal()
        self.scanner = MultiTickerGEXScanner(tickers=WATCHLIST)
    
    def scan_and_log(self):
        """Run scanner and convert signals to journal trades"""
        results = self.scanner.run()
        
        trades_created = []
        for result in results:
            signal = result.get('signal', {})
            
            # Only log actionable signals (BUY or SELL)
            if signal.get('action') in ['BUY', 'SELL']:
                trade = self._signal_to_trade(result)
                trade_id = self.journal.add_trade(trade)
                trades_created.append({
                    'id': trade_id,
                    'ticker': trade.ticker,
                    'signal': signal['action'],
                    'confidence': signal['confidence']
                })
                logger.info(f"Signal converted to trade: {trade.ticker} {signal['action']} (ID: {trade_id})")
        
        return trades_created
    
    def _signal_to_trade(self, result: dict) -> Trade:
        """Convert a GEX signal result to a Trade object"""
        signal = result['signal']
        tech = result['tech']
        
        direction = TradeDirection.LONG.value if signal['direction'] == 'LONG' else TradeDirection.SHORT.value
        
        # Calculate position size (paper trading default: $1000 per trade)
        position_size = 1000
        quantity = max(1, int(position_size / (signal['price'] * 100)))
        
        # Set stop loss and take profit based on GEX level
        entry = signal['price']
        gex_level = signal.get('target_level', entry)
        
        if direction == TradeDirection.LONG.value:
            # For longs: stop below GEX level, target above
            stop_loss = gex_level * 0.98  # 2% below GEX level
            take_profit = entry * 1.05     # 5% target
        else:
            # For shorts: stop above GEX level, target below
            stop_loss = gex_level * 1.02  # 2% above GEX level
            take_profit = entry * 0.95     # 5% target
        
        return Trade(
            timestamp=signal['timestamp'],
            ticker=result['ticker'],
            direction=direction,
            entry_price=signal['price'],
            quantity=quantity,
            position_size=position_size,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            strategy='gex',
            confidence=signal.get('confidence', 0),
            notes=f"GEX Level: ${signal.get('target_level')} | Reasons: {' | '.join(signal.get('reasons', []))}",
            tags=f"gex,rsi_{tech['rsi']:.0f},{result['ticker']}"
        )
    
    def check_exits(self):
        """Check open positions against stop loss and take profit levels"""
        import yfinance as yf
        
        open_positions = self.journal.get_open_positions()
        
        exits_triggered = []
        for pos in open_positions:
            if pos['strategy'] != 'gex':
                continue  # Only auto-manage GEX trades
            
            try:
                # Get current price
                ticker = yf.Ticker(pos['ticker'])
                current_price = ticker.history(period='1d')['Close'].iloc[-1]
                
                stop = pos.get('stop_loss')
                target = pos.get('take_profit')
                direction = pos['direction']
                
                exit_triggered = False
                exit_reason = None
                
                if direction == TradeDirection.LONG.value:
                    if stop and current_price <= stop:
                        exit_triggered = True
                        exit_reason = f"stop_loss ({current_price:.2f} <= {stop:.2f})"
                    elif target and current_price >= target:
                        exit_triggered = True
                        exit_reason = f"take_profit ({current_price:.2f} >= {target:.2f})"
                else:  # SHORT
                    if stop and current_price >= stop:
                        exit_triggered = True
                        exit_reason = f"stop_loss ({current_price:.2f} >= {stop:.2f})"
                    elif target and current_price <= target:
                        exit_triggered = True
                        exit_reason = f"take_profit ({current_price:.2f} <= {target:.2f})"
                
                if exit_triggered:
                    result = self.journal.close_trade(
                        pos['id'], 
                        current_price, 
                        exit_reason=exit_reason
                    )
                    exits_triggered.append({
                        'trade_id': pos['id'],
                        'ticker': pos['ticker'],
                        'exit_price': current_price,
                        'reason': exit_reason,
                        'pnl': result.get('pnl_absolute')
                    })
                    logger.info(f"Auto-exited {pos['ticker']}: {exit_reason}")
                    
            except Exception as e:
                logger.error(f"Error checking exit for {pos['ticker']}: {e}")
        
        return exits_triggered
    
    def time_based_exit(self, max_hold_hours: float = 24):
        """Close positions held longer than max_hold_hours"""
        open_positions = self.journal.get_open_positions()
        
        from datetime import datetime
        now = datetime.now()
        
        exits = []
        for pos in open_positions:
            entry_time = datetime.fromisoformat(pos['timestamp'].replace('Z', '+00:00'))
            hold_hours = (now - entry_time).total_seconds() / 3600
            
            if hold_hours > max_hold_hours:
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(pos['ticker'])
                    current_price = ticker.history(period='1d')['Close'].iloc[-1]
                    
                    result = self.journal.close_trade(
                        pos['id'],
                        current_price,
                        exit_reason=f"time_exit ({hold_hours:.1f}h > {max_hold_hours}h)"
                    )
                    exits.append({
                        'trade_id': pos['id'],
                        'ticker': pos['ticker'],
                        'hold_time': f"{hold_hours:.1f}h",
                        'pnl': result.get('pnl_absolute')
                    })
                    logger.info(f"Time-exit {pos['ticker']} after {hold_hours:.1f}h")
                except Exception as e:
                    logger.error(f"Error time-exiting {pos['ticker']}: {e}")
        
        return exits

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GEX-Journal Bridge')
    parser.add_argument('--scan', action='store_true', help='Run scan and log signals')
    parser.add_argument('--check-exits', action='store_true', help='Check SL/TP levels')
    parser.add_argument('--time-exit', type=float, help='Time-based exit (hours)')
    
    args = parser.parse_args()
    
    bridge = GEXJournalBridge()
    
    if args.scan:
        print("🔄 Running GEX scan and logging signals...")
        trades = bridge.scan_and_log()
        print(f"✅ Created {len(trades)} trades from signals")
        for t in trades:
            print(f"   ID {t['id']}: {t['ticker']} {t['signal']} ({t['confidence']}% confidence)")
    
    elif args.check_exits:
        print("🔍 Checking stop loss / take profit levels...")
        exits = bridge.check_exits()
        print(f"✅ {len(exits)} positions exited")
        for e in exits:
            print(f"   {e['ticker']}: {e['reason']} | P&L: ${e['pnl']:.2f}")
    
    elif args.time_exit:
        print(f"⏰ Checking positions older than {args.time_exit} hours...")
        exits = bridge.time_based_exit(args.time_exit)
        print(f"✅ {len(exits)} time-based exits")
        for e in exits:
            print(f"   {e['ticker']}: {e['hold_time']} | P&L: ${e['pnl']:.2f}")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
