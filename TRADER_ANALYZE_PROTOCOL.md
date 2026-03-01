# TRADER_ANALYZE Protocol v1.0

## Overview
A systematic reasoning framework for TraderBot to evaluate trading opportunities, validate signals, and execute with risk-managed precision.

**Philosophy**: Every trade decision follows a structured thought chain. No FOMO. No gut feelings. Only validated signals.

---

## Protocol Structure

```
TRADER_ANALYZE(symbol, signal_data, market_context)
    → Market Regime Assessment
    → Signal Confirmation Checklist  
    → Risk Assessment Scoring
    → Position Sizing Calculation
    → Exit Condition Definition
    → FINAL DECISION
```

---

## 1. Market Regime Identification

### Questions to Answer

**Q1: What is the primary trend?**
- [ ] Price > 200 EMA (Bullish trend)
- [ ] Price < 200 EMA (Bearish trend)  
- [ ] Price within ±2% of 200 EMA (Neutral/Choppy)
- **Score**: STRONG_TREND (+20) | WEAK_TREND (+5) | CHOPPY (-10)

**Q2: Is volatility supportive?**
- [ ] Average True Range (ATR) > 20-day ATR average (High vol)
- [ ] ATR near baseline (Normal vol)
- [ ] ATR < 80% of 20-day average (Low vol / compressed)
- **Score**: NORMAL_VOL (+10) | HIGH_VOL (+5) | LOW_VOL (-5) | SQUEEZE (+15)

**Q3: What is RSI indicating?**
- [ ] RSI > 70 (Overbought - caution)
- [ ] RSI 50-70 (Bullish momentum zone)
- [ ] RSI 30-50 (Recovery zone)
- [ ] RSI < 30 (Oversold - mean reversion potential)
- **Score**: MOMENTUM_ZONE (+15) | OVERBOUGHT (-10) | OVERSOLD (+5)

**Q4: Volume character?**
- [ ] Volume > 150% of 20-day average (Breakout confirmation)
- [ ] Volume 100-150% of average (Normal interest)
- [ ] Volume < 100% of average (Lack of conviction)
- **Score**: HIGH_VOLUME (+15) | NORMAL_VOLUME (+5) | LOW_VOLUME (-10)

**Regime Classification**:
- TRENDING_BULLISH: Price > 200 EMA, RSI 50-70, Rising volume
- TRENDING_BEARISH: Price < 200 EMA, RSI 30-50, Distribution volume
- RANGING/CHOPPY: Price near 200 EMA, RSI 40-60, Low volume
- VOLATILITY_EXPANSION: High ATR, High volume, Extreme RSI
- VOLATILITY_COMPRESSION: Low ATR, Declining volume (setting up breakout)

---

## 2. Signal Confirmation Checklist

### Core Signal Validation

| Check | Weight | Pass Criteria |
|-------|--------|---------------|
| Trend Alignment | 25% | Signal direction matches 200 EMA trend |
| Moving Average Cross | 20% | Fast EMA (20) crossed Slow EMA (50) within 3 bars |
| RSI Confirmation | 15% | RSI in appropriate zone for signal direction |
| Volume Confirmation | 20% | Volume > 1.3x average on signal bar |
| Support/Resistance | 15% | Price near key level (not in middle of range) |
| Timeframe Alignment | 5% | Higher timeframe (15min+) confirms signal |

**Signal Score Calculation**:
```python
def calculate_signal_score(checks):
    score = 0
    score += 25 if checks['trend_aligned'] else 0
    score += 20 if checks['ma_cross_valid'] else 0
    score += 15 if checks['rsi_confirmed'] else 0
    score += 20 if checks['volume_confirmed'] else 0
    score += 15 if checks['key_level_near'] else 0
    score += 5 if checks['htf_aligned'] else 0
    return score

MINIMUM_SIGNAL_SCORE = 60  # Must exceed to proceed
```

---

## 3. Risk Assessment Scoring

### Risk Factors Matrix

