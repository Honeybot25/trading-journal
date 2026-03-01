"""
GEX Educational Content Module
Contains explanations, tooltips, and educational content for the GEX Terminal
"""

GEX_KNOWLEDGE_BASE = {
    "gamma_exposure": {
        "title": "What is Gamma Exposure (GEX)?",
        "content": """
Gamma Exposure (GEX) measures the total gamma risk held by market participants, primarily option dealers.

**Key Concepts:**
- Gamma measures how much an option's delta changes as the underlying price moves
- Dealers who sell options become short gamma (must hedge dynamically)
- Dealers who buy options become long gamma (naturally hedged)

**Why It Matters:**
When dealers are short gamma (negative GEX), they must buy high and sell low to hedge, 
amplifying price moves. When long gamma (positive GEX), they sell rallies and buy dips, 
stabilizing prices.
        """
    },
    
    "dealer_hedging": {
        "title": "How Do Dealers Hedge?",
        "content": """
Dealers hedge by trading the underlying stock to remain delta-neutral.

**Short Gamma Position:**
- Stock rises → Delta increases → Dealers must BUY more shares
- Stock falls → Delta decreases → Dealers must SELL shares
- Result: Trend amplification, accelerated moves

**Long Gamma Position:**
- Stock rises → Dealers SELL shares (taking profits)
- Stock falls → Dealers BUY shares (averaging down)
- Result: Mean reversion, price stabilization

**The Flip:**
When price crosses zero gamma level, dealer hedging behavior reverses!
        """
    },
    
    "zero_gamma": {
        "title": "Zero Gamma Level (Flip Point)",
        "content": """
The Zero Gamma Level is the price where total gamma exposure equals zero.

**Significance:**
- Above zero gamma: Dealers are net long gamma → mean reversion
- Below zero gamma: Dealers are net short gamma → trend following
- Near zero gamma: Maximum instability, potential for large moves

**Trading Implication:**
Approaching zero gamma from above = increasing volatility risk
Breaking through zero gamma = regime change
        """
    },
    
    "positive_vs_negative": {
        "title": "Positive vs Negative Gamma Regimes",
        "content": """
**POSITIVE GAMMA (Dealers Long Gamma):**
- Market behavior: Range-bound, mean-reverting
- Volatility: Suppressed, pinning to strikes
- Strategy: Sell premium, fade moves
- Risk: False breakouts

**NEGATIVE GAMMA (Dealers Short Gamma):**
- Market behavior: Trending, momentum-driven
- Volatility: Elevated, accelerated moves
- Strategy: Follow trends, buy breakouts
- Risk: Sharp reversals

**Transition Zones:**
When near zero gamma, expect choppy price action as dealers adjust hedges.
        """
    },
    
    "pin_risk": {
        "title": "Pin Risk Explained",
        "content": """
Pin Risk occurs when price gravitates toward high gamma strike prices.

**Mechanics:**
- High open interest at a strike creates gamma concentration
- Dealers hedging around that strike act as price magnets
- As expiration approaches, pinning effect strengthens

**Max Pain Theory:**
Price tends to settle where option buyers lose the most (dealers profit).

**Trading Around Pins:**
- Expect mean reversion toward high GEX strikes
- Acceleration possible if price breaks away from pin
- Time decay increases pinning effect near expiration
        """
    },
    
    "gamma_squeeze": {
        "title": "Gamma Squeeze Dynamics",
        "content": """
A Gamma Squeeze occurs when rapid price movement forces dealers to hedge aggressively.

**The Squeeze Loop:**
1. Price moves up → Short gamma dealers must buy
2. Buying pushes price higher
3. Higher price = more buying required
4. Loop continues until option flow exhausts

**Identifying Squeeze Conditions:**
- Large negative GEX (dealers short gamma)
- Price approaching key strike from below
- High call buying activity
- Low time to expiration (higher gamma)

**Historical Examples:**
GME (Jan 2021), AMC (June 2021), various meme stocks
        """
    },
    
    "gex_calculation": {
        "title": "How GEX Is Calculated",
        "content": """
**Formula:**
GEX = Gamma × Open Interest × Contract Multiplier × Spot Price

**Components:**
- Gamma: Rate of delta change per $1 move (from Black-Scholes)
- Open Interest: Number of outstanding contracts
- Contract Multiplier: Usually 100 (shares per contract)
- Spot Price: Current underlying price

**Per-Strike Aggregation:**
- Sum all call GEX (positive)
- Sum all put GEX (positive, but subtracted in net)
- Net GEX = Call GEX - Put GEX

**Normalization:**
Displayed in billions ($) for readability
        """
    },
    
    "iv_percentile": {
        "title": "Implied Volatility Percentile",
        "content": """
IV Percentile shows where current implied volatility ranks vs historical range.

**Interpretation:**
- 0-20%: Low IV, options cheap, good for buying
- 20-50%: Below average, neutral bias
- 50-80%: Above average, elevated expectations
- 80-100%: High IV, options expensive, good for selling

**GEX Correlation:**
High negative GEX + High IV = Potential for explosive moves
High positive GEX + Low IV = Range-bound, collect premium
        """
    },
    
    "put_call_skew": {
        "title": "Put/Call Skew Analysis",
        "content": """
Skew measures the difference in implied volatility between puts and calls.

**Normal Skew (Puts > Calls):**
- Markets price in downside protection
- Natural state due to crash risk premium
- Steep put skew = fear of downside

**Reverse Skew (Calls > Puts):**
- Bullish sentiment or upside hedging
- Often seen before earnings or events
- Flat/inverted skew = complacency

**GEX Context:**
High put skew + negative GEX = Amplified downside risk
        """
    }
}

