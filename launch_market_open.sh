#!/bin/bash
# Momentum Scanner Market Open Launcher
# Auto-starts scanner 6:30 AM PST

SCRIPT_DIR="/Users/Honeybot/.openclaw/workspace/trading"
LOG_DIR="$SCRIPT_DIR/logs"
VENV="$SCRIPT_DIR/venv"

# Ensure log directory exists
mkdir -p $LOG_DIR

# Activate virtual environment
source $VENV/bin/activate

echo "🚀 Momentum Scanner Market Open Launch"
echo "========================================"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S') PST"
echo "Tickers: NVDA, SPY, QQQ, TSLA"
echo "Mode: PAPER TRADING"
echo ""

# Initial scan
echo "📊 Running pre-market scan..."
cd $SCRIPT_DIR
python3 momentum_scanner.py --scan --no-execute >> $LOG_DIR/market_open.log 2>&1

# Start continuous scanner in background
echo "🔄 Starting continuous scanner..."
nohup python3 momentum_scanner.py --continuous --interval 60 >> $LOG_DIR/scanner_continuous.log 2>&1 &
SCANNER_PID=$!
echo $SCANNER_PID > $LOG_DIR/scanner.pid

# Start alert watcher in background
echo "🔔 Starting alert system..."
nohup python3 alert_system.py --watch --interval 30 >> $LOG_DIR/alerts.log 2>&1 &
ALERT_PID=$!
echo $ALERT_PID > $LOG_DIR/alert.pid

echo ""
echo "✅ Scanner deployed successfully!"
echo "   Scanner PID: $SCANNER_PID"
echo "   Alert PID: $ALERT_PID"
echo ""
echo "Logs:"
echo "   Scanner: tail -f $LOG_DIR/scanner_continuous.log"
echo "   Alerts:  tail -f $LOG_DIR/alerts.log"
echo ""
echo "To stop: kill $SCANNER_PID $ALERT_PID"
