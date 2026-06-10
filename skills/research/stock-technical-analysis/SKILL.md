---
name: stock-technical-analysis
description: "Stock technical analysis with chart generation. Use when user asks for technical analysis, chart reading, support/resistance levels, indicator analysis (RSI, MACD, Bollinger, SMA), or visual charts for any stock. Covers both IDX (Indonesia) and US markets. Triggers: 'analisis teknikal', 'chart saham', 'technical analysis', 'support resistance', 'RSI MACD', 'candlestick', 'review saham', 'saham naik/turun'."
---

## What this is

Generate professional technical analysis reports with candlestick charts, oscillators, and trading signals. Combines data from multiple sources (Yahoo Finance, TradingView) and generates publication-ready chart images.

**Read-only analysis** — does NOT execute trades. For trade execution, route through governor.

---

## Data Sources & Priority

### 1. Yahoo Finance (via yfinance Python lib) — PRIMARY
- **Best for**: OHLCV data, fundamentals (P/E, EPS, market cap, beta), historical prices
- **Install**: `pip install yfinance mplfinance pandas matplotlib`
- **Usage**: See `references/data-sources.md` for patterns and pitfalls
- **Limitations**: Chart page is JS-rendered (won't work in headless browser); use yfinance lib instead

### 2. TradingView (via browser) — SECONDARY
- **Best for**: Technical consensus (Buy/Sell/Neutral from oscillators + moving averages), key stats
- **URL pattern**: `https://www.tradingview.com/symbols/{EXCHANGE}-{TICKER}/technicals/`
  - IDX: `https://www.tradingview.com/symbols/IDX-BBRI/technicals/`
  - NYSE/NASDAQ: `https://www.tradingview.com/symbols/NASDAQ-AAPL/technicals/`
- **Works in browser**: Yes, the technicals page renders static HTML (no WebGL needed)
- **Does NOT work in browser**: Full chart (`/chart/`) — requires WebGL/Canvas
- **Data available**: RSI, Stochastic, MACD, CCI, ADX, BB, pivot points, MA/EMA signals, oscillator summary

### 3. Yahoo Finance (via browser) — SUPPLEMENTARY
- **URL**: `https://finance.yahoo.com/quote/{TICKER}/`
- **Works in browser**: Summary page (price, volume, key stats)
- **Does NOT work**: Chart tab (JS-rendered), Financials (truncated in snapshot)

---

## Workflow

### Step 1: Gather Price Data
```python
import yfinance as yf
ticker = yf.Ticker("BBRI.JK")
df = ticker.history(period="6mo")  # 6 months daily
info = ticker.info  # fundamentals
```

### Step 2: Calculate Indicators & Generate Charts
See `scripts/generate_charts.py` for the complete reusable script:
- SMA (20, 50), EMA (12, 26), MACD (12, 26, 9)
- RSI (14), Bollinger Bands (20, 2), Pivot Points
- Candlestick + volume + SMA/BB overlay chart
- RSI subplot, MACD subplot
- Dark theme (nightclouds style)

See `references/data-sources.md` for data source details, exchange codes, and pitfalls.

### Step 4: Get TradingView Consensus
Navigate to TradingView technicals page in browser for oscillator/MA consensus summary.

### Step 5: Compose Analysis
Structure the output as:
1. **Price Summary** — current price, change, volume
2. **Price Structure** — trend, SMA position, death/golden cross
3. **Oscillators** — RSI, Stochastic, MACD, CCI values + interpretation
4. **Bollinger Bands** — position relative to bands
5. **Pivot Levels** — Pivot, R1-R2, S1-S2
6. **TradingView Consensus** — Summary gauge
7. **Reading** — synthesis + key levels + outlook
8. **Charts** — attach generated images

---

## Output Format

Use this structure for the analysis message:

```
📊 **[TICKER] TECHNICAL ANALYSIS — [Date]**
**Harga: Rp X,XXX (+X.XX%)**

━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **PRICE STRUCTURE**
• Trend: [uptrend/downtrend/consolidation]
• SMA 20: **X,XXX** — harga di [ATAS/BAWAH] → [bullish/bearish]
• SMA 50: **X,XXX** — harga di [ATAS/BAWAH] → [bullish/bearish]

📉 **OSCILLATORS**
• RSI (14): **XX.X** — [interpretation]
• MACD: **XXX** (Signal: XXX) — [bullish/bearish momentum]

📏 **BOLLINGER BANDS**
• Upper: **X,XXX** | Mid: **X,XXX** | Lower: **X,XXX**

🔑 **PIVOT LEVELS**
• Pivot: **X,XXX** | R1: **X,XXX** | S1: **X,XXX**

📊 **TRADINGVIEW CONSENSUS**
• Summary: **[BUY/SELL/NEUTRAL]** (X Buy, X Neutral, X Sell)

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 **READING:**
[Synthesis paragraph — 3-5 sentences]
[Key support/resistance levels]
[Outlook/scenarios]

MEDIA:/tmp/[ticker]_chart.png
MEDIA:/tmp/[ticker]_rsi.png
MEDIA:/tmp/[ticker]_macd.png
```

---

## Exchange Ticker Formats

| Exchange | yfinance | TradingView |
|---|---|---|
| Indonesia (IDX) | `BBRI.JK` | `IDX-BBRI` |
| US (NYSE/NASDAQ) | `AAPL`, `MSFT` | `NASDAQ-AAPL` |
| Hong Kong | `0700.HK` | `HKEX-0700` |
| Singapore | `D05.SI` | `SGX-D05` |

---

## Chart Generation Notes

- **mplfinance** `plot()` does NOT accept `dpi` kwarg — use `fig.savefig(..., dpi=150)` instead
- **execute_code** tool may be blocked in some sessions — use `write_file` + `terminal(python3 /tmp/script.py)` as fallback
- Charts are saved to `/tmp/` — include `MEDIA:/tmp/filename.png` in message to send
- Use `matplotlib.use('Agg')` before importing pyplot (headless rendering)
- Dark theme: `base_mpf_style='nightclouds'` with custom colors

---

## Trigger Phrases

`analisis teknikal`, `chart saham`, `technical analysis`, `support resistance`, `RSI MACD`, `candlestick`, `review saham`, `saham naik`, `saham turun`, `analisis chart`, `bikin chart`, `trading view`, `pivot point`, `bollinger band`, `moving average`

---

## Pitfalls

- Yahoo Finance chart page (`/chart/`) is JS-rendered — don't try to screenshot it in headless browser
- TradingView full chart requires WebGL — use `/technicals/` page instead for indicator data
- `yfinance` may return adjusted prices — use `auto_adjust=False` if you need raw prices
- Volume data can have NaN for some tickers — handle with `df['Volume'].fillna(0)`
- Indonesian tickers need `.JK` suffix in yfinance
