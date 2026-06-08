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
`~/.hermes/skills/superagent/tools/sctg_solver.py` — SCTG CLI solver

See `references/sctg-solver.md` for full SCTG API docs, pricing, and integration.
See `references/vinci-world-otp.md` for Vinci World OTP login flow details and DOM structure.
See `references/gmail-oauth-vs-app-password-vps.md` for a detailed failure log of every OAuth approach from VPS and why App Password is the only viable path for personal Gmail.
See `references/airdrop-api-discovery.md` for the pattern of discovering REST API endpoints from airdrop/Web3 sites via `performance.getEntriesByType()` and inline `<script>` analysis — faster than browser form submission.

## API Keys Required
```env
# Priority: YesCaptcha (paid, reliable) > SCTG (cheap, more types) > 2captcha (fallback)
YESCAPTCHA_KEY=your_yescaptcha_key      # api.yescaptcha.com — paid, $15+ balance
SCTG_API_KEY=your_sctg_key_here        # sctg.xyz — 2captcha-compatible, 35+ types
SCTG_ENDPOINT=https://sctg.xyz         # or ru.sctg.xyz / api.sctg.xyz
TWOCAPTCHA_API_KEY=your_2captcha_key   # fallback if no SCTG
PROXY_URL=http://user:pass@host:port
```

### YesCaptcha (primary for paid solving)
- **Endpoint**: `https://api.yescaptcha.com`
- **API**: `createTask` / `getTaskResult` (anticaptcha-compatible, NOT 2captcha format)
- **Tool**: `~/.hermes/skills/superagent/tools/captcha.py`
- **Balance check**: `python3 captcha.py balance`
- **Pricing**: ReCaptcha v2 ~$2/1K, hCaptcha ~$2/1K, Turnstile ~$2/1K, Image ~$1/1K, FunCaptcha ~$3/1K

### YesCaptcha Task Types
| Type | Task Type String | Use Case |
|------|------------------|----------|
| ReCaptcha v2 | `NoCaptchaTaskProxyless` | Google reCAPTCHA v2 |
| ReCaptcha v3 | `RecaptchaV3TaskProxyless` | Score-based reCAPTCHA |
| hCaptcha | `HCaptchaTaskProxyless` | hCaptcha (NVIDIA, many modern sites) |
| Turnstile | `TurnstileTaskProxyless` | Cloudflare Turnstile |
| Image | `ImageToTextTask` | Image/text CAPTCHA |
| FunCaptcha | `FunCaptchaTaskProxyless` | Arkose Labs / FunCaptcha |

### YesCaptcha Python API
```python
from bypass_utils import yes_solve, yes_balance

# Check balance (returns USD)
balance = yes_balance()  # e.g. 15.0

# Solve ReCaptcha v2
result = yes_solve('NoCaptchaTaskProxyless', website_url, website_key)
token = result['solution']['gRecaptchaResponse']

# Solve hCaptcha
result = yes_solve('HCaptchaTaskProxyless', website_url, website_key)
token = result['solution']['gRecaptchaResponse']

# Solve Turnstile
result = yes_solve('TurnstileTaskProxyless', website_url, website_key)
token = result['solution']['token']
```

**SCTG is cheaper** but YesCaptcha is more reliable for paid solving. Use YesCaptcha when balance > $0 and you need guaranteed solves.

### SCTG Pricing (per 1000 solves)
| Type | Price | Type | Price |
|------|-------|------|-------|
| ReCaptcha v2 | $0.07 | ReCaptcha v3 | $0.40 |
| hCaptcha | $0.015 | Turnstile | $0.22 |
| Image/Text | $0.015 | Yandex SC | $0.05 |
| GeeTest | $0.015 | FunCaptcha | $0.10 |
| Slider | $0.015 | AuthKong | $0.10 |
| LLM AI | $0.10 | Protonmail | $0.015 |

