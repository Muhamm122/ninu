---
name: superagent-briefing
description: "Daily assistant: briefing, alerts, price monitoring. Covers crypto price alerts, stock price monitoring (Yahoo Finance API), and cron-based alert systems."
---

## What this is

Bikin bot kerasa kayak asisten harian, bukan alat panggil-pakai:
- **Daily briefing** — push ringkasan tiap pagi tanpa diminta.
- **Alert engine** — trigger persisten "kabarin kalau ...".

Scripts: `tools/briefing.py` + `tools/alerts.py`. Notifier reuse `monitoring.Notifier` (Telegram/Discord). Keyless di mana bisa (harga DexScreener, gas via RPC).

Read-only / notify-only — gak ada yang sign tx, jadi gak nyentuh governor. Begitu sebuah alert mau MEMICU aksi dana (mis. "auto-swap pas dip"), aksinya tetap lewat governor + konfirmasi.

---

## Daily briefing

Ngekompos dari yang udah ada — section tanpa data di-skip:

```
💼 Portfolio   ← inject portfolio_provider (balanceOf multicall, keyless)
⛽ Gas         ← inject gas_provider (eth_gasPrice / feeHistory, keyless)
🔔 Alert aktif ← alerts.py
🧠 Lesson      ← memory_engine (lesson terbaru)
⏳ Masih open  ← memory_engine (blocker/decision belum kelar)
📝 Proposal    ← reflection.py (yang nunggu review)
```

```python
from briefing import push_briefing
from memory_engine import MemoryEngine
from alerts import AlertEngine
from monitoring import Notifier

notifier = Notifier(telegram=(os.environ["HERMES_TG_BOT_TOKEN"], os.environ["HERMES_TG_CHAT_ID"]))
await push_briefing(notifier, memory_engine=MemoryEngine(), alert_engine=AlertEngine(),
                    portfolio_provider=my_portfolio_fn, gas_provider=my_gas_fn)
```

`once_per_day=True` (default) ada guard biar gak dobel kalau heartbeat sering. Jadwal: cron harian atau scheduler in-process.

---

## Alert engine

Trigger persisten di SQLite. Sekali set, jalan terus.

| kind | params | contoh |
|---|---|---|
| `price_below` / `price_above` | token/stock, threshold | ETH < $2000, BBRI > 3000 |
| `gas_below` / `gas_above` | chain, threshold_gwei | gas < 10 gwei |
| `wallet_activity` | wallet, chain | whale gerak |
| `claim_window` | label, opens_ts | airdrop claim buka |
| `custom` | expr | kondisi sendiri |

```python
from alerts import AlertEngine
ae = AlertEngine()
ae.add_rule("price_below", {"token": "0x...", "chain": "ethereum", "threshold": 2000},
            cooldown_s=3600, label="ETH dip")
ae.add_rule("price_above", {"stock": "BBRI.JK", "threshold": 3000},
            cooldown_s=7200, label="BBRI TP1")

# loop poll
await ae.run(notifier, poll_interval_s=60, fetchers={"gas_fn": my_gas_fn})
```

**Dedup**: tiap rule punya `cooldown_s` — alert yang udah nyala gak refire sampai cooldown lewat. Gak spam.

**Sumber data keyless**: harga default dari DexScreener (free, no key); saham dari Yahoo Finance API (free, no key — tapi rate limited & 401 untuk fundamentals).

---

## Stock Price Monitoring (Yahoo Finance)

**Pattern used for BBRI alerts:**

```python
import urllib.request, json

def get_stock_price(ticker="BBRI.JK"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        meta = data["chart"]["result"][0]["meta"]
        return {
            "price": meta.get("regularMarketPrice"),
            "prev_close": meta.get("previousClose"),
            "52w_high": meta.get("fiftyTwoWeekHigh"),
            "52w_low": meta.get("fiftyTwoWeekLow"),
            "volume": meta.get("regularMarketVolume"),
        }
```

**Limitations:**
- Yahoo Finance API is **unauthenticated** and **rate limited**
- Quote summary endpoint (`/v10/finance/quoteSummary/`) returns **401 Unauthorized** from server IPs
- Coingecko API works for crypto prices (no auth needed)
- Stooq uses JS challenge (blocked from headless)
- Finnhub requires valid API key (demo token expired)

**Alert levels pattern:**
```
STOP_LOSS:  -5% from entry (CRIT priority)
BUY_ZONE:   near support / oversold (HIGH priority)
TP1/TP2/TP3: profit targets (MED priority)
BREAKOUT:   above resistance (HIGH priority)
```

---

## Cron vs Systemd Timer for Alerts

| Pattern | Use |
|---------|-----|
| **Cron job with LLM** | When alert needs reasoning/analysis |
| **Systemd timer** | When alert runs a script (zero tokens) |
| **Cron script-only** (`no_agent=True`) | When delivering script stdout directly |

For stock price checks with alerts: use **cron with LLM** (analyzes and formats the message).

---

## Env var

```bash
export HERMES_ALERTS_DB=~/.hermes/alerts.db
export HERMES_BRIEFING_STATE=~/.hermes/briefing-last.txt
# Notifier pakai HERMES_TG_BOT_TOKEN / HERMES_TG_CHAT_ID / HERMES_DISCORD_WEBHOOK (udah ada)
```

## Trigger phrases (router)

`briefing`, `ringkasan harian`, `tiap pagi`, `alert`, `kabarin kalau`, `notify kalau`, `pantau harga`, `pasang alarm`, `monitor saham`, `cek harga`.