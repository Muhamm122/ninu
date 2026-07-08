---
name: boterdrop-solver
description: "Boterdrop-Solver — Turnstile, cf_clearance, Recaptcha V3 & AWS WAF Token solver via Camoufox + FastAPI + Playwright. Deploy dan setup di VPS"
---

# Boterdrop-Solver — Turnstile / CF Clearance / reCAPTCHA V3 / AWS WAF Token Solver

## Source
- `https://github.com/najibyahya/Boterdrop-Solver` — cloned ke `/tmp/boterdrop-solver/`
- 4 endpoint: `/turnstile`, `/clearance`, `/aws-token`, `/recaptchaV3`
- Backend: **Camoufox** (stealth browser) + **FastAPI** + **Playwright**
- Konfig: `config.json` di root

## Dependencies
```bash
python3 -m pip install fastapi==0.95.2 uvicorn "camoufox[fetch]" loguru psutil
```

## Deployment Flow
1. `git clone https://github.com/najibyahya/Boterdrop-Solver`
2. `cd Boterdrop-Solver && python3 -m venv venv && source venv/bin/activate`
3. Install dependencies
4. `python3 -m camoufox fetch` (fetch browser binary — wajib!)
5. Edit `config.json` — port, thread, proxy
6. `python3 api_server.py` — atau `uvicorn api_server:app`

## Config
```json
{
    "headless": true,
    "thread": 2,
    "page_count": 2,
    "proxy_support": true,
    "proxy_file": "proxies.txt",
    "host": "0.0.0.0",
    "port": 8003,
    "debug": false,
    "cleanup_interval_minutes": 10
}
```

## Endpoints
- `GET /turnstile?url=<TARGET>&sitekey=<SITEKEY>` — Turnstile token
- `GET /clearance?url=<TARGET>&timeout=<S>` — cf_clearance cookie
- `GET /aws-token?url=<TARGET>&timeout=<S>` — AWS WAF token
- `GET /recaptchaV3?url=<TARGET>&sitekey=<SITEKEY>` — reCAPTCHA v3
- `GET /result?id=<TASK_ID>` — polling hasil

## Polling Pattern
1. `GET /turnstile` → return `task_id` + `status: "accepted"` (202)
2. Loop `GET /result?id=<task_id>` setiap 1-2 detik
3. Sampai `status: "success"` berisi `value` (token) atau `cookies` (cf_clearance)

## Pitfalls
- **RAM**: butuh 1.2GB+ untuk browser (2 thread × 2 page). VPS <2GB = OOM.
- **fastapi version**: `fastapi>=0.100.0` gak punya `add_event_handler` — butuh **0.95.2**.
- **input**: script punya `_interactive_config` yang minta input stdin — di background mode gak bisa baca. Patch jadi `return config` langsung.
- **port**: `_check_port` juga minta input — patch jadi `return cfg` langsung.
- **proxy**: format `http://user:pass@host:port`.
- **Turnstile vs CF challenge**: Turnstile = `challenges.cloudflare.com/api.js` (JS), bukan page challenge.

## VPS Patching (non-interactive)

Banyak solver (termasuk `captcha-solver` dari Wawanahayy) punya `_interactive_config` yang butuh `input()` dari stdin. Di background mode (systemd, screen, nohup) **gak bisa baca** — error `EOFError: EOF when reading a line`.

**Fix pattern:**
1. Cari `_interactive_config` function
2. Ganti `input(...)` → `return config` langsung
3. Cari `_check_port` → ganti jadi `return cfg` (skip)
4. Hapus semua `_auto_install`, `_check_xvfb`, `_check_system` — ganti `pass`

**Contoh script fix:**
```python
# ganti _interactive_config
old = '''def _interactive_config(cfg: dict) -> dict:
    _show_config_summary(cfg)
    print()
    ans = input("  ▶  Lanjutkan? [Enter/Y = ya  |  N = ubah] : ").strip().lower()
    if ans not in ("n", "no", "tidak"):
        return cfg'''

new = '''def _interactive_config(cfg: dict) -> dict:
    return cfg'''
```

## Wawanahayy/captcha-skill (`/tmp/captcha-skill/`)

Source: `https://github.com/Wawanahayy/captcha-skill` — cloned ke `/tmp/captcha-skill/`.
Sama seperti Boterdrop-Solver tapi ada tambahan:
- **`/solve`** — LLM-based image CAPTCHA solver (via `hermes` + `--image`)
- **`POST /solve`** — `{image: base64, type: hcaptcha_image, hint: "..."}` → return `{value: ...}`
- **Samples** — `samples/` berisi test images (hcaptcha grid, math, botdetect)

### Fix yang diterapkan
- Hapus `_interactive_config` dan `_check_port` → direct run config.json
- `captcha_solver_clean.py` — versi minimal tanpa Camoufox (pake `cloudscraper`)
- Port: `8004` (default)
- Ramah RAM 1.9GB (1 thread, 1 page, ~0.3GB)

## References
- `references/turnstile-vs-challenge.md`
- `references/boterdrop-deployment.md`