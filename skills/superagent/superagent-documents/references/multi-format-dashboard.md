# Multi-Format Dashboard Deliverable — Full Recipe

Companion to `superagent-documents/SKILL.md` "Multi-Format Dashboard Deliverable" section. Full code patterns for building a single dataset into HTML + XLSX + Apps Script deliverables in one session.

## Sample data shape (single source of truth)

```json
{
  "metadata": {
    "currency": "IDR",
    "user": "user",
    "start_date": "2026-04-01",
    "end_date": "2026-08-31"
  },
  "accounts": [
    {"id": "cash",   "name": "Cash",      "balance": 5000000},
    {"id": "bank",   "name": "BCA",       "balance": 15000000},
    {"id": "ewallet","name": "GoPay",     "balance": 2500000}
  ],
  "categories": {
    "income":  {"gaji": "Gaji", "bonus": "Bonus", "freelance": "Freelance", "dividen": "Dividen"},
    "expense": {"makanan":"Makanan", "transport":"Transport", "belanja":"Belanja",
                "tagihan":"Tagihan", "hiburan":"Hiburan", "kesehatan":"Kesehatan",
                "pendidikan":"Pendidikan", "donasi":"Donasi"}
  },
  "transaksi": [
    {"tanggal":"2026-04-01","tipe":"Pemasukan","kategori":"gaji","jumlah":8500000,
     "akun":"bank","catatan":"Gaji bulanan"},
    {"tanggal":"2026-04-02","tipe":"Pengeluaran","kategori":"makanan","jumlah":45000,
     "akun":"ewallet","catatan":"Sarapan"}
  ],
  "goals": [
    {"nama":"Dana Darurat","target":30000000,"current":18500000,"deadline":"2026-12-31"},
    {"nama":"Liburan Bali","target":15000000,"current":8000000,"deadline":"2026-09-30"}
  ],
  "investments": [
    {"nama":"Reksa Dana Pasar Uang","jenis":"RDP","modal":5000000,"nilai":5350000,
     "return_pct":7.0,"tanggal_beli":"2026-01-15"},
    {"nama":"BBCA","jenis":"Saham","modal":2000000,"nilai":2450000,
     "return_pct":22.5,"tanggal_beli":"2026-02-10"}
  ]
}
```

CRITICAL: JSON key is `transaksi` (Bahasa Indonesia, matches UI), NOT `transactions`. The user often writes English field names — always check actual data file before coding.

CRITICAL: Category values are LOWERCASE IDs (`gaji`, `makanan`). Display labels in `categories` dict are Title Case. Always normalize: `for t in TX: t["kategori"] = t["kategori"].lower()`.

## KPI card builder (openpyxl)

```python
def kpi_card(ws, row, col_start, col_end, title, value, sublabel, color="2563EB"):
    """Place a KPI card spanning (row, col_start:col_end)."""
    sc, ec = get_column_letter(col_start), get_column_letter(col_end)
    # Title band (row, cols)
    ws.merge_cells(f'{sc}{row}:{ec}{row}')
    cell = ws[f'{sc}{row}']
    cell.value = title.upper()
    cell.fill = PatternFill('solid', fgColor=color)
    cell.font = Font(bold=True, color='FFFFFF', size=10)
    cell.alignment = Alignment(horizontal='center', vertical='center')
    # Value cell (row+1, cols)
    ws.merge_cells(f'{sc}{row+1}:{ec}{row+1}')
    v = ws[f'{sc}{row+1}']
    v.value = value
    v.font = Font(bold=True, color=color, size=18)
    v.alignment = Alignment(horizontal='center', vertical='center')
    # Sublabel (row+2, cols)
    ws.merge_cells(f'{sc}{row+2}:{ec}{row+2}')
    s = ws[f'{sc}{row+2}']
    s.value = sublabel
    s.font = Font(italic=True, color='666666', size=9)
    s.alignment = Alignment(horizontal='center', vertical='center')
    # Set row heights
    ws.row_dimensions[row].height = 20
    ws.row_dimensions[row+1].height = 32
    ws.row_dimensions[row+2].height = 16
```

Usage:
```python
kpi_card(ws, 2, 1, 3, "💰 PEMASUKAN", "Rp 29,32jt", "10 transaksi Apr-Agu", "10B981")
kpi_card(ws, 2, 4, 6, "💸 PENGELUARAN", "Rp 6,59jt", "43 transaksi", "EF4444")
kpi_card(ws, 2, 7, 9, "📈 NET", "+Rp 22,72jt", "Saldo: 77.5%", "3B82F6")
```

## Chart recipes (openpyxl)

