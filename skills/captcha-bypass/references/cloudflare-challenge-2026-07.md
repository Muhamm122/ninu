# Cloudflare Challenge Bypass — 2026-07 Session Findings

## Validated Approach

When residential proxy is available:

1. **cloudscraper + residential proxy** (primary)
   - Highest success rate on "Just a moment" pages
   - Lightweight and fast
   - Validated on 10 GSuite accounts → 10/10 success

2. **Playwright stealth** (fallback)
   - Only needed when cloudscraper fails
   - Higher resource cost

3. **Widget solvers** (2captcha, ohmycaptcha)
   - Only for reCAPTCHA/hCaptcha/Turnstile widgets
   - Not effective against full Cloudflare challenge pages

## Proxy Used
- `instant-proxies` (US residential) — highly effective

## Key Lesson
Do not default to Playwright for Cloudflare challenges when residential proxy + cloudscraper is available. The latter is faster and more reliable in this environment.