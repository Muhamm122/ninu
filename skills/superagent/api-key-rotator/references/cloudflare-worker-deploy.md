# Cloudflare Worker Deploy — Session Notes 2026-06-10

## Context
User wanted to deploy a Cloudflare Worker as a proxy for MEXC futures API (to avoid IP-based rate limits from VPS).

## What We Learned

### Cloudflare API Token Permissions (CRITICAL)
- API tokens from dashboard have limited permissions by default
- Token with only `User:Read` can verify but CANNOT list accounts/zones or edit workers
- To edit workers via API, token needs: `Account Resources → Cloudflare Pages and Workers → Edit`
- Token format: `cfut_...` (API token, not Global API Key)
- `Authorization: Bearer` with valid token returns "Invalid request headers" (code 6111) on accounts/zones endpoints when token lacks permission — NOT an auth format issue

### Cloudflare Dashboard Bot Detection
- `dash.cloudflare.com` blocks headless browser from VPS (returns "Just a moment..." challenge)
- Cannot automate worker editing via browser from VPS

### MEXC Futures API
- Base URL: `https://futures.mexc.com` (NOT `https://api.mexc.com`)
- Worker proxy must forward to `futures.mexc.com`

### Worker Code (MEXC-specific)
```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    let path = url.pathname;
    if (!path.startsWith('/')) path = '/' + path;
    const targetUrl = 'https://futures.mexc.com' + path + url.search;
    const headers = new Headers();
    for (const [key, value] of request.headers) {
      if (!['host', 'cf-connecting-ip'].includes(key.toLowerCase())) {
        headers.set(key, value);
      }
    }
    return fetch(targetUrl, {
      method: request.method,
      headers: headers,
      body: request.method !== 'GET' ? request.body : undefined,
    });
  }
};
```

### Wrangler CLI
- Needs `CLOUDFLARE_API_TOKEN` env var + `account_id` in wrangler.toml
- Cannot use without proper API token permissions

## Pitfalls
1. **Token permission**: Verify `Workers Scripts:Edit` before API deploy attempts
2. **Dashboard bot detection**: Don't try browser automation on dash.cloudflare.com from VPS
3. **MEXC base URL**: Worker must proxy to `futures.mexc.com`, not `api.mexc.com`
4. **Path forwarding**: Preserve query string (`url.search`) in proxy
5. **Non-technical user**: Provide step-by-step instructions for dashboard operations

## User-Specific
- Cloudflare account: `muhammadadib1217`, email: `adibmuhadi@gmail.com`
- Worker: `wild-butterfly-9d83` at `https://wild-butterfly-9d83.muhammadadib1217.workers.dev` — still contains README
- Tokens `cfut_Ey4B...` and `cfut_cx8w...` — verified active but only User:Read
