#!/usr/bin/env python3
"""
Multi-Ticker GEX Scanner with Signal Tracking
Monitors SPY, QQQ, NVDA, TSLA, AMD for GEX signals
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import norm
import math
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import requests
import sqlite3
import os

# High options volume tickers to monitor
WATCHLIST = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/Honeybot/.openclaw/workspace/trading/logs/gex_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SignalTracker:
    """SQLite database for tracking signals and P&L"""
    
    def __init__(self, db_path: str = '/Users/Honeybot/.openclaw/workspace/trading/signals.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize signal tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                price REAL NOT NULL,
                action TEXT NOT NULL,
                direction TEXT,
                confidence INTEGER,
                gex_level REAL,
                gex_value REAL,
                rsi REAL,
                reasons TEXT,
                status TEXT DEFAULT 'open',
                exit_price REAL,
                exit_timestamp TEXT,
                pnl_pct REAL,
                exit_reason TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ticker ON signals(ticker)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON signals(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON signals(status)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Signal database initialized at {self.db_path}")
    
    def log_signal(self, ticker: str, price: float, signal: Dict, tech: Dict):
        """Log a generated signal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (
                timestamp, ticker, price, action, direction, confidence,
                gex_level, gex_value, rsi, reasons, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal['timestamp'],
            ticker,
            price,
            signal['action'],
            signal['direction'],
            signal['confidence'],
            signal.get('target_level'),
            signal.get('gex_at_level'),
            tech['rsi'],
            ' | '.join(signal['reasons']),
            'open' if signal['action'] != 'HOLD' else 'hold'
        ))
        
        conn.commit()
        conn.close()
    
    def get_open_signals(self, ticker: str = None) -> List[Dict]:
        """Get all open signals for potential exit tracking"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if ticker:
            cursor.execute(
                "SELECT * FROM signals WHERE status = 'open' AND ticker = ?",
                (ticker,)
            )
        else:
            cursor.execute("SELECT * FROM signals WHERE status = 'open'")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def close_signal(self, signal_id: int, exit_price: float, exit_reason: str = 'auto'):
        """Mark a signal as closed and calculate P&L"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
        row = cursor.fetchone()
        
        if row:
            entry_price = row[3]  # price column
            direction = row[5]  # direction column
            
            if direction == 'LONG':
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            
            cursor.execute('''
                UPDATE signals 
                SET status = 'closed', exit_price = ?, exit_timestamp = ?, 
                    pnl_pct = ?, exit_reason = ?
                WHERE id = ?
            ''', (exit_price, datetime.now().isoformat(), pnl_pct, exit_reason, signal_id))
            
            conn.commit()
        
        conn.close()
    
    def get_win_rate_stats(self, days: int = 7) -> Dict:
        """Calculate win rate and other stats for last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Total signals (excluding HOLD)
        cursor.execute(
            "SELECT COUNT(*) FROM signals WHERE timestamp > ? AND action != 'HOLD'",
            (since,)
        )
        total = cursor.fetchone()[0]
        
        if total == 0:
            conn.close()
            return {'total_signals': 0, 'win_rate': 0, 'avg_pnl_pct': 0, 'by_ticker': {}}
        
        # Wins (PnL > 0)
        cursor.execute(
            "SELECT COUNT(*) FROM signals WHERE timestamp > ? AND status = 'closed' AND pnl_pct > 0",
            (since,)
        )
        wins = cursor.fetchone()[0]
        
        # Average PnL
        cursor.execute(
            "SELECT AVG(pnl_pct) FROM signals WHERE timestamp > ? AND status = 'closed'",
            (since,)
        )
        avg_pnl = cursor.fetchone()[0] or 0
        
        # By ticker
        cursor.execute('''
            SELECT ticker, COUNT(*) as count, AVG(pnl_pct) as avg_pnl
            FROM signals 
            WHERE timestamp > ? AND status = 'closed'
            GROUP BY ticker
        ''', (since,))
        
        by_ticker = {row[0]: {'count': row[1], 'avg_pnl': row[2]} for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_signals': total,
            'closed_signals': wins,  # Actually this is just closed count, need to fix
            'wins': wins,
            'win_rate': (wins / max(total, 1)) * 100,
            'avg_pnl_pct': avg_pnl,
            'by_ticker': by_ticker,
            'period_days': days
        }

class GEXCalculator:
    def __init__(self, risk_free_rate: float = 0.045, contract_size: int = 100):
        self.risk_free_rate = risk_free_rate
        self.contract_size = contract_size
    
    def calculate_gamma(self, S: float, K: float, sigma: float, T: float) -> float:
        if sigma <= 0.0001 or T <= 0:
            return 0
        d1 = (math.log(S / K) + (self.risk_free_rate + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        return gamma
    
    def calculate_gex(self, row: pd.Series, spot_price: float, days_to_exp: int, option_type: str) -> float:
        T = days_to_exp / 365.0
        S = spot_price
        K = row['strike']
        sigma = row.get('impliedVolatility', 0.2)
        open_interest = row.get('openInterest', 0)
        
        if pd.isna(sigma) or sigma <= 0 or open_interest == 0:
            return 0
        
        gamma = self.calculate_gamma(S, K, sigma, T)
        gex = gamma * open_interest * self.contract_size * S * 0.01
        
        if option_type == 'put':
            gex = -gex
        
        return gex

class SignalGenerator:
    def __init__(self, config: Dict):
        self.config = config
        self.gex_threshold = config.get('gex_threshold', 1000000)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.gex_buffer_percent = config.get('gex_buffer_percent', 0.005)
    
    def find_key_levels(self, gex_by_strike: pd.Series, top_n: int = 5) -> pd.Series:
        abs_gex = gex_by_strike.abs()
        return gex_by_strike[abs_gex.nlargest(top_n).index].sort_values(ascending=False)
    
    def generate_signal(self, price: float, key_levels: pd.Series, tech: Dict) -> Dict:
        signal = {
            'timestamp': datetime.now().isoformat(),
            'price': price,
            'action': 'HOLD',
            'direction': None,
            'confidence': 0,
            'reasons': [],
            'target_level': None,
            'expected_move': None
        }
        
        if key_levels.empty:
            signal['reasons'].append('No significant GEX levels')
            return signal
        
        closest_strike = min(key_levels.index, key=lambda x: abs(x - price))
        closest_gex = key_levels[closest_strike]
        distance_pct = abs(price - closest_strike) / price
        
        signal['target_level'] = closest_strike
        signal['gex_at_level'] = closest_gex
        
        # Buy signal
        if closest_gex > self.gex_threshold and distance_pct < self.gex_buffer_percent * 2:
            if tech['rsi'] < self.rsi_oversold:
                signal['confidence'] += 30
                signal['reasons'].append(f"RSI oversold ({tech['rsi']:.1f})")
            
            if tech['trend']['above_ema21']:
                signal['confidence'] += 20
                signal['reasons'].append('Above EMA21')
            
            if tech['trend']['ema_bullish']:
                signal['confidence'] += 20
                signal['reasons'].append('Bullish EMA')
            
            if signal['confidence'] >= 50:
                signal['action'] = 'BUY'
                signal['direction'] = 'LONG'
        
        # Sell signal
        elif closest_gex < -self.gex_threshold and distance_pct < self.gex_buffer_percent * 2:
            if tech['rsi'] > self.rsi_overbought:
                signal['confidence'] += 30
                signal['reasons'].append(f"RSI overbought ({tech['rsi']:.1f})")
            
            if not tech['trend']['above_ema21']:
                signal['confidence'] += 20
                signal['reasons'].append('Below EMA21')
            
            if signal['confidence'] >= 50:
                signal['action'] = 'SELL'
                signal['direction'] = 'SHORT'
        
        if signal['action'] == 'HOLD':
            signal['reasons'].append(f'GEX ${closest_gex:,.0f} at {closest_strike} - no clear signal')
        
        return signal

class TechnicalAnalyzer:
    @staticmethod
    def ema(prices: pd.Series, period: int) -> pd.Series:
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).ewm(span=period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(span=period, adjust=False).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def get_signal_confirmation(self, df: pd.DataFrame) -> Dict:
        close = df['close']
        volume = df['volume']
        
        ema_9 = self.ema(close, 9)
        ema_21 = self.ema(close, 21)
        ema_50 = self.ema(close, 50)
        
        price = close.iloc[-1]
        
        return {
            'price': price,
            'rsi': self.rsi(close).iloc[-1],
            'trend': {
                'above_ema9': price > ema_9.iloc[-1],
                'above_ema21': price > ema_21.iloc[-1],
                'above_ema50': price > ema_50.iloc[-1],
                'ema_bullish': ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1],
            },
            'volume_ratio': volume.iloc[-1] / volume.rolling(20).mean().iloc[-1],
            'ema_9': ema_9.iloc[-1],
            'ema_21': ema_21.iloc[-1],
            'ema_50': ema_50.iloc[-1]
        }

class MultiTickerGEXScanner:
    """Scan multiple tickers for GEX signals"""
    
    def __init__(self, tickers: List[str] = None, config_path: str = None):
        self.tickers = tickers or WATCHLIST
        self.config = self._load_config(config_path)
        self.gex_calc = GEXCalculator(self.config.get('risk_free_rate', 0.045))
        self.tech_analyzer = TechnicalAnalyzer()
        self.signal_gen = SignalGenerator(self.config)
        self.tracker = SignalTracker()
        self.discord_webhook = self.config.get('discord_webhook_url')
        
        # Track which tickers had signals this run
        self.signals_generated = []
    
    def _load_config(self, path: str) -> Dict:
        if path and Path(path).exists():
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def scan_ticker(self, ticker: str) -> Optional[Dict]:
        """Scan a single ticker for GEX signals"""
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Scanning {ticker}")
            logger.info(f"{'='*50}")
            
            # Get price data
            stock = yf.Ticker(ticker)
            hist = stock.history(period='60d')
            hist.columns = [c.lower() for c in hist.columns]
            current_price = hist['close'].iloc[-1]
            
            logger.info(f"Price: ${current_price:.2f}")
            
            # Get options chain
            expirations = stock.options
            if not expirations:
                logger.warning(f"No options data for {ticker}")
                return None
            
            # Find nearest expiration with >= 1 day
            today = datetime.now().date()
            expiration = None
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                days_to_exp = (exp_date - today).days
                if days_to_exp >= 1:
                    expiration = exp
                    break
            
            if not expiration:
                logger.warning(f"No valid expiration for {ticker}")
                return None
            
            chain = stock.option_chain(expiration)
            calls = chain.calls.copy()
            puts = chain.puts.copy()
            
            exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
            days_to_exp = (exp_date - today).days
            
            logger.info(f"Using expiration: {expiration} ({days_to_exp} days)")
            
            # Calculate GEX
            calls['gex'] = calls.apply(
                lambda row: self.gex_calc.calculate_gex(row, current_price, days_to_exp, 'call'), axis=1
            )
            puts['gex'] = puts.apply(
                lambda row: self.gex_calc.calculate_gex(row, current_price, days_to_exp, 'put'), axis=1
            )
            
            calls_gex = calls.groupby('strike')['gex'].sum()
            puts_gex = puts.groupby('strike')['gex'].sum() * -1
            total_gex = calls_gex.add(puts_gex, fill_value=0)
            
            # Get key levels
            key_levels = self.signal_gen.find_key_levels(total_gex, top_n=3)
            
            logger.info(f"Key GEX levels: {[(k, f'${v:,.0f}') for k, v in key_levels.items()]}")
            
            # Technical analysis
            tech = self.tech_analyzer.get_signal_confirmation(hist)
            
            # Generate signal
            signal = self.signal_gen.generate_signal(current_price, key_levels, tech)
            
            # Log signal to database
            self.tracker.log_signal(ticker, current_price, signal, tech)
            
            # If actionable signal, add to list and notify
            if signal['action'] != 'HOLD':
                self.signals_generated.append({
                    'ticker': ticker,
                    'signal': signal,
                    'tech': tech
                })
                
                self._send_alert(ticker, signal, tech)
                logger.info(f"🚨 SIGNAL: {signal['action']} {signal['direction']} - Confidence: {signal['confidence']}%")
            else:
                logger.info(f"⏸️ No signal - Reasons: {' | '.join(signal['reasons'])}")
            
            return {
                'ticker': ticker,
                'price': current_price,
                'signal': signal,
                'tech': tech,
                'key_levels': key_levels.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}")
            return None
    
    def _send_alert(self, ticker: str, signal: Dict, tech: Dict):
        """Send Discord alert for actionable signal"""
        if not self.discord_webhook:
            return
        
        emoji = "📈" if signal['direction'] == 'LONG' else "📉" if signal['direction'] == 'SHORT' else "⏸️"
        
        message = (
            f"🚨 **GEX SIGNAL: {ticker}** {emoji}\n\n"
            f"**Action:** {signal['action']} {signal['direction']}\n"
            f"**Price:** ${signal['price']:.2f}\n"
            f"**GEX Level:** ${signal['target_level']:.2f} (${signal['gex_at_level']:,.0f})\n"
            f"**Confidence:** {signal['confidence']}%\n"
            f"**RSI:** {tech['rsi']:.1f}\n"
            f"**Reasons:** {' | '.join(signal['reasons'])}\n\n"
            f"*Paper trade only - review before executing*"
        )
        
        try:
            requests.post(self.discord_webhook, json={
                "content": message,
                "username": "GEX Scanner"
            })
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
    
    def run(self):
        """Run scan on all tickers"""
        logger.info(f"\n{'='*60}")
        logger.info(f"MULTI-TICKER GEX SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"Watchlist: {', '.join(self.tickers)}")
        logger.info(f"{'='*60}\n")
        
        results = []
        for ticker in self.tickers:
            result = self.scan_ticker(ticker)
            if result:
                results.append(result)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("SCAN COMPLETE")
        logger.info(f"Total scanned: {len(results)}")
        logger.info(f"Signals generated: {len(self.signals_generated)}")
        
        if self.signals_generated:
            for sig in self.signals_generated:
                logger.info(f"  - {sig['ticker']}: {sig['signal']['action']} {sig['signal']['direction']}")
        
        logger.info(f"{'='*60}\n")
        
        return results
    
    def get_stats_report(self) -> str:
        """Generate performance report"""
        stats = self.tracker.get_win_rate_stats(days=7)
        
        report = [
            f"📊 **7-Day GEX Signal Performance**",
            f"```",
            f"Total Signals: {stats['total_signals']}",
            f"Win Rate: {stats['win_rate']:.1f}%",
            f"Avg PnL: {stats['avg_pnl_pct']:.2f}%",
            f"```",
            f"\n**By Ticker:**",
        ]
        
        for ticker, data in stats.get('by_ticker', {}).items():
            report.append(f"- {ticker}: {data['count']} signals, {data['avg_pnl']:.2f}% avg")
        
        return '\n'.join(report)

def main():
    """Entry point"""
    scanner = MultiTickerGEXScanner(
        tickers=WATCHLIST,
        config_path='/Users/Honeybot/.openclaw/workspace/trading/config.yaml'
    )
    
    results = scanner.run()
    
    # Print stats report
    print("\n" + scanner.get_stats_report())
    
    return results

if __name__ == '__main__':
    main()
