"""
Export Utility for GEX Terminal
Export data to CSV and Excel formats
"""

import pandas as pd
import json
from datetime import datetime
import os

class GEXExporter:
    """Export GEX data to various formats"""
    
    def __init__(self, export_dir='exports'):
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)
    
    def export_gex_profile(self, gex_data, ticker, format='csv'):
        """
        Export GEX profile data
        
        Args:
            gex_data: GEX calculation results
            ticker: Stock ticker symbol
            format: 'csv' or 'excel'
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{ticker}_GEX_{timestamp}"
        
        # Create DataFrame
        df = pd.DataFrame({
            'Strike': gex_data.get('strikes', []),
            'Call_GEX': gex_data.get('call_gex', []),
            'Put_GEX': gex_data.get('put_gex', []),
            'Net_GEX': gex_data.get('net_gex_by_strike', [])
        })
        
        # Add metadata
        metadata = {
            'Ticker': ticker,
            'Export_Time': datetime.now().isoformat(),
            'Zero_Gamma_Level': gex_data.get('zero_gamma_level', 'N/A'),
            'Max_Gamma_Strike': gex_data.get('max_gamma_strike', 'N/A'),
            'Total_GEX': gex_data.get('total_gex', 0),
            'Put_Call_Ratio': gex_data.get('put_call_ratio', 1.0)
        }
        
        if format == 'csv':
            filepath = os.path.join(self.export_dir, f"{filename}.csv")
            
            # Write metadata as comments
            with open(filepath, 'w') as f:
                f.write("# GEX Terminal Export\n")
                for key, value in metadata.items():
                    f.write(f"# {key}: {value}\n")
                f.write("#\n")
            
            # Append data
            df.to_csv(filepath, mode='a', index=False)
            return filepath
            
        elif format == 'excel':
            filepath = os.path.join(self.export_dir, f"{filename}.xlsx")
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Write data
                df.to_excel(writer, sheet_name='GEX Profile', index=False)
                
                # Write metadata
                meta_df = pd.DataFrame(list(metadata.items()), columns=['Field', 'Value'])
                meta_df.to_excel(writer, sheet_name='Metadata', index=False)
                
                # Write heatmap data if available
                heatmap = gex_data.get('heatmap_data', [])
                if heatmap:
                    heatmap_df = pd.DataFrame(heatmap)
                    heatmap_df.to_excel(writer, sheet_name='Heatmap', index=False)
            
            return filepath
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def export_ticker_summary(self, tickers_data, format='csv'):
        """
        Export summary for multiple tickers
        
        Args:
            tickers_data: Dict of {ticker: gex_data}
            format: 'csv' or 'excel'
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"GEX_Summary_{timestamp}"
        
        summary_data = []
        for ticker, gex_data in tickers_data.items():
            summary_data.append({
                'Ticker': ticker,
                'Zero_Gamma': gex_data.get('zero_gamma_level', 'N/A'),
                'Max_Gamma_Strike': gex_data.get('max_gamma_strike', 'N/A'),
                'Total_GEX_B': gex_data.get('total_gex', 0),
                'Put_Call_Ratio': gex_data.get('put_call_ratio', 1.0),
                'Gamma_Regime': 'POSITIVE' if gex_data.get('total_gex', 0) > 0 else 'NEGATIVE'
            })
        
        df = pd.DataFrame(summary_data)
        
        if format == 'csv':
            filepath = os.path.join(self.export_dir, f"{filename}.csv")
            df.to_csv(filepath, index=False)
            return filepath
        elif format == 'excel':
            filepath = os.path.join(self.export_dir, f"{filename}.xlsx")
            df.to_excel(filepath, index=False, sheet_name='Summary')
            return filepath
        
        return None
    
    def export_alerts(self, alerts, ticker):
        """Export alerts to CSV"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{ticker}_Alerts_{timestamp}.csv"
        filepath = os.path.join(self.export_dir, filename)
        
        df = pd.DataFrame(alerts)
        df.to_csv(filepath, index=False)
        return filepath
    
    def list_exports(self):
        """List all exported files"""
        files = []
        for f in os.listdir(self.export_dir):
            if f.endswith(('.csv', '.xlsx')):
                filepath = os.path.join(self.export_dir, f)
                files.append({
                    'filename': f,
                    'path': filepath,
                    'size': os.path.getsize(filepath),
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                })
        return sorted(files, key=lambda x: x['created'], reverse=True)
    
    def get_export_summary(self):
        """Get summary of exports"""
        files = self.list_exports()
        return {
            'total_files': len(files),
            'csv_files': len([f for f in files if f['filename'].endswith('.csv')]),
            'excel_files': len([f for f in files if f['filename'].endswith('.xlsx')]),
            'latest_export': files[0] if files else None
        }