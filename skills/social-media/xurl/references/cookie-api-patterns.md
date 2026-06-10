# Cookie-Based X API Patterns

## Verified Working Patterns

### 1. Profile Verification (requests — instant)

```python
import requests, re

s = requests.Session()
s.cookies.set('auth_token', AUTH, domain='.x.com')
s.cookies.set('ct0', CT0, domain='.x.com')
s.cookies.set('twid', f'u%3D{USER_ID}', domain='.x.com')

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...'
r = s.get('https://x.com/home', headers={'User-Agent': UA}, timeout=10)
handle = re.search(r'"screen_name":"(\w+)"', r.text)
# Returns YOUR handle if cookies valid. URL stays /home (not /login).
```

### 2. Get Another User's ID (requests — heuristic)

```python
r = s.get('https://x.com/target_handle', headers={'User-Agent': UA}, timeout=10)
idx = r.text.find('target_handle')
if idx > 0:
    chunk = r.text[max(0,idx-5000):idx+5000]
    ids = re.findall(r'"id_str"\s*:\s*"(\d+)"', chunk)
    # Pick the one that isn't YOUR user ID
    target_id = [x for x in ids if x != YOUR_ID][0]
```

### 3. Playwright Follow (with cookie injection)

```python
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = await browser.new_context(user_agent=UA, viewport={'width':1280,'height':900})
    await context.add_cookies([
        {"name":"auth_token","value":AUTH,"domain":".x.com","path":"/",
         "secure":True,"httpOnly":True,"sameSite":"None","expires":1812333299},
        {"name":"ct0","value":CT0,"domain":".x.com","path":"/",
         "secure":True,"sameSite":"Lax","expires":1815357299},
        {"name":"twid","value":f"u%3D{USER_ID}","domain":".x.com","path":"/",
         "secure":True,"sameSite":"None","expires":1812333434},
    ])
    page = await context.new_page()
    await page.goto(f'https://x.com/{TARGET}', wait_until='commit', timeout=15000)
    await asyncio.sleep(7)  # X needs time to hydrate
    fb = page.locator('button:has-text("Follow")').first
    await fb.click()
```

### 4. GraphQL API Call (correct format)

```
POST https://x.com/i/api/graphql/{QID}/{OperationName}
Headers: Authorization: Bearer {BEARER}, X-Csrf-Token: {CT0}, Cookie: auth_token=...; ct0=...
Body: JSON {"variables": {...}, "features": {...}}
```

NOT `https://api.x.com/graphql/...` — that returns 401/404.

## Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Parse response |
| 404 | Query not found | QID is stale — need fresh QIDs |
| 405 | Method not allowed | QID may be stale OR wrong URL format |
| 422 | Validation failed | **QID is valid!** Fix payload schema |
| 403 | Auth/anti-automation | Cookie or bearer issue |

## Stale QIDs (as of 2026-06)

These are all 404 ("Query not found") — do NOT use:

- `S1Pm52XhLrWEx6rlWU3H2g` (CreateFollow)
- `H-t2v_HvFR07ZBP9aOeKoA` (CreateTweet) — returns 200 with empty `tweet_results: {}` on /i/api/ path
- `lI07N6Otwv1PhnEgXILM7A` (FavoriteTweet) — returns 422 (valid but schema wrong)
- `VOY_qOLfGr5YEpM6Vc-cqQ` (UserByScreenName)

Fresh QIDs must be extracted via browser network intercept, which itself requires a residential proxy from AWS/GCP datacenters.

## Bearer Token (still valid)

```
AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA
```

This is the public bearer used by X's web client. It works for guest/anonymous requests and as the Authorization header alongside cookie auth.

## Datacenter Limitations

From AWS/GCP IPs:
- ❌ Browser login: "We've temporarily limited your login"
- ❌ Playwright rendering: X React SPA does not hydrate — 0 tweet elements visible, Network.requestWillBeSent fires for static assets only, zero `/i/api/graphql/` calls
- ❌ GraphQL QID extraction: browser intercept returns 0 calls (page doesn't load)
- ❌ Account creation: IP reputation block
- ✅ Cookie-auth requests via `requests.Session`: profile data, verification
- ✅ Playwright with injected cookies: Follow button click works (but page is very slow to hydrate — use `wait_until='commit'` + `asyncio.sleep(7-10)`)

From residential IPs (proxy):
- ✅ All of the above works
- ✅ Fresh QIDs extractable via network intercept
- ✅ Full like/retweet/quote/reply automation

## Playwright Timing for X Pages

X's React SPA is extremely slow to hydrate in Playwright, even when it does render. Rules:

- **Never** use `wait_until='networkidle'` — it almost always times out on X (>30s)
- **Never** use `wait_until='load'` — fires too early, React hasn't started
- **Use** `wait_until='commit'` + `asyncio.sleep(7-10)` — gives React time to hydrate
- **For DOM interactions** (follow, like): After navigation, wait 7-10s, then scroll 2-3 times (500px each, 2s between) to trigger lazy loading
- **For data extraction**: Always prefer `requests.Session` (instant, ~1s) over Playwright (multi-second, often 0 results from datacenter)
