#!/usr/bin/env python3
"""
Rotating Proxy Pool Manager
Auto-rotate, health check, geo-routing, sticky sessions, failover.

Usage:
  # CLI mode
  python3 proxy_pool.py --config ~/.hermes/proxies.json --next --geo id
  python3 proxy_pool.py --config ~/.hermes/proxies.json --verify-all
  python3 proxy_pool.py --config ~/.hermes/proxies.json --stats

  # Server mode (HTTP API)
  python3 proxy_pool.py --config ~/.hermes/proxies.json --serve --port 9100
    GET /next?geo=id&sticky=true&account=email@gmail.com
    GET /health
    GET /stats
"""
import argparse
import asyncio
import hashlib
import json
import random
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    print("pip install httpx")
    exit(1)

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


# ─── Datacenter ISP keywords ───
DC_KEYWORDS = [
    "amazon", "aws", "google", "gcp", "microsoft", "azure",
    "digitalocean", "linode", "vultr", "hetzner", "ovh",
    "cloudflare", "alibaba", "oracle", "rackspace", "scaleway",
]


class ProxyPool:
    """Rotating proxy pool with health check, geo-routing, sticky sessions."""

    def __init__(self, config: dict):
        self.providers = config.get("providers", [])
        self.defaults = config.get("defaults", {})
        self.geo_map = config.get("geo_map", {})
        self._sessions = {}        # account → session_id
        _sticky_cache = {}         # session_id → proxy_url
        self._sticky_cache = _sticky_cache
        self._stats = defaultdict(lambda: {"requests": 0, "failures": 0, "last_used": 0})
        self._health = {}          # provider_name → last health result

    @classmethod
    def from_config(cls, path: str) -> "ProxyPool":
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Config not found: {p}")
        with open(p) as f:
            return cls(json.load(f))

    def _build_url(self, provider: dict, geo: Optional[str] = None,
                   session_id: Optional[str] = None) -> str:
        """Build proxy URL with optional geo and session."""
        server = provider["server"].replace("http://", "").replace("https://", "")
        user = provider["username"]
        pwd = provider["password"]

        # Inject geo-country code into username (provider-specific)
        if geo and provider.get("geo_support", True):
            user = f"{user}-country-{geo}"

        # Inject session ID
        if session_id:
            user = f"{user}-session-{session_id}"

        proto = provider.get("protocol", "http")
        return f"{proto}://{user}:{pwd}@{server}"

    def get(self, geo: Optional[str] = None, sticky: bool = False,
            account: Optional[str] = None, target: Optional[str] = None,
            provider_name: Optional[str] = None) -> dict:
        """Get next proxy from pool.

        Returns: {"proxy": {...}, "url": "http://...", "session_id": "..."}
        """
        # Resolve geo from target
        if not geo and target:
            for key, g in self.geo_map.items():
                if key in target.lower():
                    geo = g
                    break
        if not geo:
            geo = self.defaults.get("geo", "us")

        # Determine session
        session_id = None
        if sticky or account:
            if account and account in self._sessions:
                session_id = self._sessions[account]
            else:
                session_id = f"s-{uuid.uuid4().hex[:12]}"
                if account:
                    self._sessions[account] = session_id

        # Select provider
        provider = None
        if provider_name:
            provider = next((p for p in self.providers if p["name"] == provider_name), None)
        if not provider:
            # Try providers in order, prefer healthy ones
            healthy = [p for p in self.providers
                      if self._health.get(p["name"], {}).get("alive", True)]
            provider = healthy[0] if healthy else (self.providers[0] if self.providers else None)

        if not provider:
            raise RuntimeError("No proxy providers configured")

        url = self._build_url(provider, geo=geo, session_id=session_id)

        # Update stats
        self._stats[provider["name"]]["requests"] += 1
        self._stats[provider["name"]]["last_used"] = time.time()

        return {
            "provider": provider["name"],
            "url": url,
            "session_id": session_id,
            "geo": geo,
            "sticky": sticky or bool(account),
        }

    def release(self, account: str):
        """Release sticky session for account."""
        self._sessions.pop(account, None)

    async def verify_proxy(self, proxy_url: str) -> dict:
        """Check if proxy is alive and residential."""
        try:
            t0 = time.time()
            async with httpx.AsyncClient(proxy=proxy_url, timeout=15,
                                        follow_redirects=True) as client:
                r = await client.get("https://ipinfo.io/json")
                elapsed = int((time.time() - t0) * 1000)

                if r.status_code != 200:
                    return {"alive": False, "error": f"HTTP {r.status_code}"}

                data = r.json()
                isp = data.get("org", "").lower()
                is_dc = any(kw in isp for kw in DC_KEYWORDS)

                return {
                    "alive": True,
                    "ip": data.get("ip"),
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "isp": data.get("org"),
                    "residential": not is_dc,
                    "latency_ms": elapsed,
                }
        except Exception as e:
            return {"alive": False, "error": str(e)[:100]}

    async def verify_all(self) -> list:
        """Verify all providers."""
        results = []
        for p in self.providers:
            url = self._build_url(p, geo=self.defaults.get("geo", "us"),
                                  session_id=f"health-{uuid.uuid4().hex[:8]}")
            result = await self.verify_proxy(url)
            result["provider"] = p["name"]
            self._health[p["name"]] = result
            results.append(result)
            icon = "✅" if result.get("alive") and result.get("residential") else "❌"
            ip = result.get("ip", "?")
            isp = result.get("isp", "?")
            print(f"  {icon} {p['name']}: {ip} ({isp})")
        return results

    def stats(self) -> dict:
        """Get pool statistics."""
        return {
            "providers": len(self.providers),
            "active_sessions": len(self._sessions),
            "per_provider": dict(self._stats),
            "health": self._health,
        }