| Factor | Impact | Assessment |
|--------|--------|------------|
| Market Risk | High | SPY/QQQ trend direction vs position |
| Sector Risk | Medium | Sector ETF correlation |
| Position Risk | High | Max 2% account risk per trade |
| Time Risk | Medium | Hold time vs opportunity cost |
| Correlation Risk | Medium | Existing correlated positions |

**Risk Tiers**:

| Tier | Conditions | Position Size Limit | Stop Required |
|------|------------|---------------------|---------------|
| LOW_RISK | Strong trend + High signal score + Low recent volatility | 3% max risk | 2% stop |
| MEDIUM_RISK | Mixed signals or choppy market | 2% max risk | 2% stop |
| HIGH_RISK | Counter-trend or high volatility | 1% max risk | 1.5% stop |
| NO_TRADE | Signal score < 60 or max drawdown period | 0% | N/A |

### Risk Score Formula
```python
risk_score = (
    trend_strength * 0.30 +
    signal_quality * 0.25 +
    volatility_context * 0.20 +
    account_heat * 0.15 +
    market_correlation * 0.10
)

# Risk score 0-100
# 0-40: HIGH_RISK tier
# 41-60: MEDIUM_RISK tier  
# 61-80: LOW_RISK tier
# 81-100: VERY_LOW_RISK (increase size)
```

---

## 4. Position Sizing Logic

### Core Formula - Fixed Fractional

```python
def calculate_position_size(account_value, entry_price, stop_price, risk_tier):
    """
    Fixed fractional position sizing with risk tier adjustments
    """
    risk_percent = {  # Max % of account to risk
        'LOW_RISK': 0.03,
        'MEDIUM_RISK': 0.02,
        'HIGH_RISK': 0.01
    }[risk_tier]
    
    risk_amount = account_value * risk_percent
    risk_per_share = abs(entry_price - stop_price)
    
    if risk_per_share <= 0:
        return 0  # Invalid stop placement
    
    shares = int(risk_amount / risk_per_share)
    
    # Max position value constraint (no more than 25% in one trade)
    max_position_value = account_value * 0.25
    max_shares_by_value = int(max_position_value / entry_price)
    
    shares = min(shares, max_shares_by_value)
    
    # Min position filter (avoid very small positions)
    min_position_value = 1000  # $1k minimum
    if shares * entry_price < min_position_value:
        return 0
    
    return shares
```

### Kelly Criterion Adjustment (Optional)

```python
def kelly_fraction(win_rate, avg_win_pct, avg_loss_pct):
    """
    Optimal fraction of bankroll to bet given edge
    Kelly% = W - [(1-W)/R]
    Where W = win rate, R = avg_win/avg_loss ratio
    """
    if avg_loss_pct == 0:
        return 0.25  # Conservative default if no losses yet
    
    win_loss_ratio = avg_win_pct / avg_loss_pct
    kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
    
    return max(0, min(kelly * 0.25, 0.05))  # Half-Kelly, capped at 5%
```

---

## 5. Exit Condition Evaluation

### Stop Loss Rules

| Type | Condition | Placement |
|------|-----------|-----------|
| HARD_STOP | Initial risk definition | Entry - (Entry × 0.02) |
| TRAILING_STOP | Protect profits | Highest price × 0.95 (5% trailing) |
| TIME_STOP | Max hold period | 10-14 days depending on timeframe |
| TECHNICAL_STOP | Signal invalidated | EMA cross opposite direction |

### Exit Evaluation Priority

```
1. HARD_STOP: Triggered immediately if price touches
2. TRAILING_STOP: Activated after +3% profit, checked each bar
3. TECHNICAL_STOP: On bearish EMA crossover after position
4. TIME_STOP: At 14 days regardless of P&L
5. PROFIT_TARGET: 2:1 R/R achieved (optional, can let run)
```

### Exit Score Assessment

Before entering, evaluate likely exit scenario:

| Exit Type | Probability | Expected R/R |
|-----------|-------------|--------------|
| Trailing Stop (Profitable) | Historical % | Avg gain |
| Stop Loss (Loss) | Historical % | Max loss |
| Time Stop (Breakeven/Small) | Historical % | Avg result |

**Expected Value Calculation**:
```
EV = (Win_Prob × Avg_Win) - (Loss_Prob × Avg_Loss)
Must be > 0 for valid trade
```

