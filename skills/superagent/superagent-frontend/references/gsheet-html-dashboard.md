---
name: gsheet-html-dashboard
description: Google Apps Script HTML service dashboard — single-file dashboard that reads from a Google Sheet via Code.gs backend. Inlined Chart.js, 5min server-side cache, mock google.script.run for local testing. Use when user wants a dashboard inside Google Sheets with no separate server, no hosting, no domain.
---

# Google Apps Script HTML Service Dashboard Pattern

A **dashboard that lives inside a Google Sheet** — no separate server, no hosting, no domain. The HTML is served by Apps Script's `HtmlService`, reads data from the same sheet via `google.script.run`, and renders with inlined Chart.js. Setup takes 5 minutes, deploy is one click.

Use this when:
- User's source of truth is a Google Sheet (financial tracker, project log, inventory, attendance)
- User wants zero infra (no VPS, no domain, no hosting)
- User wants to share via GSheet editor/viewer permissions
- The dashboard has <5000 rows (Apps Script has execution time limits)

Don't use this when:
- Real-time data needed (Apps Script is request/response, no streaming)
- Sheet is private/restricted and gviz doesn't work — but if user can share, this works
- User needs >50K rows (Apps Script will hit quotas)
- Multi-user concurrent writes (Apps Script has race conditions on `setValue`)

---

## Architecture

```
Google Sheet (user's data)
    ↓
Code.gs (Apps Script backend, ~400-700 lines)
    ├── onOpen()                    → adds custom menu to sheet
    ├── doGet()                     → serves Index.html
    ├── getDashboardData()          → reads sheet, returns JSON
    ├── setupSampleData()           → seeds sample for testing
    └── CacheService (5min TTL)     → avoids re-reading sheet on every render
    ↓
Index.html (single-file dashboard, ~200-300 KB with Chart.js inlined)
    ├── Chart.js (inlined, no CDN)
    ├── <?!= include('CSS') ?>      → optional separate CSS file
    └── <script>
          google.script.run
            .withSuccessHandler(render)
            .withFailureHandler(showError)
            .getDashboardData();
        </script>
```

Deploy: **Publish → Deploy as web app** (or just "Test deployments" for personal use). Anyone with edit access to the sheet can run the script.

---

## Field name conventions (Indonesian Sheets)

Apps Script reads sheet rows with `getRange().getValues()` and converts to objects with the first row as keys. Match Indonesian headers in the sheet to keep the data flow trivial:

| Sheet column | Type | Example |
|--------------|------|---------|
| `tanggal` | date string | `2026-06-01` |
| `kategori` | string | `Makan`, `Transport`, `Gaji` |
| `deskripsi` | string | `Makan siang warteg` |
| `jumlah` | number (no separator) | `50000` |
| `tipe` | enum | `income` / `expense` / `transfer` |
| `akun` | string | `BCA`, `Cash`, `GoPay` |
| `sumber_aset` | enum | `saham`, `reksa_dana`, `crypto`, `deposito`, `properti`, `emas` |
| `nama_instrumen` | string | `BBCA`, `ETH`, `Reksa Dana Money Market` |
| `nominal` | number | `10000000` |
| `return_pct` | number | `12.5` (annualized) |
| `tanggal_beli` | date | `2024-01-15` |
| `platform` | string | `IPOT`, `Pluang`, `Binance` |

Header row should be **row 1**, data starts row 2. Apps Script `getDataRange().getValues()` returns the whole range — slice off row 0 as keys.

---

## Code.gs template (slim version)

