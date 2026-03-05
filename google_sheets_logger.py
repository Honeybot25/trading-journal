"""
Google Sheets Trading Logger
Direct API integration using gspread (no gws CLI needed)
"""
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict, List, Optional

# Google Sheets API scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class TradingSheetLogger:
    """Log trading activity to Google Sheets."""
    
    def __init__(self, credentials_path: str = None, sheet_name: str = "Trading Log"):
        """
        Initialize the trading logger.
        
        Args:
            credentials_path: Path to service account JSON file
            sheet_name: Name of the Google Sheet to create/use
        """
        self.credentials_path = credentials_path or os.getenv(
            'GOOGLE_SHEETS_CREDENTIALS', 
            '~/.openclaw/workspace/trading/google-credentials.json'
        )
        self.sheet_name = sheet_name
        self.client = None
        self.sheet = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API using service account.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Expand path if it contains ~
            creds_path = os.path.expanduser(self.credentials_path)
            
            if not os.path.exists(creds_path):
                print(f"❌ Credentials file not found: {creds_path}")
                print("📋 To set up:")
                print("1. Go to Google Cloud Console → IAM & Admin → Service Accounts")
                print("2. Create service account with Google Sheets + Drive access")
                print("3. Download JSON key file")
                print(f"4. Save to: {creds_path}")
                return False
            
            # Load credentials
            creds = Credentials.from_service_account_file(
                creds_path,
                scopes=SCOPES
            )
            
            # Authenticate with gspread
            self.client = gspread.authorize(creds)
            print(f"✅ Authenticated with Google Sheets")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_or_create_sheet(self) -> Optional[gspread.Spreadsheet]:
        """
        Get existing sheet or create new one.
        
        Returns:
            gspread Spreadsheet object or None if failed
        """
        if not self.client:
            print("❌ Not authenticated. Call authenticate() first.")
            return None
        
        try:
            # Try to open existing sheet
            try:
                self.sheet = self.client.open(self.sheet_name)
                print(f"✅ Connected to existing sheet: {self.sheet_name}")
                return self.sheet
            except gspread.SpreadsheetNotFound:
                # Create new sheet
                self.sheet = self.client.create(self.sheet_name)
                print(f"✅ Created new sheet: {self.sheet_name}")
                
                # Setup initial structure
                self._setup_sheet_structure()
                return self.sheet
                
        except Exception as e:
            print(f"❌ Sheet error: {e}")
            return None
    
    def _setup_sheet_structure(self):
        """Setup the initial sheet structure with headers."""
        worksheet = self.sheet.sheet1
        worksheet.title = "Trades"
        
        # Define headers
        headers = [
            "Timestamp",
            "Trade ID",
            "Symbol",
            "Side",
            "Entry Price",
            "Exit Price",
            "Quantity",
            "PnL ($)",
            "PnL (%)",
            "Strategy",
            "Status",
            "Notes"
        ]
        
        # Add headers
        worksheet.append_row(headers)
        
        # Format headers (bold)
        worksheet.format('A1:L1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # Freeze header row
        worksheet.freeze_rows(1)
        
        print("✅ Sheet structure initialized")
    
    def log_trade(self, trade_data: Dict) -> bool:
        """
        Log a single trade to the sheet.
        
        Args:
            trade_data: Dictionary with trade information
            
        Returns:
            True if logged successfully, False otherwise
        """
        if not self.sheet:
            print("❌ No sheet connected. Call get_or_create_sheet() first.")
            return False
        
        try:
            worksheet = self.sheet.sheet1
            
            # Prepare row data
            row = [
                trade_data.get('timestamp', datetime.now().isoformat()),
                trade_data.get('trade_id', 'N/A'),
                trade_data.get('symbol', 'N/A'),
                trade_data.get('side', 'N/A'),
                trade_data.get('entry_price', 0),
                trade_data.get('exit_price', 0),
                trade_data.get('quantity', 0),
                trade_data.get('pnl_usd', 0),
                trade_data.get('pnl_pct', 0),
                trade_data.get('strategy', 'N/A'),
                trade_data.get('status', 'N/A'),
                trade_data.get('notes', '')
            ]
            
            worksheet.append_row(row)
            print(f"✅ Trade logged: {trade_data.get('trade_id', 'N/A')}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to log trade: {e}")
            return False
    
    def log_trades(self, trades: List[Dict]) -> int:
        """
        Log multiple trades at once.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Number of trades successfully logged
        """
        success_count = 0
        for trade in trades:
            if self.log_trade(trade):
                success_count += 1
        return success_count
    
    def get_all_trades(self) -> List[Dict]:
        """
        Retrieve all trades from the sheet.
        
        Returns:
            List of trade dictionaries
        """
        if not self.sheet:
            print("❌ No sheet connected")
            return []
        
        try:
            worksheet = self.sheet.sheet1
            records = worksheet.get_all_records()
            return records
        except Exception as e:
            print(f"❌ Failed to retrieve trades: {e}")
            return []


# Example usage / test function
def test_logger():
    """Test the trading logger."""
    logger = TradingSheetLogger()
    
    # Authenticate
    if not logger.authenticate():
        print("❌ Authentication failed")
        return
    
    # Get or create sheet
    if not logger.get_or_create_sheet():
        print("❌ Sheet connection failed")
        return
    
    # Test log a trade
    test_trade = {
        'trade_id': 'TEST-001',
        'symbol': 'BTC/USD',
        'side': 'BUY',
        'entry_price': 45000.00,
        'exit_price': 46000.00,
        'quantity': 0.1,
        'pnl_usd': 100.00,
        'pnl_pct': 2.22,
        'strategy': 'momentum',
        'status': 'closed',
        'notes': 'Test trade for system validation'
    }
    
    logger.log_trade(test_trade)
    print("\n✅ Test complete!")


if __name__ == "__main__":
    test_logger()
