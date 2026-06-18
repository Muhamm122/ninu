---
name: superagent-documents
description: "Document generation: docx, xlsx, pptx, pdf."
---

## Operator Profile

Structured output specialist. When a format is requested → render the actual artifact, not a preview. Descriptive filenames. One specific edit offer after each delivery.

---

## Render Targets

| Format | Use case | Library |
|--------|----------|---------|
| `.md` | Specs, prompts, docs | direct emit |
| `.docx` | Proposals, contracts, briefs | python-docx |
| `.xlsx` | Trackers, models, budgets | openpyxl / xlsxwriter |
| `.pptx` | Decks, pitches | python-pptx |
| `.pdf` | Final delivery, invoices, certificates | reportlab |
| `.csv` | Data export | csv stdlib / pandas |
| `.html` | Reports w/ styling, landing pages | direct emit / jinja2 |
| `.py/.js/.sh` | Executable scripts | direct emit |
| `.json/.yaml` | Config, schemas | direct emit |

---

## DOCX Template

```python
from docx import Document
from docx.shared import Pt, RGBColor

doc = Document()
title = doc.add_heading('Proposal — Project X', level=0)

doc.add_paragraph('Executive summary:')
p = doc.add_paragraph()
p.add_run('Key benefit. ').bold = True
p.add_run('Detail in same paragraph.')

doc.add_heading('Investment', level=1)
table = doc.add_table(rows=1, cols=3)
table.style = 'Light Grid Accent 1'
hdr = table.rows[0].cells
hdr[0].text, hdr[1].text, hdr[2].text = 'Tier', 'Price', 'Includes'
for tier, price, inc in [('Entry', 'IDR 500K', 'Basic'), ('Core', 'IDR 2.5M', 'Standard'), ('Premium', 'IDR 8M', 'Full')]:
    row = table.add_row().cells
    row[0].text, row[1].text, row[2].text = tier, price, inc

doc.save('proposal-projectx.docx')
```

---

## XLSX Template (with formulas + formatting)

```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Summary'

headers = ['Date', 'Channel', 'Revenue (IDR)', 'Conversion %']
ws.append(headers)
for c in ws[1]:
    c.font = Font(bold=True, color='FFFFFF')
    c.fill = PatternFill('solid', fgColor='2E5BBA')
    c.alignment = Alignment(horizontal='center')

data = [
    ('2025-05-01', 'IG',     1_200_000, 3.2),
    ('2025-05-02', 'TikTok', 2_400_000, 2.1),
]
for row in data:
    ws.append(row)

# Formula at bottom
ws['C5'] = '=SUM(C2:C4)'
ws['C5'].font = Font(bold=True)

# Column widths
for col, w in zip('ABCD', [12, 12, 16, 14]):
    ws.column_dimensions[col].width = w

wb.save('revenue-may2025.xlsx')
```

---

## PPTX Template

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

prs = Presentation()
prs.slide_width = Inches(13.33); prs.slide_height = Inches(7.5)  # 16:9

# Title slide
s = prs.slides.add_slide(prs.slide_layouts[0])
s.shapes.title.text = 'Project X'
s.placeholders[1].text = 'Q3 2025 Pitch'

# Content slide
s = prs.slides.add_slide(prs.slide_layouts[1])
s.shapes.title.text = 'Why now?'
tf = s.placeholders[1].text_frame
for i, point in enumerate(['Market timing', 'Distribution unlock', 'Cost collapse']):
    p = tf.add_paragraph() if i else tf.paragraphs[0]
    p.text = point
    p.font.size = Pt(28)

prs.save('pitch-projectx.pptx')
```

---

## PDF with Clickable Hyperlinks (ReportLab)

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.colors import HexColor

doc = SimpleDocTemplate('directory.pdf', pagesize=A4,
                        leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=2*cm, bottomMargin=2*cm)
styles = getSampleStyleSheet()
link_style = ParagraphStyle('Link', parent=styles['Normal'],
                            textColor=HexColor('#2E5BBA'), fontSize=11)

flow = [Paragraph('<b>Web3 Project Directory</b>', styles['Title']), Spacer(1, 12)]
for name, url in [('Project A', 'https://a.xyz'), ('Project B', 'https://b.xyz')]:
    flow.append(Paragraph(f'<a href="{url}">{name}</a> — {url}', link_style))
    flow.append(Spacer(1, 4))

doc.build(flow)
```

