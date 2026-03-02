"""
PATCH FILE for GEX Terminal - Production Fixes
Apply these changes to fix symbol switching, Polygon integration, and signal display
"""

# FIX 1: Add callback for sidebar ticker highlighting
# Add this callback after the main update_dashboard callback in app.py

SIDEBAR_TICKER_CALLBACK = '''
# Callback to update sidebar ticker highlighting when symbol changes
@app.callback(
    *[Output(f'sidebar-{ticker}', 'style') for ticker in TICKERS],
    *[Output(f'sidebar-{ticker}', 'children') for ticker in TICKERS],
    Input('current-ticker-store', 'data')
)
def update_sidebar_highlighting(current_ticker):
    """Update sidebar styling to highlight active ticker"""
    styles = []
    children = []
    
    for ticker in TICKERS:
        is_active = ticker == current_ticker
        
        # Style for ticker row
        style = {
            'padding': '8px 10px',
            'borderBottom': f'1px solid {COLORS["border"]}',
            'cursor': 'pointer',
            'display': 'flex',
            'justifyContent': 'space-between',
            'backgroundColor': COLORS['bg_panel_alt'] if is_active else 'transparent'
        }
        styles.append(style)
        
        # Children for ticker row
        child = html.Div([
            html.Span(ticker, style={
                'color': COLORS['amber'] if is_active else COLORS['white'],
                'fontWeight': 'bold' if is_active else 'normal',
                'fontSize': '12px'
            }),
            html.Div(id=f'price-{ticker}', style={'color': COLORS['gray'], 'fontSize': '10px'})
        ])
        children.append(child)
    
    return styles + children
'''

# FIX 2: Ensure Polygon API is used in data_fetcher.py
# Make sure the Polygon API is the primary data source

POLYGON_PRIORITY_FIX = '''
# In data_fetcher.py, ensure Polygon is tried first:

def get_current_price(self, ticker):
    """Get current price - prioritize Polygon for real-time data"""
    # Try Polygon first for real-time data
    if self.polygon_client and self.api_priority == 'polygon':
        try:
            last_trade = self.polygon_client.get_last_trade(ticker)
            if last_trade and last_trade.price:
                print(f"[POLYGON] {ticker} price: ${last_trade.price:.2f}")
                return float(last_trade.price)
        except Exception as e:
            print(f"[POLYGON] Price fetch failed for {ticker}: {e}")
    
    # Fallback to other sources...
'''

# FIX 3: Enhanced signal display with contract details
# Replace the create_signal_display function

