# Chrome DevTools Protocol (CDP) for Social Media Auth

## Overview

CDP is the low-level WebSocket protocol that Chrome DevTools uses. Playwright exposes it via `context.new_cdp_session(page)`. CDP gives **direct browser-engine control** below the Playwright API — critical for social media login automation because:

1. **Network.setCookie** can inject **httpOnly** cookies (JS `document.cookie` cannot)
2. **Network.enable** + events intercept all requests (live GraphQL QID extraction)
3. **Page.addScriptToEvaluateOnNewDocument** injects JS **before** any page script (anti-detection)
4. **Fetch.enable** + `requestPaused` can **intercept, modify, or block** requests in-flight
5. **Emulation** domain fakes device metrics, locale, timezone at engine level

## Key CDP Domains for Social Media

### Network Domain
- `Network.enable` — start monitoring
- `Network.setCookie` — inject cookies including httpOnly (THE killer feature)
- `Network.getCookies` — read all cookies (including httpOnly)
- `Network.deleteCookies` — remove cookies
- `Network.clearBrowserCookies` — wipe all
- `Network.setUserAgentOverride` — override UA per-page
- `Network.setExtraHTTPHeaders` — inject custom headers on all requests
- **Events**: `Network.requestWillBeSent`, `Network.responseReceived`, `Network.loadingFinished`

### Fetch Domain (request interception — MORE powerful than Network monitoring)
- `Fetch.enable` + patterns — intercept matching requests
- `Fetch.continueRequest` — let request through (optionally modified)
- `Fetch.fulfillRequest` — serve a synthetic response (never hit network)
- `Fetch.failRequest` — block the request
- **Event**: `Fetch.requestPaused` — fired for each matching request

### Page Domain
- `Page.addScriptToEvaluateOnNewDocument` — inject JS before EVERY page load (persists across navigations)
- `Page.captureScreenshot` — screenshot at CDP level
- `Page.reload` — force reload

### Emulation Domain
- `Emulation.setDeviceMetricsOverride` — fake device (mobile, width, height, scale, posture)
- `Emulation.setTimezoneOverride` — fake timezone
- `Emulation.setLocaleOverride` — fake locale (conflicts if Playwright context already set one)
- `Emulation.setGeolocationOverride` — fake GPS

### Runtime Domain
- `Runtime.evaluate` — execute JS in page context (like `page.evaluate` but at CDP level)

## Usage Pattern (Playwright)

```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(viewport={'width': 1366, 'height': 768})
    page = await context.new_page()
    
    # ===== GET CDP SESSION =====
    cdp = await context.new_cdp_session(page)
    
    # ===== INJECT httpOnly COOKIES =====
    await cdp.send('Network.setCookie', {
        'name': 'auth_token',
        'value': 'xxx',
        'domain': '.x.com',
        'path': '/',
        'secure': True,
        'httpOnly': True,   # JS CANNOT read/write this!
        'sameSite': 'None',
        'expires': 1812333299,
    })
    
    # ===== ANTI-DETECTION JS (runs before any page script) =====
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
    })
    
    # ===== NETWORK INTERCEPTION =====
    await cdp.send('Network.enable')
    cdp.on('Network.requestWillBeSent', lambda e: print(e['request']['url']))
    
    # ===== FAKE DEVICE =====
    await cdp.send('Emulation.setDeviceMetricsOverride', {
        'mobile': True, 'width': 375, 'height': 812, 'deviceScaleFactor': 3,
        'screenWidth': 375, 'screenHeight': 812,
    })
    
    # ===== NAVIGATE =====
    await page.goto('https://x.com/home')
```

## Stealth JS (inject via Page.addScriptToEvaluateOnNewDocument)

```javascript
// 1. Kill navigator.webdriver (most common bot check)
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 2. Fake chrome runtime
if (!window.chrome) window.chrome = {};
if (!window.chrome.runtime) window.chrome.runtime = {};

// 3. Override permissions
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) => (
    params.name === 'notifications' ?
    Promise.resolve({state: Notification.permission}) :
    origQuery(params)
);

// 4. Fake plugins (non-empty = not headless)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer'}];
        arr.refresh = () => {};
        return arr;
    },
    configurable: true,
});

// 5. Set languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['id-ID', 'id', 'en-US', 'en'],
    configurable: true,
});

// 6. Hide headless indicators
Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel', configurable: true});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});

// 7. Override WebGL renderer
const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';
    if (param === 37446) return 'Intel Iris OpenGL Engine';
    return getParam.call(this, param);
};
```

## X/Twitter GraphQL QID Extraction via CDP

X/Twitter uses GraphQL with operation-specific queryIds that **expire with each frontend release**. To get fresh QIDs:

```python
graphql_calls = {}

def on_request(event):
    url = event.get('request', {}).get('url', '')
    if 'graphql' in url and '/i/api/' in url:
        import re
        m = re.search(r'/i/api/graphql/([^/]+)/([^/?]+)', url)
        if m:
            qid, op_name = m.group(1), m.group(2)
            for key in ['CreateTweet', 'CreateFollow', 'FavoriteTweet', 'CreateRetweet',
                       'UserTweets', 'HomeTimeline', 'SearchTimeline', 'UserByScreenName']:
                if key in op_name:
                    graphql_calls[key] = qid

cdp.on('Network.requestWillBeSent', on_request)
await cdp.send('Network.enable')
await page.goto('https://x.com/home')  # must render for GraphQL calls to fire
```

**Problem**: X SPA won't render from AWS/datacenter IPs — needs residential proxy.

## Tested Capabilities (2026-06-07)

| CDP Feature | Verified | Notes |
|-------------|----------|-------|
| Network.setCookie (httpOnly) | ✅ | Injected 4 X cookies including auth_token |
| Network.enable + requestWillBeSent | ✅ | Intercepted requests on non-blocking sites |
| Page.addScriptToEvaluateOnNewDocument | ✅ | Anti-detection JS runs before page |
| Emulation.setDeviceMetricsOverride | ✅ | Faked iPhone X, desktop, etc |
| Fetch.enable + requestPaused | ✅ | Intercepted and continued requests |
| X/Twitter login via CDP | ❌ | X SPA won't render from AWS IP |

## Known Limitations

- **Emulation.setLocaleOverride** errors if Playwright context already set locale — use only one
- **Fetch.continueRequest** with `headers` param requires array of [name, value] pairs, not dict — invalid params crash the session
- **SPA sites** (X, Instagram) may not render at all from datacenter IPs even with CDP stealth — the block is IP-level, not fingerprint-level
- **GraphQL QIDs** can only be extracted from live page rendering — impossible from server-side requests

## Residential Proxy Requirement

For social media login from a VPS:
1. CDP Network.setCookie → inject auth cookies
2. CDP Network.enable → intercept GraphQL QIDs
3. CDP Fetch.enable → modify requests in-flight
4. **BUT** SPA must render → needs residential IP

Recommended: IPRoyal ($1.75/GB, Indonesia available)
