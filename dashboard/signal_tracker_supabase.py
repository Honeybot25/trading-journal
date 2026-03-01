"""
Signal Tracker Module - Supabase PostgreSQL Version
For serverless deployment on Vercel
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Supabase configuration from environment
SUPABASE_URL = os.environ.get('SUPABASE_URL') or os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY') or os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')

class SignalTrackerSupabase:
    """Track trading signals using Supabase PostgreSQL"""
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                self._init_db()
            except Exception as e:
                print(f"Supabase connection error: {e}")
                self.supabase = None
    
    def _is_available(self) -> bool:
        return self.supabase is not None
    
    def _init_db(self):
        """Initialize database tables - tables should be created in Supabase dashboard"""
        # Tables are created via Supabase SQL Editor or migrations
        # This method just verifies connection
        if self._is_available():
            try:
                # Test connection by querying signals table
                self.supabase.table('signals').select('count', count='exact').limit(0).execute()
            except Exception as e:
                print(f"Supabase init check error: {e}")
    
    def log_signal(self, signal_data: Dict) -> int:
        """Log a new signal to the database"""
        if not self._is_available():
            # Return a mock ID when Supabase is not available
            return int(datetime.now().timestamp())
        
        try:
            data = {
                'ticker': signal_data.get('ticker'),
                'direction': signal_data.get('direction'),
                'entry_price': signal_data.get('entry_price'),
                'confidence': signal_data.get('confidence', 50),
                'signal_type': signal_data.get('signal_type', 'GEX'),
                'stop_loss': signal_data.get('stop_loss'),
                'take_profit': signal_data.get('take_profit'),
                'expected_move': signal_data.get('expected_move'),
                'gex_level': signal_data.get('gex_level'),
                'rsi_value': signal_data.get('rsi_value'),
                'trend_direction': signal_data.get('trend_direction'),
                'status': 'OPEN',
                'notes': signal_data.get('notes', ''),
                'signal_time': datetime.now().isoformat()
            }
            
            result = self.supabase.table('signals').insert(data).execute()
            signal_id = result.data[0]['id'] if result.data else int(datetime.now().timestamp())
            
            # Log conditions if provided
            conditions = signal_data.get('conditions', [])
            if conditions and signal_id:
                for cond in conditions:
                    cond_data = {
                        'signal_id': signal_id,
                        'condition_name': cond.get('name'),
                        'condition_met': cond.get('met', False),
                        'condition_value': cond.get('value', 0),
                        'weight': cond.get('weight', 1)
                    }
                    try:
                        self.supabase.table('signal_conditions').insert(cond_data).execute()
                    except:
                        pass
            
            return signal_id
        except Exception as e:
            print(f"Error logging signal: {e}")
            return int(datetime.now().timestamp())
    
    def update_signal_exit(self, signal_id: int, exit_data: Dict):
        """Update signal with exit information"""
        if not self._is_available():
            return
        
        try:
            data = {
                'status': 'CLOSED',
                'exit_price': exit_data.get('exit_price'),
                'exit_time': datetime.now().isoformat(),
                'exit_reason': exit_data.get('exit_reason', 'UNKNOWN'),
                'pnl': exit_data.get('pnl'),
                'pnl_percent': exit_data.get('pnl_percent'),
                'notes': f"Exit: {exit_data.get('notes', '')}"
            }
            self.supabase.table('signals').update(data).eq('id', signal_id).execute()
        except Exception as e:
            print(f"Error updating signal exit: {e}")
    
    def get_all_signals(self, limit: int = 100, ticker: str = None, 
                        direction: str = None, status: str = None) -> List[Dict]:
        """Get signals with optional filters"""
        if not self._is_available():
            return []
        
        try:
            query = self.supabase.table('signals').select('*')
            
            if ticker:
                query = query.eq('ticker', ticker)
            if direction:
                query = query.eq('direction', direction)
            if status:
                query = query.eq('status', status)
            
            result = query.order('signal_time', desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting signals: {e}")
            return []
    
    def get_open_signals(self) -> List[Dict]:
        """Get currently open signals"""
        return self.get_all_signals(status='OPEN', limit=100)
    
    def get_performance_stats(self) -> Dict:
        """Calculate overall performance statistics"""
        if not self._is_available():
            return {
                'total': 0, 'winners': 0, 'losers': 0, 'open': 0,
                'win_rate': 0, 'total_pnl': 0, 'by_ticker': [],
                'by_direction': [], 'equity_curve': []
            }
        
        try:
            # Get all closed signals for stats
            result = self.supabase.table('signals').select('*').eq('status', 'CLOSED').execute()
            signals = result.data if result.data else []
            
            total = len(signals)
            winners = sum(1 for s in signals if s.get('pnl', 0) > 0)
            losers = sum(1 for s in signals if s.get('pnl', 0) < 0)
            total_pnl = sum(s.get('pnl', 0) or 0 for s in signals)
            
            win_rate = (winners / (winners + losers) * 100) if (winners + losers) > 0 else 0
            
            # By ticker
            by_ticker = {}
            for s in signals:
                ticker = s.get('ticker')
                if ticker not in by_ticker:
                    by_ticker[ticker] = {'count': 0, 'wins': 0, 'pnl': 0}
                by_ticker[ticker]['count'] += 1
                if s.get('pnl', 0) > 0:
                    by_ticker[ticker]['wins'] += 1
                by_ticker[ticker]['pnl'] += s.get('pnl', 0) or 0
            
            by_ticker_list = [{'ticker': k, **v} for k, v in by_ticker.items()]
            by_ticker_list.sort(key=lambda x: x['pnl'], reverse=True)
            
            # By direction
            by_direction = {}
            for s in signals:
                direction = s.get('direction')
                if direction not in by_direction:
                    by_direction[direction] = {'count': 0, 'wins': 0, 'pnl': 0}
                by_direction[direction]['count'] += 1
                if s.get('pnl', 0) > 0:
                    by_direction[direction]['wins'] += 1
                by_direction[direction]['pnl'] += s.get('pnl', 0) or 0
            
            by_direction_list = [{'direction': k, **v} for k, v in by_direction.items()]
            
            # Equity curve
            sorted_signals = sorted([s for s in signals if s.get('pnl') is not None], 
                                   key=lambda x: x.get('signal_time', ''))
            cumulative_pnl = 0
            equity_curve = []
            for s in sorted_signals:
                cumulative_pnl += s.get('pnl', 0) or 0
                equity_curve.append({
                    'date': s.get('signal_time'),
                    'pnl': s.get('pnl'),
                    'cumulative_pnl': round(cumulative_pnl, 2)
                })
            
            return {
                'total': total,
                'winners': winners,
                'losers': losers,
                'closed_signals': winners + losers,
                'open': len(self.get_open_signals()),
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'by_ticker': by_ticker_list,
                'by_direction': by_direction_list,
                'equity_curve': equity_curve
            }
        except Exception as e:
            print(f"Error getting performance stats: {e}")
            return {
                'total': 0, 'winners': 0, 'losers': 0, 'open': 0,
                'win_rate': 0, 'total_pnl': 0, 'by_ticker': [],
                'by_direction': [], 'equity_curve': []
            }
    
    def check_signal_exits(self, current_prices: Dict[str, float]):
        """Check open signals against current prices and close if SL/TP hit"""
        if not self._is_available():
            return
        
        open_signals = self.get_open_signals()
        
        for signal in open_signals:
            ticker = signal.get('ticker')
            if ticker not in current_prices:
                continue
            
            current_price = current_prices[ticker]
            entry = signal.get('entry_price')
            sl = signal.get('stop_loss')
            tp = signal.get('take_profit')
            direction = signal.get('direction')
            signal_time = signal.get('signal_time')
            signal_id = signal.get('id')
            
            if not signal_id or not entry:
                continue
            
            # Parse signal time
            try:
                if isinstance(signal_time, str):
                    signal_dt = datetime.fromisoformat(signal_time.replace('Z', '+00:00'))
                else:
                    signal_dt = datetime.now() - timedelta(hours=1)
            except:
                signal_dt = datetime.now() - timedelta(hours=1)
            
            # Check time exit (24 hours)
            if datetime.now() - signal_dt > timedelta(hours=24):
                pnl = (current_price - entry) if direction == 'CALL' else (entry - current_price)
                pnl_pct = (pnl / entry) * 100 if entry else 0
                self.update_signal_exit(signal_id, {
                    'exit_price': current_price,
                    'exit_reason': 'TIME_EXIT',
                    'pnl': pnl,
                    'pnl_percent': pnl_pct,
                    'notes': '24h time exit'
                })
                continue
            
            # Check stop loss
            if sl:
                if direction == 'CALL' and current_price <= sl:
                    pnl = sl - entry
                    pnl_pct = (pnl / entry) * 100 if entry else 0
                    self.update_signal_exit(signal_id, {
                        'exit_price': sl,
                        'exit_reason': 'SL_HIT',
                        'pnl': pnl,
                        'pnl_percent': pnl_pct,
                        'notes': 'Stop loss triggered'
                    })
                    continue
                elif direction == 'PUT' and current_price >= sl:
                    pnl = entry - sl
                    pnl_pct = (pnl / entry) * 100 if entry else 0
                    self.update_signal_exit(signal_id, {
                        'exit_price': sl,
                        'exit_reason': 'SL_HIT',
                        'pnl': pnl,
                        'pnl_percent': pnl_pct,
                        'notes': 'Stop loss triggered'
                    })
                    continue
            
            # Check take profit
            if tp:
                if direction == 'CALL' and current_price >= tp:
                    pnl = tp - entry
                    pnl_pct = (pnl / entry) * 100 if entry else 0
                    self.update_signal_exit(signal_id, {
                        'exit_price': tp,
                        'exit_reason': 'TP_HIT',
                        'pnl': pnl,
                        'pnl_percent': pnl_pct,
                        'notes': 'Take profit hit'
                    })
                    continue
                elif direction == 'PUT' and current_price <= tp:
                    pnl = entry - tp
                    pnl_pct = (pnl / entry) * 100 if entry else 0
                    self.update_signal_exit(signal_id, {
                        'exit_price': tp,
                        'exit_reason': 'TP_HIT',
                        'pnl': pnl,
                        'pnl_percent': pnl_pct,
                        'notes': 'Take profit hit'
                    })
                    continue


# Global instance
_signal_tracker_supabase = None

def get_signal_tracker_supabase():
    """Get singleton SignalTrackerSupabase instance"""
    global _signal_tracker_supabase
    if _signal_tracker_supabase is None:
        _signal_tracker_supabase = SignalTrackerSupabase()
    return _signal_tracker_supabase
