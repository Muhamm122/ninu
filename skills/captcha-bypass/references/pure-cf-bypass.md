# Pure Cloudflare Bypass (No GSuite / Account Login)

## When to Use
- Task only requires bypassing CF challenge page ("Just a moment...")
- No need to perform authenticated actions (login, dashboard access)
- GSuite accounts are unavailable or not desired

## Recommended Stack (Proven 2026-07)
- **Primary**: `cloudscraper` + residential proxy (instant-proxies US)
- **Fallback**: Playwright headless + stealth + same residential proxy
- Success rate in session: 10/10 accounts when residential proxy was active

## Key Configuration
- Proxy: `http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188`
- User-Agent: Chrome 124 Windows
- cloudscraper with browser emulation enabled

## Limitations
- Still vulnerable to very strong protections (Datadome, Akamai, PerimeterX)
- Residential proxy is mandatory for reliable results from VPS/datacenter IPs

## Related Scripts
- `scripts/cf_bypass_pure.py` — production pure bypass script