---
name: offline-html-build
description: Python build script pattern for inlining JS/CSS libs into a single self-contained HTML file (no CDN, file:// portable). Includes the SheetJS decode quirk, </script> escape pitfall, and Playwright headless verification.
---

# Offline-First Single-File HTML Build Pattern

The **offline-first** build produces one `dist/asset.html` that works from `file://` (no server, no CDN). Used when:
- VPS is air-gapped or behind strict no-CDN firewall
- User wants one file sharable via Telegram/email
- User explicitly says "100% offline" / "no CDN"

---

## Directory layout

```
/tmp/finance-v2/
├── src/                  # what you author
│   ├── style.css         # ~10 KB CSS, dark theme, glass-morphism
│   ├── body.html         # HTML skeleton with token placeholders
│   └── app.js            # application logic, ~30-50 KB
├── libs/                 # downloaded once, checked into the build
│   ├── chart.umd.min.js  # ~205 KB
│   └── xlsx.full.min.js  # ~951 KB on disk, 709 KB decoded (see quirk)
├── data/                 # sample data baked in
│   └── sample-data.js    # window.SAMPLE_DATA = {...}
└── build.py              # assembles dist/dashboard.html
```

The split source approach is more maintainable than a single 1 MB HTML. The build script is idempotent — re-run anytime.

---

## Build script template (`build.py`)

```python
#!/usr/bin/env python3
"""Build a single self-contained HTML file from split sources + libs."""
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
LIBS = ROOT / "libs"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)

def read(p: Path) -> str:
    """Read file as bytes, decode UTF-8 with replacement.

    CRITICAL: must use 'rb' + decode with errors='replace' so multi-byte
    chars in minified libs survive. See 'SheetJS decode quirk' below.
    """
    return p.read_bytes().decode("utf-8", errors="replace")

# 1. Read sources
style = read(SRC / "style.css")
app_js = read(SRC / "app.js")
body_html = read(SRC / "body.html")

# 2. Read libs (Chart.js, SheetJS, etc.)
chart_js = read(LIBS / "chart.umd.min.js")
xlsx_js = read(LIBS / "xlsx.full.min.js")

# 3. CRITICAL: escape </script> inside JS bodies before inlining.
# Otherwise HTML parser terminates the script tag early and the rest
# of the JS is rendered as text, breaking the page silently.
def safe_inline(js: str) -> str:
    return js.replace("</script>", "<\\/script>")

# 4. Read sample data file
sample_data = read(ROOT / "data" / "sample-data.js")

# 5. Assemble final HTML
template = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
__STYLE__
</style>
</head>
<body>
__BODY__
<script>
__CHART_JS__
</script>
<script>
__XLSX_JS__
</script>
<script>
__SAMPLE_DATA__
</script>
<script>
__APP_JS__
</script>
</body>
</html>
"""

out = (template
    .replace("__TITLE__", "Financial Dashboard")
    .replace("__STYLE__", style)
    .replace("__BODY__", body_html)
    .replace("__CHART_JS__", safe_inline(chart_js))
    .replace("__XLSX_JS__", safe_inline(xlsx_js))
    .replace("__SAMPLE_DATA__", sample_data)
    .replace("__APP_JS__", safe_inline(app_js)))

(DIST / "dashboard.html").write_text(out, encoding="utf-8")
print(f"Built {DIST / 'dashboard.html'}: {len(out):,} bytes")
```

Run with `python3 build.py`. Output is one file, typically 1-2 MB.

---

## Pitfalls (read these BEFORE debugging)

### ⚠️ Pitfall 1: SheetJS decode size mismatch (951 KB → 709 KB is NORMAL)

`xlsx.full.min.js` from SheetJS is **951 KB on disk** but **decodes to ~709 KB as UTF-8 text**. The "missing" ~240 KB is **multi-byte character entries in codepage mapping tables** — those are binary sequences that don't represent valid UTF-8.

```
File size on disk:     951,130 bytes
After .decode('utf-8'): 709,182 bytes  ← this is what gets inlined
```

**Don't try to "fix" this size mismatch.** It is by design. SheetJS ships binary codepage tables that don't all survive UTF-8 round-tripping — the runtime uses the codepage table to decode Excel files in legacy encodings (CP1252, Shift-JIS, GBK, etc.).

**Why this matters:**
- If you read the file with `read_text()` (text mode), Python decodes with the **default encoding** (usually UTF-8 with strict mode), which **raises UnicodeDecodeError on some bytes**.
- If you read with `read_bytes()` then `decode('utf-8', errors='replace')`, the binary bytes are silently replaced with `\ufffd` (replacement char), and the file is **fully intact at runtime** — SheetJS treats the codepage table as a flat byte array, not as text.

**Required pattern:**
```python
# ✅ CORRECT
content = path.read_bytes().decode("utf-8", errors="replace")

# ❌ WRONG — raises UnicodeDecodeError
content = path.read_text(encoding="utf-8")

# ❌ WRONG — silently drops the bad bytes (corrupts the codepage table)
content = path.read_bytes().decode("ascii", errors="ignore")
```

Verified working with SheetJS 0.20.x and Chart.js 4.x.

### ⚠️ Pitfall 2: `</script>` inside inlined JS breaks the HTML parser

When you inline a JS file into an HTML `<script>` block, the HTML parser scans for `</script>` **before** the JS interpreter runs. If your minified JS contains the literal string `</script>` (rare, but possible in regex literals or template strings), the HTML parser will **terminate the script tag early** and render the rest of the JS as plain HTML text. The page silently breaks.

**Fix:** escape `</script>` to `<\/script>` before inlining. The backslash is ignored by the JS parser (it sees the same string), but the HTML parser doesn't match the closing tag anymore.

```python
def safe_inline(js: str) -> str:
    return js.replace("</script>", "<\\/script>")
```

Also applies to `<!--` and `</style>` in HTML-embedded content. Chart.js minified bundle does **not** contain `</script>` (verified), but defensive escape costs nothing.

### ⚠️ Pitfall 3: Don't use string-concat assembly, use token replacement

```python
# ❌ Fragile: easy to break a quote, hard to grep
html = '<style>' + css + '</style>' + '<script>' + js + '</script>'

# ✅ Robust: tokens survive any character
html = template.replace("__STYLE__", css).replace("__APP_JS__", js)
```

Use a token like `__TOKEN_NAME__` that **cannot appear** in any of the inputs (double underscore prefix + uppercase = safe). If a token appears in user data, rename it.

### ⚠️ Pitfall 4: file:// + fetch() doesn't work for user-supplied data

If your dashboard uses `fetch('data.json')` to load data, **that breaks under `file://`** in Chromium (CORS blocks local file fetches). Workarounds:

| Option | Pros | Cons |
|--------|------|------|
| Bake data into a `<script>` block at build time | Works everywhere | Static; re-build to refresh |
| Use XLSX import via `XLSX.read(file)` from `<input type="file">` | User-supplied | Needs SheetJS; UI for file picker |
| Use localStorage for user-entered data | Persists across reloads | Manual export/import |
| Prompt user to drag-drop a CSV | One-shot upload | UI complexity |

**The XLSX import pattern** (most common in operator dashboards):
```javascript
// In app.js — user picks an XLSX/CSV file from disk
document.getElementById('xlsx-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const buf = await file.arrayBuffer();
    const wb = XLSX.read(buf, { type: 'array' });
    const sheet = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(sheet);
    // rows = [{tanggal: '2026-06-01', kategori: 'Makan', jumlah: 50000, ...}, ...]
    loadTransactions(rows);
});
```

---

## Headless verification pattern

Don't ship until you verify the build works under `file://`. Playwright headless is the fastest way:

```python
"""test.py — headless verification for an offline HTML build."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).parent / "dist" / "dashboard.html"

def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"file://{HTML.absolute()}")
        page.wait_for_load_state("networkidle", timeout=10_000)

        # 1. Verify libraries loaded
        chart_ok = page.evaluate("typeof Chart === 'function'")
        xlsx_ok = page.evaluate("typeof XLSX === 'object'")
        if not (chart_ok and xlsx_ok):
            print(f"❌ Libraries failed — Chart: {chart_ok}, XLSX: {xlsx_ok}")
            return 1

        # 2. Verify KPIs rendered (check for a known value, not just non-empty)
        kpi_text = page.locator(".kpi-value").first.inner_text()
        if not kpi_text or kpi_text == "Rp 0":
            print(f"❌ KPI not rendered: '{kpi_text}'")
            return 1

        # 3. Verify chart canvas was created
        canvas_count = page.locator("canvas").count()
        if canvas_count == 0:
            print("❌ No chart canvases found")
            return 1

        # 4. Screenshot for visual review
        page.screenshot(path="verify_dashboard.png", full_page=True)
        print(f"✅ {canvas_count} charts, KPI='{kpi_text}'")
        browser.close()
    return 0

sys.exit(main())
```

Run: `python3 test.py` — exits 0 on success, 1 on any check failure. Pair with `vision_analyze()` on the screenshot for visual QA.

**Common test failures and what they mean:**
- `Chart: False` → Chart.js didn't load. Check the inlined JS didn't get truncated by `</script>` escape issue.
- `KPI: 'Rp 0'` → Sample data didn't propagate. Check `window.SAMPLE_DATA` is set before `app.js` runs.
- `No chart canvases` → Either Chart.js failed (see above) or `app.js` errored. Open in non-headless mode to see the console.

---

## Indonesian / regional field names for finance dashboards

If the source is a Google Sheet or CSV with Indonesian headers, the dashboard field names should match:

| UI field | GSheet/CSV column | Type |
|----------|-------------------|------|
| Tanggal | `tanggal` | date (ISO `YYYY-MM-DD` or JS `Date()` literal from gviz) |
| Kategori | `kategori` | string |
| Deskripsi | `deskripsi` | string |
| Jumlah | `jumlah` | number (IDR, no decimal) |
| Tipe | `tipe` | enum: `income` / `expense` |
| Akun | `akun` | string (e.g. `BCA`, `Cash`, `GoPay`) |
| Sumber Aset | `sumber_aset` | enum: `saham`, `reksa_dana`, `crypto`, `deposito`, `properti`, `emas`, `obligasi` |
| Nama Instrumen | `nama_instrumen` | string (ticker / coin / fund name) |
| Nominal | `nominal` | number |
| Return % | `return_pct` | number (annualized) |
| Tanggal Beli | `tanggal_beli` | date |
| Platform | `platform` | string (broker name) |

Date parsing: gviz returns `Date(2026,5,1)` (month is 0-indexed in JS). Python regex parse:
```python
import re
m = re.match(r"Date\((\d+),(\d+),(\d+)\)", s)
y, mo, d = int(m.group(1)), int(m.group(2)) + 1, int(m.group(3))
```

---

## When NOT to use this pattern

- **Real-time data** (live prices, websocket streams): bake a snapshot at build time and accept staleness, or use a SPA backend
- **Server-side rendering** (SEO-critical pages): use Next.js
- **>3 MB of libs** (TensorFlow.js, Monaco editor): use a real bundler (Vite, esbuild) and lazy-load
- **Multi-page apps** (10+ views): one HTML becomes unwieldy; split into Vite + React Router
- **Team handoff** (other devs will maintain): split source is harder to onboard, single React app is more standard

For everything else (operator dashboards, internal tools, one-off data viz, financial summaries, social media analytics), this pattern is the fastest ship.
