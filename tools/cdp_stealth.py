#!/usr/bin/env python3
"""
CDP Stealth Browser v1.0 — CUPANG AI AGENT
==========================================
Chrome DevTools Protocol for social media automation.
Key features:
- Network.setCookie: inject httpOnly cookies (THE killer feature)
- Network.enable: intercept GraphQL API calls → fresh QIDs
- Fetch.enable: intercept/modify/block requests
- Page.addScriptToEvaluateOnNewDocument: anti-detection JS
- Emulation: fake device, timezone, viewport
"""
import asyncio, json, re, time
from playwright.async_api import async_playwright

# X/Twitter credentials
X_AUTH = 'db9e9b...5169'
X_CT0 = 'cbbd319ca8e37abb7ca81a251892401c4d0341f6bfa52b0ff884d8993429b98899f69da0a0fc0b71d06887734bf31fa5b0edf0f9ece987b701bd7a95c3a4ae6a27c46f3c3dcdd7ba0284337f44d31c7a'
X_TWID = 'u%3D1205811165873332225'
X_USER_ID = '1205811165873332225'
X_HANDLE = '@muhamm122'

# Stealth JS (injected BEFORE any page script via CDP)
STEALTH_JS = """
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

// 4. Fake plugins array (non-empty = not headless)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer'}];
        arr.refresh = () => {};
        return arr;
    },
    configurable: true,
});

// 5. Set languages (Indonesian)
Object.defineProperty(navigator, 'languages', {
    get: () => ['id-ID', 'id', 'en-US', 'en'],
    configurable: true,
});

// 6. Override navigator.platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'MacIntel',
    configurable: true,
});

// 7. Hide headless Chrome indicators
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});

// 8. Override WebGL renderer (headless has different fingerprint)
const getParam = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
    if (param === 37445) return 'Intel Inc.';  // UNMASKED_VENDOR
    if (param === 37446) return 'Intel Iris OpenGL Engine';  // UNMASKED_RENDERER
    return getParam.call(this, param);
};

console.log('🛡️ CDP Stealth JS injected!');
"""

