#!/usr/bin/env python3
"""
Comprehensive Trading Journal System
Tracks positions, P&L, performance metrics, and trading notes
"""

import sqlite3
import json
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from enum import Enum

# Setup paths
JOURNAL_DIR = Path('/Users/Honeybot/.openclaw/workspace/trading/journal')
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = JOURNAL_DIR / 'trading_journal.db'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(JOURNAL_DIR / 'journal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"

@dataclass
class Trade:
    """Represents a single trade/position"""
    id: Optional[int] = None
    timestamp: str = ""
    ticker: str = ""
    direction: str = ""
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: int = 0
    position_size: float = 0.0  # Dollar amount
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: str = TradeStatus.OPEN.value
    exit_timestamp: Optional[str] = None
    pnl_absolute: Optional[float] = None
    pnl_percent: Optional[float] = None
    exit_reason: Optional[str] = None
    strategy: str = "gex"  # gex, manual, momentum, etc.
    confidence: int = 0
    notes: str = ""
    tags: str = ""  # comma-separated tags
    
    def to_dict(self) -> Dict:
        return asdict(self)

class TradingJournal:
    """Main trading journal class"""
    
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with all tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades/Positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity INTEGER NOT NULL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                status TEXT DEFAULT 'open',
                exit_timestamp TEXT,
                pnl_absolute REAL,
                pnl_percent REAL,
                exit_reason TEXT,
                strategy TEXT DEFAULT 'manual',
                confidence INTEGER DEFAULT 0,
                notes TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Journal entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                mood TEXT,
                market_condition TEXT,
                lessons_learned TEXT,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily performance summary
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_win REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                best_trade REAL DEFAULT 0,
                worst_trade REAL DEFAULT 0,
                notes TEXT
            )
        ''')
        
        # Strategy performance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_stats (
                strategy TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_return REAL DEFAULT 0,
                last_updated TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(date)')
        
        conn.commit()
        conn.close()
        logger.info(f"Trading journal database initialized at {self.db_path}")
    
    def add_trade(self, trade: Trade) -> int:
        """Add a new trade to the journal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (
                timestamp, ticker, direction, entry_price, exit_price, quantity,
                position_size, stop_loss, take_profit, status, exit_timestamp,
                pnl_absolute, pnl_percent, exit_reason, strategy, confidence,
                notes, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.timestamp, trade.ticker, trade.direction, trade.entry_price,
            trade.exit_price, trade.quantity, trade.position_size, trade.stop_loss,
            trade.take_profit, trade.status, trade.exit_timestamp, trade.pnl_absolute,
            trade.pnl_percent, trade.exit_reason, trade.strategy, trade.confidence,
            trade.notes, trade.tags
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Trade added: {trade.ticker} {trade.direction} @ ${trade.entry_price:.2f} (ID: {trade_id})")
        return trade_id
    
    def close_trade(self, trade_id: int, exit_price: float, 
                   exit_reason: str = "manual", exit_notes: str = "") -> Dict:
        """Close an open trade and calculate P&L"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get trade details
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": f"Trade {trade_id} not found"}
        
        entry_price = row[3]
        direction = row[2]
        quantity = row[5]
        
        # Calculate P&L
        if direction == TradeDirection.LONG.value:
            pnl_absolute = (exit_price - entry_price) * quantity * 100  # Options = 100 shares
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_absolute = (entry_price - exit_price) * quantity * 100
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        exit_time = datetime.now().isoformat()
        
        # Update trade
        cursor.execute('''
            UPDATE trades 
            SET status = 'closed', exit_price = ?, exit_timestamp = ?,
                pnl_absolute = ?, pnl_percent = ?, exit_reason = ?,
                notes = COALESCE(notes, '') || ' | Exit: ' || ?
            WHERE id = ?
        ''', (exit_price, exit_time, pnl_absolute, pnl_percent, exit_reason, exit_notes, trade_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Trade {trade_id} closed: P&L ${pnl_absolute:.2f} ({pnl_percent:.2f}%)")
        
        return {
            "trade_id": trade_id,
            "exit_price": exit_price,
            "pnl_absolute": pnl_absolute,
            "pnl_percent": pnl_percent,
            "exit_reason": exit_reason,
            "hold_time": self._calculate_hold_time(row[1], exit_time)
        }
    
    def _calculate_hold_time(self, entry_time: str, exit_time: str) -> str:
        """Calculate how long position was held"""
        try:
            entry = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            exit = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            duration = exit - entry
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f}h"
        except:
            return "unknown"
    
    def get_open_positions(self) -> List[Dict]:
        """Get all currently open positions"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_trade_history(self, limit: int = 50, ticker: str = None) -> List[Dict]:
        """Get trade history with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if ticker:
            cursor.execute(
                "SELECT * FROM trades WHERE ticker = ? ORDER BY timestamp DESC LIMIT ?",
                (ticker, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_journal_entry(self, date: str, title: str, content: str = "",
                         mood: str = "", market_condition: str = "",
                         lessons: str = "", tags: str = "") -> int:
        """Add a journal entry for the day"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO journal_entries 
            (date, title, content, mood, market_condition, lessons_learned, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date, title, content, mood, market_condition, lessons, tags))
        
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Journal entry added: {title} (ID: {entry_id})")
        return entry_id
    
    def calculate_daily_summary(self, date: str = None) -> Dict:
        """Calculate performance summary for a specific date"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all closed trades for the date
        cursor.execute('''
            SELECT pnl_absolute, pnl_percent FROM trades 
            WHERE DATE(timestamp) = ? AND status = 'closed'
        ''', (date,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                "date": date,
                "total_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "message": "No trades for this date"
            }
        
        pnls = [r[0] for r in results]
        pnl_percents = [r[1] for r in results]
        
        wins = sum(1 for pnl in pnls if pnl > 0)
        losses = sum(1 for pnl in pnls if pnl <= 0)
        total = len(pnls)
        
        win_pnl = [pnl for pnl in pnls if pnl > 0]
        loss_pnl = [pnl for pnl in pnls if pnl <= 0]
        
        summary = {
            "date": date,
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": (wins / total * 100) if total > 0 else 0,
            "total_pnl": sum(pnls),
            "avg_win": np.mean(win_pnl) if win_pnl else 0,
            "avg_loss": np.mean(loss_pnl) if loss_pnl else 0,
            "best_trade": max(pnls) if pnls else 0,
            "worst_trade": min(pnls) if pnls else 0,
            "profit_factor": abs(sum(win_pnl) / sum(loss_pnl)) if loss_pnl and sum(loss_pnl) != 0 else float('inf'),
            "avg_return": np.mean(pnl_percents)
        }
        
        return summary
    
    def get_performance_report(self, days: int = 30) -> Dict:
        """Generate comprehensive performance report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Overall stats
        cursor.execute('''
            SELECT COUNT(*), SUM(CASE WHEN pnl_absolute > 0 THEN 1 ELSE 0 END),
                   SUM(pnl_absolute), AVG(pnl_percent)
            FROM trades 
            WHERE DATE(timestamp) >= ? AND status = 'closed'
        ''', (since,))
        
        total, wins, total_pnl, avg_return = cursor.fetchone()
        total = total or 0
        wins = wins or 0
        
        # By strategy
        cursor.execute('''
            SELECT strategy, COUNT(*), 
                   SUM(CASE WHEN pnl_absolute > 0 THEN 1 ELSE 0 END),
                   SUM(pnl_absolute), AVG(pnl_percent)
            FROM trades 
            WHERE DATE(timestamp) >= ? AND status = 'closed'
            GROUP BY strategy
        ''', (since,))
        
        by_strategy = {}
        for row in cursor.fetchall():
            by_strategy[row[0]] = {
                "total": row[1],
                "wins": row[2],
                "win_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                "total_pnl": row[3],
                "avg_return": row[4]
            }
        
        # By ticker
        cursor.execute('''
            SELECT ticker, COUNT(*), 
                   SUM(CASE WHEN pnl_absolute > 0 THEN 1 ELSE 0 END),
                   SUM(pnl_absolute)
            FROM trades 
            WHERE DATE(timestamp) >= ? AND status = 'closed'
            GROUP BY ticker
            ORDER BY SUM(pnl_absolute) DESC
        ''', (since,))
        
        by_ticker = {row[0]: {"total": row[1], "wins": row[2], "pnl": row[3]} 
                     for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "period_days": days,
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": total - wins,
            "win_rate": (wins / total * 100) if total > 0 else 0,
            "total_pnl": total_pnl or 0,
            "avg_return": avg_return or 0,
            "by_strategy": by_strategy,
            "by_ticker": by_ticker
        }
    
    def export_to_csv(self, filepath: str = None):
        """Export all trades to CSV"""
        if filepath is None:
            filepath = JOURNAL_DIR / f"trades_export_{datetime.now().strftime('%Y%m%d')}.csv"
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp DESC", conn)
        df.to_csv(filepath, index=False)
        conn.close()
        
        logger.info(f"Trades exported to {filepath}")
        return filepath
    
    def print_dashboard(self):
        """Print a nice terminal dashboard"""
        print("\n" + "="*70)
        print("📊 TRADING JOURNAL DASHBOARD")
        print("="*70)
        
        # Open positions
        open_pos = self.get_open_positions()
        print(f"\n🟢 OPEN POSITIONS: {len(open_pos)}")
        if open_pos:
            for pos in open_pos:
                print(f"   {pos['ticker']:5} | {pos['direction']:5} | "
                      f"${pos['entry_price']:>8.2f} | {pos['strategy']:10} | "
                      f"{pos['timestamp'][:10]}")
        
        # Today's summary
        today_summary = self.calculate_daily_summary()
        print(f"\n📈 TODAY'S PERFORMANCE ({today_summary['date']})")
        print(f"   Trades: {today_summary['total_trades']}")
        if today_summary['total_trades'] > 0:
            print(f"   Win Rate: {today_summary['win_rate']:.1f}%")
            print(f"   P&L: ${today_summary['total_pnl']:,.2f}")
            print(f"   Best: ${today_summary['best_trade']:,.2f} | Worst: ${today_summary['worst_trade']:,.2f}")
        
        # 7-day performance
        report = self.get_performance_report(days=7)
        print(f"\n📊 7-DAY PERFORMANCE")
        print(f"   Total Trades: {report['total_trades']}")
        print(f"   Win Rate: {report['win_rate']:.1f}%")
        print(f"   Total P&L: ${report['total_pnl']:,.2f}")
        print(f"   Avg Return: {report['avg_return']:.2f}%")
        
        if report['by_strategy']:
            print(f"\n🎯 BY STRATEGY:")
            for strategy, stats in report['by_strategy'].items():
                print(f"   {strategy:12} | {stats['total']:3} trades | "
                      f"{stats['win_rate']:5.1f}% WR | ${stats['total_pnl']:>10,.2f}")
        
        if report['by_ticker']:
            print(f"\n📈 TOP TICKERS:")
            for ticker, stats in list(report['by_ticker'].items())[:5]:
                print(f"   {ticker:6} | {stats['total']:3} trades | ${stats['pnl']:>10,.2f}")
        
        print("\n" + "="*70)

# CLI Interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Trading Journal CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add trade
    add_parser = subparsers.add_parser('add', help='Add a new trade')
    add_parser.add_argument('--ticker', required=True)
    add_parser.add_argument('--direction', choices=['long', 'short'], required=True)
    add_parser.add_argument('--price', type=float, required=True)
    add_parser.add_argument('--quantity', type=int, default=1)
    add_parser.add_argument('--size', type=float, help='Position size in dollars')
    add_parser.add_argument('--stop', type=float, help='Stop loss price')
    add_parser.add_argument('--target', type=float, help='Take profit price')
    add_parser.add_argument('--strategy', default='manual')
    add_parser.add_argument('--confidence', type=int, default=0)
    add_parser.add_argument('--notes', default='')
    
    # Close trade
    close_parser = subparsers.add_parser('close', help='Close a trade')
    close_parser.add_argument('--id', type=int, required=True)
    close_parser.add_argument('--price', type=float, required=True)
    close_parser.add_argument('--reason', default='manual')
    close_parser.add_argument('--notes', default='')
    
    # List trades
    list_parser = subparsers.add_parser('list', help='List trades')
    list_parser.add_argument('--status', choices=['open', 'closed', 'all'], default='all')
    list_parser.add_argument('--ticker')
    list_parser.add_argument('--limit', type=int, default=20)
    
    # Dashboard
    dashboard_parser = subparsers.add_parser('dashboard', help='Show dashboard')
    
    # Stats
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--days', type=int, default=30)
    
    # Journal entry
    journal_parser = subparsers.add_parser('journal', help='Add journal entry')
    journal_parser.add_argument('--title', required=True)
    journal_parser.add_argument('--content', default='')
    journal_parser.add_argument('--mood', default='')
    journal_parser.add_argument('--market', default='')
    journal_parser.add_argument('--lessons', default='')
    
    # Export
    export_parser = subparsers.add_parser('export', help='Export to CSV')
    export_parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    journal = TradingJournal()
    
    if args.command == 'add':
        trade = Trade(
            timestamp=datetime.now().isoformat(),
            ticker=args.ticker.upper(),
            direction=args.direction,
            entry_price=args.price,
            quantity=args.quantity,
            position_size=args.size or args.price * args.quantity * 100,
            stop_loss=args.stop,
            take_profit=args.target,
            strategy=args.strategy,
            confidence=args.confidence,
            notes=args.notes
        )
        trade_id = journal.add_trade(trade)
        print(f"✅ Trade added with ID: {trade_id}")
    
    elif args.command == 'close':
        result = journal.close_trade(args.id, args.price, args.reason, args.notes)
        if 'error' in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ Trade closed")
            print(f"   P&L: ${result['pnl_absolute']:.2f} ({result['pnl_percent']:.2f}%)")
            print(f"   Hold time: {result['hold_time']}")
    
    elif args.command == 'list':
        trades = journal.get_trade_history(limit=args.limit, ticker=args.ticker)
        print(f"\n{'ID':<5} {'Date':<12} {'Ticker':<8} {'Dir':<6} {'Entry':<10} {'Exit':<10} {'P&L':<12} {'Status':<8}")
        print("-" * 80)
        for t in trades:
            pnl_str = f"${t['pnl_absolute']:,.0f}" if t['pnl_absolute'] else "-"
            exit_str = f"${t['exit_price']:.2f}" if t['exit_price'] else "-"
            print(f"{t['id']:<5} {t['timestamp'][:10]:<12} {t['ticker']:<8} "
                  f"{t['direction']:<6} ${t['entry_price']:<9.2f} {exit_str:<10} "
                  f"{pnl_str:<12} {t['status']:<8}")
    
    elif args.command == 'dashboard':
        journal.print_dashboard()
    
    elif args.command == 'stats':
        report = journal.get_performance_report(days=args.days)
        print(f"\n📊 PERFORMANCE REPORT (Last {args.days} days)")
        print(f"Total Trades: {report['total_trades']}")
        print(f"Win Rate: {report['win_rate']:.1f}%")
        print(f"Total P&L: ${report['total_pnl']:,.2f}")
        print(f"Avg Return: {report['avg_return']:.2f}%")
        
        if report['by_strategy']:
            print("\nBy Strategy:")
            for strat, stats in report['by_strategy'].items():
                print(f"  {strat}: {stats['total']} trades, {stats['win_rate']:.1f}% WR")
    
    elif args.command == 'journal':
        entry_id = journal.add_journal_entry(
            date=datetime.now().strftime('%Y-%m-%d'),
            title=args.title,
            content=args.content,
            mood=args.mood,
            market_condition=args.market,
            lessons=args.lessons
        )
        print(f"✅ Journal entry added: {entry_id}")
    
    elif args.command == 'export':
        path = journal.export_to_csv(args.output)
        print(f"✅ Exported to: {path}")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
