#!/usr/bin/env python3
"""
Quick test script for GEX Terminal Dashboard
Verifies all components are working correctly
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import dash
        import plotly
        import yfinance
        import pandas
        import numpy
        import scipy
        print("✓ All required packages installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        return False

def test_gex_calculator():
    """Test GEX calculator functionality"""
    print("\nTesting GEX Calculator...")
    try:
        from gex_calculator import GEXCalculator
        calc = GEXCalculator()
        
        # Test with sample data
        result = calc.calculate_gex(None, 500.0)
        
        assert 'strikes' in result
        assert 'call_gex' in result
        assert 'put_gex' in result
        assert 'zero_gamma_level' in result
        
        print(f"  - Generated {len(result['strikes'])} strikes")
        print(f"  - Zero gamma level: {result['zero_gamma_level']:.2f}")
        print(f"  - Total GEX: {result['total_gex']:.2f}B")
        print("✓ GEX Calculator working")
        return True
    except Exception as e:
        print(f"❌ GEX Calculator error: {e}")
        return False

def test_data_fetcher():
    """Test data fetcher functionality"""
    print("\nTesting Data Fetcher...")
    try:
        from data_fetcher import DataFetcher
        fetcher = DataFetcher()
        
        # Test price fetching
        price = fetcher.get_current_price('SPY')
        print(f"  - SPY price: ${price:.2f}")
        
        # Test options fetching
        options = fetcher.get_options_chain('SPY')
        if options is not None and not options.empty:
            print(f"  - Options data: {len(options)} rows")
        
        print("✓ Data Fetcher working")
        return True
    except Exception as e:
        print(f"❌ Data Fetcher error: {e}")
        return False

def test_layouts():
    """Test layouts module"""
    print("\nTesting Layouts...")
    try:
        from layouts import TerminalLayouts
        layouts = TerminalLayouts()
        
        # Test component creation
        table = layouts.create_bloomberg_table(['A', 'B'], [[1, 2], [3, 4]], id='test-table')
        alert = layouts.create_alert_box("Test alert", "warning")
        
        print("✓ Layouts working")
        return True
    except Exception as e:
        print(f"❌ Layouts error: {e}")
        return False

def test_dashboard():
    """Test main dashboard app"""
    print("\nTesting Dashboard App...")
    try:
        import app
        
        # Check key components exist
        assert hasattr(app, 'app')
        assert hasattr(app, 'COLORS')
        assert hasattr(app, 'TICKERS')
        
        print(f"  - Dashboard tickers: {', '.join(app.TICKERS[:5])}...")
        print(f"  - Color scheme: Amber on Black")
        print("✓ Dashboard app loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False

def main():
    """Run all tests"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                GEX Terminal Dashboard Tests                  ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    
    tests = [
        ("Imports", test_imports),
        ("GEX Calculator", test_gex_calculator),
        ("Data Fetcher", test_data_fetcher),
        ("Layouts", test_layouts),
        ("Dashboard App", test_dashboard)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*64)
    print("TEST SUMMARY")
    print("="*64)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status:10} {name}")
    
    print("-"*64)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🚀 All tests passed! Dashboard is ready to use.")
        print("\nStart with: python3 app.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())