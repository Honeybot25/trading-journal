#!/usr/bin/env python3
"""
Integration Example: Options Alerts with Signal Generator

Shows how to integrate the Discord alert system with the existing
momentum scanner and signal generation code.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from options_alerts_bridge import OptionsAlertBridge, OptionsSignal

# Example 1: Send a high-confidence CALL alert
def example_call_alert():
    """Send a high-confidence CALL options alert"""
    
    bridge = OptionsAlertBridge(
        webhook_url=os.getenv('DISCORD_OPTIONS_WEBHOOK_URL'),
        confidence_threshold=75,
        test_mode=True  # Set to False in production
    )
    
    signal = OptionsSignal(
        symbol="NVDA",
        type="CALL",
        confidence=87,  # Above 75% threshold
        expiration_date=(datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        strike_price=875.00,
        premium=12.50,
        underlying_price=860.25,
        unusual_volume=True,
        implied_volatility=0.42,
        delta=0.52,
        gamma=0.012,
        theta=-0.35,
        vega=0.85,
        source="Options Flow Scanner",
        strategy="Unusual Volume + Momentum Breakout"
    )
    
    result = bridge.send_alert(signal)
    
    if result['success']:
        print(f"✅ Alert sent for {signal.symbol} {signal.type}")
    elif result.get('filtered'):
        print(f"⏭️  Filtered: {result['reason']}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    return result


# Example 2: Send a PUT alert (bearish signal)
def example_put_alert():
    """Send a high-confidence PUT options alert"""
    
    bridge = OptionsAlertBridge(test_mode=True)
    
    signal = OptionsSignal(
        symbol="TSLA",
        type="PUT",
        confidence=82,
        expiration_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        strike_price=175.00,
        premium=4.25,
        underlying_price=180.50,
        unusual_volume=True,
        implied_volatility=0.58,
        delta=-0.48,
        gamma=0.015,
        theta=-0.42,
        vega=0.22,
        source="Dark Pool Scanner",
        strategy="Dark Pool Block Trade Detection"
    )
    
    result = bridge.send_alert(signal)
    print(f"PUT Alert Result: {result}")
    return result


# Example 3: Filtered alert (low confidence)
def example_filtered_alert():
    """Demonstrate confidence filtering"""
    
    bridge = OptionsAlertBridge(test_mode=True)
    
    signal = OptionsSignal(
        symbol="AAPL",
        type="CALL",
        confidence=60,  # Below 75% threshold - will be filtered
        expiration_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        strike_price=200.00,
        premium=5.00,
        underlying_price=195.00,
    )
    
    result = bridge.send_alert(signal)
    print(f"Low confidence alert result: {result}")
    # Expected: {'success': False, 'filtered': True, 'reason': '...'}
    return result


# Example 4: Integration with signal generator
def on_signal_generated(signal_data: dict):
    """
    Callback to integrate with existing signal generator
    
    Usage in signal_generator.py:
        from options_alerts_bridge import send_options_alert
        
        def generate_signals():
            for signal in scanner.scan():
                # ... existing signal processing ...
                
                # Send to Discord if high confidence
                if signal['confidence'] >= 75:
                    send_options_alert(
                        symbol=signal['ticker'],
                        signal_type=signal['direction'],
                        confidence=signal['confidence'],
                        expiration_date=signal['expiration'],
                        strike_price=signal['strike'],
                        premium=signal['premium'],
                        underlying_price=signal['price'],
                        unusual_volume=signal.get('unusual_volume', False),
                        source=signal.get('source', 'Scanner'),
                        strategy=signal.get('strategy', 'Momentum')
                    )
    """
    from options_alerts_bridge import send_options_alert
    
    result = send_options_alert(
        symbol=signal_data['symbol'],
        signal_type=signal_data['type'],
        confidence=signal_data['confidence'],
        expiration_date=signal_data['expiration_date'],
        strike_price=signal_data['strike_price'],
        premium=signal_data['premium'],
        underlying_price=signal_data['underlying_price'],
        unusual_volume=signal_data.get('unusual_volume', False),
        source=signal_data.get('source'),
        strategy=signal_data.get('strategy')
    )
    
    return result


# Example 5: Batch alert multiple signals
def batch_alert(signals: list):
    """Send multiple alerts with duplicate protection"""
    
    bridge = OptionsAlertBridge(test_mode=True)
    results = []
    
    for signal_data in signals:
        signal = OptionsSignal(**signal_data)
        result = bridge.send_alert(signal)
        results.append({
            'symbol': signal.symbol,
            'result': result
        })
        
        # Brief pause to avoid rate limiting
        import time
        time.sleep(0.5)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Options Alert Examples")
    parser.add_argument('--call', action='store_true', help='Send CALL example')
    parser.add_argument('--put', action='store_true', help='Send PUT example')
    parser.add_argument('--filter', action='store_true', help='Show filtered example')
    parser.add_argument('--all', action='store_true', help='Run all examples')
    
    args = parser.parse_args()
    
    if args.all or not any([args.call, args.put, args.filter]):
        print("🧪 Running all examples...\n")
        print("1. CALL Alert Example:")
        example_call_alert()
        
        print("\n2. PUT Alert Example:")
        example_put_alert()
        
        print("\n3. Filtered Alert Example (low confidence):")
        example_filtered_alert()
    else:
        if args.call:
            example_call_alert()
        if args.put:
            example_put_alert()
        if args.filter:
            example_filtered_alert()
