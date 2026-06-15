#!/usr/bin/env python3
"""
🔑 apikeys — Unified API Key Management CLI
Manage all LLM API keys: add, remove, test, rotate, switch, status.

Install:
  cp scripts/apikeys_cli.py ~/bin/apikeys
  chmod +x ~/bin/apikeys
  ln -sf ~/bin/apikeys /usr/local/bin/apikeys

Usage:
  apikeys [command] [args]

Commands:
  (no args)              List all keys
  list                   List all keys with status
  current                Show current active key
  status                 Pool summary
  stats                  Usage bars per key
  models [id]            Available models for key (or all)

  test <id>              Test single key (HTTP probe, ~2s)
  test-all               Test all keys, report working/failed counts

  rotate                 Rotate to next active key
  switch <id>            Jump to specific key (updates current_index)
  enable <id>            Mark key as active
  disable <id>           Mark key as inactive

  add                    Interactive add (prompts for provider/url/key/model)
  remove <id>            Remove key from pool

  help                   Show this help

The CLI is the operator-facing front-end to ~/.hermes/api-key-pool.json and
~/.hermes/config.yaml. For scripted/automation use, see api_key_rotator.py
(installed at ~/.hermes/scripts/api_key_rotator.py) which provides the
programmatic verb-based API.

See references/unified-cli.md in this skill for full design notes.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import time
import argparse
from datetime import datetime
from pathlib import Path

# Paths
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/ubuntu/.hermes"))
POOL_FILE = HERMES_HOME / "api-key-pool.json"
CONFIG_FILE = HERMES_HOME / "config.yaml"

# Color codes
class C:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

def cprint(msg, color=C.NC, end='\n', flush=False):
    if sys.stdout.isatty():
        print(f"{color}{msg}{C.NC}", end=end, flush=flush)
    else:
        print(msg, end=end, flush=flush)

def load_pool():
    if not POOL_FILE.exists():
        cprint(f"❌ Pool file not found: {POOL_FILE}", C.RED)
        sys.exit(1)
    with open(POOL_FILE) as f:
        return json.load(f)

def save_pool(pool):
    with open(POOL_FILE, 'w') as f:
        json.dump(pool, f, indent=2)

def get_pool(pool, name="primary"):
    if name not in pool.get("pools", {}):
        cprint(f"❌ Pool '{name}' not found. Available: {list(pool.get('pools', {}).keys())}", C.RED)
        sys.exit(1)
    return pool["pools"][name]

def get_key(pool, key_id):
    for k in pool["keys"]:
        if k["id"] == key_id:
            return k
    cprint(f"❌ Key '{key_id}' not found in pool.", C.RED)
    sys.exit(1)

def mask_key(key, show=4):
    if not key or len(key) < show * 2:
        return "***"
    return f"{key[:show]}...{key[-show:]}"

def test_key_http(key):
    """Test a single key by hitting /chat/completions with minimal prompt."""
    url = f"{key['base_url'].rstrip('/')}/chat/completions"
    model = key.get("active_model") or key.get("model", "unknown")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5
    }).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key['key']}",
            "Content-Type": "application/json",
        }
    )

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            latency = (time.time() - start) * 1000
            return {
                "ok": True,
                "status": resp.status,
                "latency_ms": round(latency),
                "response": data[:200].decode(errors='replace')
            }
    except urllib.error.HTTPError as e:
        latency = (time.time() - start) * 1000
        body = ""
        try:
            body = e.read()[:200].decode(errors='replace')
        except Exception:
            pass
        return {
            "ok": False,
            "status": e.code,
            "latency_ms": round(latency),
            "error": body or str(e.reason)
        }
    except Exception as e:
        latency = (time.time() - start) * 1000
        return {
            "ok": False,
            "status": 0,
            "latency_ms": round(latency),
            "error": str(e)[:200]
        }

def cmd_list(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]

    cprint(f"\n┌{'─'*68}┐", C.CYAN)
    cprint(f"│ {'API Key Pool':^66} │", C.BOLD + C.CYAN)
    cprint(f"├{'─'*68}┤", C.CYAN)
    cprint(f"│ {'idx':<5}{'id':<18}{'model':<22}{'status':<12}{'uses':<6} │", C.CYAN)
    cprint(f"├{'─'*68}┤", C.CYAN)

    for i, k in enumerate(keys):
        is_current = (i == p.get("current_index", -1))
        idx_str = f"{i}⭐" if is_current else str(i)
        status = k.get("status", "?")
        status_str = f"✅ {status}" if status == "active" else f"🔴 {status}"
        model = k.get("active_model") or k.get("model", "?")
        if len(model) > 20:
            model = model[:18] + ".."
        uses = k.get("usage_count", 0)
        cprint(f"│ {idx_str:<5}{k['id']:<18}{model:<22}{status_str:<12}{uses:<6} │")

    cprint(f"└{'─'*68}┘\n", C.CYAN)
    cprint(f"Total: {len(keys)} keys | Current: {keys[p['current_index']]['id'] if 0 <= p.get('current_index', -1) < len(keys) else 'none'}", C.YELLOW)

def cmd_current(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    idx = p.get("current_index", 0)
    if 0 <= idx < len(p["keys"]):
        k = p["keys"][idx]
        cprint(f"\n⭐ Current Active: {k['id']}", C.GREEN + C.BOLD)
        cprint(f"   Provider: {k.get('provider', '?')}")
        cprint(f"   Model:    {k.get('active_model') or k.get('model', '?')}")
        cprint(f"   URL:      {k.get('base_url', '?')}")
        cprint(f"   Key:      {mask_key(k.get('key', ''))}")
        cprint(f"   Used:     {k.get('usage_count', 0)} times")
        cprint(f"   Last:     {k.get('last_used', 'never')}\n")
    else:
        cprint("❌ No active key", C.RED)

def cmd_status(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]
    active = sum(1 for k in keys if k.get("status") == "active")
    inactive = len(keys) - active
    total_uses = sum(k.get("usage_count", 0) for k in keys)
    idx = p.get("current_index", 0)
    current_id = keys[idx]["id"] if 0 <= idx < len(keys) else "none"

    cprint(f"\n╔════════════════════════════════════════════════════════════════╗", C.CYAN)
    cprint(f"║  🔑 Pool Status                                                ║", C.BOLD + C.CYAN)
    cprint(f"╠════════════════════════════════════════════════════════════════╣", C.CYAN)
    cprint(f"║  Total keys:      {len(keys):<46}║")
    cprint(f"║  Active:          {active:<3}  |  Inactive:   {inactive:<30}║")
    cprint(f"║  Total uses:       {total_uses:<45}║")
    cprint(f"║  Current idx:     {idx}  →  {current_id:<40}║")
    cprint(f"╚════════════════════════════════════════════════════════════════╝\n", C.CYAN)

def cmd_test(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    k = get_key(p, args.key_id)
    cprint(f"  Testing {k['id']}... ", C.CYAN, end='', flush=True)
    r = test_key_http(k)
    if r["ok"]:
        cprint(f"✅ {r['status']} ({r['latency_ms']}ms)", C.GREEN)
    else:
        cprint(f"❌ HTTP {r['status']} ({r['latency_ms']}ms)", C.RED)
        if r.get("error"):
            cprint(f"     {r['error'][:120]}", C.RED)

def cmd_test_all(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]

    cprint(f"\n🧪 Testing {len(keys)} keys\n", C.BOLD)
    results = []
    for k in keys:
        cprint(f"  {C.CYAN}Testing {k['id']}... {C.NC}", end='', flush=True)
        result = test_key_http(k)
        results.append((k, result))
        if result["ok"]:
            cprint(f"✅ {result['status']} ({result['latency_ms']}ms)", C.GREEN)
        else:
            cprint(f"❌ HTTP {result['status']} ({result['latency_ms']}ms)", C.RED)

    working = sum(1 for _, r in results if r["ok"])
    failed = len(results) - working
    cprint(f"\n{'─' * 60}")
    cprint(f"  ✅ {working} working  |  ❌ {failed} failed  |  Total: {len(results)}", C.BOLD)
    print()

def cmd_rotate(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]
    cur = p.get("current_index", 0)
    # Find next active key
    n = len(keys)
    for i in range(1, n + 1):
        next_idx = (cur + i) % n
        if keys[next_idx].get("status") == "active":
            p["current_index"] = next_idx
            save_pool(pool)
            cprint(f"🔄 Rotated: {keys[cur]['id']} → {keys[next_idx]['id']}", C.GREEN)
            cprint(f"   Model: {keys[next_idx].get('active_model') or keys[next_idx].get('model')}", C.CYAN)
            # Hot-reload Hermes
            os.system("hermes config reload 2>/dev/null || true")
            return
    cprint("❌ No active key to rotate to", C.RED)

def cmd_switch(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]
    for i, k in enumerate(keys):
        if k["id"] == args.key_id:
            p["current_index"] = i
            save_pool(pool)
            cprint(f"✅ Switched to {args.key_id} (index {i})", C.GREEN)
            cmd_current(args)
            os.system("hermes config reload 2>/dev/null || true")
            return
    cprint(f"❌ Key '{args.key_id}' not found", C.RED)
    sys.exit(1)

def cmd_enable(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    k = get_key(p, args.key_id)
    k["status"] = "active"
    save_pool(pool)
    cprint(f"✅ Enabled: {args.key_id}", C.GREEN)

def cmd_disable(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    k = get_key(p, args.key_id)
    k["status"] = "inactive"
    save_pool(pool)
    cprint(f"🔴 Disabled: {args.key_id}", C.YELLOW)

def cmd_add(args):
    cprint("\n📝 Add new key (interactive)\n", C.BOLD)
    kid = input("Key ID: ").strip()
    if not kid:
        cprint("❌ Key ID required", C.RED)
        return
    provider = input("Provider (e.g. mimo, openrouter, custom): ").strip()
    base_url = input("Base URL: ").strip()
    key_val = input("API Key: ").strip()
    model = input("Model (e.g. mimo-v2.5-pro): ").strip()

    pool = load_pool()
    p = get_pool(pool, args.pool)
    p["keys"].append({
        "id": kid,
        "key": key_val,
        "base_url": base_url,
        "provider": provider,
        "active_model": model,
        "model": model,
        "status": "active",
        "usage_count": 0,
        "last_used": None,
        "last_used_ts": 0
    })
    save_pool(pool)
    cprint(f"✅ Added: {kid}", C.GREEN)

def cmd_remove(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]
    for i, k in enumerate(keys):
        if k["id"] == args.key_id:
            del keys[i]
            # Adjust current_index if needed
            if p.get("current_index", 0) >= len(keys):
                p["current_index"] = 0
            save_pool(pool)
            cprint(f"🗑️  Removed: {args.key_id}", C.YELLOW)
            return
    cprint(f"❌ Key '{args.key_id}' not found", C.RED)

def cmd_stats(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]
    max_uses = max((k.get("usage_count", 0) for k in keys), default=1) or 1

    cprint(f"\n📊 Usage Stats\n", C.BOLD)
    for k in keys:
        uses = k.get("usage_count", 0)
        bar_len = int((uses / max_uses) * 30) if max_uses > 0 else 0
        bar = "█" * bar_len
        cprint(f"  {k['id']:<18} {bar:<30} {uses}")

def cmd_models(args):
    pool = load_pool()
    p = get_pool(pool, args.pool)
    keys = p["keys"]

    if args.key_id:
        k = get_key(p, args.key_id)
        cprint(f"\n📦 Models for {k['id']}:", C.BOLD)
        for m in k.get("models", [k.get("active_model") or k.get("model")]):
            active = " ⭐" if m == (k.get("active_model") or k.get("model")) else ""
            cprint(f"  - {m}{active}")
    else:
        cprint(f"\n📦 All models:", C.BOLD)
        for k in keys:
            m = k.get("active_model") or k.get("model", "?")
            cprint(f"  {k['id']:<18} {m}")
    print()

def cmd_help(args):
    cprint(__doc__, C.CYAN)

def main():
    parser = argparse.ArgumentParser(description="apikeys — LLM API key management", add_help=False)
    parser.add_argument("command", nargs="?", default="list")
    parser.add_argument("key_id", nargs="?", default=None)
    parser.add_argument("--pool", default="primary", help="Pool name (default: primary)")

    args = parser.parse_args()
    cmd = args.command

    if cmd in ("help", "-h", "--help"):
        cmd_help(args)
        return
    elif cmd == "list":
        cmd_list(args)
    elif cmd == "current":
        cmd_current(args)
    elif cmd == "status":
        cmd_status(args)
    elif cmd == "test":
        if not args.key_id:
            cprint("Usage: apikeys test <id>", C.RED)
            return
        cmd_test(args)
    elif cmd == "test-all":
        cmd_test_all(args)
    elif cmd == "rotate":
        cmd_rotate(args)
    elif cmd == "switch":
        if not args.key_id:
            cprint("Usage: apikeys switch <id>", C.RED)
            return
        cmd_switch(args)
    elif cmd == "enable":
        if not args.key_id:
            cprint("Usage: apikeys enable <id>", C.RED)
            return
        cmd_enable(args)
    elif cmd == "disable":
        if not args.key_id:
            cprint("Usage: apikeys disable <id>", C.RED)
            return
        cmd_disable(args)
    elif cmd == "add":
        cmd_add(args)
    elif cmd == "remove":
        if not args.key_id:
            cprint("Usage: apikeys remove <id>", C.RED)
            return
        cmd_remove(args)
    elif cmd == "stats":
        cmd_stats(args)
    elif cmd == "models":
        cmd_models(args)
    else:
        cprint(f"❌ Unknown command: {cmd}", C.RED)
        cprint("Run `apikeys help` for usage", C.YELLOW)

if __name__ == "__main__":
    main()