```javascript
/**
 * Finance Dashboard — Apps Script backend.
 * 5-minute cache; re-renders are <100ms.
 */
const SHEET_NAME = 'Transaksi';     // tab name to read
const ASSET_SHEET = 'Aset';
const GOAL_SHEET = 'Goals';
const CACHE_TTL_SEC = 300;          // 5 minutes

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 Dashboard')
    .addItem('Buka Dashboard', 'showDashboard')
    .addItem('Refresh Data', 'invalidateCache')
    .addItem('Setup Sample Data', 'setupSampleData')
    .addToUi();
}

function showDashboard() {
  const html = HtmlService.createHtmlOutputFromFile('Index')
    .setWidth(1400)
    .setHeight(900)
    .setTitle('Finance Dashboard');
  SpreadsheetApp.getUi().showModalDialog(html, 'Finance Dashboard');
}

// Alternative: full web app via doGet (use this if user wants standalone URL)
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Finance Dashboard')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function invalidateCache() {
  CacheService.getScriptCache().remove('dashboard_data');
}

function getDashboardData() {
  // 1. Check cache
  const cache = CacheService.getScriptCache();
  const cached = cache.get('dashboard_data');
  if (cached) {
    Logger.log('Cache hit');
    return JSON.parse(cached);
  }

  // 2. Read sheet
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const txSheet = ss.getSheetByName(SHEET_NAME);
  const txData = txSheet.getDataRange().getValues();
  const txHeaders = txData[0];
  const transactions = txData.slice(1).map(row => {
    const obj = {};
    txHeaders.forEach((h, i) => obj[h] = row[i]);
    return obj;
  });

  // 3. Read other sheets (assets, goals)
  const assets = readSheetAsObjects(ss, ASSET_SHEET);
  const goals = readSheetAsObjects(ss, GOAL_SHEET);

  // 4. Aggregate
  const data = {
    ok: true,
    transactions: transactions,
    assets: assets,
    goals: goals,
    totals: computeTotals(transactions),
    categories: groupByCategory(transactions),
    monthlyTrend: computeMonthlyTrend(transactions),
    accounts: groupByAccount(transactions),
    topExpenses: topN(filterByType(transactions, 'expense'), 5),
    counts: {
      transactions: transactions.length,
      assets: assets.length,
      goals: goals.length
    }
  };

  // 5. Cache for 5 minutes
  cache.put('dashboard_data', JSON.stringify(data), CACHE_TTL_SEC);
  return data;
}

function readSheetAsObjects(ss, sheetName) {
  const sheet = ss.getSheetByName(sheetName);
  if (!sheet) return [];
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];
  const headers = data[0];
  return data.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => obj[h] = row[i]);
    return obj;
  });
}

function computeTotals(txs) {
  const income = txs.filter(t => t.tipe === 'income').reduce((s, t) => s + Number(t.jumlah || 0), 0);
  const expense = txs.filter(t => t.tipe === 'expense').reduce((s, t) => s + Number(t.jumlah || 0), 0);
  return {
    income, expense,
    net: income - expense,
    savingRate: income > 0 ? (income - expense) / income : 0
  };
}

function groupByCategory(txs) {
  const map = {};
  txs.filter(t => t.tipe === 'expense').forEach(t => {
    map[t.kategori] = (map[t.kategori] || 0) + Number(t.jumlah || 0);
  });
  return Object.entries(map)
    .map(([kategori, total]) => ({ kategori, total }))
    .sort((a, b) => b.total - a.total);
}

function topN(arr, n) {
  return arr.slice().sort((a, b) => Number(b.jumlah) - Number(a.jumlah)).slice(0, n);
}

function setupSampleData() {
  // 36 sample transactions + 15 assets + 5 goals
  // ... (write to sheets)
}
```

**Critical pattern:** `readSheetAsObjects` normalizes the sheet rows into objects keyed by header. Without this, your JS code receives nested arrays and is much harder to work with.

**Date handling:** Apps Script returns dates as JS `Date` objects from `getValues()`. Serialize to ISO string before JSON.stringify to avoid timezone drift:
```javascript
if (obj.tanggal instanceof Date) {
  obj.tanggal = Utilities.formatDate(obj.tanggal, 'Asia/Jakarta', 'yyyy-MM-dd');
}
```

---

## Index.html template (inlined Chart.js)