### SCTG CLI
```bash
python3 ~/.hermes/skills/superagent/tools/sctg_solver.py --balance
python3 ~/.hermes/skills/superagent/tools/sctg_solver.py --type recaptcha_v2 --sitekey KEY --url URL
python3 ~/.hermes/skills/superagent/tools/sctg_solver.py --type hcaptcha --sitekey KEY --url URL
python3 ~/.hermes/skills/superagent/tools/sctg_solver.py --type turnstile --sitekey KEY --url URL
python3 ~/.hermes/skills/superagent/tools/sctg_solver.py --type image --file captcha.png
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

### Playwright Stealth (hard mode) — CORRECT API
```python
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # Class, NOT function!

async def stealth_get(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox',
                  '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
        )
        page = await context.new_page()
        
        # CORRECT: Stealth() class with NO positional args + apply_stealth_async(page)
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        await page.goto(url, wait_until='networkidle', timeout=60000)
        content = await page.content()
        await browser.close()
        return content
```

**WRONG patterns (do NOT use):**
- `from playwright_stealth import stealth_async` — doesn't exist
- `await stealth_async(page)` — wrong, it's a module not function
- `stealth = Stealth(page)` — wrong, Stealth() takes keyword-only args
- `await stealth.apply_stealth_sync(page)` — wrong in async context

## Cara Cari Sitekey
```bash
grep -o 'data-sitekey="[^"]*"' page.html   # reCAPTCHA / hCaptcha
grep -o 'sitekey.*\"' page.js              # Turnstile
```

## Known Working Flows

### Gmail Account Creation (AWS IP → Google signup)
1. Navigate to `https://accounts.google.com/signup`
2. Playwright Stealth (`Stealth()` + `apply_stealth_async`) bypasses JS challenge
3. Fill form: Name → Birthday → Gender → Username
4. **Birthday step REACHED** with Playwright Stealth (cloudscraper fails at 400)
5. **Birthday form uses custom combobox** (NOT `<select>`) — need click-based interaction:
   - Click `combobox "Month"` → select option from dropdown list
   - Fill `textbox "Day"` and `textbox "Year"`
6. Username checked after clicking Next — "That username is taken" error
7. No CAPTCHA triggered during signup (as of 2026-06-06)
8. Phone verification likely at password step

### GitHub SSH Key Setup (for auto-backup)
```bash
# Generate key
ssh-keygen -t ed25519 -C "agent-name" -f ~/.ssh/id_ed25519 -N ""

# Add public key to GitHub → Settings → SSH Keys → New SSH key
# Test: ssh -T git@github.com -o StrictHostKeyChecking=no
# Setup: git remote add origin git@github.com:USERNAME/REPO.git
```

## PEMBEDAKAN KEY (penting!)
- `fe_oa_...` = FreeLLMAPI key → untuk FreeLLMAPI endpoint (127.0.0.1:3001) saja
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
- Gmail signup: Playwright Stealth reaches birthday, but custom dropdowns are problematic
- X/Twitter signup: need phone verification + residential IP
- **Vinci World / Web3 OTP login**: WORKS from AWS IP — email OTP method functions fine; no CAPTCHA triggered
- **NVIDIA build.nvidia.com**: hCaptcha + AWS IP = BLOCKED — user must register from phone/PC
- **GCP Console (console.cloud.google.com)**: "This browser or app may not be secure" — BLOCKED from AWS IP, even with Playwright Stealth. Cannot login to manage IAM, enable APIs, or create OAuth credentials from VPS.
- SOLUSI: residential proxy atau user manual dari HP
- EXCEPT: Web3/OTP-based sites (Vinci World, etc.) work without proxy

### ⛔ Datacenter IP Hard Blocks (CAPTCHA solver CANNOT fix these)

These are **IP reputation blocks** that happen BEFORE any CAPTCHA is shown. YesCaptcha/SCTG cannot solve them because there is no CAPTCHA to solve — the server rejects the IP outright.

