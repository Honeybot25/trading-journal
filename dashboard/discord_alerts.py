"""
Discord Alert Integration for GEX Terminal Signals
Sends signal alerts to Discord via webhook
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional
import os

class DiscordAlert:
    """Send signal alerts to Discord"""
    
    def __init__(self, webhook_url: str = None):
        if webhook_url is None:
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
    
    def send_signal_alert(self, signal: Dict) -> bool:
        """Send a signal alert to Discord"""
        if not self.enabled:
            return False
        
        direction = signal.get('direction', 'UNKNOWN')
        is_call = direction == 'CALL'
        
        color = 0x00FF00 if is_call else 0xFF0000  # Green or Red
        emoji = "🟢" if is_call else "🔴"
        title = f"{emoji} BUY {direction} SIGNAL"
        
        embed = {
            "title": title,
            "description": f"New trading signal generated for **{signal.get('ticker', 'UNKNOWN')}**",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📊 Entry Price",
                    "value": f"${signal.get('entry_price', 0):.2f}",
                    "inline": True
                },
                {
                    "name": "🛑 Stop Loss",
                    "value": f"${signal.get('stop_loss', 0):.2f}",
                    "inline": True
                },
                {
                    "name": "🎯 Take Profit",
                    "value": f"${signal.get('take_profit', 0):.2f}",
                    "inline": True
                },
                {
                    "name": "📈 Expected Move",
                    "value": f"${signal.get('expected_move', 0):.2f}",
                    "inline": True
                },
                {
                    "name": "💪 Confidence",
                    "value": f"{signal.get('confidence', 0)}%",
                    "inline": True
                },
                {
                    "name": "📉 RSI",
                    "value": f"{signal.get('rsi_value', 'N/A')}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "GEX Terminal Pro | Signal Alert"
            }
        }
        
        # Add conditions
        conditions = signal.get('conditions', [])
        if conditions:
            cond_text = "\n".join([
                f"{'✅' if c.get('met') else '⬜'} {c.get('name', 'Unknown')}"
                for c in conditions[:4]
            ])
            embed["fields"].append({
                "name": "📋 Conditions",
                "value": cond_text,
                "inline": False
            })
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"[Discord Alert Error] {e}")
            return False
    
    def send_exit_alert(self, signal: Dict, exit_reason: str) -> bool:
        """Send a signal exit alert to Discord"""
        if not self.enabled:
            return False
        
        pnl = signal.get('pnl', 0)
        pnl_pct = signal.get('pnl_percent', 0)
        
        is_win = pnl > 0 if pnl else False
        color = 0x00FF00 if is_win else 0xFF0000
        emoji = "✅" if is_win else "❌"
        
        embed = {
            "title": f"{emoji} SIGNAL CLOSED - {signal.get('ticker', 'UNKNOWN')}",
            "description": f"**{signal.get('direction', 'UNKNOWN')}** position closed",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "💰 P&L",
                    "value": f"${pnl:+.2f} ({pnl_pct:+.1f}%)",
                    "inline": True
                },
                {
                    "name": "📤 Exit Reason",
                    "value": exit_reason,
                    "inline": True
                },
                {
                    "name": "💵 Exit Price",
                    "value": f"${signal.get('exit_price', 0):.2f}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "GEX Terminal Pro | Exit Alert"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"[Discord Alert Error] {e}")
            return False
    
    def send_daily_summary(self, stats: Dict) -> bool:
        """Send daily performance summary"""
        if not self.enabled:
            return False
        
        total = stats.get('total_today', 0)
        if total == 0:
            return False  # Don't send if no signals
        
        embed = {
            "title": "📊 DAILY SIGNAL SUMMARY",
            "description": f"Performance summary for {datetime.now().strftime('%Y-%m-%d')}",
            "color": 0xFF6600,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📈 Total Signals",
                    "value": str(total),
                    "inline": True
                },
                {
                    "name": "🟢 CALLS",
                    "value": str(stats.get('calls', 0)),
                    "inline": True
                },
                {
                    "name": "🔴 PUTS",
                    "value": str(stats.get('puts', 0)),
                    "inline": True
                },
                {
                    "name": "🏆 Winners",
                    "value": str(stats.get('winners', 0)),
                    "inline": True
                },
                {
                    "name": "💵 Total P&L",
                    "value": f"${stats.get('pnl', 0):+.2f}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "GEX Terminal Pro | Daily Summary"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"[Discord Alert Error] {e}")
            return False

# Global instance
_discord_alert = None

def get_discord_alert() -> DiscordAlert:
    """Get singleton DiscordAlert instance"""
    global _discord_alert
    if _discord_alert is None:
        _discord_alert = DiscordAlert()
    return _discord_alert
