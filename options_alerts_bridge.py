#!/usr/bin/env python3
"""
Python Bridge for Options Discord Alerts
Integrates TypeScript alert module with Python trading system
"""

import os
import json
import requests
import subprocess
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

# Default configuration
DEFAULT_WEBHOOK_URL = os.getenv('DISCORD_OPTIONS_WEBHOOK_URL')
DEFAULT_CONFIDENCE_THRESHOLD = 75
DEFAULT_MISSION_CONTROL_URL = "https://mission-control-lovat-rho.vercel.app"


@dataclass
class OptionsSignal:
    """Options signal data structure"""
    symbol: str
    type: str  # 'CALL' or 'PUT'
    confidence: float
    expiration_date: str  # YYYY-MM-DD
    strike_price: float
    premium: float
    underlying_price: float
    timestamp: Optional[str] = None
    unusual_volume: bool = False
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    source: Optional[str] = None
    strategy: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


class OptionsAlertBridge:
    """Bridge to TypeScript Discord alert module"""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        confidence_threshold: int = DEFAULT_CONFIDENCE_THRESHOLD,
        mission_control_url: str = DEFAULT_MISSION_CONTROL_URL,
        tsx_path: str = "npx",
        test_mode: bool = False
    ):
        self.webhook_url = webhook_url or DEFAULT_WEBHOOK_URL
        self.confidence_threshold = confidence_threshold
        self.mission_control_url = mission_control_url
        self.tsx_path = tsx_path
        self.test_mode = test_mode
        
        if not self.webhook_url:
            raise ValueError("Discord webhook URL required. Set DISCORD_OPTIONS_WEBHOOK_URL env var.")
        
        # Check if TypeScript module exists
        self.ts_module_path = os.path.join(
            os.path.dirname(__file__),
            "src/lib/discord-alerts.ts"
        )
        
    def send_alert(self, signal: OptionsSignal) -> Dict[str, Any]:
        """
        Send an options alert to Discord
        
        Returns:
            dict with 'success' boolean and optional 'error' or 'message'
        """
        # Check confidence threshold
        if signal.confidence < self.confidence_threshold:
            return {
                'success': False,
                'filtered': True,
                'reason': f'Confidence {signal.confidence}% below threshold {self.confidence_threshold}%'
            }
        
        # Set timestamp if not provided
        if not signal.timestamp:
            signal.timestamp = datetime.now().isoformat()
        
        # Method 1: Direct HTTP call to Discord (simple, no TypeScript dependency)
        return self._send_via_http(signal)
    
    def _send_via_http(self, signal: OptionsSignal) -> Dict[str, Any]:
        """Send alert directly via Discord HTTP API"""
        try:
            payload = self._build_discord_payload(signal)
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 204:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'Discord API error: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _build_discord_payload(self, signal: OptionsSignal) -> Dict[str, Any]:
        """Build Discord webhook payload"""
        is_call = signal.type.upper() == 'CALL'
        emoji = "🟢" if is_call else "🔴"
        color = 0x00FF00 if is_call else 0xFF0000
        volume_emoji = "🔥" if signal.unusual_volume else "📊"
        
        # Format expiration date
        exp_date = datetime.strptime(signal.expiration_date, "%Y-%m-%d")
        exp_formatted = exp_date.strftime("%b %d, %Y")
        days_to_exp = (exp_date - datetime.now()).days
        
        fields = [
            {
                "name": f"{emoji} Contract",
                "value": f"**{signal.symbol}** {signal.type}\n${signal.strike_price:.2f} {exp_formatted}",
                "inline": True
            },
            {
                "name": "🎯 Confidence",
                "value": f"**{signal.confidence:.0f}%**",
                "inline": True
            },
            {
                "name": f"{volume_emoji} Premium",
                "value": f"${signal.premium:.2f} per contract",
                "inline": True
            },
            {
                "name": "📈 Underlying",
                "value": f"${signal.underlying_price:.2f}",
                "inline": True
            },
            {
                "name": "⏱️ DTE",
                "value": f"{days_to_exp} days",
                "inline": True
            },
            {
                "name": "📊 Volume",
                "value": "Unusual Activity 🔥" if signal.unusual_volume else "Normal",
                "inline": True
            }
        ]
        
        # Add Greeks if available
        greeks_parts = []
        if signal.delta is not None:
            greeks_parts.append(f"Delta: {signal.delta:.3f}")
        if signal.gamma is not None:
            greeks_parts.append(f"Gamma: {signal.gamma:.3f}")
        if signal.theta is not None:
            greeks_parts.append(f"Theta: {signal.theta:.3f}")
        if signal.vega is not None:
            greeks_parts.append(f"Vega: {signal.vega:.3f}")
        if signal.implied_volatility is not None:
            greeks_parts.append(f"IV: {signal.implied_volatility*100:.1f}%")
        
        if greeks_parts:
            fields.append({
                "name": "📐 Greeks",
                "value": " | ".join(greeks_parts),
                "inline": False
            })
        
        # Add strategy/source
        if signal.strategy or signal.source:
            fields.append({
                "name": "🔍 Signal Source",
                "value": signal.strategy or signal.source or "Unknown",
                "inline": False
            })
        
        embed = {
            "title": f"🚨 OPTIONS ALERT: ${signal.symbol}",
            "description": f"{signal.type} | Confidence: **{signal.confidence:.0f}%** | {'Unusual Volume Detected' if signal.unusual_volume else 'Standard Signal'}",
            "color": color,
            "timestamp": signal.timestamp,
            "fields": fields,
            "footer": {
                "text": f"Options Alert System • {'TEST MODE' if self.test_mode else 'Live'}"
            }
        }
        
        payload = {"embeds": [embed]}
        
        if self.test_mode:
            payload["content"] = "🧪 **TEST ALERT** (This is a test)"
        
        return payload
    
    def send_test_alert(self) -> Dict[str, Any]:
        """Send a test alert"""
        test_signal = OptionsSignal(
            symbol="TEST",
            type="CALL",
            confidence=85,
            expiration_date=(datetime.now().replace(
                day=datetime.now().day + 7
            )).strftime("%Y-%m-%d"),
            strike_price=150.00,
            premium=2.50,
            underlying_price=148.50,
            unusual_volume=True,
            implied_volatility=0.35,
            delta=0.45,
            gamma=0.08,
            theta=-0.05,
            vega=0.12,
            source="Test System",
            strategy="Test Alert",
        )
        return self.send_alert(test_signal)


