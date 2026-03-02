"""
Tradier API Client for Options Data
Free tier: Delayed options data (15 min delay)
Docs: https://documentation.tradier.com/
"""
import os
import requests
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta


class TradierOptionsClient:
    """Fetch options data from Tradier API (free tier)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('TRADIER_API_KEY')
        self.base_url = 'https://sandbox.tradier.com'  # Free tier uses sandbox
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
    
    def is_configured(self) -> bool:
        """Check if API key is valid"""
        return self.api_key and self.api_key != 'your-api-key-here'
    
    def get_options_chain(self, ticker: str) -> Optional[pd.DataFrame]:
        """Get options chain for ticker"""
        if not self.is_configured():
            return None
        
        url = f'{self.base_url}/v1/markets/options/chains'
        params = {
            'symbol': ticker,
            'expiration': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if 'options' in data and 'option' in data['options']:
                options = data['options']['option']
                df = pd.DataFrame(options)
                return df
            return None
        except Exception as e:
            print(f"[Tradier] Error fetching options: {e}")
            return None
    
    def get_quote(self, ticker: str) -> Optional[float]:
        """Get last price for ticker"""
        if not self.is_configured():
            return None
        
        url = f'{self.base_url}/v1/markets/quotes'
        params = {'symbols': ticker}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = response.json()
            
            if 'quotes' in data and 'quote' in data['quotes']:
                quote = data['quotes']['quote']
                if isinstance(quote, list):
                    quote = quote[0]
                return float(quote.get('last', 0))
            return None
        except Exception as e:
            print(f"[Tradier] Error fetching quote: {e}")
            return None


# Global instance
tradier_client = TradierOptionsClient()


def get_tradier_client() -> TradierOptionsClient:
    """Get or create Tradier client"""
    global tradier_client
    if not tradier_client.is_configured():
        tradier_client = TradierOptionsClient()
    return tradier_client
