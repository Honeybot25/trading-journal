"""
GEX Bloomberg Terminal Dashboard - Production Version
Professional Gamma Exposure Visualization Terminal with Signal Tracking
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

app.title = "GEX TERMINAL PRO"

# Initialize components
data_fetcher = DataFetcher()
gex_calc = GEXCalculator()
layouts = TerminalLayouts()
signal_tracker = get_signal_tracker()

# Use enhanced signal generator if available
if ENHANCED_SIGNALS_AVAILABLE:
    signal_generator = get_enhanced_signal_generator(account_size=100000)
else:
    from signal_tracker import SignalGenerator
    signal_generator = SignalGenerator()

# Bloomberg Terminal Color Scheme
COLORS = {
    'bg': '#0d0d0d',
    'bg_panel': '#1a1a1a',
    'bg_panel_alt': '#141414',
    'amber': '#FF6600',
    'amber_bright': '#FF8800',
    'amber_dim': '#CC5200',
    'yellow': '#FFFF00',
    'green': '#00FF00',
    'red': '#FF0000',
    'white': '#FFFFFF',
    'gray': '#808080',
    'gray_dark': '#404040',
    'border': '#333333',
    'cursor': '#FF6600'
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

# Global ticker state - use this for proper state management
global_current_ticker = 'SPY'

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
            # Data freshness indicator with staleness warning
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
                'display': 'none'  # Hidden by default, shown when stale
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
    
    # Test signal buttons
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
        
        # Quick ticker buttons
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
        # Create ticker rows with IDs for callback targeting
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
                **{'data-ticker': ticker}  # Store ticker for click handler
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

def create_buy_signal_panel():
    """Create prominent BUY CALL / BUY PUT signal display with professional trading platform styling"""
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
        
        # Main signal display - enhanced with all details
        html.Div(id='main-signal-display', children=[
            html.Div("NO ACTIVE SIGNALS", style={
                'color': COLORS['gray'],
                'textAlign': 'center',
                'padding': '20px',
                'fontSize': '12px'
            })
        ], style={
            'padding': '8px',
            'minHeight': '400px',
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
            'backgroundColor': 'rgba(13, 13, 13, 0.9)',
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
            'backgroundColor': 'rgba(13, 13, 13, 0.95)',
            'zIndex': 4000,
            'justifyContent': 'center',
            'alignItems': 'center'
        }
    )

def create_main_panel():
    """Create main content area with enhanced signal panels"""
    return html.Div([
        # Loading overlay
        create_loading_overlay(),
        
        # Error modal
        create_error_modal(),
        
        # Top section: Signal Panel and GEX Profile
        html.Div([
            # Left: Buy Signal Panel
            html.Div([
                create_buy_signal_panel()
            ], style={
                'width': '30%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg'],
                'overflowY': 'auto'
            }),
            
            # Middle: GEX Profile Chart
            html.Div([
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
                    style={'height': 'calc(100% - 50px)', 'backgroundColor': COLORS['bg_panel']}
                )
            ], style={
                'width': '40%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg_panel']
            }),
            
            # Right: Key Stats
            html.Div([
                html.Div([
                    html.Span("KEY LEVELS", style={
                        'color': COLORS['amber'],
                        'fontSize': '12px',
                        'fontWeight': 'bold'
                    }),
                    html.Span("ⓘ", id='key-levels-help', style={
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
                html.Div("Critical gamma levels and price targets", style={
                    'color': COLORS['gray'],
                    'fontSize': '9px',
                    'padding': '3px 10px',
                    'backgroundColor': COLORS['bg_panel_alt']
                }),
                html.Div(id='key-levels-content', style={
                    'padding': '10px',
                    'fontFamily': 'Courier New, monospace',
                    'fontSize': '11px'
                })
            ], style={
                'width': '30%',
                'backgroundColor': COLORS['bg_panel_alt']
            })
        ], style={
            'display': 'flex',
            'height': '55%',
            'borderBottom': f'1px solid {COLORS["border"]}'
        }),
        
        # Bottom section: Heatmap, Performance, and Signals Log
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
                'width': '35%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg_panel']
            }),
            
            # Middle: Performance Panel
            html.Div([
                create_performance_panel()
            ], style={
                'width': '30%',
                'borderRight': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg'],
                'overflowY': 'auto'
            }),
            
            # Right: Signal Log
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
            ], style={
                'width': '35%',
                'backgroundColor': COLORS['bg_panel_alt']
            })
        ], style={
            'display': 'flex',
            'height': '45%'
        })
    ], style={
        'flex': '1',
        'display': 'flex',
        'flexDirection': 'column'
    })

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
        'backgroundColor': 'rgba(0,0,0,0.9)',
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
            
            # Tabs for help sections
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
            
            # Help content area
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
    
    # JavaScript for sound and animations
    html.Script("""
        // Signal sound toggle
        let soundEnabled = false;
        let lastSignalId = null;
        
        function toggleSound() {
            soundEnabled = !soundEnabled;
            const btn = document.getElementById('sound-toggle');
            if (btn) {
                btn.textContent = soundEnabled ? '🔔 Sound: ON' : '🔔 Sound: OFF';
                btn.style.color = soundEnabled ? '#00FF00' : '#808080';
            }
        }
        
        function playSignalSound(isBuy) {
            if (!soundEnabled) return;
            const audio = document.getElementById(isBuy ? 'buy-sound' : 'signal-sound');
            if (audio) {
                audio.currentTime = 0;
                audio.play().catch(e => console.log('Audio play failed:', e));
            }
        }
        
        // Flash animation for new signals
        function flashSignalBanner() {
            const banner = document.querySelector('.signal-banner-new');
            if (banner) {
                banner.style.animation = 'none';
                setTimeout(() => {
                    banner.style.animation = 'flashSignal 1.5s ease-in-out 3, pulseBorder 1s ease-in-out infinite';
                }, 10);
            }
        }
        
        // Check for new signals
        setInterval(() => {
            const signalDisplay = document.getElementById('main-signal-display');
            if (signalDisplay) {
                const hasSignal = signalDisplay.textContent.includes('BUY CALL') || 
                                  signalDisplay.textContent.includes('BUY PUT');
                const signalId = signalDisplay.innerHTML;
                if (hasSignal && signalId !== lastSignalId) {
                    lastSignalId = signalId;
                    const isBuy = signalDisplay.textContent.includes('BUY CALL');
                    playSignalSound(isBuy);
                    flashSignalBanner();
                }
            }
        }, 2000);
        
        // Add click handler for sound toggle
        document.addEventListener('click', function(e) {
            if (e.target && e.target.id === 'sound-toggle') {
                toggleSound();
            }
        });
    """),
    
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
    Output('key-levels-content', 'children'),
    Output('signal-log-content', 'children'),
    Output('ticker-tape-content', 'children'),
    Output('data-age', 'children'),
    Output('last-update', 'children'),
    *[Output(f'sidebar-{ticker}', 'style') for ticker in TICKERS],
    *[Output(f'sidebar-{ticker}', 'children') for ticker in TICKERS],
    Input('interval-component', 'n_intervals'),
    Input('current-ticker-store', 'data'),
    *[Input(f'sidebar-{ticker}', 'n_clicks') for ticker in TICKERS]
)
def update_dashboard(n_intervals, current_ticker, *sidebar_clicks):
    """Main dashboard update callback"""
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
    
    # Key levels
    key_levels = create_key_levels(gex_data, spot_price, current_ticker) if gex_data else html.Div("No data")
    
    # Signal log
    signals = signal_tracker.get_all_signals(limit=10, ticker=current_ticker)
    signal_log = create_signal_log_content(signals)
    
    # Ticker tape
    tape = create_ticker_tape_content()
    
    # Status
    now = datetime.now()
    data_age = f"Updated: {now.strftime('%H:%M:%S')}"
    last_update = f"Last: {now.strftime('%H:%M:%S')}"
    
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
        current_ticker, profile_fig, heatmap_fig, key_levels, 
        signal_log, tape, data_age, last_update,
        *sidebar_styles, *sidebar_children
    )


def create_gex_profile_chart(gex_data, spot_price, ticker):
    """Create GEX profile chart"""
    fig = go.Figure()
    
    if gex_data and 'strikes' in gex_data:
        strikes = gex_data['strikes']
        gamma = gex_data.get('gamma', [0] * len(strikes))
        
        fig.add_trace(go.Bar(
            x=strikes,
            y=gamma,
            marker_color=[COLORS['green'] if g > 0 else COLORS['red'] for g in gamma]
        ))
        
        # Add spot price line
        if spot_price:
            fig.add_vline(x=spot_price, line_dash="dash", line_color=COLORS['amber'])
    
    fig.update_layout(
        title=f"{ticker} GEX Profile",
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['white']),
        xaxis_title="Strike",
        yaxis_title="Gamma",
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    return fig


def create_gex_heatmap(gex_data, ticker):
    """Create GEX heatmap"""
    fig = go.Figure()
    
    fig.update_layout(
        title=f"{ticker} GEX Heatmap",
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['white']),
        showlegend=False
    )
    
    return fig


def create_key_levels(gex_data, spot_price, ticker):
    """Create key levels display"""
    if not gex_data:
        return html.Div("No GEX data available", style={'color': COLORS['gray']})
    
    zero_gamma = gex_data.get('zero_gamma', spot_price)
    max_gamma = gex_data.get('max_gamma_strike', spot_price)
    min_gamma = gex_data.get('min_gamma_strike', spot_price)
    
    return html.Div([
        html.Div([html.Span("Spot: ", style={'color': COLORS['gray']}), 
                 html.Span(f"${spot_price:.2f}" if spot_price else "N/A", style={'color': COLORS['white']})]),
        html.Div([html.Span("Zero Gamma: ", style={'color': COLORS['gray']}),
                 html.Span(f"${zero_gamma:.2f}", style={'color': COLORS['amber']})]),
        html.Div([html.Span("Max GEX: ", style={'color': COLORS['gray']}),
                 html.Span(f"${max_gamma:.2f}", style={'color': COLORS['green']})]),
        html.Div([html.Span("Min GEX: ", style={'color': COLORS['gray']}),
                 html.Span(f"${min_gamma:.2f}", style={'color': COLORS['red']})])
    ])


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
            if price:
                items.append(html.Span(f"{ticker} ${price:.2f}  ", style={'marginRight': '20px', 'color': COLORS['amber']}))
        except:
            pass
    return html.Div(items)
