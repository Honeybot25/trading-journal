"""
GEX Calculator Module
Calculates Gamma Exposure from options data - enhanced for Polygon.io data
"""

import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta


class GEXCalculator:
    """Calculate Gamma Exposure metrics with Polygon.io support"""
    
    def __init__(self):
        self.iv_default = 0.30
        self.risk_free_rate = 0.05
        self.contract_multiplier = 100
    
    def calculate_gex(self, options_data, spot_price, data_quality="BASIC"):
        """
        Calculate Gamma Exposure from options chain
        
        Args:
            options_data: DataFrame with options data (from Polygon or yfinance)
            spot_price: Current spot price
            data_quality: "PREMIUM" for Polygon data, "BASIC" for yfinance
        """
        if options_data is None or options_data.empty:
            return self._generate_sample_data(spot_price)
        
        try:
            strikes = sorted(options_data['strike'].unique())
            
            call_gex = []
            put_gex = []
            net_gex_by_strike = []
            heatmap_data = []
            
            total_call_gex = 0
            total_put_gex = 0
            
            for strike in strikes:
                strike_data = options_data[options_data['strike'] == strike]
                
                # Get call data
                call_row = strike_data[strike_data['type'] == 'call']
                call_gamma = 0.0
                call_oi = 0
                if not call_row.empty:
                    call_gamma = float(call_row.iloc[0].get('gamma', 0) or 0)
                    call_oi = int(call_row.iloc[0].get('open_interest', 0) or 0)
                    # Fallback to volume if OI is 0
                    if call_oi == 0:
                        call_oi = int(call_row.iloc[0].get('volume', 0) or 0)
                
                # Get put data
                put_row = strike_data[strike_data['type'] == 'put']
                put_gamma = 0.0
                put_oi = 0
                if not put_row.empty:
                    put_gamma = float(put_row.iloc[0].get('gamma', 0) or 0)
                    put_oi = int(put_row.iloc[0].get('open_interest', 0) or 0)
                    if put_oi == 0:
                        put_oi = int(put_row.iloc[0].get('volume', 0) or 0)
                
                # Calculate GEX: Gamma x OI x ContractSize x Spot
                call_gex_value = call_gamma * call_oi * self.contract_multiplier * spot_price / 1e9
                put_gex_value = put_gamma * put_oi * self.contract_multiplier * spot_price / 1e9
                
                call_gex.append(call_gex_value)
                put_gex.append(put_gex_value)
                net_gex_by_strike.append(call_gex_value - put_gex_value)
                
                total_call_gex += call_gex_value
                total_put_gex += put_gex_value
                
                # Add to heatmap data
                exp_dates = strike_data['expiration'].unique() if 'expiration' in strike_data.columns else ['']
                for exp in exp_dates:
                    heatmap_data.append({
                        'strike': strike,
                        'expiration': str(exp)[:10] if exp else 'N/A',
                        'gex': call_gex_value - put_gex_value
                    })
            
            # Calculate zero gamma level
            zero_gamma = self._find_zero_crossing(strikes, net_gex_by_strike)
            
            # Find max gamma strike
            abs_gex = [abs(x) for x in net_gex_by_strike]
            max_gamma_idx = abs_gex.index(max(abs_gex)) if abs_gex else 0
            max_gamma_strike = strikes[max_gamma_idx] if strikes else spot_price
            
            # Find max put and call strikes
            if put_gex:
                max_put_idx = put_gex.index(max(put_gex))
                max_put_strike = strikes[max_put_idx]
            else:
                max_put_strike = spot_price * 0.95
            
            if call_gex:
                max_call_idx = call_gex.index(max(call_gex))
                max_call_strike = strikes[max_call_idx]
            else:
                max_call_strike = spot_price * 1.05
            
            total_gex = total_call_gex - total_put_gex
            put_call_ratio = total_put_gex / total_call_gex if total_call_gex > 0 else 1.0
            
            return {
                'strikes': strikes,
                'call_gex': call_gex,
                'put_gex': put_gex,
                'net_gex_by_strike': net_gex_by_strike,
                'heatmap_data': heatmap_data,
                'zero_gamma_level': zero_gamma or spot_price,
                'max_gamma_strike': max_gamma_strike,
                'max_put_strike': max_put_strike,
                'max_call_strike': max_call_strike,
                'total_gex': total_gex,
                'put_call_ratio': put_call_ratio,
                'net_gex': total_call_gex - total_put_gex,
                'data_quality': data_quality,
                'total_call_gex': total_call_gex,
                'total_put_gex': total_put_gex
            }
            
        except Exception as e:
            print(f"Error calculating GEX: {e}")
            return self._generate_sample_data(spot_price)
    
    def _find_zero_crossing(self, strikes, values):
        """Find where values cross zero using linear interpolation"""
        if not strikes or not values:
            return None
        
        for i in range(len(values) - 1):
            if values[i] == 0:
                return strikes[i]
            if values[i] * values[i+1] < 0:  # Sign change
                t = abs(values[i]) / (abs(values[i]) + abs(values[i+1]))
                return strikes[i] + t * (strikes[i+1] - strikes[i])
        
        return strikes[len(strikes)//2] if strikes else None
    
    def _generate_sample_data(self, spot_price):
        """Generate realistic sample GEX data"""
        strike_range = 0.15
        num_strikes = 21
        
        strikes = np.linspace(
            spot_price * (1 - strike_range),
            spot_price * (1 + strike_range),
            num_strikes
        )
        
        call_gex = []
        put_gex = []
        net_gex_by_strike = []
        heatmap_data = []
        
        for i, strike in enumerate(strikes):
            distance = abs(strike - spot_price) / spot_price
            base_gamma = max(0, 1 - distance * 5)
            
            if strike > spot_price:
                call_oi = base_gamma * 50000 * (1 + np.random.random() * 0.3)
                put_oi = base_gamma * 10000 * (1 + np.random.random() * 0.3)
            else:
                call_oi = base_gamma * 10000 * (1 + np.random.random() * 0.3)
                put_oi = base_gamma * 50000 * (1 + np.random.random() * 0.3)
            
            call_gamma_val = base_gamma * 0.05 * call_oi * 100 * spot_price / 1e9
            put_gamma_val = base_gamma * 0.05 * put_oi * 100 * spot_price / 1e9
            
            call_gex.append(call_gamma_val)
            put_gex.append(put_gamma_val)
            net_gex_by_strike.append(call_gamma_val - put_gamma_val)
            
            expirations = ['0DTE', '1W', '2W', '1M', '2M']
            for j, exp in enumerate(expirations):
                decay = 1 / (j + 1)
                heatmap_data.append({
                    'strike': strike,
                    'expiration': exp,
                    'gex': (call_gamma_val - put_gamma_val) * decay
                })
        
        zero_gamma = self._find_zero_crossing(strikes.tolist(), net_gex_by_strike)
        abs_gex = [abs(x) for x in net_gex_by_strike]
        max_gamma_idx = abs_gex.index(max(abs_gex))
        max_gamma_strike = strikes[max_gamma_idx]
        
        max_put_idx = put_gex.index(max(put_gex))
        max_put_strike = strikes[max_put_idx]
        
        max_call_idx = call_gex.index(max(call_gex))
        max_call_strike = strikes[max_call_idx]
        
        total_call = sum(call_gex)
        total_put = sum(put_gex)
        
        return {
            'strikes': strikes.tolist(),
            'call_gex': call_gex,
            'put_gex': put_gex,
            'net_gex_by_strike': net_gex_by_strike,
            'heatmap_data': heatmap_data,
            'zero_gamma_level': zero_gamma or spot_price,
            'max_gamma_strike': max_gamma_strike,
            'max_put_strike': max_put_strike,
            'max_call_strike': max_call_strike,
            'total_gex': total_call - total_put,
            'put_call_ratio': total_put / total_call if total_call > 0 else 1.0,
            'net_gex': total_call - total_put,
            'data_quality': 'SIMULATED',
            'total_call_gex': total_call,
            'total_put_gex': total_put
        }
    
    def calculate_theoretical_gamma(self, S, K, T, r, sigma, option_type='call'):
        """Calculate gamma using Black-Scholes"""
        if T <= 0 or sigma <= 0:
            return 0
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        return gamma
    
    def estimate_gamma_flip(self, gex_data, spot_price):
        """Estimate the gamma flip point and its implications"""
        zero_gamma = gex_data.get('zero_gamma_level', spot_price)
        distance_pct = abs(spot_price - zero_gamma) / spot_price * 100
        
        analysis = {
            'flip_level': zero_gamma,
            'distance_pct': distance_pct,
            'direction': 'ABOVE' if spot_price > zero_gamma else 'BELOW',
            'regime': 'POSITIVE GAMMA' if gex_data.get('total_gex', 0) > 0 else 'NEGATIVE GAMMA',
            'risk_level': 'LOW',
            'implications': []
        }
        
        if distance_pct < 1:
            analysis['risk_level'] = 'CRITICAL'
            analysis['implications'].append('Gamma flip imminent - high volatility expected')
        elif distance_pct < 2:
            analysis['risk_level'] = 'HIGH'
            analysis['implications'].append('Approaching gamma flip zone')
        elif distance_pct < 5:
            analysis['risk_level'] = 'MODERATE'
        
        if gex_data.get('total_gex', 0) > 0:
            analysis['implications'].append('Dealers long gamma - pinning to strikes likely')
            analysis['implications'].append('Mean reversion favored')
        else:
            analysis['implications'].append('Dealers short gamma - trending moves likely')
            analysis['implications'].append('Breakouts can accelerate')
        
        return analysis
    
    def generate_signals(self, gex_data, spot_price, ticker):
        """
        Generate trading signals based on GEX analysis
        Returns list of signal dictionaries with interpretations
        """
        signals = []
        
        total_gex = gex_data.get('total_gex', 0)
        zero_gamma = gex_data.get('zero_gamma_level', spot_price)
        strikes = gex_data.get('strikes', [])
        net_gex_by_strike = gex_data.get('net_gex_by_strike', [])
        
        if not strikes or not net_gex_by_strike:
            return signals
        
        # 1. Zero Gamma Flip Approach Signal
        distance_to_flip = abs(spot_price - zero_gamma) / spot_price * 100
        if distance_to_flip < 2.0:
            signals.append({
                'type': 'FLIP_APPROACH',
                'priority': 'HIGH' if distance_to_flip < 1.0 else 'MEDIUM',
                'title': f'Zero Gamma Flip {"Imminent" if distance_to_flip < 1.0 else "Approaching"}',
                'message': f'Price is {distance_to_flip:.2f}% from flip level at ${zero_gamma:.2f}',
                'implications': [
                    'Dealer hedging behavior will reverse at flip',
                    f'Expect increased volatility near ${zero_gamma:.2f}',
                    'Regime change: ' + ('Stability → Trending' if total_gex > 0 else 'Trending → Stability')
                ],
                'confidence': max(50, 95 - int(distance_to_flip * 20)),
                'direction': 'VOLATILE' if distance_to_flip < 1.0 else 'CAUTION'
            })
        
        # 2. Gamma Support/Resistance Signals
        for i, strike in enumerate(strikes):
            if i >= len(net_gex_by_strike):
                continue
                
            distance = abs(spot_price - strike) / spot_price * 100
            if distance > 3.0:
                continue
            
            net_gex = net_gex_by_strike[i]
            abs_gex = abs(net_gex)
            
            # High positive GEX = Support
            if net_gex > 2.0 and spot_price > strike and distance < 2.0:
                signals.append({
                    'type': 'GAMMA_SUPPORT',
                    'priority': 'HIGH' if abs_gex > 5 else 'MEDIUM',
                    'title': f'Gamma Support at ${strike:.2f}',
                    'message': f'Large positive GEX ({net_gex:.1f}B) creates buying interest',
                    'implications': [
                        f'Dealers must buy if price drops to ${strike:.2f}',
                        'Expect bounce from this level',
                        f'Target: ${spot_price + (spot_price - strike):.2f}'
                    ],
                    'confidence': min(90, int(60 + abs_gex * 3)),
                    'direction': 'BULLISH'
                })
            
            # High negative GEX = Resistance
            elif net_gex < -2.0 and spot_price < strike and distance < 2.0:
                signals.append({
                    'type': 'GAMMA_RESISTANCE',
                    'priority': 'HIGH' if abs_gex > 5 else 'MEDIUM',
                    'title': f'Gamma Resistance at ${strike:.2f}',
                    'message': f'Large negative GEX ({abs(net_gex):.1f}B) creates selling pressure',
                    'implications': [
                        f'Dealers must sell if price rallies to ${strike:.2f}',
                        'Expect rejection at this level',
                        f'Target: ${spot_price - (strike - spot_price):.2f}'
                    ],
                    'confidence': min(90, int(60 + abs_gex * 3)),
                    'direction': 'BEARISH'
                })
        
        # 3. Gamma Squeeze Potential
        if total_gex < -5.0:
            max_negative_idx = None
            max_negative_val = 0
            for i, gex in enumerate(net_gex_by_strike):
                if gex < max_negative_val:
                    max_negative_val = gex
                    max_negative_idx = i
            
            if max_negative_idx is not None:
                squeeze_strike = strikes[max_negative_idx]
                if spot_price < squeeze_strike:
                    distance_pct = (squeeze_strike - spot_price) / spot_price * 100
                    if distance_pct < 3.0:
                        signals.append({
                            'type': 'SQUEEZE_POTENTIAL',
                            'priority': 'HIGH',
                            'title': f'Gamma Squeeze Setup at ${squeeze_strike:.2f}',
                            'message': f'Break above ${squeeze_strike:.2f} could trigger squeeze ({abs(total_gex):.1f}B negative GEX)',
                            'implications': [
                                'Dealers are short gamma - must buy on rallies',
                                'Feedback loop potential if momentum builds',
                                f'Watch for volume spike above ${squeeze_strike:.2f}'
                            ],
                            'confidence': min(85, int(50 + abs(total_gex) * 2)),
                            'direction': 'BULLISH'
                        })
        
        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        signals.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return signals
    
    def get_dealer_positioning(self, gex_data):
        """Calculate and explain dealer positioning"""
        total_gex = gex_data.get('total_gex', 0)
        total_call = gex_data.get('total_call_gex', 0)
        total_put = gex_data.get('total_put_gex', 0)
        
        if total_gex > 0:
            position_type = "LONG"
            description = "Dealers are net long gamma"
            hedge_behavior = "Buy dips, sell rallies (stabilizing)"
            market_effect = "Mean reversion, pinning"
            risk = "Pin risk elevated"
        else:
            position_type = "SHORT"
            description = "Dealers are net short gamma"
            hedge_behavior = "Buy highs, sell lows (amplifying)"
            market_effect = "Trend following, momentum"
            risk = "Squeeze potential"
        
        shares_per_dollar = abs(total_gex) * 1e9 / 100
        
        return {
            'position_type': position_type,
            'total_gex': total_gex,
            'call_gex': total_call,
            'put_gex': total_put,
            'description': description,
            'hedge_behavior': hedge_behavior,
            'market_effect': market_effect,
            'risk': risk,
            'shares_per_dollar': shares_per_dollar,
            'regime': 'POSITIVE' if total_gex > 0 else 'NEGATIVE'
        }
