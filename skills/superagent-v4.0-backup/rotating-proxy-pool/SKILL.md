---
name: rotating-proxy-pool
version: 1.0.0
category: infrastructure
description: Rotating proxy pool manager — auto-rotate, health check, geo-routing, sticky sessions, failover, and integration with CloakBrowser/Hermes.
triggers:
  - rotating proxy
  - proxy pool
  - proxy rotator
  - proxy manager
  - rotasi ip
  - ganti ip otomatis
  - pool proxy
related_skills:
  - residential-proxy
  - browser-agent
---

# Rotating Proxy Pool Skill

## Overview

A rotating proxy pool manages multiple proxies with automatic rotation, health checking, failover, and geo-routing. This is essential for:
- Multi-account operations (Gmail, social media, airdrop farming)
- Web scraping at scale
- dApp interactions across multiple wallets
- Any task where you need fresh IPs

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Agent /    │────▶│  Proxy Pool      │────▶│  Provider   │
│   Script    │     │  Manager         │     │  Gateway    │
└─────────────┘     │                  │     └─────────────┘
                    │  • Rotate policy │
                    │  • Health check  │
                    │  • Geo routing   │
                    │  • Failover      │
                    │  • Sticky sess   │
                    │  • Metrics       │
                    └──────────────────┘
```

## Rotation Modes

### 1. Per-Request (Auto-Rotate via Session ID)
Fastest — provider handles rotation. Each request gets a new IP.

```python
# IPRoyal: random session ID = new IP each time
def get_proxy_url():
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    return f"http://user-country-id-session-{session_id}:pass@gw.iproyal.com:12321"

# Bright Data: same pattern
def get_proxy_url():
    session_id = f"s-{random.randint(10000,99999)}"
    return f"http://brd-customer-user-country-id-session-{session_id}:pass@zproxy.lum-superproxy.io:22225"
```

### 2. Per-Session (Sticky Session)
Same IP for entire browser session (e.g., Google OAuth flow).

```python
# Create one session ID, reuse for entire login flow
SESSION_ID = f"sticky-{uuid.uuid4().hex[:8]}"

async def launch_with_sticky_proxy(geo="id"):
    proxy = {
        "server":   "http://gw.iproyal.com:12321",
        "username": f"user-country-{geo}-session-{SESSION_ID}",
        "password": "pass",
    }
    return await launch_persistent_context_async(proxy=proxy, ...)
```

### 3. Per-Account (Account-IP Binding)
Each account gets a dedicated sticky IP (prevents cross-account detection).

```python
# Map: account → session ID → proxy IP
ACCOUNT_PROXIES = {}

def get_account_proxy(email: str, geo: str = "id") -> dict:
    if email not in ACCOUNT_PROXIES:
        session_id = f"acct-{hashlib.md5(email.encode()).hexdigest()[:12]}"
        ACCOUNT_PROXIES[email] = {
            "server":   "http://gw.iproyal.com:12321",
            "username": f"user-country-{geo}-session-{session_id}",
            "password": "pass",
        }
    return ACCOUNT_PROXIES[email]
```

### 4. Timed Rotation
Rotate IP every N minutes for long-running tasks.

```python
class TimedRotator:
    def __init__(self, provider, geo="id", rotate_every=300):
        self.provider = provider
        self.geo = geo
        self.rotate_every = rotate_every
        self.last_rotate = 0
        self.session_id = None

    def get_proxy(self):
        now = time.time()
        if now - self.last_rotate > self.rotate_every:
            self.session_id = f"tmr-{uuid.uuid4().hex[:8]}"
            self.last_rotate = now
        return {
            "server":   self.provider["server"],
            "username": f"{self.provider['user']}-country-{self.geo}-session-{self.session_id}",
            "password": self.provider["pass"],
        }
```

## Health Checking

Periodically verify proxies are alive and residential:

```python
HEALTH_CHECK_URLS = [
    "https://ipinfo.io/json",        # IP + geo info
    "https://api.ipify.org?format=json",  # Just IP
]

async def check_proxy(proxy_url: str) -> dict:
    """Check if proxy works and is residential."""
    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=10) as client:
            r = await client.get("https://ipinfo.io/json")
            data = r.json()

            # Classify: residential vs datacenter
            isp = data.get("org", "").lower()
            dc_keywords = ["amazon", "google", "microsoft", "azure", "aws",
                          "digitalocean", "linode", "vultr", "hetzner", "ovh",
                          "cloudflare", "alibaba", "oracle"]
            is_residential = not any(kw in isp for kw in dc_keywords)

            return {
                "alive": True,
                "ip": data.get("ip"),
                "country": data.get("country"),
                "city": data.get("city"),
                "isp": data.get("org"),
                "residential": is_residential,
                "latency_ms": int(r.elapsed.total_seconds() * 1000),
            }
    except Exception as e:
        return {"alive": False, "error": str(e)}
