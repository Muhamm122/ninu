---
name: residential-proxy
version: 1.0.0
category: infrastructure
description: Residential proxy management — provider setup, verification, geo-targeting, anti-ban patterns for Google/Cloudflare/Stripe bypass.
triggers:
  - proxy
  - residential proxy
  - bypass cloudflare
  - bypass google
  - anti-ban
  - rotasi proxy
  - proxy indonesia
  - proxy US
related_skills:
  - rotating-proxy-pool
  - browser-agent
---

# Residential Proxy Skill

## Overview

Residential proxies route traffic through real ISP IPs — appearing as normal home users. This bypasses bot detection on Google, Cloudflare, Stripe, and similar services that block datacenter IPs (AWS, GCP, etc.).

## Provider Comparison

### Free Options

| Provider | Type | Bandwidth | Geo | Limitation |
|----------|------|-----------|-----|------------|
| **ProxyScrape** | Residential | 10 free IPs | US/EU | Slow, low uptime |
| **Webshare** | Residential | 10 IPs free | US | 1GB/month, slow |
| **GeoNode** | Residential | Free list | Global | Unreliable, public |
| **FreeProxyList** | Mixed | Unlimited | Global | Mostly datacenter, unstable |

> ⚠️ Free residential proxies are **unreliable**. For production (Gmail signup, Stripe, etc.), use paid providers.

### Paid Providers (Best Value)

| Provider | Billing | Price | Min Buy | ID Geo | US Geo | Rotating | Protocol |
|----------|---------|-------|---------|--------|--------|----------|----------|
| **IPRoyal** | Bandwidth | $1.75/GB | $5 | ✅ | ✅ | Auto | HTTP/SOCKS5 |
| **Smartproxy** | Bandwidth | $2.2/GB | $8 | ✅ | ✅ | Auto | HTTP/SOCKS5 |
| **Webshare** | IP-based | $2.99/mo (10 IPs) | Free tier | ❌ | ✅ | Manual | HTTP/SOCKS5 |
| **Bright Data** | Bandwidth | $3.5/GB | $10 | ✅ | ✅ | Auto | HTTP/SOCKS5 |
| **Oxylabs** | Bandwidth | $6/GB | $15 | ✅ | ✅ | Auto | HTTP/SOCKS5 |
| **PacketStream** | Bandwidth | $1/GB | $5 | ✅ | ✅ | Auto | HTTP |
| **ProxyScrape** | Bandwidth | $2/GB | $5 | ✅ | ✅ | Auto | HTTP/SOCKS5 |

**Recommended for SUPERAGENT:**
1. **IPRoyal** — cheapest, good geo support, $5 minimum
2. **Smartproxy** — best dashboard, good ID/US geo
3. **PacketStream** — cheapest per GB at $1/GB

## Proxy Config Format

### Playwright / CloakBrowser

```python
# Static proxy (single IP)
browser = await launch_persistent_context_async(
    proxy={
        "server":   "http://gw.smartproxy.com:7000",
        "username": "user",
        "password": "pass",
    }
)

# Rotating via session ID (each request = new IP)
# Many providers support random session IDs in username
browser = await launch_persistent_context_async(
    proxy={
        "server":   "http://gw.smartproxy.com:7000",
        "username": "user-session-rand12345",
        "password": "pass",
    }
)

# Geo-targeted (Indonesia)
browser = await launch_persistent_context_async(
    proxy={
        "server":   "http://gw.iproyal.com:12321",
        "username": "user-country-id-session-rand67890",
        "password": "pass",
    }
)
```

### Provider Session ID Patterns

| Provider | Session ID Format | Geo Format | Example Username |
|----------|-------------------|------------|------------------|
| **IPRoyal** | `user-session-RAND` | `user-country-CODE-session-RAND` | `adib-country-id-session-abc123` |
| **Smartproxy** | `user-RAND` | Via dashboard | `adib-x8k2m9` |
| **Bright Data** | `user-session-RAND` | `user-country-CODE-session-RAND` | `brd-customer-adib-country-id-session-p1q2` |
| **PacketStream** | Rotating by default | Via API | `adib` (auto-rotate) |

## Anti-Ban Patterns

### Google OAuth (most strict)
```
1. Use residential proxy (Indonesia if ID account, US if .com account)
2. Randomize fingerprint per session
3. Add human-like delay (3-7s between actions)
4. Don't reuse same IP for multiple accounts
5. Avoid headless=True — Google detects it
```

### Cloudflare
```
1. Residential proxy helps, but CloakBrowser stealth is often enough
2. Use TLS fingerprint match (CloakBrowser handles this)
3. If still blocked → residential proxy + headless=False
```

