# GEX Terminal Dashboard

A Bloomberg Terminal-style Gamma Exposure (GEX) visualization dashboard for professional traders.

![GEX Terminal](assets/preview.png)

## Features

### Core Functionality
- **Real-time GEX Profile**: Visualize gamma exposure across strike prices
- **GEX Heatmap**: View gamma exposure by strike and expiration
- **Zero Gamma Level**: Identify the flip point between positive/negative gamma
- **Multi-ticker Support**: SPY, QQQ, NVDA, TSLA, AMD, AAPL, MSFT, AMZN, META, GOOGL
- **Live Price Integration**: Current price relative to key gamma levels
- **Auto-refresh**: Updates every 60 seconds during market hours

### Bloomberg Terminal Style
- **Signature Colors**: Amber (#FF6600) on dark background (#1a1a1a)
- **Command Interface**: "GEX <GO>" style command bar
- **F-Key Navigation**: Quick access to functions (F1-F12)
- **Ticker Tape**: Scrolling live prices at bottom
- **Multi-panel Layout**: Quadrant view showing different data simultaneously
- **Monospace Fonts**: Courier New for authentic terminal feel

### Trading Features
- **Gamma Squeeze Alerts**: Flashing warnings when near zero gamma
- **Key Levels Panel**: Zero gamma, max gamma strikes, put/call ratios
- **Visual Indicators**: Green/red for calls/puts, yellow highlights
- **Pin Risk Detection**: High GEX exposure warnings

## Installation

```bash
# Install dependencies
pip3 install -r requirements.txt

# Or manually
pip3 install dash plotly yfinance pandas numpy scipy
```

## Usage

```bash
# Start the dashboard
python3 app.py

# Open in browser
http://localhost:8050
```

## Commands

Type in the command bar and press GO:

| Command | Description |
|---------|-------------|
| `SPY` | Load SPY data |
| `GEX QQQ` | Show GEX profile for QQQ |
| `HEATMAP` | Toggle heatmap view |
| `PROFILE` | Show GEX profile chart |
| `ALERTS` | View gamma squeeze alerts |
| `EXPORT` | Export data to CSV |
| `REFRESH` | Force data refresh |
| `HELP` | Show command reference |

## Keyboard Shortcuts

- **F1**: Help
- **F2**: GEX Profile
- **F3**: Heatmap
- **F4**: Profile
- **F5**: Alerts
- **F6**: Export
- **F9-F12**: Quick ticker select

## Data Sources

- **Real-time prices**: Yahoo Finance (yfinance)
- **Options data**: Yahoo Finance options chains
- **Fallback**: Realistic simulated data if API unavailable

## Architecture

```
trading/dashboard/
├── app.py              # Main Dash application
├── gex_calculator.py   # GEX calculation engine
├── data_fetcher.py     # Market data fetching
├── layouts.py          # UI component library
├── assets/
│   └── style.css       # Bloomberg terminal styling
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## GEX Calculation

Gamma Exposure (GEX) represents the total gamma of all options contracts:

```
GEX = Gamma × Open Interest × 100 × Spot Price
```

- **Positive GEX**: Dealers are long gamma → Mean reversion, price pinning
- **Negative GEX**: Dealers are short gamma → Trending moves, breakouts accelerate
- **Zero Gamma**: The flip point where exposure changes sign

## Alerts

The dashboard monitors for:
1. **Gamma Flip Imminent**: Price within 1% of zero gamma level
2. **Near Zero Gamma**: Price within 2% of flip point
3. **High GEX**: Total exposure > $10B (pin risk)

## Customization

### Adding Tickers
Edit `TICKERS` list in `app.py`:

```python
TICKERS = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL']
```

### Color Scheme
Edit colors in `app.py`:

```python
COLORS = {
    'bg': '#0d0d0d',
    'amber': '#FF6600',
    'green': '#00FF00',
    'red': '#FF0000',
    # ...
}
```

### Refresh Interval
Change interval in `app.py`:

```python
dcc.Interval(id='interval-component', interval=60000, n_intervals=0)  # milliseconds
```

## API Rate Limits

The dashboard uses yfinance which has rate limits. For production use:
- Consider adding API key for premium data
- Implement caching (Redis/SQLite)
- Add retry logic with exponential backoff

## License

MIT License - Feel free to use and modify for your trading needs.

---

**Built for professional traders who want Bloomberg-style GEX analysis without the $24,000/year subscription.**