# ─── HTTP Server ───

async def serve(pool: ProxyPool, port: int):
    """Run as HTTP API server."""
    if not HAS_AIOHTTP:
        print("pip install aiohttp  (required for --serve mode)")
        return

    async def handle_next(request):
        geo = request.query.get("geo")
        sticky = request.query.get("sticky", "false").lower() == "true"
        account = request.query.get("account")
        target = request.query.get("target")
        provider = request.query.get("provider")

        try:
            result = pool.get(geo=geo, sticky=sticky, account=account,
                            target=target, provider_name=provider)
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_health(request):
        results = await pool.verify_all()
        return web.json_response(results)

    async def handle_stats(request):
        return web.json_response(pool.stats())

    app = web.Application()
    app.router.add_get("/next", handle_next)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/stats", handle_stats)

    print(f"Proxy Pool API on http://localhost:{port}")
    print(f"  GET /next?geo=id&sticky=true&account=email")
    print(f"  GET /health")
    print(f"  GET /stats")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass


# ─── CLI ───

async def main():
    parser = argparse.ArgumentParser(description="Rotating Proxy Pool Manager")
    parser.add_argument("--config", default="~/.hermes/proxies.json",
                       help="Proxy config file")
    parser.add_argument("--next", action="store_true", help="Get next proxy")
    parser.add_argument("--geo", default=None, help="Geo country code (id, us, sg)")
    parser.add_argument("--sticky", action="store_true", help="Sticky session")
    parser.add_argument("--account", help="Account email for sticky session")
    parser.add_argument("--target", help="Target service for geo-routing")
    parser.add_argument("--provider", help="Specific provider name")
    parser.add_argument("--verify-all", action="store_true", help="Verify all providers")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    parser.add_argument("--serve", action="store_true", help="Run as HTTP API server")
    parser.add_argument("--port", type=int, default=9100, help="Server port")
    args = parser.parse_args()

    try:
        pool = ProxyPool.from_config(args.config)
    except FileNotFoundError:
        print(f"❌ Config not found: {args.config}")
        print("Create ~/.hermes/proxies.json first — see rotating-proxy-pool skill")
        return

    if args.verify_all:
        print("Verifying all providers...\n")
        await pool.verify_all()

    elif args.next:
        result = pool.get(geo=args.geo, sticky=args.sticky,
                         account=args.account, target=args.target,
                         provider_name=args.provider)
        print(json.dumps(result, indent=2))

    elif args.stats:
        s = pool.stats()
        print(json.dumps(s, indent=2))

    elif args.serve:
        await serve(pool, args.port)

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