SIGNAL_INTERPRETATION_TEMPLATES = {
    "gamma_support": {
        "name": "Gamma Support Bounce",
        "description": "Price approaching positive GEX cluster",
        "why_triggered": "Price within {distance}% of high positive GEX strike at ${strike}",
        "expected_move": "Price likely to find support and bounce toward ${target}",
        "confidence_factors": [
            "Large positive GEX at nearby strikes",
            "Dealers must buy dips to hedge",
            "Mean-reversion dynamics active"
        ],
        "risk_factors": [
            "Break below GEX support invalidates thesis",
            "High volume sell-off can overwhelm gamma hedging",
            "News events can override technical levels"
        ],
        "historical_context": "Similar gamma support setups have {success_rate}% success rate"
    },
    
    "gamma_resistance": {
        "name": "Gamma Resistance",
        "description": "Price approaching negative GEX cluster",
        "why_triggered": "Price within {distance}% of high negative GEX strike at ${strike}",
        "expected_move": "Price likely to face resistance and reverse toward ${target}",
        "confidence_factors": [
            "Large negative GEX creates selling pressure",
            "Dealers must sell rallies to hedge",
            "Trend-following dynamics near flip point"
        ],
        "risk_factors": [
            "Break above resistance can trigger squeeze",
            "Low liquidity can cause gap moves",
            "Momentum can carry through gamma levels"
        ],
        "historical_context": "Gamma resistance holds {success_rate}% of the time in this regime"
    },
    
    "flip_approach": {
        "name": "Zero Gamma Flip Approach",
        "description": "Price approaching zero gamma level - regime change imminent",
        "why_triggered": "Price {distance}% from zero gamma flip at ${flip_level}",
        "expected_move": "Expect increased volatility. Above flip = stability, Below = trending",
        "confidence_factors": [
            "Dealer hedging behavior will reverse at flip",
            "Historical volatility expansion near flip",
            "Maximum uncertainty at zero gamma"
        ],
        "risk_factors": [
            "False breaks common near flip level",
            "Whipsaw action can stop out positions",
            "Time of day affects flip significance"
        ],
        "historical_context": "Volatility typically increases {vol_increase}% near flip levels"
    },
    
    "squeeze_potential": {
        "name": "Gamma Squeeze Potential",
        "description": "Conditions favorable for gamma squeeze",
        "why_triggered": "Negative GEX {gex_level}B + Price near {strike} strike OI {oi} contracts",
        "expected_move": "Potential for rapid {direction} acceleration if {trigger} breaks",
        "confidence_factors": [
            "Large negative gamma creates feedback loop",
            "High call OI above current price",
            "Dealers forced to chase price higher"
        ],
        "risk_factors": [
            "Requires sustained buying to maintain",
            "Can reverse violently when flow stops",
            "Timing difficult to predict"
        ],
        "historical_context": "Squeeze events average {avg_move}% move over {avg_duration} hours"
    },
    
    "pin_risk": {
        "name": "Pin Risk Warning",
        "description": "Price gravitating toward high GEX strike",
        "why_triggered": "High gamma concentration at ${strike} with {days} days to expiration",
        "expected_move": "Price likely to pin near ${strike} into expiration",
        "confidence_factors": [
            "Maximum gamma at strike creates magnet effect",
            "Dealer hedging reinforces pin",
            "Time decay increases pinning effect"
        ],
        "risk_factors": [
            "Large orders can break pin",
            "Late-day moves can invalidate",
            "News events override technicals"
        ],
        "historical_context": "Pins to max GEX strike occur {pin_rate}% of the time"
    }
}

