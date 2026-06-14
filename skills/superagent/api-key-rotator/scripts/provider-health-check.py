#!/usr/bin/env python3
"""
LLM Provider Health Check — probe all providers/keys/models in one shot.

Output a table: provider × key × model → status (200/401/402/403/429/...)
Read from ~/.hermes/config.yaml (providers section) and optionally
~/.hermes/credentials/kimchi-pool.json.

Distinguishes:
  - 200/OK             → healthy
  - 401 "User not found" → key invalid (remove from pool)
  - 402 "exhausted credits" → upstream provider dead (keep key, topup CastAI)
  - 403 "error 1010"   → IP block at Cloudflare (keep key, retry later)
  - 429                → rate limited (auto-recover 60s)
  - DNS failure        → URL typo, check base_url
  - Connection refused → local service down (9router, ollama)

Usage:
  python3 provider-health-check.py                    # probe all from config
  python3 provider-health-check.py --provider kimchi  # probe one provider
  python3 provider-health-check.py --models-only      # only list /models
  python3 provider-health-check.py --json             # JSON output

Exit code: 0 = all healthy, 1 = at least one provider degraded
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"
KIMCHI_POOL_PATH = Path.home() / ".hermes" / "credentials" / "kimchi-pool.json"


def load_yaml_simple(path):
    """Minimal YAML reader — handles the subset Hermes config uses.
    Falls back to a regex-based scan if PyYAML missing."""
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        # Use ruamel or fall back to grep
        import re
        text = Path(path).read_text()
        # Very crude: extract providers section as key-value
        providers = {}
        m = re.search(r"^providers:\s*\n((?:  \w[\w-]*:.*\n(?:    .*\n)*)+)", text, re.MULTILINE)
        if m:
            block = m.group(1)
            for pm in re.finditer(r"^  (\w[\w-]*):\s*\n((?:    .*\n)+)", block, re.MULTILINE):
                name = pm.group(1)
                body = pm.group(2)
                p = {}
                for line in body.splitlines():
                    mm = re.match(r"    (\w+):\s*(.+)", line)
                    if mm:
                        p[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
                providers[name] = p
        return {"providers": providers}


def probe(url, key, model, max_tokens=15, timeout=30):
    """Returns (status_code, info_dict)."""
    info = {"url": url, "model": model, "ms": 0}
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Reply OK"}],
        "max_tokens": max_tokens,
    }).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(
        f"{url.rstrip('/')}/chat/completions",
        data=body, headers=headers, method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            info["ms"] = int((time.time() - t0) * 1000)
            info["code"] = r.status
            info["reply"] = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:60]
            info["usage"] = data.get("usage", {}).get("total_tokens", "?")
            return r.status, info
    except urllib.error.HTTPError as e:
        info["ms"] = int((time.time() - t0) * 1000)
        info["code"] = e.code
        body = e.read().decode(errors="replace")[:200]
        info["body"] = body
        # Classify the error
        if e.code == 401:
            info["class"] = "invalid_key"
        elif e.code == 402:
            info["class"] = "exhausted_credits"
        elif e.code == 403 and "1010" in body:
            info["class"] = "ip_blocked"
        elif e.code == 403 and "User not found" in body:
            info["class"] = "invalid_key"
        elif e.code == 429:
            info["class"] = "rate_limited"
        else:
            info["class"] = f"http_{e.code}"
        return e.code, info
    except urllib.error.URLError as e:
        info["ms"] = int((time.time() - t0) * 1000)
        info["code"] = 0
        info["class"] = "url_error"
        info["body"] = str(e.reason)[:80]
        return 0, info
    except Exception as e:
        info["ms"] = int((time.time() - t0) * 1000)
        info["code"] = 0
        info["class"] = type(e).__name__
        info["body"] = str(e)[:80]
        return 0, info


def list_models(url, key, timeout=10):
    """List models via /models endpoint. Returns (status, list[str])."""
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    req = urllib.request.Request(f"{url.rstrip('/')}/models", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return r.status, [m["id"] for m in data.get("data", [])]
    except urllib.error.HTTPError as e:
        return e.code, []
    except Exception:
        return 0, []


def collect_providers(config, kimchi_pool=None):
    """Yield (provider_name, base_url, key, default_model) tuples from config."""
    providers = config.get("providers", {})
    for name, p in providers.items():
        if not isinstance(p, dict):
            continue
        url = p.get("base_url")
        key = p.get("api_key")
        model = p.get("default_model", "unknown")
        if url and key:
            yield name, url, key, model
    # Kimchi pool override
    if kimchi_pool:
        keys = kimchi_pool.get("keys", [])
        for k in keys:
            yield (
                f"kimchi-pool/{k.get('id', '?')}",
                kimchi_pool.get("base_url", "https://llm.kimchi.dev/openai/v1"),
                k.get("key"),
                kimchi_pool.get("model", "kimi-k2.6"),
            )


def format_row(name, info):
    """Format a single probe result as a one-line table row."""
    code = info.get("code", 0)
    cls = info.get("class", "ok" if code == 200 else "?")
    ms = info.get("ms", 0)
    model = info.get("model", "?")
    if code == 200:
        reply = info.get("reply", "")[:40]
        return f"  ✅ {code}  {name:<24} {model:<22}  {ms:>5}ms  {reply!r}"
    body = info.get("body", "")[:60].replace("\n", " ")
    return f"  ❌ {code}  {name:<24} {model:<22}  {ms:>5}ms  [{cls}]  {body}"


def main():
    ap = argparse.ArgumentParser(description="Probe LLM providers from Hermes config")
    ap.add_argument("--provider", help="only probe this provider name (e.g. kimchi-1)")
    ap.add_argument("--models-only", action="store_true", help="only list /models, no chat")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--config", default=str(CONFIG_PATH))
    args = ap.parse_args()

    if not Path(args.config).exists():
        print(f"❌ Config not found: {args.config}", file=sys.stderr)
        sys.exit(2)

    config = load_yaml_simple(args.config)
    kimchi_pool = None
    if KIMCHI_POOL_PATH.exists():
        try:
            kimchi_pool = json.loads(KIMCHI_POOL_PATH.read_text())
        except Exception:
            pass

    results = []
    degraded = 0
    for name, url, key, model in collect_providers(config, kimchi_pool):
        if args.provider and args.provider not in name:
            continue
        if args.models_only:
            code, models = list_models(url, key)
            if args.json:
                results.append({"provider": name, "url": url, "models": models, "code": code})
            else:
                print(f"  {code:>4}  {name:<24}  {len(models)} models: {', '.join(models[:6])}")
            if code != 200:
                degraded += 1
            continue
        code, info = probe(url, key, model)
        info["provider"] = name
        info["url"] = url
        results.append(info)
        if code != 200:
            degraded += 1
        if not args.json:
            print(format_row(name, info))

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    if not args.json and not results:
        print("(no providers probed — check config.yaml providers section)")

    sys.exit(1 if degraded else 0)


if __name__ == "__main__":
    main()
