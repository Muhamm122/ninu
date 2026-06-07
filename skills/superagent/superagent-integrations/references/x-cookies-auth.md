# X/Twitter Cookies-Based Auth (Internal API)

## When to Use This Over xurl

| Method | Auth | API Surface | Cost | Limits |
|--------|------|-------------|------|--------|
| **xurl** (official) | OAuth 2.0 PKCE | v2 REST | Paid ($100/mo basic) | Per-endpoint rate limits |
| **Cookies** (internal) | auth_token + ct0 | Undocumented GraphQL | Free | ~344 actions/day per account |

Use cookies-based auth when:
- No X developer account / API credits available
- Need to post/like/follow without paying for API access
- Building automation that mirrors browser behavior
- Multi-account rotation for garapan/engagement tasks

## Cookie Acquisition

1. User logs into X in their browser (phone or PC)
2. Open DevTools → Application → Cookies → `.x.com`
3. Copy `auth_token` (httpOnly) and `ct0` values
4. Export as JSON via cookie manager extension, or copy-paste the two values

**Key cookies:**
- `auth_token` — httpOnly, long-lived session token (~2 weeks)
- `ct0` — CSRF token, required as `X-Csrf-Token` header AND cookie on every request
- `twid` — `u%3D<user_id>`, identifies the logged-in user

## Profile Verification Pattern

Fetch `x.com/home` with cookies set. If valid, the page contains `screen_name` in embedded JSON:

```python
import requests, re

s = requests.Session()
s.cookies.set('auth_token', AUTH_TOKEN, domain='.x.com')
s.cookies.set('ct0', CT0, domain='.x.com')
s.cookies.set('twid', f'u%3D{USER_ID}', domain='.x.com')

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

# DO NOT set Authorization header on page requests — it conflicts with cookie auth
r = s.get('https://x.com/home', headers={'User-Agent': UA}, timeout=10)

handle = re.search(r'"screen_name":"(\w+)"', r.text)
if handle:
    print(f"Logged in as @{handle.group(1)}")
else:
    print("Cookies expired or invalid")
```

## Common Pitfalls

1. **Authorization header conflict**: Setting `Authorization: Bearer *** alongside cookies on `x.com/home` page requests causes the server to reject. Remove the Authorization header for page-level requests; only add it for `api.x.com/graphql/...` calls.

2. **GraphQL queryId expiration**: QueryIds (e.g. `H-t2v_HvFR07ZBP9aOeKoA` for CreateTweet) change on every X frontend deploy. Hard-coded IDs break after days/weeks. More robust: scrape current queryIds from the JS bundle at `https://x.com` at session start.

3. **v1.1 REST endpoints gone**: `api.x.com/1.1/account/verify_credentials.json` and `api.x.com/1.1/guest/activate.json` return 404. Use GraphQL or page-scraping.

4. **Guest token activation 404**: The `/1.1/guest/activate.json` endpoint is gone. Don't rely on it.

5. **Cookie expiry**: `auth_token` lasts ~2 weeks. When `x.com/home` doesn't contain `screen_name`, cookies expired — user must re-extract from browser.

6. **httpOnly cookies**: `auth_token` cannot be set via `document.cookie` in browser automation. Must use Playwright `context.add_cookies()` or CDP.

7. **Datacenter IP blocks on login**: X blocks login/signup from datacenter IPs ("not allowed to log in at this time"). Cookies extracted from a residential IP still work from datacenter IPs for API calls — the block is on the login gate, not on authenticated requests.

## Bearer Token (public, not a secret)

```
AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA
```

Embedded in every X page. Can be dynamically extracted from the JS bundle for resilience against rotation.

## Browser Cookie Injection (Playwright)

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()
    await context.add_cookies([
        {"name": "auth_token", "value": AUTH_TOKEN, "domain": ".x.com",
         "path": "/", "secure": True, "httpOnly": True, "sameSite": "None"},
        {"name": "ct0", "value": CT0, "domain": ".x.com",
         "path": "/", "secure": True, "httpOnly": False, "sameSite": "Lax"},
    ])
    page = await context.new_page()
    await page.goto('https://x.com/home')
    # Page shows logged-in timeline
```

## Storage Convention

```
~/.hermes/x-cookies.json  — full cookie set (for browser injection)
<project>/.env            — X_AUTH_TOKEN=*** and X_CT0=... (for API scripts)
# NEVER commit cookies to git — add to .gitignore
```

## x_auto.py Architecture (x-actions repo)

Multi-account GraphQL automation:
- Different accounts for different garapan (NOT rotation within same task)
- Auto warm-up (first post is benign "gm ☀️" style)
- Rate limit tracking (344 daily limit per account)
- Fallback to browser DOM injection on 344/226 API errors
- QueryIds: `CreateTweet=H-t2v_HvFR07ZBP9aOeKoA`, etc.

Account config in `.env`:
```
X_AUTH_TOKEN=<auth_token_value>
X_CT0=<ct0_value>
```