DEALER_POSITIONING_EXPLANATIONS = {
    "short_gamma_flow": """
**Dealers are SHORT ${amount} million gamma**

This means for every $1 the stock moves:
- Dealers must trade ${hedge_ratio} shares to stay neutral
- On rallies: Forced buying amplifies upside
- On selloffs: Forced selling accelerates decline

**Position Management:**
Dealers want this to expire or be unwound. They will:
- Sell rallies (trying to reduce exposure)
- Buy dips (trying to reduce exposure)
- But forced to do opposite when price moves
    """,
    
    "long_gamma_flow": """
**Dealers are LONG ${amount} million gamma**

This means for every $1 the stock moves:
- Dealers naturally want to fade the move
- On rallies: They SELL (taking profits)
- On selloffs: They BUY (averaging down)

**Position Management:**
Dealers act as market stabilizers:
- Provide liquidity on both sides
- Mean-reversion behavior dominates
- Price tends to pin to high gamma strikes
    """,
    
    "hedge_visualization": {
        "title": "Dealer Hedging Flow",
        "short_gamma_up": "Stock ↑ → Delta ↑ → Dealers BUY → Stock ↑↑",
        "short_gamma_down": "Stock ↓ → Delta ↓ → Dealers SELL → Stock ↓↓",
        "long_gamma_up": "Stock ↑ → Dealers SELL → Stock stabilizes",
        "long_gamma_down": "Stock ↓ → Dealers BUY → Stock bounces"
    }
}

HELP_SCREEN_CONTENT = """
## GEX TERMINAL COMMANDS

**Navigation:**
- `<TICKER>` - Load any supported ticker (SPY, QQQ, NVDA, etc.)
- `GEX <TICKER>` - Show GEX profile for specific ticker
- `F1` - Show this help screen
- `ESC` - Close help or panels

**Views:**
- `HEATMAP` - Toggle GEX heatmap by strike and expiration
- `PROFILE` - Show GEX profile chart (default view)
- `ALERTS` - Show active gamma squeeze alerts
- `EDUCATION` - Show GEX learning panel

**Data:**
- `REFRESH` - Force data refresh (clears cache)
- `EXPORT` - Export current GEX data to CSV
- `SETTINGS` - Configure display preferences

**Quick Keys:**
- F2: GEX Profile
- F3: Heatmap
- F4: Market Profile
- F5: Alerts Panel
- F9-F12: Quick ticker buttons

**Understanding the Display:**

**GEX Profile Chart:**
- Green bars = Call GEX (positive)
- Red bars = Put GEX (negative)
- Orange line = Net GEX
- Yellow dashed line = Current price
- Orange dotted line = Zero gamma level

**Key Metrics:**
- **Zero GEX**: Price where gamma exposure flips sign
- **Max GEX**: Strike with highest gamma concentration
- **Total GEX**: Net gamma exposure in billions
- **P/C Ratio**: Put/Call gamma ratio

**Data Source Indicators:**
- POLYGON = Premium real-time data
- YFINANCE = Delayed/basic data
- Rate limit shows remaining API calls

**Color Coding:**
- Green = Positive/bullish signals
- Red = Negative/bearish signals
- Amber = Warnings/flip points
- Yellow = Price reference lines
"""

