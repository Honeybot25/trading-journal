#!/usr/bin/env python3
"""
Momentum Scanner Alert System
Sends Discord alerts and logs to Mission Control
"""

import os
import sys
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "/Users/Honeybot/.openclaw/workspace/trading/signals.db"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1343791872923201546/sv_5FTBG_Uh4jk6L7AHSKaF2DK8s1wdAGx-4JrhqH_IH3vvb1eAaFQzhMNz4YBj8C5pR"

def get_recent_signals(minutes: int = 5) -> List[Dict]:
    """Get signals from last N minutes"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    since = (datetime.now() - __import__('datetime').timedelta(minutes=minutes)).isoformat()
    cursor.execute("""
        SELECT * FROM momentum_signals 
        WHERE timestamp > ? AND signal_type = 'MOMENTUM_BREAKOUT'
        ORDER BY timestamp DESC
    """, (since,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_open_positions() -> List[Dict]:
    """Get current open positions"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE status = 'open'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def send_discord_alert(signal: Dict):
    """Send Discord embed alert"""
    color = 3066993  # Green
    status_emoji = "🚀"
    
    if signal.get('status') == 'executed':
        status_emoji = "✅ EXECUTED"
    elif signal.get('status') == 'paper':
        status_emoji = "📝 PAPER"
    elif signal.get('status') == 'pending':
        status_emoji = "⏳ PENDING"
    
    embed = {
        "title": f"{status_emoji} Momentum Breakout: {signal['ticker']}",
        "description": f"**{signal['ticker']}** breaking out with momentum confirmation",
        "color": color,
        "fields": [
            {"name": "💰 Entry Price", "value": f"${signal.get('price', 'N/A')}", "inline": True},
            {"name": "📊 Volume Spike", "value": f"{signal.get('volume_spike_ratio', 0):.1f}x avg", "inline": True},
            {"name": "📈 RSI", "value": f"{signal.get('rsi', 0):.1f}", "inline": True},
            {"name": "🛑 Stop Loss", "value": f"${signal.get('stop_loss', 'N/A')}", "inline": True},
            {"name": "🎯 Take Profit", "value": f"${signal.get('take_profit', 'N/A')}", "inline": True},
            {"name": "📦 Position Size", "value": f"{signal.get('position_size', 0)} shares", "inline": True},
            {"name": "💵 Risk Amount", "value": f"${signal.get('risk_amount', 0):.2f}", "inline": True},
            {"name": "Status", "value": signal.get('status', 'pending').upper(), "inline": True}
        ],
        "footer": {
            "text": f"Momentum Scanner • {datetime.now().strftime('%H:%M:%S')} PST"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)
        if response.status_code == 204:
            logger.info(f"✅ Discord alert sent for {signal['ticker']}")
            return True
        else:
            logger.error(f"Discord webhook failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False

def log_to_mission_control(event_type: str, data: Dict):
    """Log to Mission Control dashboard"""
    try:
        log_entry = {
            "agent": "TraderBot",
            "project": "momentum-scanner",
            "status": "active",
            "description": f"{event_type}: {data.get('ticker', 'SCANNER')}",
            "estimated_impact": "high",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        mc_url = "https://mission-control-lovat-rho.vercel.app/api/logs"
        response = requests.post(mc_url, json=log_entry, timeout=5)
        logger.info(f"✅ Mission Control: {event_type}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Mission Control log failed: {e}")
        return False

def send_summary_alert():
    """Send summary of recent activity"""
    signals = get_recent_signals(minutes=30)
    positions = get_open_positions()
    
    if not signals and not positions:
        return
    
    embed = {
        "title": "📊 Momentum Scanner Update",
        "description": f"Recent activity summary",
        "color": 3447003,
        "fields": [
            {"name": "🚀 Signals (30m)", "value": str(len(signals)), "inline": True},
            {"name": "📈 Open Positions", "value": str(len(positions)), "inline": True}
        ],
        "footer": {"text": f"Scanner Active • {datetime.now().strftime('%H:%M')} PST"},
        "timestamp": datetime.now().isoformat()
    }
    
    if signals:
        signal_text = "\n".join([f"• {s['ticker']} @ ${s['price']} ({s.get('status', 'pending')})" for s in signals[:5]])
        embed["fields"].append({"name": "Recent Signals", "value": signal_text, "inline": False})
    
    try:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]}, timeout=5)
    except Exception as e:
        logger.error(f"Summary alert failed: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--recent', action='store_true', help='Alert recent signals')
    parser.add_argument('--summary', action='store_true', help='Send summary')
    parser.add_argument('--watch', action='store_true', help='Continuous watch mode')
    parser.add_argument('--interval', type=int, default=60, help='Watch interval')
    args = parser.parse_args()
    
    if args.recent:
        signals = get_recent_signals(minutes=60)
        for sig in signals:
            send_discord_alert(sig)
            log_to_mission_control('SIGNAL_ALERT', sig)
    
    elif args.summary:
        send_summary_alert()
    
    elif args.watch:
        logger.info(f"🔍 Alert watch mode started (interval: {args.interval}s)")
        import time
        alerted_signals = set()
        
        while True:
            signals = get_recent_signals(minutes=5)
            for sig in signals:
                sig_key = f"{sig['ticker']}_{sig['timestamp']}"
                if sig_key not in alerted_signals:
                    send_discord_alert(sig)
                    log_to_mission_control('REALTIME_ALERT', sig)
                    alerted_signals.add(sig_key)
            
            time.sleep(args.interval)
    
    else:
        # Default: check and alert
        signals = get_recent_signals(minutes=60)
        for sig in signals:
            send_discord_alert(sig)

if __name__ == "__main__":
    main()