```html
<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <meta charset="UTF-8">
  <style>
    /* dark glass-morphism theme */
    body {
      background: linear-gradient(135deg, #0f1729 0%, #1a1f3a 100%);
      color: #e4e4e7; font-family: system-ui, sans-serif;
      margin: 0; padding: 20px;
    }
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
    .kpi-card {
      background: rgba(255,255,255,0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px; padding: 20px;
    }
    /* ... rest of CSS ... */
  </style>
</head>
<body>
  <div id="app">Loading...</div>

  <!-- Chart.js inlined (no CDN — Apps Script HTML service has no internet) -->
  <script>
    /* __CHART_JS__ */
  </script>

  <script>
    let dashboardData = null;

    function init() {
      if (typeof google !== 'undefined' && google.script && google.script.run) {
        // Inside Apps Script: real backend
        google.script.run
          .withSuccessHandler(render)
          .withFailureHandler(showError)
          .getDashboardData();
      } else {
        // Local testing: mock data (see below)
        loadMockData();
      }
    }

    function render(data) {
      if (!data || !data.ok) { showError('Invalid data'); return; }
      dashboardData = data;
      document.getElementById('app').innerHTML = buildLayout(data);
      renderCharts(data);
    }

    function showError(err) {
      document.getElementById('app').innerHTML =
        `<div class="error">❌ ${err.message || err}</div>`;
    }

    function buildLayout(data) {
      const t = data.totals;
      return `
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Pemasukan</div>
            <div class="kpi-value">Rp ${t.income.toLocaleString('id-ID')}</div>
          </div>
          <!-- ... 3 more cards ... -->
        </div>
        <canvas id="trend-chart"></canvas>
        <canvas id="category-chart"></canvas>
      `;
    }

    function renderCharts(data) {
      new Chart(document.getElementById('trend-chart'), {
        type: 'line',
        data: {
          labels: data.monthlyTrend.map(m => m.month),
          datasets: [{
            label: 'Net', data: data.monthlyTrend.map(m => m.net),
            borderColor: '#F96167', tension: 0.4
          }]
        }
      });
    }

    // Bootstrap
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  </script>
</body>
</html>
```

**Build the inlined file** with a small Python script (same pattern as the standalone HTML offline build — see `references/offline-html-build.md`):

```python
# build_gsheet.py
from pathlib import Path
ROOT = Path(__file__).parent
template = (ROOT / "Index.template.html").read_text()
chart_js = (ROOT / "libs" / "chart.umd.min.js").read_bytes().decode("utf-8", errors="replace")
out = template.replace("/* __CHART_JS__ */", chart_js.replace("</script>", "<\\/script>"))
(ROOT / "Index.html").write_text(out)
```

Apps Script then imports the **two separate files** (`Index.html` + `Code.gs`), not the build artifact. The build artifact is for local testing only.

---

## ⚠️ Pitfall: Mock google.script.run for local testing