```python
from openpyxl.chart import BarChart, PieChart, LineChart, DoughnutChart, Reference
from openpyxl.chart.label import DataLabelList

# Bar chart — income vs expense per month
bar = BarChart()
bar.type = "col"
bar.style = 11
bar.title = "Income vs Expense per Bulan"
bar.y_axis.title = "Jumlah (Rp)"
bar.x_axis.title = "Bulan"
data = Reference(ws, min_col=2, min_row=1, max_col=3, max_row=6)
cats = Reference(ws, min_col=1, min_row=2, max_row=6)
bar.add_data(data, titles_from_data=True)
bar.set_categories(cats)
bar.height = 9
bar.width = 18
ws.add_chart(bar, "A10")

# Pie chart — expense by category
pie = PieChart()
pie.title = "Distribusi Pengeluaran"
labels = Reference(ws, min_col=1, min_row=2, max_row=10)
data = Reference(ws, min_col=2, min_row=1, max_row=10)
pie.add_data(data, titles_from_data=True)
pie.set_categories(labels)
pie.dataLabels = DataLabelList(showPercent=True)
ws.add_chart(pie, "K10")
```

## Conditional formatting (color scale)

```python
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule

# Gradient 0% green → 100% red (budget usage)
rule = ColorScaleRule(start_type='num', start_value=0, start_color='C6EFCE',
                      mid_type='num', mid_value=50, mid_color='FFEB9C',
                      end_type='num', end_value=100, end_color='FFC7CE')
ws.conditional_formatting.add(f'B2:B50', rule)

# Boolean highlight — "over budget" rows
over = CellIsRule(operator='greaterThan', formula=['100%'],
                  fill=PatternFill('solid', fgColor='FFC7CE'),
                  font=Font(bold=True, color='9C0006'))
ws.conditional_formatting.add(f'B2:B50', over)
```

## Apps Script — full Kode.gs skeleton

```javascript
// === CONFIG ===
const CONFIG = {
  sheetNames: {
    dashboard: 'Dashboard',
    transaksi:  'Transaksi',
    kategori:   'Kategori',
    goals:      'Goals',
    investasi:  'Investasi',
    budget:     'Budget',
    laporan:    'Laporan'
  },
  currentVersion: 'v2'
};

const CATS_INC = {gaji:'Gaji', bonus:'Bonus', freelance:'Freelance', dividen:'Dividen'};
const CATS_EXP = {makanan:'Makanan', transport:'Transport', belanja:'Belanja',
                  tagihan:'Tagihan', hiburan:'Hiburan', kesehatan:'Kesehatan'};

// === ON OPEN: add custom menu ===
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('💰 Laporan Keuangan')
    .addItem('🚀 Setup Template', 'setupTemplate')
    .addItem('📊 Refresh Dashboard', 'refreshDashboard')
    .addSeparator()
    .addSubMenu(SpreadsheetApp.getUi().createMenu('📁 Data')
      .addItem('📥 Import dari CSV', 'importCSV')
      .addItem('📤 Export ke CSV', 'exportCSV')
      .addItem('🗑️ Reset ke Sample', 'resetToSample'))
    .addSubMenu(SpreadsheetApp.getUi().createMenu('➕ Tambah')
      .addItem('Tambah Transaksi', 'showAddTxDialog')
      .addItem('Tambah Goal', 'showAddGoalDialog')
      .addItem('Tambah Investasi', 'showAddInvDialog'))
    .addToUi();
}

// === SETUP TEMPLATE (one-click) ===
function setupTemplate() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();
  const resp = ui.alert('🚀 Setup Template', 'Buat semua sheet + sample data + dashboard?', ui.ButtonSet.YES_NO);
  if (resp !== ui.Button.YES) return;

  // Create each sheet
  createDashboardSheet(ss);
  createTransaksiSheet(ss);
  createKategoriSheet(ss);
  createGoalsSheet(ss);
  createInvestasiSheet(ss);
  createBudgetSheet(ss);
  createLaporanSheet(ss);
  populateSampleData(ss);

  ui.alert('✅ Setup selesai! Sidebar dashboard: menu → Buka Dashboard.');
}

function createTransaksiSheet(ss) {
  const ws = ss.insertSheet(CONFIG.sheetNames.transaksi);
  ws.setHiddenGridlines(true);
  // Title row
  ws.getRange('A1:G1').merge()
    .setValue('📋 TRANSAKSI').setBackground('1F2937').setFontColor('FFFFFF').setFontWeight('bold')
    .setHorizontalAlignment('center');
  // Header row
  ws.getRange(2, 1, 1, 7).setValues([['Tanggal','Tipe','Kategori','Jumlah','Akun','Catatan','Bukti']])
    .setFontWeight('bold').setBackground('E5E7EB');
  ws.setFrozenRows(2);
  // Column widths
  ws.setColumnWidth(1, 100).setColumnWidth(2, 100).setColumnWidth(3, 100)
    .setColumnWidth(4, 120).setColumnWidth(5, 80).setColumnWidth(6, 200).setColumnWidth(7, 80);
}

// === CLIENT-FACING DATA READER ===
function getDashboardData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ws = ss.getSheetByName(CONFIG.sheetNames.transaksi);
  const data = ws.getDataRange().getValues();
  const headers = data[1]; // row 2
  const rows = data.slice(2);

  const tx = rows.map(r => ({
    tanggal: r[0] instanceof Date ? r[0].toISOString().slice(0,10) : r[0],
    tipe: r[1], kategori: r[2], jumlah: r[3], akun: r[4], catatan: r[5]
  }));

  // Group by month
  const byMonth = {};
  tx.forEach(t => {
    const m = t.tanggal.slice(0,7);
    if (!byMonth[m]) byMonth[m] = {income:0, expense:0, count:0};
    if (t.tipe === 'Pemasukan') byMonth[m].income += t.jumlah;
    else if (t.tipe === 'Pengeluaran') byMonth[m].expense += t.jumlah;
    byMonth[m].count++;
  });

  // Group expense by category
  const byCat = {};
  tx.filter(t => t.tipe === 'Pengeluaran').forEach(t => {
    byCat[t.kategori] = (byCat[t.kategori] || 0) + t.jumlah;
  });

  const totalIn = tx.filter(t => t.tipe === 'Pemasukan').reduce((s,t) => s+t.jumlah, 0);
  const totalOut = tx.filter(t => t.tipe === 'Pengeluaran').reduce((s,t) => s+t.jumlah, 0);

  return {
    transaksi: tx,
    byMonth, byCat,
    totals: {income: totalIn, expense: totalOut, net: totalIn - totalOut,
             savingsRate: totalIn > 0 ? (totalIn - totalOut) / totalIn : 0}
  };
}

// === SIDEBAR ===
function openDashboard() {
  const html = HtmlService.createHtmlOutputFromFile('dashboard')
    .setWidth(1400).setHeight(900)
    .setTitle('📊 Dashboard');
  SpreadsheetApp.getUi().showSidebar(html);
}
```

