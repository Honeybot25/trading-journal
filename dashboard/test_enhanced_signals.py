#!/usr/bin/env python3
"""
Test script for Enhanced Signal Generator
Tests signal generation with SPY, QQQ, and NVDA
"""

import sys
sys.path.insert(0, '/Users/Honeybot/.openclaw/workspace/trading/dashboard')

import numpy as np
from datetime import datetime
from signal_generator import EnhancedSignalGenerator, get_enhanced_signal_generator
from gex_calculator import GEXCalculator

def create_sample_gex_data(ticker, spot_price):
    """Create realistic GEX data for testing"""
    calc = GEXCalculator()
    
    # Generate realistic strikes around spot price
    strike_range = 0.15
    num_strikes = 21
    
    strikes = np.linspace(
        spot_price * (1 - strike_range),
        spot_price * (1 + strike_range),
        num_strikes
    )
    
    # Generate realistic GEX profile based on ticker
    call_gex = []
    put_gex = []
    net_gex = []
    
    for strike in strikes:
        distance = abs(strike - spot_price) / spot_price
        
        # Simulate gamma concentration near spot
        if ticker == 'SPY':
            # SPY typically has balanced GEX
            base_gamma = max(0, 1 - distance * 3)
            call_oi = base_gamma * 40000 * (1.2 if strike > spot_price else 0.8)
            put_oi = base_gamma * 40000 * (0.8 if strike > spot_price else 1.2)
        elif ticker == 'QQQ':
            # QQQ can have tech-driven skew
            base_gamma = max(0, 1 - distance * 4)
            call_oi = base_gamma * 35000 * (1.3 if strike > spot_price else 0.7)
            put_oi = base_gamma * 35000 * (0.7 if strike > spot_price else 1.3)
        else:  # NVDA
            # NVDA has higher gamma due to volatility
            base_gamma = max(0, 1 - distance * 5)
            call_oi = base_gamma * 25000 * (1.4 if strike > spot_price else 0.6)
            put_oi = base_gamma * 25000 * (0.6 if strike > spot_price else 1.4)
        
        call_gex_val = base_gamma * 0.05 * call_oi * 100 * spot_price / 1e9
        put_gex_val = base_gamma * 0.05 * put_oi * 100 * spot_price / 1e9
        
        call_gex.append(call_gex_val)
        put_gex.append(put_gex_val)
        net_gex.append(call_gex_val - put_gex_val)
    
    # Add some significant gamma levels for signals
    # Create conditions that trigger signals:
    # For CALL signals: Need price > strike with strong positive GEX below
    # For PUT signals: Need price < strike with strong negative GEX above
    
    spot_idx = np.searchsorted(strikes, spot_price)
    
    # Create strong positive GEX support just below spot (for CALL signals)
    if spot_idx > 1:
        support_idx = spot_idx - 1
        net_gex[support_idx] = 8.5  # Very strong positive GEX
        net_gex[support_idx - 1] = 4.2
    
    # Create strong negative GEX resistance just above spot (for PUT signals)
    if spot_idx < len(strikes) - 2:
        resistance_idx = spot_idx + 1
        net_gex[resistance_idx] = -7.8  # Very strong negative GEX
        net_gex[resistance_idx + 1] = -3.5
    
    total_call = sum(call_gex)
    total_put = sum(put_gex)
    
    # Find max gamma strike
    abs_gex = [abs(x) for x in net_gex]
    max_gamma_idx = abs_gex.index(max(abs_gex))
    
    # Calculate zero gamma level
    zero_gamma = spot_price
    for i in range(len(net_gex) - 1):
        if net_gex[i] * net_gex[i+1] < 0:
            t = abs(net_gex[i]) / (abs(net_gex[i]) + abs(net_gex[i+1]))
            zero_gamma = strikes[i] + t * (strikes[i+1] - strikes[i])
            break
    
    return {
        'strikes': strikes.tolist(),
        'call_gex': call_gex,
        'put_gex': put_gex,
        'net_gex_by_strike': net_gex,
        'heatmap_data': [],  # Simplified for test
        'zero_gamma_level': zero_gamma,
        'max_gamma_strike': strikes[max_gamma_idx],
        'max_put_strike': strikes[put_gex.index(max(put_gex))],
        'max_call_strike': strikes[call_gex.index(max(call_gex))],
        'total_gex': total_call - total_put,
        'put_call_ratio': total_put / total_call if total_call > 0 else 1.0,
        'net_gex': total_call - total_put,
        'spot': spot_price
    }

