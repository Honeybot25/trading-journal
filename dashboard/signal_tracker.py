"""
Signal Tracker Module
SQLite database for tracking BUY CALL / BUY PUT signals and calculating win rates
Falls back to Supabase on Vercel serverless environment
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import threading
import numpy as np

# Try to import Supabase version
try:
    from signal_tracker_supabase import get_signal_tracker_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

class SignalTracker:
    """Track trading signals and calculate performance metrics"""
    
    def __init__(self, db_path: str = None):
        # Check if we should use Supabase (Vercel environment with credentials)
        self.use_supabase = False
        self.supabase_tracker = None
        
        if os.environ.get('VERCEL') and SUPABASE_AVAILABLE:
            try:
                self.supabase_tracker = get_signal_tracker_supabase()
                if self.supabase_tracker._is_available():
                    self.use_supabase = True
                    self.db_path = None
                    self._lock = threading.Lock()
                    return
            except Exception as e:
                print(f"Failed to initialize Supabase: {e}")
        
        # Fall back to SQLite
        if db_path is None:
            if os.environ.get('VERCEL'):
                db_path = '/tmp/signals.db'
            else:
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals.db')
        
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
    
    def _get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database tables"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Main signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    direction TEXT NOT NULL,  -- 'CALL' or 'PUT'
                    entry_price REAL NOT NULL,
                    signal_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence INTEGER,
                    signal_type TEXT,  -- 'GEX_RSI', 'GEX_TREND', etc.
                    stop_loss REAL,
                    take_profit REAL,
                    expected_move REAL,
                    gex_level REAL,
                    rsi_value REAL,
                    trend_direction TEXT,
                    status TEXT DEFAULT 'OPEN',  -- 'OPEN', 'CLOSED', 'EXPIRED'
                    exit_price REAL,
                    exit_time TIMESTAMP,
                    exit_reason TEXT,  -- 'SL_HIT', 'TP_HIT', 'TIME_EXIT', 'MANUAL'
                    pnl REAL,
                    pnl_percent REAL,
                    max_profit REAL,
                    max_drawdown REAL,
                    notes TEXT,
                    -- Contract specifications (new fields)
                    contract_strike REAL,
                    contract_expiration TEXT,
                    contract_expiration_days INTEGER,
                    contract_strike_type TEXT,  -- 'ITM', 'ATM', 'OTM'
                    contract_estimated_price REAL,
                    -- Entry/Exit zones (new fields)
                    entry_price_low REAL,
                    entry_price_high REAL,
                    risk_reward_ratio REAL,
                    position_size_risk_pct REAL,
                    max_contracts INTEGER,
                    kelly_fraction REAL,
                    -- Greeks (new fields)
                    greek_delta REAL,
                    greek_gamma REAL,
                    greek_theta REAL,
                    greek_vega REAL,
                    greek_iv REAL,
                    greek_iv_percentile REAL,
                    -- Reasoning (stored as JSON)
                    reasoning_json TEXT,
                    -- Actual performance tracking
                    actual_max_profit REAL,
                    actual_max_drawdown REAL,
                    price_at_expiration REAL,
                    contract_pnl REAL,
                    contract_pnl_percent REAL
                )
            ''')
            
            # Signal conditions table for detailed signal breakdown
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_conditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    condition_name TEXT,
                    condition_met BOOLEAN,
                    condition_value REAL,
                    weight INTEGER,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            ''')
            
            # Price history for tracking exits
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    price REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    signal_id INTEGER,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT CURRENT_DATE,
                    total_signals INTEGER DEFAULT 0,
                    winning_signals INTEGER DEFAULT 0,
                    losing_signals INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    avg_pnl REAL DEFAULT 0,
                    best_trade REAL DEFAULT 0,
                    worst_trade REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)')
            # cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(signal_time)')  # Column may not exist
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_history_signal ON price_history(signal_id)')
            
            conn.commit()
            conn.close()
    
    def log_signal(self, signal_data: Dict) -> int:
        """Log a new signal to the database with contract details"""
        # Use Supabase if available
        if self.use_supabase and self.supabase_tracker:
            return self.supabase_tracker.log_signal(signal_data)
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Extract contract specs
            contract_specs = signal_data.get('contract_specs', {})
            zones = signal_data.get('zones', {})
            greeks = signal_data.get('greeks', {})
            reasoning = signal_data.get('reasoning', {})
            
            cursor.execute('''
                INSERT INTO signals (
                    ticker, direction, entry_price, confidence, signal_type,
                    stop_loss, take_profit, expected_move, gex_level, rsi_value,
                    trend_direction, notes,
                    contract_strike, contract_expiration, contract_expiration_days,
                    contract_strike_type, contract_estimated_price,
                    entry_price_low, entry_price_high, risk_reward_ratio,
                    position_size_risk_pct, max_contracts, kelly_fraction,
                    greek_delta, greek_gamma, greek_theta, greek_vega,
                    greek_iv, greek_iv_percentile, reasoning_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('ticker'),
                signal_data.get('direction'),
                signal_data.get('entry_price'),
                signal_data.get('confidence', 50),
                signal_data.get('signal_type', 'GEX'),
                signal_data.get('stop_loss'),
                signal_data.get('take_profit'),
                signal_data.get('expected_move'),
                signal_data.get('gex_level'),
                signal_data.get('rsi_value'),
                signal_data.get('trend_direction'),
                signal_data.get('notes', ''),
                # Contract specs
                contract_specs.get('strike'),
                contract_specs.get('expiration'),
                contract_specs.get('expiration_days'),
                contract_specs.get('strike_type'),
                contract_specs.get('estimated_price'),
                # Entry/Exit zones
                zones.get('entry_price_low'),
                zones.get('entry_price_high'),
                zones.get('risk_reward_ratio'),
                zones.get('position_size_risk_pct'),
                zones.get('max_contracts'),
                zones.get('kelly_fraction'),
                # Greeks
                greeks.get('delta'),
                greeks.get('gamma'),
                greeks.get('theta'),
                greeks.get('vega'),
                greeks.get('iv'),
                greeks.get('iv_percentile'),
                # Reasoning as JSON
                json.dumps(reasoning) if reasoning else None
            ))
            
            signal_id = cursor.lastrowid
            
            # Log conditions if provided
            conditions = signal_data.get('conditions', [])
            for cond in conditions:
                cursor.execute('''
                    INSERT INTO signal_conditions (signal_id, condition_name, condition_met, condition_value, weight)
                    VALUES (?, ?, ?, ?, ?)
                ''', (signal_id, cond.get('name'), cond.get('met', False), 
                      cond.get('value', 0), cond.get('weight', 1)))
            
            conn.commit()
            conn.close()
            return signal_id
    
    def update_signal_exit(self, signal_id: int, exit_data: Dict):
        """Update signal with exit information including contract P&L"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE signals SET
                    status = 'CLOSED',
                    exit_price = ?,
                    exit_time = CURRENT_TIMESTAMP,
                    exit_reason = ?,
                    pnl = ?,
                    pnl_percent = ?,
                    notes = COALESCE(notes, '') || ?,
                    contract_pnl = ?,
                    contract_pnl_percent = ?,
                    price_at_expiration = ?
                WHERE id = ?
            ''', (
                exit_data.get('exit_price'),
                exit_data.get('exit_reason', 'UNKNOWN'),
                exit_data.get('pnl'),
                exit_data.get('pnl_percent'),
                f" | Exit: {exit_data.get('notes', '')}",
                exit_data.get('contract_pnl'),
                exit_data.get('contract_pnl_percent'),
                exit_data.get('price_at_expiration'),
                signal_id
            ))
            
            conn.commit()
            conn.close()
    
    def update_contract_performance(self, signal_id: int, performance_data: Dict):
        """Update actual contract performance metrics"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE signals SET
                    actual_max_profit = ?,
                    actual_max_drawdown = ?,
                    price_at_expiration = ?,
                    contract_pnl = ?,
                    contract_pnl_percent = ?
                WHERE id = ?
            ''', (
                performance_data.get('actual_max_profit'),
                performance_data.get('actual_max_drawdown'),
                performance_data.get('price_at_expiration'),
                performance_data.get('contract_pnl'),
                performance_data.get('contract_pnl_percent'),
                signal_id
            ))
            
            conn.commit()
            conn.close()
    
    def check_signal_exits(self, current_prices: Dict[str, float]):
        """Check open signals against current prices and close if SL/TP hit"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM signals WHERE status = 'OPEN'
            ''')
            
            open_signals = [dict(row) for row in cursor.fetchall()]
            
            for signal in open_signals:
                ticker = signal['ticker']
                if ticker not in current_prices:
                    continue
                
                current_price = current_prices[ticker]
                entry = signal['entry_price']
                sl = signal.get('stop_loss')
                tp = signal.get('take_profit')
                direction = signal['direction']
                signal_time = datetime.fromisoformat(signal['signal_time'].replace('Z', '+00:00'))
                
                # Check time exit (24 hours)
                if datetime.now() - signal_time > timedelta(hours=24):
                    pnl = (current_price - entry) if direction == 'CALL' else (entry - current_price)
                    pnl_pct = (pnl / entry) * 100
                    self.update_signal_exit(signal['id'], {
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
                        pnl_pct = (pnl / entry) * 100
                        self.update_signal_exit(signal['id'], {
                            'exit_price': sl,
                            'exit_reason': 'SL_HIT',
                            'pnl': pnl,
                            'pnl_percent': pnl_pct,
                            'notes': 'Stop loss triggered'
                        })
                        continue
                    elif direction == 'PUT' and current_price >= sl:
                        pnl = entry - sl
                        pnl_pct = (pnl / entry) * 100
                        self.update_signal_exit(signal['id'], {
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
                        pnl_pct = (pnl / entry) * 100
                        self.update_signal_exit(signal['id'], {
                            'exit_price': tp,
                            'exit_reason': 'TP_HIT',
                            'pnl': pnl,
                            'pnl_percent': pnl_pct,
                            'notes': 'Take profit hit'
                        })
                        continue
                    elif direction == 'PUT' and current_price <= tp:
                        pnl = entry - tp
                        pnl_pct = (pnl / entry) * 100
                        self.update_signal_exit(signal['id'], {
                            'exit_price': tp,
                            'exit_reason': 'TP_HIT',
                            'pnl': pnl,
                            'pnl_percent': pnl_pct,
                            'notes': 'Take profit hit'
                        })
                        continue
            
            conn.close()
    
    def get_all_signals(self, limit: int = 100, ticker: str = None, 
                        direction: str = None, status: str = None) -> List[Dict]:
        """Get signals with optional filters"""
        # Use Supabase if available
        if self.use_supabase and self.supabase_tracker:
            return self.supabase_tracker.get_all_signals(limit, ticker, direction, status)
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM signals WHERE 1=1'
            params = []
            
            if ticker:
                query += ' AND ticker = ?'
                params.append(ticker)
            if direction:
                query += ' AND direction = ?'
                params.append(direction)
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY signal_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            signals = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return signals
    
    def get_performance_stats(self) -> Dict:
        """Calculate overall performance statistics"""
        # Use Supabase if available
        if self.use_supabase and self.supabase_tracker:
            return self.supabase_tracker.get_performance_stats()
        
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
                    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                FROM signals
            ''')
            
            row = cursor.fetchone()
            stats = dict(row) if row else {}
            
            # Calculate win rate
            closed_signals = (stats.get('winners', 0) or 0) + (stats.get('losers', 0) or 0)
            win_rate = ((stats.get('winners', 0) or 0) / closed_signals * 100) if closed_signals > 0 else 0
            stats['win_rate'] = round(win_rate, 2)
            stats['closed_signals'] = closed_signals
            
            # Performance by ticker
            cursor.execute('''
                SELECT 
                    ticker,
                    COUNT(*) as count,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as pnl,
                    AVG(pnl) as avg_pnl
                FROM signals
                WHERE status = 'CLOSED'
                GROUP BY ticker
                ORDER BY pnl DESC
            ''')
            stats['by_ticker'] = [dict(row) for row in cursor.fetchall()]
            
            # Performance by direction (CALL vs PUT)
            cursor.execute('''
                SELECT 
                    direction,
                    COUNT(*) as count,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as pnl,
                    AVG(pnl) as avg_pnl
                FROM signals
                WHERE status = 'CLOSED'
                GROUP BY direction
            ''')
            stats['by_direction'] = [dict(row) for row in cursor.fetchall()]
            
            # Recent signals (last 7 days)
            cursor.execute('''
                SELECT * FROM signals 
                WHERE signal_time >= datetime('now', '-7 days')
                ORDER BY signal_time DESC
            ''')
            stats['recent_signals'] = [dict(row) for row in cursor.fetchall()]
            
            # Equity curve data
            cursor.execute('''
                SELECT signal_time, pnl, pnl_percent
                FROM signals
                WHERE status = 'CLOSED' AND pnl IS NOT NULL
                ORDER BY signal_time
            ''')
            equity_data = cursor.fetchall()
            
            cumulative_pnl = 0
            equity_curve = []
            for row in equity_data:
                cumulative_pnl += row['pnl'] if row['pnl'] else 0
                equity_curve.append({
                    'date': row['signal_time'],
                    'pnl': row['pnl'],
                    'cumulative_pnl': round(cumulative_pnl, 2)
                })
            stats['equity_curve'] = equity_curve
            
            conn.close()
            return stats
    
    def export_to_csv(self, filepath: str):
        """Export all signals to CSV"""
        import pandas as pd
        
        signals = self.get_all_signals(limit=10000)
        df = pd.DataFrame(signals)
        df.to_csv(filepath, index=False)
        return filepath
    
    def get_open_signals(self) -> List[Dict]:
        """Get currently open signals"""
        if self.use_supabase and self.supabase_tracker:
            return self.supabase_tracker.get_open_signals()
        return self.get_all_signals(status='OPEN', limit=100)
    
    def get_daily_summary(self) -> Dict:
        """Get today's signal summary"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_today,
                    SUM(CASE WHEN direction = 'CALL' THEN 1 ELSE 0 END) as calls,
                    SUM(CASE WHEN direction = 'PUT' THEN 1 ELSE 0 END) as puts,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(pnl) as pnl
                FROM signals
                WHERE date(signal_time) = date('now')
            ''')
            
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else {}
    
    def clear_old_signals(self, days: int = 90):
        """Archive signals older than specified days"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM signals
                WHERE signal_time < datetime('now', '-? days')
            ''', (days,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted


# Global signal tracker instance
_signal_tracker = None

def get_signal_tracker() -> SignalTracker:
    """Get singleton SignalTracker instance"""
    global _signal_tracker
    if _signal_tracker is None:
        _signal_tracker = SignalTracker()
    return _signal_tracker


# Signal generation logic
class SignalGenerator:
    """Generate BUY CALL / BUY PUT signals based on GEX, RSI, and trend"""
    
    def __init__(self):
        self.tracker = get_signal_tracker()
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI from price series"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def determine_trend(self, prices: List[float]) -> str:
        """Determine trend direction from price series"""
        if len(prices) < 20:
            return 'NEUTRAL'
        
        # Simple moving average trend
        sma_short = np.mean(prices[-5:])
        sma_long = np.mean(prices[-20:])
        
        if sma_short > sma_long * 1.02:
            return 'BULLISH'
        elif sma_short < sma_long * 0.98:
            return 'BEARISH'
        return 'NEUTRAL'
    
    def generate_signal(self, ticker: str, gex_data: Dict, spot_price: float,
                        price_history: List[float] = None) -> Optional[Dict]:
        """Generate BUY CALL or BUY PUT signal based on conditions"""
        
        total_gex = gex_data.get('total_gex', 0)
        zero_gamma = gex_data.get('zero_gamma_level', spot_price)
        
        # Calculate RSI if price history available
        rsi = None
        if price_history and len(price_history) >= 15:
            rsi = self.calculate_rsi(price_history)
        
        # Determine trend
        trend = 'NEUTRAL'
        if price_history:
            trend = self.determine_trend(price_history)
        
        # Calculate distance from zero gamma
        distance_from_flip = abs(spot_price - zero_gamma) / spot_price * 100
        
        # Initialize conditions
        conditions = []
        confidence = 0
        direction = None
        signal_type = None
        
        # BUY CALL Conditions:
        # 1. Price near positive GEX (within 2% of major positive strike)
        # 2. RSI < 30 (oversold)
        # 3. Bullish trend
        
        call_conditions = {
            'near_positive_gex': False,
            'rsi_oversold': False,
            'bullish_trend': False
        }
        
        # Check for positive GEX support
        net_gex_by_strike = gex_data.get('net_gex_by_strike', [])
        strikes = gex_data.get('strikes', [])
        near_positive_gex = False
        
        for i, strike in enumerate(strikes):
            if i < len(net_gex_by_strike):
                gex = net_gex_by_strike[i]
                distance = abs(spot_price - strike) / spot_price * 100
                if gex > 2.0 and distance < 2.0 and spot_price > strike:
                    near_positive_gex = True
                    call_conditions['near_positive_gex'] = True
                    break
        
        conditions.append({
            'name': 'Near Positive GEX',
            'met': near_positive_gex,
            'value': distance_from_flip,
            'weight': 3
        })
        
        # RSI check
        rsi_oversold = rsi is not None and rsi < 35
        rsi_overbought = rsi is not None and rsi > 65
        
        if rsi is not None:
            conditions.append({
                'name': 'RSI Oversold (< 35)',
                'met': rsi_oversold,
                'value': rsi if rsi else 0,
                'weight': 2
            })
            conditions.append({
                'name': 'RSI Overbought (> 65)',
                'met': rsi_overbought,
                'value': rsi if rsi else 0,
                'weight': 2
            })
        
        # Trend check
        bullish_trend = trend == 'BULLISH'
        bearish_trend = trend == 'BEARISH'
        
        conditions.append({
            'name': 'Bullish Trend',
            'met': bullish_trend,
            'value': 1 if bullish_trend else 0,
            'weight': 2
        })
        conditions.append({
            'name': 'Bearish Trend',
            'met': bearish_trend,
            'value': 1 if bearish_trend else 0,
            'weight': 2
        })
        
        # Calculate expected move (simplified)
        expected_move = spot_price * 0.02  # 2% default
        if total_gex != 0:
            expected_move = spot_price * (0.01 + abs(total_gex) / 100)
        
        # Determine signal
        if near_positive_gex and (rsi_oversold or bullish_trend):
            # BUY CALL signal
            direction = 'CALL'
            signal_type = 'GEX_RSI_BULLISH'
            
            # Calculate confidence
            confidence = 50
            if near_positive_gex:
                confidence += 20
            if rsi_oversold:
                confidence += 15
            if bullish_trend:
                confidence += 15
            
            # Calculate SL/TP
            stop_loss = spot_price * 0.98  # 2% stop
            take_profit = spot_price + expected_move
            
        elif total_gex < -3 and (rsi_overbought or bearish_trend):
            # BUY PUT signal - Price near negative GEX + RSI > 70 + Bearish trend
            near_negative_gex = False
            for i, strike in enumerate(strikes):
                if i < len(net_gex_by_strike):
                    gex = net_gex_by_strike[i]
                    distance = abs(spot_price - strike) / spot_price * 100
                    if gex < -2.0 and distance < 2.0 and spot_price < strike:
                        near_negative_gex = True
                        break
            
            if near_negative_gex:
                direction = 'PUT'
                signal_type = 'GEX_RSI_BEARISH'
                
                confidence = 50
                if near_negative_gex:
                    confidence += 20
                if rsi_overbought:
                    confidence += 15
                if bearish_trend:
                    confidence += 15
                
                stop_loss = spot_price * 1.02  # 2% stop
                take_profit = spot_price - expected_move
        
        if direction and confidence >= 60:
            signal = {
                'ticker': ticker,
                'direction': direction,
                'entry_price': spot_price,
                'confidence': min(confidence, 100),
                'signal_type': signal_type,
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'expected_move': round(expected_move, 2),
                'gex_level': zero_gamma,
                'rsi_value': rsi,
                'trend_direction': trend,
                'conditions': conditions,
                'notes': f"Generated at {datetime.now().strftime('%H:%M:%S')}"
            }
            
            # Log to database
            signal_id = self.tracker.log_signal(signal)
            signal['id'] = signal_id
            
            return signal
        
        return None