| Platform | Error Message | Block Level | Only Fix |
|----------|---------------|-------------|----------|
| **Gmail signup** | "Sorry, we could not create your Google Account" | After password step | Residential proxy only |
| **X/Twitter signup** | "Sorry, you are not allowed to log in at this time" | At phone step | Residential proxy only |
| **X/Twitter landing form** | Login form renders, "Continue" button present but click does nothing | Unauthenticated x.com from datacenter IP | Residential proxy only |
| **X/Twitter SPA render** | Page loads (HTTP 200) but zero tweets, zero GraphQL calls, React never hydrates | Any authenticated X page from datacenter IP | Residential proxy only; WARP may improve |
| **X/Twitter httpOnly cookies** | Hermes Playwright has no CDP port access; document.cookie can't set httpOnly cookies | All X browser auth from VPS | Use x_tool.py (requests) instead; works with or without WARP |
| **X/Twitter v1.1 API** | `api.x.com/1.1/` endpoints return 404 (not 401) — fully decommissioned as of 2026-06 | Any code using v1.1 REST endpoints | Use GraphQL (`api.x.com/graphql/`) exclusively |
| **Google OAuth login** | "This browser or app may not be secure" | At email entry | Residential proxy only |
| **NVIDIA NIM** | hCaptcha loop / block | At signup | Residential proxy or manual from phone |

**Key insight**: Even with YesCaptcha ($15 balance) + CloakBrowser stealth + correct form filling, Google/X block account creation from known datacenter IPs. The block is on the SERVER side — the IP is in a datacenter ASN list. No amount of browser fingerprinting or CAPTCHA solving fixes this.

## Security — NEVER Accept User Passwords

If the user sends a password in chat:
1. **Refuse it** — state clearly you cannot accept passwords per policy
2. Guide them to set it themselves via SSH or their own device
3. Only accept API keys (not login credentials) — those are safe to store in `.env`
4. For OAuth/signups requiring passwords: user must do it on their own device

This applies to ALL services — NVIDIA, Google, X/Twitter, email, proxy, etc. No exceptions.

### Redirect pattern after password refusal
When the user asks for account creation that needs a password you can't accept:
1. Refuse the password (step above)
2. **Propose alternatives that work without passwords:**
   - Email OTP login (Vinci World pattern) — you enter email, user gives OTP
   - API key auth — user creates account on their device, gives you the API key
   - Wallet connect — if MetaMask/wallet extension is available
3. If no alternative works, give the user a **2-minute manual step** (open URL on phone, create account, paste result back)
4. Never leave the user with just a "can't do" — always provide a path forward

## User Setup Pattern
Kalo user ga paham teknis:
1. Kasih panduan step-by-step (F12 instructions)
2. JANGAN extract password/token dari user
3. User yang set sendiri via SSH
4. Token/keys jangan dikirim di chat group

## Troubleshooting
| Error | Fix |
|-------|-----|
| `Unable to handle challenge` | Pakai Playwright Stealth |
| `ERROR_ZERO_BALANCE` | Top up 2captcha.com |
| `ERROR_CAPTCHA_UNSOLVABLE` | Retry atau ganti metode |
| `ProxyError` | Cek PROXY_URL format |
| `TypeError: Stealth.__init__() takes 1 positional arg` | Use `Stealth()` with NO args, then `await stealth.apply_stealth_async(page)` |
| `cannot import name stealth_async` | Import `Stealth` class, not `stealth_async` |
| `Page.click: Timeout` on Google dropdown | Google uses custom combobox, not `<select>` — use `page.click('combobox')` then select from list |
| `400 Bad Request` on Google form POST | Use browser automation instead of cloudscraper for form submission |
| Username taken | Try variations with numbers/suffixes |
| SCTG `ERROR_ZERO_BALANCE` | Top up at sctg.xyz (via bot or support) |
| SCTG balance negative | Same — needs top up before solving |

## OTP-Based Auth Flows (e.g., Vinci World, Magic Links)

Many Web3 and modern apps use **email OTP** instead of password login.

### Preferred: Auto-OTP via IMAP Polling

When you have IMAP access to the user's Gmail (App Password configured), **automate the OTP retrieval** — don't ask the user for the code. This is especially useful for Privy.io-powered Web3 sites (Vinci World, etc.).

Full pattern in `references/vinci-world-otp.md` and `superagent-web3` skill `references/airdrop-research-pattern.md` Step 7c.

