---
name: stock-analyzer
description: "Complete IDX stock analysis — teknikal (S/R multi-method, oscillators, MAs, BB, volume profile), fundamental (P/E, EPS, ROE, margins, analyst consensus, financials), ekonomi mikro (sector cycle, company-specific factors), ekonomi makro (real-time IHSG, S&P 500, Gold, Oil, BTC, VIX, US 10Y, USD/IDR), dan chart (candlestick+S/R, RSI, MACD). Single pipeline: stock_complete.py + stock_chart.py. Trigger: user sends any IDX ticker (e.g. BBCA, TLKM, BBRI) or says 'analisa X' / 'analyze X'."
---

# IDX Stock Analyzer

## Trigger

Activate when user sends:
- A bare IDX ticker: `BBCA`, `TLKM`, `BBRI`, `ADRO`, etc.
- Explicit request: `analisa BBCA`, `analyze TLKM`, `chart BBRI`, `saham BBCA`
- Comparison request: `bandingkan BBCA vs BBRI`, `compare TLKM BBRI`
- Alert check: `alert BBCA`, `sinyal TLKM`

**Do NOT activate** for general market questions without a specific ticker — use general knowledge instead.

## Support & Resistance Model

This is a **mandatory** section in every analysis. Compute S/R using multiple methods:

### Method 1: Pivot Points (Standard)
```
Pivot = (High + Low + Close) / 3
R1 = 2 × Pivot − Low
R2 = Pivot + (High − Low)
S1 = 2 × Pivot − High
S2 = Pivot − (High − Low)
```
Use the last completed trading day's H/L/C for daily pivots. For weekly, use last week's H/L/C.

### Method 2: Fibonacci Retracements
From the **most recent swing high to swing low** (or vice versa for uptrend):
```
Range = Swing High − Swing Low
23.6% retracement = High − Range × 0.236
38.2% retracement = High − Range × 0.382
50.0% retracement = High − Range × 0.500
61.8% retracement = High − Range × 0.618
78.6% retracement = High − Range × 0.786 (sqrt of 0.618)
```
These act as dynamic S/R zones. When 2+ fib levels cluster together → **strong zone**.

### Method 3: Volume Profile (Price Levels with High Volume)
Use `yfinance` daily data to find **volume-weighted price zones**:
1. Divide the 6-month range into 20 price bins
2. Sum volume traded at each bin
3. The top 3 bins by volume = **high-volume nodes (HVN)** → strong S/R
4. The bottom 3 bins by volume = **low-volume nodes (LVN)** → price moves fast through these

### Method 4: Historical Swing Highs/Lows (Multi-Timeframe)
Load price data and identify:
- **Major Resistance**: Last 3 swing highs that rejected price upward (within 2% of each other = confluence)
- **Major Support**: Last 3 swing lows that bounced price (within 2% of each other = confluence)
- Mark levels at: 20-day, 60-day, and 200-day swing points

### Method 5: Moving Average S/R
Dynamic support/resistance from MAs:
- SMA 20 (short-term trend S/R)
- SMA 50 (medium-term trend S/R)
- SMA 200 (long-term trend S/R — "make or break" level)
- EMA 12 (momentum S/R in fast moves)

### Method 6: Round Numbers (Psychological S/R)
Psychological levels act as magnets:
- For stocks > Rp 10,000: round thousands (10,000 / 11,000 / 12,000)
- For stocks Rp 1,000–10,000: round 500 and 1,000 (5,000 / 5,500 / 6,000)
- For stocks Rp 100–1,000: round 100 and 50 (500 / 600 / 700)

### S/R Confluence Scoring
When multiple methods identify the SAME price zone (±1% tolerance), that's a **confluence zone** — much stronger signal:

| Confluence Level | Methods Overlapping | Strength |
|---|---|---|
| 🔴 Extreme | 4+ methods | Major wall — expect strong reaction |
| 🟠 Strong | 3 methods | Significant S/R — plan entries around it |
| 🟡 Moderate | 2 methods | Notable level — watch for reaction |
| ⚪ Weak | 1 method | Reference only |

