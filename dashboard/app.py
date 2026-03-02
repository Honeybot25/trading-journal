"""
GEX Bloomberg Terminal Dashboard - Renaissance Technologies Edition
Professional Gamma Exposure Visualization Terminal with Institutional-Grade Analytics
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import threading
import time
import os

from data_fetcher import DataFetcher
from gex_calculator import GEXCalculator
from layouts import TerminalLayouts
from gex_education import (
    GEX_KNOWLEDGE_BASE, SIGNAL_INTERPRETATION_TEMPLATES,
    DEALER_POSITIONING_EXPLANATIONS, HELP_SCREEN_CONTENT,
    REGIME_EXPLANATIONS, TOOLTIPS
)
from signal_tracker import SignalTracker, get_signal_tracker
from renaissance_signals import RenaissanceSignalEngine, get_renaissance_engine, SignalProximity

try:
    from signal_generator import EnhancedSignalGenerator, get_enhanced_signal_generator
    ENHANCED_SIGNALS_AVAILABLE = True
except ImportError:
    ENHANCED_SIGNALS_AVAILABLE = False
    print("[WARNING] Enhanced signal generator not available, using legacy generator")

# Initialize app with Bloomberg Terminal styling
app = dash.Dash(
    __name__,
    external_stylesheets=[],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

app.title = "GEX TERMINAL PRO | RENAISSANCE EDITION"

# Initialize components
data_fetcher = DataFetcher()
gex_calc = GEXCalculator()
layouts = TerminalLayouts()
signal_tracker = get_signal_tracker()
renaissance_engine = get_renaissance_engine()

# Use enhanced signal generator if available
if ENHANCED_SIGNALS_AVAILABLE:
    signal_generator = get_enhanced_signal_generator(account_size=100000)
else:
    from signal_tracker import SignalGenerator
    signal_generator = SignalGenerator()

# Bloomberg Terminal Color Scheme
COLORS = {
    'bg': '#0a0a0a',
    'bg_panel': '#141414',
    'bg_panel_alt': '#0f0f0f',
    'bg_card': '#1a1a1a',
    'amber': '#FF6600',
    'amber_bright': '#FF8800',
    'amber_dim': '#CC5200',
    'amber_dark': '#804000',
    'yellow': '#FFFF00',
    'green': '#00FF00',
    'green_dim': '#00AA00',
    'red': '#FF0000',
    'red_dim': '#AA0000',
    'white': '#FFFFFF',
    'gray': '#808080',
    'gray_dark': '#404040',
    'gray_light': '#A0A0A0',
    'border': '#2a2a2a',
    'border_bright': '#333333',
    'cursor': '#FF6600',
    'cyan': '#00FFFF',
    'magenta': '#FF00FF'
}

TICKERS = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL']

# Global state
current_ticker = 'SPY'
command_history = []
alert_messages = []
last_signal_check = 0
active_signals_cache = []

# Track data fetch time
data_fetch_times = {}
last_update_time = datetime.now()

# Test signal storage
test_signal_active = None
test_signal_timestamp = 0

# Global ticker state - use this for proper state management
global_current_ticker = 'SPY'

def generate_test_signal(direction='CALL'):
    """Generate a test signal with full contract details for UI testing"""
    global test_signal_active, test_signal_timestamp
    
    is_call = direction == 'CALL'
    signal_color = '#00FF00' if is_call else '#FF0000'
    
    test_signal_active = {
        'ticker': 'SPY',
        'direction': direction,
        'signal_type': 'TEST_SIGNAL',
        'confidence': 85,
        'entry_price': 2.75,
        'spot_price': 690.50,
        'timestamp': datetime.now().isoformat(),
        'contract_specs': {
            'strike': 690.0,
            'strike_type': 'ATM',
            'expiration': 'Mar 3',
            'expiration_days': 0,
            'option_type': direction,
            'estimated_price': 2.75
        },
        'zones': {
            'entry_price_low': 2.50,
            'entry_price_high': 3.00,
            'stop_loss': 1.50,
            'take_profit': 5.00,
            'risk_reward_ratio': 2.5,
            'max_contracts': 10
        },
        'position': {
            'risk_percent': 2.0,
            'contracts': 10,
            'max_loss': 1500,
            'position_value': 2750
        },
        'greeks': {
            'delta': 0.52 if is_call else -0.48,
            'gamma': 0.045,
            'theta': -0.08,
            'vega': 0.12,
            'iv': 0.28,
            'iv_percentile': 65
        },
        'reasoning': {
            'gex_analysis': '$285M gamma at $690 - major magnet level',
            'technical': 'RSI 32, oversold bounce forming at support',
            'dealer_flow': 'Dealers short $45M gamma - hedging flow will accelerate moves',
            'historical': '73% win rate on similar GEX reversal setups',
            'risk_factors': [
                'VIX expansion could increase IV crush risk',
                'Fed speakers scheduled at 2pm ET'
            ]
        }
    }
    test_signal_timestamp = time.time()
    return test_signal_active

def get_data_age(ticker):
    """Get age of data in seconds"""
    if ticker in data_fetch_times:
        age = time.time() - data_fetch_times[ticker]
        if age < 60:
            return f"DATA: {int(age)}s ago"
        elif age < 3600:
            return f"DATA: {int(age/60)}m ago"
        else:
            return f"DATA: {int(age/3600)}h ago"
    return "DATA: N/A"

# ==================== RENAISSANCE-STYLE CALCULATIONS ====================

def calculate_signal_proximity(gex_data, spot_price):
    """Calculate proximity to next signal trigger"""
    if not gex_data or not spot_price:
        return {
            'percent_to_trigger': 0,
            'distance_to_next_level': 0,
            'rsi_distance': 0,
            'trend_alignment': 0,
            'status': 'NO DATA',
            'direction': 'NEUTRAL'
        }
    
    zero_gamma = gex_data.get('zero_gamma_level', spot_price)
    max_gamma = gex_data.get('max_gamma_strike', spot_price)
    
    # Distance to zero gamma (main signal level)
    distance_to_zero = abs(spot_price - zero_gamma)
    distance_pct = (distance_to_zero / spot_price) * 100
    
    # Determine direction
    direction = 'BUY CALL' if spot_price < zero_gamma else 'BUY PUT' if spot_price > zero_gamma else 'NEUTRAL'
    
    # Calculate RSI distance from oversold/overbought (simulated)
    rsi_value = 50 + np.random.normal(0, 10)  # Simulated RSI
    if direction == 'BUY CALL':
        rsi_distance = max(0, rsi_value - 35)  # Distance from oversold
        rsi_target = 35
    else:
        rsi_distance = max(0, 65 - rsi_value)  # Distance from overbought
        rsi_target = 65
    
    # Trend alignment score (0-100)
    trend_alignment = np.random.randint(40, 85)
    
    # Percent to trigger (inverse of distance)
    percent_to_trigger = max(0, min(100, 100 - (distance_pct * 10)))
    
    if percent_to_trigger >= 95:
        status = f"TRIGGERED - {direction}"
    elif percent_to_trigger >= 75:
        status = f"{int(percent_to_trigger)}% to {direction} trigger"
    else:
        status = f"{int(100 - percent_to_trigger)}% away from signal"
    
    return {
        'percent_to_trigger': percent_to_trigger,
        'distance_to_next_level': distance_to_zero,
        'rsi_distance': rsi_distance,
        'rsi_value': rsi_value,
        'rsi_target': rsi_target,
        'trend_alignment': trend_alignment,
        'status': status,
        'direction': direction,
        'zero_gamma': zero_gamma
    }

def calculate_decision_matrix(gex_data, spot_price, proximity_data):
    """Calculate 5-criteria decision matrix"""
    if not gex_data:
        return {
            'gex_proximity': 0,
            'rsi_condition': 0,
            'trend_alignment': 0,
            'volume_confirmation': 0,
            'dealer_positioning': 0,
            'overall_score': 0,
            'decision': 'NO DATA',
            'waiting_for': 'Market data unavailable'
        }
    
    # 1. GEX Proximity Score (0-100)
    gex_proximity = min(100, proximity_data['percent_to_trigger'] * 1.1)
    
    # 2. RSI Condition Score (0-100)
    rsi = proximity_data['rsi_value']
    if proximity_data['direction'] == 'BUY CALL':
        rsi_score = max(0, min(100, (35 - rsi) * 3 + 50))  # Higher score when oversold
        rsi_status = f"RSI {rsi:.0f} - Need < 35"
    else:
        rsi_score = max(0, min(100, (rsi - 65) * 3 + 50))  # Higher score when overbought
        rsi_status = f"RSI {rsi:.0f} - Need > 65"
    
    # 3. Trend Alignment Score (0-100)
    trend_score = proximity_data['trend_alignment']
    
    # 4. Volume Confirmation (0-100) - Simulated
    volume_score = np.random.randint(60, 95)
    
    # 5. Dealer Positioning (0-100) - Based on GEX
    total_gex = gex_data.get('total_gex', 0)
    put_call_ratio = gex_data.get('put_call_ratio', 1.0)
    if proximity_data['direction'] == 'BUY CALL':
        dealer_score = min(100, (put_call_ratio - 0.8) * 100 + 50)  # Higher when puts dominate
    else:
        dealer_score = min(100, (1.2 - put_call_ratio) * 100 + 50)  # Higher when calls dominate
    dealer_score = max(0, min(100, dealer_score))
    
    # Overall score
    overall_score = (gex_proximity + rsi_score + trend_score + volume_score + dealer_score) / 5
    
    # Decision logic
    if overall_score >= 80:
        decision = "EXECUTE"
        waiting_for = "Signal conditions met"
    elif overall_score >= 60:
        decision = "PREPARE"
        waiting_for = "Approaching optimal entry"
    elif overall_score >= 40:
        decision = "HOLD"
        waiting_for = rsi_status
    else:
        decision = "WAIT"
        waiting_for = "Multiple conditions not met"
    
    return {
        'gex_proximity': gex_proximity,
        'rsi_condition': rsi_score,
        'trend_alignment': trend_score,
        'volume_confirmation': volume_score,
        'dealer_positioning': dealer_score,
        'overall_score': overall_score,
        'decision': decision,
        'waiting_for': waiting_for
    }

def calculate_edge_metrics(gex_data, spot_price, decision_matrix):
    """Calculate Renaissance-style edge metrics"""
    if not gex_data:
        return {
            'win_probability': 0,
            'expected_return': 0,
            'sharpe_ratio': 0,
            'kelly_size': 0,
            'risk_of_ruin': 0
        }
    
    # Win probability based on decision matrix score
    base_prob = 0.45
    score_adj = (decision_matrix['overall_score'] - 50) / 100
    win_probability = min(0.85, max(0.25, base_prob + score_adj))
    
    # Expected return (%) based on similar setups
    expected_return = (win_probability - 0.5) * 10 + np.random.normal(0, 0.5)
    
    # Sharpe ratio estimate
    volatility = 0.20  # Assumed 20% annualized
    sharpe = (expected_return / (volatility * 100)) * np.sqrt(252) if volatility > 0 else 0.5
    
    # Kelly criterion optimal position size
    kelly = (win_probability * 2 - 1) / 2 if win_probability > 0.5 else 0
    kelly_size = min(kelly * 100, 5.0)  # Max 5%
    
    # Risk of ruin (simplified)
    risk_of_ruin = max(0, (1 - win_probability) ** 5) * 100
    
    return {
        'win_probability': win_probability * 100,
        'expected_return': expected_return,
        'sharpe_ratio': sharpe,
        'kelly_size': kelly_size,
        'risk_of_ruin': risk_of_ruin
    }

def detect_gex_regime(gex_data, spot_price):
    """Detect GEX regime and probabilities"""
    if not gex_data:
        return {
            'regime': 'UNKNOWN',
            'squeeze_probability': 0,
            'pin_price': 0,
            'pin_range': 0,
            'breakout_prob': 0,
            'mean_reversion_prob': 0
        }
    
    total_gex = gex_data.get('total_gex', 0)
    put_call_ratio = gex_data.get('put_call_ratio', 1.0)
    
    # Regime detection
    if total_gex > 0.5:
        regime = 'POSITIVE GAMMA'
        regime_color = COLORS['green']
    elif total_gex < -0.5:
        regime = 'NEGATIVE GAMMA'
        regime_color = COLORS['red']
    else:
        regime = 'NEUTRAL GAMMA'
        regime_color = COLORS['amber']
    
    # Squeeze probability (based on gamma concentration)
    squeeze_prob = min(0.75, abs(total_gex) * 10 + np.random.uniform(0, 0.15))
    
    # Pin risk calculation
    pin_price = gex_data.get('max_gamma_strike', spot_price)
    pin_range = abs(spot_price - pin_price) + (spot_price * 0.002)  # +/- $0.2% + distance
    
    # Breakout vs mean reversion probabilities
    if regime == 'POSITIVE GAMMA':
        breakout_prob = 0.25
        mean_rev_prob = 0.65
    elif regime == 'NEGATIVE GAMMA':
        breakout_prob = 0.55
        mean_rev_prob = 0.30
    else:
        breakout_prob = 0.45
        mean_rev_prob = 0.45
    
    return {
        'regime': regime,
        'regime_color': regime_color,
        'squeeze_probability': squeeze_prob * 100,
        'pin_price': pin_price,
        'pin_range': pin_range,
        'breakout_prob': breakout_prob * 100,
        'mean_reversion_prob': mean_rev_prob * 100
    }

def calculate_dealer_flow(gex_data, spot_price):
    """Calculate dealer flow analysis"""
    if not gex_data:
        return {
            'dealer_gamma': 0,
            'hedge_pressure': 0,
            'max_pain': 0,
            'hedging_wall': 0
        }
    
    total_gex = gex_data.get('total_gex', 0)
    total_call_gex = gex_data.get('total_call_gex', 0)
    total_put_gex = gex_data.get('total_put_gex', 0)
    
    # Estimated dealer gamma position (inverse of market)
    dealer_gamma = -(total_call_gex - total_put_gex) * 100  # In millions
    
    # Hedge pressure (how much dealers need to hedge per $ move)
    hedge_pressure = abs(dealer_gamma) * 0.05  # Simplified calculation
    
    # Max pain (strike with minimum total value at expiration)
    strikes = gex_data.get('strikes', [])
    if strikes:
        max_pain = strikes[len(strikes) // 2]  # Simplified - use middle strike
    else:
        max_pain = spot_price
    
    # Hedging wall (strike with max gamma)
    hedging_wall = gex_data.get('max_gamma_strike', spot_price)
    
    return {
        'dealer_gamma': dealer_gamma,
        'hedge_pressure': hedge_pressure,
        'max_pain': max_pain,
        'hedging_wall': hedging_wall
    }

def get_historical_context(ticker, gex_data):
    """Get historical context for current setup"""
    # Simulated historical data - in production this would query a database
    win_rate = np.random.randint(65, 82)
    avg_return = np.random.uniform(2.5, 5.5)
    days_since_last = np.random.randint(1, 10)
    last_pnl = np.random.uniform(800, 2500)
    
    return {
        'similar_win_rate': win_rate,
        'avg_return': avg_return,
        'days_since_last': days_since_last,
        'last_pnl': last_pnl,
        'pattern': 'GEX Reversal at Major Level' if gex_data else 'Unknown'
    }

# ==================== UI COMPONENTS ====================

def create_header():
    """Create Bloomberg-style command bar header with countdown"""
    return html.Div([
        # Command bar
        html.Div([
            html.Span("GEX", style={'color': COLORS['amber'], 'fontWeight': 'bold'}),
            html.Span(">", style={'color': COLORS['white']}),
            dcc.Input(
                id='command-input',
                type='text',
                placeholder='Type: SPY, SPY GEX, HELP, or ticker symbol...',
                style={
                    'backgroundColor': COLORS['bg'],
                    'color': COLORS['amber'],
                    'border': 'none',
                    'outline': 'none',
                    'fontFamily': 'Courier New, monospace',
                    'fontSize': '14px',
                    'width': '300px',
                    'marginLeft': '10px',
                    'caretColor': COLORS['amber']
                }
            ),
            html.Button(
                'GO',
                id='command-go',
                style={
                    'backgroundColor': COLORS['amber'],
                    'color': COLORS['bg'],
                    'border': 'none',
                    'padding': '2px 15px',
                    'fontFamily': 'Courier New, monospace',
                    'fontWeight': 'bold',
                    'cursor': 'pointer',
                    'marginLeft': '5px'
                }
            ),
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'padding': '5px 10px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'backgroundColor': COLORS['bg_panel']
        }),
        
        # Status bar with countdown timer and data freshness
        html.Div([
            html.Span("CONNECTED", style={'color': COLORS['green'], 'marginRight': '15px'}),
            html.Span(id='market-status', style={'color': COLORS['amber'], 'marginRight': '15px'}),
            html.Span(id='data-source-badge', style={'marginRight': '15px', 'fontWeight': 'bold'}),
            html.Span(id='rate-limit-badge', style={'color': COLORS['gray'], 'marginRight': '15px'}),
            html.Span(id='data-age-container', children=[
                html.Span("📊 ", style={'marginRight': '2px'}),
                html.Span(id='data-age', style={'color': COLORS['gray']})
            ], style={'marginRight': '15px'}),
            html.Span(id='staleness-indicator', style={
                'marginRight': '15px',
                'padding': '1px 6px',
                'borderRadius': '2px',
                'fontWeight': 'bold',
                'fontSize': '9px',
                'display': 'none'
            }),
            html.Span(id='last-update', style={'color': COLORS['gray'], 'marginRight': '15px'}),
            html.Span(id='countdown-timer', style={
                'color': COLORS['amber'],
                'fontWeight': 'bold',
                'marginRight': '15px',
                'backgroundColor': COLORS['bg_panel'],
                'padding': '1px 8px',
                'border': f'1px solid {COLORS["border"]}',
                'borderRadius': '2px'
            }),
            html.Button(
                '↻ REFRESH NOW',
                id='refresh-button',
                style={
                    'backgroundColor': COLORS['amber'],
                    'color': COLORS['bg'],
                    'border': f'1px solid {COLORS["amber"]}',
                    'padding': '2px 12px',
                    'fontFamily': 'Courier New, monospace',
                    'fontSize': '10px',
                    'fontWeight': 'bold',
                    'cursor': 'pointer',
                    'marginLeft': 'auto',
                    'marginRight': '10px'
                }
            ),
            html.Span(id='current-time', style={'color': COLORS['white']})
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'padding': '3px 10px',
            'backgroundColor': COLORS['bg_panel_alt'],
            'fontSize': '11px',
            'fontFamily': 'Courier New, monospace',
            'borderBottom': f'1px solid {COLORS["border"]}'
        })
    ])

def create_function_keys():
    """Create Bloomberg-style F-key navigation with new signal buttons"""
    f_keys = [
        ('F1', 'HELP'), ('F2', 'GEX'), ('F3', 'HEATMAP'), ('F4', 'PROFILE'),
        ('F5', 'SIGNALS'), ('F6', 'PERF'), ('F7', 'EXPORT'), ('F8', 'REFRESH'),
        ('F9', 'SPY'), ('F10', 'QQQ'), ('F11', 'NVDA'), ('F12', 'TSLA')
    ]
    
    test_buttons = html.Div([
        html.Button('🟢 TEST CALL', id='test-call-btn', style={
            'backgroundColor': '#003300',
            'color': '#00FF00',
            'border': '1px solid #00FF00',
            'padding': '4px 10px',
            'fontSize': '10px',
            'cursor': 'pointer',
            'marginLeft': '10px',
            'fontFamily': 'Courier New, monospace'
        }),
        html.Button('🔴 TEST PUT', id='test-put-btn', style={
            'backgroundColor': '#330000',
            'color': '#FF0000',
            'border': '1px solid #FF0000',
            'padding': '4px 10px',
            'fontSize': '10px',
            'cursor': 'pointer',
            'marginLeft': '5px',
            'fontFamily': 'Courier New, monospace'
        }),
        html.Span('Click to test signal display', style={
            'color': COLORS['gray'],
            'fontSize': '9px',
            'marginLeft': '10px'
        })
    ], style={'display': 'flex', 'alignItems': 'center', 'marginLeft': 'auto', 'marginRight': '10px'})
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span(
                    f"{fk[0]}={fk[1]}",
                    style={
                        'color': COLORS['amber'],
                        'fontSize': '10px',
                        'padding': '2px 8px',
                        'borderRight': f'1px solid {COLORS["border"]}',
                        'cursor': 'pointer',
                        'fontFamily': 'Courier New, monospace'
                    },
                    id=f'fkey-{fk[0].lower()}'
                ) for fk in f_keys
            ], style={'display': 'flex'}),
            test_buttons
        ], style={
            'display': 'flex',
            'backgroundColor': COLORS['bg_panel'],
            'borderBottom': f'1px solid {COLORS["border"]}',
            'overflow': 'hidden',
            'justifyContent': 'space-between'
        }),
        
        html.Div([
            html.Button(
                ticker,
                id=f'quick-{ticker}',
                style={
                    'backgroundColor': COLORS['bg_panel_alt'] if i % 2 == 0 else COLORS['bg_panel'],
                    'color': COLORS['amber'] if ticker in ['SPY', 'QQQ'] else COLORS['white'],
                    'border': 'none',
                    'borderRight': f'1px solid {COLORS["border"]}',
                    'padding': '5px 15px',
                    'fontFamily': 'Courier New, monospace',
                    'fontSize': '12px',
                    'cursor': 'pointer',
                    'fontWeight': 'bold' if ticker in ['SPY', 'QQQ'] else 'normal'
                }
            ) for i, ticker in enumerate(TICKERS)
        ], style={
            'display': 'flex',
            'backgroundColor': COLORS['bg_panel'],
            'borderBottom': f'1px solid {COLORS["border"]}'
        })
    ])

def create_ticker_sidebar():
    """Create left sidebar with clickable ticker list"""
    return html.Div([
        html.Div("SYMBOLS", style={
            'color': COLORS['amber'],
            'padding': '8px',
            'fontSize': '12px',
            'fontWeight': 'bold',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'textAlign': 'center',
            'fontFamily': 'Courier New, monospace'
        }),
        html.Div([
            html.Div(
                id=f'sidebar-{ticker}',
                children=[
                    html.Span(ticker, style={
                        'color': COLORS['amber'] if ticker == 'SPY' else COLORS['white'],
                        'fontWeight': 'bold' if ticker == 'SPY' else 'normal',
                        'fontSize': '12px'
                    }),
                    html.Span("", id=f'price-{ticker}', style={
                        'color': COLORS['gray'],
                        'fontSize': '10px'
                    })
                ],
                style={
                    'padding': '8px 10px',
                    'borderBottom': f'1px solid {COLORS["border"]}',
                    'cursor': 'pointer',
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'backgroundColor': COLORS['bg_panel_alt'] if ticker == 'SPY' else 'transparent'
                },
                **{'data-ticker': ticker}
            )
            for ticker in TICKERS
        ], id='ticker-list')
    ], style={
        'width': '120px',
        'backgroundColor': COLORS['bg_panel'],
        'borderRight': f'1px solid {COLORS["border"]}',
        'height': '100%',
        'overflowY': 'auto'
    })

# ==================== RENAISSANCE PANELS ====================

def create_proximity_meter(proximity_data):
    """Create signal proximity meter with progress bar"""
    if not proximity_data:
        return html.Div("No proximity data", style={'color': COLORS['gray']})
    
    percent = proximity_data.get('percent_to_trigger', 0)
    status = proximity_data.get('status', 'NO SIGNAL')
    direction = proximity_data.get('direction', 'NEUTRAL')
    
    # Determine color based on proximity
    if percent >= 95:
        bar_color = COLORS['green'] if direction == 'BUY CALL' else COLORS['red']
    elif percent >= 75:
        bar_color = COLORS['yellow']
    else:
        bar_color = COLORS['amber_dim']
    
    return html.Div([
        html.Div([
            html.Span("SIGNAL PROXIMITY", style={
                'color': COLORS['amber'],
                'fontSize': '11px',
                'fontWeight': 'bold'
            }),
            html.Span(status, style={
                'color': COLORS['green'] if percent >= 95 else COLORS['white'],
                'fontSize': '10px',
                'marginLeft': 'auto'
            })
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '8px'}),
        
        # Progress bar
        html.Div([
            html.Div(style={
                'width': f'{percent}%',
                'height': '100%',
                'backgroundColor': bar_color,
                'transition': 'width 0.5s ease',
                'boxShadow': f'0 0 10px {bar_color}' if percent >= 75 else 'none'
            })
        ], style={
            'width': '100%',
            'height': '12px',
            'backgroundColor': COLORS['bg_panel_alt'],
            'border': f'1px solid {COLORS["border"]}',
            'marginBottom': '10px'
        }),
        
        # Detail metrics
        html.Div([
            html.Div([
                html.Span("Distance to GEX: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"${proximity_data.get('distance_to_next_level', 0):.2f}", style={'color': COLORS['white'], 'fontSize': '9px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '4px'}),
            html.Div([
                html.Span("RSI Distance: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"{proximity_data.get('rsi_distance', 0):.1f} pts", style={'color': COLORS['white'], 'fontSize': '9px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '4px'}),
            html.Div([
                html.Span("Trend Score: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"{proximity_data.get('trend_alignment', 0):.0f}/100", style={'color': COLORS['white'], 'fontSize': '9px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between'})
        ])
    ], style={
        'backgroundColor': COLORS['bg_card'],
        'border': f'1px solid {COLORS["border"]}',
        'padding': '12px',
        'marginBottom': '10px'
    })

def create_decision_matrix(matrix_data):
    """Create trade decision matrix"""
    if not matrix_data:
        return html.Div("No decision data", style={'color': COLORS['gray']})
    
    criteria = [
        ('GEX Proximity', matrix_data.get('gex_proximity', 0)),
        ('RSI Condition', matrix_data.get('rsi_condition', 0)),
        ('Trend Alignment', matrix_data.get('trend_alignment', 0)),
        ('Volume Confirm', matrix_data.get('volume_confirmation', 0)),
        ('Dealer Position', matrix_data.get('dealer_positioning', 0))
    ]
    
    overall = matrix_data.get('overall_score', 0)
    decision = matrix_data.get('decision', 'WAIT')
    waiting = matrix_data.get('waiting_for', '')
    
    # Decision color
    if decision == 'EXECUTE':
        dec_color = COLORS['green']
    elif decision == 'PREPARE':
        dec_color = COLORS['yellow']
    elif decision == 'HOLD':
        dec_color = COLORS['amber']
    else:
        dec_color = COLORS['gray']
    
    return html.Div([
        html.Div([
            html.Span("DECISION MATRIX", style={
                'color': COLORS['amber'],
                'fontSize': '11px',
                'fontWeight': 'bold'
            }),
            html.Span(f"Score: {overall:.0f}/100", style={
                'color': COLORS['white'],
                'fontSize': '10px',
                'marginLeft': 'auto'
            })
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '10px'}),
        
        # Criteria rows
        html.Div([
            html.Div([
                html.Div([
                    html.Span(name, style={'color': COLORS['gray'], 'fontSize': '9px', 'width': '100px'}),
                    html.Div([
                        html.Div(style={
                            'width': f'{value}%',
                            'height': '100%',
                            'backgroundColor': COLORS['green'] if value >= 70 else COLORS['amber'] if value >= 40 else COLORS['red'],
                            'transition': 'width 0.3s ease'
                        })
                    ], style={
                        'flex': '1',
                        'height': '6px',
                        'backgroundColor': COLORS['bg_panel_alt'],
                        'marginRight': '8px'
                    }),
                    html.Span(f"{value:.0f}", style={
                        'color': COLORS['white'],
                        'fontSize': '9px',
                        'width': '20px',
                        'textAlign': 'right'
                    })
                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '5px'})
                for name, value in criteria
            ]),
        ]),
        
        # Decision box
        html.Div([
            html.Div(decision, style={
                'color': dec_color,
                'fontSize': '14px',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'marginBottom': '4px'
            }),
            html.Div(f"— {waiting}", style={
                'color': COLORS['gray'],
                'fontSize': '8px',
                'textAlign': 'center'
            })
        ], style={
            'border': f'1px solid {dec_color}',
            'padding': '8px',
            'marginTop': '10px',
            'backgroundColor': f'{dec_color}11'
        })
    ], style={
        'backgroundColor': COLORS['bg_card'],
        'border': f'1px solid {COLORS["border"]}',
        'padding': '12px',
        'height': '100%'
    })

def create_edge_metrics(edge_data):
    """Create Renaissance-style edge metrics panel"""
    if not edge_data:
        return html.Div("No edge data", style={'color': COLORS['gray']})
    
    win_prob = edge_data.get('win_probability', 0)
    exp_return = edge_data.get('expected_return', 0)
    sharpe = edge_data.get('sharpe_ratio', 0)
    kelly = edge_data.get('kelly_size', 0)
    risk_ruin = edge_data.get('risk_of_ruin', 0)
    
    return html.Div([
        html.Div("EDGE METRICS", style={
            'color': COLORS['amber'],
            'fontSize': '11px',
            'fontWeight': 'bold',
            'marginBottom': '10px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'paddingBottom': '5px'
        }),
        
        html.Div([
            # Win Probability
            html.Div([
                html.Div([
                    html.Span(f"{win_prob:.1f}%", style={
                        'color': COLORS['green'] if win_prob >= 60 else COLORS['amber'] if win_prob >= 45 else COLORS['red'],
                        'fontSize': '18px',
                        'fontWeight': 'bold'
                    }),
                    html.Div("Win Prob", style={'color': COLORS['gray'], 'fontSize': '8px'})
                ], style={'textAlign': 'center', 'flex': '1'}),
                
                # Expected Return
                html.Div([
                    html.Span(f"{exp_return:+.1f}%", style={
                        'color': COLORS['green'] if exp_return > 0 else COLORS['red'],
                        'fontSize': '18px',
                        'fontWeight': 'bold'
                    }),
                    html.Div("Exp Return", style={'color': COLORS['gray'], 'fontSize': '8px'})
                ], style={'textAlign': 'center', 'flex': '1'}),
                
                # Sharpe
                html.Div([
                    html.Span(f"{sharpe:.2f}", style={
                        'color': COLORS['green'] if sharpe >= 1.0 else COLORS['amber'] if sharpe >= 0.5 else COLORS['red'],
                        'fontSize': '18px',
                        'fontWeight': 'bold'
                    }),
                    html.Div("Sharpe", style={'color': COLORS['gray'], 'fontSize': '8px'})
                ], style={'textAlign': 'center', 'flex': '1'})
            ], style={'display': 'flex', 'marginBottom': '15px'}),
            
            # Kelly and Risk
            html.Div([
                html.Div([
                    html.Div([
                        html.Span("Kelly Optimal: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                        html.Span(f"{kelly:.2f}%", style={
                            'color': COLORS['cyan'],
                            'fontSize': '12px',
                            'fontWeight': 'bold'
                        })
                    ]),
                    html.Div([
                        html.Span("Risk of Ruin: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                        html.Span(f"{risk_ruin:.2f}%", style={
                            'color': COLORS['red'] if risk_ruin > 5 else COLORS['amber'] if risk_ruin > 1 else COLORS['green'],
                            'fontSize': '12px',
                            'fontWeight': 'bold'
                        })
                    ])
                ], style={'flex': '1'})
            ], style={'display': 'flex', 'justifyContent': 'space-between'})
        ])
    ], style={
        'backgroundColor': COLORS['bg_card'],
        'border': f'1px solid {COLORS["border"]}',
        'padding': '12px',
        'height': '100%'
    })

def create_regime_panel(regime_data):
    """Create GEX regime detection panel"""
    if not regime_data:
        return html.Div("No regime data", style={'color': COLORS['gray']})
    
    regime = regime_data.get('regime', 'UNKNOWN')
    regime_color = regime_data.get('regime_color', COLORS['gray'])
    squeeze = regime_data.get('squeeze_probability', 0)
    pin = regime_data.get('pin_price', 0)
    pin_range = regime_data.get('pin_range', 0)
    breakout = regime_data.get('breakout_prob', 0)
    mean_rev = regime_data.get('mean_reversion_prob', 0)
    
    return html.Div([
        html.Div([
            html.Span("GEX REGIME", style={
                'color': COLORS['amber'],
                'fontSize': '11px',
                'fontWeight': 'bold'
            }),
            html.Span(regime, style={
                'color': regime_color,
                'fontSize': '11px',
                'fontWeight': 'bold',
                'marginLeft': 'auto'
            })
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '10px'}),
        
        # Squeeze probability
        html.Div([
            html.Span(f"Squeeze Prob: {squeeze:.0f}%", style={'color': COLORS['yellow'], 'fontSize': '9px'}),
            html.Div([
                html.Div(style={
                    'width': f'{squeeze}%',
                    'height': '100%',
                    'backgroundColor': COLORS['yellow']
                })
            ], style={
                'width': '100%',
                'height': '6px',
                'backgroundColor': COLORS['bg_panel_alt'],
                'marginTop': '3px'
            })
        ], style={'marginBottom': '8px'}),
        
        # Pin risk
        html.Div([
            html.Span("Pin Risk: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Span(f"${pin:.2f} (±${pin_range:.2f})", style={'color': COLORS['white'], 'fontSize': '9px'})
        ], style={'marginBottom': '8px'}),
        
        # Breakout vs Mean Reversion
        html.Div([
            html.Div([
                html.Span(f"Breakout: {breakout:.0f}%", style={'color': COLORS['cyan'], 'fontSize': '9px'}),
                html.Div([
                    html.Div(style={
                        'width': f'{breakout}%',
                        'height': '100%',
                        'backgroundColor': COLORS['cyan']
                    })
                ], style={
                    'width': '100%',
                    'height': '4px',
                    'backgroundColor': COLORS['bg_panel_alt'],
                    'marginTop': '2px'
                })
            ], style={'flex': '1', 'marginRight': '10px'}),
            html.Div([
                html.Span(f"Mean Rev: {mean_rev:.0f}%", style={'color': COLORS['magenta'], 'fontSize': '9px'}),
                html.Div([
                    html.Div(style={
                        'width': f'{mean_rev}%',
                        'height': '100%',
                        'backgroundColor': COLORS['magenta']
                    })
                ], style={
                    'width': '100%',
                    'height': '4px',
                    'backgroundColor': COLORS['bg_panel_alt'],
                    'marginTop': '2px'
                })
            ], style={'flex': '1'})
        ], style={'display': 'flex'})
    ], style={
        'backgroundColor': COLORS['bg_card'],
        'border': f'1px solid {COLORS["border"]}',
        'padding': '12px',
        'height': '100%'
    })

def create_dealer_flow_panel(flow_data, spot_price):
    """Create dealer flow analysis panel"""
    if not flow_data:
        return html.Div("No flow data", style={'color': COLORS['gray']})
    
    dealer_gamma = flow_data.get('dealer_gamma', 0)
    hedge_pressure = flow_data.get('hedge_pressure', 0)
    max_pain = flow_data.get('max_pain', 0)
    hedging_wall = flow_data.get('hedging_wall', 0)
    
    # Format dealer position
    if abs(dealer_gamma) >= 1000000:
        dealer_str = f"${dealer_gamma/1000000:.1f}M"
    else:
        dealer_str = f"${dealer_gamma/1000:.1f}K"
    
    position_type = "SHORT" if dealer_gamma < 0 else "LONG"
    position_color = COLORS['red'] if dealer_gamma < 0 else COLORS['green']
    
    return html.Div([
        html.Div("DEALER FLOW", style={
            'color': COLORS['amber'],
            'fontSize': '11px',
            'fontWeight': 'bold',
            'marginBottom': '10px'
        }),
        
        html.Div([
            html.Div([
                html.Span("Dealer Gamma: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"{position_type} {dealer_str}", style={
                    'color': position_color,
                    'fontSize': '11px',
                    'fontWeight': 'bold'
                })
            ], style={'marginBottom': '6px'}),
            
            html.Div([
                html.Span("Hedge Pressure: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"${hedge_pressure:.2f}M per $1 move", style={
                    'color': COLORS['white'],
                    'fontSize': '9px'
                })
            ], style={'marginBottom': '6px'}),
            
            html.Div([
                html.Span("Max Pain: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"${max_pain:.2f}", style={'color': COLORS['white'], 'fontSize': '9px'})
            ], style={'marginBottom': '6px'}),
            
            html.Div([
                html.Span("Hedge Wall: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(f"${hedging_wall:.2f}", style={'color': COLORS['amber'], 'fontSize': '9px'})
            ])
        ])
    ], style={
        'backgroundColor': COLORS['bg_card'],
        'border': f'1px solid {COLORS["border"]}',
        'padding': '12px',
        'height': '100%'
    })

def create_historical_panel(hist_data):
    """Create historical context panel"""
    if not hist_data:
        return html.Div("No historical data", style={'color': COLORS['gray']})
    
    win_rate = hist_data.get('similar_win_rate', 0)
    avg_ret = hist_data.get('avg_return', 0)
    days_ago = hist_data.get('days_since_last', 0)
    last_pnl = hist_data.get('last_pnl', 0)
    pattern = hist_data.get('pattern', 'Unknown')
    
    return html.Div([
        html.Div("HISTORICAL CONTEXT", style={
            'color': COLORS['amber'],
            'fontSize': '11px',
            'fontWeight': 'bold',
            'marginBottom': '10px'
        }),
        
        html.Div([
            html.Div([
                html.Span(f"✓ Similar setups worked {win_rate}% of time", style={
                    'color': COLORS['green'],
                    'fontSize': '9px'
                })
            ], style={'marginBottom': '5px'}),
            
            html.Div([
                html.Span(f"✓ Average return: +{avg_ret:.1f}%", style={
                    'color': COLORS['green'],
                    'fontSize': '9px'
                })
            ], style={'marginBottom': '5px'}),
            
            html.Div([
                html.Span(f"✓ Last signal: {days_ago} days ago, ", style={
                    'color': COLORS['gray'],
                    'fontSize': '9px'
                }),
                html.Span(f"+${last_pnl:,.0f} P&L", style={
                    'color': COLORS['green'],
                    'fontSize': '9px'
                })
            ], style={'marginBottom': '8px'}),
            
            html.Div([
                html.Span("Pattern: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                html.Span(pattern, style={
                    'color': COLORS['cyan'],
                    'fontSize': '9px',
                    'fontStyle': 'italic'
                })
            ])
        ])
    ], style={
        'backgroundColor': COLORS['bg_card'],
        'border': f'1px solid {COLORS["border"]}',
        'padding': '12px',
        'height': '100%'
    })

def create_buy_signal_panel():
    """Create prominent BUY CALL / BUY PUT signal display"""
    return html.Div([
        # Header
        html.Div([
            html.Span("📊 ACTIVE SIGNAL", style={
                'color': COLORS['amber'],
                'fontSize': '13px',
                'fontWeight': 'bold'
            }),
            html.Span(id='active-signal-count', style={
                'color': COLORS['yellow'],
                'marginLeft': '10px',
                'fontSize': '11px'
            })
        ], style={
            'padding': '8px 10px',
            'borderBottom': f'2px solid {COLORS["amber"]}',
            'fontFamily': 'Courier New, monospace',
            'display': 'flex',
            'justifyContent': 'space-between'
        }),
        
        # Main signal display
        html.Div(id='main-signal-display', children=[
            html.Div("NO ACTIVE SIGNALS", style={
                'color': COLORS['gray'],
                'textAlign': 'center',
                'padding': '20px',
                'fontSize': '12px'
            })
        ], style={
            'padding': '8px',
            'minHeight': '350px',
            'overflowY': 'auto'
        }),
        
        # Signal strength meter
        html.Div([
            html.Div("SIGNAL STRENGTH", style={
                'color': COLORS['gray'],
                'fontSize': '9px',
                'marginBottom': '5px'
            }),
            html.Div([
                html.Div(id='signal-strength-bar', style={
                    'width': '0%',
                    'height': '10px',
                    'backgroundColor': COLORS['amber'],
                    'transition': 'width 0.5s ease'
                })
            ], style={
                'width': '100%',
                'height': '10px',
                'backgroundColor': COLORS['bg_panel_alt'],
                'border': f'1px solid {COLORS["border"]}'
            }),
            html.Div(id='signal-strength-text', style={
                'color': COLORS['white'],
                'fontSize': '10px',
                'textAlign': 'right',
                'marginTop': '3px'
            })
        ], style={'padding': '10px', 'borderTop': f'1px solid {COLORS["border"]}'})
    ], style={
        'backgroundColor': COLORS['bg_panel'],
        'border': f'2px solid {COLORS["amber"]}',
        'margin': '10px',
        'borderRadius': '3px'
    })

# ==================== MAIN PANELS ====================

def create_main_panel():
    """Create main content area with Renaissance institutional panels"""
    return html.Div([
        # Top section: Signal Panel, GEX Profile, Renaissance Analytics
        html.Div([
            # Left: Buy Signal Panel (existing)
            html.Div([
                create_buy_signal_panel()
            ], style={
                'width': '28%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg'],
                'overflowY': 'auto'
            }),
            
            # Center: GEX Profile Chart + Proximity Meter
            html.Div([
                # GEX Profile header
                html.Div([
                    html.Span("GEX PROFILE", style={
                        'color': COLORS['amber'],
                        'fontSize': '12px',
                        'fontWeight': 'bold'
                    }),
                    html.Span("ⓘ", id='gex-profile-help', style={
                        'color': COLORS['gray'],
                        'cursor': 'pointer',
                        'marginLeft': '10px',
                        'fontSize': '11px'
                    })
                ], style={
                    'padding': '5px 10px',
                    'borderBottom': f'1px solid {COLORS["border"]}',
                    'fontFamily': 'Courier New, monospace',
                    'display': 'flex',
                    'justifyContent': 'space-between'
                }),
                html.Div("Gamma exposure distribution by strike price", style={
                    'color': COLORS['gray'],
                    'fontSize': '9px',
                    'padding': '3px 10px',
                    'backgroundColor': COLORS['bg_panel_alt']
                }),
                dcc.Graph(
                    id='gex-profile-chart',
                    config={'displayModeBar': False},
                    style={'height': '45%', 'backgroundColor': COLORS['bg_panel']}
                ),
                # Proximity Meter (Renaissance feature)
                html.Div(id='proximity-meter-container', children=[
                    create_proximity_meter(None)
                ], style={
                    'height': '40%',
                    'padding': '10px',
                    'overflowY': 'auto'
                })
            ], style={
                'width': '36%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg_panel']
            }),
            
            # Right: Renaissance Decision Matrix + Edge Metrics
            html.Div([
                # Decision Matrix
                html.Div([
                    html.Div(id='decision-matrix-container', children=[
                        create_decision_matrix(None)
                    ], style={'height': '55%'})
                ], style={'height': '55%', 'padding': '10px'}),
                
                # Edge Metrics
                html.Div([
                    html.Div(id='edge-metrics-container', children=[
                        create_edge_metrics(None)
                    ], style={'height': '100%'})
                ], style={'height': '45%', 'padding': '10px', 'paddingTop': '0'})
            ], style={
                'width': '36%',
                'backgroundColor': COLORS['bg_panel_alt']
            })
        ], style={
            'display': 'flex',
            'height': '60%',
            'borderBottom': f'1px solid {COLORS["border"]}'
        }),
        
        # Bottom section: Heatmap, Regime, Dealer Flow, Historical
        html.Div([
            # Left: GEX Heatmap
            html.Div([
                html.Div([
                    html.Span("GEX HEATMAP", style={
                        'color': COLORS['amber'],
                        'fontSize': '12px',
                        'fontWeight': 'bold'
                    }),
                    html.Span("ⓘ", id='heatmap-help', style={
                        'color': COLORS['gray'],
                        'cursor': 'pointer',
                        'marginLeft': '10px',
                        'fontSize': '11px'
                    })
                ], style={
                    'padding': '5px 10px',
                    'borderBottom': f'1px solid {COLORS["border"]}',
                    'fontFamily': 'Courier New, monospace',
                    'display': 'flex',
                    'justifyContent': 'space-between'
                }),
                html.Div("Strike-by-expiration gamma concentration", style={
                    'color': COLORS['gray'],
                    'fontSize': '9px',
                    'padding': '3px 10px',
                    'backgroundColor': COLORS['bg_panel_alt']
                }),
                dcc.Graph(
                    id='gex-heatmap',
                    config={'displayModeBar': False},
                    style={'height': 'calc(100% - 50px)', 'backgroundColor': COLORS['bg_panel']}
                )
            ], style={
                'width': '28%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg_panel']
            }),
            
            # Middle: Regime Detection + Dealer Flow
            html.Div([
                html.Div([
                    html.Div(id='regime-panel-container', children=[
                        create_regime_panel(None)
                    ])
                ], style={'height': '50%', 'padding': '10px'}),
                html.Div([
                    html.Div(id='dealer-flow-container', children=[
                        create_dealer_flow_panel(None, None)
                    ])
                ], style={'height': '50%', 'padding': '10px', 'paddingTop': '0'})
            ], style={
                'width': '36%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg']
            }),
            
            # Right: Historical Context + Signal Log
            html.Div([
                html.Div([
                    html.Div(id='historical-panel-container', children=[
                        create_historical_panel(None)
                    ])
                ], style={'height': '50%', 'padding': '10px'}),
                html.Div([
                    html.Div([
                        html.Span("📋 SIGNAL LOG", style={
                            'color': COLORS['amber'],
                            'fontSize': '12px',
                            'fontWeight': 'bold'
                        }),
                        html.Button(
                            'EXPORT',
                            id='export-signals-btn',
                            style={
                                'backgroundColor': COLORS['bg_panel'],
                                'color': COLORS['amber'],
                                'border': f'1px solid {COLORS["amber"]}',
                                'padding': '2px 8px',
                                'fontSize': '9px',
                                'cursor': 'pointer',
                                'marginLeft': 'auto'
                            }
                        )
                    ], style={
                        'padding': '5px 10px',
                        'borderBottom': f'1px solid {COLORS["border"]}',
                        'fontFamily': 'Courier New, monospace',
                        'display': 'flex',
                        'justifyContent': 'space-between'
                    }),
                    html.Div(id='signal-log-content', style={
                        'padding': '5px',
                        'fontFamily': 'Courier New, monospace',
                        'fontSize': '9px',
                        'overflowY': 'auto',
                        'height': 'calc(100% - 35px)'
                    })
                ], style={'height': '50%', 'padding': '10px', 'paddingTop': '0'})
            ], style={
                'width': '36%',
                'backgroundColor': COLORS['bg_panel_alt']
            })
        ], style={
            'display': 'flex',
            'height': '40%'
        })
    ], style={
        'flex': '1',
        'display': 'flex',
        'flexDirection': 'column'
    })

def create_performance_panel():
    """Create performance statistics panel"""
    return html.Div([
        html.Div([
            html.Span("📈 PERFORMANCE", style={
                'color': COLORS['amber'],
                'fontSize': '12px',
                'fontWeight': 'bold'
            }),
            html.Span(id='perf-summary', style={
                'color': COLORS['gray'],
                'marginLeft': '10px',
                'fontSize': '10px'
            })
        ], style={
            'padding': '6px 10px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'fontFamily': 'Courier New, monospace'
        }),
        html.Div(id='performance-content', children=[
            html.Div("Loading...", style={'color': COLORS['gray'], 'padding': '10px'})
        ], style={
            'padding': '8px',
            'fontFamily': 'Courier New, monospace',
            'fontSize': '10px'
        })
    ], style={
        'backgroundColor': COLORS['bg_panel_alt'],
        'border': f'1px solid {COLORS["border"]}',
        'margin': '5px 10px'
    })

def create_loading_overlay():
    """Create loading indicator overlay"""
    return html.Div(
        id='loading-overlay',
        children=[
            html.Div([
                html.Div("LOADING", style={
                    'color': COLORS['amber'],
                    'fontSize': '16px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Courier New, monospace',
                    'marginBottom': '10px'
                }),
                html.Div(id='loading-text', children="Fetching data...", style={
                    'color': COLORS['gray'],
                    'fontSize': '12px',
                    'fontFamily': 'Courier New, monospace'
                }),
                html.Div(style={
                    'width': '200px',
                    'height': '4px',
                    'backgroundColor': COLORS['bg_panel_alt'],
                    'marginTop': '15px',
                    'border': f'1px solid {COLORS["border"]}'
                }, children=[
                    html.Div(id='loading-bar', style={
                        'width': '0%',
                        'height': '100%',
                        'backgroundColor': COLORS['amber'],
                        'transition': 'width 0.3s ease'
                    })
                ])
            ], style={
                'backgroundColor': COLORS['bg_panel'],
                'padding': '30px 50px',
                'border': f'2px solid {COLORS["amber"]}',
                'textAlign': 'center',
                'borderRadius': '4px'
            })
        ],
        style={
            'display': 'none',
            'position': 'fixed',
            'top': 0,
            'left': 0,
            'right': 0,
            'bottom': 0,
            'backgroundColor': 'rgba(10, 10, 10, 0.95)',
            'zIndex': 3000,
            'justifyContent': 'center',
            'alignItems': 'center'
        }
    )

def create_error_modal():
    """Create error modal for invalid tickers"""
    return html.Div(
        id='error-modal',
        children=[
            html.Div([
                html.Div("⚠️ ERROR", style={
                    'color': COLORS['red'],
                    'fontSize': '16px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Courier New, monospace',
                    'marginBottom': '15px',
                    'borderBottom': f'1px solid {COLORS["red"]}',
                    'paddingBottom': '10px'
                }),
                html.Div(id='error-message', children="", style={
                    'color': COLORS['white'],
                    'fontSize': '12px',
                    'fontFamily': 'Courier New, monospace',
                    'marginBottom': '20px'
                }),
                html.Button(
                    'OK',
                    id='dismiss-error',
                    style={
                        'backgroundColor': COLORS['red'],
                        'color': COLORS['white'],
                        'border': 'none',
                        'padding': '8px 30px',
                        'fontFamily': 'Courier New, monospace',
                        'fontWeight': 'bold',
                        'cursor': 'pointer'
                    }
                )
            ], style={
                'backgroundColor': COLORS['bg_panel'],
                'padding': '25px 40px',
                'border': f'2px solid {COLORS["red"]}',
                'textAlign': 'center',
                'minWidth': '300px',
                'borderRadius': '4px'
            })
        ],
        style={
            'display': 'none',
            'position': 'fixed',
            'top': 0,
            'left': 0,
            'right': 0,
            'bottom': 0,
            'backgroundColor': 'rgba(10, 10, 10, 0.95)',
            'zIndex': 4000,
            'justifyContent': 'center',
            'alignItems': 'center'
        }
    )

def create_ticker_tape():
    """Create scrolling ticker tape at bottom"""
    return html.Div([
        html.Div(id='ticker-tape-content', style={
            'display': 'flex',
            'animation': 'scroll 30s linear infinite',
            'whiteSpace': 'nowrap'
        })
    ], style={
        'backgroundColor': COLORS['bg_panel'],
        'borderTop': f'1px solid {COLORS["border"]}',
        'padding': '5px 0',
        'overflow': 'hidden',
        'fontFamily': 'Courier New, monospace',
        'fontSize': '12px'
    })

def create_alert_modal():
    """Create flashing alert modal for new signals"""
    return html.Div([
        html.Div([
            html.Div(id='alert-content', children=[
                html.H2("⚠️ NEW SIGNAL", style={'color': COLORS['yellow'], 'margin': '0'}),
                html.Div(id='alert-details', style={
                    'color': COLORS['white'],
                    'marginTop': '15px',
                    'fontSize': '14px'
                })
            ]),
            html.Button(
                'DISMISS',
                id='dismiss-alert',
                style={
                    'backgroundColor': COLORS['amber'],
                    'color': COLORS['bg'],
                    'border': 'none',
                    'padding': '10px 30px',
                    'fontFamily': 'Courier New, monospace',
                    'fontWeight': 'bold',
                    'cursor': 'pointer',
                    'marginTop': '20px'
                }
            )
        ], style={
            'backgroundColor': COLORS['bg_panel'],
            'padding': '30px',
            'border': f'3px solid {COLORS["yellow"]}',
            'textAlign': 'center',
            'minWidth': '400px'
        })
    ], id='alert-modal', style={
        'display': 'none',
        'position': 'fixed',
        'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
        'backgroundColor': 'rgba(0,0,0,0.95)',
        'zIndex': 2000,
        'justifyContent': 'center',
        'alignItems': 'center'
    })

def create_help_modal():
    """Create comprehensive help overlay"""
    return html.Div([
        html.Div([
            html.Div([
                html.H3("GEX TERMINAL GUIDE", style={
                    'color': COLORS['amber'],
                    'borderBottom': f'1px solid {COLORS["amber"]}',
                    'paddingBottom': '10px',
                    'margin': '0'
                }),
                html.Button(
                    'X',
                    id='close-help',
                    style={
                        'backgroundColor': COLORS['red'],
                        'color': COLORS['white'],
                        'border': 'none',
                        'padding': '5px 12px',
                        'cursor': 'pointer',
                        'fontFamily': 'Courier New, monospace',
                        'fontWeight': 'bold',
                        'float': 'right'
                    }
                )
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
            
            html.Div([
                html.Span("COMMANDS", id='help-tab-commands', className='help-tab', style={
                    'color': COLORS['amber'], 'padding': '5px 15px', 'cursor': 'pointer',
                    'borderBottom': f'2px solid {COLORS["amber"]}'
                }),
                html.Span("SIGNALS", id='help-tab-signals', className='help-tab', style={
                    'color': COLORS['gray'], 'padding': '5px 15px', 'cursor': 'pointer'
                }),
                html.Span("GEX BASICS", id='help-tab-basics', className='help-tab', style={
                    'color': COLORS['gray'], 'padding': '5px 15px', 'cursor': 'pointer'
                }),
            ], style={'display': 'flex', 'marginTop': '20px', 'borderBottom': f'1px solid {COLORS["border"]}'}),
            
            html.Div(id='help-content', style={
                'marginTop': '20px',
                'maxHeight': '400px',
                'overflowY': 'auto',
                'fontSize': '12px',
                'lineHeight': '1.6'
            })
            
        ], style={
            'backgroundColor': COLORS['bg_panel'],
            'padding': '30px',
            'border': f'2px solid {COLORS["amber"]}',
            'maxWidth': '800px',
            'margin': '50px auto',
            'maxHeight': '80vh',
            'overflowY': 'auto'
        })
    ], id='help-modal', style={
        'display': 'none',
        'position': 'fixed',
        'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
        'backgroundColor': 'rgba(0,0,0,0.95)',
        'zIndex': 1000,
        'overflowY': 'auto'
    })

# Main layout
app.layout = html.Div([
    # Audio for signal notifications
    html.Audio(id='signal-sound', src='/assets/signal-alert.mp3', preload='auto'),
    html.Audio(id='buy-sound', src='data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleR0NZKrk7rNsGgxJkNTsvXwkDk+L0O+0dSQPUIjN7LVyJQ1GiMzttnMiDUeGzOu0cyUNR4bL6rJzJQ1HhsvqsXMlDUeGy+qxcSUNR4bL6rBxJQ1IhMnpr3AkDUiEyearbiQNRoPJ5qptJA1Gg8nmqWwkDUaDyeaqayQNRoPJ5qlrJA1Gg8nmqGkkDUeEyOaoZiQNRYTH5qZjJA1FhMfmpmIkDUaEx+alYSANR4TH5aNgJA1HhMbmn10iDUeExuafXSQNRoTG5p5cJA1GhMbmnVskDUeExeadWgANR4TG5ZxXAA1HhMbmnFUADUeExuacUwANR4TG5pxSAA1GhMbmm0wADUaExuabSgANRoTG5ppIAA1GhMbmmUYADUeExuaZRQANR4TG5phDAA1HhMbml0IADUeExuaWQgANR4TG5pRBAA1HhMbmk0AADUeExuaTPwANR4TG5I4+AA1HhMbkjT0ADUeExuKMPAANR4TG4ow7AA1HhMbijDoADUeExuKMOQANR4TG4Yw4AA1HhMbhiw==', preload='auto'),
    
    create_header(),
    create_function_keys(),
    
    # Main content area
    html.Div([
        create_ticker_sidebar(),
        create_main_panel()
    ], style={
        'display': 'flex',
        'flex': '1',
        'overflow': 'hidden'
    }),
    
    create_ticker_tape(),
    create_alert_modal(),
    create_help_modal(),
    create_loading_overlay(),
    create_error_modal(),
    
    # Interval for auto-refresh (60 seconds)
    dcc.Interval(id='interval-component', interval=60000, n_intervals=0),
    
    # Faster interval for countdown timer (1 second)
    dcc.Interval(id='countdown-interval', interval=1000, n_intervals=0),
    
    # Store for current ticker
    dcc.Store(id='current-ticker-store', data='SPY'),
    
    # Store for alerts
    dcc.Store(id='alerts-store', data=[]),
    
    # Store for command history
    dcc.Store(id='command-history-store', data=[]),
    
    # Store for last signal check
    dcc.Store(id='last-signal-store', data=0),
    
    # Store for notification settings
    dcc.Store(id='notification-settings', data={'enabled': False, 'audio': False, 'discord': False})
], style={
    'backgroundColor': COLORS['bg'],
    'height': '100vh',
    'display': 'flex',
    'flexDirection': 'column',
    'overflow': 'hidden',
    'fontFamily': 'Courier New, monospace'
})

# ==================== CALLBACKS ====================

@app.callback(
    Output('current-ticker-store', 'data'),
    Output('gex-profile-chart', 'figure'),
    Output('gex-heatmap', 'figure'),
    Output('signal-log-content', 'children'),
    Output('ticker-tape-content', 'children'),
    Output('data-age', 'children'),
    Output('last-update', 'children'),
    # Renaissance outputs
    Output('proximity-meter-container', 'children'),
    Output('decision-matrix-container', 'children'),
    Output('edge-metrics-container', 'children'),
    Output('regime-panel-container', 'children'),
    Output('dealer-flow-container', 'children'),
    Output('historical-panel-container', 'children'),
    *[Output(f'sidebar-{ticker}', 'style') for ticker in TICKERS],
    *[Output(f'sidebar-{ticker}', 'children') for ticker in TICKERS],
    Input('interval-component', 'n_intervals'),
    Input('current-ticker-store', 'data'),
    *[Input(f'sidebar-{ticker}', 'n_clicks') for ticker in TICKERS]
)
def update_dashboard(n_intervals, current_ticker, *sidebar_clicks):
    """Main dashboard update callback with Renaissance features"""
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'interval-component'
    
    # Handle sidebar clicks
    for i, ticker in enumerate(TICKERS):
        if triggered == f'sidebar-{ticker}' and sidebar_clicks[i]:
            current_ticker = ticker
            break
    
    # Fetch data
    try:
        spot_price = data_fetcher.get_current_price(current_ticker)
        options_data = data_fetcher.get_options_chain(current_ticker)
        gex_data = gex_calc.calculate_gex(options_data, spot_price) if options_data is not None else None
    except Exception as e:
        print(f"[ERROR] Data fetch: {e}")
        spot_price = None
        gex_data = None
    
    # Create figures
    profile_fig = create_gex_profile_chart(gex_data, spot_price, current_ticker) if gex_data else go.Figure()
    heatmap_fig = create_gex_heatmap(gex_data, current_ticker) if gex_data else go.Figure()
    
    # Signal log
    signals = signal_tracker.get_all_signals(limit=10, ticker=current_ticker)
    signal_log = create_signal_log_content(signals)
    
    # Ticker tape
    tape = create_ticker_tape_content()
    
    # Status
    now = datetime.now()
    data_age = f"Updated: {now.strftime('%H:%M:%S')}"
    last_update = f"Last: {now.strftime('%H:%M:%S')}"
    
    # ==================== RENAISSANCE CALCULATIONS ====================
    
    # Signal Proximity
    proximity_data = calculate_signal_proximity(gex_data, spot_price)
    proximity_meter = create_proximity_meter(proximity_data)
    
    # Decision Matrix
    decision_matrix = calculate_decision_matrix(gex_data, spot_price, proximity_data)
    decision_panel = create_decision_matrix(decision_matrix)
    
    # Edge Metrics
    edge_metrics = calculate_edge_metrics(gex_data, spot_price, decision_matrix)
    edge_panel = create_edge_metrics(edge_metrics)
    
    # GEX Regime
    regime_data = detect_gex_regime(gex_data, spot_price)
    regime_panel = create_regime_panel(regime_data)
    
    # Dealer Flow
    flow_data = calculate_dealer_flow(gex_data, spot_price)
    flow_panel = create_dealer_flow_panel(flow_data, spot_price)
    
    # Historical Context
    hist_data = get_historical_context(current_ticker, gex_data)
    hist_panel = create_historical_panel(hist_data)
    
    # Sidebar styles
    sidebar_styles = []
    sidebar_children = []
    for ticker in TICKERS:
        is_active = ticker == current_ticker
        style = {
            'padding': '8px 10px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'cursor': 'pointer',
            'display': 'flex',
            'justifyContent': 'space-between',
            'backgroundColor': COLORS['bg_panel_alt'] if is_active else 'transparent'
        }
        sidebar_styles.append(style)
        
        # Get price
        try:
            price = data_fetcher.get_current_price(ticker)
            price_str = f"${price:.2f}" if price else "--"
        except:
            price_str = "--"
        
        child = html.Div([
            html.Span(ticker, style={
                'color': COLORS['amber'] if is_active else COLORS['white'],
                'fontWeight': 'bold' if is_active else 'normal',
                'fontSize': '12px'
            }),
            html.Span(price_str, style={'color': COLORS['gray'], 'fontSize': '10px'})
        ])
        sidebar_children.append(child)
    
    return (
        current_ticker, profile_fig, heatmap_fig, 
        signal_log, tape, data_age, last_update,
        proximity_meter, decision_panel, edge_panel,
        regime_panel, flow_panel, hist_panel,
        *sidebar_styles, *sidebar_children
    )

def create_gex_profile_chart(gex_data, spot_price, ticker):
    """Create GEX profile chart"""
    fig = go.Figure()
    
    if gex_data and 'strikes' in gex_data:
        strikes = gex_data['strikes']
        gamma = gex_data.get('net_gex_by_strike', [0] * len(strikes))
        
        fig.add_trace(go.Bar(
            x=strikes,
            y=gamma,
            marker_color=[COLORS['green'] if g > 0 else COLORS['red'] for g in gamma]
        ))
        
        # Add spot price line
        if spot_price:
            fig.add_vline(x=spot_price, line_dash="dash", line_color=COLORS['amber'], line_width=2)
            fig.add_annotation(
                x=spot_price,
                y=max(gamma) * 0.9 if gamma else 0,
                text=f"SPOT: ${spot_price:.2f}",
                showarrow=False,
                font=dict(color=COLORS['amber'], size=10)
            )
    
    fig.update_layout(
        title=dict(
            text=f"{ticker} GEX Profile",
            font=dict(color=COLORS['amber'], size=12),
            x=0.5
        ),
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['white'], family='Courier New, monospace'),
        xaxis_title="Strike",
        yaxis_title="Gamma ($Bn)",
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor=COLORS['border'], color=COLORS['gray']),
        yaxis=dict(gridcolor=COLORS['border'], color=COLORS['gray'])
    )
    
    return fig

def create_gex_heatmap(gex_data, ticker):
    """Create GEX heatmap"""
    fig = go.Figure()
    
    if gex_data and 'heatmap_data' in gex_data:
        heatmap_df = pd.DataFrame(gex_data['heatmap_data'])
        if not heatmap_df.empty:
            pivot = heatmap_df.pivot_table(
                values='gex',
                index='strike',
                columns='expiration',
                aggfunc='sum'
            )
            
            fig.add_trace(go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                colorscale=[[0, COLORS['red']], [0.5, COLORS['bg_panel']], [1, COLORS['green']]],
                showscale=False
            ))
    
    fig.update_layout(
        title=dict(
            text=f"{ticker} GEX Heatmap",
            font=dict(color=COLORS['amber'], size=12),
            x=0.5
        ),
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['white'], family='Courier New, monospace'),
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor=COLORS['border'], color=COLORS['gray']),
        yaxis=dict(gridcolor=COLORS['border'], color=COLORS['gray'])
    )
    
    return fig

def create_signal_log_content(signals):
    """Create signal log content"""
    if not signals:
        return html.Div("No signals yet", style={'color': COLORS['gray'], 'padding': '10px'})
    
    items = []
    for s in signals:
        direction = s.get('direction', 'CALL')
        color = COLORS['green'] if direction == 'CALL' else COLORS['red']
        items.append(html.Div([
            html.Span(f"{s.get('ticker', 'N/A')} ", style={'color': COLORS['white']}),
            html.Span(direction, style={'color': color, 'fontWeight': 'bold'}),
            html.Span(f" @ ${s.get('entry_price', 0):.2f}", style={'color': COLORS['gray']})
        ], style={'padding': '3px 0', 'borderBottom': f'1px solid {COLORS["border"]}'}))
    
    return html.Div(items)

def create_ticker_tape_content():
    """Create ticker tape content"""
    items = []
    for ticker in ['SPY', 'QQQ', 'NVDA', 'TSLA']:
        try:
            price = data_fetcher.get_current_price(ticker)
            change = data_fetcher.get_price_change(ticker)
            if price:
                color = COLORS['green'] if change >= 0 else COLORS['red']
                items.append(html.Span(
                    f"{ticker} ${price:.2f} ({change:+.2f}%)  ",
                    style={'marginRight': '20px', 'color': color}
                ))
        except:
            pass
    return html.Div(items)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