---

## 6. Final Decision Matrix

```python
class TradeDecision:
    def __init__(self):
        self.enter = False
        self.size = 0
        self.entry_price = 0
        self.stop_price = 0
        self.target_price = 0
        self.exit_rules = {}
        self.reason = ""

def make_trade_decision(symbol, signal_data, market_context, account_value):
    decision = TradeDecision()
    
    # Step 1: Market Regime
    regime = identify_regime(market_context)
    regime_score = calculate_regime_score(regime)
    
    # Step 2: Signal Confirmation
    signal_score = confirm_signal(signal_data, regime)
    
    # Step 3: Risk Assessment  
    risk_tier = assess_risk_tier(regime, signal_score, account_value)
    
    # Step 4: Position Sizing
    if signal_score >= 60 and regime_score >= 40:
        shares = calculate_position_size(
            account_value,
            signal_data['price'],
            signal_data['stop_price'],
            risk_tier
        )
    else:
        shares = 0
    
    # Step 5: Decision
    if shares > 0:
        decision.enter = True
        decision.size = shares
        decision.entry_price = signal_data['price']
        decision.stop_price = signal_data.get('stop_price', signal_data['price'] * 0.98)
        decision.target_price = signal_data.get('target_price', signal_data['price'] * 1.06)
        decision.exit_rules = define_exit_rules(risk_tier)
        decision.reason = f"Signal score: {signal_score}, Regime: {regime}, Risk: {risk_tier}"
    else:
        decision.enter = False
        decision.reason = f"Signal score: {signal_score} (min 60), Regime score: {regime_score} (min 40)"
    
    return decision
```

---

## Reasoning Log Format

Every analysis produces a structured log entry:

```json
{
  "timestamp": "2026-02-28T19:00:00Z",
  "symbol": "SPY",
  "protocol_version": "1.0",
  "market_regime": {
    "classification": "TRENDING_BULLISH",
    "score": 65,
    "factors": {
      "price_vs_200ema": 4.2,
      "rsi": 58,
      "volume_ratio": 1.45,
      "atr_vs_average": 0.95
    }
  },
  "signal_analysis": {
    "source": "dual_ma_crossover",
    "score": 85,
    "checks": {
      "trend_aligned": true,
      "ma_cross_valid": true,
      "rsi_confirmed": true,
      "volume_confirmed": true,
      "key_level_near": false,
      "htf_aligned": true
    }
  },
  "risk_assessment": {
    "tier": "LOW_RISK",
    "score": 72,
    "risks_identified": ["slight_overbought_rsi", "end_of_day_timing"]
  },
  "position_sizing": {
    "account_value": 100000,
    "risk_percent": 0.03,
    "risk_amount": 3000,
    "entry_price": 450.00,
    "stop_price": 441.00,
    "shares": 333
  },
  "exit_rules": {
    "hard_stop": 441.00,
    "trailing_stop_enabled": true,
    "trailing_stop_pct": 0.05,
    "time_stop_days": 14,
    "technical_exit": "ema_cross_down"
  },
  "decision": {
    "action": "ENTER_LONG",
    "shares": 333,
    "confidence": 85,
    "reasoning_summary": "Strong bullish trend, confirmed MA crossover with high volume. Low risk tier allows 3% position size."
  }
}
```

---

## Quick Reference Card

### Before Every Trade, Ask:

1. **What regime are we in?** → Trending bullish/bearish, ranging, expanding/compressing
2. **Does the signal score exceed 60?** → No = skip
3. **What's the risk tier?** → Determines position size and stop placement
4. **Where is my stop?** → Defined BEFORE entry
5. **Where do I take profits?** → Trailing stop activated after +3%
6. **What's my max hold time?** → Time stop enforces discipline

### No-Trade Conditions:
- Signal score < 60
- In drawdown > 15% from equity peak
- 3+ open correlated positions
- News event within 30 minutes
- Opening first 15 minutes (unless pre-planned)
- Closing last 15 minutes

---

*Protocol Version: 1.0*
*Created: 2026-02-28*
*Applies to: All TraderBot strategies*
