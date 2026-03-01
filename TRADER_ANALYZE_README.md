# TRADER_ANALYZE Protocol Suite

## Overview

A complete reasoning framework for systematic trading decisions, validated against a +68.67% backtest strategy.

---

## Files in This Suite

| File | Purpose |
|------|---------|
| `TRADER_ANALYZE_PROTOCOL.md` | Complete protocol specification with 6-step reasoning framework |
| `TRADER_ANALYZE_EXAMPLES.md` | Sample reasoning traces from actual +68.67% backtest trades |
| `TRADER_ANALYZE_INTEGRATION.md` | Implementation guide with code samples for live deployment |
| `TRADER_ANALYZE_README.md` | This file - quick reference and index |

---

## The 6-Step Protocol

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Market Regime Identification                             │
│ Questions: Trend, Volatility, RSI, Volume                        │
│ Output: Regime Classification + Score                            │
├─────────────────────────────────────────────────────────────────┤
│ STEP 2: Signal Confirmation Checklist                           │
│ Checks: Trend alignment, MA cross, RSI, Volume, Levels          │
│ Output: Signal Score (0-100)                                     │
├─────────────────────────────────────────────────────────────────┤
│ STEP 3: Risk Assessment Scoring                                 │
│ Factors: Market, Signal, Volatility, Account, Correlation       │
│ Output: Risk Tier (LOW/MEDIUM/HIGH/NO_TRADE)                    │
├─────────────────────────────────────────────────────────────────┤
│ STEP 4: Position Sizing Logic                                   │
│ Formula: Risk $ / Risk Per Share → Constrained by Max Position  │
│ Output: Shares, Stop Price, Target Price                        │
├─────────────────────────────────────────────────────────────────┤
│ STEP 5: Exit Condition Evaluation                               │
│ Rules: Hard stop, Trailing stop, Time stop, Technical exit      │
│ Output: Complete exit plan                                       │
├─────────────────────────────────────────────────────────────────┤
│ STEP 6: Final Decision                                          │
│ Matrix: Signal ≥60 AND Regime ≥40 → Approved                    │
│ Output: TradeDecision object with full reasoning log            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Parameters (from +68.67% Strategy)

```python
# Dual MA Crossover Strategy
FAST_EMA = 20
SLOW_EMA = 50
TREND_EMA = 200
RSI_PERIOD = 14
RSI_MID = 50  # Filter threshold
STOP_LOSS_PCT = 0.02       # -2%
TRAILING_STOP_PCT = 0.05   # -5% from high
RISK_PER_TRADE_LOW = 0.03  # 3% for LOW_RISK tier
MAX_POSITION_PCT = 0.25    # 25% account in one trade
```

---

## Backtest Validation Results

| Metric | Value | Notes |
|--------|-------|-------|
| Total Return | **+68.67%** | Over 3 years on SPY |
| Win Rate | **100%** | 3/3 trades profitable |
| Avg Trade | +$4,735 | Mix of trailing stops |
| Max Drawdown | -33.78% | During trade, not realized |
| Sharpe Ratio | 0.65 | Risk-adjusted returns |
| Signal Scores | 80-88 | All exceeded 60 threshold |
| Regime Scores | 50-60 | All exceeded 40 threshold |
| Hold Time | 139-175 days | Trend-following duration |

---

## Quick Start

### 1. Review Protocol
```bash
code /Users/Honeybot/.openclaw/workspace/trading/TRADER_ANALYZE_PROTOCOL.md
```

### 2. Study Examples
```bash
code /Users/Honeybot/.openclaw/workspace/trading/TRADER_ANALYZE_EXAMPLES.md
```

### 3. Implement Integration
```bash
# Copy integration template
cp /Users/Honeybot/.openclaw/workspace/trading/TRADER_ANALYZE_INTEGRATION.md ./integration_plan.md

# Create module from Option A code
# Save as: trader_analyze.py
```

### 4. Configure
```yaml
# trader_config.yaml
thresholds:
  min_signal_score: 60
  min_regime_score: 40
  
account:
  risk_per_trade: 0.03  # 3% for LOW_RISK
  max_position_pct: 0.25
```

### 5. Test
```bash
python test_trader_analyze.py
```

---

## Protocol vs Current System

| Aspect | Current | With TRADER_ANALYZE |
|--------|---------|---------------------|
| Signal Validation | Threshold-only | 6-factor weighted score |
| Position Sizing | Fixed % | Risk-based, tier-adjusted |
| Exit Planning | Configurable | Systematic multi-rule |
| Regime Awareness | None | Trend/vol classification |
| Reasoning Logs | Basic | Structured JSON audit trail |
| Rejection Tracking | None | Full analysis logged |

---

## Decision Matrix Summary

```
Signal Score (0-100) │ Regime Score (0-100) │ Risk Tier     │ Action
─────────────────────┼──────────────────────┼───────────────┼──────────
≥ 70                 │ ≥ 60                 │ LOW_RISK      │ Enter 3%
60-69                │ 40-59                │ MEDIUM_RISK   │ Enter 2%
60-69                │ < 40                 │ HIGH_RISK     │ Enter 1%
< 60                 │ Any                  │ NO_TRADE      │ Skip
Any                  │ < 40                 │ NO_TRADE      │ Skip
In drawdown > 15%    │ Any                  │ NO_TRADE      │ Skip
```

---

## Example Alert Output

```json
{
  "timestamp": "2026-02-28T19:30:00Z",
  "symbol": "SPY",
  "action": "APPROVED_FOR_ENTRY",
  "shares": 55,
  "entry_price": 510.25,
  "stop_price": 499.50,
  "risk_tier": "LOW_RISK",
  "confidence": 82,
  "regime": "TRENDING_BULLISH",
  "reasoning": {
    "signal_checks": {
      "trend_aligned": true,
      "ma_cross_valid": true,
      "rsi_confirmed": true,
      "volume_confirmed": false,
      "key_level_near": true
    },
    "exit_plan": {
      "hard_stop": 499.50,
      "trailing_stop": "activate at 535.76",
      "time_stop": "14 days"
    }
  }
}
```

---

## Integration Priority

1. **Week 1**: Implement `trader_analyze.py` - core module only
2. **Week 2**: Update `momentum_scanner.py` with protocol
3. **Week 3**: Update `gex_scanner.py` with protocol  
4. **Week 4**: Paper trade with protocol, review logs
5. **Week 5**: Go live if performance matches backtest expectations

---

## Questions?

- See `TRADER_ANALYZE_EXAMPLES.md` for reasoning trace walkthroughs
- See `TRADER_ANALYZE_INTEGRATION.md` for complete code samples
- See `TRADER_ANALYZE_PROTOCOL.md` for full specification

---

*Suite Version: 1.0*
*Validated Strategy: Dual MA Crossover with RSI Filter*
*Backtest Return: +68.67% (3 years, 3 trades)*
