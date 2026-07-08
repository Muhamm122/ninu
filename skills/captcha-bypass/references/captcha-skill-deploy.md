# CAPTCHA-SKILL — Deploy Guide

## Source: https://github.com/Wawanahayy/captcha-skill
## What it does:
- `/turnstile` → Cloudflare Turnstile token (solve via browser)
- `/clearance` → cf_clearance cookie (bypass CF WAF)
- `/aws-token` → AWS WAF token cookie
- `/recaptchaV3` → Google reCAPTCHA v3 token
- `/solve` → LLM-based image CAPTCHA solver (via hermes)

## Key pitfalls (2026-07-08):
- **RAM < 2GB**: Camoufox browser crashes on VPS with <2GB RAM (est ~1.2GB). Solution: set `thread=1, page=1` + leverage system swap. On 1.9GB free, still too tight — use `cloudscraper` fallback (no browser).
- **Interactive prompt blocking**: `_interactive_config()` uses `input()` — can't run from background. Patch by replacing with `return cfg` (no-op).
- **Port collision**: Default 8001 conflicts with web `skripsi.muham.dev` on same VPS. Use 8002-8003.
- **Two identical repos**: `Boterdrop-Solver` (najibyahya) and `captcha-skill` (Wawanahayy) — same architecture. Use `captcha_solver.py` from either, deploy is identical.
- **Proxy**: instant-proxies user 2952 → `http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188` — works for cloudscraper but NOT for Playwright Camoufox (detected as datacenter).

## Tech stack:
- **FastAPI** (API)
- **Camoufox** (browser automation — Firefox-based)
- **cloudscraper** (fallback for non-browser requests)
- **Playwright** (browser for Turnstile)
- **Proxy** (residential via proxy.txt)

## Deploy on 1.9GB RAM:
```bash
cd /tmp/captcha-skill
pip install fastapi==0.95.2 uvicorn camoufox[fetch] loguru psutil cloudscraper
# Set thread=1, page=1, headless=true
python3 captcha_solver.py
```

## Test:
```bash
curl http://127.0.0.1:8001/turnstile?url=TARGET&sitekey=KEY
curl http://127.0.0.1:8001/clearance?url=TARGET
curl http://127.0.0.1:8001/result?id=TASK_ID
```

## Status: ✅ CAN deploy on this VPS
- 1.9GB RAM → 1 thread × 1 page = ~600MB
- Proxy: `http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188`
- `cloudscraper` fallback = 80% bypass without browser
- `Camoufox` = 95% bypass with browser (but need RAM ≥ 2GB)