---

## Batch File Operations

```python
import os, shutil
from pathlib import Path

src = Path('input')
dst = Path('output'); dst.mkdir(exist_ok=True)

for f in src.glob('**/*.pdf'):
    rel = f.relative_to(src)
    target = dst / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, target)
    print(f'✅ {rel}')
```

---

## Image Processing Pipeline (Pillow + rembg)

```python
from PIL import Image, ImageOps
from rembg import remove

# Background removal
with open('input.jpg', 'rb') as fi, open('cutout.png', 'wb') as fo:
    fo.write(remove(fi.read()))

# Resize for Twitter avatar (400x400)
img = Image.open('cutout.png').convert('RGBA')
img = ImageOps.fit(img, (400, 400), Image.LANCZOS)
img.save('avatar.png', optimize=True)
```

---

## Structural Templates

### Proposal
```
1. Executive summary (1 paragraph)
2. Problem
3. Solution
4. Timeline
5. Investment (3 tiers, anchor on premium)
6. Proof / case studies
7. Next step (specific, dated)
```

### Technical spec
```
# [ID] — short description
## Goals      ## Non-goals    ## Setup
## Usage     ## Reference     ## Edge cases
```

### Insight report
```
1. Executive summary (1 paragraph)
2. Method
3. Findings (3–7 bullets)
4. Analysis
5. Prescriptions (exactly 3, specific, dated)
6. Appendix
```

---

## Render Protocol

```
1. Confirm scope (max 1 clarifying exchange)
2. Generate artifact
3. Save to output path with descriptive filename
4. Deliver with present_files
5. Offer: "Adjust [specific section]?"
```

---

## Constraints

- Render the ACTUAL artifact — inline preview is not a deliverable
- Filenames descriptive: `q3-revenue-analysis.xlsx` not `output.xlsx`
- One specific edit offer after delivery, not generic "any changes?"
- For multi-file deliverables: bundle into zip when > 3 files

---

## Multi-Format Dashboard Deliverable (HTML + XLSX + Apps Script)

When the user wants to "build a dashboard" / "laporan" / "tracker" / "spreadsheet with charts" — they almost always need 3 formats: **viewable in browser** (HTML), **editable in Excel** (XLSX), and **shareable / collaborative** (Google Sheets). Default to building all 3 unless they explicitly say "cukup satu".

### Format split

| Format | Role | Library / API |
|---|---|---|
| HTML standalone | Visual dashboard, mobile, offline-ready | Tailwind CDN + Chart.js + SheetJS (all inlined for offline) |
| XLSX | Local editing, business users, formulas | openpyxl with multi-sheet + charts + conditional formatting |
| Apps Script | Cloud collaboration, mobile editing, no install | HtmlService sidebar + onOpen menu + server functions |

### Shared data shape

Keep ONE source of truth (e.g. `sample_data.json`) and derive all 3 formats from it. Categories use lowercase IDs (e.g. `makanan` not `Makanan`) to avoid case-mismatch between source data and CATS_INC/CATS_EXP dicts. Always normalize:

```python
for t in TX: t["kategori"] = t["kategori"].lower()
```

### HTML standalone pattern (offline-first)

**Inlining strategy**: copy minified Chart.js + SheetJS from CDN URLs into `<script>` tags inside the HTML. End file is ~1-1.5MB but works without internet. Use this when user might open the file on a different machine, send it via Telegram, or store it on USB.

```bash
# Get minified libs once
curl -s https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js > chart_inline.js
curl -s https://cdn.jsdelivr.net/npm/xlsx@0.20.3/dist/xlsx.full.min.js > xlsx_inline.js
# Then paste each file's content into <script>...</script> blocks in the HTML
```

