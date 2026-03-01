"""
Terminal Layouts Module
UI component definitions for Bloomberg Terminal style
"""

from dash import html, dcc

class TerminalLayouts:
    """Define UI layouts and components"""
    
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
    }
    
    def create_bloomberg_table(self, headers, rows, id=None):
        """Create a Bloomberg-style data table"""
        return html.Table([
            html.Thead([
                html.Tr([
                    html.Th(
                        h,
                        style={
                            'color': self.COLORS['amber'],
                            'borderBottom': f'2px solid {self.COLORS["amber"]}',
                            'padding': '5px 8px',
                            'textAlign': 'left',
                            'fontSize': '11px',
                            'fontFamily': 'Courier New, monospace'
                        }
                    ) for h in headers
                ])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td(
                        cell,
                        style={
                            'color': self.COLORS['white'] if j == 0 else self.COLORS['gray'],
                            'borderBottom': f'1px solid {self.COLORS["border"]}',
                            'padding': '4px 8px',
                            'fontSize': '11px',
                            'fontFamily': 'Courier New, monospace',
                            'textAlign': 'left' if j == 0 else 'right'
                        }
                    ) for j, cell in enumerate(row)
                ]) for row in rows
            ])
        ], id=id, style={
            'width': '100%',
            'borderCollapse': 'collapse'
        })
    
    def create_panel_header(self, title, subtitle=None, actions=None):
        """Create a panel header with title and optional actions"""
        children = [
            html.Span(
                title,
                style={
                    'color': self.COLORS['amber'],
                    'fontSize': '12px',
                    'fontWeight': 'bold'
                }
            )
        ]
        
        if subtitle:
            children.append(html.Span(
                f" | {subtitle}",
                style={
                    'color': self.COLORS['gray'],
                    'fontSize': '10px'
                }
            ))
        
        if actions:
            children.append(html.Div(
                actions,
                style={'marginLeft': 'auto', 'display': 'flex'}
            ))
        
        return html.Div(
            children,
            style={
                'padding': '5px 10px',
                'borderBottom': f'1px solid {self.COLORS["border"]}',
                'display': 'flex',
                'alignItems': 'center',
                'fontFamily': 'Courier New, monospace'
            }
        )
    
    def create_alert_box(self, message, level='info', timestamp=None):
        """Create an alert box"""
        colors = {
            'critical': self.COLORS['red'],
            'warning': self.COLORS['amber'],
            'info': self.COLORS['yellow'],
            'success': self.COLORS['green']
        }
        
        color = colors.get(level, self.COLORS['gray'])
        
        content = [
            html.Span(
                "■ ",
                style={'color': color}
            ),
            html.Span(
                message,
                style={'color': self.COLORS['white']}
            )
        ]
        
        if timestamp:
            content.append(html.Br())
            content.append(html.Span(
                timestamp,
                style={
                    'color': self.COLORS['gray'],
                    'fontSize': '9px'
                }
            ))
        
        return html.Div(
            content,
            style={
                'padding': '6px 8px',
                'marginBottom': '4px',
                'borderLeft': f'3px solid {color}',
                'backgroundColor': self.COLORS['bg_panel'],
                'fontFamily': 'Courier New, monospace',
                'fontSize': '10px'
            }
        )
    
    def create_metric_card(self, label, value, change=None, unit=None):
        """Create a metric display card"""
        value_color = self.COLORS['white']
        if change is not None:
            value_color = self.COLORS['green'] if change >= 0 else self.COLORS['red']
        
        return html.Div([
            html.Div(
                label,
                style={
                    'color': self.COLORS['gray'],
                    'fontSize': '10px',
                    'marginBottom': '2px'
                }
            ),
            html.Div([
                html.Span(
                    f"{value}{unit if unit else ''}",
                    style={
                        'color': value_color,
                        'fontSize': '16px',
                        'fontWeight': 'bold'
                    }
                ),
                html.Span(
                    f" ({change:+.2f})" if change is not None else "",
                    style={
                        'color': self.COLORS['green'] if change and change >= 0 else self.COLORS['red'],
                        'fontSize': '11px',
                        'marginLeft': '8px'
                    }
                ) if change is not None else None
            ])
        ], style={
            'padding': '8px',
            'backgroundColor': self.COLORS['bg_panel'],
            'border': f'1px solid {self.COLORS["border"]}',
            'fontFamily': 'Courier New, monospace'
        })
    
    def create_command_reference(self):
        """Create command reference panel"""
        commands = [
            ("<TICKER>", "Load ticker data (e.g., SPY)"),
            ("GEX <T>", "Show GEX profile for ticker T"),
            ("HEATMAP", "Toggle GEX heatmap view"),
            ("PROFILE", "Show GEX strike profile"),
            ("FLIP", "Show gamma flip analysis"),
            ("ALERTS", "View active alerts"),
            ("EXPORT", "Export data to CSV"),
            ("REFRESH", "Force data refresh"),
            ("CLEAR", "Clear command history"),
            ("HELP", "Show this help")
        ]
        
        return html.Div([
            html.Div(
                "QUICK REFERENCE",
                style={
                    'color': self.COLORS['amber'],
                    'padding': '8px',
                    'borderBottom': f'1px solid {self.COLORS["border"]}',
                    'fontSize': '11px',
                    'fontWeight': 'bold',
                    'fontFamily': 'Courier New, monospace'
                }
            ),
            html.Div([
                html.Div([
                    html.Span(
                        cmd[0],
                        style={
                            'color': self.COLORS['amber'],
                            'display': 'inline-block',
                            'width': '100px'
                        }
                    ),
                    html.Span(
                        cmd[1],
                        style={'color': self.COLORS['gray']}
                    )
                ], style={
                    'padding': '4px 8px',
                    'borderBottom': f'1px solid {self.COLORS["border"]}',
                    'fontSize': '10px',
                    'fontFamily': 'Courier New, monospace'
                })
                for cmd in commands
            ])
        ], style={
            'backgroundColor': self.COLORS['bg_panel_alt'],
            'border': f'1px solid {self.COLORS["border"]}'
        })
    
    def create_status_indicator(self, label, status, value=None):
        """Create a status indicator light"""
        status_colors = {
            'ok': self.COLORS['green'],
            'warning': self.COLORS['amber'],
            'error': self.COLORS['red'],
            'info': self.COLORS['yellow']
        }
        
        color = status_colors.get(status, self.COLORS['gray'])
        
        return html.Div([
            html.Span(
                "●",
                style={
                    'color': color,
                    'marginRight': '8px'
                }
            ),
            html.Span(
                label,
                style={
                    'color': self.COLORS['white'],
                    'marginRight': '8px'
                }
            ),
            html.Span(
                value if value else "",
                style={'color': self.COLORS['gray']}
            )
        ], style={
            'padding': '4px 8px',
            'fontSize': '11px',
            'fontFamily': 'Courier New, monospace'
        })