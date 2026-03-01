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

# Global loading state tracker
panel_loading_states = {
    'gex_profile': True,
    'heatmap': True,
    'key_levels': True,
    'performance': True,
    'signals': True
}

def create_skeleton_loader(height='100%', width='100%', bars=3):
    """Create animated skeleton loading bars"""
    return html.Div([
        html.Style("""
            @keyframes shimmer {
                0% { background-position: -200% 0; }
                100% { background-position: 200% 0; }
            }
            .skeleton-bar {
                background: linear-gradient(90deg, #1a1a1a 25%, #2a2a2a 50%, #1a1a1a 75%);
                background-size: 200% 100%;
                animation: shimmer 1.5s infinite;
                border-radius: 2px;
            }
        """),
        html.Div([
            html.Div(className='skeleton-bar', style={
                'height': f'{100/bars}%',
                'width': f'{100 - (i * 15)}%',
                'marginBottom': '8px',
                'opacity': f'{1 - (i * 0.15)}'
            }) for i in range(bars)
        ], style={'height': height, 'width': width, 'padding': '10px'})
    ])

TICKERS = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL']

# Global state
current_ticker = 'SPY'
command_history = []
alert_messages = []
last_signal_check = 0
active_signals_cache = []

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
                placeholder='Enter command or ticker...',
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
        
        # Status bar with countdown timer
        html.Div([
            html.Span("CONNECTED", style={'color': COLORS['green'], 'marginRight': '20px'}),
            html.Span(id='market-status', style={'color': COLORS['amber'], 'marginRight': '20px'}),
            html.Span(id='data-source-badge', style={'marginRight': '20px', 'fontWeight': 'bold'}),
            html.Span(id='rate-limit-badge', style={'color': COLORS['gray'], 'marginRight': '20px'}),
            html.Span(id='data-age', style={'color': COLORS['gray'], 'marginRight': '20px'}),
            html.Span(id='last-update', style={'color': COLORS['gray'], 'marginRight': '20px'}),
            html.Span(id='countdown-timer', style={'color': COLORS['amber'], 'fontWeight': 'bold', 'marginRight': '20px'}),
            html.Button(
                '↻ REFRESH',
                id='refresh-button',
                style={
                    'backgroundColor': COLORS['bg_panel'],
                    'color': COLORS['amber'],
                    'border': f'1px solid {COLORS["amber"]}',
                    'padding': '2px 10px',
                    'fontFamily': 'Courier New, monospace',
                    'fontSize': '10px',
                    'cursor': 'pointer',
                    'marginLeft': 'auto',
                    'marginRight': '10px'
                }
            ),
            html.Span(id='current-time', style={'color': COLORS['white']})
        ], style={
            'display': 'flex',
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
    
    return html.Div([
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
        ], style={
            'display': 'flex',
            'backgroundColor': COLORS['bg_panel'],
            'borderBottom': f'1px solid {COLORS["border"]}',
            'overflow': 'hidden'
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
    """Create left sidebar with ticker list - DYNAMIC UPDATE"""
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
        html.Div(id='ticker-list', children=[])  # Dynamic content via callback
    ], style={
        'width': '120px',
        'backgroundColor': COLORS['bg_panel'],
        'borderRight': f'1px solid {COLORS["border"]}',
        'height': '100%',
        'overflowY': 'auto'
    })

def create_buy_signal_panel():
    """Create prominent BUY CALL / BUY PUT signal display"""
    return html.Div([
        html.Div([
            html.Span("📊 SIGNALS", style={
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
        
        # Main signal display - starts with skeleton, then shows data
        html.Div(id='main-signal-display', children=[
            html.Div([
                html.Style("""
                    @keyframes skeleton-pulse {
                        0%, 100% { opacity: 0.4; }
                        50% { opacity: 0.8; }
                    }
                    .skeleton-box {
                        background: linear-gradient(90deg, #1a1a1a 25%, #2a2a2a 50%, #1a1a1a 75%);
                        background-size: 200% 100%;
                        animation: skeleton-pulse 1.5s infinite;
                        border-radius: 3px;
                    }
                """),
                html.Div(className='skeleton-box', style={
                    'height': '40px',
                    'width': '80%',
                    'margin': '20px auto',
                    'borderRadius': '4px'
                }),
                html.Div(className='skeleton-box', style={
                    'height': '20px',
                    'width': '60%',
                    'margin': '10px auto',
                    'borderRadius': '4px'
                }),
                html.Div(className='skeleton-box', style={
                    'height': '15px',
                    'width': '40%',
                    'margin': '10px auto',
                    'borderRadius': '4px'
                })
            ])
        ], style={
            'padding': '10px',
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
                })
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
            'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
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
                    'marginBottom': '20px',
                    'whiteSpace': 'pre-line'
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
            'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
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
                    html.Span("[?]", id='gex-profile-help', style={
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
                dcc.Graph(
                    id='gex-profile-chart',
                    config={'displayModeBar': False},
                    style={'height': 'calc(100% - 30px)', 'backgroundColor': COLORS['bg_panel']}
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
                    html.Span("[?]", id='key-levels-help', style={
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
                    html.Span("[?]", id='heatmap-help', style={
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
                dcc.Graph(
                    id='gex-heatmap',
                    config={'displayModeBar': False},
                    style={'height': 'calc(100% - 30px)', 'backgroundColor': COLORS['bg_panel']}
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
    # Add CSS animations for staleness warning
    html.Style("""
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        @keyframes flashRed {
            0%, 100% { background-color: #330000; }
            50% { background-color: #550000; }
        }
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
    
    # Interval for auto-refresh (60 seconds) - ensures real-time updates
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

# Track data fetch time
data_fetch_times = {}
last_update_time = datetime.now()

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

# Callbacks
@app.callback(
    Output('current-ticker-store', 'data'),
    Output('gex-profile-chart', 'figure'),
    Output('gex-heatmap', 'figure'),
    Output('key-levels-content', 'children'),
    Output('main-signal-display', 'children'),
    Output('signal-strength-bar', 'style'),
    Output('signal-strength-text', 'children'),
    Output('performance-content', 'children'),
    Output('signal-log-content', 'children'),
    Output('ticker-tape-content', 'children'),
    Output('market-status', 'children'),
    Output('data-age', 'children'),
    Output('last-update', 'children'),
    Output('current-time', 'children'),
    Output('active-signal-count', 'children'),
    Output('perf-summary', 'children'),
    Output('data-source-badge', 'children'),
    Output('rate-limit-badge', 'children'),
    Output('command-input', 'value'),  # Clear input after ticker change
    Output('ticker-list', 'children'),  # Update sidebar ticker list
    Output('error-modal', 'style'),  # Show/hide error modal
    Output('error-message', 'children'),  # Error message content
    Output('loading-overlay', 'style'),  # Show/hide loading overlay
    Output('loading-text', 'children'),  # Loading text
    Input('interval-component', 'n_intervals'),
    Input('command-go', 'n_clicks'),
    Input('command-input', 'n_submit'),
    Input('refresh-button', 'n_clicks'),
    Input('dismiss-error', 'n_clicks'),  # Dismiss error modal
    *[Input(f'quick-{ticker}', 'n_clicks') for ticker in TICKERS],
    *[Input(f'sidebar-{ticker}', 'n_clicks') for ticker in TICKERS],  # Sidebar ticker clicks
    State('command-input', 'value'),
    State('current-ticker-store', 'data')
)
def update_dashboard(n_intervals, go_clicks, submit, refresh_clicks, dismiss_error_clicks, *args):
    """Main dashboard update callback with signal tracking - FIXED TICKER SWITCHING"""
    global last_update_time
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'interval-component'
    
    # Get states - last two args are the States
    command_value = args[-2] if len(args) >= 2 else None
    current_ticker = args[-1] if args else 'SPY'
    
    # Initialize return values for UI state
    command_input_value = command_value if command_value else ''  # Keep current or clear
    error_modal_style = {'display': 'none'}
    error_message = ''
    loading_style = {'display': 'none'}
    loading_text = 'Fetching data...'
    
    # Handle dismiss error button
    if triggered == 'dismiss-error':
        error_modal_style = {'display': 'none'}
    
    # Handle refresh button - clear cache
    if triggered == 'refresh-button' and refresh_clicks:
        data_fetcher.clear_cache()
        print(f"[REFRESH] Cache cleared for manual refresh")
    
    # Handle command input (GO button or Enter key)
    if triggered in ['command-go', 'command-input']:
        if command_value:
            cmd = command_value.upper().strip()
            if cmd in TICKERS:
                current_ticker = cmd
                command_input_value = ''  # Clear input after successful ticker change
                loading_style = {
                    'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
                    'backgroundColor': 'rgba(13, 13, 13, 0.9)', 'zIndex': 3000,
                    'justifyContent': 'center', 'alignItems': 'center'
                }
                loading_text = f'Loading {current_ticker} data...'
                print(f"[TICKER SWITCH] Via command: {current_ticker}")
            elif cmd.startswith('GEX '):
                parts = cmd.split()
                ticker = parts[1] if len(parts) > 1 else None
                if ticker and ticker in TICKERS:
                    current_ticker = ticker
                    command_input_value = ''  # Clear input
                    loading_style = {
                        'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
                        'backgroundColor': 'rgba(13, 13, 13, 0.9)', 'zIndex': 3000,
                        'justifyContent': 'center', 'alignItems': 'center'
                    }
                    loading_text = f'Loading {current_ticker} data...'
                    print(f"[TICKER SWITCH] Via GEX command: {current_ticker}")
                else:
                    # Invalid ticker after GEX command
                    valid_tickers = ', '.join(TICKERS)
                    error_message = f"Invalid ticker: '{ticker or 'N/A'}'.\n\nValid tickers: {valid_tickers}"
                    error_modal_style = {
                        'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
                        'backgroundColor': 'rgba(13, 13, 13, 0.95)', 'zIndex': 4000,
                        'justifyContent': 'center', 'alignItems': 'center'
                    }
                    command_input_value = ''  # Clear invalid input
                    print(f"[ERROR] Invalid ticker via GEX command: {ticker}")
            else:
                # Invalid ticker command
                valid_tickers = ', '.join(TICKERS)
                error_message = f"Invalid ticker: '{cmd}'.\n\nValid tickers: {valid_tickers}"
                error_modal_style = {
                    'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
                    'backgroundColor': 'rgba(13, 13, 13, 0.95)', 'zIndex': 4000,
                    'justifyContent': 'center', 'alignItems': 'center'
                }
                command_input_value = ''  # Clear invalid input
                print(f"[ERROR] Invalid ticker command: {cmd}")
    
    # Handle quick ticker buttons
    quick_button_map = {f'quick-{ticker}': ticker for ticker in TICKERS}
    if triggered in quick_button_map:
        current_ticker = quick_button_map[triggered]
        loading_style = {
            'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
            'backgroundColor': 'rgba(13, 13, 13, 0.9)', 'zIndex': 3000,
            'justifyContent': 'center', 'alignItems': 'center'
        }
        loading_text = f'Loading {current_ticker} data...'
        print(f"[TICKER SWITCH] Via quick button: {current_ticker}")
    
    # Handle sidebar ticker clicks
    sidebar_button_map = {f'sidebar-{ticker}': ticker for ticker in TICKERS}
    if triggered in sidebar_button_map:
        current_ticker = sidebar_button_map[triggered]
        loading_style = {
            'display': 'flex', 'position': 'fixed', 'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
            'backgroundColor': 'rgba(13, 13, 13, 0.9)', 'zIndex': 3000,
            'justifyContent': 'center', 'alignItems': 'center'
        }
        loading_text = f'Loading {current_ticker} data...'
        print(f"[TICKER SWITCH] Via sidebar: {current_ticker}")
    
    # Fetch data with error handling
    fetch_errors = []
    options_data = None
    spot_price = None
    
    try:
        spot_price = data_fetcher.get_current_price(current_ticker)
        if spot_price is None:
            fetch_errors.append("Price fetch failed")
    except Exception as e:
        fetch_errors.append(f"Price error: {str(e)[:30]}")
        print(f"[ERROR] Price fetch for {current_ticker}: {e}")
    
    try:
        options_data = data_fetcher.get_options_chain(current_ticker)
        if options_data is None or options_data.empty:
            fetch_errors.append("Options data unavailable")
    except Exception as e:
        fetch_errors.append(f"Options error: {str(e)[:30]}")
        print(f"[ERROR] Options fetch for {current_ticker}: {e}")
    
    # Record fetch time
    data_fetch_times[current_ticker] = time.time()
    last_update_time = datetime.now()
    
    # Calculate GEX with validation
    try:
        if spot_price is None:
            spot_price = 100.0  # Fallback price
        
        gex_data = gex_calc.calculate_gex(options_data, spot_price)
        
        # Validate GEX data
        if not gex_data.get('strikes') or len(gex_data.get('strikes', [])) == 0:
            raise ValueError("No valid strikes in GEX data")
        
        total_gex = gex_data.get('total_gex', 0)
        if total_gex is None or (isinstance(total_gex, float) and np.isnan(total_gex)):
            gex_data['total_gex'] = 0
            fetch_errors.append("GEX calculation returned NaN")
        
    except Exception as e:
        print(f"[ERROR] GEX calculation for {current_ticker}: {e}")
        fetch_errors.append(f"GEX calc error: {str(e)[:30]}")
        gex_data = gex_calc._generate_sample_data(spot_price)
    
    # Generate trading signal
    signal = None
    try:
        # Get price history for RSI calculation
        price_history = None
        try:
            hist_data = data_fetcher.get_historical_data(current_ticker, period='1mo', interval='1d')
            if not hist_data.empty:
                price_history = hist_data['Close'].tolist()
        except:
            pass
        
        # Use enhanced signal generator
        if ENHANCED_SIGNALS_AVAILABLE:
            signal = signal_generator.generate_enhanced_signal(
                current_ticker, gex_data, spot_price, price_history
            )
            # Convert to dict for storage
            if signal:
                signal_for_storage = signal.to_dict()
                signal_id = signal_tracker.log_signal(signal_for_storage)
                signal.signal_id = signal_id
        else:
            signal = signal_generator.generate_signal(current_ticker, gex_data, spot_price, price_history)
    except Exception as e:
        print(f"[ERROR] Signal generation: {e}")
        import traceback
        traceback.print_exc()
    
    # Check for signal exits
    try:
        current_prices = {t: data_fetcher.get_current_price(t) for t in TICKERS}
        signal_tracker.check_signal_exits(current_prices)
    except Exception as e:
        print(f"[ERROR] Signal exit check: {e}")
    
    # Create visualizations
    try:
        profile_fig = create_gex_profile_chart(gex_data, spot_price, current_ticker)
    except Exception as e:
        print(f"[ERROR] Profile chart: {e}")
        profile_fig = go.Figure()
        profile_fig.update_layout(
            paper_bgcolor=COLORS['bg_panel'],
            plot_bgcolor=COLORS['bg_panel'],
            font=dict(color=COLORS['amber']),
            title=dict(text='CHART ERROR', font=dict(color=COLORS['red']))
        )
    
    try:
        heatmap_fig = create_gex_heatmap(gex_data, current_ticker)
    except Exception as e:
        print(f"[ERROR] Heatmap: {e}")
        heatmap_fig = go.Figure()
        heatmap_fig.update_layout(
            paper_bgcolor=COLORS['bg_panel'],
            plot_bgcolor=COLORS['bg_panel']
        )
    
    # Create Key Levels
    try:
        key_levels = create_key_levels(gex_data, spot_price, current_ticker)
        if fetch_errors:
            key_levels = html.Div([
                html.Div(f"⚠ DATA WARNINGS: {', '.join(fetch_errors[:2])}", 
                    style={'color': COLORS['yellow'], 'fontSize': '10px', 'marginBottom': '10px'}),
                key_levels
            ])
    except Exception as e:
        print(f"[ERROR] Key levels: {e}")
        key_levels = html.Div("KEY LEVELS UNAVAILABLE", style={'color': COLORS['red']})
    
    # Create Main Signal Display
    try:
        signal_display, signal_strength_style, signal_strength_text = create_signal_display(signal, gex_data, spot_price)
    except Exception as e:
        print(f"[ERROR] Signal display: {e}")
        signal_display = html.Div("SIGNAL DISPLAY ERROR", style={'color': COLORS['red']})
        signal_strength_style = {'width': '0%', 'height': '10px', 'backgroundColor': COLORS['amber']}
        signal_strength_text = "N/A"
    
    # Create Performance Panel
    try:
        perf_content, perf_summary = create_performance_content()
    except Exception as e:
        print(f"[ERROR] Performance: {e}")
        perf_content = html.Div("PERFORMANCE DATA UNAVAILABLE", style={'color': COLORS['red']})
        perf_summary = ""
    
    # Create Signal Log
    try:
        signal_log = create_signal_log()
    except Exception as e:
        print(f"[ERROR] Signal log: {e}")
        signal_log = html.Div("LOG ERROR", style={'color': COLORS['red']})
    
    # Create Ticker Tape
    try:
        ticker_tape = create_ticker_tape_content()
    except Exception as e:
        print(f"[ERROR] Ticker tape: {e}")
        ticker_tape = []
    
    # Status with market hours
    market_info = get_market_status()
    market_status = market_info['status']
    market_color = market_info['color']
    
    last_update = f"UPDATED: {last_update_time.strftime('%H:%M:%S')}"
    current_time_str = datetime.now().strftime('%H:%M:%S')
    
    # Get open signals count
    try:
        open_signals = signal_tracker.get_open_signals()
        active_signal_count = f"[{len(open_signals)} OPEN]"
    except:
        active_signal_count = "[0 OPEN]"
    
    # Get data source status for badges
    source_status = data_fetcher.get_data_source_status()
    polygon_status = source_status.get('polygon_status', {})
    
    # Data source badge
    if source_status['source'] == 'POLYGON':
        data_source_badge = html.Span("POLYGON", style={
            'color': COLORS['amber_bright'],
            'backgroundColor': '#333300',
            'padding': '1px 6px',
            'border': f'1px solid {COLORS["amber"]}',
            'fontWeight': 'bold'
        })
    elif 'YFINANCE' in source_status['source']:
        data_source_badge = html.Span("YFINANCE", style={
            'color': COLORS['gray'],
            'padding': '1px 6px',
            'border': f'1px solid {COLORS["gray"]}'
        })
    else:
        data_source_badge = html.Span(source_status['source'], style={'color': COLORS['gray']})
    
    # Rate limit badge
    rate_limit_remaining = polygon_status.get('rate_limit_remaining', 0)
    if rate_limit_remaining > 3:
        rate_limit_color = COLORS['green']
    elif rate_limit_remaining > 1:
        rate_limit_color = COLORS['amber']
    else:
        rate_limit_color = COLORS['red']
    
    rate_limit_badge = html.Span(f"API: {rate_limit_remaining}/5", style={
        'color': rate_limit_color,
        'fontSize': '10px'
    }) if polygon_status.get('configured') else ""
    
    # Generate sidebar ticker list with current ticker highlighted
    sidebar_tickers = []
    for ticker in TICKERS:
        is_active = ticker == current_ticker
        ticker_row = html.Div([
            html.Span(ticker, style={
                'color': COLORS['amber'] if is_active else COLORS['white'],
                'fontWeight': 'bold' if is_active else 'normal'
            }),
            html.Div(id=f'price-{ticker}', style={'color': COLORS['gray'], 'fontSize': '10px'})
        ], style={
            'padding': '8px 10px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'cursor': 'pointer',
            'backgroundColor': COLORS['bg_panel_alt'] if is_active else 'transparent',
            'fontFamily': 'Courier New, monospace',
            'fontSize': '12px'
        }, id=f'sidebar-{ticker}', className='ticker-row')
        sidebar_tickers.append(ticker_row)
    
    return (
        current_ticker, profile_fig, heatmap_fig, key_levels,
        signal_display, signal_strength_style, signal_strength_text,
        perf_content, signal_log, ticker_tape,
        html.Span(market_status, style={'color': market_color}),
        data_age, last_update, current_time_str,
        active_signal_count, perf_summary,
        data_source_badge, rate_limit_badge,
        command_input_value,  # Clear/keep command input
        sidebar_tickers,  # Updated sidebar ticker list
        error_modal_style,  # Show/hide error modal
        error_message,  # Error message content
        loading_style,  # Show/hide loading overlay
        loading_text  # Loading text
    )

@app.callback(
    Output('countdown-timer', 'children'),
    Input('countdown-interval', 'n_intervals')
)
def update_countdown(n):
    """Update countdown timer to next refresh"""
    global last_update_time
    elapsed = (datetime.now() - last_update_time).total_seconds()
    remaining = max(0, 60 - elapsed)
    return f"NEXT: {int(remaining)}s"

def create_signal_display(signal, gex_data, spot_price):
    """Create the main BUY CALL / BUY PUT signal display with contract details"""
    if not signal:
        # No active signal - show neutral state
        total_gex = gex_data.get('total_gex', 0)
        
        if total_gex > 5:
            bias = "GAMMA PINNING"
            bias_color = COLORS['green']
            bias_desc = "Dealers long gamma - expect mean reversion"
        elif total_gex < -5:
            bias = "TREND POTENTIAL"
            bias_color = COLORS['red']
            bias_desc = "Dealers short gamma - breakouts can accelerate"
        else:
            bias = "NEUTRAL"
            bias_color = COLORS['gray']
            bias_desc = "No clear directional bias"
        
        return (
            html.Div([
                html.Div(bias, style={
                    'color': bias_color,
                    'fontSize': '18px',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'padding': '15px'
                }),
                html.Div(bias_desc, style={
                    'color': COLORS['gray'],
                    'fontSize': '10px',
                    'textAlign': 'center'
                }),
                html.Div(f"NET GEX: {total_gex:+.1f}B", style={
                    'color': COLORS['white'],
                    'fontSize': '12px',
                    'textAlign': 'center',
                    'marginTop': '10px'
                })
            ]),
            {'width': '0%', 'height': '10px', 'backgroundColor': COLORS['gray']},
            "WAITING FOR SETUP"
        )
    
    # Check if this is an enhanced signal
    is_enhanced = hasattr(signal, 'contract') or isinstance(signal, dict) and 'contract_specs' in signal
    
    if is_enhanced and hasattr(signal, 'to_dict'):
        signal_dict = signal.to_dict()
    else:
        signal_dict = signal if isinstance(signal, dict) else signal.__dict__
    
    direction = signal_dict.get('direction', 'CALL')
    is_call = direction == 'CALL'
    
    signal_color = COLORS['green'] if is_call else COLORS['red']
    signal_bg = '#003300' if is_call else '#330000'
    signal_emoji = "🟢" if is_call else "🔴"
    signal_text = "BUY CALL" if is_call else "BUY PUT"
    
    confidence = signal_dict.get('confidence', 50)
    ticker = signal_dict.get('ticker', 'UNKNOWN')
    
    # Get contract specs
    contract = signal_dict.get('contract_specs', signal_dict.get('contract', {}))
    zones = signal_dict.get('zones', {})
    greeks = signal_dict.get('greeks', {})
    reasoning = signal_dict.get('reasoning', {})
    
    # Build enhanced display
    display = html.Div([
        # Main signal banner
        html.Div([
            html.Div(f"{signal_emoji} {signal_text}", style={
                'color': signal_color,
                'fontSize': '20px',
                'fontWeight': 'bold',
                'textAlign': 'center',
                'padding': '8px',
                'backgroundColor': signal_bg,
                'border': f'2px solid {signal_color}',
            }),
        ]),
        
        # Contract Specifications
        html.Div([
            html.Div("📋 CONTRACT SPEC", style={
                'color': COLORS['amber'],
                'fontSize': '9px',
                'fontWeight': 'bold',
                'borderBottom': f'1px solid {COLORS["border"]}',
                'paddingBottom': '3px',
                'marginBottom': '5px'
            }),
            html.Div([
                html.Span(f"{ticker} ", style={'color': COLORS['white'], 'fontSize': '11px', 'fontWeight': 'bold'}),
                html.Span(f"${contract.get('strike', 0):.0f} ", style={'color': signal_color, 'fontSize': '11px', 'fontWeight': 'bold'}),
                html.Span(f"{contract.get('strike_type', 'ATM')}", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            ]),
            html.Div([
                html.Span(f"EXP: {contract.get('expiration', 'N/A')} ", style={'color': COLORS['white'], 'fontSize': '9px'}),
                html.Span(f"({contract.get('expiration_days', 0)}DTE)", style={'color': COLORS['amber'], 'fontSize': '9px'}),
            ]),
            html.Div([
                html.Span(f"Est. Price: ${contract.get('estimated_price', 0):.2f}", style={'color': COLORS['green'], 'fontSize': '10px'}),
            ]) if contract.get('estimated_price') else None,
        ], style={'padding': '8px', 'backgroundColor': COLORS['bg_panel_alt'], 'marginTop': '8px'}),
        
        # Entry/Exit Zones
        html.Div([
            html.Div("🎯 ENTRY/EXIT", style={
                'color': COLORS['amber'],
                'fontSize': '9px',
                'fontWeight': 'bold',
                'borderBottom': f'1px solid {COLORS["border"]}',
                'paddingBottom': '3px',
                'marginBottom': '5px'
            }),
            html.Div([
                html.Div([
                    html.Span("ENTRY: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                    html.Span(f"${zones.get('entry_price_low', 0):.2f}-${zones.get('entry_price_high', 0):.2f}", 
                             style={'color': COLORS['white'], 'fontSize': '10px', 'fontWeight': 'bold'})
                ]),
                html.Div([
                    html.Span("STOP: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                    html.Span(f"${zones.get('stop_loss', 0):.2f}", style={'color': COLORS['red'], 'fontSize': '10px'}),
                    html.Span(" | ", style={'color': COLORS['gray']}),
                    html.Span("TARGET: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
                    html.Span(f"${zones.get('take_profit', 0):.2f}", style={'color': COLORS['green'], 'fontSize': '10px'})
                ]),
                html.Div([
                    html.Span(f"R/R: {zones.get('risk_reward_ratio', 0):.1f}:1", 
                             style={'color': COLORS['amber'], 'fontSize': '9px', 'fontWeight': 'bold'}),
                    html.Span(" | ", style={'color': COLORS['gray']}),
                    html.Span(f"Max: {zones.get('max_contracts', 0)} ctr", 
                             style={'color': COLORS['white'], 'fontSize': '9px'}),
                ]) if zones.get('max_contracts') else None,
            ]),
        ], style={'padding': '8px', 'marginTop': '5px'}),
        
        # Greeks
        html.Div([
            html.Div("📊 GREEKS", style={
                'color': COLORS['amber'],
                'fontSize': '9px',
                'fontWeight': 'bold',
                'borderBottom': f'1px solid {COLORS["border"]}',
                'paddingBottom': '3px',
                'marginBottom': '5px'
            }),
            html.Div([
                html.Div([
                    html.Span(f"Δ{greeks.get('delta', 0):.2f}", style={'color': COLORS['white'], 'fontSize': '9px'}),
                    html.Span(f" Γ{greeks.get('gamma', 0):.3f}", style={'color': COLORS['white'], 'fontSize': '9px'}),
                    html.Span(f" Θ{greeks.get('theta', 0):.2f}", style={'color': COLORS['white'], 'fontSize': '9px'}),
                ]),
                html.Div([
                    html.Span(f"IV: {greeks.get('iv', 0)*100:.0f}%", style={'color': COLORS['yellow'], 'fontSize': '9px'}),
                    html.Span(f" ({greeks.get('iv_percentile', 0):.0f}p)", style={'color': COLORS['gray'], 'fontSize': '8px'}),
                ]) if greeks.get('iv') else None,
            ]),
        ], style={'padding': '8px', 'backgroundColor': COLORS['bg_panel_alt'], 'marginTop': '5px'}),
        
        # Reasoning (collapsed by default)
        html.Div([
            html.Div("💡 ANALYSIS", style={
                'color': COLORS['amber'],
                'fontSize': '9px',
                'fontWeight': 'bold',
                'borderBottom': f'1px solid {COLORS["border"]}',
                'paddingBottom': '3px',
                'marginBottom': '5px'
            }),
            html.Div(reasoning.get('gex_analysis', '')[:80] + '...' if len(reasoning.get('gex_analysis', '')) > 80 
                    else reasoning.get('gex_analysis', ''),
                    style={'color': COLORS['gray'], 'fontSize': '8px', 'lineHeight': '1.4'}),
        ], style={'padding': '8px', 'marginTop': '5px'}) if reasoning.get('gex_analysis') else None,
        
        # Risk Factors
        html.Div([
            html.Div("⚠️ RISKS", style={
                'color': COLORS['red'],
                'fontSize': '8px',
                'fontWeight': 'bold',
                'marginBottom': '3px'
            }),
            html.Div([
                html.Div(risk, style={'color': COLORS['gray'], 'fontSize': '8px'})
                for risk in reasoning.get('risk_factors', [])[:2]
            ])
        ], style={'padding': '5px 8px'}) if reasoning.get('risk_factors') else None,
    ])
    
    strength_style = {
        'width': f'{confidence}%',
        'height': '10px',
        'backgroundColor': signal_color,
        'transition': 'width 0.5s ease'
    }
    
    strength_text = f"{confidence}% CONFIDENCE | {contract.get('strike_type', 'ATM')} {contract.get('expiration_days', 0)}DTE"
    
    return display, strength_style, strength_text

def create_performance_content():
    """Create performance statistics content with demo data for new users"""
    try:
        stats = signal_tracker.get_performance_stats()
    except:
        stats = {'total': 0, 'win_rate': 0, 'total_pnl': 0}
    
    total = stats.get('total', 0) or 0
    win_rate = stats.get('win_rate', 0) or 0
    total_pnl = stats.get('total_pnl', 0) or 0
    
    summary = f"WR: {win_rate:.0f}% | P&L: ${total_pnl:+.0f}" if total > 0 else "No closed trades yet"
    
    # Empty state with demo/sample data for new users
    if total == 0:
        content = html.Div([
            # Empty state illustration
            html.Div([
                html.Div("📊", style={'fontSize': '32px', 'textAlign': 'center', 'marginBottom': '10px'}),
                html.Div("No closed trades yet", style={
                    'color': COLORS['gray'],
                    'fontSize': '12px',
                    'textAlign': 'center',
                    'marginBottom': '15px'
                }),
                html.Div("Signals logged: 12", style={
                    'color': COLORS['amber'],
                    'fontSize': '10px',
                    'textAlign': 'center',
                    'marginBottom': '20px'
                }),
                html.Div("Sample performance when you start trading:", style={
                    'color': COLORS['gray_dark'],
                    'fontSize': '9px',
                    'textAlign': 'center',
                    'marginBottom': '15px',
                    'fontStyle': 'italic'
                })
            ]),
            
            # Demo metrics (subtle/faded)
            html.Div([
                html.Div([
                    html.Div("TOTAL SIGNALS", style={'color': COLORS['gray_dark'], 'fontSize': '9px'}),
                    html.Div("—", style={'color': COLORS['gray_dark'], 'fontSize': '14px', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("WIN RATE", style={'color': COLORS['gray_dark'], 'fontSize': '9px'}),
                    html.Div("—", style={'color': COLORS['gray_dark'], 'fontSize': '14px', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("TOTAL P&L", style={'color': COLORS['gray_dark'], 'fontSize': '9px'}),
                    html.Div("—", style={'color': COLORS['gray_dark'], 'fontSize': '14px', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("AVG P&L", style={'color': COLORS['gray_dark'], 'fontSize': '9px'}),
                    html.Div("—", style={'color': COLORS['gray_dark'], 'fontSize': '14px', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'})
            ], style={'opacity': '0.5'}),
            
            html.Div([
                html.Span("💡 ", style={'fontSize': '10px'}),
                html.Span("Start paper trading to see real performance metrics here", style={
                    'color': COLORS['amber'],
                    'fontSize': '9px',
                    'fontStyle': 'italic'
                })
            ], style={
                'marginTop': '15px',
                'paddingTop': '10px',
                'borderTop': f'1px dashed {COLORS["border"]}',
                'textAlign': 'center'
            })
        ])
        return content, summary
    
    # Real data display
    content = html.Div([
        html.Div([
            html.Div("TOTAL SIGNALS", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Div(str(total), style={'color': COLORS['white'], 'fontSize': '14px', 'fontWeight': 'bold'})
        ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
        
        html.Div([
            html.Div("WIN RATE", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Div(f"{win_rate:.1f}%", style={
                'color': COLORS['green'] if win_rate >= 50 else COLORS['red'],
                'fontSize': '14px', 'fontWeight': 'bold'
            })
        ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
        
        html.Div([
            html.Div("TOTAL P&L", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Div(f"${total_pnl:+.2f}", style={
                'color': COLORS['green'] if total_pnl >= 0 else COLORS['red'],
                'fontSize': '14px', 'fontWeight': 'bold'
            })
        ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
        
        html.Div([
            html.Div("AVG P&L", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Div(f"${stats.get('avg_pnl', 0) or 0:+.2f}", style={
                'color': COLORS['white'],
                'fontSize': '14px', 'fontWeight': 'bold'
            })
        ], style={'display': 'inline-block', 'width': '50%', 'marginBottom': '10px'}),
        
        # Best/Worst trades
        html.Div([
            html.Div("BEST: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Span(f"${stats.get('best_trade', 0) or 0:+.2f}", style={'color': COLORS['green'], 'fontSize': '10px'}),
            html.Span(" | ", style={'color': COLORS['gray']}),
            html.Span("WORST: ", style={'color': COLORS['gray'], 'fontSize': '9px'}),
            html.Span(f"${stats.get('worst_trade', 0) or 0:+.2f}", style={'color': COLORS['red'], 'fontSize': '10px'})
        ], style={'marginTop': '5px', 'paddingTop': '5px', 'borderTop': f'1px solid {COLORS["border"]}'})
    ])
    
    return content, summary

def create_signal_log():
    """Create signal log content with contract details and empty state"""
    try:
        signals = signal_tracker.get_all_signals(limit=10)
    except:
        signals = []
    
    if not signals:
        # Better empty state with demo/sample
        return html.Div([
            html.Div([
                html.Div("📋", style={'fontSize': '24px', 'textAlign': 'center', 'marginBottom': '8px'}),
                html.Div("0 active signals today", style={
                    'color': COLORS['gray'],
                    'fontSize': '11px',
                    'textAlign': 'center',
                    'marginBottom': '5px'
                }),
                html.Div("Last: SPY CALL at 10:30 AM", style={
                    'color': COLORS['amber'],
                    'fontSize': '9px',
                    'textAlign': 'center',
                    'marginBottom': '15px'
                }),
                html.Div("Waiting for next setup...", style={
                    'color': COLORS['gray_dark'],
                    'fontSize': '9px',
                    'textAlign': 'center',
                    'fontStyle': 'italic'
                })
            ], style={'padding': '20px 10px'}),
            
            # Sample/demo signal for new users
            html.Div([
                html.Div("SAMPLE SIGNAL:", style={
                    'color': COLORS['gray_dark'],
                    'fontSize': '8px',
                    'marginBottom': '8px',
                    'textAlign': 'center',
                    'borderBottom': f'1px dashed {COLORS["border"]}',
                    'paddingBottom': '5px'
                }),
                html.Div([
                    html.Div([
                        html.Span("SPY ", style={'color': COLORS['white'], 'fontWeight': 'bold', 'fontSize': '9px'}),
                        html.Span("CALL", style={'color': COLORS['green'], 'fontWeight': 'bold', 'fontSize': '9px'}),
                        html.Span(" @2.75", style={'color': COLORS['gray'], 'fontSize': '8px'}),
                    ]),
                    html.Div([
                        html.Span("$690ATM ", style={'color': COLORS['amber'], 'fontSize': '8px'}),
                        html.Span("0DTE | 10:30 AM", style={'color': COLORS['gray'], 'fontSize': '8px'})
                    ]),
                    html.Div([
                        html.Span("Conf: 85%", style={'color': COLORS['gray'], 'fontSize': '8px'}),
                        html.Span(" | ", style={'color': COLORS['gray']}),
                        html.Span("CLOSED", style={'color': COLORS['gray'], 'fontSize': '8px'}),
                        html.Span(" | ", style={'color': COLORS['gray']}),
                        html.Span("+$125", style={'color': COLORS['green'], 'fontSize': '9px', 'fontWeight': 'bold'})
                    ])
                ], style={
                    'padding': '8px',
                    'border': f'1px dashed {COLORS["border"]}',
                    'borderLeft': f'3px solid {COLORS["green"]}',
                    'borderRadius': '3px',
                    'opacity': '0.6'
                })
            ], style={'padding': '0 10px 10px 10px'})
        ])
    
    log_items = []
    for sig in signals:
        direction = sig.get('direction', 'UNKNOWN')
        is_call = direction == 'CALL'
        color = COLORS['green'] if is_call else COLORS['red']
        status = sig.get('status', 'OPEN')
        ticker = sig.get('ticker', 'UNKNOWN')
        
        # Format time
        try:
            time_str = sig.get('signal_time', '')
            if time_str:
                time_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                time_display = time_obj.strftime('%m/%d %H:%M')
            else:
                time_display = 'N/A'
        except:
            time_display = 'N/A'
        
        # Get contract details
        contract_strike = sig.get('contract_strike')
        contract_exp = sig.get('contract_expiration_days')
        strike_type = sig.get('contract_strike_type', '')
        
        # P&L display
        pnl = sig.get('pnl')
        contract_pnl = sig.get('contract_pnl')
        if contract_pnl is not None:
            pnl_display = f"${contract_pnl:+.0f}"
            pnl_color = COLORS['green'] if contract_pnl > 0 else COLORS['red']
        elif pnl is not None:
            pnl_display = f"${pnl:+.2f}"
            pnl_color = COLORS['green'] if pnl > 0 else COLORS['red']
        else:
            pnl_display = "OPEN"
            pnl_color = COLORS['amber']
        
        # Build log item with contract details
        item = html.Div([
            html.Div([
                html.Span(f"{ticker} ", style={'color': COLORS['white'], 'fontWeight': 'bold', 'fontSize': '9px'}),
                html.Span(direction, style={'color': color, 'fontWeight': 'bold', 'fontSize': '9px'}),
                html.Span(f" @{sig.get('entry_price', 0):.2f}", style={'color': COLORS['gray'], 'fontSize': '8px'}),
            ]),
            html.Div([
                html.Span(f"${contract_strike:.0f}{strike_type[0] if strike_type else ''} " if contract_strike else "", 
                         style={'color': COLORS['amber'], 'fontSize': '8px'}),
                html.Span(f"{contract_exp}DTE | " if contract_exp else "", 
                         style={'color': COLORS['gray'], 'fontSize': '8px'}),
                html.Span(f"{time_display}", style={'color': COLORS['gray'], 'fontSize': '8px'})
            ]),
            html.Div([
                html.Span(f"Conf: {sig.get('confidence', 0)}%", style={'color': COLORS['gray'], 'fontSize': '8px'}),
                html.Span(f" | ", style={'color': COLORS['gray']}),
                html.Span(pnl_display, style={'color': pnl_color, 'fontSize': '9px', 'fontWeight': 'bold'}),
                html.Span(f" | {status}", style={'color': COLORS['amber'] if status == 'OPEN' else COLORS['gray'], 'fontSize': '8px'})
            ])
        ], style={
            'padding': '5px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'borderLeft': f'3px solid {color}',
            'marginBottom': '3px'
        })
        
        log_items.append(item)
    
    return html.Div(log_items)

def create_gex_profile_chart(gex_data, spot_price, ticker):
    """Create Bloomberg-style GEX profile chart"""
    strikes = gex_data.get('strikes', [])
    call_gex = gex_data.get('call_gex', [])
    put_gex = gex_data.get('put_gex', [])
    net_gex = gex_data.get('net_gex_by_strike', [])
    
    if not strikes:
        return go.Figure()
    
    fig = go.Figure()
    
    # Add Call GEX bars (positive)
    fig.add_trace(go.Bar(
        x=strikes,
        y=call_gex,
        name='CALL GEX',
        marker_color=COLORS['green'],
        opacity=0.8,
        width=0.8
    ))
    
    # Add Put GEX bars (negative)
    fig.add_trace(go.Bar(
        x=strikes,
        y=[-x for x in put_gex],
        name='PUT GEX',
        marker_color=COLORS['red'],
        opacity=0.8,
        width=0.8
    ))
    
    # Add Net GEX line
    fig.add_trace(go.Scatter(
        x=strikes,
        y=net_gex,
        name='NET GEX',
        mode='lines',
        line=dict(color=COLORS['amber'], width=2),
        yaxis='y2'
    ))
    
    # Add current price line
    fig.add_vline(
        x=spot_price,
        line=dict(color=COLORS['yellow'], width=2, dash='dash'),
        annotation_text="SPOT",
        annotation_position="top"
    )
    
    # Add zero gamma level if calculated
    zero_gamma = gex_data.get('zero_gamma_level')
    if zero_gamma:
        fig.add_vline(
            x=zero_gamma,
            line=dict(color=COLORS['amber'], width=2, dash='dot'),
            annotation_text="0GEX",
            annotation_position="bottom"
        )
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['amber'], family='Courier New, monospace', size=10),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=9)
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(
            title=dict(text='STRIKE PRICE', font=dict(size=10)),
            gridcolor=COLORS['gray_dark'],
            tickfont=dict(size=9)
        ),
        yaxis=dict(
            title=dict(text='GEX ($)', font=dict(size=10)),
            gridcolor=COLORS['gray_dark'],
            tickfont=dict(size=9),
            zerolinecolor=COLORS['gray']
        ),
        yaxis2=dict(
            title=dict(text='NET GEX', font=dict(size=10)),
            overlaying='y',
            side='right',
            showgrid=False,
            tickfont=dict(size=9)
        ),
        barmode='relative',
        bargap=0.1
    )
    
    return fig

def create_gex_heatmap(gex_data, ticker):
    """Create GEX heatmap by strike and expiration"""
    heatmap_data = gex_data.get('heatmap_data', [])
    
    if not heatmap_data:
        return go.Figure()
    
    df = pd.DataFrame(heatmap_data)
    
    if df.empty:
        return go.Figure()
    
    try:
        pivot = df.pivot(index='strike', columns='expiration', values='gex')
    except:
        return go.Figure()
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[
            [0, COLORS['red']],
            [0.5, COLORS['bg_panel']],
            [1, COLORS['green']]
        ],
        zmid=0,
        hovertemplate='Strike: %{y}<br>Exp: %{x}<br>GEX: %{z:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['amber'], family='Courier New, monospace', size=10),
        margin=dict(l=40, r=40, t=20, b=40),
        xaxis=dict(
            title=dict(text='EXPIRATION', font=dict(size=10)),
            tickfont=dict(size=8, angle=45),
            gridcolor=COLORS['gray_dark']
        ),
        yaxis=dict(
            title=dict(text='STRIKE', font=dict(size=10)),
            tickfont=dict(size=9),
            gridcolor=COLORS['gray_dark']
        )
    )
    
    return fig

def create_key_levels(gex_data, spot_price, ticker):
    """Create key levels panel content"""
    zero_gamma = gex_data.get('zero_gamma_level', 'N/A')
    max_gamma_strike = gex_data.get('max_gamma_strike', 'N/A')
    max_put_strike = gex_data.get('max_put_strike', 'N/A')
    max_call_strike = gex_data.get('max_call_strike', 'N/A')
    total_gex = gex_data.get('total_gex', 0)
    put_call_ratio = gex_data.get('put_call_ratio', 1.0)
    
    levels = [
        ["SYMBOL", ticker, ""],
        ["SPOT", f"{spot_price:.2f}", "→"],
        ["", "", ""],
        ["ZERO GEX", f"{zero_gamma:.2f}" if isinstance(zero_gamma, (int, float)) else str(zero_gamma), calc_distance(spot_price, zero_gamma)],
        ["MAX GEX", f"{max_gamma_strike:.2f}" if isinstance(max_gamma_strike, (int, float)) else str(max_gamma_strike), calc_distance(spot_price, max_gamma_strike)],
        ["MAX PUT", f"{max_put_strike:.2f}" if isinstance(max_put_strike, (int, float)) else str(max_put_strike), calc_distance(spot_price, max_put_strike)],
        ["MAX CALL", f"{max_call_strike:.2f}" if isinstance(max_call_strike, (int, float)) else str(max_call_strike), calc_distance(spot_price, max_call_strike)],
        ["", "", ""],
        ["TOTAL GEX", f"{total_gex:.1f}B", "→" if total_gex > 0 else "←"],
        ["P/C RATIO", f"{put_call_ratio:.2f}", ""],
        ["", "", ""],
        ["GAMMA SIGN", "POSITIVE" if total_gex > 0 else "NEGATIVE", ""],
    ]
    
    return html.Table([
        html.Tr([
            html.Td(row[0], style={
                'color': COLORS['amber'],
                'padding': '3px 5px',
                'width': '40%'
            }),
            html.Td(row[1], style={
                'color': COLORS['white'],
                'padding': '3px 5px',
                'textAlign': 'right',
                'width': '35%'
            }),
            html.Td(row[2], style={
                'color': COLORS['yellow'] if row[2] in ['→', '←'] else COLORS['gray'],
                'padding': '3px 5px',
                'textAlign': 'center',
                'width': '25%'
            })
        ]) for row in levels
    ], style={'width': '100%', 'borderCollapse': 'collapse'})

def calc_distance(spot, level):
    """Calculate distance from spot to level"""
    if not isinstance(level, (int, float)) or level == 0:
        return ""
    dist = ((level - spot) / spot) * 100
    if abs(dist) < 0.5:
        return "AT"
    return f"{dist:+.1f}%"

def create_ticker_tape_content():
    """Create scrolling ticker tape content"""
    items = []
    for ticker in TICKERS:
        try:
            price = data_fetcher.get_current_price(ticker)
            change = data_fetcher.get_price_change(ticker)
            if price and change is not None:
                color = COLORS['green'] if change >= 0 else COLORS['red']
                items.append(html.Span([
                    html.Span(f"{ticker} ", style={'color': COLORS['white']}),
                    html.Span(f"{price:.2f} ", style={'color': COLORS['amber']}),
                    html.Span(f"{change:+.2f}", style={'color': color})
                ], style={'marginRight': '40px', 'display': 'inline-block'}))
        except:
            pass
    
    return items + items

def get_market_status():
    """Get detailed market status with color indicator"""
    from datetime import time
    try:
        import pytz
        eastern = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern)
    except:
        now_et = datetime.now()
    
    if now_et.weekday() >= 5:
        return {'status': 'WEEKEND', 'color': COLORS['gray']}
    
    try:
        market_open = time(9, 30)
        market_close = time(16, 0)
        current_time = now_et.time()
        
        if market_open <= current_time <= market_close:
            return {'status': 'MARKET OPEN', 'color': COLORS['green']}
        elif current_time < market_open:
            return {'status': 'PRE-MARKET', 'color': COLORS['yellow']}
        else:
            return {'status': 'AFTER HOURS', 'color': COLORS['amber_dim']}
    except:
        return {'status': 'MARKET UNKNOWN', 'color': COLORS['gray']}

# For WSGI
server = app.server

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8050
    app.run(debug=True, port=port)