### S/R in Report Format
Always present in the report as:

```
🔑 SUPPORT & RESISTANCE ANALYSIS

📏 Static Levels (Pivot / Fib / Round):
• R3: X,XXX
• R2: X,XXX
• R1: X,XXX
• Pivot: X,XXX
• S1: X,XXX
• S2: X,XXX
• S3: X,XXX

📐 Fibonacci (Swing High X,XXX → Swing Low X,XXX):
• 23.6%: X,XXX
• 38.2%: X,XXX
• 50.0%: X,XXX
• 61.8%: X,XXX
• 78.6%: X,XXX

📊 Volume Profile:
• HVN (high volume): X,XXX — X,XXX
• LVN (low volume): X,XXX — X,XXX
• POC (point of control): X,XXX

📈 Dynamic Levels (MAs):
• SMA 20: X,XXX
• SMA 50: X,XXX
• SMA 200: X,XXX

🔴 EXTREME Confluence (4+ methods): X,XXX — X,XXX
🟠 STRONG Confluence (3 methods): X,XXX
🟡 MODERATE Confluence (2 methods): X,XXX

52W Range Position: XX% (near bottom/top/middle)
```

### S/R Breach Rules
When price approaches a confluence zone (within 1%):
- If STRONG BUY signal + price at strong SUPPORT → highlight as "prime entry zone"
- If STRONG SELL signal + price at strong RESISTANCE → highlight as "prime exit zone"
- If price breaks through a confluence zone with volume > 1.5x avg → "breakout/breakdown confirmed" → next S/R level becomes target

## Data Sources (Verified Accessible)

| Source | URL Pattern | Data Available | Blocked? |
|---|---|---|---|
| Yahoo Finance Summary | `finance.yahoo.com/quote/TICKER.JK/` | Price, P/E, EPS, DY, Beta, 52W, analyst target, market cap | ❌ No |
| Yahoo Finance Financials | `finance.yahoo.com/quote/TICKER.JK/financials/` | Revenue, Gross Profit, Operating Income, Net Income (annual + quarterly) | ❌ No |
| Yahoo Finance Analysis | `finance.yahoo.com/quote/TICKER.JK/analysis/` | EPS/Revenue estimates, # analysts, earnings history table | ❌ No |
| Yahoo Finance Holders | `finance.yahoo.com/quote/TICKER.JK/holders/` | Insider %, Institutions %, Float held by inst, # of institutions, top holders table | ❌ No |
| Yahoo Finance IHSG | `finance.yahoo.com/quote/%5EJKSE/` | Index level, change %, 52W range | ❌ No |
| Yahoo Finance Statistics | `finance.yahoo.com/quote/TICKER.JK/statistics/` | ⚠️ Redirects to Summary page — not directly accessible | ⚠️ Redirect |
| TradingView Overview | `tradingview.com/symbols/IDX-TICKER/` | Key stats, multi-period perf (1D/1M/6M/YTD/1Y/5Y/10Y/All) | ❌ No |
| TradingView News | `tradingview.com/symbols/IDX-TICKER/news/` | Earnings headlines, company developments, analyst actions | ❌ No |
| TradingView Technicals | `tradingview.com/symbols/IDX-TICKER/technicals/` | Oscillator consensus, MA consensus, overall rating (buy/sell/neutral counts) | ❌ No |
| yfinance (Python) | `yfinance` library | Price data, info dict, financials DataFrame, institutional_holders, major_holders, quarterly_earnings | ❌ No |
| IDX Official | `www.idx.co.id/` | Volume, foreign flow | ✅ Yes (Cloudflare) |
| BI Website | `www.bi.go.id/` | Interest rate, policy | ✅ Yes (connection reset) |
| Broker Sites | Various | Research reports, target prices | ✅ Yes (403/Cloudflare) |
| Investing.com | `investing.com/equities/...` | Target price, consensus, financials | ✅ Yes (Cloudflare) |

### Yahoo Finance Browser Scraping Notes

When yfinance API data is incomplete or stale, use `browser_navigate` to Yahoo Finance pages:

