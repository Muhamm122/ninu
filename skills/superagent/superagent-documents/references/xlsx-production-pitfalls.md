# XLSX Production Pitfalls & Patterns (openpyxl + LibreOffice + Excel)

## Hard-won lessons from building a 16-sheet financial workbook

### 1. LibreOffice round-trip resets openpyxl column widths

`soffice --headless --calc --convert-to ods` then back to `.xlsx` strips most custom column widths back to the default 13. This is by design — LibreOffice uses different internal units and re-computes on save. **Symptoms**: PDF render looks fine, but Excel shows `###` for currency columns and "..." for truncated headers.

**Fix**: post-process the xlsx XML directly to force widths after recalc.

```python
# /tmp/force_widths.py
import zipfile, shutil, re
from openpyxl import load_workbook

PATH = '/path/to/file.xlsx'
# Read desired widths from openpyxl (your last openpyxl save)
wb = load_workbook(PATH, data_only=False)
desired = {}
for sn in wb.sheetnames:
    desired[sn] = {}
    for col_letter, dim in wb[sn].column_dimensions.items():
        if dim.width:
            desired[sn][col_letter] = dim.width

# Find sheet name -> internal sheet file mapping (workbook.xml -> rId -> sheetN.xml)
with zipfile.ZipFile(PATH, 'r') as z:
    wb_xml = z.read('xl/workbook.xml').decode('utf-8')
    rels_xml = z.read('xl/_rels/workbook.xml.rels').decode('utf-8')

name_to_rid = dict(re.findall(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="(rId\d+)"', wb_xml))
rid_to_target = dict(re.findall(r'<Relationship Id="(rId\d+)"[^>]*Target="([^"]+)"', rels_xml))
sheet_to_internal = {n: 'xl/' + rid_to_target[name_to_rid[n]].lstrip('/') for n in name_to_rid}

# Rewrite each sheetN.xml with explicit <col> elements
TMP = '/tmp/force_widths.tmp.xlsx'
with zipfile.ZipFile(PATH, 'r') as zin, zipfile.ZipFile(TMP, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.namelist():
        data = zin.read(item)
        for sheet_name, widths in desired.items():
            if item == sheet_to_internal.get(sheet_name):
                xml = data.decode('utf-8')
                # Remove any existing <cols>...</cols>
                xml = re.sub(r'<cols>.*?</cols>', '', xml, flags=re.DOTALL)
                # Build new <cols> block
                cols_xml = '<cols>'
                for col_letter, width in widths.items():
                    col_idx = ord(col_letter) - ord('A') + 1
                    cols_xml += f'<col customWidth="1" min="{col_idx}" max="{col_idx}" width="{width}"/>'
                cols_xml += '</cols>'
                # Insert before <sheetData>
                xml = xml.replace('<sheetData', cols_xml + '<sheetData', 1)
                data = xml.encode('utf-8')
                break
        zout.writestr(item, data)
shutil.copy(TMP, PATH)
```

**ALWAYS run this** as the last step before delivery if you used LibreOffice for recalc.

### 2. Force recalc via ODS round-trip

openpyxl writes formula TEXT but no cached values. When user opens in Excel cold, it must recalc everything. This is slow AND causes false "[Repaired]" / "Circular References" warnings on first open if the workbook has any quirk.

**Fix**: round-trip through LibreOffice to bake in cached values.

```python
import subprocess, shutil, os
TMP = '/tmp/recalc'
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
subprocess.run(['soffice', '--headless', '--calc', '--convert-to', 'ods', '--outdir', TMP, PATH], capture_output=True, timeout=60)
subprocess.run(['soffice', '--headless', '--calc', '--convert-to', 'xlsx', '--outdir', TMP + '/out', TMP + '/laporan_keuangan_v29_dummy.ods'], capture_output=True, timeout=60)
shutil.copy(TMP + '/out/laporan_keuangan_v29_dummy.xlsx', PATH)
```

The output xlsx has cached values for every formula, so Excel opens instantly without recalc prompt.

### 3. "Circular References" warning is usually a #VALUE!/#DIV/0! false positive