To test `Index.html` in a regular browser (file://) **without** deploying to Apps Script, inject a mock `google.script.run` before the page scripts run:

```html
<!-- Add to a SEPARATE file, e.g. test-mock.html that loads Index.html in iframe -->
<script>
// Mock google.script.run for local testing
window.google = {
  script: {
    run: {
      withSuccessHandler: function(cb) { this._success = cb; return this; },
      withFailureHandler: function(cb) { this._failure = cb; return this; },
      getDashboardData: function() {
        // Simulate async response
        setTimeout(() => {
          this._success(window.MOCK_DASHBOARD_DATA);
        }, 100);
      }
    }
  }
};

// Mock data (same shape as getDashboardData returns)
window.MOCK_DASHBOARD_DATA = {
  ok: true,
  transactions: [...],  // 30+ rows
  assets: [...],
  goals: [...],
  totals: { income: 29320700, expense: 6595000, net: 22725700, savingRate: 0.775 },
  categories: [...],
  monthlyTrend: [...],
  accounts: [...],
  topExpenses: [...],
  counts: { transactions: 53, assets: 15, goals: 5 }
};
</script>
```

The `init()` function in `Index.html` checks for `typeof google !== 'undefined' && google.script && google.script.run` and falls back to the mock. **In production (Apps Script), `google` is injected by the Apps Script runtime and the mock is bypassed.**

**Test pattern with Playwright:**
```python
# test_gsheet.py
from playwright.sync_api import sync_playwright
from pathlib import Path

INDEX = Path(__file__).parent / "Index.html"
MOCK = Path(__file__).parent / "test-mock.html"

# Use a wrapper HTML that injects mock then loads Index in an iframe
WRAPPER = f"""
<!DOCTYPE html>
<html><head>
<script>
{window.MOCK_DASHBOARD_DATA_SCRIPT}  // inline the mock
</script>
</head>
<body>
<iframe src="file://{INDEX.absolute()}" width="1400" height="900"></iframe>
</body>
</html>
"""
```

Or simpler: serve both files from a local server and use the same template pattern. The key is: **never deploy to Apps Script before testing locally with the mock**.

---

## Deploy steps (5 minutes)

1. Open the Google Sheet that has the data
2. **Extensions → Apps Script**
3. Create `Code.gs`, paste the backend (with menu functions)
4. Create `Index.html`, paste the inlined dashboard (with Chart.js inlined, NOT referenced from CDN)
5. Save project (Ctrl+S), name it "Finance Dashboard"
6. **Run `onOpen` once** to authorize script (will prompt for permissions — first time only)
7. Refresh the sheet — see "📊 Dashboard" menu appear
8. Click "Buka Dashboard" — modal opens with the dashboard
9. For web app URL: **Deploy → New deployment → Web app**, set "Execute as: Me", "Who has access: Anyone with Google account" (or "Anyone" if sheet is public)

**Permissions on first run:**
- `SpreadsheetApp` (read/write the sheet)
- `HtmlService` (serve the HTML)
- `CacheService` (cache the data)
- `Utilities` (date formatting)

User approves once, never prompted again.

---

## Common deployment pitfalls

### ⚠️ Apps Script HTML service has NO internet access
- ❌ `<script src="https://cdn.jsdelivr.net/chart.js"></script>` — silently fails
- ✅ Inline Chart.js (build script) — works
- ❌ `fetch('https://api.example.com/...')` — blocked
- ✅ Use `UrlFetchApp` in Code.gs to make the request, return JSON to the client

### ⚠️ Modal dialog can be too small
- `HtmlService.createHtmlOutputFromFile('Index').setWidth(1400).setHeight(900)` — needs explicit dimensions
- Or use `SpreadsheetApp.getUi().showSidebar(html)` for a thin side panel (300px)
- For full-screen, use web app deployment (`doGet`) and open the URL directly

### ⚠️ `google.script.run` is async
- Don't expect `let data = google.script.run.getDashboardData()` to work — it's a function call, not a value
- Always use `.withSuccessHandler(render)` callback

### ⚠️ Cache key is per-user, per-script
- `CacheService.getScriptCache().put('dashboard_data', ...)` caches for **5 min for that user**
- If you update the sheet manually, click "Refresh Data" in the menu to invalidate
- Or use a time-based key like `dashboard_data_v1` and bump the version on schema change

### ⚠️ Date objects in getValues() lose timezone
- `getValues()` returns a `Date` object representing midnight UTC
- When you JSON.stringify and ship to the client, the timezone is lost
- Always format dates server-side: `Utilities.formatDate(d, 'Asia/Jakarta', 'yyyy-MM-dd')`

---

## When NOT to use this pattern

- **Sheet is restricted to specific users** and user won't share with `Anyone with the link` — the gviz trick won't work for input, and the script needs at least the user's own access (which they have)
- **>10K rows** — Apps Script has 6-min execution limit; 50K row reads can take 30+ seconds
- **Multi-user concurrent writes** — last-write-wins, no transactions
- **User wants a public link** without sign-in — use a web app deployment with `Anyone` access (sheet itself still needs to be public or use a public data view)
- **Real-time data** (live prices, websocket streams) — Apps Script is request/response only
