# Google Sheets Trading Logger

Direct API integration for logging trades from the trading system to Google Sheets. No CLI dependencies.

## Setup

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Click **Create Service Account**
4. Grant roles:
   - Google Sheets API → **Editor**
   - Google Drive API → **Editor**
5. Create a **JSON key** and download it
6. Move the key file to:
   ```
   ~/.openclaw/workspace/trading/google-credentials.json
   ```

### 2. Install Dependencies

```bash
cd ~/.openclaw/workspace/trading
pip install -r requirements-sheets.txt
```

### 3. Test the Connection

```bash
python google_sheets_logger.py
```

Expected output on first run:
```
✅ Authenticated with Google Sheets
✅ Created new sheet: Trading Log
✅ Sheet structure initialized
✅ Trade logged: TEST-001

✅ Test complete!
```

## Usage

### Basic Logging

```python
from google_sheets_logger import TradingSheetLogger

logger = TradingSheetLogger()
logger.authenticate()
logger.get_or_create_sheet()

# Log a trade
logger.log_trade({
    'trade_id': 'BTC-001',
    'symbol': 'BTC/USD',
    'side': 'BUY',
    'entry_price': 45000.00,
    'exit_price': 46000.00,
    'quantity': 0.1,
    'pnl_usd': 100.00,
    'pnl_pct': 2.22,
    'strategy': 'momentum',
    'status': 'closed',
    'notes': 'Breakout confirmed'
})
```

### Environment Variable

Set custom credentials path:
```bash
export GOOGLE_SHEETS_CREDENTIALS="/path/to/your/credentials.json"
```

## Sheet Structure

The logger creates a sheet with these columns:
| Column | Description |
|--------|-------------|
| Timestamp | ISO format datetime |
| Trade ID | Unique identifier |
| Symbol | Trading pair (e.g., BTC/USD) |
| Side | BUY or SELL |
| Entry Price | Entry price |
| Exit Price | Exit price |
| Quantity | Position size |
| PnL ($) | Profit/Loss in USD |
| PnL (%) | Profit/Loss percentage |
| Strategy | Strategy used |
| Status | open/closed/pending |
| Notes | Additional notes |

## Integration with Trading System

```python
from cryptocom_trader import CryptoTrader
from google_sheets_logger import TradingSheetLogger

# Initialize both
trader = CryptoTrader()
logger = TradingSheetLogger()
logger.authenticate()
logger.get_or_create_sheet()

# After a trade executes
trade_result = trader.execute_signal(signal)
logger.log_trade(trade_result)
```

## Local Test Mode

Run without credentials for development:
```bash
python test_sheets_local.py
```