REGIME_EXPLANATIONS = {
    "positive_gamma": {
        "name": "POSITIVE GAMMA REGIME",
        "emoji": "🟢",
        "description": "Dealers are net long gamma - stabilizing force",
        "characteristics": [
            "Mean reversion favored",
            "Range-bound price action",
            "Volatility compression",
            "Pinning to strikes likely"
        ],
        "trading_implications": [
            "Sell premium / collect theta",
            "Fade moves outside range",
            "Expect false breakouts",
            "Iron condors perform well"
        ],
        "risk_level": "LOW TREND RISK / HIGH PIN RISK"
    },
    
    "negative_gamma": {
        "name": "NEGATIVE GAMMA REGIME",
        "emoji": "🔴",
        "description": "Dealers are net short gamma - amplifying force",
        "characteristics": [
            "Trend following favored",
            "Momentum accelerates",
            "Volatility expansion",
            "Breakouts can run"
        ],
        "trading_implications": [
            "Follow the trend",
            "Buy breakouts/sell breakdowns",
            "Use wider stops",
            "Long straddles perform well"
        ],
        "risk_level": "HIGH TREND RISK / LOW PIN RISK"
    },
    
    "zero_gamma": {
        "name": "ZERO GAMMA ZONE",
        "emoji": "⚠️",
        "description": "At the flip point - maximum uncertainty",
        "characteristics": [
            "Regime change imminent",
            "Dealer hedging reverses",
            "Volatility spike likely",
            "Choppy price action"
        ],
        "trading_implications": [
            "Reduce position size",
            "Wait for clarity",
            "Watch for breakout direction",
            "Straddles may pay off"
        ],
        "risk_level": "MAXIMUM UNCERTAINTY"
    }
}

# Tooltip texts for UI elements
TOOLTIPS = {
    "total_gex": "Total Gamma Exposure: Net of all call and put gamma across strikes",
    "zero_gamma": "Zero Gamma Level: Price where dealer gamma exposure equals zero",
    "max_gamma": "Max Gamma Strike: Strike with highest absolute gamma concentration",
    "pc_ratio": "Put/Call Ratio: Total put gamma divided by total call gamma",
    "spot_price": "Current Spot Price: Last traded price of underlying",
    "gex_profile": "GEX Profile: Gamma exposure distribution by strike price",
    "heatmap": "GEX Heatmap: Gamma exposure across strikes and expirations",
    "flip_distance": "Distance to Flip: How close price is to zero gamma level",
    "pin_risk": "Pin Risk: Likelihood price will gravitate to high GEX strike"
}

MARKET_MICROSTRUCTURE_GUIDE = {
    "expiration_countdown": {
        "title": "Options Expiration Impact",
        "content": """
As options approach expiration:
1. Gamma increases (higher delta sensitivity)
2. Pinning effect strengthens
3. Gamma squeeze potential rises
4. Dealer hedging becomes more urgent

**Trading Implications:**
- 0DTE (0 days to expiration): Maximum gamma, highest risk
- Weekly expiration: Strong pinning Friday afternoons
- Monthly expiration: Most significant (3rd Friday)
- Quarterly expiration: Jumbo expiration effects
        """
    },
    
    "largest_strikes": {
        "title": "Largest Gamma Strikes",
        "content": """
Strikes with highest gamma act as:
- Support/resistance levels
- Price magnets (pin risk)
- Potential squeeze triggers
- Liquidity concentrations

**How to Use:**
- Watch for bounces at large positive GEX strikes
- Expect resistance at large negative GEX strikes
- Note when price breaks through (regime change)
        """
    },
    
    "iv_gex_correlation": {
        "title": "IV vs GEX Correlation",
        "content": """
Relationship between implied volatility and gamma:

**High IV + Negative GEX:**
- Maximum squeeze potential
- Dealers short gamma during high uncertainty
- Explosive move risk elevated

**Low IV + Positive GEX:**
- Stable, range-bound conditions
- Dealers long gamma, providing stability
- Good environment for selling premium

**Divergences:**
- Rising IV with positive GEX = Fear without cause?
- Falling IV with negative GEX = Complacency risk
        """
    }
}