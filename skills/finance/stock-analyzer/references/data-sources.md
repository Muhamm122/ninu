# Yahoo Finance Data Sources — Quick Reference

## Accessible Pages (Verified June 2026)

### Summary Page (`/quote/TICKER.JK/`)
- Real-time price, change %, day range, volume
- Market cap, P/E, EPS, DY, Beta, 52W range
- Analyst target price, # analysts, recommendation
- Forward dividend & yield

### Holders Page (`/quote/TICKER.JK/holders/`)
- **Major Holders table**: Insider %, Institutions %, Float held by institutions, # of institutions
- **Top Institutional Holders table**: Holder name, shares held, date reported, % of outstanding, value
- **Top Mutual Fund Holders table**: Fund name, shares, date, %, value
- Navigation tabs: Major Holders | Insider Roster | Insider Transactions

### Financials Page (`/quote/TICKER.JK/financials/`)
- **Income Statement** (default): Total Revenue, Cost of Revenue, Gross Profit, Operating Expense, Operating Income, Pretax Income, Tax Provision, Net Income
- **Balance Sheet**: Total Assets, Total Liabilities, Shareholder Equity
- **Cash Flow**: Operating Cash Flow, Investing Cash Flow, Financing Cash Flow, Free Cash Flow
- Toggle: Annual | Quarterly
- Time range: TTM + 4 historical years

### Analysis Page (`/quote/TICKER.JK/analysis/`)
- **Earnings Trends**: EPS chart (actual vs estimate)
- **Revenue vs Earnings**: Quarterly breakdown
- **Revenue Estimate table**: Current Qtr, Next Qtr, Current Year, Next Year (with # analysts, avg/low/high estimates)
- **EPS Estimate table**: Same structure
- **Earnings History**: Past quarters with actual vs estimate

### Statistics Page (`/quote/TICKER.JK/statistics/`)
- ⚠️ **Redirects to Summary page** — not directly accessible
- For statistics data, use yfinance `ticker.info` dict instead

## TradingView Pages (Verified June 2026)

### Overview (`/symbols/IDX-TICKER/`)
- Key stats, multi-period performance (1D, 5D, 1M, 6M, YTD, 1Y, 5Y, 10Y, All)
- Market cap, P/E, EPS, DY, Beta, shares float, beta (1Y)
- Revenue (FY), Net income (FY), Employees

### Technicals (`/symbols/IDX-TICKER/technicals/`)
- **Oscillators**: RSI, Stochastic, CCI, MACD, Williams %R, Ultimate, Awesome, Bull Bear Power
- **Moving Averages**: SMA 10/20/50/100/200, EMA 10/20/50/100/200
- **Summary gauge**: Strong Buy / Buy / Neutral / Sell / Strong Sell with counts
- Timeframe selector: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1D, 1W, 1M

### News (`/symbols/IDX-TICKER/news/`)
- Latest headlines with timestamps
- Filter tabs: All, Earnings, Earnings calls, Press Releases, SEC Filings, Strategy/M&A, Analysts
- Provider attribution (e.g., "Trading Economics", "PR Newswire")

## Blocked Sources (Do NOT attempt)

| Site | Reason |
|---|---|
| investing.com | Cloudflare challenge, always blocks headless |
| idx.co.id | Cloudflare challenge |
| bi.go.id | Connection reset |
| Most broker sites (mncsekuritas, poems, etc.) | 403 Forbidden |

## yfinance Python Library Data Mapping

| Yahoo Finance Page | yfinance Method |
|---|---|
| Summary | `ticker.info` dict (trailingPE, trailingEps, marketCap, dividendYield, beta, targetMeanPrice, etc.) |
| Holders | `ticker.major_holders` (DataFrame), `ticker.institutional_holders` (DataFrame) |
| Financials | `ticker.financials` (annual), `ticker.quarterly_financials` |
| Analysis estimates | `ticker.info['revenueGrowth']`, `ticker.info['earningsGrowth']` |
| Quarterly earnings | `ticker.quarterly_earnings` (deprecated but still works) |
| Price history | `ticker.history(period="6mo")` |
| IHSG | `yf.Ticker("^JKSE").history(period="6mo")` |

## Data Freshness Notes

- yfinance `ticker.info` may lag real-time by 15-20 minutes during market hours
- For real-time price, prefer Yahoo Finance Summary page via browser
- `ticker.major_holders` may return incomplete data — browser scraping is more reliable
- `ticker.quarterly_earnings` shows deprecated warning but still returns data
- Analyst target price from `ticker.info['targetMeanPrice']` is usually current