### Instagram (direct access / third-party viewers)
```
1. IG blocks datacenter IPs at login — redirect to login wall or about:blank
2. Third-party IG viewers (imginn, pikdo) also behind Cloudflare → block bots
3. CloakBrowser stealth alone is NOT enough — IP reputation is the primary filter
4. Solution: residential proxy (any geo) for IG scraping/automation
5. Content creation (calendars, captions, style guides) does NOT need IG access
```

### X/Twitter Account Creation
```
1. X signup form loads from datacenter IP (no CF block on page load)
2. BUT: "Sign up with Phone" → enters phone → "Sorry, you are not allowed to log in at this time"
3. Email signup redirects to "Get the app to finish signing up" with QR code
4. X checks IP reputation DURING phone verification — hard block at that point
5. No CAPTCHA presented — just a flat refusal
6. Solution: residential proxy (Indonesia geo for +62 numbers)
7. Post-creation: X cookies (auth_token + ct0) can be extracted for API use without proxy
```

### Gmail Account Creation
```
1. Google signup form loads fine from datacenter IP
2. Name → Birthday → Gender → Username → Password — all steps reachable
3. BUT: After password, "Sorry, we could not create your Google Account" — hard block
4. No CAPTCHA — Google checks ASN/IP reputation and silently rejects datacenter IPs
5. Even YesCaptcha cannot fix (no CAPTCHA to solve)
6. Solution: residential proxy (Indonesia geo for Indonesian accounts)
7. Alternative: user creates account manually on phone (1 min), then gives App Password for IMAP/SMTP access
```

### Stripe
```
1. ⚠️ Stripe BLOCKS many proxy IPs — test first
2. Best: use direct IP or residential proxy with fresh IP
3. Never use datacenter proxies with Stripe
4. Some providers (IPRoyal, Smartproxy) work better than others
```

## Verification

Before using a proxy, always verify:

```bash
# Quick check (no proxy)
curl -s https://ipinfo.io/json

# Check with proxy
curl -s -x http://user:pass@gw.iproyal.com:12321 https://ipinfo.io/json

# Check if residential (vs datacenter)
# Look for: "org" field — ISP name = residential, cloud/DC name = datacenter
```

### Python Verification Script

Use `scripts/proxy_verify.py`:

```bash
python3 proxy_verify.py --proxy "http://user:pass@gw:port" --check-residential
```

Output:
```
IP:         103.xxx.xxx.xxx
Country:    Indonesia (ID)
City:       Jakarta
ISP:        PT Indosat Ooredoo
Type:       residential ✅
Anonymity:  elite
Latency:    245ms
```

## Setup Checklist

1. [ ] Buy proxy plan (IPRoyal/Smartproxy recommended, $5-8 min)
2. [ ] Get credentials (gateway URL, username, password)
3. [ ] Test with `proxy_verify.py`
4. [ ] Add to `~/.hermes/proxies.json` (encrypted)
5. [ ] Test with CloakBrowser
6. [ ] Test target site (Google/Stripe/etc)

## Credential Safety

**NEVER accept or store user passwords in conversation.** If user sends credentials (Google password, API key, etc.):
1. Acknowledge receipt
2. Use them ONLY for the immediate operation
3. Do NOT log, echo back, or write to files in plaintext
4. If the operation is blocked (wrong IP, expired key), tell the user ONCE and offer alternatives
5. Do NOT ask for the same credential again

If user sends Google credentials for automated signup from a server, refuse and explain: Google blocks datacenter IPs — the operation will fail. Suggest residential proxy or running from home IP instead.

## Pitfalls

- ❌ Free residential proxies = unreliable, often honeypots
- ❌ Reusing same proxy IP for multiple accounts on same service
- ❌ Using datacenter proxies for Google/Stripe
- ❌ Not verifying proxy type (many "residential" are actually datacenter)
- ❌ Not rotating session IDs — same IP gets flagged too
- ❌ Attempting Google OAuth from AWS/GCP/Azure IPs without residential proxy — Google silently redirects to about:blank or shows speedbump/challenge. This happens even with CloakBrowser stealth. The IP reputation is the blocker, not browser fingerprinting.
- ❌ **Datacenter proxy + Playwright browser** = too slow; default 20s timeout hits before page loads. Need 30s+ timeout AND `wait_until='commit'` (not `domcontentloaded`)
- ❌ **Cogent Communications (AS174), M247, Leaseweb IPs** = flagged datacenter. These work for basic HTTP but fail for X/Google SPA rendering
- ✅ Rotate session ID per account/session
- ✅ Geo-target to account's country (ID account → ID proxy)
- ✅ Test proxy before critical operations
- ✅ Keep backup proxy provider
- ✅ Verify proxy returns residential ISP in ipinfo.io "org" field (not Amazon/Google/Microsoft/Azure)
- ✅ For datacenter proxies: use `curl` for API calls, avoid Playwright browser (too slow)
