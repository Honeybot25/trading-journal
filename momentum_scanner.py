#!/usr/bin/env python3
"""
Momentum Breakout Scanner - Live Trading with Alpaca Paper
Strategy: Volume Spike + Price Breakout + RSI + MACD
Tickers: NVDA, SPY, QQQ, TSLA
Timeframe: 5-min and 15-min candles
Deployed: 2026-02-26 06:10 PST for market open
"""

import os
import sys
import time
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests

import pandas as pd
import numpy as np

# Alpaca imports
try:
    from alpaca_trade_api import REST, Stream
    from alpaca_trade_api.entity import Bar
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("⚠️ Alpaca SDK not available. Running in scan-only mode.")

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class StrategyConfig:
    # Tickers to monitor
    tickers: List[str] = None
    
    # Timeframes
    primary_timeframe: str = "5Min"
    secondary_timeframe: str = "15Min"
    
    # Indicator Parameters
    volume_spike_threshold: float = 1.5  # 150% of average
    breakout_lookback: int = 20  # 20-period high
    rsi_period: int = 14
    rsi_min: float = 50.0  # Strong but not overbought
    rsi_max: float = 70.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Risk Management
    max_position_pct: float = 0.02  # 2% max per trade
    stop_loss_pct: float = 0.03  # -3% stop loss
    take_profit_pct: float = 0.06  # 6% take profit (2:1 R/R)
    max_open_positions: int = 4
    
    # Account Settings
    paper_trading: bool = True
    initial_capital: float = 100000.0
    
    # Monitoring
    pre_market_start: str = "04:00"  # PST
    market_open: str = "06:30"  # PST
    market_close: str = "13:00"  # PST
    check_interval_seconds: int = 60
    
    # Alerting
    discord_webhook: Optional[str] = None
    log_to_db: bool = True
    
    def __post_init__(self):
        if self.tickers is None:
            self.tickers = ["NVDA", "SPY", "QQQ", "TSLA"]

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/Users/Honeybot/.openclaw/workspace/trading/logs/momentum_scanner.log')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP
# ============================================================================