ENHANCED_SIGNAL_DISPLAY = '''
def create_signal_display(signal, gex_data, spot_price):
    """Create production-grade signal display with contract details"""
    if not signal:
        return html.Div("NO ACTIVE SIGNAL", style={
            'color': COLORS['gray'],
            'textAlign': 'center',
            'padding': '20px'
        }), {'width': '0%', 'height': '10px', 'backgroundColor': COLORS['gray']}, "NO SIGNAL"
    
    # Extract signal info
    direction = getattr(signal, 'direction', signal.get('direction', 'NEUTRAL'))
    confidence = getattr(signal, 'confidence', signal.get('confidence', 50))
    entry_price = getattr(signal, 'entry_price', signal.get('entry_price', spot_price))
    
    # Calculate contract details
    if direction in ['BUY CALL', 'CALL']:
        signal_color = COLORS['green']
        bg_color = '#0d2d0d'
        text_color = COLORS['green']
        option_type = 'CALL'
        # Find call strike near 30-40 delta (slightly OTM)
        strike_offset = 0.02  # 2% OTM for calls
    elif direction in ['BUY PUT', 'PUT']:
        signal_color = COLORS['red']
        bg_color = '#2d0d0d'
        text_color = COLORS['red']
        option_type = 'PUT'
        # Find put strike near 30-40 delta (slightly OTM)
        strike_offset = -0.02  # 2% OTM for puts
    else:
        signal_color = COLORS['amber']
        bg_color = COLORS['bg_panel']
        text_color = COLORS['amber']
        option_type = 'NONE'
        strike_offset = 0
    
    # Calculate optimal contract
    if spot_price and strike_offset != 0:
        target_strike = spot_price * (1 + strike_offset)
        # Round to nearest standard strike
        if spot_price > 200:
            strike = round(target_strike / 5) * 5  # $5 increments for high-priced
        elif spot_price > 50:
            strike = round(target_strike / 2.5) * 2.5  # $2.50 increments
        else:
            strike = round(target_strike / 1) * 1  # $1 increments
    else:
        strike = spot_price
    
    # Find expiration 30-45 DTE
    from datetime import datetime, timedelta
    expiry = datetime.now() + timedelta(days=35)
    expiry_str = expiry.strftime("%b %d '%y")  # e.g., "Mar 15 '25"
    
    # Calculate stop/target
    stop_loss = entry_price * 0.95 if entry_price else spot_price * 0.95
    take_profit = entry_price * 1.10 if entry_price else spot_price * 1.10
    
    # Signal strength bar
    strength_pct = min(confidence, 100)
    strength_style = {
        'width': f'{strength_pct}%',
        'height': '10px',
        'backgroundColor': signal_color,
        'transition': 'width 0.5s ease'
    }
    strength_text = f"CONFIDENCE: {confidence}%"
    
    # Get signal reasoning
    reasoning = []
    if hasattr(signal, 'reasoning') and signal.reasoning:
        reasoning = signal.reasoning
    elif isinstance(signal, dict) and 'reasoning' in signal:
        reasoning = signal['reasoning']
    
    if not reasoning:
        # Generate reasoning from GEX data
        zero_gamma = gex_data.get('zero_gamma', spot_price)
        total_gex = gex_data.get('total_gex', 0)
        
        if direction in ['BUY CALL', 'CALL']:
            if spot_price > zero_gamma:
                reasoning.append("Price above Zero Gamma (bullish)")
            if total_gex > 0:
                reasoning.append("Positive GEX (dealer long, supports rallies)")
        elif direction in ['BUY PUT', 'PUT']:
            if spot_price < zero_gamma:
                reasoning.append("Price below Zero Gamma (bearish)")
            if total_gex < 0:
                reasoning.append("Negative GEX (dealer short, accelerates drops)")
    
    # Build display
    display = html.Div([
        # Signal Banner
        html.Div([
            html.Div(f"🎯 {direction}", style={
                'fontSize': '24px',
                'fontWeight': 'bold',
                'color': text_color,
                'textAlign': 'center',
                'padding': '15px',
                'backgroundColor': bg_color,
                'border': f'2px solid {signal_color}',
                'borderRadius': '5px',
                'marginBottom': '15px'
            }),
            
            # Contract Details
            html.Div([
                html.Div("OPTIONS CONTRACT", style={
                    'color': COLORS['amber'],
                    'fontSize': '10px',
                    'marginBottom': '5px',
                    'fontWeight': 'bold'
                }),
                html.Div([
                    html.Span(f"Strike: ${strike:.2f}", style={'color': COLORS['white'], 'marginRight': '15px'}),
                    html.Span(f"Expiry: {expiry_str}", style={'color': COLORS['white'], 'marginRight': '15px'}),
                    html.Span(f"Type: {option_type}", style={'color': text_color, 'fontWeight': 'bold'})
                ], style={'fontSize': '14px', 'marginBottom': '10px'}),
                html.Div(f"Delta Target: ~0.30-0.35 | DTE: 30-45", style={
                    'color': COLORS['gray'],
                    'fontSize': '9px'
                })
            ], style={
                'padding': '10px',
                'backgroundColor': COLORS['bg_panel_alt'],
                'borderLeft': f'3px solid {signal_color}',
                'marginBottom': '15px'
            }),
            
            # Entry/Stop/Target
            html.Div([
                html.Div("TRADE LEVELS", style={
                    'color': COLORS['amber'],
                    'fontSize': '10px',
                    'marginBottom': '5px',
                    'fontWeight': 'bold'
                }),
                html.Div([
                    html.Div([
                        html.Span("ENTRY: ", style={'color': COLORS['gray']}),
                        html.Span(f"${entry_price:.2f}" if entry_price else "MARKET", style={'color': COLORS['white']})
                    ], style={'marginBottom': '5px'}),
                    html.Div([
                        html.Span("STOP: ", style={'color': COLORS['gray']}),
                        html.Span(f"${stop_loss:.2f} (-5%)", style={'color': COLORS['red']})
                    ], style={'marginBottom': '5px'}),
                    html.Div([
                        html.Span("TARGET: ", style={'color': COLORS['gray']}),
                        html.Span(f"${take_profit:.2f} (+10%)", style={'color': COLORS['green']})
                    ])
                ], style={'fontSize': '12px', 'fontFamily': 'Courier New, monospace'})
            ], style={
                'padding': '10px',
                'backgroundColor': COLORS['bg_panel_alt'],
                'borderLeft': f'3px solid {COLORS['amber']}',
                'marginBottom': '15px'
            }),
            
            # Signal Reasoning
            html.Div([
                html.Div("📊 SIGNAL REASONING", style={
                    'color': COLORS['amber'],
                    'fontSize': '10px',
                    'marginBottom': '5px',
                    'fontWeight': 'bold'
                }),
                html.Ul([html.Li(r, style={'color': COLORS['white'], 'fontSize': '11px', 'marginBottom': '3px'}) for r in reasoning],
                       style={'marginLeft': '15px'})
            ], style={
                'padding': '10px',
                'backgroundColor': COLORS['bg_panel_alt'],
                'borderLeft': f'3px solid {COLORS['yellow']}',
                'marginBottom': '15px'
            })
        ])
    ])
    
    return display, strength_style, strength_text
'''

print("="*70)
print("GEX TERMINAL PRODUCTION FIXES")
print("="*70)
print("\n1. SIDEBAR HIGHLIGHTING CALLBACK:")
print(SIDEBAR_TICKER_CALLBACK)
print("\n2. POLYGON PRIORITY FIX:")
print(POLYGON_PRIORITY_FIX)
print("\n3. ENHANCED SIGNAL DISPLAY:")
print(ENHANCED_SIGNAL_DISPLAY[:500] + "...")
