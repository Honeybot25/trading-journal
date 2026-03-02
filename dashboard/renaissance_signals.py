"""
Renaissance-Style Quantitative Signal Generator
Multi-factor alpha generation with edge metrics
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SignalProximity(Enum):
    """How close we are to a signal"""
    FAR = "far"
    APPROACHING = "approaching" 
    NEAR = "near"
    TRIGGERED = "triggered"


@dataclass
class EdgeMetrics:
    """Alpha and edge calculations"""
    expected_value: float
    win_probability: float
    risk_reward_ratio: float
    sharpe_estimate: float
    confidence_interval: Tuple[float, float]
    historical_win_rate: float
    optimal_position_size: float


@dataclass
class SignalContext:
    """Full context for why/why not trading"""
    proximity: SignalProximity
    distance_to_signal: float  # Percentage
    current_price: float
    trigger_price: float
    direction: str
    
    # Renaissance-style factors
    mean_reversion_score: float  # -1 to 1
    momentum_score: float  # -1 to 1
    volatility_regime: str  # low, normal, high
    correlation_to_market: float
    
    # Edge metrics
    edge_metrics: EdgeMetrics
    
    # Decision logic
    should_trade: bool
    reason: str
    alternative_action: str
    

class RenaissanceSignalEngine:
    """
    Multi-factor signal engine inspired by Renaissance Technologies
    Combines: Mean reversion, momentum, statistical arbitrage, microstructure
    """
    
    def __init__(self):
        self.lookback_periods = [5, 10, 20, 60]  # Multiple timeframes
        self.factor_weights = {
            'mean_reversion': 0.25,
            'momentum': 0.25,
            'volatility': 0.20,
            'microstructure': 0.15,
            'correlation': 0.15
        }
    
    def calculate_mean_reversion_score(self, price_history: pd.Series) -> float:
        """
        Mean reversion score (-1 to 1)
        Positive = expect bounce back
        Negative = expect continued trend
        """
        if len(price_history) < 20:
            return 0.0
        
        # Z-score of price relative to moving averages
        sma_5 = price_history.rolling(5).mean().iloc[-1]
        sma_20 = price_history.rolling(20).mean().iloc[-1]
        current_price = price_history.iloc[-1]
        
        # Distance from moving averages
        dist_from_sma5 = (current_price - sma_5) / sma_5
        dist_from_sma20 = (current_price - sma_20) / sma_20
        
        # Mean reversion: if price is far above/below MA, expect reversal
        z_score = (dist_from_sma5 + dist_from_sma20) / 2
        
        # Normalize to -1 to 1
        return np.clip(z_score * 10, -1, 1)
    
    def calculate_momentum_score(self, price_history: pd.Series) -> float:
        """
        Momentum score (-1 to 1)
        Positive = upward momentum
        Negative = downward momentum
        """
        if len(price_history) < 20:
            return 0.0
        
        # Multiple timeframe momentum
        returns_5d = (price_history.iloc[-1] / price_history.iloc[-5] - 1)
        returns_20d = (price_history.iloc[-1] / price_history.iloc[-20] - 1)
        
        # Normalize
        momentum = (returns_5d * 0.7 + returns_20d * 0.3) * 10
        return np.clip(momentum, -1, 1)
    
    def calculate_volatility_regime(self, price_history: pd.Series) -> Tuple[str, float]:
        """
        Determine current volatility regime
        Returns: regime, current_volatility
        """
        if len(price_history) < 20:
            return "unknown", 0.0
        
        returns = price_history.pct_change().dropna()
        current_vol = returns.rolling(20).std().iloc[-1] * np.sqrt(252)  # Annualized
        
        # Historical vol for comparison
        historical_vol = returns.std() * np.sqrt(252)
        
        if current_vol < historical_vol * 0.8:
            regime = "low"
        elif current_vol > historical_vol * 1.2:
            regime = "high"
        else:
            regime = "normal"
        
        return regime, current_vol
    
    def calculate_edge_metrics(self, 
                              price: float,
                              strike: float,
                              signal_direction: str,
                              price_history: pd.Series) -> EdgeMetrics:
        """
        Calculate expected value and edge metrics
        """
        # Win probability based on historical GEX signals
        if len(price_history) >= 60:
            # Calculate historical edge
            returns = price_history.pct_change().dropna()
            
            # Historical win rate for similar setups
            if signal_direction == "CALL":
                wins = (returns > 0).sum()
            else:
                wins = (returns < 0).sum()
            
            historical_win_rate = wins / len(returns)
        else:
            historical_win_rate = 0.52  # Default slight edge
        
        # Expected move calculation (1 standard deviation)
        if len(price_history) >= 20:
            volatility = price_history.pct_change().rolling(20).std().iloc[-1]
            expected_move = price * volatility * np.sqrt(30/252)  # 30-day expected move
        else:
            expected_move = price * 0.02  # Default 2%
        
        # Risk/Reward based on GEX levels
        entry = price
        target = strike * 1.05 if signal_direction == "CALL" else strike * 0.95
        stop = strike * 0.97 if signal_direction == "CALL" else strike * 1.03
        
        risk = abs(entry - stop)
        reward = abs(target - entry)
        risk_reward = reward / risk if risk > 0 else 1.0
        
        # Expected value calculation
        win_prob = historical_win_rate
        loss_prob = 1 - win_prob
        
        expected_value = (win_prob * reward) - (loss_prob * risk)
        expected_value_pct = (expected_value / entry) * 100
        
        # Sharpe estimate (simplified)
        sharpe = (expected_value_pct / (volatility * 100 * np.sqrt(252))) if volatility > 0 else 0.5
        
        # Confidence interval (95%)
        margin_of_error = 1.96 * volatility * price * np.sqrt(30/252)
        conf_interval = (price - margin_of_error, price + margin_of_error)
        
        # Optimal position size (Kelly Criterion simplified)
        kelly = win_prob - ((1 - win_prob) / risk_reward) if risk_reward > 0 else 0.0
        position_size = min(kelly * 0.5, 0.05)  # Half Kelly, max 5%
        
        return EdgeMetrics(
            expected_value=expected_value_pct,
            win_probability=win_prob * 100,
            risk_reward_ratio=risk_reward,
            sharpe_estimate=sharpe,
            confidence_interval=conf_interval,
            historical_win_rate=historical_win_rate * 100,
            optimal_position_size=position_size * 100
        )
    
    def generate_enhanced_context(self,
                                  ticker: str,
                                  current_price: float,
                                  gex_data: Dict,
                                  price_history: pd.Series,
                                  market_correlation: float = 0.7) -> SignalContext:
        """
        Generate full context for why/why not taking a trade
        """
        # Calculate proximity to signal
        zero_gamma = gex_data.get('zero_gamma', current_price)
        max_gamma_strike = gex_data.get('max_gamma_strike', current_price)
        
        # Distance to zero gamma (main signal trigger)
        distance_to_zero = abs(current_price - zero_gamma) / current_price
        
        # Determine proximity
        if distance_to_zero < 0.001:  # Within 0.1%
            proximity = SignalProximity.TRIGGERED
            direction = "BUY CALL" if current_price > zero_gamma else "BUY PUT"
            trigger_price = zero_gamma
        elif distance_to_zero < 0.005:  # Within 0.5%
            proximity = SignalProximity.NEAR
            direction = "BUY CALL" if current_price > zero_gamma else "BUY PUT"
            trigger_price = zero_gamma
        elif distance_to_zero < 0.01:  # Within 1%
            proximity = SignalProximity.APPROACHING
            direction = "NEUTRAL"
            trigger_price = zero_gamma
        else:
            proximity = SignalProximity.FAR
            direction = "NEUTRAL"
            trigger_price = zero_gamma
        
        # Calculate Renaissance-style factors
        mr_score = self.calculate_mean_reversion_score(price_history)
        mom_score = self.calculate_momentum_score(price_history)
        vol_regime, _ = self.calculate_volatility_regime(price_history)
        
        # Calculate edge metrics
        edge = self.calculate_edge_metrics(
            current_price, 
            max_gamma_strike if max_gamma_strike else current_price,
            direction if direction != "NEUTRAL" else "CALL",
            price_history
        )
        
        # Decision logic
        should_trade = False
        reason = ""
        alternative_action = ""
        
        if proximity == SignalProximity.TRIGGERED:
            # Check if edge is favorable
            if edge.expected_value > 1.0 and edge.sharpe_estimate > 0.5:
                should_trade = True
                reason = f"Signal triggered with positive edge ({edge.expected_value:.2f}%)"
            else:
                should_trade = False
                reason = f"Signal triggered but edge insufficient ({edge.expected_value:.2f}%)"
                alternative_action = "Wait for better entry or stronger edge"
        elif proximity == SignalProximity.NEAR:
            should_trade = False
            reason = f"Price near signal zone ({distance_to_zero*100:.2f}% away)"
            if mr_score > 0.3:
                alternative_action = "Price stretched - mean reversion likely, wait for entry"
            elif mom_score > 0.3:
                alternative_action = "Momentum building - may break through soon"
            else:
                alternative_action = "Monitor for confirmation"
        elif proximity == SignalProximity.APPROACHING:
            should_trade = False
            reason = f"Approaching signal zone ({distance_to_zero*100:.2f}% away)"
            alternative_action = "Set alerts for when price reaches zero gamma"
        else:
            should_trade = False
            reason = f"Far from signal zone ({distance_to_zero*100:.2f}% away)"
            alternative_action = "No action needed - monitor other tickers"
        
        return SignalContext(
            proximity=proximity,
            distance_to_signal=distance_to_zero * 100,
            current_price=current_price,
            trigger_price=trigger_price,
            direction=direction,
            mean_reversion_score=mr_score,
            momentum_score=mom_score,
            volatility_regime=vol_regime,
            correlation_to_market=market_correlation,
            edge_metrics=edge,
            should_trade=should_trade,
            reason=reason,
            alternative_action=alternative_action
        )


# Global instance
renaissance_engine = RenaissanceSignalEngine()


def get_renaissance_engine() -> RenaissanceSignalEngine:
    """Get the Renaissance signal engine"""
    return renaissance_engine
