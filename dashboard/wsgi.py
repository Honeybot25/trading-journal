"""
WSGI Entry Point for Vercel Serverless Deployment
Adapted Dash app for serverless environment
"""

import os
import sys
import traceback

# Add the dashboard directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for Vercel BEFORE importing app
os.environ['VERCEL'] = '1'
os.environ['DASH_DEBUG'] = 'false'
os.environ['DASH_SILENCE_ROUTES_LOGGING'] = 'true'

try:
    # Import and expose the Flask server from the Dash app
    from app import app as dash_app
    
    # Get the Flask server instance
    server = dash_app.server
    
    # Vercel Python runtime looks for 'app' variable
    app = server
    
    # Also expose as 'application' for WSGI compatibility
    application = server
    
    # Add health check endpoint
    @server.route('/health')
    def health_check():
        return {'status': 'ok', 'service': 'gex-terminal'}, 200
    
    # Add API endpoint for signal tracking
    @server.route('/api/signals')
    def get_signals():
        try:
            from signal_tracker import SignalTracker
            tracker = SignalTracker()
            signals = tracker.get_all_signals()
            return {'signals': signals}, 200
        except Exception as e:
            return {'error': str(e), 'signals': []}, 500
    
    # Add seed endpoint for demo signals
    @server.route('/api/seed')
    def seed_demo():
        try:
            from signal_tracker import SignalTracker
            from demo_data import get_demo_generator
            from datetime import datetime, timedelta
            
            tracker = SignalTracker()
            demo = get_demo_generator()
            
            # Generate demo signals
            tickers = ['SPY', 'QQQ', 'NVDA', 'TSLA']
            created = []
            
            for ticker in tickers:
                signal_data = demo.generate_demo_signal(ticker)
                if signal_data['direction'] != 'NEUTRAL':
                    signal_id = tracker.log_signal(signal_data)
                    created.append({'ticker': ticker, 'direction': signal_data['direction'], 'id': signal_id})
            
            # Add one closed signal
            closed_signal = demo.generate_demo_signal('SPY')
            closed_signal['status'] = 'CLOSED'
            closed_signal['exit_price'] = closed_signal['entry_price'] * 1.08
            closed_signal['exit_time'] = (datetime.now() - timedelta(hours=2)).isoformat()
            closed_signal['exit_reason'] = 'TP_HIT'
            closed_signal['pnl'] = (closed_signal['exit_price'] - closed_signal['entry_price']) * 100
            closed_signal['pnl_percent'] = 8.0
            
            closed_id = tracker.log_signal(closed_signal)
            tracker.update_signal_exit(closed_id, {
                'exit_price': closed_signal['exit_price'],
                'exit_reason': 'TP_HIT',
                'pnl': closed_signal['pnl'],
                'pnl_percent': closed_signal['pnl_percent'],
                'notes': 'Demo take profit hit'
            })
            created.append({'ticker': 'SPY', 'direction': closed_signal['direction'], 'id': closed_id, 'status': 'CLOSED'})
            
            return {'success': True, 'created': created, 'count': len(created)}, 200
        except Exception as e:
            import traceback
            return {'error': str(e), 'traceback': traceback.format_exc()}, 500
    
except Exception as e:
    # Log the error for debugging
    error_msg = f"Error loading app: {str(e)}\n{traceback.format_exc()}"
    print(error_msg, file=sys.stderr)
    
    # Create a minimal Flask app that shows the error
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error_page():
        return f"<h1>Server Error</h1><pre>{error_msg}</pre>", 500
    
    @app.route('/health')
    def health_check_error():
        return {'status': 'error', 'message': str(e)}, 500
    
    application = app
    server = app