def create_price_history(ticker, current_price, trend='neutral'):
    """Create sample price history with trend"""
    days = 30
    prices = []
    
    if trend == 'bullish':
        # Upward trend
        for i in range(days):
            price = current_price * (0.95 + (i / days) * 0.10)
            prices.append(price + np.random.normal(0, current_price * 0.005))
    elif trend == 'bearish':
        # Downward trend
        for i in range(days):
            price = current_price * (1.05 - (i / days) * 0.10)
            prices.append(price + np.random.normal(0, current_price * 0.005))
    else:
        # Sideways with RSI setup
        for i in range(days):
            price = current_price * (1 + np.sin(i * 0.3) * 0.02)
            prices.append(price + np.random.normal(0, current_price * 0.005))
    
    return prices

def test_signal_generator():
    """Test the enhanced signal generator"""
    print("=" * 80)
    print("ENHANCED SIGNAL GENERATOR TEST")
    print("=" * 80)
    
    # Initialize generator
    generator = get_enhanced_signal_generator(account_size=100000)
    
    test_cases = [
        ('SPY', 600.00, 'bullish'),
        ('QQQ', 500.00, 'neutral'),
        ('NVDA', 130.00, 'bearish')
    ]
    
    for ticker, spot, trend in test_cases:
        print(f"\n{'='*80}")
        print(f"TESTING: {ticker} @ ${spot:.2f} ({trend.upper()} TREND)")
        print(f"{'='*80}")
        
        # Create test data
        gex_data = create_sample_gex_data(ticker, spot)
        price_history = create_price_history(ticker, spot, trend)
        
        # Generate signal
        signal = generator.generate_enhanced_signal(ticker, gex_data, spot, price_history)
        
        if signal:
            print(f"\n🎯 SIGNAL GENERATED!")
            print(f"   Direction: {'🟢 BUY CALL' if signal.direction == 'CALL' else '🔴 BUY PUT'}")
            print(f"   Confidence: {signal.confidence}%")
            print(f"   Signal Type: {signal.signal_type}")
            
            print(f"\n📋 CONTRACT SPECIFICATIONS:")
            print(f"   Ticker: {signal.ticker}")
            print(f"   Strike: ${signal.contract.strike:.2f} ({signal.contract.strike_type})")
            print(f"   Expiration: {signal.contract.expiration}")
            print(f"   Option Type: {signal.contract.option_type}")
            print(f"   Est. Price: ${signal.contract.estimated_price:.2f}")
            
            print(f"\n🎯 ENTRY/EXIT PLAN:")
            print(f"   Entry Zone: ${signal.zones.entry_price_low:.2f} - ${signal.zones.entry_price_high:.2f}")
            print(f"   Stop Loss: ${signal.zones.stop_loss:.2f}")
            print(f"   Take Profit: ${signal.zones.take_profit:.2f}")
            print(f"   Risk/Reward: {signal.zones.risk_reward_ratio}:1")
            
            print(f"\n💰 POSITION SIZING:")
            print(f"   Risk %: {signal.zones.position_size_risk_pct}%")
            print(f"   Max Contracts: {signal.zones.max_contracts}")
            print(f"   Kelly Fraction: {signal.zones.kelly_fraction}")
            max_loss = signal.zones.max_contracts * signal.contract.estimated_price * 100
            print(f"   Max Loss: ${max_loss:.2f}")
            
            print(f"\n📊 GREEKS:")
            print(f"   Delta: {signal.greeks.delta}")
            print(f"   Gamma: {signal.greeks.gamma}")
            print(f"   Theta: {signal.greeks.theta}")
            print(f"   Vega: {signal.greeks.vega}")
            print(f"   IV: {signal.greeks.iv*100:.0f}% ({signal.greeks.iv_percentile}p)")
            
            print(f"\n💡 REASONING:")
            print(f"   GEX Analysis: {signal.reasoning.gex_analysis[:100]}...")
            print(f"   Technical: {signal.reasoning.technical_context}")
            print(f"   Dealer Position: {signal.reasoning.dealer_positioning}")
            print(f"   Historical Win Rate: {signal.reasoning.historical_win_rate:.0f}%")
            print(f"   Similar Setups: {signal.reasoning.similar_setups_count}")
            
            print(f"\n⚠️  RISK FACTORS:")
            for risk in signal.reasoning.risk_factors:
                print(f"   • {risk}")
            
            print(f"\n🚀 CATALYSTS:")
            for catalyst in signal.reasoning.catalysts:
                print(f"   • {catalyst}")
            
            print(f"\n📈 CONDITIONS MET:")
            for cond in signal.conditions:
                status = "✅" if cond['met'] else "❌"
                print(f"   {status} {cond['name']} (weight: {cond['weight']})")
        else:
            print(f"\n⏸️  No signal generated for {ticker}")
            print(f"   (Conditions not met - need stronger GEX setup)")
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}")

if __name__ == '__main__':
    test_signal_generator()
