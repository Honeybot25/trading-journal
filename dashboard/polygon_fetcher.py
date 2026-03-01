"""
Polygon.io API Fetcher Module
Fetches premium options data from Polygon.io
Rate limit: 5 requests/minute on free tier
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import requests
from scipy.stats import norm

# Load environment variables
try:
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()  # Try to load from current directory
except:
    pass  # Environment variables may be set directly


class PolygonRateLimiter:
    """Rate limiter for Polygon.io free tier (5 requests/minute)"""
    
    def __init__(self, max_requests_per_minute: int = 5):
        self.max_requests = max_requests_per_minute
        self.request_times: List[float] = []
        self._lock = threading.Lock()
    
    def can_make_request(self) -> bool:
        with self._lock:
            now = time.time()
            self.request_times = [t for t in self.request_times if now - t < 60]
            return len(self.request_times) < self.max_requests
    
    def record_request(self):
        with self._lock:
            self.request_times.append(time.time())
    
    def get_remaining_requests(self) -> int:
        with self._lock:
            now = time.time()
            self.request_times = [t for t in self.request_times if now - t < 60]
            return self.max_requests - len(self.request_times)
    
    def get_time_until_reset(self) -> float:
        with self._lock:
            if len(self.request_times) < self.max_requests:
                return 0
            now = time.time()
            oldest = min(self.request_times)
            return max(0, 60 - (now - oldest))


class PolygonFetcher:
    """Fetch options data from Polygon.io API"""
    
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY", "")
        self.base_url = "https://api.polygon.io"
        self.rate_limiter = PolygonRateLimiter(max_requests_per_minute=5)
        self.cache = {}
        self.cache_ttl = 300
        self.last_fetch = {}
        self._lock = threading.Lock()
        self.api_calls_made = 0
        self.data_source_status = "UNKNOWN"
        self.last_error = None
        self.last_successful_fetch = None
    
    def is_configured(self) -> bool:
        return bool(self.api_key) and len(self.api_key) > 10
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured(),
            "rate_limit_remaining": self.rate_limiter.get_remaining_requests(),
            "time_until_reset": self.rate_limiter.get_time_until_reset(),
            "api_calls_made": self.api_calls_made,
            "data_source": self.data_source_status,
            "last_error": self.last_error,
            "last_successful_fetch": self.last_successful_fetch
        }
    
    def _get_cache_key(self, ticker: str, data_type: str) -> str:
        return f"polygon_{ticker}_{data_type}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.last_fetch:
            return False
        elapsed = time.time() - self.last_fetch[cache_key]
        return elapsed < self.cache_ttl
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not self.is_configured():
            self.last_error = "API key not configured"
            return None
        
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.get_time_until_reset()
            self.last_error = f"Rate limit reached"
            return None
        
        url = f"{self.base_url}{endpoint}"
        request_params = params or {}
        request_params["apiKey"] = self.api_key
        
        try:
            self.rate_limiter.record_request()
            self.api_calls_made += 1
            response = requests.get(url, params=request_params, timeout=15)
            response.raise_for_status()
            self.last_error = None
            return response.json()
        except Exception as e:
            self.last_error = "API error"
            return None
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        cache_key = self._get_cache_key(ticker, "price")
        
        with self._lock:
            if self._is_cache_valid(cache_key) and cache_key in self.cache:
                return self.cache[cache_key]
        
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"
        data = self._make_request(endpoint)
        
        if data and "results" in data and len(data["results"]) > 0:
            price = data["results"][0].get("c")
            if price:
                with self._lock:
                    self.cache[cache_key] = price
                    self.last_fetch[cache_key] = time.time()
                self.data_source_status = "POLYGON"
                return price
        
        endpoint = f"/v2/last/trade/{ticker}"
        data = self._make_request(endpoint)
        
        if data and "results" in data:
            price = data["results"].get("p")
            if price:
                with self._lock:
                    self.cache[cache_key] = price
                    self.last_fetch[cache_key] = time.time()
                self.data_source_status = "POLYGON"
                return price
        
        return None
    
    def _calculate_gamma(self, spot: float, strike: float, tte: float, iv: float) -> float:
        if tte <= 0 or iv <= 0 or strike <= 0:
            return 0.001
        try:
            r = 0.05
            d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * tte) / (iv * np.sqrt(tte))
            gamma = norm.pdf(d1) / (spot * iv * np.sqrt(tte))
            return max(gamma, 0.0001)
        except:
            return 0.001
    
    def _parse_option_result(self, result: Dict, spot_price: float) -> Optional[Dict]:
        try:
            details = result.get("details", {})
            greeks = result.get("greeks", {})
            day = result.get("day", {})
            prev_day = result.get("previous_day", {})
            
            strike = details.get("strike_price", 0) / 100.0
            if strike == 0:
                return None
            
            contract_type = details.get("contract_type", "call").lower()
            expiration = details.get("expiration_date", "")
            
            volume = day.get("v", 0)
            open_interest = prev_day.get("o", 0) or prev_day.get("v", 0)
            
            gamma = greeks.get("gamma", 0.0)
            iv = greeks.get("implied_volatility", 0.0)
            delta = greeks.get("delta", 0.0)
            
            # Calculate gamma if needed
            if gamma == 0 and iv > 0 and expiration and spot_price > 0:
                try:
                    exp_date = datetime.strptime(expiration, "%Y-%m-%d")
                    today = datetime.now()
                    tte = max((exp_date - today).days / 365.0, 0.001)
                    gamma = self._calculate_gamma(spot_price, strike, tte, iv)
                except:
                    gamma = 0.001
            elif gamma == 0:
                gamma = 0.001
            
            return {
                "strike": strike,
                "type": contract_type,
                "expiration": expiration,
                "gamma": gamma,
                "delta": delta,
                "iv": iv,
                "open_interest": open_interest,
                "volume": volume
            }
        except Exception:
            return None
    
    def get_options_chain(self, ticker: str) -> Optional[pd.DataFrame]:
        cache_key = self._get_cache_key(ticker, "options")
        
        with self._lock:
            if self._is_cache_valid(cache_key) and cache_key in self.cache:
                self.data_source_status = "POLYGON (CACHED)"
                return self.cache[cache_key]
        
        # Get current price first
        spot_price = self.get_current_price(ticker)
        if not spot_price:
            self.last_error = "Could not fetch spot price"
            return None
        
        # Fetch options snapshot
        endpoint = f"/v3/snapshot/options/{ticker}"
        all_options = []
        
        data = self._make_request(endpoint)
        
        if not data:
            return None
        
        results = data.get("results", [])
        if not results:
            self.last_error = "No options data returned"
            return None
        
        for result in results:
            option_data = self._parse_option_result(result, spot_price)
            if option_data:
                all_options.append(option_data)
        
        if not all_options:
            self.last_error = "No valid options parsed"
            return None
        
        df = pd.DataFrame(all_options)
        
        # Filter strikes near current price (20% range)
        strike_range = 0.20
        mask = (df["strike"] >= spot_price * (1 - strike_range)) & \
               (df["strike"] <= spot_price * (1 + strike_range))
        df = df[mask]
        
        if df.empty:
            self.last_error = "No options in strike range"
            return None
        
        with self._lock:
            self.cache[cache_key] = df
            self.last_fetch[cache_key] = time.time()
        
        self.data_source_status = "POLYGON"
        self.last_successful_fetch = datetime.now().strftime("%H:%M:%S")
        
        return df
    
    def get_price_change(self, ticker: str) -> Optional[float]:
        """Get price change percentage"""
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"
        data = self._make_request(endpoint)
        
        if data and "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            open_price = result.get("o")
            close_price = result.get("c")
            if open_price and close_price:
                return ((close_price - open_price) / open_price) * 100
        
        return None
    
    def clear_cache(self):
        """Clear all cached data"""
        with self._lock:
            self.cache.clear()
            self.last_fetch.clear()


# Singleton instance
_polygon_fetcher = None

def get_polygon_fetcher() -> PolygonFetcher:
    """Get singleton PolygonFetcher instance"""
    global _polygon_fetcher
    if _polygon_fetcher is None:
        _polygon_fetcher = PolygonFetcher()
    return _polygon_fetcher
