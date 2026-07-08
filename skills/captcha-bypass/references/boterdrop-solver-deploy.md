# Boterdrop-Solver Deployment Guide

## Source
`github.com/najibyahya/Boterdrop-Solver` — Turnstile + cf_clearance + AWS WAF + reCAPTCHA v3 solver

## Architecture
- **FastAPI** (v0.95.2) — REST API server
- **Camoufox** (v0.4.11) — Stealth browser (Playwright-based)
- **Async** — Non-blocking task queue

## Endpoints
| Endpoint | Method | Params | Description |
|----------|--------|--------|-------------|
| `/turnstile` | GET | `url`, `sitekey` | Cloudflare Turnstile token |
| `/clearance` | GET | `url` | cf_clearance cookie |
| `/aws-token` | GET | `url` | AWS WAF token |
| `/recaptchaV3` | GET/POST | `url`, `sitekey` | reCAPTCHA v3 |

## Deployment

```bash
# Config
{"headless": true, "thread": 2, "page_count": 2, "port": 8001}

# Run
python3 api_server.py
```

## Fixes Required (on 1.9GB VPS)

| Issue | Fix |
|-------|-----|
| `input()` on no-interactive | Remove `_interactive_config()` — use config directly |
| Port 8001 in use | Change to 8002 |
| `fastapi` v0.139 no `add_event_handler` | Downgrade to `fastapi==0.95.2` |
| RAM < 2GB | Set `thread=1`, `page_count=1` |
| `loguru` missing | `pip install loguru` |

## Test Results (2026-07-08)

| Target | Method | Result |
|--------|--------|--------|
| `challenges.cloudflare.com` | cloudscraper | ✅ 200 (Turnstile page visible) |
| `namecheap.com` | cloudscraper + proxy | ❌ 403 (CF block) |
| `namecheap.com` | Playwright + proxy | ❌ timeout |

## Limitation
- Camoufox/Playwright **cannot run on <2GB RAM** VPS
- For RAM-constrained: use `cloudscraper` + `requests` only (no browser)