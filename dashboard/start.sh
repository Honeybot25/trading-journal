#!/bin/bash

# GEX Terminal Dashboard Startup Script
# Usage: ./start.sh [port]

# Use PORT from environment (for Railway/Render/Fly) or default to 8050
PORT=${PORT:-${1:-8050}}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    GEX TERMINAL DASHBOARD                    ║"
echo "║           Bloomberg-Style Gamma Exposure Analytics           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Starting GEX Terminal on port $PORT..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check if required packages are installed
echo "Checking dependencies..."
python3 -c "import dash, plotly, yfinance, pandas, numpy, scipy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Missing dependencies. Installing..."
    pip3 install -r requirements.txt --break-system-packages --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✓ Dependencies installed"
else
    echo "✓ All dependencies found"
fi

echo ""
echo "Starting server..."
echo "📊 Dashboard URL: http://localhost:$PORT"
echo "🌐 Network URL:   http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '0.0.0.0'):$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo "────────────────────────────────────────────────────────────────"

# Start the dashboard
python3 app.py