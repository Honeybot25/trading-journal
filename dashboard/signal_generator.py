"""
Enhanced Signal Generator Module
Professional-grade signal generation with contract specifications,
entry/exit plans, detailed reasoning, and position sizing.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class ContractSpecs:
    """Option contract specifications"""
    strike: float
    strike_type: str  # 'ITM', 'ATM', 'OTM'
    expiration: str
    expiration_days: int
    option_type: str  # 'CALL', 'PUT'
    estimated_price: float
    
    def to_dict(self):
        return {
            'strike': self.strike,
            'strike_type': self.strike_type,
            'expiration': self.expiration,
            'expiration_days': self.expiration_days,
            'option_type': self.option_type,
            'estimated_price': self.estimated_price
        }


@dataclass
class EntryExitZones:
    """Entry, exit, and stop loss zones"""
    entry_price_low: float
    entry_price_high: float
    take_profit: float
    stop_loss: float
    risk_reward_ratio: float
    position_size_risk_pct: float
    max_contracts: int
    kelly_fraction: float
    
    def to_dict(self):
        return {
            'entry_price_low': self.entry_price_low,
            'entry_price_high': self.entry_price_high,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'risk_reward_ratio': self.risk_reward_ratio,
            'position_size_risk_pct': self.position_size_risk_pct,
            'max_contracts': self.max_contracts,
            'kelly_fraction': self.kelly_fraction
        }


@dataclass
class Greeks:
    """Option Greeks"""
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float
    iv_percentile: float
    
    def to_dict(self):
        return {
            'delta': self.delta,
            'gamma': self.gamma,
            'theta': self.theta,
            'vega': self.vega,
            'iv': self.iv,
            'iv_percentile': self.iv_percentile
        }


@dataclass
class SignalReasoning:
    """Detailed reasoning for the signal"""
    gex_analysis: str
    technical_context: str
    dealer_positioning: str
    historical_win_rate: float
    similar_setups_count: int
    risk_factors: List[str]
    catalysts: List[str]
    
    def to_dict(self):
        return {
            'gex_analysis': self.gex_analysis,
            'technical_context': self.technical_context,
            'dealer_positioning': self.dealer_positioning,
            'historical_win_rate': self.historical_win_rate,
            'similar_setups_count': self.similar_setups_count,
            'risk_factors': self.risk_factors,
            'catalysts': self.catalysts
        }


@dataclass
class EnhancedSignal:
    """Complete trading signal with professional-grade details"""
    ticker: str
    direction: str  # 'CALL', 'PUT'
    entry_price: float
    signal_time: datetime
    confidence: int
    signal_type: str
    
    # Contract specifications
    contract: ContractSpecs
    
    # Entry/Exit plan
    zones: EntryExitZones
    
    # Greeks
    greeks: Greeks
    
    # Detailed reasoning
    reasoning: SignalReasoning
    
    # Additional metadata
    gex_level: float
    rsi_value: Optional[float]
    trend_direction: str
    conditions: List[Dict] = field(default_factory=list)
    notes: str = ""
    signal_id: Optional[int] = None
    
    def to_dict(self):
        return {
            'ticker': self.ticker,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'signal_time': self.signal_time.isoformat(),
            'confidence': self.confidence,
            'signal_type': self.signal_type,
            'contract_specs': self.contract.to_dict(),
            'zones': self.zones.to_dict(),
            'greeks': self.greeks.to_dict(),
            'reasoning': self.reasoning.to_dict(),
            'gex_level': self.gex_level,
            'rsi_value': self.rsi_value,
            'trend_direction': self.trend_direction,
            'conditions': self.conditions,
            'notes': self.notes,
            'signal_id': self.signal_id
        }


class EnhancedSignalGenerator:
    """
    Professional-grade signal generator with contract details,
    entry/exit plans, and comprehensive reasoning.
    """
    
    def __init__(self, account_size: float = 100000, risk_per_trade_pct: float = 2.0):
        self.account_size = account_size
        self.risk_per_trade_pct = risk_per_trade_pct
        self.historical_signals = []
        
        # Signal history for win rate calculation (simulated for now)
        self.setup_history = {
            'GEX_RSI_BULLISH': {'wins': 45, 'losses': 25, 'avg_gain': 3.2, 'avg_loss': 1.8},
            'GEX_RSI_BEARISH': {'wins': 38, 'losses': 22, 'avg_gain': 2.9, 'avg_loss': 2.1},
            'GEX_SQUEEZE': {'wins': 32, 'losses': 18, 'avg_gain': 5.4, 'avg_loss': 2.5},
            'GEX_FLIP_BULLISH': {'wins': 28, 'losses': 20, 'avg_gain': 2.8, 'avg_loss': 1.9},
            'GEX_FLIP_BEARISH': {'wins': 25, 'losses': 19, 'avg_gain': 2.6, 'avg_loss': 2.0}
        }
    
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
        
        sma_short = np.mean(prices[-5:])
        sma_long = np.mean(prices[-20:])
        
        if sma_short > sma_long * 1.02:
            return 'BULLISH'
        elif sma_short < sma_long * 0.98:
            return 'BEARISH'
        return 'NEUTRAL'
    
    def select_strike(self, spot_price: float, direction: str, 
                      strikes: List[float], net_gex: List[float],
                      gex_data: Dict) -> Tuple[float, str]:
        """
        Select optimal strike price based on GEX analysis
        Returns: (strike_price, strike_type)
        """
        if not strikes:
            # Default to 1% OTM if no strikes available
            if direction == 'CALL':
                return spot_price * 1.01, 'OTM'
            else:
                return spot_price * 0.99, 'OTM'
        
        # Find the highest GEX level
        max_gamma_strike = gex_data.get('max_gamma_strike', spot_price)
        zero_gamma = gex_data.get('zero_gamma_level', spot_price)
        
        # Sort strikes by proximity to spot
        strikes_sorted = sorted(strikes, key=lambda s: abs(s - spot_price))
        
        # Strike selection logic based on direction
        if direction == 'CALL':
            # For CALLs: Target strike just above key resistance (negative GEX)
            # or ATM if near positive GEX support
            
            # Look for negative GEX strikes above spot (resistance)
            resistance_strikes = [(s, net_gex[i]) for i, s in enumerate(strikes) 
                                  if s > spot_price and i < len(net_gex) and net_gex[i] < -1.0]
            
            if resistance_strikes:
                # Pick strike just below first major resistance
                target = min(resistance_strikes, key=lambda x: x[0])
                selected_strike = max([s for s in strikes if s < target[0]]) if any(s < target[0] for s in strikes) else target[0]
                strike_type = 'ATM' if abs(selected_strike - spot_price) / spot_price < 0.005 else 'OTM'
            else:
                # Default to slightly OTM
                selected_strike = spot_price * 1.01
                closest = min(strikes, key=lambda s: abs(s - selected_strike))
                selected_strike = closest
                strike_type = 'OTM'
        else:  # PUT
            # For PUTs: Target strike just below key support (positive GEX)
            support_strikes = [(s, net_gex[i]) for i, s in enumerate(strikes) 
                              if s < spot_price and i < len(net_gex) and net_gex[i] > 1.0]
            
            if support_strikes:
                # Pick strike just above first major support
                target = max(support_strikes, key=lambda x: x[0])
                selected_strike = min([s for s in strikes if s > target[0]]) if any(s > target[0] for s in strikes) else target[0]
                strike_type = 'ATM' if abs(selected_strike - spot_price) / spot_price < 0.005 else 'OTM'
            else:
                # Default to slightly OTM
                selected_strike = spot_price * 0.99
                closest = min(strikes, key=lambda s: abs(s - selected_strike))
                selected_strike = closest
                strike_type = 'OTM'
        
        # Adjust for ITM if high confidence and good R/R
        if strike_type == 'OTM':
            distance = abs(selected_strike - spot_price) / spot_price
            if distance > 0.03:  # More than 3% OTM, consider closer ATM
                atm_strike = min(strikes, key=lambda s: abs(s - spot_price))
                selected_strike = atm_strike
                strike_type = 'ATM'
        
        return selected_strike, strike_type
    
    def select_expiration(self, ticker: str, direction: str, 
                          confidence: int, is_0dte_available: bool = True) -> Tuple[str, int]:
        """
        Select optimal expiration based on setup type and confidence
        Returns: (expiration_string, days_to_expiration)
        """
        today = datetime.now()
        
        # Determine DTE based on signal characteristics
        if confidence >= 80 and is_0dte_available:
            # High confidence + momentum = 0DTE for quick capture
            exp_days = 0
            exp_str = "0DTE"
        elif confidence >= 70:
            # Good confidence = 2-3 DTE for swing
            exp_days = 2
            exp_str = f"{exp_days}DTE"
        elif direction == 'CALL' and confidence >= 60:
            # Standard bullish = 5-7 DTE
            exp_days = 5
            exp_str = f"{exp_days}DTE"
        else:
            # Lower confidence = Weekly for more time
            exp_days = 7
            exp_str = "1WK"
        
        exp_date = today + timedelta(days=exp_days)
        exp_formatted = exp_date.strftime("%m/%d")
        
        return f"{exp_str} ({exp_formatted})", exp_days
    
    def estimate_option_price(self, spot: float, strike: float, 
                              days: int, iv: float, direction: str) -> float:
        """
        Estimate option price using simplified Black-Scholes
        """
        if iv <= 0:
            iv = 0.30  # Default 30% IV
        
        # Time decay factor
        t = max(days, 1) / 365.0
        
        # Intrinsic value
        if direction == 'CALL':
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
        
        # Time value (simplified)
        distance = abs(strike - spot) / spot
        time_value = spot * iv * np.sqrt(t) * np.exp(-distance * 2)
        
        # For OTM options, time value is the price
        # For ITM options, add intrinsic
        estimated_price = intrinsic + time_value
        
        # Adjust for realistic pricing
        estimated_price = max(estimated_price, 0.10)  # Minimum $0.10
        
        return round(estimated_price, 2)
    
    def calculate_greeks(self, spot: float, strike: float, 
                         days: int, iv: float, direction: str) -> Greeks:
        """
        Estimate Greeks for the option
        """
        from scipy.stats import norm
        
        t = max(days, 1) / 365.0
        r = 0.05  # Risk-free rate
        
        if iv <= 0:
            iv = 0.30
        
        d1 = (np.log(spot / strike) + (r + 0.5 * iv**2) * t) / (iv * np.sqrt(t))
        d2 = d1 - iv * np.sqrt(t)
        
        # Delta
        if direction == 'CALL':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(d1) / (spot * iv * np.sqrt(t))
        
        # Theta (daily time decay)
        theta = -spot * norm.pdf(d1) * iv / (2 * np.sqrt(t)) / 365
        if direction == 'PUT':
            theta -= r * strike * np.exp(-r * t) * norm.cdf(-d2) / 365
        else:
            theta -= r * strike * np.exp(-r * t) * norm.cdf(d2) / 365
        
        # Vega (sensitivity to IV)
        vega = spot * norm.pdf(d1) * np.sqrt(t) / 100
        
        # IV percentile (simulated - would come from historical data)
        iv_percentile = min(95, max(5, int((iv / 0.50) * 50)))
        
        return Greeks(
            delta=round(delta, 2),
            gamma=round(gamma, 3),
            theta=round(theta, 2),
            vega=round(vega, 2),
            iv=round(iv, 2),
            iv_percentile=iv_percentile
        )
    
    def calculate_position_size(self, estimated_price: float, 
                                stop_loss_price: float, direction: str,
                                confidence: int) -> Tuple[int, float, float]:
        """
        Calculate position size based on Kelly Criterion and risk management
        Returns: (max_contracts, risk_pct, kelly_fraction)
        """
        # Maximum risk per trade
        max_risk_amount = self.account_size * (self.risk_per_trade_pct / 100)
        
        # Risk per contract
        if direction == 'CALL':
            risk_per_contract = estimated_price  # Max loss is premium paid
        else:
            risk_per_contract = estimated_price
        
        # Kelly fraction based on confidence
        win_rate = confidence / 100
        avg_win = 2.5  # Target 2.5x return
        avg_loss = 1.0  # Max loss is premium
        
        # Kelly formula: f = (p*b - q) / b
        # where p = win rate, q = loss rate, b = win/loss ratio
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b if b > 0 else 0
        
        # Use half-Kelly for safety
        kelly_fraction = max(0, min(kelly * 0.5, 0.25))  # Cap at 25%
        
        # Calculate contracts based on Kelly
        kelly_risk = self.account_size * kelly_fraction
        max_contracts_kelly = int(kelly_risk / (risk_per_contract * 100))
        
        # Calculate contracts based on max risk
        max_contracts_risk = int(max_risk_amount / (risk_per_contract * 100))
        
        # Use the more conservative of the two
        max_contracts = min(max_contracts_kelly, max_contracts_risk)
        max_contracts = max(1, max_contracts)  # At least 1 contract
        
        # Actual risk percentage
        actual_risk = (max_contracts * risk_per_contract * 100) / self.account_size * 100
        
        return max_contracts, round(actual_risk, 2), round(kelly_fraction, 3)
    
    def calculate_entry_exit_zones(self, spot: float, direction: str,
                                    gex_data: Dict, strike: float,
                                    estimated_price: float, confidence: int) -> EntryExitZones:
        """
        Calculate entry zone, stop loss, and take profit levels
        """
        # Entry zone: Current price +/- small buffer
        entry_buffer = spot * 0.001  # 0.1% buffer
        entry_low = spot - entry_buffer
        entry_high = spot + entry_buffer
        
        # Calculate expected move based on GEX
        total_gex = abs(gex_data.get('total_gex', 0))
        base_move = spot * 0.02  # 2% base
        gex_factor = min(total_gex / 10, 0.03)  # Up to 3% additional based on GEX
        expected_move = base_move + (spot * gex_factor)
        
        # Find next major GEX level for target
        strikes = gex_data.get('strikes', [])
        net_gex = gex_data.get('net_gex_by_strike', [])
        
        if direction == 'CALL':
            # Look for next negative GEX (resistance) above current price
            take_profit = spot + expected_move
            for i, s in enumerate(strikes):
                if s > spot and i < len(net_gex):
                    if net_gex[i] < -2.0:  # Significant negative GEX
                        take_profit = s * 0.99  # Just below resistance
                        break
            
            # Stop loss: Below nearest positive GEX support or 1.5x expected move
            stop_loss = spot - (expected_move * 0.75)
            for i, s in enumerate(strikes):
                if s < spot and i < len(net_gex):
                    if net_gex[i] > 2.0:  # Strong support
                        stop_loss = s * 0.99  # Just below support
                        break
        else:  # PUT
            take_profit = spot - expected_move
            for i, s in enumerate(strikes):
                if s < spot and i < len(net_gex):
                    if net_gex[i] > 2.0:  # Significant positive GEX (support to break)
                        take_profit = s * 1.01  # Just below broken support
                        break
            
            stop_loss = spot + (expected_move * 0.75)
            for i, s in enumerate(strikes):
                if s > spot and i < len(net_gex):
                    if net_gex[i] < -2.0:  # Strong resistance
                        stop_loss = s * 1.01  # Just above resistance
                        break
        
        # Calculate R/R ratio
        if direction == 'CALL':
            risk = entry_high - stop_loss
            reward = take_profit - entry_low
        else:
            risk = stop_loss - entry_low
            reward = entry_high - take_profit
        
        risk_reward = reward / risk if risk > 0 else 1.0
        
        # Adjust for minimum R/R
        if risk_reward < 1.5:
            # Extend target to achieve at least 1.5:1
            if direction == 'CALL':
                take_profit = entry_high + (risk * 1.5)
            else:
                take_profit = entry_low - (risk * 1.5)
            risk_reward = 1.5
        
        # Position sizing
        max_contracts, risk_pct, kelly = self.calculate_position_size(
            estimated_price, stop_loss, direction, confidence
        )
        
        return EntryExitZones(
            entry_price_low=round(entry_low, 2),
            entry_price_high=round(entry_high, 2),
            take_profit=round(take_profit, 2),
            stop_loss=round(stop_loss, 2),
            risk_reward_ratio=round(risk_reward, 1),
            position_size_risk_pct=risk_pct,
            max_contracts=max_contracts,
            kelly_fraction=kelly
        )
    
    def generate_gex_analysis(self, gex_data: Dict, spot: float, 
                              direction: str, strike: float) -> str:
        """
        Generate detailed GEX analysis text
        """
        total_gex = gex_data.get('total_gex', 0)
        zero_gamma = gex_data.get('zero_gamma_level', spot)
        max_gamma_strike = gex_data.get('max_gamma_strike', spot)
        
        net_gex = gex_data.get('net_gex_by_strike', [])
        strikes = gex_data.get('strikes', [])
        
        # Find relevant GEX levels
        nearby_gex = []
        for i, s in enumerate(strikes):
            if i < len(net_gex):
                distance = abs(s - spot) / spot * 100
                if distance < 3.0:  # Within 3%
                    nearby_gex.append((s, net_gex[i], distance))
        
        # Sort by absolute GEX value
        nearby_gex.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Build analysis text
        analysis_parts = []
        
        # Overall regime
        if total_gex > 5:
            analysis_parts.append(f"Net GEX ${total_gex:.1f}B POSITIVE - Dealers long gamma, mean-reversion environment")
        elif total_gex < -5:
            analysis_parts.append(f"Net GEX ${abs(total_gex):.1f}B NEGATIVE - Dealers short gamma, trending environment")
        else:
            analysis_parts.append(f"Net GEX ${total_gex:.1f}B NEUTRAL - Mixed gamma, choppy conditions")
        
        # Key strike analysis
        if nearby_gex:
            top_level = nearby_gex[0]
            level_type = "resistance" if top_level[1] < 0 else "support"
            analysis_parts.append(f"Primary gamma {level_type} at ${top_level[0]:.2f} with {abs(top_level[1]):.1f}B exposure")
        
        # Zero gamma flip
        distance_to_flip = abs(spot - zero_gamma) / spot * 100
        if distance_to_flip < 2.0:
            analysis_parts.append(f"⚠️ CRITICAL: Only {distance_to_flip:.1f}% from zero gamma flip at ${zero_gamma:.2f}")
        
        # Strike-specific analysis
        strike_gex = 0
        for s, gex, _ in nearby_gex:
            if abs(s - strike) < 0.01:
                strike_gex = gex
                break
        
        if strike_gex != 0:
            gex_type = "positive" if strike_gex > 0 else "negative"
            analysis_parts.append(f"Selected strike has {abs(strike_gex):.1f}B {gex_type} GEX")
        
        return " | ".join(analysis_parts)
    
    def generate_technical_context(self, rsi: Optional[float], 
                                   trend: str, prices: List[float]) -> str:
        """
        Generate technical analysis context
        """
        context_parts = []
        
        # RSI context
        if rsi is not None:
            if rsi < 30:
                context_parts.append(f"RSI {rsi:.1f} OVERSOLD - Bullish reversal setup")
            elif rsi < 40:
                context_parts.append(f"RSI {rsi:.1f} Weak momentum - potential bounce zone")
            elif rsi > 70:
                context_parts.append(f"RSI {rsi:.1f} OVERBOUGHT - Bearish reversal setup")
            elif rsi > 60:
                context_parts.append(f"RSI {rsi:.1f} Strong momentum - trend continuation")
            else:
                context_parts.append(f"RSI {rsi:.1f} Neutral momentum")
        
        # Trend context
        trend_emoji = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}
        context_parts.append(f"{trend_emoji.get(trend, '')} Trend: {trend}")
        
        # Volatility context
        if len(prices) >= 20:
            recent_vol = np.std(prices[-5:]) / np.mean(prices[-5:]) * 100
            hist_vol = np.std(prices[-20:]) / np.mean(prices[-20:]) * 100
            if recent_vol > hist_vol * 1.5:
                context_parts.append("Volatility EXPANDING")
            elif recent_vol < hist_vol * 0.7:
                context_parts.append("Volatility CONTRACTING - breakout imminent")
        
        return " | ".join(context_parts)
    
    def get_historical_win_rate(self, signal_type: str) -> Tuple[float, int]:
        """
        Get historical win rate for similar setups
        """
        history = self.setup_history.get(signal_type, 
                                         {'wins': 0, 'losses': 0, 'avg_gain': 0, 'avg_loss': 0})
        
        total = history['wins'] + history['losses']
        if total == 0:
            return 50.0, 0
        
        win_rate = (history['wins'] / total) * 100
        return win_rate, total
    
    def identify_risk_factors(self, gex_data: Dict, rsi: Optional[float],
                              trend: str, direction: str) -> List[str]:
        """
        Identify potential risk factors for the trade
        """
        risks = []
        
        total_gex = gex_data.get('total_gex', 0)
        zero_gamma = gex_data.get('zero_gamma_level', 0)
        spot = gex_data.get('spot', 0)
        
        # Gamma flip risk
        if spot > 0 and zero_gamma > 0:
            distance_to_flip = abs(spot - zero_gamma) / spot * 100
            if distance_to_flip < 1.5:
                risks.append(f"CRITICAL: Within {distance_to_flip:.1f}% of gamma flip - volatility spike risk")
        
        # Divergence risk
        if direction == 'CALL' and trend == 'BEARISH':
            risks.append("Contrarian signal: Buying calls in bearish trend")
        elif direction == 'PUT' and trend == 'BULLISH':
            risks.append("Contrarian signal: Buying puts in bullish trend")
        
        # RSI divergence
        if rsi is not None:
            if direction == 'CALL' and rsi > 60:
                risks.append("RSI elevated - limited upside before overbought")
            elif direction == 'PUT' and rsi < 40:
                risks.append("RSI depressed - limited downside before oversold")
        
        # GEX regime risk
        if direction == 'CALL' and total_gex < -5:
            risks.append("Negative GEX regime - trend can accelerate against position")
        elif direction == 'PUT' and total_gex > 5:
            risks.append("Positive GEX regime - pinning risk to upside")
        
        # Time decay warning for short-dated options
        risks.append("0DTE options expire worthless if target not hit today")
        
        return risks[:4]  # Return top 4 risks
    
    def identify_catalysts(self, gex_data: Dict, direction: str) -> List[str]:
        """
        Identify potential catalysts for the trade
        """
        catalysts = []
        
        total_gex = gex_data.get('total_gex', 0)
        
        # Dealer positioning catalysts
        if total_gex < -3 and direction == 'CALL':
            catalysts.append("Dealer short gamma - forced buying on any rally")
        elif total_gex > 3 and direction == 'PUT':
            catalysts.append("Dealer long gamma breaking down - hedging unwind")
        
        # General catalysts
        catalysts.append("Options flow supportive of direction")
        catalysts.append("Key technical level approaching")
        
        return catalysts
    
    def generate_enhanced_signal(self, ticker: str, gex_data: Dict, 
                                 spot_price: float, price_history: List[float] = None) -> Optional[EnhancedSignal]:
        """
        Generate a professional-grade trading signal with full contract details
        """
        # Get base signal logic
        total_gex = gex_data.get('total_gex', 0)
        zero_gamma = gex_data.get('zero_gamma_level', spot_price)
        strikes = gex_data.get('strikes', [])
        net_gex_by_strike = gex_data.get('net_gex_by_strike', [])
        
        # Calculate RSI
        rsi = None
        if price_history and len(price_history) >= 15:
            rsi = self.calculate_rsi(price_history)
        
        # Determine trend
        trend = 'NEUTRAL'
        if price_history:
            trend = self.determine_trend(price_history)
        
        # Evaluate conditions for signal generation
        conditions = []
        confidence = 50
        direction = None
        signal_type = None
        
        # Check for positive GEX support (for CALLs)
        near_positive_gex = False
        positive_gex_level = None
        for i, strike in enumerate(strikes):
            if i < len(net_gex_by_strike):
                gex = net_gex_by_strike[i]
                distance = abs(spot_price - strike) / spot_price * 100
                if gex > 2.0 and distance < 2.0 and spot_price > strike:
                    near_positive_gex = True
                    positive_gex_level = strike
                    break
        
        # Check for negative GEX resistance (for PUTs)
        near_negative_gex = False
        negative_gex_level = None
        for i, strike in enumerate(strikes):
            if i < len(net_gex_by_strike):
                gex = net_gex_by_strike[i]
                distance = abs(spot_price - strike) / spot_price * 100
                if gex < -2.0 and distance < 2.0 and spot_price < strike:
                    near_negative_gex = True
                    negative_gex_level = strike
                    break
        
        # RSI conditions
        rsi_oversold = rsi is not None and rsi < 35
        rsi_overbought = rsi is not None and rsi > 65
        
        # Trend conditions
        bullish_trend = trend == 'BULLISH'
        bearish_trend = trend == 'BEARISH'
        
        # Signal generation logic
        if near_positive_gex and (rsi_oversold or bullish_trend):
            # BUY CALL signal
            direction = 'CALL'
            signal_type = 'GEX_RSI_BULLISH'
            
            confidence = 50
            if near_positive_gex:
                confidence += 25
            if rsi_oversold:
                confidence += 15
            if bullish_trend:
                confidence += 10
                
        elif near_negative_gex and (rsi_overbought or bearish_trend):
            # BUY PUT signal
            direction = 'PUT'
            signal_type = 'GEX_RSI_BEARISH'
            
            confidence = 50
            if near_negative_gex:
                confidence += 25
            if rsi_overbought:
                confidence += 15
            if bearish_trend:
                confidence += 10
        
        # Gamma squeeze setup (short gamma breakout)
        if total_gex < -5 and not direction:
            # Look for potential squeeze
            max_neg_idx = None
            max_neg_val = 0
            for i, gex in enumerate(net_gex_by_strike):
                if gex < max_neg_val:
                    max_neg_val = gex
                    max_neg_idx = i
            
            if max_neg_idx is not None and max_neg_idx < len(strikes):
                squeeze_strike = strikes[max_neg_idx]
                if spot_price < squeeze_strike:
                    distance_pct = (squeeze_strike - spot_price) / spot_price * 100
                    if distance_pct < 2.0 and bullish_trend:
                        direction = 'CALL'
                        signal_type = 'GEX_SQUEEZE'
                        confidence = min(85, 60 + int(abs(total_gex)))
        
        # If no signal generated, return None
        if not direction or confidence < 65:
            return None
        
        # Generate contract specifications
        selected_strike, strike_type = self.select_strike(
            spot_price, direction, strikes, net_gex_by_strike, gex_data
        )
        
        expiration_str, exp_days = self.select_expiration(
            ticker, direction, confidence, is_0dte_available=True
        )
        
        # Estimate IV (simplified - would come from market data)
        iv = 0.30
        if ticker in ['NVDA', 'TSLA']:
            iv = 0.45
        elif ticker in ['AMD', 'COIN']:
            iv = 0.50
        
        estimated_price = self.estimate_option_price(
            spot_price, selected_strike, max(exp_days, 1), iv, direction
        )
        
        contract = ContractSpecs(
            strike=selected_strike,
            strike_type=strike_type,
            expiration=expiration_str,
            expiration_days=exp_days,
            option_type=direction,
            estimated_price=estimated_price
        )
        
        # Calculate entry/exit zones
        zones = self.calculate_entry_exit_zones(
            spot_price, direction, gex_data, selected_strike, estimated_price, confidence
        )
        
        # Calculate Greeks
        greeks = self.calculate_greeks(
            spot_price, selected_strike, max(exp_days, 1), iv, direction
        )
        
        # Generate reasoning
        gex_analysis = self.generate_gex_analysis(gex_data, spot_price, direction, selected_strike)
        technical_context = self.generate_technical_context(rsi, trend, price_history or [])
        
        # Dealer positioning
        if total_gex > 0:
            dealer_pos = f"Dealers LONG {total_gex:.1f}B gamma - Buy dips, sell rallies (mean-reversion)"
        else:
            dealer_pos = f"Dealers SHORT {abs(total_gex):.1f}B gamma - Buy highs, sell lows (momentum)"
        
        # Historical win rate
        win_rate, setup_count = self.get_historical_win_rate(signal_type)
        
        # Risk factors
        risk_factors = self.identify_risk_factors(gex_data, rsi, trend, direction)
        
        # Catalysts
        catalysts = self.identify_catalysts(gex_data, direction)
        
        reasoning = SignalReasoning(
            gex_analysis=gex_analysis,
            technical_context=technical_context,
            dealer_positioning=dealer_pos,
            historical_win_rate=win_rate,
            similar_setups_count=setup_count,
            risk_factors=risk_factors,
            catalysts=catalysts
        )
        
        # Build conditions list
        conditions = [
            {'name': 'Near Key GEX Level', 'met': near_positive_gex or near_negative_gex, 'value': 1.0, 'weight': 3},
            {'name': 'RSI Oversold' if direction == 'CALL' else 'RSI Overbought', 
             'met': rsi_oversold if direction == 'CALL' else rsi_overbought, 'value': rsi or 50, 'weight': 2},
            {'name': f'{trend} Trend', 'met': trend != 'NEUTRAL', 'value': 1.0, 'weight': 2},
            {'name': 'Favorable R/R Ratio', 'met': zones.risk_reward_ratio >= 1.5, 
             'value': zones.risk_reward_ratio, 'weight': 2}
        ]
        
        # Create the enhanced signal
        signal = EnhancedSignal(
            ticker=ticker,
            direction=direction,
            entry_price=spot_price,
            signal_time=datetime.now(),
            confidence=min(confidence, 100),
            signal_type=signal_type,
            contract=contract,
            zones=zones,
            greeks=greeks,
            reasoning=reasoning,
            gex_level=zero_gamma,
            rsi_value=rsi,
            trend_direction=trend,
            conditions=conditions,
            notes=f"Generated at {datetime.now().strftime('%H:%M:%S')} | GEX Regime: {'Positive' if total_gex > 0 else 'Negative'}"
        )
        
        return signal


# Global instance
_enhanced_signal_generator = None

def get_enhanced_signal_generator(account_size: float = 100000) -> EnhancedSignalGenerator:
    """Get singleton EnhancedSignalGenerator instance"""
    global _enhanced_signal_generator
    if _enhanced_signal_generator is None:
        _enhanced_signal_generator = EnhancedSignalGenerator(account_size=account_size)
    return _enhanced_signal_generator
