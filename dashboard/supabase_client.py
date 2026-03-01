"""
Supabase Client for Signal Tracking
Handles connection, schema creation, and operations with Supabase PostgreSQL
Gracefully falls back to SQLite if Supabase is unavailable
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('supabase_client')

# Try to import supabase
try:
    from supabase import create_client, Client
    SUPABASE_SDK_AVAILABLE = True
except ImportError:
    SUPABASE_SDK_AVAILABLE = False
    logger.warning("Supabase SDK not installed. Install with: pip install supabase")


@dataclass
class SupabaseConfig:
    """Configuration for Supabase connection"""
    url: str
    anon_key: str
    service_role_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'SupabaseConfig':
        """Load configuration from environment variables"""
        # Try different env var names
        url = os.environ.get('SUPABASE_URL') or os.environ.get('NEXT_PUBLIC_SUPABASE_URL', '')
        anon_key = os.environ.get('SUPABASE_ANON_KEY') or os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY', '')
        service_role_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
        return cls(url=url, anon_key=anon_key, service_role_key=service_role_key)
    
    def is_valid(self) -> bool:
        """Check if configuration is valid (not placeholders)"""
        return (
            self.url and 
            self.anon_key and 
            'your-project' not in self.url and 
            'your-anon-key' not in self.anon_key
        )


class SupabaseSignalTracker:
    """
    Supabase-based signal tracker for persistent storage.
    Mirrors the SQLite SignalTracker interface for easy swapping.
    """
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or SupabaseConfig.from_env()
        self.client: Optional[Client] = None
        self._connected = False
        self._schema_initialized = False
        
        if self.config.is_valid() and SUPABASE_SDK_AVAILABLE:
            self._connect()
    
    def _connect(self) -> bool:
        """Initialize Supabase connection"""
        try:
            if not SUPABASE_SDK_AVAILABLE:
                logger.warning("Supabase SDK not available")
                return False
            
            # Use service role key if available for more permissions
            key = self.config.service_role_key or self.config.anon_key
            self.client = create_client(self.config.url, key)
            
            # Test connection with a simple query
            result = self.client.table('signals').select('count', count='exact').limit(1).execute()
            self._connected = True
            logger.info("✅ Supabase connection established")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Failed to connect to Supabase: {e}")
            self._connected = False
            return False
    
    def is_available(self) -> bool:
        """Check if Supabase is available and connected"""
        return self._connected and self.client is not None
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test connection and return status with message"""
        if not self.config.is_valid():
            return False, "Invalid configuration (placeholder values detected)"
        
        if not SUPABASE_SDK_AVAILABLE:
            return False, "Supabase SDK not installed (pip install supabase)"
        
        if not self._connected:
            return False, "Not connected"
        
        try:
            # Test with a lightweight query
            result = self.client.table('signals').select('id').limit(1).execute()
            return True, f"Connection successful. Schema exists."
        except Exception as e:
            return False, f"Connection test failed: {e}"
    
    def ensure_schema(self) -> bool:
        """Ensure database schema exists. Creates tables if needed."""
        if not self.is_available():
            logger.warning("Cannot create schema - Supabase not available")
            return False
        
        try:
            # Note: Tables should be created via Supabase Dashboard or migrations
            # This method checks if tables exist and logs instructions if not
            
            # Check signals table
            try:
                result = self.client.table('signals').select('id').limit(1).execute()
                logger.info("✅ Signals table exists")
            except Exception as e:
                if 'does not exist' in str(e).lower() or '404' in str(e):
                    logger.error("❌ Signals table does not exist. Run SQL schema below in Supabase SQL Editor:")
                    self._print_schema_sql()
                    return False
                raise
            
            # Check performance_metrics table
            try:
                result = self.client.table('performance_metrics').select('id').limit(1).execute()
                logger.info("✅ Performance metrics table exists")
            except Exception as e:
                if 'does not exist' in str(e).lower() or '404' in str(e):
                    logger.error("❌ Performance metrics table does not exist")
                    return False
                raise
            
            # Check price_history table
            try:
                result = self.client.table('price_history').select('id').limit(1).execute()
                logger.info("✅ Price history table exists")
            except Exception as e:
                if 'does not exist' in str(e).lower() or '404' in str(e):
                    logger.error("❌ Price history table does not exist")
                    return False
                raise
            
            self._schema_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Schema check failed: {e}")
            return False
    
    def _print_schema_sql(self):
        """Print SQL schema for manual creation"""
        sql = """
-- Run this SQL in Supabase SQL Editor to create tables

-- Signals table (main trading signals)
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL,  -- 'CALL' or 'PUT'
    entry_price REAL NOT NULL,
    signal_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
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
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_reason TEXT,  -- 'SL_HIT', 'TP_HIT', 'TIME_EXIT', 'MANUAL'
    pnl REAL,
    pnl_percent REAL,
    max_profit REAL,
    max_drawdown REAL,
    notes TEXT,
    -- Contract specifications
    contract_strike REAL,
    contract_expiration DATE,
    contract_expiration_days INTEGER,
    contract_strike_type TEXT,  -- 'ITM', 'ATM', 'OTM'
    contract_estimated_price REAL,
    -- Entry/Exit zones
    entry_price_low REAL,
    entry_price_high REAL,
    risk_reward_ratio REAL,
    position_size_risk_pct REAL,
    max_contracts INTEGER,
    kelly_fraction REAL,
    -- Greeks
    greek_delta REAL,
    greek_gamma REAL,
    greek_theta REAL,
    greek_vega REAL,
    greek_iv REAL,
    greek_iv_percentile REAL,
    -- Reasoning (stored as JSON)
    reasoning_json JSONB,
    -- Actual performance tracking
    actual_max_profit REAL,
    actual_max_drawdown REAL,
    price_at_expiration REAL,
    contract_pnl REAL,
    contract_pnl_percent REAL,
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    ticker TEXT,
    strategy TEXT,
    total_signals INTEGER DEFAULT 0,
    winning_signals INTEGER DEFAULT 0,
    losing_signals INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    avg_pnl REAL DEFAULT 0,
    avg_pnl_percent REAL DEFAULT 0,
    best_trade REAL DEFAULT 0,
    worst_trade REAL DEFAULT 0,
    avg_win REAL DEFAULT 0,
    avg_loss REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    max_drawdown_percent REAL DEFAULT 0,
    -- Breakdown by direction
    call_signals INTEGER DEFAULT 0,
    call_wins INTEGER DEFAULT 0,
    call_pnl REAL DEFAULT 0,
    put_signals INTEGER DEFAULT 0,
    put_wins INTEGER DEFAULT 0,
    put_pnl REAL DEFAULT 0,
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, ticker, strategy)
);

-- Price history table (for tracking exits)
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    price REAL NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    source TEXT,  -- 'API', 'MANUAL', 'WEBSOCKET'
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Signal conditions table for detailed signal breakdown
CREATE TABLE IF NOT EXISTS signal_conditions (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id) ON DELETE CASCADE,
    condition_name TEXT,
    condition_met BOOLEAN,
    condition_value REAL,
    weight INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_direction ON signals(direction);
CREATE INDEX IF NOT EXISTS idx_signals_signal_time ON signals(signal_time);
CREATE INDEX IF NOT EXISTS idx_price_history_signal ON price_history(signal_id);
CREATE INDEX IF NOT EXISTS idx_price_history_ticker_time ON price_history(ticker, timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_metrics(date);
CREATE INDEX IF NOT EXISTS idx_performance_ticker ON performance_metrics(ticker);

-- Enable Row Level Security (RLS)
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_conditions ENABLE ROW LEVEL SECURITY;

-- Create policy for anonymous access (adjust for your needs)
CREATE POLICY "Allow anonymous read" ON signals FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON signals FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON signals FOR UPDATE USING (true);

CREATE POLICY "Allow anonymous read" ON performance_metrics FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON performance_metrics FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anonymous update" ON performance_metrics FOR UPDATE USING (true);

CREATE POLICY "Allow anonymous read" ON price_history FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON price_history FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous read" ON signal_conditions FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON signal_conditions FOR INSERT WITH CHECK (true);
        """
        print(sql)
    
    # ==================== CRUD Operations ====================
    
    def log_signal(self, signal_data: Dict) -> Optional[int]:
        """Log a new signal to Supabase"""
        if not self.is_available():
            return None
        
        try:
            # Extract nested data
            contract_specs = signal_data.get('contract_specs', {})
            zones = signal_data.get('zones', {})
            greeks = signal_data.get('greeks', {})
            reasoning = signal_data.get('reasoning', {})
            conditions = signal_data.get('conditions', [])
            
            # Build record
            record = {
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
                'notes': signal_data.get('notes', ''),
                'status': 'OPEN',
                # Contract specs
                'contract_strike': contract_specs.get('strike'),
                'contract_expiration': contract_specs.get('expiration'),
                'contract_expiration_days': contract_specs.get('expiration_days'),
                'contract_strike_type': contract_specs.get('strike_type'),
                'contract_estimated_price': contract_specs.get('estimated_price'),
                # Zones
                'entry_price_low': zones.get('entry_price_low'),
                'entry_price_high': zones.get('entry_price_high'),
                'risk_reward_ratio': zones.get('risk_reward_ratio'),
                'position_size_risk_pct': zones.get('position_size_risk_pct'),
                'max_contracts': zones.get('max_contracts'),
                'kelly_fraction': zones.get('kelly_fraction'),
                # Greeks
                'greek_delta': greeks.get('delta'),
                'greek_gamma': greeks.get('gamma'),
                'greek_theta': greeks.get('theta'),
                'greek_vega': greeks.get('vega'),
                'greek_iv': greeks.get('iv'),
                'greek_iv_percentile': greeks.get('iv_percentile'),
                # Reasoning as JSON
                'reasoning_json': json.dumps(reasoning) if reasoning else None
            }
            
            # Remove None values for clean insert
            record = {k: v for k, v in record.items() if v is not None}
            
            # Insert signal
            result = self.client.table('signals').insert(record).execute()
            signal_id = result.data[0]['id'] if result.data else None
            
            # Insert conditions if any
            if signal_id and conditions:
                conditions_records = [
                    {
                        'signal_id': signal_id,
                        'condition_name': cond.get('name'),
                        'condition_met': cond.get('met', False),
                        'condition_value': cond.get('value', 0),
                        'weight': cond.get('weight', 1)
                    }
                    for cond in conditions
                ]
                self.client.table('signal_conditions').insert(conditions_records).execute()
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
            return None
    
    def update_signal_exit(self, signal_id: int, exit_data: Dict) -> bool:
        """Update signal with exit information"""
        if not self.is_available():
            return False
        
        try:
            update = {
                'status': 'CLOSED',
                'exit_price': exit_data.get('exit_price'),
                'exit_time': datetime.now().isoformat(),
                'exit_reason': exit_data.get('exit_reason', 'UNKNOWN'),
                'pnl': exit_data.get('pnl'),
                'pnl_percent': exit_data.get('pnl_percent'),
                'contract_pnl': exit_data.get('contract_pnl'),
                'contract_pnl_percent': exit_data.get('contract_pnl_percent'),
                'price_at_expiration': exit_data.get('price_at_expiration'),
                'updated_at': datetime.now().isoformat()
            }
            
            # Remove None values
            update = {k: v for k, v in update.items() if v is not None}
            
            # Append to notes if provided
            if exit_data.get('notes'):
                current = self.client.table('signals').select('notes').eq('id', signal_id).execute()
                current_notes = current.data[0].get('notes', '') if current.data else ''
                update['notes'] = f"{current_notes} | Exit: {exit_data.get('notes', '')}".strip()
            
            self.client.table('signals').update(update).eq('id', signal_id).execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update signal exit: {e}")
            return False
    
    def update_contract_performance(self, signal_id: int, performance_data: Dict) -> bool:
        """Update actual contract performance metrics"""
        if not self.is_available():
            return False
        
        try:
            update = {
                'actual_max_profit': performance_data.get('actual_max_profit'),
                'actual_max_drawdown': performance_data.get('actual_max_drawdown'),
                'price_at_expiration': performance_data.get('price_at_expiration'),
                'contract_pnl': performance_data.get('contract_pnl'),
                'contract_pnl_percent': performance_data.get('contract_pnl_percent'),
                'updated_at': datetime.now().isoformat()
            }
            update = {k: v for k, v in update.items() if v is not None}
            
            self.client.table('signals').update(update).eq('id', signal_id).execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update contract performance: {e}")
            return False
    
    def get_all_signals(self, limit: int = 100, ticker: str = None, 
                        direction: str = None, status: str = None) -> List[Dict]:
        """Get signals with optional filters"""
        if not self.is_available():
            return []
        
        try:
            query = self.client.table('signals').select('*').order('signal_time', desc=True).limit(limit)
            
            if ticker:
                query = query.eq('ticker', ticker)
            if direction:
                query = query.eq('direction', direction)
            if status:
                query = query.eq('status', status)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get signals: {e}")
            return []
    
    def get_open_signals(self) -> List[Dict]:
        """Get currently open signals"""
        return self.get_all_signals(limit=1000, status='OPEN')
    
    def get_performance_stats(self) -> Dict:
        """Calculate overall performance statistics"""
        if not self.is_available():
            return {}
        
        try:
            # Get all closed signals for stats calculation
            result = self.client.table('signals').select('*').eq('status', 'CLOSED').execute()
            signals = result.data if result.data else []
            
            if not signals:
                return {
                    'total_signals': 0,
                    'winners': 0,
                    'losers': 0,
                    'open_signals': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'by_ticker': [],
                    'by_direction': [],
                    'equity_curve': []
                }
            
            # Calculate stats
            total = len(signals)
            winners = sum(1 for s in signals if s.get('pnl', 0) > 0)
            losers = sum(1 for s in signals if s.get('pnl', 0) < 0)
            total_pnl = sum(s.get('pnl', 0) or 0 for s in signals)
            avg_pnl = total_pnl / total if total > 0 else 0
            best_trade = max(s.get('pnl', 0) or 0 for s in signals)
            worst_trade = min(s.get('pnl', 0) or 0 for s in signals)
            
            # Win rate
            win_rate = (winners / (winners + losers) * 100) if (winners + losers) > 0 else 0
            
            # Get open signals count
            open_result = self.client.table('signals').select('id', count='exact').eq('status', 'OPEN').execute()
            open_count = open_result.count if hasattr(open_result, 'count') else 0
            
            # Performance by ticker
            ticker_stats = {}
            for s in signals:
                t = s.get('ticker')
                if t not in ticker_stats:
                    ticker_stats[t] = {'count': 0, 'wins': 0, 'pnl': 0}
                ticker_stats[t]['count'] += 1
                if s.get('pnl', 0) > 0:
                    ticker_stats[t]['wins'] += 1
                ticker_stats[t]['pnl'] += s.get('pnl', 0) or 0
            
            by_ticker = [
                {'ticker': t, **stats}
                for t, stats in sorted(ticker_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
            ]
            
            # Performance by direction
            direction_stats = {}
            for s in signals:
                d = s.get('direction')
                if d not in direction_stats:
                    direction_stats[d] = {'count': 0, 'wins': 0, 'pnl': 0}
                direction_stats[d]['count'] += 1
                if s.get('pnl', 0) > 0:
                    direction_stats[d]['wins'] += 1
                direction_stats[d]['pnl'] += s.get('pnl', 0) or 0
            
            by_direction = [
                {'direction': d, **stats}
                for d, stats in direction_stats.items()
            ]
            
            # Equity curve
            sorted_signals = sorted(signals, key=lambda x: x.get('signal_time', ''))
            cumulative_pnl = 0
            equity_curve = []
            for s in sorted_signals:
                pnl = s.get('pnl', 0) or 0
                cumulative_pnl += pnl
                equity_curve.append({
                    'date': s.get('signal_time'),
                    'pnl': pnl,
                    'cumulative_pnl': round(cumulative_pnl, 2)
                })
            
            return {
                'total_signals': total,
                'winners': winners,
                'losers': losers,
                'open_signals': open_count,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl': round(avg_pnl, 2),
                'best_trade': round(best_trade, 2),
                'worst_trade': round(worst_trade, 2),
                'by_ticker': by_ticker,
                'by_direction': by_direction,
                'equity_curve': equity_curve
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {}
    
    def record_price(self, ticker: str, price: float, signal_id: int = None, 
                     source: str = 'API', metadata: Dict = None) -> bool:
        """Record price point to history"""
        if not self.is_available():
            return False
        
        try:
            record = {
                'ticker': ticker,
                'price': price,
                'signal_id': signal_id,
                'source': source,
                'metadata': json.dumps(metadata) if metadata else None
            }
            record = {k: v for k, v in record.items() if v is not None}
            
            self.client.table('price_history').insert(record).execute()
            return True
            
        except Exception as e:
            logger.error(f"Failed to record price: {e}")
            return False
    
    def get_daily_summary(self) -> Dict:
        """Get today's signal summary"""
        if not self.is_available():
            return {}
        
        try:
            today = datetime.now().date().isoformat()
            
            result = self.client.table('signals').select('*').gte('signal_time', today).execute()
            signals = result.data if result.data else []
            
            return {
                'total_today': len(signals),
                'calls': sum(1 for s in signals if s.get('direction') == 'CALL'),
                'puts': sum(1 for s in signals if s.get('direction') == 'PUT'),
                'winners': sum(1 for s in signals if s.get('pnl', 0) > 0),
                'pnl': round(sum(s.get('pnl', 0) or 0 for s in signals), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get daily summary: {e}")
            return {}
    
    def update_performance_metrics(self, date: str = None, ticker: str = None, 
                                   strategy: str = None, metrics: Dict = None) -> bool:
        """Update or create performance metrics record"""
        if not self.is_available():
            return False
        
        try:
            if date is None:
                date = datetime.now().date().isoformat()
            
            record = {
                'date': date,
                'ticker': ticker or 'ALL',
                'strategy': strategy or 'ALL',
                **(metrics or {}),
                'updated_at': datetime.now().isoformat()
            }
            
            # Upsert logic
            existing = self.client.table('performance_metrics').select('id')\
                .eq('date', date).eq('ticker', ticker or 'ALL').eq('strategy', strategy or 'ALL').execute()
            
            if existing.data:
                # Update
                self.client.table('performance_metrics').update(record)\
                    .eq('id', existing.data[0]['id']).execute()
            else:
                # Insert
                self.client.table('performance_metrics').insert(record).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")
            return False


# Global instance
_supabase_tracker = None

def get_supabase_tracker(config: Optional[SupabaseConfig] = None) -> SupabaseSignalTracker:
    """Get singleton SupabaseSignalTracker instance"""
    global _supabase_tracker
    if _supabase_tracker is None:
        _supabase_tracker = SupabaseSignalTracker(config)
    return _supabase_tracker


def test_supabase_connection() -> Tuple[bool, str]:
    """Test Supabase connection and return status"""
    tracker = get_supabase_tracker()
    return tracker.test_connection()


def init_supabase_schema() -> bool:
    """Initialize/check Supabase schema"""
    tracker = get_supabase_tracker()
    return tracker.ensure_schema()


# ==================== Testing ====================

if __name__ == '__main__':
    print("🧪 Testing Supabase Signal Tracker...")
    
    # Load config
    config = SupabaseConfig.from_env()
    print(f"\n📋 Configuration:")
    print(f"   URL: {config.url[:40]}..." if config.url else "   URL: Not set")
    print(f"   Valid: {config.is_valid()}")
    
    # Test connection
    tracker = SupabaseSignalTracker(config)
    success, message = tracker.test_connection()
    print(f"\n🔌 Connection Test: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"   Message: {message}")
    
    if success:
        # Test schema
        print("\n📊 Schema Check:")
        schema_ok = tracker.ensure_schema()
        print(f"   Result: {'✅ OK' if schema_ok else '⚠️ Needs Setup'}")
        
        if schema_ok:
            # Test insert
            print("\n📝 Test Signal Insert:")
            test_signal = {
                'ticker': 'TEST',
                'direction': 'CALL',
                'entry_price': 100.0,
                'confidence': 75,
                'signal_type': 'TEST',
                'stop_loss': 98.0,
                'take_profit': 105.0,
                'notes': 'Test signal from schema validation'
            }
            signal_id = tracker.log_signal(test_signal)
            print(f"   Signal ID: {signal_id}")
            
            if signal_id:
                # Test retrieval
                print("\n🔍 Test Signal Retrieval:")
                signals = tracker.get_all_signals(limit=5)
                print(f"   Retrieved {len(signals)} signals")
                
                # Cleanup
                print("\n🧹 Cleanup test data...")
                tracker.client.table('signals').delete().eq('id', signal_id).execute()
                print("   ✅ Test signal deleted")
    
    print("\n✨ Test complete!")