**Holders Page** (`/holders/`):
- Extract: "Major Holders" table (insider %, institutions %, float held, # institutions)
- Extract: "Top Institutional Holders" table (holder name, shares, date, % out, value)
- Extract: "Top Mutual Fund Holders" table
- yfinance `ticker.major_holders` returns a DataFrame but may be incomplete — browser is more reliable

**Financials Page** (`/financials/`):
- Extract: Income Statement table (TTM + 4 annual columns)
- Key rows: Total Revenue, Cost of Revenue, Gross Profit, Operating Expense, Operating Income, Net Income
- Switch between Annual/Quarterly tabs for different granularity
- yfinance `ticker.financials` returns similar data but browser shows more detail

**Analysis Page** (`/analysis/`):
- Extract: "Revenue Estimate" table (current/next quarter, current/next year with # analysts)
- Extract: "Earnings Per Share" chart data
- Extract: "Revenue vs. Earnings" quarterly breakdown
- Cross-check yfinance `ticker.info['revenueEstimates']` with browser data

**TradingView Technicals Page** (`/technicals/`):
- Extract: Oscillator summary (RSI, Stochastic, CCI, MACD, etc. with Buy/Sell/Neutral counts)
- Extract: Moving Average summary (SMA/EMA with Buy/Sell counts)
- Extract: Overall Summary gauge (Strong Buy / Buy / Neutral / Sell / Strong Sell)
- Use as cross-check with script-calculated signals

## Pipeline (MANDATORY — every ticker analysis MUST follow this)

### Step 1: Resolve Ticker

- If user sends bare uppercase word → treat as IDX ticker, append `.JK`
- If user sends `.JK` suffix → use as-is
- If ambiguous (e.g. "BRI") → clarify: "Maksud lo BBRI.JK?"
- If US/international ticker → use as-is without `.JK`

### Step 2: Run Complete Analysis (Single Script — ALL sections)

```bash
python3 ~/.hermes/scripts/stock_complete.py TICKER [period]
```

This single script provides ALL 8 sections in one run:
- **I. FUNDAMENTAL**: P/E, Fwd P/E, EPS, Fwd EPS, P/B, ROE, D/E, margins, growth, analyst consensus, financials
- **II. PERFORMANCE**: 1W, 1M, 3M, 6M, YTD, 1Y, IHSG comparison, alpha
- **III. TECHNICAL**: RSI, MACD, SMA 20/50/200, BB, Stochastic, ATR
- **IV. SUPPORT & RESISTANCE**: Pivot points, Fibonacci, volume profile, swing points, confluence zones
- **V. SIGNALS**: Score-based detection with overall rating
- **VI. TRADE PLAN**: Entry zone, stop loss, targets
- **VII. EKONOMI MIKRO**: Sector cycle, key drivers, company-specific factors (valuation, growth, profitability, balance sheet, dividend, 52W position, volume)
- **VIII. EKONOMI MAKRO**: Real-time Indonesia macro (IHSG, BI rate, GDP, inflation, fiscal, rupiah), global macro (S&P 500, VIX, Gold, Oil, BTC, US 10Y), sector-specific macro impact

Default period is `6mo`. Script may show DeprecationWarning for `Ticker.earnings` — expected, handled gracefully.

### Step 3: Generate Charts (MANDATORY — ALWAYS run, NEVER skip)

```bash
python3 ~/.hermes/scripts/stock_chart.py TICKER 6mo
```

**⚠️ USER REQUIREMENT: Every ticker analysis MUST include charts. Never send analysis without charts.**

Produces 3 files:
- `/{TICKER}_chart.png` — candlestick + SMA 20/50 + BB + S/R horizontal lines + swing point markers
- `/{TICKER}_rsi.png` — RSI (14) with overbought/oversold zones
- `/{TICKER}_macd.png` — MACD (12,26,9) with histogram

**Chart generation takes 30-45s** — use `timeout=45`.

**If chart generation fails:** Send analysis without charts + note "⚠️ Chart gagal di-generate."

### Step 4: Send Report + Charts

Send analysis text FIRST, then attach all 3 chart images:
```
MEDIA:/tmp/{TICKER}_chart.png
MEDIA:/tmp/{TICKER}_rsi.png
MEDIA:/tmp/{TICKER}_macd.png
```

Structure the output as follows:

```
📊 **[TICKER] COMPREHENSIVE ANALYSIS**
**Harga: Rp X,XXX (+/-X.XX%)** | Market Open/Close
**Sector: XXX | Industry: XXX**

═══════════════════════════════════════

**I. FUNDAMENTAL**
• P/E: X.XX | Fwd P/E: X.XX (→ cheaper/more expensive going forward)
• EPS: Rp XXX | Fwd EPS: Rp XXX (→ growth trajectory)
• P/B: X.XX | ROE: XX% | D/E: XX
• Div Yield: X.XX% | Beta: X.XX
• Profit Margin: XX% | Op Margin: XX%
• Revenue Growth: XX% | Earnings Growth: XX%
• Market Cap: Rp XXXT

📌 **Analyst Consensus:**
• Target Price: Rp X,XXX (Low: X,XXX | High: X,XXX)
• # Analysts: XX | Consensus: buy/hold/sell
• Implication: XX% upside/downside from current

═══════════════════════════════════════

**II. PERFORMANCE**
• 1W: +X.X% | 1M: +X.X% | 3M: +X.X%
• 6M: +X.X% | YTD: +X.X% | 1Y: +X.X%
• IHSG 6M: +X.X% | **Alpha vs IHSG: +X.X%** (outperform/underperform)
• 52W Range: X,XXX — X,XXX (posisi: XX% — near bottom/middle/top)

═══════════════════════════════════════

**III. TECHNICAL**
• Trend: Uptrend / Downtrend / Sideways
• SMA 20: X,XXX | SMA 50: X,XXX | SMA 200: X,XXX
• Golden Cross ✅ / Death Cross ❌
• RSI (14): XX.X (oversold <30 / overbought >70 / neutral)
• MACD: XX.X (Signal: XX.X) — bullish/bearish
• Stochastic: XX — zone
• BB: Upper X,XXX | Mid X,XXX | Lower X,XXX
• TradingView Consensus: Summary X / MA X / Oscillators X

═══════════════════════════════════════

**IV. SUPPORT & RESISTANCE (Multi-Method)**

📏 Pivot Points:
• R3: X,XXX | R2: X,XXX | R1: X,XXX
• Pivot: X,XXX
• S1: X,XXX | S2: X,XXX | S3: X,XXX

📐 Fibonacci (Swing High X,XXX → Swing Low X,XXX):
• 23.6%: X,XXX | 38.2%: X,XXX | 50.0%: X,XXX | 61.8%: X,XXX | 78.6%: X,XXX

📊 Volume Profile:
• POC: X,XXX | HVN: X,XXX, X,XXX | LVN: X,XXX, X,XXX

📈 Dynamic (MAs):
• SMA 20: X,XXX | SMA 50: X,XXX | SMA 200: X,XXX

🔑 Swing Points:
• Highs: X,XXX, X,XXX, X,XXX
• Lows: X,XXX, X,XXX, X,XXX

🔴 EXTREME Confluence (4+ methods): X,XXX
🟠 STRONG Confluence (3 methods): X,XXX
🟡 MODERATE Confluence (2 methods): X,XXX

📍 Current Position: Price is at [S1/Pivot/R1] zone, [X%] above/below [nearest S/R]
🔄 S/R Status: [Holding / Tested / Broken] at [level]

═══════════════════════════════════════

**V. SIGNAL DETECTION**
• Overall: 🟢🟢 STRONG BUY / 🟢 BUY / 🟡 MILD BUY / ⚪ NEUTRAL / 🟠 MILD SELL / 🔴 SELL / 🔴🔴 STRONG SELL
• Score: X
• Signals:
  - [BUY/SELL] Reason
  - [BUY/SELL] Reason

═══════════════════════════════════════

**VI. TRADE PLAN**
• Entry Zone: X,XXX — X,XXX
• Stop Loss: X,XXX (-X.X%)
• Target 1: X,XXX (+X.X%)
• Target 2: X,XXX (+X.X%)
• Target 3: X,XXX (+X.X%)
• Analyst Target: X,XXX (+X.X%)
• Risk/Reward: X.X:1

═══════════════════════════════════════

**VII. MACRO & SENTIMEN**

📌 Indonesia:
• BI Rate: 5.75% (easing cycle)
• GDP: ~5.0-5.2% | Inflation: ~2.5-3.0%
• Fiscal: MBG, Danantara, KUR subsidies
• Rupiah: ~16,500-17,000

📌 Global:
• S&P Futures: X,XXX (-X.XX%) | VIX: XX.XX (+X.X%)
• Gold: $X,XXX | Oil: $XX | BTC: $XX,XXX
• Sentiment: risk-on / risk-off

═══════════════════════════════════════

**VIII. SWOT**

✅ Strengths: ...
⚠️ Weaknesses: ...
🔵 Opportunities: ...
🔴 Threats: ...

═══════════════════════════════════════

**IX. OUTLOOK & KESIMPULAN**
• Fundamental: BULLISH/BEARISH (reason)
• Technical: BULLISH/BEARISH/BOTTOMING (reason)
• Sentiment: POSITIVE/NEGATIVE/MIXED

📌 Skenario:
• Bull (XX%): catalyst → target
• Base (XX%): range
• Bear (XX%): risk → target

📌 REKOMENDASI:
• Holder: HOLD/BUY MORE/SELL (reason)
• New entry: ACCUMULATE/WAIT at range
• Stop loss: below X,XXX
• Target: X,XXX — X,XXX
• Catalysts to watch: earnings, BI rate, etc.

📎 Charts attached: candlestick + S/R, RSI, MACD
⚠️ *Disclaimer: Analisis bukan rekomendasi. DYOR.*
```

### Step 8: Send Charts (MANDATORY)

Attach all 3 chart images:
- `MEDIA:/tmp/{TICKER}_chart.png`
- `MEDIA:/tmp/{TICKER}_rsi.png`
- `MEDIA:/tmp/{TICKER}_macd.png`

**IMPORTANT:** Charts MUST be sent together with the analysis text. Never send analysis without charts unless chart generation fails.

```
📊 **[TICKER] COMPREHENSIVE ANALYSIS**
**Harga: Rp X,XXX (+/-X.XX%)** | Market Open/Close
**Sector: XXX | Industry: XXX**

═══════════════════════════════════════

**I. FUNDAMENTAL**
• P/E: X.XX | Fwd P/E: X.XX (→ cheaper/more expensive going forward)
• EPS: Rp XXX | Fwd EPS: Rp XXX (→ growth trajectory)
• P/B: X.XX | ROE: XX% | D/E: XX
• Div Yield: X.XX% | Beta: X.XX
• Profit Margin: XX% | Op Margin: XX%
• Revenue Growth: XX% | Earnings Growth: XX%
• Market Cap: Rp XXXT

📌 **Analyst Consensus:**
• Target Price: Rp X,XXX (Low: X,XXX | High: X,XXX)
• # Analysts: XX | Consensus: buy/hold/sell
• Implication: XX% upside/downside from current

═══════════════════════════════════════

**II. PERFORMANCE**
• 1W: +X.X% | 1M: +X.X% | 3M: +X.X%
• 6M: +X.X% | YTD: +X.X% | 1Y: +X.X%
• IHSG 6M: +X.X% | **Alpha vs IHSG: +X.X%** (outperform/underperform)
• 52W Range: X,XXX — X,XXX (posisi: XX% — near bottom/middle/top)

═══════════════════════════════════════

**III. TECHNICAL**
• Trend: Uptrend / Downtrend / Sideways
• SMA 20: X,XXX | SMA 50: X,XXX | SMA 200: X,XXX
• Golden Cross ✅ / Death Cross ❌
• RSI (14): XX.X (oversold <30 / overbought >70 / neutral)
• MACD: XX.X (Signal: XX.X) — bullish/bearish
• Stochastic: XX — zone
• BB: Upper X,XXX | Mid X,XXX | Lower X,XXX
• TradingView Consensus: Summary X / MA X / Oscillators X

═══════════════════════════════════════

**IV. SUPPORT & RESISTANCE (Multi-Method)**

📏 Pivot Points:
• R3: X,XXX | R2: X,XXX | R1: X,XXX
• Pivot: X,XXX
• S1: X,XXX | S2: X,XXX | S3: X,XXX

📐 Fibonacci (Swing High X,XXX → Swing Low X,XXX):
• 23.6%: X,XXX | 38.2%: X,XXX | 50.0%: X,XXX | 61.8%: X,XXX | 78.6%: X,XXX

📊 Volume Profile:
• POC: X,XXX | HVN: X,XXX, X,XXX | LVN: X,XXX, X,XXX

📈 Dynamic (MAs):
• SMA 20: X,XXX | SMA 50: X,XXX | SMA 200: X,XXX

🔑 Swing Points:
• Highs: X,XXX, X,XXX, X,XXX
• Lows: X,XXX, X,XXX, X,XXX

🔴 EXTREME Confluence (4+ methods): X,XXX
🟠 STRONG Confluence (3 methods): X,XXX
🟡 MODERATE Confluence (2 methods): X,XXX

📍 Current Position: Price is at [S1/Pivot/R1] zone, [X%] above/below [nearest S/R]
🔄 S/R Status: [Holding / Tested / Broken] at [level]

═══════════════════════════════════════

**V. SIGNAL DETECTION**
• Overall: 🟢🟢 STRONG BUY / 🟢 BUY / 🟡 MILD BUY / ⚪ NEUTRAL / 🟠 MILD SELL / 🔴 SELL / 🔴🔴 STRONG SELL
• Score: X
• Signals:
  - [BUY/SELL] Reason
  - [BUY/SELL] Reason

═══════════════════════════════════════

**VI. TRADE PLAN**
• Entry Zone: X,XXX — X,XXX
• Stop Loss: X,XXX (-X.X%)
• Target 1: X,XXX (+X.X%)
• Target 2: X,XXX (+X.X%)
• Target 3: X,XXX (+X.X%)
• Analyst Target: X,XXX (+X.X%)
• Risk/Reward: X.X:1

═══════════════════════════════════════

**VII. MACRO & SENTIMEN**

📌 Indonesia:
• BI Rate: 5.75% (easing cycle)
• GDP: ~5.0-5.2% | Inflation: ~2.5-3.0%
• Fiscal: MBG, Danantara, KUR subsidies
• Rupiah: ~16,500-17,000

📌 Global:
• S&P Futures: X,XXX (-X.XX%) | VIX: XX.XX (+X.X%)
• Gold: $X,XXX | Oil: $XX | BTC: $XX,XXX
• Sentiment: risk-on / risk-off

═══════════════════════════════════════

**VIII. SWOT**

✅ Strengths: ...
⚠️ Weaknesses: ...
🔵 Opportunities: ...
🔴 Threats: ...

═══════════════════════════════════════

**IX. OUTLOOK & KESIMPULAN**
• Fundamental: BULLISH/BEARISH (reason)
• Technical: BULLISH/BEARISH/BOTTOMING (reason)
• Sentiment: POSITIVE/NEGATIVE/MIXED

📌 Skenario:
• Bull (XX%): catalyst → target
• Base (XX%): range
• Bear (XX%): risk → target

📌 REKOMENDASI:
• Holder: HOLD/BUY MORE/SELL (reason)
• New entry: ACCUMULATE/WAIT at range
• Stop loss: below X,XXX
• Target: X,XXX — X,XXX
• Catalysts to watch: earnings, BI rate, etc.

📎 Charts attached: candlestick + S/R, RSI, MACD
⚠️ *Disclaimer: Analisis bukan rekomendasi. DYOR.*
```

### Step 7: Send Charts

Attach all 3 chart images:
- `MEDIA:/tmp/{TICKER}_chart.png`
- `MEDIA:/tmp/{TICKER}_rsi.png`
- `MEDIA:/tmp/{TICKER}_macd.png`

## Alert System

After generating the analysis, check for **STRONG signals**:

| Condition | Alert Level | Action |
|---|---|---|
| Score >= 5 | 🟢🟢 STRONG BUY | Pin/emphasize prominently |
| Score <= -5 | 🔴🔴 STRONG SELL | Pin/emphasize prominently |
| Score 3-4 | 🟢 BUY | Highlight in summary |
| Score -3 to -4 | 🔴 SELL | Highlight in summary |
| RSI < 20 or > 80 | Extreme | Add ⚠️ warning |
| Golden/Death Cross | Critical | Add 🔥 alert |
| Volume spike > 2x avg | Significant | Add 📊 note |
| MACD fresh crossover | Significant | Add 📈 note |

If STRONG BUY or STRONG SELL detected, prefix the report with:
```
🚨 ALERT: [STRONG BUY/SELL] [TICKER] 🚨
Score: X | Signal count: N
```

## Comparison Mode

If user asks to compare 2-3 tickers:
1. Run signal detection for each
2. Run chart generation for each
3. Create a comparison table:

```
Metric     | Ticker A | Ticker B | Ticker C
-----------|----------|----------|--------
Price      |          |          |
P/E        |          |          |
RSI        |          |          |
Signal     |          |          |
Entry      |          |          |
DY         |          |          |
```

4. Send individual charts for each ticker
5. Give overall ranking and preference

## Changelog Mode

If ticker followed by "1M", "1Y", "YTD", or "5Y":
- Adjust chart period: `stock_chart.py TICKER 1mo` / `1y` / `ytd` / `5y`
- Keep other analysis the same

## Error Handling

- If `yfinance` returns empty data → "Data untuk [TICKER] tidak tersedia. Cek ulang ticker."
- If chart generation fails → send analysis without charts, note "Chart gagal di-generate."
- If Yahoo Finance page fails → rely on signal script output + TradingView + general knowledge
- If ambiguous ticker → ask user to clarify before proceeding

## Tips

- BBRI, BBCA, BMRI, BBNI = big 4 banks (always have `.JK`)
- ADRO, PTBA, ANTM = commodity mining
- TLKM, EXCL, FREN = telco
- UNVR, ICBP, INDF = consumer
- GOTO, BUKA = tech
- If user sends BMRI instead of BMRI.JK, auto-append `.JK`
- For US tickers (AAPL, TSLA, NVDA, etc.), don't append `.JK`
- **⚠️ ALWAYS send charts as MEDIA attachments** — user explicitly requires charts with every ticker analysis. Never send analysis without charts unless chart generation fails.
- **Pipeline order**: Run `stock_complete.py` first (analysis), then `stock_chart.py` (charts). Both are mandatory.
- **Chart generation takes 30-45s** — use `timeout=45`. If timeout, send analysis without charts and note "Chart gagal di-generate."
- **Do NOT attempt to scrape investing.com** — it always blocks with Cloudflare challenge
- **Yahoo Finance Statistics page redirects to Summary** — use yfinance `ticker.info` for statistics data
- **Group chat IDs**: SAHAM=-1003773927697, Trading=-1004295492283, Haus Living=-1003952018713, Pengaturan Agent=-1004298792270
- **Data sources**: Yahoo Finance + TradingView are the only reliable accessible sources. BI, BPS, TradingEconomics, Investing.com, CNBC all blocked.
- **Economic mikro/makro**: Built into `stock_complete.py` — includes sector-specific micro analysis + real-time macro data (IHSG, S&P 500, Gold, Oil, BTC, VIX, US 10Y, USD/IDR) via yfinance tickers. See `references/economic-framework.md` for sector classification table and micro analysis framework.
- **Real-time macro**: Script scrapes ^JKSE, ^GSPC, GC=F, BZ=F, BTC-USD, USDIDR=X, ^TNX, ^VIX via yfinance for live macro snapshot
- **One pipeline**: teknikal + fundamental + mikro + makro ALL in one `stock_complete.py` run — no need for separate scripts unless user wants lighter analysis (then use `stock_deep.py`)