**✅ Auto-OTP proven working** — fully automated Vinci World registration completed with zero user input:
1. Navigate to target → Login → Email field → type `adibmuhadi@gmail.com` → click **"Send OTP"**
2. IMAP poll loop (every 5s, 90s max) finds OTP email from `no-reply@privy.io` (Privy.io sends for many Web3 sites)
3. Regex `r'\b(\d{6})\b'` extracts code from email body
4. Type 6 digits into separate input fields via `browser_type` ref
5. Page auto-submits → logged in. **Entire flow: ~15 seconds, zero user interaction.**

Key implementation details:
- Gmail App Password stored in himalaya config (`~/.config/himalaya/config.toml` → `passwd-cmd`)
- Some OTP emails come from **Privy.io** (`no-reply@privy.io`) not the target domain — search by `(FROM "privy.io")` not `(FROM "vinciworld")`
- OTP email subject format: `"Your login code for <AppName>"` where AppName may differ from domain (Renaiss for Vinci World)
- IMAP search `(FROM "privy.io")` is more reliable than `(SUBJECT "Vinci")` for Privy-powered sites
- After entering OTP, check `document.body.innerText` for success text like "You're on the list!" rather than relying on DOM snapshots

Quick version:
```python
# After clicking "Send OTP" in browser, poll IMAP for the code:
import imaplib, email, re, time
def poll_otp(email_addr, app_password, from_filter="privy.io", max_wait=90):
    seen = set()
    start = time.time()
    while time.time() - start < max_wait:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_addr, app_password)
        mail.select('INBOX')
        _, data = mail.search(None, f'(FROM "{from_filter}")')
        for eid in reversed(data[0].split()):
            eid_str = eid.decode()
            if eid_str in seen: continue
            seen.add(eid_str)
            _, msg_data = mail.fetch(eid, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            body = ''.join(p.get_payload(decode=True).decode(errors='ignore') 
                          for p in msg.walk() if p.get_content_type() == 'text/plain') or \
                   ''.join(p.get_payload(decode=True).decode(errors='ignore')
                          for p in msg.walk() if p.get_content_type() == 'text/html')
            otp = re.search(r'\b(\d{6})\b', body)
            if otp: mail.logout(); return otp.group(1)
        mail.logout(); time.sleep(5)
    return None
```

### Fallback: Manual OTP

If no IMAP access, use this flow:

1. Enter email in textbox → click **"Send OTP"** / **"Send Code"**
2. Page shows 6-digit input fields (one per digit) or a single code field
3. Ask user to check email and provide the code
4. Enter code — **digit-by-digit** if separate inputs, or all at once if single field
5. Page may auto-submit on last digit, or may need explicit submit