```

## Multi-Provider Failover

```python
PROVIDERS = [
    {"name": "iproyal",    "server": "http://gw.iproyal.com:12321",    "user": "u1", "pass": "p1"},
    {"name": "smartproxy", "server": "http://gw.smartproxy.com:7000",  "user": "u2", "pass": "p2"},
    {"name": "brightdata", "server": "http://zproxy.lum-superproxy.io:22225", "user": "u3", "pass": "p3"},
]

async def get_working_proxy(geo="id", max_attempts=3):
    """Try providers in order until one works."""
    for provider in PROVIDERS:
        for attempt in range(max_attempts):
            session = f"fail-{uuid.uuid4().hex[:8]}"
            proxy_url = f"http://{provider['user']}-country-{geo}-session-{session}:{provider['pass']}@{provider['server'].split('//')[1]}"

            result = await check_proxy(proxy_url)
            if result["alive"] and result.get("residential"):
                log(f"✅ {provider['name']} working: {result['ip']} ({result['isp']})")
                return proxy_url

            log(f"❌ {provider['name']} attempt {attempt+1} failed")

    raise RuntimeError("No working proxy found — all providers down")
```

## Geo-Routing

Route requests through specific countries:

```python
GEO_MAP = {
    # Google account region → proxy country
    "gmail.com":    "id",   # Indonesia
    "google.co.id": "id",
    "google.com":   "us",   # United States

    # dApp chains → proxy region
    "ethereum":     "us",
    "solana":       "us",
    "bsc":          "sg",   # Singapore (close to Binance)
}

def get_geo_for_target(target: str) -> str:
    for key, geo in GEO_MAP.items():
        if key in target.lower():
            return geo
    return "us"  # default
```

## Proxy Pool Manager Script

Use `scripts/proxy_pool.py` for a full-featured pool:

```bash
# Start pool manager (foreground)
python3 proxy_pool.py --config ~/.hermes/proxies.json

# Get next proxy (curl interface)
curl http://localhost:9100/next?geo=id

# Get proxy for account
curl http://localhost:9100/next?geo=id&account=example@gmail.com

# Health check all
curl http://localhost:9100/health

# Stats
curl http://localhost:9100/stats
```

## Integration with Hermes

### Config: `~/.hermes/proxies.json`

```json
{
  "providers": [
    {
      "name": "iproyal",
      "server": "http://gw.iproyal.com:12321",
      "username": "your-user",
      "password": "your-pass",
      "geo_support": true,
      "protocol": "http"
    }
  ],
  "defaults": {
    "geo": "id",
    "rotation": "per-session",
    "failover": true
  },
  "geo_map": {
    "google": "id",
    "stripe": "us",
    "dapp": "us"
  }
}
```

### CloakBrowser Integration

```python
from proxy_pool import ProxyPool

pool = ProxyPool.from_config("~/.hermes/proxies.json")

# For Google OAuth (sticky session, Indonesia IP)
proxy = pool.get(geo="id", sticky=True, target="google")
browser = await launch_persistent_context_async(proxy=proxy, ...)

# For scraping (rotate per request, any geo)
proxy = pool.get(geo="us", sticky=False)
```

## Scripts

- `scripts/proxy_pool.py` — Full-featured pool manager: CLI + HTTP API server. Usage: `python3 proxy_pool.py --config ~/.hermes/proxies.json --next --geo id` or `--serve --port 9100` for API mode. Dependencies: `httpx`, `aiohttp` (for serve mode).

## Pitfalls

- ❌ Using same session ID across different accounts/services
- ❌ Not health-checking before critical operations
- ❌ Forgetting to set geo-targeting (wrong country = account lock)
- ❌ Using datacenter proxies as "backup" for residential tasks
- ❌ Not monitoring bandwidth usage (costs add up fast)
- ✅ Test proxy immediately after getting it
- ✅ Use sticky sessions for multi-step flows (OAuth, checkout)
- ✅ Use per-request rotation for scraping
- ✅ Map accounts to dedicated proxy IPs
- ✅ Monitor bandwidth and set alerts
- ✅ Keep 2+ providers for failover

## Confirmed Server IP Behavior (2026-06-04)

Current server IP: `18.143.107.30` (AWS Singapore, datacenter). Verified via `proxy_verify.py`:
- Type: datacenter ⚠️
- ISP: Amazon.com, Inc.
- This IP will be blocked by Google, Cloudflare (sometimes), and flagged by Stripe
- Residential proxy is REQUIRED for Google OAuth/signup from this server
- Stripe must use DIRECT IP (no proxy) — Stripe blocks proxy IPs
