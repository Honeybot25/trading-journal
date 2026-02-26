#!/usr/bin/env python3
"""
SPY GEX Options Trading Bot
Gamma Exposure (GEX) based signals for SPY options trading
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/Honeybot/.openclaw/workspace/trading/logs/trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GEXCalculator:
    """Calculate Gamma Exposure (GEX) from options chain data"""
    
    def __init__(self, risk_free_rate: float = 0.01, contract_size: int = 100):
        self.risk_free_rate = risk_free_rate
        self.contract_size = contract_size
    
    def calculate_gamma(self, S: float, K: float, sigma: float, T: float) -> float:
        """
        Calculate option gamma using Black-Scholes model
        Gamma = N'(d1) / (S * sigma * sqrt(T))
        """
        if sigma <= 0.0001 or T <= 0:
            return 0
        
        d1 = (math.log(S / K) + (self.risk_free_rate + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        return gamma
    
    def calculate_gex(self, row: pd.Series, spot_price: float, days_to_exp: int, option_type: str) -> float:
        """
        Calculate Gamma Exposure for a single option
        GEX = gamma * open_interest * contract_size * spot_price * 0.01
        
        Calls: +GEX (market makers short calls -> positive gamma exposure)
        Puts: -GEX (market makers short puts -> negative gamma exposure)
        """
        T = days_to_exp / 365.0
        S = spot_price
        K = row['strike']
        sigma = row.get('impliedVolatility', 0.2)  # Default 20% IV if missing
        open_interest = row.get('openInterest', 0)
        
        if pd.isna(sigma) or sigma <= 0 or open_interest == 0:
            return 0
        
        gamma = self.calculate_gamma(S, K, sigma, T)
        gex = gamma * open_interest * self.contract_size * S * 0.01
        
        # Puts contribute negative GEX from market maker perspective
        if option_type == 'put':
            gex = -gex
        
        return gex

class TechnicalAnalyzer:
    """Technical analysis indicators for signal confirmation"""
    
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
    
    @staticmethod
    def volume_profile(df: pd.DataFrame, bins: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate volume profile for support/resistance"""
        price_bins = np.linspace(df['low'].min(), df['high'].max(), bins)
        volume_profile = np.zeros(bins - 1)
        
        for i in range(len(df)):
            idx = np.digitize(df.iloc[i]['close'], price_bins) - 1
            if 0 <= idx < len(volume_profile):
                volume_profile[idx] += df.iloc[i]['volume']
        
        return price_bins, volume_profile
    
    def get_signal_confirmation(self, df: pd.DataFrame) -> Dict:
        """
        Get technical indicators for signal confirmation
        Returns: RSI, EMA trend, volume strength
        """
        close = df['close']
        volume = df['volume']
        
        # EMAs
        ema_9 = self.ema(close, 9)
        ema_21 = self.ema(close, 21)
        ema_50 = self.ema(close, 50)
        
        # RSI
        rsi_value = self.rsi(close).iloc[-1]
        
        # Trend
        price = close.iloc[-1]
        trend = {
            'above_ema9': price > ema_9.iloc[-1],
            'above_ema21': price > ema_21.iloc[-1],
            'above_ema50': price > ema_50.iloc[-1],
            'ema_bullish': ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1],
        }
        
        # Volume strength (current vs 20-day average)
        volume_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        
        return {
            'price': price,
            'rsi': rsi_value,
            'trend': trend,
            'volume_ratio': volume_ratio,
            'ema_9': ema_9.iloc[-1],
            'ema_21': ema_21.iloc[-1],
            'ema_50': ema_50.iloc[-1]
        }