### OTP Timing Pitfalls — CRITICAL
- ⚠️ **OTP expires fast** — typically 60–120 seconds. Tell the user to check email IMMEDIATELY and respond with the code ASAP.
- ⚠️ **Resend invalidates old code** — if you click "Resend", the previous code is dead. The user MUST check for the NEW email, not reuse the old code.
- ⚠️ **Page navigation loses state** — if you navigate away or reload, the OTP session may reset. Avoid `browser_navigate` again unless the page is truly gone; use `browser_snapshot` to check state instead.
- ⚠️ **Ref IDs expire** — OTP digit fields may lose their ref IDs after a few seconds. If typing fails, re-snapshot and get fresh refs.
- ⚠️ **Never re-enter an old OTP after page reload** — if you had to reload the page, the old OTP is guaranteed invalid (new session). You MUST Send OTP again and wait for the user to give you the new code. Entering a stale code wastes the user's time and shows an "Invalid" error.
- ⚠️ **Coordinate BEFORE sending OTP** — tell the user "I'm about to send OTP, check your email NOW and reply with the 6-digit code immediately." Then send. This avoids the common failure mode where OTP is sent, then you explain, then the user checks email 30+ seconds later and the code is already expired.
- ⚠️ **"Gmail creation" requests may actually need OAuth** — if the user gives a GCP project URL or asks to "implement OAuth Gmail", they want API-based email access (google-workspace skill), not a new Gmail account. Detect `console.cloud.google.com` URLs or mentions of `serviceaccounts`, `OAuth client ID`, or `credentials` as signals for OAuth setup, not account creation.
- ⚠️ **GCP API key ≠ Gmail access** — if the user provides a GCP API key (format `AIzaSy...`) for Gmail, it will NOT work. Gmail API requires OAuth2. API keys only work for non-identity APIs (Maps, YouTube, Translate). Redirect user to create OAuth Client ID + Secret instead.
- ⚠️ **Service Account email ≠ personal Gmail access** — if the user provides a Service Account email (format `name@project.iam.gserviceaccount.com`) or numeric SA ID, it does NOT grant access to personal `@gmail.com` inboxes. Service Accounts only work with Google Workspace (business) via domain-wide delegation. Redirect to OAuth Desktop App flow.
- ⚠️ **User may provide credentials incrementally** — they might first give an API key, then a SA email, then finally the OAuth Client ID + Secret. Be patient, explain why each doesn't work for Gmail, and keep guiding them toward OAuth Client ID + Client Secret.
- ⚠️ **OAuth 403 `access_denied` / "app hasn't completed verification"** — the OAuth app is in Testing mode and the user's email is not in the test users list. Fix: User adds their email as test user at `https://console.cloud.google.com/auth/audience?project=PROJECT_ID`, then retries the auth URL.
- ⚠️ **GCP project access denied** — if user gets "You need additional access to the project" in console, they're not owner/editor. Redirect to project list `https://console.cloud.google.com/iam-admin/projects` or create new project.
- ⚠️ **Client ID ≠ enough** — OAuth Client ID alone is insufficient. Must also have Client Secret (format `GOCSPX-xxxxx`). If user only provides Client ID, explicitly ask: "I also need the Client Secret from the same page."
- ⚠️ **OOB redirect is dead for unverified apps** — `urn:ietf:wg:oauth:2.0:oob` returns `access_denied` for apps in Testing mode. Use `redirect_uri=http://localhost:PORT` instead, and tell the user to copy the full redirect URL from the address bar (page won't load, but URL contains the auth code).
- ⚠️ **When OAuth is a dead end, offer App Password** — If the user only needs email (read/send/search), not Calendar/Drive, skip the entire OAuth dance and direct them to Gmail App Password: (1) Enable 2-FA at myaccount.google.com/security (2) Create App Password at myaccount.google.com/apppasswords (3) Use with IMAP/SMTP via himalaya skill or `scripts/gmail.py`. **2-FA must be enabled first or App Password creation is unavailable.** If IMAP login fails with `AUTHENTICATIONFAILED`, first suspect: 2-FA is off.
- ⚠️ **Gmail access decision tree** — When user wants Gmail access, choose the shortest path:
  1. **Need only email (read/send/search)?** → App Password + IMAP/SMTP (2 min setup, no GCP needed)
  2. **Need Calendar/Drive/Sheets too?** → OAuth (but must be done from user's device, not VPS)
  3. **User gives GCP API key?** → Explain it won't work for Gmail, redirect to App Password
  4. **User gives Service Account email?** → Explain it won't work for @gmail.com, redirect to App Password
  5. **User gives just Client ID?** → Ask for Client Secret too, then guide OAuth from their device
  6. **OAuth 403 access_denied?** → Add user as test user in Consent Screen, OR switch to App Password

### Entering OTP Digit-by-Digit
When the page has separate `<input>` per digit (e.g., `textbox "Digit 1 of 6"` through `textbox "Digit 6 of 6"`):
```python
# Each digit goes in its own field
digits = "550633"
for i, d in enumerate(digits):
    browser_type(ref=digit_refs[i], text=d)
# May auto-submit after last digit — snapshot to check result
```

If typing into digit fields fails (ref expired), re-snapshot first.

### OTP Flow Checklist
1. ⬜ **Pre-coordinate**: Tell user "I'll send OTP now — check email IMMEDIATELY and reply with the code"
2. ⬜ Enter email → Send OTP
3. ⬜ Re-snapshot to confirm OTP input page appeared
4. ⬜ Wait for user to provide code (remind: ~60s expiry)
5. ⬜ Re-snapshot to get fresh refs (may have expired while waiting)
6. ⬜ Enter code digit-by-digit or bulk
7. ⬜ Snapshot result — check for "Invalid" error or success redirect
8. ⬜ If "Invalid": you MUST re-send OTP (old code is dead), tell user to check for NEW email, repeat from step 4

## CDP (Chrome DevTools Protocol) — Advanced Browser Control

CDP gives raw WebSocket access to Chrome's internals via Playwright's `context.new_cdp_session(page)`. Use for tasks impossible via standard Playwright API.

### 5 Key CDP Features (Verified Working)

| Feature | Method | Use Case |
|---------|--------|----------|
| **Inject httpOnly cookies** | `Network.setCookie` | auth_token for X/Twitter — JS `document.cookie` CANNOT set httpOnly cookies |
| **Monitor all requests** | `Network.enable` + `Network.requestWillBeSent` | Intercept X GraphQL API calls → extract fresh QIDs |
| **Anti-detection JS** | `Page.addScriptToEvaluateOnNewDocument` | Runs BEFORE any page script; removes `navigator.webdriver`, fakes plugins/languages |
| **Fake device** | `Emulation.setDeviceMetricsOverride` | Pretend to be iPhone, desktop, or any resolution |
| **Intercept & modify requests** | `Fetch.enable` + `Fetch.requestPaused` | Modify headers, block requests, inject custom headers |

### Setup Pattern
```python
cdp = await context.new_cdp_session(page)

# 1. Inject httpOnly cookies (THE killer feature)
for cookie in cookies:
    await cdp.send('Network.setCookie', cookie)

# 2. Anti-detection JS (before page loads)
await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
    'source': 'Object.defineProperty(navigator,"webdriver",{get:()=>undefined});'
})

# 3. Monitor requests
await cdp.send('Network.enable')
cdp.on('Network.requestWillBeSent', handler)

# 4. Fake device
await cdp.send('Emulation.setDeviceMetricsOverride', {
    'mobile': True, 'width': 375, 'height': 812, 'deviceScaleFactor': 3
})

# 5. Intercept requests
await cdp.send('Fetch.enable', {'patterns': [{'urlPattern': '*'}]})
# Handler must call cdp.send('Fetch.continueRequest', {'requestId': id}) — don't block!
```

### ⚠️ Fetch.continueRequest Error
When handling `Fetch.requestPaused`, ALWAYS call `Fetch.continueRequest` with the exact `requestId` from the event. Passing wrong parameters causes: `Protocol error (Fetch.continueRequest): Invalid parameters`. Do NOT block requests unless explicitly intended.

### CDP Tool Location
Full CDP stealth browser class: `~/.hermes/skills/superagent/tools/cdp_stealth.py`

### When to Use CDP
1. Injecting httpOnly auth cookies (X/Twitter login)
2. Intercepting GraphQL calls to get fresh QIDs
3. Anti-detection fingerprint override
4. Modifying request headers mid-flight
5. Fake device metrics beyond Playwright's API

### ⚠️ CDP Limitations (from testing)
- **CDP works 100%** — all 5 features verified on example.com, httpbin, outworlders.xyz
- **BUT**: X/Twitter SPA still won't render from datacenter IPs even with CDP — IP-level block is the bottleneck, not browser fingerprinting
- **Playwright + datacenter proxy** = too slow (timeouts on 20s default)
- **Playwright + residential proxy** = works (needs real residential IP)
- **`Emulation.setLocaleOverride`** fails if Playwright context already set locale (error: "Another locale override is already in effect") — set locale via Playwright API only, not CDP

## Tips
1. Cek tipe captcha dulu sebelum solve
2. Token ~2 menit, submit langsung
3. cloudscraper = 90% CF, Playwright = hard mode
4. Proxy residential > datacenter untuk strict CF
5. Google custom dropdowns: click combobox → wait for list → click option (NOT select_option)
6. OTP auth: always tell user code expires ~60s, resend kills old code, re-snapshot before entering
7. CDP for httpOnly cookie injection — only way to inject auth_token for X/Twitter browser login
8. For X/Twitter: even with CDP, residential proxy is required for SPA rendering — datacenter IP = empty page