Excel shows "Circular References" in the status bar even when there is NO actual cycle. Triggers:
- A formula that returns #VALUE! because of an empty cell reference
- A formula that returns #DIV/0! (e.g., `=C11/$C$16` where C16 is empty)
- A formula referencing an undefined named range (e.g., `budget` instead of `E9`)

**Don't trust a regex-based cycle detector** that scans formula text — false positives from sheet-qualified cell refs. Trust LibreOffice's macro: `oRanges = oDoc.getCellLinks()` plus iterating `oRange.AbsoluteName` will show the actual cycle if one exists.

**Action plan** when user reports "Circular References":
1. Run LibreOffice headless recalc → check cells for `#VALUE!` / `#DIV/0!` / `#NAME?`
2. Wrap culprit formulas with `IFERROR(formula, 0)`
3. Re-save

### 4. VLOOKUP column-index trap

VLOOKUP searches the FIRST column of the lookup range. If your categories are in column B but your range starts at column A, the lookup silently fails (returns #N/A) — and IFERROR-wrapped formulas return 0 without telling you.

**Pattern check**:
```python
# RENCANA sheet has:
# A: No (numbers 1-12)  <- first column
# B: Kategori (Makanan, Sewa, etc)  <- THIS is what you want to match
# C: Limit (Rp amount)

# WRONG:
=VLOOKUP("Makanan", RENCANA!$A$3:$C$14, 3, FALSE)  # searches column A (numbers)
# Returns #N/A

# RIGHT:
=VLOOKUP("Makanan", RENCANA!$B$3:$C$14, 2, FALSE)  # searches column B (categories)
# Returns 2,000,000
```

**Always verify the lookup range starts at the column you want to match**, not the leftmost column of the table.

### 5. Dynamic-dashboard date reference pitfall

In a dashboard driven by a `PERIODE` sheet, all DASHBOARD formulas reference the active period cells. If you put the dates at A5/B5 but the formulas reference A6/B6, **all KPIs show 0** with no error message (SUMIFS just returns 0 for "between epoch and epoch").

**Fix**: put the active period dates in the SAME cells the formulas reference. Use a helper cell that maps A6 = A5 + 0 if you need visual separation, OR update all DASHBOARD formulas to match the actual cell.

### 6. Percentage column with currency format trap

```python
cell.value = 12.3  # percentage as 12.3, not 0.123
cell.number_format = '"Rp "#,##0'  # WRONG — shows "Rp 12"
```

**Fix for percentage values stored as 0-100**:
```python
cell.number_format = '0.0"%"'  # shows "12.3%"
```

**Fix for percentage values stored as 0-1 (decimal)**:
```python
cell.number_format = '0.0%'  # shows "12.3%"
```

Pick based on how the value is stored. Both look the same on screen, but wrong format = `###` or "Rp" prefix on a percent.

### 7. Total row placement — find the actual last data row, not the cached max_row

After multiple populate+clean cycles, `ws.max_row` may be 2000+ (the trim script may have skipped some), but actual data ends at row 22. A total row at `last_data + 1` placed against stale `max_row` will land in the middle of your data.

**Fix**:
```python
last_data = 2
for r in range(3, ws.max_row + 1):
    if ws.cell(row=r, column=1).value is not None:
        last_data = r
total_row = last_data + 1
```

Also: after adding a total row, scan for any existing `🎯 TOTAL` / `💰 TOTAL` cells (left over from prior populate runs) and clear them before placing the new one.

### 8. MergedCell.value is read-only

If a cell is inside a merged range, `cell.value = "X"` raises `AttributeError: MergedCell object attribute 'value' is read-only`.

**Fix**: unmerge first, then write, then optionally re-merge.
```python
ws_unmerged = list(ws.merged_cells.ranges)
for mr in ws_unmerged:
    if mr.min_row == row_to_clear or mr.max_row == row_to_clear:
        ws.unmerge_cells(str(mr))
# Now safe to write
ws.cell(row=row_to_clear, column=2, value='TOTAL')
```

**Or** use the all-in-one safe clear:
```python
def safe_clear_row(ws, row):
    for mr in list(ws.merged_cells.ranges):
        if mr.min_row <= row <= mr.max_row:
            ws.unmerge_cells(str(mr))
    for c in range(1, ws.max_column + 1):
        ws.cell(row=row, column=c).value = None
        ws.cell(row=row, column=c).fill = PatternFill(fill_type=None)
```

### 9. Per-sheet comprehensive formatter (the "make it look pro" recipe)

A data sheet should have: merged title, dark header band, alternating row colors, borders, right-aligned numbers, center-aligned dates, color-coded status, frozen header, and a green total row at bottom.

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

C_HEADER_BG = '5D4037'    # dark chocolate
C_HEADER_FG = 'FFFFFF'
C_TITLE_BG  = '8B6F47'    # warm brown
C_TITLE_FG  = 'FFFFFF'
C_ROW_ODD   = 'F5E6D3'    # cream
C_ROW_EVEN  = 'FFFAF3'    # off-white
C_TOTAL_BG  = '2C5F2D'    # dark green
C_TOTAL_FG  = 'FFFFFF'
C_BORDER    = '8B6F47'
C_ACTIVE_BG = 'E8F5E9'

thin = Border(
    left=Side(style='thin', color=C_BORDER),
    right=Side(style='thin', color=C_BORDER),
    top=Side(style='thin', color=C_BORDER),
    bottom=Side(style='thin', color=C_BORDER)
)
thick = Border(
    left=Side(style='medium', color=C_TOTAL_BG),
    right=Side(style='medium', color=C_TOTAL_BG),
    top=Side(style='medium', color=C_TOTAL_BG),
    bottom=Side(style='medium', color=C_TOTAL_BG)
)

def format_data_sheet(ws, title, col_widths, data_start_row, last_data_row,
                     last_col_letter, total_row=None, freeze_row=3,
                     date_cols=(), money_cols=(), int_cols=(), has_status=False):
    # widths
    for col, w in col_widths.items():
        ws.column_dimensions[col].width = w

    last_col_idx = ord(last_col_letter) - ord('A') + 1

    # title row 1 — merged banner
    if ws.cell(row=1, column=1).value:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col_idx)
        t = ws.cell(row=1, column=1)
        t.font = Font(bold=True, size=16, color=C_TITLE_FG)
        t.fill = PatternFill('solid', fgColor=C_TITLE_BG)
        t.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28

    # header row (assumed at data_start_row - 1)
    hdr_row = data_start_row - 1
    for c in range(1, last_col_idx + 1):
        h = ws.cell(row=hdr_row, column=c)
        h.font = Font(bold=True, size=11, color=C_HEADER_FG)
        h.fill = PatternFill('solid', fgColor=C_HEADER_BG)
        h.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        h.border = thin
    ws.row_dimensions[hdr_row].height = 24

    # data rows
    for r in range(data_start_row, last_data_row + 1):
        for c in range(1, last_col_idx + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = thin
            col = get_column_letter(c)
            cell.fill = PatternFill('solid',
                fgColor=C_ROW_ODD if (r - data_start_row) % 2 == 0 else C_ROW_EVEN)
            if col in date_cols:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.number_format = 'DD/MM/YYYY'
            elif col in money_cols:
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.number_format = '"Rp"#,##0'
            elif col in int_cols:
                cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.number_format = '#,##0'
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            if has_status and col == last_col_letter:
                v = str(cell.value or '').lower()
                if 'active' in v:
                    cell.fill = PatternFill('solid', fgColor=C_ACTIVE_BG)
                    cell.font = Font(bold=True, color=C_TOTAL_BG, size=10)
                    cell.alignment = Alignment(horizontal='center', vertical='center')

    # total row
    if total_row and total_row <= last_data_row + 1:
        for c in range(1, last_col_idx + 1):
            t = ws.cell(row=total_row, column=c)
            t.font = Font(bold=True, size=11, color=C_TOTAL_FG)
            t.fill = PatternFill('solid', fgColor=C_TOTAL_BG)
            t.border = thick
            col = get_column_letter(c)
            if col in money_cols:
                t.alignment = Alignment(horizontal='right', vertical='center')
                t.number_format = '"Rp"#,##0'
            elif col in int_cols:
                t.alignment = Alignment(horizontal='right', vertical='center')
                t.number_format = '#,##0'
            else:
                t.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[total_row].height = 24

    if freeze_row:
        ws.freeze_panes = f'A{freeze_row}'
```

### 10. Vision-based visual QA for XLSX

After any complex XLSX build, render to PDF page-by-page and run vision_analyze per page. Catches:
- "###" in currency columns (column too narrow)
- Orphan rows from old populate runs
- Wrong format (`Rp` prefix on percentage)
- Misaligned KPI cards
- Stale cached values from prior version

```bash
soffice --headless --calc --convert-to pdf --outdir /tmp/audit /path/to/file.xlsx
pdftoppm -png -r 100 /tmp/audit/file.pdf /tmp/audit/p
# Then vision_analyze(image_url='/tmp/audit/p-07.png', question='Check DASHBOARD ...')
```

For 16+ sheet workbooks, render once and walk each page with vision. Don't trust openpyxl reads of cached values — LibreOffice recalc may have updated them.

### 11. PDF preview before delivery

Always render to PDF and check the first 3 pages visually before declaring done. Common "shipped broken" patterns caught by this:
- Title cut off (`A1` too narrow)
- Date column showing as "###" or "30/12/1899" (epoch zero from broken formula)
- Bar chart shows old category names (chart data range not updated)
- Bar chart shows empty (categories list doesn't match actual data categories)

### 12. IFS() function is not portable

`IFS()` works in Excel 2019+ and Excel 365, but breaks on Excel 2016 and some LibreOffice versions. **Always use nested IF** for cross-version compatibility.

```python
# BAD
cell.value = '=IFS(A1>0, "positive", A1<0, "negative", TRUE, "zero")'

# GOOD
cell.value = '=IF(A1>0, "positive", IF(A1<0, "negative", "zero"))'
```

### 13. Date column must be datetime objects, not strings

SUMIFS / date comparison formulas silently return 0 if the date column has text "2026-01-05" instead of `datetime.date(2026, 1, 5)`. Use `datetime.datetime(year, month, day)` or `datetime.date(...)` — never `str(d)`.

```python
from datetime import datetime
ws.cell(row=3, column=1, value=datetime(2026, 1, 5))   # correct
ws.cell(row=3, column=1, value='2026-01-05')            # WRONG — breaks SUMIFS
```

### 14. Bundle multi-file XLSX deliverables

For >3 files (xlsx + PDF + source code + README + template), zip them:

```python
import zipfile, os
os.chdir('/path/to/bundle/parent')
with zipfile.ZipFile('bundle.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk('bundle_dir/'):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.relpath(full, '.')
            z.write(full, arc)
```

Send via Telegram with `MEDIA:/path/to/bundle.zip`. Always re-zip AFTER any edits to the xlsx inside.

### 15. "Save Rate" calculation pattern

User asked for "saving rate" / "savings %" — formula is `net / income`, formatted as percent with IFERROR wrapper:

```python
cell.value = '=IFERROR((A6 - J6) / A6, 0)'  # where A6=income, J6=expense
cell.number_format = '0.0%'
# value 0.4395 → "44.0%" on screen
```

Wrap in IFERROR because if A6 is 0 (no income) the division fails.

### 16. Trim empty rows without losing data

Aggressive `ws.delete_rows(start, amount)` can hit MergedCell errors. Use this safe pattern:

```python
def trim_empty_rows(ws, keep_buffer=5):
    last_with_data = 1
    for r in range(1, ws.max_row + 1):
        if any(ws.cell(row=r, column=c).value is not None
               for c in range(1, ws.max_column + 1)):
            last_with_data = r
    # Unmerge anything past the last data row + buffer
    target_end = last_with_data + keep_buffer
    for mr in list(ws.merged_cells.ranges):
        if mr.max_row > target_end:
            ws.unmerge_cells(str(mr))
    # Delete rows beyond target
    if ws.max_row > target_end:
        ws.delete_rows(target_end + 1, ws.max_row - target_end)
```

### 17. User preference: don't say "table is now clean" until every page is verified

User said "MASIH TIDAK RAPI" twice in a row. Pattern: after one round of "table is clean", do NOT claim victory. Instead, render to PDF and run vision on every page. Fix any flagged issues. Then present the bundle with a screenshot of the most important page as proof.

The user trusts the visual evidence, not the data-side check.