## Apps Script — dashboard.html skeleton

```html
<!DOCTYPE html>
<html>
<head>
  <base target="_top">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; padding: 12px; background: #F9FAFB; }
    .kpi { display: flex; gap: 8px; margin-bottom: 12px; }
    .kpi-card { flex: 1; padding: 12px; border-radius: 8px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-card .label { font-size: 11px; color: #6B7280; text-transform: uppercase; }
    .kpi-card .value { font-size: 22px; font-weight: bold; margin-top: 4px; }
    .kpi-card .sub { font-size: 11px; color: #9CA3AF; margin-top: 2px; }
    .chart-row { display: flex; gap: 12px; margin-bottom: 12px; }
    .chart-box { flex: 1; background: white; padding: 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .chart-box canvas { max-height: 240px; }
  </style>
</head>
<body>
  <div id="loading">⏳ Loading data...</div>
  <div id="content" style="display:none">
    <div class="kpi" id="kpi-row"></div>
    <div class="chart-row">
      <div class="chart-box"><h4>Income vs Expense</h4><canvas id="barChart"></canvas></div>
      <div class="chart-box"><h4>Expense by Category</h4><canvas id="pieChart"></canvas></div>
    </div>
  </div>
  <script>
    google.script.run
      .withSuccessHandler(renderDashboard)
      .withFailureHandler(err => document.getElementById('loading').textContent = '❌ ' + err.message)
      .getDashboardData();

    function renderDashboard(data) {
      document.getElementById('loading').style.display = 'none';
      document.getElementById('content').style.display = 'block';
      // KPIs
      const fmt = n => 'Rp ' + (n/1e6).toFixed(2) + 'jt';
      const kpis = [
        {l:'Pemasukan', v:fmt(data.totals.income), s:data.totals.income+' total', c:'#10B981'},
        {l:'Pengeluaran', v:fmt(data.totals.expense), s:data.totals.expense+' total', c:'#EF4444'},
        {l:'Net', v:fmt(data.totals.net), s:'Savings '+(data.totals.savingsRate*100).toFixed(1)+'%', c:'#3B82F6'}
      ];
      document.getElementById('kpi-row').innerHTML = kpis.map(k =>
        `<div class="kpi-card"><div class="label">${k.l}</div>
         <div class="value" style="color:${k.c}">${k.v}</div>
         <div class="sub">${k.s}</div></div>`
      ).join('');
      // Bar chart
      const months = Object.keys(data.byMonth).sort();
      new Chart(document.getElementById('barChart'), {
        type: 'bar',
        data: { labels: months,
          datasets: [
            {label:'Pemasukan', data: months.map(m => data.byMonth[m].income), backgroundColor:'#10B981'},
            {label:'Pengeluaran', data: months.map(m => data.byMonth[m].expense), backgroundColor:'#EF4444'}
          ]}
      });
      // Pie
      const cats = Object.keys(data.byCat);
      new Chart(document.getElementById('pieChart'), {
        type: 'doughnut',
        data: { labels: cats, datasets: [{ data: cats.map(c => data.byCat[c]) }] }
      });
    }
  </script>
</body>
</html>
```

