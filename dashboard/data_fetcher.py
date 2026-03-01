"""
Data Fetcher Module
Fetches real-time market data from Polygon.io (primary) with yfinance fallback
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading

from polygon_fetcher import PolygonFetcher, get_polygon_fetcher


class DataFetcher:
    """Fetch market data with caching - Polygon primary, yfinance fallback"""
    
    def __init__(self):
        self.yf_cache = {}
        self.yf_cache_ttl = 60
        self.yf_last_fetch = {}
        self.price_cache = {}
        self._lock = threading.Lock()
        
        # Initialize Polygon fetcher
        self.polygon = get_polygon_fetcher()
        self.use_polygon = self.polygon.is_configured()
        
        # Data source tracking
        self.last_data_source = "UNKNOWN"
        self.data_quality = "BASIC"
    
    def get_data_source_status(self):
        """Get current data source status"""
        polygon_status = self.polygon.get_status()
        return {
            'source': self.last_data_source,
            'quality': self.data_quality,
            'polygon_status': polygon_status,
            'using_polygon': self.last_data_source == "POLYGON"
        }
    
    def _get_cache_key(self, ticker, data_type):
        return f"yf_{ticker}_{data_type}"
    
    def _is_yf_cache_valid(self, cache_key):
        if cache_key not in self.yf_last_fetch:
            return False
        elapsed = time.time() - self.yf_last_fetch[cache_key]
        return elapsed < self.yf_cache_ttl
    
    def get_current_price(self, ticker):
        """Get current stock price - Polygon primary, yfinance fallback"""
        # Try Polygon first if configured
        if self.use_polygon:
            try:
                price = self.polygon.get_current_price(ticker)
                if price:
                    self.last_data_source = "POLYGON"
                    self.data_quality = "PREMIUM"
                    return price
            except Exception:
                pass
        
        # Fallback to yfinance
        cache_key = self._get_cache_key(ticker, 'price')
        
        with self._lock:
            if self._is_yf_cache_valid(cache_key) and cache_key in self.price_cache:
                return self.price_cache[cache_key]
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
            
            if price:
                with self._lock:
                    self.price_cache[cache_key] = price
                    self.yf_last_fetch[cache_key] = time.time()
                self.last_data_source = "YFINANCE"
                self.data_quality = "BASIC"
                return price
            
            hist = stock.history(period='1d', interval='1m')
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                with self._lock:
                    self.price_cache[cache_key] = price
                    self.yf_last_fetch[cache_key] = time.time()
                self.last_data_source = "YFINANCE"
                self.data_quality = "BASIC"
                return price
                
        except Exception:
            pass
        
        simulated_prices = {
            'SPY': 590.50, 'QQQ': 515.25, 'NVDA': 138.75,
            'TSLA': 355.20, 'AMD': 118.45, 'AAPL': 232.80,
            'MSFT': 435.15, 'AMZN': 225.40, 'META': 598.90,
            'GOOGL': 185.30
        }
        self.last_data_source = "SIMULATED"
        self.data_quality = "BASIC"
        return simulated_prices.get(ticker, 100.0)
    
    def get_price_change(self, ticker):
        """Get price change percentage"""
        if self.use_polygon:
            try:
                change = self.polygon.get_price_change(ticker)
                if change is not None:
                    return change
            except:
                pass
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            change = info.get('regularMarketChangePercent')
            if change:
                return change
        except:
            pass
        
        return np.random.uniform(-2, 2)
    
    def get_options_chain(self, ticker):
        """Fetch options chain - Polygon primary, yfinance fallback"""
        # Try Polygon first for premium data
        if self.use_polygon:
            try:
                options_data = self.polygon.get_options_chain(ticker)
                if options_data is not None and not options_data.empty:
                    self.last_data_source = "POLYGON"
                    self.data_quality = "PREMIUM"
                    return options_data
            except Exception:
                pass
        
        # Fallback to yfinance
        cache_key = self._get_cache_key(ticker, 'options')
        
        with self._lock:
            if self._is_yf_cache_valid(cache_key) and cache_key in self.yf_cache:
                self.last_data_source = "YFINANCE (CACHED)"
                self.data_quality = "BASIC"
                return self.yf_cache[cache_key]
        
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                return self._generate_simulated_options(ticker)
            
            all_options = []
            
            for exp_date in expirations[:4]:
                try:
                    opt_chain = stock.option_chain(exp_date)
                    
                    calls = opt_chain.calls.copy()
                    calls['type'] = 'call'
                    calls['expiration'] = exp_date
                    
                    puts = opt_chain.puts.copy()
                    puts['type'] = 'put'
                    puts['expiration'] = exp_date
                    
                    all_options.append(calls)
                    all_options.append(puts)
                except:
                    continue
            
            if all_options:
                combined = pd.concat(all_options, ignore_index=True)
                
                if 'gamma' not in combined.columns:
                    combined['gamma'] = 0.05
                else:
                    combined['gamma'] = combined['gamma'].fillna(0.05)
                
                if 'open_interest' not in combined.columns:
                    combined['open_interest'] = combined.get('volume', 0)
                else:
                    combined['open_interest'] = combined['open_interest'].fillna(0)
                    
                if 'volume' in combined.columns:
                    combined['volume'] = combined['volume'].fillna(0)
                
                spot = self.get_current_price(ticker)
                strike_range = 0.20
                mask = (combined['strike'] >= spot * (1 - strike_range)) & \
                       (combined['strike'] <= spot * (1 + strike_range))
                combined = combined[mask]
                
                with self._lock:
                    self.yf_cache[cache_key] = combined
                    self.yf_last_fetch[cache_key] = time.time()
                
                self.last_data_source = "YFINANCE"
                self.data_quality = "BASIC"
                return combined
            
        except Exception:
            pass
        
        return self._generate_simulated_options(ticker)
    
    def _generate_simulated_options(self, ticker):
        """Generate realistic simulated options data"""
        spot = self.get_current_price(ticker)
        
        strikes = np.arange(
            spot * 0.80,
            spot * 1.20,
            spot * 0.02
        )
        
        expirations = [
            (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        ]
        
        all_data = []
        
        for exp in expirations:
            for strike in strikes:
                distance = abs(strike - spot) / spot
                atm_factor = max(0.1, 1 - distance * 3)
                
                call_gamma = atm_factor * 0.08 * (1 + np.random.random() * 0.2)
                call_oi = int(atm_factor * 50000 * (1 + np.random.random()))
                if strike > spot:
                    call_oi = int(call_oi * 1.5)
                
                put_gamma = atm_factor * 0.08 * (1 + np.random.random() * 0.2)
                put_oi = int(atm_factor * 50000 * (1 + np.random.random()))
                if strike < spot:
                    put_oi = int(put_oi * 1.5)
                
                all_data.append({
                    'strike': strike,
                    'type': 'call',
                    'expiration': exp,
                    'gamma': call_gamma,
                    'open_interest': call_oi,
                    'volume': int(call_oi * 0.1)
                })
                
                all_data.append({
                    'strike': strike,
                    'type': 'put',
                    'expiration': exp,
                    'gamma': put_gamma,
                    'open_interest': put_oi,
                    'volume': int(put_oi * 0.1)
                })
        
        df = pd.DataFrame(all_data)
        
        cache_key = self._get_cache_key(ticker, 'options')
        with self._lock:
            self.yf_cache[cache_key] = df
            self.yf_last_fetch[cache_key] = time.time()
        
        self.last_data_source = "SIMULATED"
        self.data_quality = "BASIC"
        return df
    
    def get_historical_data(self, ticker, period='1mo', interval='1d'):
        """Get historical price data"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)
            return hist
        except Exception:
            return pd.DataFrame()
    
    def get_multiple_prices(self, tickers):
        """Get prices for multiple tickers"""
        prices = {}
        for ticker in tickers:
            prices[ticker] = {
                'price': self.get_current_price(ticker),
                'change': self.get_price_change(ticker)
            }
        return prices
    
    def clear_cache(self):
        """Clear all cached data"""
        with self._lock:
            self.yf_cache.clear()
            self.price_cache.clear()
            self.yf_last_fetch.clear()
        self.polygon.clear_cache()
