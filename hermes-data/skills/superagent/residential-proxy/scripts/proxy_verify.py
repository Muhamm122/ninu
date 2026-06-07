#!/usr/bin/env python3
"""
Residential Proxy Verifier
Check if a proxy works, is residential, and get geo info.

Usage:
  python3 proxy_verify.py --proxy "http://user:pass@host:port"
  python3 proxy_verify.py --proxy "socks5://user:pass@host:port"
  python3 proxy_verify.py --config ~/.hermes/proxies.json --provider iproyal
  python3 proxy_verify.py --check-residential --min-latency 500
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("pip install httpx")
    sys.exit(1)


# Datacenter ISP keywords
DC_KEYWORDS = [
    "amazon", "aws", "google", "gcp", "microsoft", "azure",
    "digitalocean", "linode", "akamai", "vultr", "hetzner", "ovh",
    "cloudflare", "alibaba", "oracle", "rackspace", "scaleway",
    "upcloud", "choopa", "leaseweb", "serverbeach", "quadranet",
    "cogent", "zenlayer", "hostwinds", "contabo", "hetzner",
]


async def verify_proxy(proxy_url: str, check_residential: bool = True) -> dict:
    """Verify a proxy and return status dict."""
    result = {
        "proxy": proxy_url.split("@")[1] if "@" in proxy_url else proxy_url,
        "alive": False,
        "ip": None,
        "country": None,
        "country_name": None,
        "city": None,
        "isp": None,
        "residential": None,
        "anonymity": None,
        "latency_ms": None,
        "error": None,
    }

    try:
        t0 = time.time()
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=15,
            follow_redirects=True,
        ) as client:
            r = await client.get("https://ipinfo.io/json")
            elapsed = int((time.time() - t0) * 1000)

            if r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                return result

            data = r.json()
            result["alive"] = True
            result["ip"] = data.get("ip")
            result["country"] = data.get("country")
            result["city"] = data.get("city")
            result["isp"] = data.get("org")
            result["latency_ms"] = elapsed

            # Country name mapping
            country_names = {
                "ID": "Indonesia", "US": "United States", "SG": "Singapore",
                "MY": "Malaysia", "GB": "United Kingdom", "DE": "Germany",
                "JP": "Japan", "KR": "South Korea", "IN": "India",
                "PH": "Philippines", "TH": "Thailand", "VN": "Vietnam",
                "NL": "Netherlands", "FR": "France", "CA": "Canada",
                "AU": "Australia", "BR": "Brazil",
            }
            result["country_name"] = country_names.get(result["country"], result["country"])

            # Check if residential
            if check_residential and result["isp"]:
                isp_lower = result["isp"].lower()
                is_dc = any(kw in isp_lower for kw in DC_KEYWORDS)
                result["residential"] = not is_dc

    except httpx.ConnectError as e:
        result["error"] = f"Connection failed: {str(e)[:100]}"
    except httpx.TimeoutException:
        result["error"] = "Timeout (15s)"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:100]}"

    return result


def print_result(result: dict, verbose: bool = True):
    """Pretty print verification result."""
    if not result["alive"]:
        print(f"  ❌ DEAD — {result.get('error', 'unknown')}")
        return

    res_icon = "✅" if result.get("residential") else "⚠️ DC"
    print(f"  {res_icon} {result['ip']}")
    print(f"     Country:  {result['country']} ({result.get('country_name', '?')})")
    if result.get("city"):
        print(f"     City:     {result['city']}")
    if result.get("isp"):
        print(f"     ISP:      {result['isp']}")
    if result.get("residential") is not None:
        ptype = "residential ✅" if result["residential"] else "datacenter ⚠️"
        print(f"     Type:     {ptype}")
    if result.get("latency_ms") is not None:
        print(f"     Latency:  {result['latency_ms']}ms")


async def main():
    parser = argparse.ArgumentParser(description="Residential Proxy Verifier")
    parser.add_argument("--proxy", help="Proxy URL: http://user:pass@host:port")
    parser.add_argument("--config", help="Proxy config JSON file")
    parser.add_argument("--provider", help="Provider name from config")
    parser.add_argument("--check-residential", action="store_true", default=True,
                       help="Check if proxy is residential (default: True)")
    parser.add_argument("--no-check-residential", action="store_true",
                       help="Skip residential check")
    parser.add_argument("--min-latency", type=int, help="Max acceptable latency (ms)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    check_res = args.check_residential and not args.no_check_residential

    # Direct proxy URL
    if args.proxy:
        print(f"Checking proxy: {args.proxy.split('@')[1] if '@' in args.proxy else args.proxy}")
        result = await verify_proxy(args.proxy, check_res)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_result(result)

        if args.min_latency and result.get("latency_ms") and result["latency_ms"] > args.min_latency:
            print(f"  ⚠️ Latency {result['latency_ms']}ms > {args.min_latency}ms threshold")

        sys.exit(0 if result["alive"] else 1)

    # From config file
    if args.config:
        config_path = Path(args.config).expanduser()
        if not config_path.exists():
            print(f"❌ Config not found: {config_path}")
            sys.exit(1)

        with open(config_path) as f:
            config = json.load(f)

        providers = config.get("providers", [])
        if args.provider:
            providers = [p for p in providers if p["name"] == args.provider]
            if not providers:
                print(f"❌ Provider '{args.provider}' not found in config")
                sys.exit(1)

        print(f"Checking {len(providers)} provider(s)...\n")
        results = []
        for p in providers:
            server = p["server"]
            # Remove protocol prefix for URL construction
            server_clean = server.replace("http://", "").replace("https://", "").replace("socks5://", "")
            proxy_url = f"http://{p['username']}:{p['password']}@{server_clean}"

            print(f"[{p['name']}]")
            result = await verify_proxy(proxy_url, check_res)
            result["provider"] = p["name"]
            print_result(result)
            print()
            results.append(result)

        if args.json:
            print(json.dumps(results, indent=2))

        alive = sum(1 for r in results if r["alive"])
        print(f"Summary: {alive}/{len(results)} alive")
        sys.exit(0 if alive > 0 else 1)

    # No proxy specified — check direct IP
    print("No proxy specified — checking direct IP...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://ipinfo.io/json")
            data = r.json()
            isp = data.get("org", "").lower()
            is_dc = any(kw in isp for kw in DC_KEYWORDS)
            ptype = "datacenter ⚠️" if is_dc else "residential ✅"
            print(f"  IP:       {data.get('ip')}")
            print(f"  Country:  {data.get('country')} — {data.get('city', '?')}")
            print(f"  ISP:      {data.get('org')}")
            print(f"  Type:     {ptype}")
    except Exception as e:
        print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