class SignalGenerator:
    """Generate trading signals based on GEX levels and technical analysis"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.gex_threshold = config.get('gex_threshold', 1000000)  # Minimum GEX level to care about
        self.rsi_oversold = config.get('rsi_oversold', 35)
        self.rsi_overbought = config.get('rsi_overbought', 65)
        self.gex_buffer_percent = config.get('gex_buffer_percent', 0.005)  # 0.5% buffer around GEX levels
    
    def find_key_levels(self, gex_by_strike: pd.Series, top_n: int = 5) -> pd.Series:
        """Find strikes with highest absolute GEX concentrations"""
        abs_gex = gex_by_strike.abs()
        return gex_by_strike[abs_gex.nlargest(top_n).index].sort_values(ascending=False)
    
    def calculate_zero_gamma_level(self, gex_by_strike: pd.Series) -> Optional[float]:
        """Find the strike where GEX crosses zero"""
        sorted_strikes = gex_by_strike.sort_index()
        
        # Find where GEX changes sign
        for i in range(len(sorted_strikes) - 1):
            if sorted_strikes.iloc[i] * sorted_strikes.iloc[i + 1] < 0:
                # Linear interpolation
                return (sorted_strikes.index[i] + sorted_strikes.index[i + 1]) / 2
        
        return None
    
    def generate_signal(self, price: float, key_levels: pd.Series, tech_analysis: Dict) -> Dict:
        """
        Generate trading signal based on GEX levels and technical confirmation
        
        SIGNAL LOGIC:
        - BUY: Price near/below positive GEX level + RSI < 35 + above EMA21
        - SELL: Price near/above negative GEX level + RSI > 65 + below EMA21
        - PASS: Mixed signals or no clear level interaction
        """
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
            signal['reasons'].append('No significant GEX levels detected')
            return signal
        
        # Find closest GEX level
        closest_strike = min(key_levels.index, key=lambda x: abs(x - price))
        closest_gex = key_levels[closest_strike]
        distance_pct = abs(price - closest_strike) / price
        
        signal['target_level'] = closest_strike
        signal['gex_at_level'] = closest_gex
        
        # Buy signal conditions
        if closest_gex > self.gex_threshold and distance_pct < self.gex_buffer_percent * 2:
            # Positive GEX support level (price approaching support)
            if tech_analysis['rsi'] < self.rsi_oversold:
                signal['confidence'] += 30
                signal['reasons'].append(f"RSI oversold ({tech_analysis['rsi']:.1f})")
            
            if tech_analysis['trend']['above_ema21']:
                signal['confidence'] += 20
                signal['reasons'].append('Price above EMA21 (uptrend)')
            
            if tech_analysis['trend']['ema_bullish']:
                signal['confidence'] += 20
                signal['reasons'].append('Bullish EMA structure')
            
            if tech_analysis['volume_ratio'] > 1.5:
                signal['confidence'] += 15
                signal['reasons'].append(f"Strong volume ({tech_analysis['volume_ratio']:.1f}x)")
            
            if signal['confidence'] >= 50:
                signal['action'] = 'BUY'
                signal['direction'] = 'LONG'
                signal['expected_move'] = 'bounce from GEX support'
        
        # Sell signal conditions
        elif closest_gex < -self.gex_threshold and distance_pct < self.gex_buffer_percent * 2:
            # Negative GEX resistance level (price approaching resistance)
            if tech_analysis['rsi'] > self.rsi_overbought:
                signal['confidence'] += 30
                signal['reasons'].append(f"RSI overbought ({tech_analysis['rsi']:.1f})")
            
            if not tech_analysis['trend']['above_ema21']:
                signal['confidence'] += 20
                signal['reasons'].append('Price below EMA21 (downtrend)')
            
            if tech_analysis['volume_ratio'] > 1.5:
                signal['confidence'] += 15
                signal['reasons'].append(f"Strong volume ({tech_analysis['volume_ratio']:.1f}x)")
            
            if signal['confidence'] >= 50:
                signal['action'] = 'SELL'
                signal['direction'] = 'SHORT'
                signal['expected_move'] = 'rejection at GEX resistance'
        
        if signal['action'] == 'HOLD':
            signal['reasons'].append(f'GEX level at {closest_strike} (${closest_gex:,.0f}) - no clear signal')
            signal['reasons'].append(f'Price {distance_pct*100:.2f}% from level')
            signal['reasons'].append(f'RSI: {tech_analysis["rsi"]:.1f}')
        
        return signal

class PaperTrader:
    """Paper trading simulator"""
    
    def __init__(self, initial_capital: float = 100000):
        self.capital = initial_capital
        self.positions = []
        self.trade_history = []
        self.position_size_pct = 0.1  # 10% per position
    
    def execute_signal(self, signal: Dict) -> Optional[Dict]:
        """Execute paper trade based on signal"""
        if signal['action'] == 'HOLD':
            return None
        
        price = signal['price']
        position_size = self.capital * self.position_size_pct
        contracts = int(position_size / (price * 100))  # 100 shares per contract
        
        trade = {
            'timestamp': signal['timestamp'],
            'action': signal['action'],
            'direction': signal['direction'],
            'price': price,
            'contracts': contracts,
            'notional': contracts * price * 100,
            'reasons': signal['reasons'],
            'gex_level': signal['target_level'],
            'confidence': signal['confidence']
        }
        
        self.trade_history.append(trade)
        self.positions.append(trade)
        
        logger.info(f"Paper Trade Executed: {signal['action']} {contracts} contracts at ${price:.2f}")
        
        return trade
    
    def get_pnl(self) -> Dict:
        """Calculate running P&L"""
        pnl = sum([
            (p['price'] - self.positions[i-1]['price']) * p['contracts'] * 100 
            if p['direction'] == 'LONG' else 
            (self.positions[i-1]['price'] - p['price']) * p['contracts'] * 100
            for i, p in enumerate(self.positions) if i > 0
        ])
        
        return {
            'total_trades': len(self.trade_history),
            'current_pnl': pnl,
            'win_rate': 0  # TODO: Track exits properly
        }

class SPYGEXBot:
    """Main SPY GEX Trading Bot"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.gex_calc = GEXCalculator()
        self.tech_analyzer = TechnicalAnalyzer()
        self.signal_gen = SignalGenerator(self.config)
        self.trader = PaperTrader(self.config.get('initial_capital', 100000))
        self.discord_webhook = self.config.get('discord_webhook_url')
        
    def _load_config(self, path: str) -> Dict:
        """Load configuration from YAML"""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {path} not found, using defaults")
            return {}
    
    def fetch_spy_data(self, period: str = '60d', interval: str = '1d') -> pd.DataFrame:
        """Fetch SPY price history"""
        spy = yf.Ticker("SPY")
        hist = spy.history(period=period, interval=interval)
        hist.columns = [c.lower() for c in hist.columns]
        return hist
    
    def fetch_options_chain(self, expiration: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch SPY options chain for given expiration"""
        spy = yf.Ticker("SPY")
        
        if expiration is None:
            # Use nearest expiration with at least 1 day remaining
            expirations = spy.options
            today = datetime.now().date()
            expiration = None
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                days_to_exp = (exp_date - today).days
                if days_to_exp >= 1:
                    expiration = exp
                    break
        
        if not expiration:
            logger.error("No expiration dates available")
            return pd.DataFrame(), pd.DataFrame()
        
        chain = spy.option_chain(expiration)
        calls = chain.calls.copy()
        puts = chain.puts.copy()
        
        calls['expiration'] = expiration
        puts['expiration'] = expiration
        
        return calls, puts
    
    def calculate_total_gex(self, calls: pd.DataFrame, puts: pd.DataFrame, spot_price: float, days_to_exp: int) -> pd.Series:
        """Calculate total GEX aggregated by strike"""
        # Calculate GEX for each option
        calls['gex'] = calls.apply(
            lambda row: self.gex_calc.calculate_gex(row, spot_price, days_to_exp, 'call'), 
            axis=1
        )
        puts['gex'] = puts.apply(
            lambda row: self.gex_calc.calculate_gex(row, spot_price, days_to_exp, 'put'), 
            axis=1
        )
        
        # Aggregate by strike
        calls_gex = calls.groupby('strike')['gex'].sum()
        puts_gex = puts.groupby('strike')['gex'].sum() * -1  # Puts contribute negative GEX from MM perspective
        
        total_gex = calls_gex.add(puts_gex, fill_value=0)
        return total_gex
    
    def send_discord_alert(self, message: str) -> bool:
        """Send message to Discord webhook"""
        if not self.discord_webhook:
            return False
        
        try:
            data = {
                "content": message,
                "username": "SPY GEX Bot"
            }
            response = requests.post(self.discord_webhook, json=data)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False
    
    def run(self):
        """Main bot execution loop"""
        logger.info("=" * 60)
        logger.info("SPY GEX BOT - INITIALIZING")
        logger.info("=" * 60)
        
        # Get current SPY price and history
        price_data = self.fetch_spy_data()
        current_price = price_data['close'].iloc[-1]
        logger.info(f"SPY Current Price: ${current_price:.2f}")
        
        # Get options chain
        calls, puts = self.fetch_options_chain()
        if calls.empty or puts.empty:
            logger.error("Failed to fetch options data")
            return
        
        # Calculate GEX
        expiration = calls['expiration'].iloc[0]
        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
        days_to_exp = (exp_date.date() - datetime.now().date()).days
        
        logger.info(f"Options Expiration: {expiration} ({days_to_exp} days)")
        
        gex_by_strike = self.calculate_total_gex(calls, puts, current_price, days_to_exp)
        
        # Find key levels
        key_levels = self.signal_gen.find_key_levels(gex_by_strike, top_n=5)
        zero_gamma = self.signal_gen.calculate_zero_gamma_level(gex_by_strike)
        
        logger.info(f"\n🔑 KEY GEX LEVELS:")
        logger.info("-" * 40)
        for strike, gex in key_levels.items():
            logger.info(f"  Strike: ${strike:.2f} | GEX: ${gex:,.0f}")
        
        if zero_gamma:
            logger.info(f"  Zero-Gamma Level: ${zero_gamma:.2f}")
        
        # Technical analysis
        tech = self.tech_analyzer.get_signal_confirmation(price_data)
        
        logger.info(f"\n📊 TECHNICAL ANALYSIS:")
        logger.info("-" * 40)
        logger.info(f"  RSI: {tech['rsi']:.1f}")
        logger.info(f"  EMA21: ${tech['ema_21']:.2f} | Above: {tech['trend']['above_ema21']}")
        logger.info(f"  EMA50: ${tech['ema_50']:.2f} | Above: {tech['trend']['above_ema50']}")
        logger.info(f"  Volume Ratio: {tech['volume_ratio']:.2f}x")
        
        # Generate signal
        signal = self.signal_gen.generate_signal(current_price, key_levels, tech)
        
        logger.info(f"\n🎯 SIGNAL GENERATED:")
        logger.info("-" * 40)
        logger.info(f"  Action: {signal['action']} {'📈' if signal['direction'] == 'LONG' else '📉' if signal['direction'] == 'SHORT' else '⏸️'}")
        logger.info(f"  Confidence: {signal['confidence']}%")
        logger.info(f"  Reasons: {' | '.join(signal['reasons'])}")
        
        # Execute if signal
        if signal['action'] != 'HOLD':
            trade = self.trader.execute_signal(signal)
            if trade:
                self.send_discord_alert(
                    f"🚨 **SPY GEX SIGNAL** 🚨\n"
                    f"**Action:** {signal['action']} {signal['direction']}\n"
                    f"**Price:** ${signal['price']:.2f}\n"
                    f"**Contracts:** {trade['contracts']}\n"
                    f"**GEX Level:** ${signal['target_level']:.2f}\n"
                    f"**Confidence:** {signal['confidence']}%\n"
                    f"**Reasons:** {' | '.join(signal['reasons'])}"
                )
        
        # Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'spy_price': current_price,
            'gex_levels': key_levels.to_dict(),
            'zero_gamma': zero_gamma,
            'technical': tech,
            'signal': signal,
            'paper_trading': self.trader.get_pnl()
        }
        
        output_path = Path('/Users/Honeybot/.openclaw/workspace/trading/output')
        output_path.mkdir(parents=True, exist_ok=True)
        
        with open(output_path / f'gex_scan_{datetime.now().strftime("%Y%m%d_%H%M")}.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n✅ Results saved to output/")
        logger.info("=" * 60)
        
        return results

def main():
    """Entry point"""
    # Setup paths
    Path('/Users/Honeybot/.openclaw/workspace/trading/logs').mkdir(parents=True, exist_ok=True)
    Path('/Users/Honeybot/.openclaw/workspace/trading/output').mkdir(parents=True, exist_ok=True)
    
    bot = SPYGEXBot('/Users/Honeybot/.openclaw/workspace/trading/config.yaml')
    results = bot.run()
    return results

if __name__ == '__main__':
    main()
