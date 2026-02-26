#!/usr/bin/env python3
"""
Daily Trading Report Generator
Posts comprehensive daily summary to Discord
"""

import sys
sys.path.insert(0, '/Users/Honeybot/.openclaw/workspace/trading')

from journal import TradingJournal
from datetime import datetime, timedelta
import json

class DailyReport:
    def __init__(self):
        self.journal = TradingJournal()
    
    def generate(self) -> str:
        """Generate formatted daily report"""
        
        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Daily summary
        summary = self.journal.calculate_daily_summary(yesterday)
        
        # Get recent trades
        recent_trades = self.journal.get_trade_history(limit=10)
        closed_trades = [t for t in recent_trades if t['status'] == 'closed'][:5]
        open_trades = [t for t in recent_trades if t['status'] == 'open']
        
        # Performance report
        perf = self.journal.get_performance_report(days=7)
        
        # Build report
        lines = [
            f"📊 **DAILY TRADING REPORT - {yesterday}**",
            "",
            f"**📈 Today's Performance**",
            f"```",
            f"Trades:     {summary['total_trades']}",
        ]
        
        if summary['total_trades'] > 0:
            lines.extend([
                f"Win Rate:   {summary['win_rate']:.1f}%",
                f"P&L:        ${summary['total_pnl']:,.2f}",
                f"Avg Win:    ${summary.get('avg_win', 0):,.2f}",
                f"Avg Loss:   ${summary.get('avg_loss', 0):,.2f}",
                f"Best:       ${summary.get('best_trade', 0):,.2f}",
                f"Worst:      ${summary.get('worst_trade', 0):,.2f}",
            ])
        
        lines.extend([
            f"```",
            "",
            f"**📊 7-Day Stats**",
            f"```",
            f"Total Trades: {perf['total_trades']}",
            f"Win Rate:     {perf['win_rate']:.1f}%",
            f"Total P&L:    ${perf['total_pnl']:,.2f}",
            f"Avg Return:   {perf['avg_return']:.2f}%",
            f"```",
            "",
        ])
        
        # Open positions
        if open_trades:
            lines.extend([
                f"**🟢 Open Positions ({len(open_trades)})**",
                f"```",
            ])
            for t in open_trades[:5]:
                lines.append(f"{t['ticker']:6} {t['direction']:5} @ ${t['entry_price']:.2f} | {t['strategy']}")
            lines.append(f"```")
            lines.append("")
        
        # Recent closed trades
        if closed_trades:
            lines.extend([
                f"**✅ Recent Closed Trades**",
                f"```",
            ])
            for t in closed_trades:
                pnl = t.get('pnl_absolute', 0) or 0
                emoji = "🟢" if pnl > 0 else "🔴"
                lines.append(f"{emoji} {t['ticker']:6} {t['direction']:5} | ${pnl:>+8.2f} | {t.get('exit_reason', 'manual')}")
            lines.append(f"```")
            lines.append("")
        
        # Strategy breakdown
        if perf.get('by_strategy'):
            lines.extend([
                f"**🎯 By Strategy**",
                f"```",
            ])
            for strat, stats in perf['by_strategy'].items():
                lines.append(f"{strat:12} {stats['total']:3} trades | {stats['win_rate']:5.1f}% WR | ${stats['total_pnl']:>+10,.2f}")
            lines.append(f"```")
        
        return "\n".join(lines)

def main():
    report = DailyReport()
    print(report.generate())

if __name__ == '__main__':
    main()
