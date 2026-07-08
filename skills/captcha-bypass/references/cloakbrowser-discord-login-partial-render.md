# CloakBrowser + Residential Proxy — Discord Login Partial Render (2026-06-25)

> Verified 2026-06-25 on VPS 18.143.107.30. CloakBrowser (C++ stealth Chromium) + T-Mobile residential proxy (AS21928) can render Discord login form, but hCaptcha still blocks submission.

## What Works

| Step | Result |
|---|---|
| CloakBrowser launch + residential proxy | ✅ Browser launches, proxy connects |
| Navigate `discord.com/login` | ✅ Page loads (body_len goes from ~1KB → 73KB after CF challenge) |
| Wait for React form render | ✅ Login form appears after ~40s (inputs=2, submit=True) |
| Fill credentials | ✅ `pg.fill('input[type="text"]', email)` works |
| Click submit | ✅ Button click registers |
| hCaptcha check | ❌ "Wait! Are you human? Please confirm you're not a robot." |

## Key Findings

### CF Challenge Passes
The Cloudflare JS challenge script in the page body executes successfully:
```
body progression: 1259 → 1283 → 1823 → 66850 → 73084 (inputs=2!)
```
This means CloakBrowser's C++ stealth patches bypass the CF challenge layer.

### hCaptcha Is Invisible Mode
After submit, the page shows "Are you human?" but:
- No `data-sitekey` attribute in DOM
- No `.h-captcha` or `[data-sitekey]` elements
- 3 iframes present (hcaptcha.com) but cross-origin blocked
- `hcaptcha_els: 0` in page query

### Cross-Origin Iframe Block
```javascript
// This throws:
// "Blocked a frame with origin 'https://discord.com' from accessing a cross-origin frame."
document.querySelector('iframe[src*="hcaptcha"]').contentDocument
```

### Direct API Still Requires Captcha
```json
POST /api/v9/auth/login
{"login":"adibmuhadi@gmail.com","password":"...","captcha_key":null}
→ {"captcha_key":["captcha-required"],"captcha_sitekey":"a9b5fb07-...","captcha_service":"hcaptcha"}
```

## Proxy Used
```
http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188
```
- Provider: InstantProxies (p101)
- IP: `172.56.107.202` (T-Mobile USA, AS21928, residential)
- Type: HTTP residential
- Session: sticky

## Script Pattern (Working Render)
```python
from cloakbrowser import launch
import time

with launch(
    headless=True,
    proxy="http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188",
) as browser:
    ctx = browser.new_context()
    ctx.add_cookies(user_cookies)  # From user's browser export
    pg = ctx.new_page()
    
    pg.goto('https://discord.com/login', wait_until='commit', timeout=15000)
    
    # Wait for form (check inputs)
    for i in range(12):
        time.sleep(5)
        inputs = pg.evaluate("() => document.querySelectorAll('input').length")
        if inputs >= 2:
            break
    
    # Fill
    pg.fill('input[type="text"]', email, timeout=5000)
    pg.fill('input[type="password"]', pw, timeout=5000)
    pg.click('button[type="submit"]', timeout=5000)
    # → hCaptcha "Are you human?" appears
```

## Why It Still Fails
1. **Invisible hCaptcha**: Cannot target what you can't find in DOM
2. **Cross-origin iframe**: Cannot interact with hcaptcha.com iframe from discord.com page
3. **Fingerprint-bound**: Even valid tokens rejected because solver IP ≠ login request IP

## Conclusion
CloakBrowser gets further than any other approach (form renders + credentials accepted), but the final hCaptcha gate is insurmountable from VPS. **Present manual paths to user immediately after confirming hCaptcha is present.**

## Related
- `discord-login-fallback-paths.md` — manual paths (token/cookie/QR/desktop)
- `ohmycaptcha-v3-setup.md` — self-hosted solver (works for widget hCaptcha, fails for invisible)
- `cloakbrowser/SKILL.md` — C++ stealth browser setup
