# Yahoo Finance API v8 (Unofficial)

Reverse-proxied through Nginx at `/api/yahoo/` on VPS to bypass CORS.

## Endpoints

### Chart Data (primary)
```
GET /v8/finance/chart/{SYMBOL}?range={RANGE}&interval={INTERVAL}
```

**Parameters**:
| Param | Values |
|-------|--------|
| `range` | `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `max` |
| `interval` | `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1wk`, `1mo` |

**Response structure**:
```json
{
  "chart": {
    "result": [{
      "meta": {
        "currency": "IDR",
        "symbol": "BBRI.JS",
        "regularMarketPrice": 2780,
        "previousClose": 2800,
        "regularMarketTime": 1719475200
      },
      "timestamp": [1719302400, ...],
      "indicators": {
        "quote": [{
          "open": [2800, ...],
          "high": [2820, ...],
          "low": [2760, ...],
          "close": [2780, ...],
          "volume": [12345678, ...]
        }],
        "adjclose": [{"adjclose": [2780, ...]}]
      }
    }]
  }
}
```

### IDX Ticker Format
- BBRI.JK, BMRI.JK, BBTN.JK, BJTM.JK
- TLKM.JK, ASII.JK, INTP.JK, PGAS.JK, DMAS.JK, TOWR.JK
- SIDO.JK, HMSP.JK, UNVR.JK, ICBP.JK, KLBF.JK

### Global Symbols (no suffix)
- `^JKSE` — IHSG (may fail from some IPs)
- `^GSPC` — S&P 500
- `GC=F` — Gold futures
- `BZ=F` — Crude Oil (WTI)
- `CL=F` — Crude Oil (Brent)
- `USDIDR=X` — USD/IDR rate
- `^TNX` — US 10-Year Treasury
- `^VIX` — VIX volatility index
- `BTC-USD` — Bitcoin
- `ETH-USD` — Ethereum

## Derived Metrics (computed in JS)

```javascript
const closes = quote.close.filter(x => x);
const last = closes[closes.length - 1];
const prev = closes[closes.length - 2];
const changePct = ((last - prev) / prev) * 100;
const high52 = Math.max(...quote.high.filter(x => x));
const low52 = Math.min(...quote.low.filter(x => x));

// RSI (14-period)
const changes = closes.slice(1).map((c, i) => c - closes[i]);
const gains = changes.map(x => x > 0 ? x : 0);
const losses = changes.map(x => x < 0 ? -x : 0);
const avgGain = gains.slice(-14).reduce((a, b) => a + b) / 14;
const avgLoss = losses.slice(-14).reduce((a, b) => a + b) / 14;
const rs = avgLoss > 0 ? avgGain / avgLoss : 100;
const rsi = 100 - (100 / (1 + rs));

// SMA
const sma20 = closes.slice(-20).reduce((a, b) => a + b) / 20;
const sma50 = closes.slice(-50).reduce((a, b) => a + b) / 50;

// MACD
const ema12 = closes.slice(-12).reduce((a, b) => a + b) / 12;
const ema26 = closes.slice(-26).reduce((a, b) => a + b) / 26;
const macd = ema12 - ema26;

// Bollinger Bands (20, 2σ)
const bbMean = sma20;
const bbStd = Math.sqrt(closes.slice(-20).reduce((s, c) => s + (c - bbMean) ** 2, 0) / 20);
const bbUpper = bbMean + 2 * bbStd;
const bbLower = bbMean - 2 * bbStd;

// Support/Resistance (classic pivot)
const pivot = (high + low + close) / 3;
const s1 = 2 * pivot - high;
const s2 = pivot - (high - low);
const r1 = 2 * pivot - low;
const r2 = pivot + (high - low);
```

## Nginx Proxy Config

```nginx
location /api/yahoo/ {
    rewrite ^/api/yalm/(.*) /$1 break;
    proxy_pass https://query1.finance.yahoo.com/;
    proxy_http_version 1.1;
    proxy_set_header Host query1.finance.yahoo.com;
    proxy_set_header User-Agent "Mozilla/5.0 (X11; Linux x86_64)";
    proxy_ssl_server_name on;
    proxy_set_header X-Real-IP $remote_addr;
    # Reduce rate-limit hits
    proxy_cache_path /tmp/yahoo_cache levels=1:2 keys_zone=yahoo:10m max_size=50m inactive=5m;
    proxy_cache yahoo;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$uri$is_args$args";
    add_header X-Cache-Status $upstream_cache_status;
}
```

## Batch Fetching Pattern (rate-limit friendly)

```javascript
const SC_UNIVERSE = ['BBRI','BMRI','BBTN','BJTM','TLKM',...];
async function batchFetch() {
  const results = [];
  const batchSize = 8;
  for (let i = 0; i < SC_UNIVERSE.length; i += batchSize) {
    const batch = SC_UNIVERSE.slice(i, i + batchSize);
    const data = await Promise.all(batch.map(t => fetchChart(t)));
    results.push(...data);
    // Show progress
    updateProgress(i + batchSize, SC_UNIVERSE.length);
  }
  return results;
}
```

## Pitfalls

1. **CORS always blocks browser→Yahoo direct** — must proxy through your own server
2. **`^JKSE` often 404 or timeout** — Yahoo treats it inconsistently; use `^JSE` or cache stale fallback
3. **Volume filter** — `null` values in arrays (weekends/holidays); always `.filter(x => x)`
4. **429 rate limit** — batches of 6-8 concurrent max; add Nginx cache; add delay between batches
5. **`.JS` vs `.JK` suffix** — Yahoo accepts both but `.JK` is standard for Jakarta exchange
鸡精. **No fundamental data in v8 chart** — P/E, ROE, market cap require separate scraping or mock data