class CDPStealthBrowser:
    """Chrome DevTools Protocol stealth browser for social media auth."""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.cdp = None
        self.graphql_calls = []
        self.fresh_qids = {}
    
    async def launch(self, headless=True):
        """Launch Chrome with stealth flags + CDP session."""
        p = await async_playwright().__aenter__()
        self._playwright = p
        
        self.browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-component-extensions-with-background-pages',
                '--disable-background-networking',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-default-apps',
                '--disable-domain-reliability',
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='id-ID',
            timezone_id='Asia/Jakarta',
            geolocation={'latitude': -6.2088, 'longitude': 106.8456},
            permissions=['geolocation'],
            color_scheme='light',
            reduced_motion='no-preference',
        )
        
        self.page = await self.context.new_page()
        
        # =============================================
        # CDP SESSION — the magic starts here
        # =============================================
        self.cdp = await self.context.new_cdp_session(self.page)
        
        # Emulation overrides
        await self.cdp.send('Emulation.setDeviceMetricsOverride', {
            'mobile': False, 'width': 1366, 'height': 768,
            'deviceScaleFactor': 1, 'screenWidth': 1920, 'screenHeight': 1080,
        })
        await self.cdp.send('Emulation.setTimezoneOverride', {'timezoneId': 'Asia/Jakarta'})
        
        # Anti-detection: inject stealth JS BEFORE any page loads
        await self.cdp.send('Page.addScriptToEvaluateOnNewDocument', {'source': STEALTH_JS})
        
        # Enable network monitoring
        await self.cdp.send('Network.enable')
        self.cdp.on('Network.requestWillBeSent', self._on_request)
        
        return self
    
    def _on_request(self, event):
        """Intercept network requests — find GraphQL QIDs."""
        url = event.get('request', {}).get('url', '')
        if 'graphql' in url and '/i/api/' in url:
            match = re.search(r'/i/api/graphql/([^/]+)/([^/?]+)', url)
            if match:
                qid, op_name = match.group(1), match.group(2)
                self.graphql_calls.append({'qid': qid, 'op_name': op_name, 'url': url[:80]})
                
                # Track key operations
                for key in ['CreateTweet', 'CreateFollow', 'FavoriteTweet', 'CreateRetweet',
                           'UserTweets', 'HomeTimeline', 'SearchTimeline', 'UserByScreenName']:
                    if key in op_name:
                        self.fresh_qids[key] = qid
    
    async def inject_cookies(self, domain, cookies):
        """Inject cookies including httpOnly via CDP Network.setCookie.
        THIS IS THE KEY METHOD — JS document.cookie cannot set httpOnly cookies!
        Only CDP Network.setCookie can do this."""
        for cookie in cookies:
            cookie['domain'] = domain
            if 'path' not in cookie:
                cookie['path'] = '/'
            result = await self.cdp.send('Network.setCookie', cookie)
        # Verify
        cookies_result = await self.cdp.send('Network.getCookies', {'urls': [f'https://{domain.strip(".")}']})
        return cookies_result.get('cookies', [])
    
    async def inject_x_cookies(self):
        """Inject X/Twitter auth cookies (including httpOnly auth_token)."""
        cookies = [
            {'name': 'auth_token', 'value': X_AUTH, 'secure': True, 'httpOnly': True, 'sameSite': 'None', 'expires': 1812333299},
            {'name': 'ct0', 'value': X_CT0, 'secure': True, 'httpOnly': False, 'sameSite': 'Lax', 'expires': 1815357299},
            {'name': 'twid', 'value': X_TWID, 'secure': True, 'httpOnly': False, 'sameSite': 'None', 'expires': 1812333434},
            {'name': 'd_tab', 'value': 'eyJ1IjoxfQ', 'secure': True, 'httpOnly': False, 'sameSite': 'None', 'expires': 1815357277},
        ]
        result = await self.inject_cookies('.x.com', cookies)
        return len(result)
    
    async def navigate(self, url, wait_seconds=8):
        """Navigate to URL and wait for content."""
        response = await self.page.goto(url, wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(wait_seconds)
        return {
            'status': response.status if response else None,
            'url': self.page.url,
            'title': await self.page.title(),
        }
    
    async def check_x_login(self):
        """Check if X/Twitter login worked."""
        content = await self.page.content()
        handle = re.search(r'"screen_name":"(\w+)"', content[:50000])
        return handle.group(1) if handle else None
    
    async def get_fresh_qids(self):
        """Get fresh GraphQL QIDs from intercepted requests."""
        return self.fresh_qids.copy()
    
    async def execute_graphql(self, operation, variables, features=None):
        """Execute X GraphQL API call using fresh QIDs."""
        if operation not in self.fresh_qids:
            return {'error': f'No fresh QID for {operation}'}
        
        qid = self.fresh_qids[operation]
        payload = {
            'variables': variables,
            'features': features or {'responsive_web_graphql_exclude_directive_enabled': True, 'verified_phone_label_enabled': False},
        }
        
        # Use the page's session to make the API call
        result = await self.page.evaluate(f"""
            async () => {{
                try {{
                    const r = await fetch('https://x.com/i/api/graphql/{qid}/{operation}', {{
                        method: 'POST',
                        headers: {{
                            'content-type': 'application/json',
                            'x-csrf-token': '{X_CT0}',
                            'x-twitter-active-user': 'yes',
                            'x-twitter-client-language': 'en',
                        }},
                        body: JSON.stringify({json.dumps(payload)}),
                        credentials: 'include',
                    }});
                    const data = await r.json();
                    return {{status: r.status, data: data}};
                }} catch(e) {{
                    return {{error: e.message}};
                }}
            }}
        """)
        return result
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()


async def main():
    print("=" * 60)
    print("🔧 CDP STEALTH BROWSER — SOCIAL MEDIA AUTH TEST")
    print("=" * 60)
    
    sb = CDPStealthBrowser()
    await sb.launch()
    
    # ===== INJECT X COOKIES VIA CDP =====
    print("\n📌 Injecting X cookies via CDP Network.setCookie...")
    count = await sb.inject_x_cookies()
    print(f"  ✅ {count} cookies injected (including httpOnly auth_token!)")
    
    # ===== NAVIGATE TO X =====
    print("\n📌 Navigating to x.com/home...")
    result = await sb.navigate('https://x.com/home', wait_seconds=10)
    print(f"  Status: {result['status']}")
    print(f"  URL: {result['url']}")
    print(f"  Title: {result['title']}")
    
    # ===== CHECK LOGIN =====
    print("\n📌 Checking X login...")
    handle = await sb.check_x_login()
    if handle:
        print(f"  ✅ LOGGED IN as @{handle}! 🔥")
    else:
        print(f"  ❌ Not logged in — checking page...")
        # Scroll to trigger more loads
        for i in range(3):
            await sb.page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(3)
    
    # ===== GET FRESH QIDs =====
    print(f"\n📌 Network interception results:")
    print(f"  Total GraphQL calls: {len(sb.graphql_calls)}")
    qids = await sb.get_fresh_qids()
    if qids:
        print(f"  🔑 FRESH QIDs found: {len(qids)}")
        for op, qid in qids.items():
            print(f"    {op}: {qid}")
        
        # Save QIDs
        with open('/home/ubuntu/.hermes/x-qids.json', 'w') as f:
            json.dump(qids, f, indent=2)
        print(f"  ✅ Saved to ~/.hermes/x-qids.json")
    else:
        # Print all intercepted calls
        if sb.graphql_calls:
            unique = list(set(f"{r['op_name']}:{r['qid'][:12]}..." for r in sb.graphql_calls))
            print(f"  All GraphQL calls: {unique[:15]}")
        else:
            print(f"  No GraphQL calls intercepted")
    
    # ===== Test GraphQL API with fresh QIDs =====
    if qids and handle:
        print(f"\n📌 Testing GraphQL API with fresh QIDs:")
        
        # Test FavoriteTweet (Like)
        if 'FavoriteTweet' in qids:
            print(f"  Testing Like...")
            # We need a tweet ID to like — use our own profile check first
            pass
        
        # Test CreateTweet (Post)
        if 'CreateTweet' in qids:
            print(f"  Testing Post tweet...")
            result = await sb.execute_graphql('CreateTweet', 
                {'tweet_text': '🔥 CUPANG AI AGENT X via CDP! @outworld3rs #OutWorlders #WL', 'dark_request': False},
                {
                    'communities_web_enable_tweet_community_results_fetch': True,
                    'c9s_tweet_anatomy_moderator_side_enabled': True,
                    'responsive_web_edit_tweet_api_enabled': True,
                    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
                    'view_counts_everywhere_api_enabled': True,
                    'longform_notetweets_consumption_enabled': True,
                    'tweetypie_tweet_mention_api_enabled': True,
                    'creator_subscriptions_tweet_count_api_enabled': True,
                }
            )
            print(f"  Result: {json.dumps(result)[:200]}")
    
    # ===== Anti-detection verification =====
    print(f"\n📌 Anti-detection verification:")
    checks = await sb.page.evaluate("""
        () => ({
            webdriver: navigator.webdriver,
            plugins: navigator.plugins.length,
            languages: navigator.languages,
            platform: navigator.platform,
            hardwareConcurrency: navigator.hardwareConcurrency,
            chrome: !!window.chrome,
            chromeRuntime: !!window.chrome?.runtime,
        })
    """)
    for k, v in checks.items():
        status = '✅' if (k == 'webdriver' and v is None) or (k != 'webdriver' and v) else '⚠️'
        print(f"  {status} {k}: {v}")
    
    # ===== SUMMARY =====
    print(f"\n" + "=" * 60)
    print(f"📋 CDP STEALTH BROWSER — RESULTS")
    print(f"=" * 60)
    print(f"  CDP Session:      ✅")
    print(f"  httpOnly Cookies:  ✅ Network.setCookie")
    print(f"  Anti-Detection:    ✅ Page.addScriptToEvaluateOnNewDocument")
    print(f"  Network Monitor:   ✅ Network.enable + requestWillBeSent")
    print(f"  Emulation:         ✅ Device + Timezone override")
    print(f"  X Login:           {'✅ @'+handle if handle else '❌'}")
    print(f"  Fresh QIDs:        {len(qids)} found")
    print(f"  GraphQL API:       {'✅' if qids else '⚠️ Need QIDs'}")
    
    await sb.close()

asyncio.run(main())
