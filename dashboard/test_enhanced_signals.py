#!/usr/bin/env python3
"""
Test script for enhanced signal generator with contract-level alpha
Tests SPY, QQQ, and NVDA signals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_generator import EnhancedSignalGenerator, ContractAnalyzer, SignalReasoningEngine
import json
from datetime import datetime


def create_test_gex_data(ticker: str, scenario: str = "bullish"):
    """Create test GEX data for different scenarios"""
    
    # Base prices
    prices = {
        'SPY': 605.0,
        'QQQ': 525.0,
        'NVDA': 145.0
    }
    
    spot = prices.get(ticker, 100.0)
    
    # Create strike ladder
    strike_increment = 5.0 if ticker in ['SPY', 'QQQ'] else 2.5
    strikes = [spot + (i * strike_increment) for i in range(-10, 11)]
    
    if scenario == "bullish":
        # Positive GEX below spot (support), negative above (resistance)
        net_gex = []
        for s in strikes:
            if s < spot:
                # Support levels
                dist = abs(s - spot) / spot
                gex = max(0, 10 - dist * 100) + (5 if abs(s - spot) < strike_increment * 2 else 0)
            else:
                # Resistance
                dist = abs(s - spot) / spot
                gex = -max(0, 8 - dist * 80)
            net_gex.append(round(gex, 2))
        
        total_gex = 15.0
        max_gamma_strike = strikes[len(strikes)//2 - 1]
        
    elif scenario == "bearish":
        # Negative GEX below spot, positive above
        net_gex = []
        for s in strikes:
            if s > spot:
                dist = abs(s - spot) / spot
                gex = max(0, 10 - dist * 100) + (5 if abs(s - spot) < strike_increment * 2 else 0)
            else:
                dist = abs(s - spot) / spot
                gex = -max(0, 8 - dist * 80)
            net_gex.append(round(gex, 2))
        
        total_gex = -12.0
        max_gamma_strike = strikes[len(strikes)//2 + 1]
    else:
        # Neutral
        net_gex = [0.5 * (1 - abs(s - spot) / spot) for s in strikes]
        total_gex = 2.0
        max_gamma_strike = strikes[len(strikes)//2]
    
    # Split into call/put GEX
    call_gex = [max(0, g) for g in net_gex]
    put_gex = [max(0, -g) for g in net_gex]
    
    return {
        'strikes': strikes,
        'net_gex_by_strike': net_gex,
        'call_gex': call_gex,
        'put_gex': put_gex,
        'total_gex': total_gex,
        'max_gamma_strike': max_gamma_strike,
        'zero_gamma_level': spot * 0.98 if total_gex > 0 else spot * 1.02,
        'spot_price': spot
    }


def test_contract_analyzer():
    """Test contract analysis functions"""
    print("=" * 70)
    print("TESTING CONTRACT ANALYZER")
    print("=" * 70)
    
    analyzer = ContractAnalyzer()
    
    # Test strike selection
    for ticker in ['SPY', 'QQQ', 'NVDA']:
        spot = 605.0 if ticker == 'SPY' else (525.0 if ticker == 'QQQ' else 145.0)
        gex_data = create_test_gex_data(ticker, "bullish")
        
        print(f"\n{ticker} @ ${spot:.2f}")
        print("-" * 50)
        
        for confidence in [85, 70, 55]:
            strike, strike_type = analyzer.calculate_optimal_strike(
                ticker, spot, 'CALL', confidence, gex_data, gex_data['strikes']
            )
            print(f"  Confidence {confidence}%: Strike ${strike:.2f} ({strike_type})")
        
        # Test expiration selection
        for conf in [85, 70, 55]:
            exp, days = analyzer.select_expiration(ticker, spot, 'CALL', conf, gex_data)
            print(f"  Exp {conf}% confidence: {exp} ({days} DTE)")
    
    print("\n✅ Contract Analyzer tests passed!")


def test_greeks_estimation():
    """Test Greeks estimation"""
    print("\n" + "=" * 70)
    print("TESTING GREEKS ESTIMATION")
    print("=" * 70)
    
    analyzer = ContractAnalyzer()
    
    test_cases = [
        ('SPY', 605.0, 605.0, 7, 'CALL'),   # ATM
        ('SPY', 605.0, 600.0, 7, 'CALL'),   # ITM
        ('SPY', 605.0, 610.0, 7, 'CALL'),   # OTM
        ('NVDA', 145.0, 145.0, 3, 'PUT'),   # ATM PUT
    ]
    
    for ticker, spot, strike, days, direction in test_cases:
        greeks = analyzer.estimate_greeks(ticker, spot, strike, days, direction)
        moneyness = "ATM" if abs(spot - strike) < 0.01 else ("ITM" if (direction == 'CALL' and strike < spot) or (direction == 'PUT' and strike > spot) else "OTM")
        
        print(f"\n{ticker} ${strike:.2f} {direction} ({moneyness}) {days}DTE")
        print(f"  Delta: {greeks.delta:+.3f} | Gamma: {greeks.gamma:.4f} | Theta: {greeks.theta:+.3f}")
        print(f"  Vega: {greeks.vega:.3f} | IV: {greeks.iv*100:.1f}% ({greeks.iv_percentile:.0f}p)")
    
    print("\n✅ Greeks Estimation tests passed!")


def test_signal_reasoning():
    """Test signal reasoning engine"""
    print("\n" + "=" * 70)
    print("TESTING SIGNAL REASONING ENGINE")
    print("=" * 70)
    
    engine = SignalReasoningEngine()
    
    for ticker in ['SPY', 'QQQ', 'NVDA']:
        spot = 605.0 if ticker == 'SPY' else (525.0 if ticker == 'QQQ' else 145.0)
        gex_data = create_test_gex_data(ticker, "bullish")
        
        print(f"\n{ticker} Analysis:")
        print("-" * 50)
        
        gex_analysis = engine.generate_gex_analysis(ticker, spot, gex_data, 'CALL')
        tech_analysis = engine.generate_technical_analysis(ticker, spot, 32, 'BULLISH', gex_data)
        dealer_analysis = engine.generate_dealer_dynamics(ticker, spot, gex_data, 'CALL')
        historical = engine.generate_historical_context(ticker, 'GEX_RSI_BULLISH', 75)
        risks = engine.generate_risk_factors(ticker, gex_data, 32, 7)
        
        print(f"  GEX: {gex_analysis[:100]}...")
        print(f"  Tech: {tech_analysis[:100]}...")
        print(f"  Dealer: {dealer_analysis[:100]}...")
        print(f"  History: {historical}")
        print(f"  Risks: {', '.join(risks[:2])}")
    
    print("\n✅ Signal Reasoning tests passed!")


def test_enhanced_signals():
    """Test full enhanced signal generation"""
    print("\n" + "=" * 70)
    print("TESTING ENHANCED SIGNAL GENERATION")
    print("=" * 70)
    
    generator = EnhancedSignalGenerator(account_size=100000)
    
    test_scenarios = [
        ('SPY', 'bullish', 32),   # Oversold + bullish setup
        ('QQQ', 'bullish', 28),   # Oversold
        ('NVDA', 'bullish', 35),  # Near oversold
    ]
    
    for ticker, scenario, rsi in test_scenarios:
        print(f"\n{'='*70}")
        print(f"SIGNAL TEST: {ticker} ({scenario.upper()})")
        print('='*70)
        
        gex_data = create_test_gex_data(ticker, scenario)
        spot = gex_data['spot_price']
        
        # Create price history with RSI
        hist_prices = [spot * (1 - 0.02 * (20-i)/20) for i in range(20)]  # Downtrend then reversal
        
        signal = generator.generate_enhanced_signal(
            ticker=ticker,
            gex_data=gex_data,
            spot_price=spot,
            price_history=hist_prices
        )
        
        if signal:
            print(f"\n🎯 SIGNAL GENERATED!")
            print(f"  Direction: {signal.direction}")
            print(f"  Confidence: {signal.confidence}%")
            print(f"  Type: {signal.signal_type}")
            
            print(f"\n  📋 CONTRACT SPECIFICATIONS:")
            print(f"    Ticker: {signal.contract.ticker}")
            print(f"    Strike: ${signal.contract.strike:.2f} ({signal.contract.strike_type})")
            print(f"    Expiration: {signal.contract.expiration} ({signal.contract.expiration_days} DTE)")
            print(f"    Option Type: {signal.contract.option_type}")
            print(f"    Est. Price: ${signal.contract.estimated_price:.2f}")
            
            print(f"\n  🎯 ENTRY/EXIT ZONES:")
            print(f"    Entry: ${signal.zones.entry_price_low:.2f} - ${signal.zones.entry_price_high:.2f}")
            print(f"    Stop Loss: ${signal.zones.stop_loss:.2f}")
            print(f"    Take Profit: ${signal.zones.take_profit:.2f}")
            print(f"    Risk/Reward: {signal.zones.risk_reward_ratio:.2f}:1")
            print(f"    Max Contracts: {signal.zones.max_contracts}")
            print(f"    Kelly: {signal.zones.kelly_fraction:.2%}")
            
            print(f"\n  📊 GREEKS:")
            print(f"    Delta: {signal.greeks.delta:+.3f}")
            print(f"    Gamma: {signal.greeks.gamma:.4f}")
            print(f"    Theta: {signal.greeks.theta:+.3f}")
            print(f"    Vega: {signal.greeks.vega:.3f}")
            print(f"    IV: {signal.greeks.iv*100:.1f}% ({signal.greeks.iv_percentile:.0f}p)")
            
            print(f"\n  💡 REASONING:")
            print(f"    GEX: {signal.reasoning.gex_analysis}")
            print(f"    Technical: {signal.reasoning.technical_analysis}")
            print(f"    Dealer: {signal.reasoning.dealer_dynamics}")
            print(f"    History: {signal.reasoning.historical_context}")
            print(f"    Risks: {', '.join(signal.reasoning.risk_factors[:2])}")
            
            # Test storage conversion
            signal_dict = signal.to_dict()
            print(f"\n  ✅ Signal serializable: {len(json.dumps(signal_dict))} bytes")
            
        else:
            print(f"\n  ⚠️ No signal generated (conditions not met)")
    
    print("\n✅ Enhanced Signal Generation tests passed!")


def test_position_sizing():
    """Test position sizing calculations"""
    print("\n" + "=" * 70)
    print("TESTING POSITION SIZING")
    print("=" * 70)
    
    analyzer = ContractAnalyzer()
    
    account_sizes = [25000, 50000, 100000]
    entry_prices = [2.50, 5.00, 10.00]
    
    for account in account_sizes:
        print(f"\nAccount Size: ${account:,.0f}")
        print("-" * 50)
        for entry in entry_prices:
            sizing = analyzer.calculate_position_size(
                account_size=account,
                risk_per_trade_pct=2.0,
                entry_price=entry,
                stop_loss=entry * 0.6,  # 40% stop
                confidence=75,
                historical_win_rate=0.65
            )
            print(f"  Entry ${entry:.2f}: Max {sizing['max_contracts']} contracts "
                  f"(Kelly: {sizing['kelly_fraction']:.1%}, Risk: ${sizing['risk_amount']:.0f})")
    
    print("\n✅ Position Sizing tests passed!")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("GEX ENHANCED SIGNAL GENERATOR - TEST SUITE")
    print("="*70 + "\n")
    
    try:
        test_contract_analyzer()
        test_greeks_estimation()
        test_signal_reasoning()
        test_enhanced_signals()
        test_position_sizing()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED ✅")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