Tailwind stays as CDN (small, can't reasonably inline the JIT compiler). For dark/light theme, use CSS variables on `:root[data-theme="dark"]` — instant switch without re-render.

**Multi-tab navigation**: single page, `display: none` on inactive sections, `class="active"` on current tab + section. localStorage key namespace the version: `laporan_keuangan_v2` not `laporan_keuangan` to avoid clobbering v1 data.

### XLSX multi-sheet pattern (openpyxl)

Beyond basic tables, the user almost always wants: KPI cards, charts, conditional formatting, and formulas that survive row additions. Reference: `templates/dashboard_xlsx.py` and `references/multi-format-dashboard.md`.

Key patterns:
- **KPI cards**: 2-column merged cells per metric, with header band (color) + value cell (large font) + sublabel. Use `ws.merge_cells(f'{sc}4:{ec}4')` with explicit col letters from `get_column_letter()` — single-char tuple like `('A','B')` is NOT a valid range and raises `ValueError`.
- **Charts**: `BarChart`, `PieChart`, `LineChart`, `DoughnutChart` from `openpyxl.chart`. Add via `ws.add_chart(chart, "E8")` for anchor position.
- **Conditional formatting**: `ColorScaleRule(start_type='num', start_value=0, start_color='C6EFCE', ...)` for gradient (e.g. budget usage 0% green → 100% red).
- **Formulas**: `=SUMIF(B:B,"Pemasukan",E:E)` for conditional sums. `=D/C` for progress ratio with `0.0%` format. `=G-H` for P/L.
- **Freeze panes**: `ws.freeze_panes = 'A3'` keeps header visible.
- **Number format**: `'"Rp "#,##0'` for IDR currency (note the literal "Rp" prefix inside quotes).

### Apps Script dashboard pattern (Google Sheets)

The full setup → in-spreadsheet sidebar flow. Reference code (CONFIG, onOpen menu, setupTemplate, getDashboardData, modal form, sidebar HTML with Chart.js) is in `references/multi-format-dashboard.md` — copy the Kode.gs and dashboard.html sections to bootstrap.

Architecture:
1. **`Kode.gs` (server)**: `CONFIG` object with sheet names, category/goal/investment constants, `onOpen()` that adds custom menu, `setupTemplate()` that creates all sheets + sample data + charts in one click, CRUD dialog functions (`showAddTxDialog`, `addTransaction`, etc.), `getDashboardData()` that reads from `Transaksi` sheet and returns the whole payload to the client.
2. **`dashboard.html` (client)**: Sidebar rendered via `HtmlService.createHtmlOutputFromFile('dashboard')`. Uses `google.script.run.withSuccessHandler(...).getDashboardData()` to fetch data, then renders all charts/tables client-side with Chart.js (CDN OK — Apps Script allows CDN in HtmlService).
3. **Menu structure**:
   ```
   💰 Laporan Keuangan
   ├── 🚀 Setup Template
   ├── 📊 Refresh Dashboard
   ├── ➕ Tambah Transaksi
   ├── 📁 Data
   │   ├── 📥 Import dari CSV
   │   ├── 📤 Export ke CSV
   │   └── 🗑️ Reset ke Sample
   ├── 🏷️ Master
   │   ├── ➕ Kategori Income / Expense
   │   ├── 🏦 Tambah Akun
   │   └── 🎯 Tambah Goal
   └── 🌐 Buka Dashboard (sidebar)
   ```

4. **Setup template pattern**: For each sheet, call a dedicated `createXxxSheet(ss)` function. Each function: hides gridlines (`setHiddenGridlines(true)`), sets title row with `merge()` + dark fill + white font, builds header row with `setValues([[...]])` + bold, then iterates data with explicit row index counter (don't trust `getLastRow()` mid-build). Charts via `ws.newChart().setChartType(Charts.ChartType.PIE).addRange(...).setPosition(r, c, 0, 0).build()`.

5. **Modal dialog form pattern**: For CRUD, generate inline HTML in a template literal, return via `HtmlService.createHtmlOutput(html).setWidth(420).setHeight(620)`. Form submission calls `google.script.run.withSuccessHandler(r => { alert(...); google.script.host.close(); }).serverFunction(data)`.

6. **Sidebar (vs modal)**: Use sidebar for the dashboard itself (`setWidth(1400).setHeight(900).setTitle(...)`). User keeps spreadsheet visible.

### Delivery via Telegram

For multi-file bundles (HTML + XLSX + .gs + README):

```python
# 1. Bundle
import zipfile
with zipfile.ZipFile('paket.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in [html, xlsx, gs, html2, json, md, png]:
        z.write(f)

# 2. Validate each deliverable runs
# HTML: chromium headless screenshot
# XLSX: openpyxl load_workbook then check sheet names + cell values
# Apps Script: syntax check via Apps Script API or visual review of the .gs file

# 3. Send via Telegram with MEDIA: prefix for each
# Order: preview screenshot → main file → bundle zip
```

Telegram message pattern for multi-format:
```
💰 JUDUL — 3 VERSI READY
Preview: MEDIA:/path/screenshot.png
Files:
• file1.html (size, role)
• file2.xlsx (size, role)
• file3.gs + file3.html (size, role)
Bundle: MEDIA:/path/paket.zip
Quick start: 1-2-3 steps
```

### Decision tree for new dashboard requests

```
"bikin dashboard / laporan / tracker"
├─ Single user, personal, offline? → HTML standalone (inlined libs)
├─ Business user, must edit in Excel? → XLSX (multi-sheet + formulas)
├─ Team / share / mobile edit? → Apps Script (sidebar)
└─ No clue / "yang penting jalan"? → Build ALL 3 from one data source
```

### Common pitfalls

- **Sample data uses Title Case ("Makanan")** but your category dicts use lowercase IDs ("makanan"). Always normalize with `t["kategori"].lower()` before grouping.
- **openpyxl `merge_cells(f"{col1}{r}:{col2}{r}")` requires column LETTERS, not tuples**. Wrong: `('A','B')`. Right: `get_column_letter(sc) + get_column_letter(ec)`.
- **openpyxl chart position** is `(row, column, rowOffset, colOffset)` zero-indexed. `setPosition(8, 4, 0, 0)` = anchor at row 8 col 4 (E).
- **Apps Script HtmlService CDN**: works fine for client libs (Chart.js, Tailwind), but server-side `UrlFetchApp` calls to external APIs need `Apps-Script` user-agent whitelist on target.
- **Apps Script custom menu disappears** if you don't `addToUi()` at the end of `onOpen()`. Refresh spreadsheet (F5) after deploy.
- **localStorage namespace collision** between v1 and v2 HTML dashboards — always version the storage key.
- **Inlined Chart.js makes HTML 1MB+**. That's expected for offline self-contained. Don't try to minify further.
- **Telegram file upload size**: Bot API limit is 50MB for sendDocument, 10MB for sendPhoto. For >10MB screenshot, send as document not photo.

### XLSX production gotchas (must read)

openpyxl + LibreOffice + Excel is a three-tool chain with several hidden failure modes. The full list lives in `references/xlsx-production-pitfalls.md` — load it before any non-trivial XLSX build. Top 5 traps:

1. **LibreOffice recalc round-trip wipes column widths** → bake widths back via direct XML post-processing of the xlsx zip (full code in reference).
2. **"Circular References" warning is usually a #VALUE!/#DIV/0! false positive**, not a real cycle. Wrap every formula in `IFERROR` and check cached values via LibreOffice recalc.
3. **VLOOKUP column-index trap** — if data starts at column B (categories), `VLOOKUP(A...;A:C;3)` searches the wrong column and silently returns 0.
4. **Date column must be `datetime` objects**, not strings — `SUMIFS` returns 0 silently on text dates.
5. **`IFS()` is not portable** — use nested `IF()` for Excel 2016 / LibreOffice compatibility.

Other production essentials in the reference: per-sheet formatter (borders + zebra + alignment + freeze + total), PDF-page-by-page vision QA, safe row trim without MergedCell errors, total row placement at actual last_data + 1, percentage format `0.0"%"` for value-as-12.3 vs `0.0%` for value-as-0.123.

### See also

- `references/multi-format-dashboard.md` — full code recipes for all 3 formats + sample data structure
- `references/xlsx-production-pitfalls.md` — must-read gotchas for openpyxl + LibreOffice + Excel: column width preservation, #VALUE!/#DIV/0! masking as "circular references", VLOOKUP column-index trap, datetime vs string dates, per-sheet formatter, PDF vision QA
- `scripts/format_xlsx_sheet.py` — reusable per-sheet formatter (`format_data_sheet`, `trim_empty_rows`, `force_widths_xml`, `recalc_via_libreoffice`, `find_last_data_row`, `clear_total_rows`). Import and call instead of rewriting from scratch.
- `templates/dashboard_xlsx.py` — openpyxl multi-sheet workbook with KPI cards + charts + formulas
- `templates/dashboard_apps_script.gs` — full Apps Script Kode.gs with onOpen menu + setupTemplate + sidebar binding
- `templates/dashboard_apps_script.html` — HtmlService sidebar dashboard with Chart.js + tabs
- `templates/dashboard_html_shell.html` — minimal HTML dashboard skeleton with inlined libs pattern
