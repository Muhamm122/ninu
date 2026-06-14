# Airdrop Intake Pattern — Image + Text Workflow

User sering submit airdrop dengan cara:
1. **Image** (project logo + funding card + investors) — extracted dari Crunchbase/rootdata
2. **Markdown text** (Register URL, steps, reward details)

Workflow: extract → verify → classify (automatable? user-only?) → response.

## Image Extraction

Gambar biasanya berisi: logo, project name, description, "Total raised: $X", investor logos (6MV, Alliance, Solana Ventures, dll).

`read_file` di image cache: `/home/ubuntu/.hermes/image_cache/img_*.jpg` (auto-discover dari user message).

Vision model: native via `vision_analyze` atau `read_file` (kalau model aktif punya vision).

## Legitimacy Quick-Check (5 fields)

```bash
# 1. Funding + investors
curl -sL "https://<domain>" -H "User-Agent: Mozilla/5.0 ..." | grep -iE "title|og:description|og:image"

# 2. Twitter / Telegram presence
curl -sIL "https://t.me/<bot>" | head -5
curl -sL "https://t.me/<bot>" | grep -iE "og:description|description"
```

Cross-check fields:
- **Project description** (Solana/EVM prediction market, yield aggregator, dll)
- **Funded date + amount** (Dec 2025 = $4.5M typical for early-2026 airdrops)
- **VC investors** (Solana Ventures, 6MV, Alliance, Multicoin, Jump, dll = legit signal)
- **Telegram bot** (real bot = `t.me/<bot>`, has `og:description` from Telegram)
- **Twitter** (from `og:description` HTML or `meta name="twitter:site"`)

## Classification Decision Tree

| Class | Signal | Action |
|---|---|---|
| **Auto-able from VPS** | Web form dengan reCAPTCHA/hCaptcha/Turnstile, no CF challenge | ohmycaptcha atau solver service |
| **Telegram bot only** | `t.me/<bot>?startapp=CODE` pattern | Telethon session (see pre-flight) |
| **Mobile-only / biometric** | "Verify your hand", palm scan, face ID | **MANUAL** — kasih step-by-step |
| **CF challenge page** | "Just a moment...", 403 dari VPS | **MANUAL** — sign up via HP/PC |
| **KYC required** | "Submit ID", Sumsub/Persona | **MANUAL** — user-only |
| **Resource-heavy** | Mining wallet, full node, RAM 4GB+ | **CHECK VPS SPECS FIRST** |

## Telegram Bot Session Pre-Flight (CRITICAL)

Sebelum bilang "gue gas pake VPS", CEK dulu:

```bash
# 1. Session file ada?
ls -la /home/ubuntu/adib_session.session /home/ubuntu/.hermes/tg*.session 2>/dev/null

# 2. API_ID + API_HASH di env?
env | grep -iE "telegram_api|tele.*hash"

# 3. Kalau env kosong — JANGAN LANJUT, tanya user dulu
```

Telethon butuh `api_id` + `api_hash` (32 char hex dari my.telegram.org/apps). Tanpa hash, session file gak bisa dipake. **Kasus umum**: session file ada, hash hilang. User harus set manual atau refresh di my.telegram.org.

```python
# Quick test pattern
from telethon import TelegramClient
import os

api_id = int(os.environ.get('TELEGRAM_API_ID', '28683464'))
api_hash = os.environ.get('TELEGRAM_API_HASH', '')

if not api_hash:
    print("STOP: API_HASH missing — need my.telegram.org/apps credentials")
    exit(1)

client = TelegramClient('/home/ubuntu/adib_session', api_id, api_hash)
await client.connect()
authorized = await client.is_user_authorized()
if not authorized:
    print("STOP: session stale — need fresh login (interactive phone code)")
    exit(1)
```

## Output Template (Indonesian, terse)

```
## 🐛 [PROJECT] — Analisis

**Project:** [chain] [category]
**Funding:** $X.XM (date) — [investor1], [investor2]
**Bot:** `[botname]` (Telegram)
**Game/Reward:** [what user actually does]

**Status gue:** ⚠️ Gak bisa automate / ✅ bisa gas
- [reason 1]
- [reason 2]

**Lo bisa gas sendiri dari [HP/Telegram desktop]:**
1. Buka link [URL] di [Telegram/browser]
2. [action 2]
3. [action 3]

**Cek hadiah** — [konversi token/USDC/nft, expected value, dll]
```

## VPS Resource Quick-Check (utk mining/wallet airdrops)

Sebelum bilang "yes, gas setup node":

```bash
echo "=== CPU ===" && lscpu | grep -E "Model name|CPU\(s\)|Thread|Core"
echo "=== RAM ===" && free -h
echo "=== DISK ===" && df -h /
echo "=== SWAP ===" && free -h | grep -i swap
```

Common gotcha: project claims "min 2GB RAM" → VPS punya 1.9GB → swap 0 → bakal OOM. **Always run this BEFORE promising setup**.

## Common Airdrop Projects yang Muncul (Q1-Q2 2026)

- **Worm WTF** (worm.wtf) — Solana prediction market, $4.5M Dec 2025, 6MV+Alliance+Solana Ventures
- **Fliply** (fliply.market) — Google sign-up + FLIP Points → $FLIP token, World Cup MEGAPOT $100K
- **ZarPay** (ref.zar.app) — mobile-only + biometric palm KYC, $1 instant Zar
- **Juno Cash** (juno.cash) — Zcash fork, CPU mining wallet, not really an airdrop
- **Polymarket** — ongoing, see `polymarket` skill

## Pitfalls

- **Don't confuse "claim instant $X" with mining/setup** — ZarPay = $1 instant; Worm = tap-tap earn points (not direct $). Different class.
- **CF-blocked ≠ broken** — site legit, just VPS IP reputation. User can access from HP.
- **Telegram session stale ≠ broken** — need API_HASH + sometimes fresh phone-code login.
- **Image OCR not perfect** — verify funding/investors via curl HTML check, don't trust image alone.
- **User prefers output `✅ bisa` / `⚠️ manual` / `❌ skip`** over long explanations.
