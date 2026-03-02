"""
Demo Data Generator for GEX Terminal
Generates realistic mock data for testing when APIs are unavailable
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class DemoDataGenerator:
    """Generate realistic demo data for testing"""
    
    def __init__(self):
        self.base_prices = {
            'SPY': 597.50,
            'QQQ': 515.25,
            'IWM': 225.75,
            'NVDA': 138.50,
            'TSLA': 285.25,
            'AAPL': 235.00,
            'MSFT': 425.75,
            'AMD': 118.25,
            'META': 615.50,
            'GOOGL': 185.25
        }
    
    def get_demo_price(self, ticker):
        """Get demo price with small random movement"""
        base = self.base_prices.get(ticker, 100.0)
        # Add small random movement (-0.5% to +0.5%)
        movement = np.random.uniform(-0.005, 0.005)
        return base * (1 + movement)
    
    def generate_demo_options_chain(self, ticker):
        """Generate realistic options chain"""
        spot = self.get_demo_price(ticker)
        
        # Generate strikes around spot price
        strike_range = 0.15  # 15% range
        num_strikes = 20
        strikes = np.linspace(
            spot * (1 - strike_range),
            spot * (1 + strike_range),
            num_strikes
        )
        
        options = []
        exp_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        for strike in strikes:
            # Generate calls
            intrinsic = max(0, spot - strike)
            time_value = max(0.50, (abs(strike - spot) / spot) * 5)
            call_price = intrinsic + time_value
            
            # Delta calculation (simplified Black-Scholes approximation)
            moneyness = spot / strike
            if moneyness > 1.1:
                call_delta = 0.90 + np.random.uniform(-0.05, 0.05)
            elif moneyness > 1.0:
                call_delta = 0.70 + np.random.uniform(-0.10, 0.10)
            elif moneyness > 0.9:
                call_delta = 0.50 + np.random.uniform(-0.15, 0.15)
            else:
                call_delta = 0.20 + np.random.uniform(-0.10, 0.10)
            
            options.append({
                'strike': strike,
                'type': 'call',
                'expiration': exp_date,
                'bid': call_price * 0.95,
                'ask': call_price * 1.05,
                'last': call_price,
                'volume': int(np.random.uniform(100, 5000)),
                'open_interest': int(np.random.uniform(1000, 50000)),
                'delta': call_delta,
                'gamma': np.random.uniform(0.01, 0.08),
                'theta': -np.random.uniform(0.05, 0.30),
                'vega': np.random.uniform(0.10, 0.50),
                'implied_volatility': np.random.uniform(0.20, 0.45)
            })
            
            # Generate puts
            put_intrinsic = max(0, strike - spot)
            put_price = put_intrinsic + time_value
            put_delta = call_delta - 1.0  # Put-call parity approximation
            
            options.append({
                'strike': strike,
                'type': 'put',
                'expiration': exp_date,
                'bid': put_price * 0.95,
                'ask': put_price * 1.05,
                'last': put_price,
                'volume': int(np.random.uniform(100, 5000)),
                'open_interest': int(np.random.uniform(1000, 50000)),
                'delta': put_delta,
                'gamma': np.random.uniform(0.01, 0.08),
                'theta': -np.random.uniform(0.05, 0.30),
                'vega': np.random.uniform(0.10, 0.50),
                'implied_volatility': np.random.uniform(0.20, 0.45)
            })
        
        return pd.DataFrame(options)
    
    def generate_demo_gex_data(self, ticker):
        """Generate demo GEX data"""
        spot = self.get_demo_price(ticker)
        options_df = self.generate_demo_options_chain(ticker)
        
        # Calculate gamma exposure
        strikes = sorted(options_df['strike'].unique())
        gamma_exposure = []
        
        for strike in strikes:
            strike_options = options_df[options_df['strike'] == strike]
            total_gamma = strike_options['gamma'].sum() * strike_options['open_interest'].sum() * spot * spot / 1000000
            gamma_exposure.append(total_gamma)
        
        # Find key levels
        zero_gamma_idx = np.argmin(np.abs(np.array(gamma_exposure)))
        zero_gamma = strikes[zero_gamma_idx]
        
        max_gamma_idx = np.argmax(gamma_exposure)
        max_gamma_strike = strikes[max_gamma_idx]
        
        min_gamma_idx = np.argmin(gamma_exposure)
        min_gamma_strike = strikes[min_gamma_idx]
        
        total_gex = sum(gamma_exposure)
        
        return {
            'strikes': strikes,
            'gamma': gamma_exposure,
            'zero_gamma': zero_gamma,
            'max_gamma_strike': max_gamma_strike,
            'min_gamma_strike': min_gamma_strike,
            'total_gex': total_gex,
            'spot_price': spot
        }
    
    def generate_demo_signal(self, ticker):
        """Generate a demo trading signal"""
        gex_data = self.generate_demo_gex_data(ticker)
        spot = gex_data['spot_price']
        zero_gamma = gex_data['zero_gamma']
        total_gex = gex_data['total_gex']
        
        # Determine signal based on price vs zero gamma
        if spot > zero_gamma * 1.005:  # Price above zero gamma
            direction = 'BUY CALL'
            confidence = min(95, 60 + abs(spot - zero_gamma) / spot * 1000)
        elif spot < zero_gamma * 0.995:  # Price below zero gamma
            direction = 'BUY PUT'
            confidence = min(95, 60 + abs(spot - zero_gamma) / spot * 1000)
        else:
            direction = 'NEUTRAL'
            confidence = 50
        
        # Generate contract specs
        if direction == 'BUY CALL':
            strike = spot * 1.02  # 2% OTM
        elif direction == 'BUY PUT':
            strike = spot * 0.98  # 2% OTM
        else:
            strike = spot
        
        strike = round(strike / 5) * 5  # Round to $5 increments
        
        return {
            'ticker': ticker,
            'direction': direction,
            'confidence': int(confidence),
            'entry_price': spot,
            'entry_price_low': spot * 0.995,
            'entry_price_high': spot * 1.005,
            'stop_loss': spot * 0.97 if direction == 'BUY CALL' else spot * 1.03,
            'take_profit': spot * 1.10 if direction == 'BUY CALL' else spot * 0.90,
            'expected_move': 2.5,
            'gex_level': zero_gamma,
            'contract_specs': {
                'strike': strike,
                'strike_type': 'OTM' if direction != 'NEUTRAL' else 'ATM',
                'expiration': (datetime.now() + timedelta(days=35)).strftime('%b %d'),
                'expiration_days': 35,
                'estimated_price': 2.50,
                'delta_estimate': 0.35 if direction != 'NEUTRAL' else 0.50
            },
            'reasoning': [
                f"Price vs Zero Gamma: ${spot:.2f} vs ${zero_gamma:.2f}",
                f"Total GEX: {total_gex:,.0f} ({'Positive' if total_gex > 0 else 'Negative'})",
                f"Signal confidence: {confidence}%"
            ]
        }


# Global instance
demo_generator = DemoDataGenerator()


def get_demo_generator():
    """Get demo data generator"""
    return demo_generator
