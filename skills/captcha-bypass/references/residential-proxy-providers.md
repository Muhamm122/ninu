# Residential Proxy Providers — Verified IPs and Patterns

> Verified 2026-06-25. Residential proxies that have been tested from VPS 18.143.107.30.

## Active Providers

### InstantProxies (p101) — T-Mobile USA Residential
```
http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188
```
- **IP**: `172.56.107.202` (T-Mobile USA, AS21928, Seattle WA)
- **Type**: HTTP residential (ISP, not datacenter)
- **Session**: sticky (same IP for duration)
- **Works for**: CF challenge bypass, page rendering
- **Fails for**: Discord hCaptcha (fingerprint-bound), Spotify reCAPTCHA
- **Notes**: AS21928 is classified as residential by most databases, but Discord still detects it as automation IP

### 9proxy (niceproxy.io) — Belgium/US Residential
```
http://muham_8J76-ssid-4rwYgFkhUL:muham@niceproxy.io:17522
```
- **IP**: `84.197.178.103` (Telenet Belgium, AS6848) — burned/401
- **IP**: `69.202.172.165` — 403
- **Type**: HTTP residential
- **Session**: 1440 min sticky
- **Status**: Password may be incorrect (401). Verify at 9proxy dashboard.

## Provider Selection Guide

| Provider | ASN | Type | Status | Notes |
|---|---|---|---|---|
| InstantProxies p101 | AS21928 (T-Mobile) | Residential | ✅ Working | Best for CF bypass |
| 9proxy niceproxy.io | AS6848 (Telenet) | Residential | ⚠️ Check creds | May need password rotation |

## Testing Pattern
```bash
curl -s --max-time 15 -x "http://user:pass@proxy:port" "https://api.ipify.org?format=json"
# Then verify IP type:
curl -s --max-time 10 "https://ipinfo.io/<IP>/json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('org','N/A'))"
```

## Key Insight
Residential proxy is **necessary but not sufficient** for Discord. The IP must be truly residential (not known to Discord's bot database), and even then, the hCaptcha fingerprint-bound check blocks cloud solvers.