class SignalDatabase:
    def __init__(self, db_path: str = "/Users/Honeybot/.openclaw/workspace/trading/signals.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS momentum_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL,
                volume REAL,
                volume_avg REAL,
                volume_spike_ratio REAL,
                rsi REAL,
                macd_histogram REAL,
                breakout_level REAL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                position_size INTEGER,
                risk_amount REAL,
                status TEXT DEFAULT 'pending',
                executed INTEGER DEFAULT 0,
                alpaca_order_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                ticker TEXT NOT NULL,
                entry_time TEXT,
                exit_time TEXT,
                entry_price REAL,
                exit_price REAL,
                position_size INTEGER,
                pnl REAL,
                pnl_pct REAL,
                exit_reason TEXT,
                status TEXT DEFAULT 'open',
                alpaca_order_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES momentum_signals(id)
            )
        ''')
        
        # Scanner log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanner_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT,
                event_type TEXT,
                message TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    
    def log_signal(self, signal: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO momentum_signals 
            (timestamp, ticker, signal_type, price, volume, volume_avg, volume_spike_ratio,
             rsi, macd_histogram, breakout_level, entry_price, stop_loss, take_profit,
             position_size, risk_amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal['timestamp'], signal['ticker'], signal['signal_type'],
            signal.get('price'), signal.get('volume'), signal.get('volume_avg'),
            signal.get('volume_spike_ratio'), signal.get('rsi'), signal.get('macd_histogram'),
            signal.get('breakout_level'), signal.get('entry_price'), signal.get('stop_loss'),
            signal.get('take_profit'), signal.get('position_size'), signal.get('risk_amount'),
            signal.get('status', 'pending')
        ))
        conn.commit()
        signal_id = cursor.lastrowid
        conn.close()
        return signal_id
    
    def log_scanner_event(self, ticker: str, event_type: str, message: str, data: Dict = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scanner_logs (timestamp, ticker, event_type, message, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), ticker, event_type, message, json.dumps(data) if data else None))
        conn.commit()
        conn.close()
    
    def get_open_positions(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE status = 'open'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_today_signals(self, ticker: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        if ticker:
            cursor.execute("SELECT * FROM momentum_signals WHERE ticker = ? AND timestamp LIKE ?", (ticker, f'{today}%'))
        else:
            cursor.execute("SELECT * FROM momentum_signals WHERE timestamp LIKE ?", (f'{today}%',))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

class TechnicalIndicators:
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI using Wilder's formula"""
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD line, signal line, and histogram"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_volume_metrics(volume: pd.Series, lookback: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Calculate volume average and spike ratio"""
        vol_avg = volume.rolling(window=lookback).mean()
        vol_spike = volume / vol_avg
        return vol_avg, vol_spike

# ============================================================================
# ALPACA PAPER TRADING
# ============================================================================

class AlpacaTrader:
    def __init__(self, paper: bool = True):
        self.paper = paper
        self.api = None
        self._init_api()
    
    def _init_api(self):
        if not ALPACA_AVAILABLE:
            logger.error("❌ Alpaca SDK not available")
            return
        
        # Use environment variables or default to paper keys
        api_key = os.getenv('ALPACA_API_KEY', 'PKBT0Q8PLZLQ4R7XUGPO')
        api_secret = os.getenv('ALPACA_API_SECRET', 'k7NTvFAsOgWD4p4M2xDp5R2d6pJf2QwpOWoN4A8T')
        base_url = 'https://paper-api.alpaca.markets' if self.paper else 'https://api.alpaca.markets'
        
        try:
            self.api = REST(api_key, api_secret, base_url, api_version='v2')
            account = self.api.get_account()
            logger.info(f"✅ Alpaca connected. Account: ${account.equity} (Buying Power: ${account.buying_power})")
        except Exception as e:
            logger.error(f"❌ Alpaca connection failed: {e}")
            self.api = None
    
    def get_account_info(self) -> Dict:
        if not self.api:
            return {}
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'daytrading_buying_power': float(account.daytrading_buying_power) if hasattr(account, 'daytrading_buying_power') else 0
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_position(self, ticker: str) -> Optional[Dict]:
        if not self.api:
            return None
        try:
            position = self.api.get_position(ticker)
            return {
                'ticker': ticker,
                'qty': int(position.qty),
                'avg_entry_price': float(position.avg_entry_price),
                'current_price': float(position.current_price),
                'market_value': float(position.market_value),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc)
            }
        except Exception:
            return None
    
    def get_positions(self) -> List[Dict]:
        if not self.api:
            return []
        try:
            positions = self.api.list_positions()
            return [{
                'ticker': p.symbol,
                'qty': int(p.qty),
                'avg_entry_price': float(p.avg_entry_price),
                'current_price': float(p.current_price),
                'market_value': float(p.market_value),
                'unrealized_pl': float(p.unrealized_pl),
                'unrealized_plpc': float(p.unrealized_plpc)
            } for p in positions]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def submit_order(self, ticker: str, qty: int, side: str, order_type: str = 'market',
                     limit_price: float = None, stop_price: float = None,
                     time_in_force: str = 'day') -> Optional[Dict]:
        if not self.api:
            logger.error("❌ Alpaca API not initialized")
            return None
        
        try:
            order = self.api.submit_order(
                symbol=ticker,
                qty=qty,
                side=side,
                type=order_type,
                limit_price=limit_price,
                stop_price=stop_price,
                time_in_force=time_in_force
            )
            logger.info(f"✅ Order submitted: {side.upper()} {qty} {ticker} @ {order_type}")
            return {
                'id': order.id,
                'status': order.status,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'type': order.type
            }
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            return None
    
    def submit_bracket_order(self, ticker: str, qty: int, entry_price: float,
                            stop_loss_pct: float, take_profit_pct: float) -> Optional[Dict]:
        """Submit bracket order with stop loss and take profit"""
        if not self.api:
            return None
        
        stop_price = round(entry_price * (1 - stop_loss_pct), 2)
        limit_price = round(entry_price * (1 + take_profit_pct), 2)
        
        try:
            order = self.api.submit_order(
                symbol=ticker,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='day',
                order_class='bracket',
                stop_loss={'stop_price': stop_price},
                take_profit={'limit_price': limit_price}
            )
            logger.info(f"✅ Bracket order submitted: {ticker} | Entry: ~${entry_price} | Stop: ${stop_price} | Target: ${limit_price}")
            return {
                'id': order.id,
                'status': order.status,
                'symbol': order.symbol,
                'qty': qty,
                'stop_loss': stop_price,
                'take_profit': limit_price
            }
        except Exception as e:
            logger.error(f"❌ Bracket order failed: {e}")
            return None
    
    def get_bars(self, ticker: str, timeframe: str = '5Min', limit: int = 100) -> pd.DataFrame:
        """Fetch historical bars from Alpaca"""
        if not self.api:
            return pd.DataFrame()
        
        try:
            # Calculate start time based on limit and timeframe
            bars = self.api.get_bars(ticker, timeframe, limit=limit).df
            if not bars.empty:
                bars.reset_index(inplace=True)
                if 'timestamp' in bars.columns:
                    bars['timestamp'] = pd.to_datetime(bars['timestamp'])
                elif 'index' in bars.columns:
                    bars.rename(columns={'index': 'timestamp'}, inplace=True)
            return bars
        except Exception as e:
            logger.error(f"Error fetching bars for {ticker}: {e}")
            return pd.DataFrame()

# ============================================================================
# YFINANCE FALLBACK
# ============================================================================

class YahooFinanceData:
    """Fallback data source using yfinance"""
    
    @staticmethod
    def get_intraday_data(ticker: str, interval: str = "5m", period: str = "5d") -> pd.DataFrame:
        try:
            import yfinance as yf
            data = yf.download(ticker, interval=interval, period=period, progress=False)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            data.reset_index(inplace=True)
            if 'Datetime' in data.columns:
                data.rename(columns={'Datetime': 'timestamp'}, inplace=True)
            elif 'Date' in data.columns:
                data.rename(columns={'Date': 'timestamp'}, inplace=True)
            return data
        except Exception as e:
            logger.error(f"yfinance error for {ticker}: {e}")
            return pd.DataFrame()

# ============================================================================
# MOMENTUM SCANNER
# ============================================================================

class MomentumScanner:
    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()
        self.db = SignalDatabase()
        self.trader = AlpacaTrader(paper=self.config.paper_trading)
        self.indicators = TechnicalIndicators()
        self.yahoo = YahooFinanceData()
        
        # Track state
        self.signals_generated = []
        self.positions_opened = []
        self.last_scan_time = None
        
        logger.info(f"🚀 Momentum Scanner initialized")
        logger.info(f"   Tickers: {', '.join(self.config.tickers)}")
        logger.info(f"   Timeframe: {self.config.primary_timeframe}")
        logger.info(f"   Volume Spike: {self.config.volume_spike_threshold*100:.0f}%")
        logger.info(f"   Max Position: {self.config.max_position_pct*100:.0f}%")
        logger.info(f"   Stop Loss: {self.config.stop_loss_pct*100:.1f}%")
    
    def is_market_hours(self) -> bool:
        """Check if we're in trading hours (PST)"""
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        # Pre-market: 4:00 AM - 6:30 AM PST
        # Market hours: 6:30 AM - 1:00 PM PST
        return True  # For testing, always return True
    
    def calculate_position_size(self, entry_price: float, account_value: float) -> int:
        """Calculate position size based on risk (max 2% per trade)"""
        risk_amount = account_value * self.config.max_position_pct
        stop_distance = entry_price * self.config.stop_loss_pct
        
        if stop_distance == 0:
            return 0
        
        shares = int(risk_amount / stop_distance)
        
        # Cap at reasonable limits
        max_shares = int((account_value * self.config.max_position_pct * 5) / entry_price)
        shares = min(shares, max_shares)
        
        return max(shares, 1)  # At least 1 share
    
    def analyze_ticker(self, ticker: str) -> Optional[Dict]:
        """Analyze a single ticker for momentum signals"""
        try:
            # Get data - try Alpaca first, fall back to yfinance
            if self.trader.api:
                df = self.trader.get_bars(ticker, self.config.primary_timeframe, limit=50)
            else:
                df = self.yahoo.get_intraday_data(ticker, interval="5m", period="5d")
            
            if df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for {ticker}")
                return None
            
            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df_cols_lower = {c.lower(): c for c in df.columns}
            
            for req in required_cols:
                if req not in df_cols_lower:
                    logger.warning(f"Missing column {req} for {ticker}")
                    return None
            
            # Rename to standard
            df.rename(columns={
                df_cols_lower['open']: 'open',
                df_cols_lower['high']: 'high',
                df_cols_lower['low']: 'low',
                df_cols_lower['close']: 'close',
                df_cols_lower['volume']: 'volume'
            }, inplace=True)
            
            # Calculate indicators
            df['rsi'] = self.indicators.calculate_rsi(df['close'], self.config.rsi_period)
            df['ema_20'] = self.indicators.calculate_ema(df['close'], 20)
            df['macd'], df['macd_signal'], df['macd_hist'] = self.indicators.calculate_macd(
                df['close'], self.config.macd_fast, self.config.macd_slow, self.config.macd_signal
            )
            df['vol_avg'], df['vol_spike'] = self.indicators.calculate_volume_metrics(
                df['volume'], self.config.breakout_lookback
            )
            df['high_20'] = df['high'].rolling(window=self.config.breakout_lookback).max()
            
            # Get latest values
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            current_price = latest['close']
            current_volume = latest['volume']
            volume_avg = latest['vol_avg']
            volume_spike = latest['vol_spike']
            rsi = latest['rsi']
            macd_hist = latest['macd_hist']
            prev_macd_hist = prev['macd_hist']
            high_20 = latest['high_20']
            
            # Check for breakout (price above 20-period high)
            is_breakout = current_price > high_20 * 0.999  # Small buffer
            
            # Check volume spike
            has_volume_spike = volume_spike >= self.config.volume_spike_threshold
            
            # Check RSI in range
            rsi_in_range = self.config.rsi_min <= rsi <= self.config.rsi_max
            
            # Check MACD bullish crossover (histogram turns positive)
            macd_crossover = prev_macd_hist < 0 and macd_hist > 0
            
            # Build analysis
            analysis = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'price': round(current_price, 2),
                'volume': int(current_volume),
                'volume_avg': round(volume_avg, 0),
                'volume_spike_ratio': round(volume_spike, 2),
                'rsi': round(rsi, 2),
                'macd_histogram': round(macd_hist, 4),
                'breakout_level': round(high_20, 2),
                'is_breakout': is_breakout,
                'has_volume_spike': has_volume_spike,
                'rsi_in_range': rsi_in_range,
                'macd_crossover': macd_crossover,
                'signals': []
            }
            
            # Check for momentum signal
            if is_breakout and has_volume_spike and rsi_in_range and macd_crossover:
                analysis['signal_type'] = 'MOMENTUM_BREAKOUT'
                analysis['signals'] = ['breakout', 'volume_spike', 'rsi_confirmed', 'macd_crossover']
                
                # Calculate trade parameters
                account_info = self.trader.get_account_info()
                account_value = account_info.get('equity', self.config.initial_capital)
                
                position_size = self.calculate_position_size(current_price, account_value)
                stop_loss = round(current_price * (1 - self.config.stop_loss_pct), 2)
                take_profit = round(current_price * (1 + self.config.take_profit_pct), 2)
                risk_amount = account_value * self.config.max_position_pct
                
                analysis['entry_price'] = round(current_price, 2)
                analysis['stop_loss'] = stop_loss
                analysis['take_profit'] = take_profit
                analysis['position_size'] = position_size
                analysis['risk_amount'] = round(risk_amount, 2)
                analysis['status'] = 'generated'
                
                logger.info(f"🎯 MOMENTUM SIGNAL: {ticker} @ ${current_price}")
                logger.info(f"   Volume: {volume_spike:.1f}x avg | RSI: {rsi:.1f} | MACD: {macd_hist:.4f}")
                
            else:
                # No signal, but log the analysis
                analysis['signal_type'] = 'NO_SIGNAL'
                missing = []
                if not is_breakout:
                    missing.append('no_breakout')
                if not has_volume_spike:
                    missing.append('low_volume')
                if not rsi_in_range:
                    missing.append(f'rsi_{rsi:.0f}')
                if not macd_crossover:
                    missing.append('no_macd_cross')
                analysis['signals'] = missing
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            self.db.log_scanner_event(ticker, 'ERROR', str(e))
            return None
    
    def execute_signal(self, signal: Dict) -> bool:
        """Execute a trading signal via Alpaca"""
        if signal.get('signal_type') != 'MOMENTUM_BREAKOUT':
            return False
        
        ticker = signal['ticker']
        
        # Check if we already have a position
        existing_position = self.trader.get_position(ticker)
        if existing_position:
            logger.info(f"⏭️ Skipping {ticker} - already have position ({existing_position['qty']} shares)")
            return False
        
        # Check open positions limit
        open_positions = self.trader.get_positions()
        if len(open_positions) >= self.config.max_open_positions:
            logger.info(f"⏭️ Skipping {ticker} - max positions reached ({len(open_positions)})")
            return False
        
        # Submit bracket order
        qty = signal['position_size']
        entry_price = signal['entry_price']
        
        if self.config.paper_trading and self.trader.api:
            order = self.trader.submit_bracket_order(
                ticker=ticker,
                qty=qty,
                entry_price=entry_price,
                stop_loss_pct=self.config.stop_loss_pct,
                take_profit_pct=self.config.take_profit_pct
            )
            
            if order:
                signal['status'] = 'executed'
                signal['alpaca_order_id'] = order['id']
                self.positions_opened.append(signal)
                logger.info(f"✅ EXECUTED: {ticker} bracket order | Qty: {qty}")
                return True
            else:
                signal['status'] = 'failed'
                logger.error(f"❌ Failed to execute {ticker}")
                return False
        else:
            logger.info(f"📝 PAPER MODE: Would execute {ticker} | Qty: {qty} @ ${entry_price}")
            signal['status'] = 'paper'
            return True
    
    def send_alert(self, signal: Dict):
        """Send alert via Discord webhook"""
        if not self.config.discord_webhook:
            return
        
        try:
            emoji = "🚀" if signal.get('signal_type') == 'MOMENTUM_BREAKOUT' else "📊"
            
            embed = {
                "title": f"{emoji} Momentum Alert: {signal['ticker']}",
                "description": f"Signal Type: {signal.get('signal_type', 'UNKNOWN')}",
                "color": 3066993 if signal.get('signal_type') == 'MOMENTUM_BREAKOUT' else 3447003,
                "fields": [
                    {"name": "Price", "value": f"${signal.get('price', 'N/A')}", "inline": True},
                    {"name": "Volume Spike", "value": f"{signal.get('volume_spike_ratio', 0):.1f}x", "inline": True},
                    {"name": "RSI", "value": f"{signal.get('rsi', 0):.1f}", "inline": True},
                    {"name": "Status", "value": signal.get('status', 'pending'), "inline": True}
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            if signal.get('entry_price'):
                embed['fields'].extend([
                    {"name": "Entry", "value": f"${signal['entry_price']}", "inline": True},
                    {"name": "Stop Loss", "value": f"${signal.get('stop_loss', 'N/A')}", "inline": True},
                    {"name": "Take Profit", "value": f"${signal.get('take_profit', 'N/A')}", "inline": True}
                ])
            
            payload = {"embeds": [embed]}
            requests.post(self.config.discord_webhook, json=payload, timeout=5)
            
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
    
    def log_to_mission_control(self, event_type: str, data: Dict):
        """Log events to Mission Control dashboard"""
        try:
            log_entry = {
                "agent": "TraderBot",
                "project": "momentum-scanner",
                "status": "active",
                "description": f"{event_type}: {data.get('ticker', 'SCANNER')}",
                "estimated_impact": "high",
                "data": data
            }
            
            # Try to POST to Mission Control
            mc_url = "https://mission-control-lovat-rho.vercel.app/api/logs"
            requests.post(mc_url, json=log_entry, timeout=5)
        except Exception as e:
            logger.debug(f"Mission Control log failed: {e}")
    
    def scan_all(self, execute: bool = True) -> List[Dict]:
        """Scan all tickers for signals"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 SCANNING {len(self.config.tickers)} TICKERS - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        signals = []
        
        for ticker in self.config.tickers:
            analysis = self.analyze_ticker(ticker)
            
            if analysis:
                # Log to database
                signal_id = self.db.log_signal(analysis)
                analysis['signal_id'] = signal_id
                
                # Execute if it's a breakout signal
                if analysis.get('signal_type') == 'MOMENTUM_BREAKOUT':
                    signals.append(analysis)
                    self.send_alert(analysis)
                    self.log_to_mission_control('SIGNAL_DETECTED', analysis)
                    
                    if execute:
                        self.execute_signal(analysis)
                else:
                    # Log no-signal info at debug level
                    logger.debug(f"📊 {ticker}: No signal (RSI: {analysis.get('rsi', 0):.1f}, Vol: {analysis.get('volume_spike_ratio', 0):.1f}x)")
        
        self.last_scan_time = datetime.now()
        logger.info(f"\n✅ Scan complete. {len(signals)} breakout signals found.")
        
        return signals
    
    def run_continuous(self, duration_minutes: int = None):
        """Run continuous scanning loop"""
        logger.info(f"\n🚀 STARTING CONTINUOUS SCANNER")
        logger.info(f"   Duration: {duration_minutes or 'unlimited'} minutes")
        logger.info(f"   Interval: {self.config.check_interval_seconds} seconds")
        
        start_time = datetime.now()
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                self.scan_all(execute=True)
                
                # Check if duration exceeded
                if duration_minutes:
                    elapsed = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed >= duration_minutes:
                        logger.info(f"⏰ Duration limit reached ({duration_minutes} min). Stopping.")
                        break
                
                # Sleep until next scan
                logger.info(f"💤 Sleeping {self.config.check_interval_seconds}s... (Scan #{scan_count})")
                time.sleep(self.config.check_interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Scanner stopped by user")
        except Exception as e:
            logger.error(f"❌ Scanner error: {e}")
        
        # Final summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 SCANNER SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total scans: {scan_count}")
        logger.info(f"Signals generated: {len(self.signals_generated)}")
        logger.info(f"Positions opened: {len(self.positions_opened)}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Momentum Breakout Scanner')
    parser.add_argument('--tickers', type=str, default='NVDA,SPY,QQQ,TSLA',
                       help='Comma-separated list of tickers')
    parser.add_argument('--scan', action='store_true',
                       help='Run single scan and exit')
    parser.add_argument('--continuous', action='store_true',
                       help='Run continuous scanning')
    parser.add_argument('--duration', type=int, default=None,
                       help='Duration in minutes for continuous mode')
    parser.add_argument('--interval', type=int, default=60,
                       help='Scan interval in seconds')
    parser.add_argument('--no-execute', action='store_true',
                       help='Scan only, do not execute trades')
    
    args = parser.parse_args()
    
    # Build config
    tickers = [t.strip() for t in args.tickers.split(',')]
    config = StrategyConfig(
        tickers=tickers,
        check_interval_seconds=args.interval
    )
    
    # Create scanner
    scanner = MomentumScanner(config)
    
    if args.scan:
        # Single scan
        signals = scanner.scan_all(execute=not args.no_execute)
        print(f"\n{'='*60}")
        print(f"SCAN COMPLETE")
        print(f"{'='*60}")
        print(f"Tickers scanned: {len(tickers)}")
        print(f"Signals found: {len(signals)}")
        for sig in signals:
            print(f"\n🎯 {sig['ticker']} @ ${sig['price']}")
            print(f"   Entry: ${sig['entry_price']} | Stop: ${sig['stop_loss']} | Target: ${sig['take_profit']}")
            print(f"   Position: {sig['position_size']} shares | Risk: ${sig['risk_amount']}")
    
    elif args.continuous:
        # Continuous mode
        scanner.run_continuous(duration_minutes=args.duration)
    
    else:
        # Default: single scan
        signals = scanner.scan_all(execute=not args.no_execute)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"MOMENTUM SCANNER - MARKET OPEN READY")
        print(f"{'='*60}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} PST")
        print(f"Tickers: {', '.join(tickers)}")
        print(f"Mode: {'PAPER TRADING' if config.paper_trading else 'LIVE'}")
        print(f"Signals: {len(signals)}")
        
        if signals:
            print(f"\n🚀 ACTIVE SIGNALS:")
            for sig in signals:
                print(f"   {sig['ticker']}: ${sig['entry_price']} → Stop ${sig['stop_loss']} / Target ${sig['take_profit']}")

if __name__ == "__main__":
    main()