## Apps Script — modal dialog form

```javascript
function showAddTxDialog() {
  const html = HtmlService.createHtmlOutput(`
    <style>body{font-family:sans-serif;padding:16px}label{display:block;margin:8px 0 4px}
    input,select,textarea{width:100%;padding:6px;box-sizing:border-box}
    .row{margin-bottom:8px}button{padding:8px 16px;background:#2563EB;color:white;
    border:none;border-radius:4px;cursor:pointer}</style>
    <h3>➕ Tambah Transaksi</h3>
    <div class="row"><label>Tanggal</label><input type="date" id="tanggal"></div>
    <div class="row"><label>Tipe</label><select id="tipe">
      <option>Pemasukan</option><option>Pengeluaran</option></select></div>
    <div class="row"><label>Kategori</label><input type="text" id="kategori" placeholder="gaji/makanan/..."></div>
    <div class="row"><label>Jumlah (Rp)</label><input type="number" id="jumlah"></div>
    <div class="row"><label>Akun</label><input type="text" id="akun" placeholder="cash/bank/ewallet"></div>
    <div class="row"><label>Catatan</label><textarea id="catatan"></textarea></div>
    <button onclick="submit()">Simpan</button>
    <script>
      function submit() {
        const data = {
          tanggal: document.getElementById('tanggal').value,
          tipe: document.getElementById('tipe').value,
          kategori: document.getElementById('kategori').value.toLowerCase(),
          jumlah: Number(document.getElementById('jumlah').value),
          akun: document.getElementById('akun').value,
          catatan: document.getElementById('catatan').value
        };
        google.script.run
          .withSuccessHandler(r => { alert('✅ Tersimpan!'); google.script.host.close(); })
          .addTransaction(data);
      }
    </script>
  `).setWidth(420).setHeight(620);
  SpreadsheetApp.getUi().showModalDialog(html, 'Tambah Transaksi');
}

function addTransaction(data) {
  const ws = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.sheetNames.transaksi);
  const lastRow = ws.getLastRow();
  ws.getRange(lastRow + 1, 1, 1, 6).setValues([[
    new Date(data.tanggal), data.tipe, data.kategori, data.jumlah, data.akun, data.catatan
  ]]);
  return {ok: true, row: lastRow + 1};
}
```

## Telegram delivery message

```python
def send_bundle(html, xlsx, gs, html2, json_, md, png, zip_path, title, user_chat):
    """Send a 3-format deliverable bundle to Telegram."""
    # Validate each
    # ...
    msg = f"""💰 {title} — 3 VERSI READY

📸 Preview:
MEDIA:{png}

📁 Files:
• {Path(html).name} ({Path(html).stat().st_size//1024} KB) — HTML standalone offline
• {Path(xlsx).name} ({Path(xlsx).stat().st_size//1024} KB) — Excel editable
• {Path(gs).name} + {Path(html2).name} ({(Path(gs).stat().st_size+Path(html2).stat().st_size)//1024} KB) — Google Sheets
• {Path(json_).name} — Sample data
• {Path(md).name} — Setup guide

📦 Bundle: MEDIA:{zip_path}

🚀 Quick start:
1. HTML: extract → double-click laporan_keuangan_v2.html
2. XLSX: open in Excel/Google Sheets → ready
3. GSheet: Extensions → Apps Script → paste Kode.gs + dashboard.html → 🚀 Setup Template
"""
    return send_message(target=f"telegram:{user_chat}", message=msg)
```

## Pitfalls recap

- JSON key: `transaksi` not `transactions` (Bahasa Indonesia)
- Category case: lowercase IDs, normalize via `.lower()`
- `merge_cells` requires column LETTERS, not tuples
- Apps Script menu needs `.addToUi()` at end of `onOpen()`
- HtmlService allows CDN for client libs
- localStorage: namespace by version
- Inlined Chart.js = 1MB+ HTML, expected
- Telegram: 50MB document, 10MB photo limit
- Sample data Title Case ("Makanan") vs dict keys lowercase ("makanan") → ALWAYS normalize
