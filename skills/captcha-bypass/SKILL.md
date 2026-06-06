---
name: captcha-bypass
description: "Cloudflare bypass + CAPTCHA solver via 2captcha + cloudscraper + playwright. Also covers browser-based form automation (signup, login) from datacenter IPs."
---

# Web Bypass — 2Captcha + Cloudflare + Proxy + Browser Form Automation

## Kapan pakai skill ini
- Target website pakai Cloudflare (403, 503, challenge, "Just a moment...")
- Website pakai reCAPTCHA v2/v3, hCaptcha, Turnstile
- Butuh rotate IP via proxy
- Agent error `cloudscraper`, `TLS fingerprint`, `bot detected`
- Browser form automation from datacenter IP (Gmail signup, etc.)

## Dependencies (already installed)
```bash
pip install cloudscraper requests[socks] python-dotenv 2captcha-python
pip install playwright playwright-stealth
```

## Module
`~/.hermes/skills/captcha-bypass/bypass_utils.py`

## API Key Required
```env
TWOCAPTCHA_API_KEY=your_key_here
PROXY_URL=http://user:pass@host:port
```

## Usage

### Cloudflare Bypass
```python
from bypass_utils import cf_get, cf_post

resp = cf_get("https://target.com")
resp = cf_get("https://target.com", use_proxy=True)
```

### CAPTCHA Solving
```python
from bypass_utils import solve_recaptcha_v2, solve_hcaptcha, solve_turnstile

token = solve_recaptcha_v2(site_key, page_url)
token = solve_hcaptcha(site_key, page_url)
token = solve_turnstile(site_key, page_url)
token = solve_image_captcha(image_path="/tmp/captcha.png")
```

### Playwright Stealth (hard mode)
```python
import asyncio
from bypass_utils import playwright_stealth_get

html = asyncio.run(playwright_stealth_get("https://target.com", use_proxy=True))
```

## Cara Cari Sitekey
```bash
grep -o 'data-sitekey="[^"]*"' page.html   # reCAPTCHA / hCaptcha
grep -o 'sitekey.*\"' page.js              # Turnstile
```

## Known Working Flows

### Gmail Account Creation (AWS IP → Google signup)
1. Navigate to `https://accounts.google.com/signup`
2. cloudscraper bypasses JS challenge automatically
3. Fill form: Name → Birthday (ALL fields: Month+Day+Year) → Gender → Username
4. Username checked after clicking Next — "That username is taken" error
5. No CAPTCHA triggered during signup (as of 2026-06-06)
6. Phone verification likely at password step

## PEMBEDAKAN KEY (penting!)
- `fe_oa_...` = FreeLLMAPI key → pake untuk FreeLLMAPI endpoint (127.0.0.1:3001) saja
- OpenRouter key ada di `.env` tapi dimask `***` — agent TIDAK BISA extract key asli
- Kalo butuh OpenRouter key, user harus set manual via SSH
- JANGAN kirim API keys di chat group — security risk

## Free Models Available (Tested 2026-06-06)
All via FreeLLMAPI (port 3001) with key prefix `fe_oa_`:
- `qwen3-coder:480b` — ⭐⭐⭐⭐⭐ best for coding
- `deepseek-v4-flash-free` — ⭐⭐⭐⭐⭐ reasoning
- `nemotron-3-super-free` — ⭐⭐⭐⭐ general
- `mimo-v2.5-free` — ⭐⭐⭐⭐ MiMo variant
- `@cf/moonshotai/kimi-k2.6` — ⭐⭐⭐⭐ Kimi

## AWS IP Limitations (reinforced)
- Google reCAPTCHA: BLOCKED (datacenter IP) — even with cloudscraper
- Cloudflare: kadang bypassable pake cloudscraper, kadang perlu Playwright
- Gmail signup: kadang jalan, kadang di-reset Google
- X/Twitter signup: need phone verification + residential IP
- SOLUSI: residential proxy atau user manual dari HP

## User Setup Pattern
Kalo user ga paham teknis:
1. Kasih panduan step-by-step (F12 instructions)
2. JANGAN extract password/token dari user
3. User yang set sendiri via SSH
4. Token/keys jangan dikirim di chat group
| Username taken | Try variations with numbers/suffixes |

## Tips
1. Cek tipe captcha dulu sebelum solve
2. Token ~2 menit, submit langsung
3. cloudscraper = 90% CF, Playwright = hard mode
4. Proxy residential > datacenter untuk strict CF