# Convenience function for simple usage
def send_options_alert(
    symbol: str,
    signal_type: str,
    confidence: float,
    expiration_date: str,
    strike_price: float,
    premium: float,
    underlying_price: float,
    **kwargs
) -> Dict[str, Any]:
    """
    Send an options alert with simple parameters
    
    Args:
        symbol: Stock symbol (e.g., 'NVDA')
        signal_type: 'CALL' or 'PUT'
        confidence: Confidence percentage (0-100)
        expiration_date: Expiration date (YYYY-MM-DD)
        strike_price: Option strike price
        premium: Option premium per contract
        underlying_price: Current stock price
        **kwargs: Optional fields (unusual_volume, delta, gamma, theta, vega, source, strategy)
    
    Returns:
        dict with 'success' boolean
    """
    bridge = OptionsAlertBridge()
    signal = OptionsSignal(
        symbol=symbol,
        type=signal_type,
        confidence=confidence,
        expiration_date=expiration_date,
        strike_price=strike_price,
        premium=premium,
        underlying_price=underlying_price,
        **kwargs
    )
    return bridge.send_alert(signal)


def send_options_alert_dict(signal_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Send alert from a dictionary (useful for JSON deserialization)"""
    bridge = OptionsAlertBridge()
    signal = OptionsSignal(**signal_dict)
    return bridge.send_alert(signal)


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Options Discord Alert Bridge")
    parser.add_argument("--test", action="store_true", help="Send test alert")
    parser.add_argument("--symbol", type=str, help="Stock symbol")
    parser.add_argument("--type", choices=["CALL", "PUT"], help="Option type")
    parser.add_argument("--confidence", type=float, help="Confidence percentage")
    parser.add_argument("--expiration", type=str, help="Expiration date (YYYY-MM-DD)")
    parser.add_argument("--strike", type=float, help="Strike price")
    parser.add_argument("--premium", type=float, help="Premium per contract")
    parser.add_argument("--underlying", type=float, help="Underlying price")
    parser.add_argument("--webhook", type=str, help="Discord webhook URL")
    
    args = parser.parse_args()
    
    if args.test:
        bridge = OptionsAlertBridge(webhook_url=args.webhook, test_mode=True)
        result = bridge.send_test_alert()
        print(json.dumps(result, indent=2))
    elif all([args.symbol, args.type, args.confidence, args.expiration, 
              args.strike, args.premium, args.underlying]):
        result = send_options_alert(
            symbol=args.symbol,
            signal_type=args.type,
            confidence=args.confidence,
            expiration_date=args.expiration,
            strike_price=args.strike,
            premium=args.premium,
            underlying_price=args.underlying,
        )
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
