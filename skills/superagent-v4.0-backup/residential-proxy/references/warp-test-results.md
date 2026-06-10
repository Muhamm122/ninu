# Cloudflare WARP — Real Test Results (2026-06-07)

## WARP on AWS Singapore VPS

| Test | Result |
|------|--------|
| **VPS origin IP** | `18.143.107.30` (Amazon AWS, SG) |
| **WARP exit IP** | `104.28.222.43` (Cloudflare, SG) |
| **WARP SOCKS5** | `socks5://127.0.0.1:40000` |
| **X.com via curl + WARP** | HTTP 200 ✅ |
| **Google via curl + WARP** | HTTP 302 ✅ |
| **x_tool.py via ALL_PROXY** | `whoami` = @muhamm122 ✅ |
| **Hermes browser + WARP** | ⏳ Requires gateway restart (config set but not active mid-session) |

## What WARP Does NOT Fix

Even via WARP (Cloudflare IP), these still fail:
- **X/Twitter login form "Continue" button** — click does nothing (likely IP-conditional JS)
- **X/Twitter SPA rendering** — page loads HTML but React never hydrates (0 GraphQL calls)
- **Google account creation** — "Sorry, we could not create your Google Account" after password step
- **httpOnly cookie injection** — can't set `auth_token`/`ct0` via JS; CDP needed but Hermes Playwright doesn't expose CDP port in managed browser sessions

## TOS Registration Pitfall

`warp-cli registration new` requires PTY to accept TOS. Even though the error says "pass --accept-tos flag", **that flag does NOT exist** on `registration new`. Use:

```bash
script -qc 'warp-cli registration new' /dev/null <<< 'y'
```

## Hermes Config

```bash
hermes config set browser.proxy socks5://127.0.0.1:40000
```

⚠️ This requires **gateway restart** + new session to take effect in `browser_*` tools.
For CLI tools, use env var instead (immediate effect):

```bash
ALL_PROXY=socks5://127.0.0.1:40000 python3 x_tool.py whoami
# or
curl --proxy socks5://127.0.0.1:40000 https://example.com
```

## Free Proxy List Results

Tested 30 free proxies from TheSpeedX/PROXY-List:
- Only 2/30 returned HTTP 200 from x.com
- Both were too slow for Playwright (>10s timeout)
- Free proxies are not viable for browser automation — use WARP or paid residential
