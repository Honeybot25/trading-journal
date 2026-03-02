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
