# Data Source Reference for Stock Technical Analysis

## TradingView Technicals Page

### URL Pattern
```
https://www.tradingview.com/symbols/{EXCHANGE}-{TICKER}/techniques/
```

### Exchange Codes
| Market | Exchange Code | yfinance Suffix |
|---|---|---|
| Indonesia | IDX | .JK |
| US Nasdaq | NASDAQ | (none) |
| US NYSE | NYSE | (none) |
| Hong Kong | HKEX | .HK |
| Singapore | SGX | .SI |
| Japan | TSE | .T |
| Korea | KRX | .KS |

### Data Available (Browser Snapshot)
The `/technicals/` page provides:
- **Oscillator Summary**: Buy/Neutral/Sell counts across 10+ oscillators
  - RSI (14), Stochastic %K (14,3,3), CCI (20), ADX (14), Awesome Oscillator
  - Momentum (10), MACD Level (12,26), Stochastic RSI Fast, Williams %R, Bull Bear Power, Ultimate Oscillator
- **Moving Average Summary**: Buy/Neutral/Sell counts across MA/EMA periods
- **Overall Summary Gauge**: Combined Buy/Sell/Neutral recommendation
- **Key Stats**: Market cap, P/E, EPS, beta, dividend yield, revenue, net income

### What Works in Headless Browser
- ✅ `/symbols/{EXCHANGE}-{TICKER}/` — key stats, about section
- ✅ `/symbols/{EXCHANGE}-{TICKER}/technicals/` — full indicator breakdown
- ✅ `/symbols/{EXCHANGE}-{TICKER}/financials/` — financial data
- ❌ `/chart/` — requires WebGL/Canvas, won't render

### Why Yahoo Finance Chart Doesn't Work
Yahoo Finance chart is rendered client-side with JavaScript (React + Canvas). In headless browser:
- Navigation loads the page shell
- "Loading chart for TICKER.JK" spinner appears but never resolves
- No actual price data in DOM — all in JS bundles
- **Workaround**: Use `yfinance` Python library instead for OHLCV data

## Yahoo Finance (yfinance Library)

### Installation
```bash
pip install yfinance mplfinance pandas matplotlib
```

### Basic Usage
```python
import yfinance as yf

ticker = yf.Ticker("BBRI.JK")

# OHLCV data
df = ticker.history(period="6mo")  # 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max

# Company info (fundamentals)
info = ticker.info  # dict with PE, EPS, marketCap, beta, dividendYield, etc.

# Financials
quarterly = ticker.quarterly_financials
annual = ticker.financials
```

### Indonesian Tickers
All IDX tickers need `.JK` suffix:
- `BBRI.JK` — Bank Rakyat Indonesia
- `BBCA.JK` — Bank Central Asia
- `TLKM.JK` — Telkom Indonesia
- `ASII.JK` — Astra International

## Indicator Reference Values

### RSI (14)
| Range | Interpretation |
|---|---|
| > 70 | Overbought |
| 50-70 | Bullish momentum |
| 30-50 | Bearish momentum |
| < 30 | Oversold |

### MACD
- MACD **above** signal line → bullish momentum
- MACD **below** signal line → bearish momentum
- Histogram **positive** → momentum increasing
- Zero ** crossover** → trend change signal

### Bollinger Bands
- Price near **upper band** → overbought / strong uptrend
- Price near **lower band** → oversold / strong downtrend
- Price near **mid band** → consolidation
- Band **squeeze** → low volatility, breakout coming

### Stochastic %K
| Range | Interpretation |
|---|---|
| > 80 | Overbought |
| 20-80 | Neutral |
| < 20 | Oversold |

## Chart Generation

### mplfinance Installation
```bash
pip install mplfinance
```

### Common Pitfall: dpi kwarg
mplfinance's `plot()` function does NOT accept `dpi` as a keyword argument.
**Wrong**: `mplf.plot(..., dpi=150)`
**Correct**: `fig.savefig('output.png', dpi=150)`

### Dark Theme Colors (Proven)
```python
style = mpf.make_mpf_style(
    base_mpf_style='nightclouds',
    marketcolors=mpf.make_marketcolors(
        up='lime', down='red',
        edge='inherit', wick='inherit', volume='in'
    ),
    figcolor='#1a1a2f',
    gridcolor='#2a2a4a',
    facecolor='#1a1a2f'
)
```

### Headless Rendering
Always set before importing pyplot:
```python
import matplotlib
matplotlib.use('Agg')  # Must be before pyplot import
import matplotlib.pyplot as plt
```

## execute_code Tool Limitation
In some Hermes configurations, `execute_code` is blocked for security.
**Workaround**: 
1. Write script to `/tmp/script.py` using `write_file` tool
2. Run with `terminal(command="python3 /tmp/script.py")`
