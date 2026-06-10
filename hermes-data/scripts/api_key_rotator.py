#!/usr/bin/env python3
"""
API Key Rotator — auto-rotate API keys across providers.
Supports round_robin, least_used, random strategies.
Each entry can have different base_url + provider (for multi-provider pools).

Usage:
    python3 api_key_rotator.py init                              # Init pool from config.yaml + .env
    python3 api_key_rotator.py get <pool>                        # Get next active key (prints JSON)
    python3 api_key_rotator.py success <pool> <key_id>           # Report successful use
    python3 api_key_rotator.py fail <pool> <key_id> <error_type> # Report failure
    python3 api_key_rotator.py list                              # List all pools + keys
    python3 api_key_rotator.py add <pool> <key_id> <key> [base_url] [provider]
    python3 api_key_rotator.py remove <pool> <key_id>            # Remove a key
    python3 api_key_rotator.py reset <pool> <key_id>             # Reset key status to active
    python3 api_key_rotator.py strategy <pool> <strategy>        # Set rotation strategy
    python3 api_key_rotator.py setup-mimo-or                     # Quick setup: 2 MiMo + 1 OR in one pool
"""

import json
import sys
import os
import random
import time
import re
from datetime import datetime

POOL_FILE = os.path.expanduser("~/.hermes/api-key-pool.json")
CONFIG_FILE = os.path.expanduser("~/.hermes/config.yaml")
ENV_FILE = os.path.expanduser("~/.hermes/.env")

VALID_STRATEGIES = ("round_robin", "least_used", "random")
VALID_ERROR_TYPES = ("rate_limit", "exhausted", "invalid")
RATE_LIMIT_COOLDOWN = 60


def load_pool():
    if os.path.exists(POOL_FILE):
        with open(POOL_FILE, "r") as f:
            return json.load(f)
    return {"pools": {}}


def save_pool(pool):
    os.makedirs(os.path.dirname(POOL_FILE), exist_ok=True)
    with open(POOL_FILE, "w") as f:
        json.dump(pool, f, indent=2)
    os.chmod(POOL_FILE, 0o600)


def mask_key(key):
    if len(key) <= 12:
        return key[:4] + "***"
    return key[:8] + "..." + key[-4:]


def get_active_keys(pool_data):
    now = time.time()
    for entry in pool_data.get("keys", []):
        if entry["status"] == "rate_limited":
            last_used = entry.get("last_used_ts") or 0
            if now - last_used >= RATE_LIMIT_COOLDOWN:
                entry["status"] = "active"
        if entry["status"] == "active":
            yield entry


def pick_key(pool_data):
    strategy = pool_data.get("strategy", "round_robin")
    keys = list(get_active_keys(pool_data))
    if not keys:
        return None

    if strategy == "round_robin":
        current_idx = pool_data.get("current_index", 0)
        if current_idx >= len(keys):
            current_idx = 0
        selected = keys[current_idx]
        pool_data["current_index"] = (current_idx + 1) % len(keys)
        return selected
    elif strategy == "least_used":
        return min(keys, key=lambda k: k.get("usage_count", 0))
    elif strategy == "random":
        return random.choice(keys)
    else:
        return keys[0]


def parse_env_file():
    env = {}
    if not os.path.exists(ENV_FILE):
        return env
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def parse_config_yaml():
    providers = {}
    if not os.path.exists(CONFIG_FILE):
        return providers

    with open(CONFIG_FILE, "r") as f:
        content = f.read()

    in_providers = False
    current_provider = None

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "providers:":
            in_providers = True
            continue

        if in_providers:
            if not line.startswith(" ") and not line.startswith("\t") and ":" in stripped:
                if stripped != "providers:":
                    in_providers = False
                    continue

            match = re.match(r'^(\s{2})(\w+):', line)
            if match and not stripped.startswith(" " * 4):
                current_provider = match.group(2)
                providers[current_provider] = {}
                continue

            if current_provider:
                kv_match = re.match(r'^\s{4,}([\w_]+):\s*(.*)', line)
                if kv_match:
                    k = kv_match.group(1)
                    v = kv_match.group(2).strip().strip('"').strip("'")
                    providers[current_provider][k] = v

    return providers


def cmd_init(args):
    pool = load_pool()
    config_providers = parse_config_yaml()
    env_vars = parse_env_file()

    pools_created = 0

    # Standard providers
    for provider_name in ["mimo", "mimo2", "openrouter", "nvidia", "9router"]:
        keys = []

        if provider_name in config_providers:
            cfg = config_providers[provider_name]
            key_value = cfg.get("api_key", "")
            base_url = cfg.get("base_url", "")
            if key_value and "***" not in key_value:
                keys.append({
                    "id": f"{provider_name}-config",
                    "key": key_value,
                    "base_url": base_url,
                    "provider": provider_name,
                    "usage_count": 0,
                    "last_used": None,
                    "last_used_ts": 0,
                    "status": "active",
                    "source": "config.yaml"
                })

        env_map = {
            "mimo": "MIMO_API_KEY",
            "mimo2": "MIMO2_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
            "9router": "NINEROUTER_API_KEY",
        }

        if provider_name in env_map and env_map[provider_name] in env_vars:
            key_value = env_vars[env_map[provider_name]]
            base_url = config_providers.get(provider_name, {}).get("base_url", "")
            if not any(k["key"] == key_value for k in keys):
                keys.append({
                    "id": f"{provider_name}-env",
                    "key": key_value,
                    "base_url": base_url,
                    "provider": provider_name,
                    "usage_count": 0,
                    "last_used": None,
                    "last_used_ts": 0,
                    "status": "active",
                    "source": ".env"
                })

        if keys:
            strategy = pool["pools"].get(provider_name, {}).get("strategy", "round_robin")
            current_idx = pool["pools"].get(provider_name, {}).get("current_index", 0)
            pool["pools"][provider_name] = {
                "strategy": strategy,
                "current_index": current_idx,
                "keys": keys
            }
            pools_created += 1

    save_pool(pool)
    print(f"OK Initialized {pools_created} pools")
    cmd_list([])


def cmd_setup_mimo_or(args):
    """Quick setup: 2 MiMo + 1 OpenRouter in one pool called 'primary'."""
    pool = load_pool()
    config_providers = parse_config_yaml()
    env_vars = parse_env_file()

    keys = []

    # MiMo 1
    if "mimo" in config_providers:
        cfg = config_providers["mimo"]
        key_value = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "https://token-plan-sgp.xiaomimimo.com/v1")
        if key_value and "***" not in key_value:
            keys.append({
                "id": "mimo-1",
                "key": key_value,
                "base_url": base_url,
                "provider": "mimo",
                "model": "mimo-v2.5-pro",
                "usage_count": 0,
                "last_used": None,
                "last_used_ts": 0,
                "status": "active",
                "source": "config.yaml"
            })

    # MiMo 2
    if "mimo2" in config_providers:
        cfg = config_providers["mimo2"]
        key_value = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "https://token-plan-sgp.xiaomimimo.com/v1")
        if key_value and "***" not in key_value:
            keys.append({
                "id": "mimo-2",
                "key": key_value,
                "base_url": base_url,
                "provider": "mimo2",
                "model": "mimo-v2.5-pro",
                "usage_count": 0,
                "last_used": None,
                "last_used_ts": 0,
                "status": "active",
                "source": "config.yaml"
            })

    # OpenRouter
    or_key = env_vars.get("OPENROUTER_API_KEY", "")
    or_base = "https://openrouter.ai/api/v1"
    if "openrouter" in config_providers:
        or_base = config_providers["openrouter"].get("base_url", or_base)
        if not or_key or "***" in or_key:
            cfg_key = config_providers["openrouter"].get("api_key", "")
            if cfg_key and "***" not in cfg_key:
                or_key = cfg_key

    if or_key and "***" not in or_key:
        keys.append({
            "id": "openrouter-1",
            "key": or_key,
            "base_url": or_base,
            "provider": "openrouter",
            "model": "openrouter/owl-alpha",
            "usage_count": 0,
            "last_used": None,
            "last_used_ts": 0,
            "status": "active",
            "source": "auto"
        })

    pool["pools"]["primary"] = {
        "strategy": "round_robin",
        "current_index": 0,
        "keys": keys
    }

    save_pool(pool)
    print(f"OK Setup 'primary' pool with {len(keys)} keys (round_robin)")
    cmd_list([])


def cmd_get(args):
    if len(args) < 1:
        print("Usage: get <pool>", file=sys.stderr)
        sys.exit(1)

    pool_name = args[0]
    pool = load_pool()

    if pool_name not in pool.get("pools", {}):
        print(f"ERR Pool '{pool_name}' not found", file=sys.stderr)
        sys.exit(1)

    pool_data = pool["pools"][pool_name]
    selected = pick_key(pool_data)

    if selected is None:
        print(f"ERR No active keys in pool '{pool_name}'", file=sys.stderr)
        sys.exit(2)

    for i, k in enumerate(pool_data["keys"]):
        if k["id"] == selected["id"]:
            pool_data["keys"][i]["usage_count"] = k.get("usage_count", 0) + 1
            pool_data["keys"][i]["last_used"] = datetime.now().isoformat()
            pool_data["keys"][i]["last_used_ts"] = time.time()
            break

    save_pool(pool)

    # Output as JSON for easy parsing
    output = {
        "key": selected["key"],
        "base_url": selected.get("base_url", ""),
        "provider": selected.get("provider", ""),
        "model": selected.get("model", ""),
        "key_id": selected["id"]
    }
    print(json.dumps(output))


def cmd_success(args):
    if len(args) < 2:
        print("Usage: success <pool> <key_id>", file=sys.stderr)
        sys.exit(1)

    pool_name, key_id = args[0], args[1]
    pool = load_pool()

    if pool_name not in pool.get("pools", {}):
        print(f"ERR Pool '{pool_name}' not found", file=sys.stderr)
        sys.exit(1)

    for key in pool["pools"][pool_name]["keys"]:
        if key["id"] == key_id:
            key["usage_count"] = key.get("usage_count", 0) + 1
            key["last_used"] = datetime.now().isoformat()
            key["last_used_ts"] = time.time()
            if key["status"] != "active":
                key["status"] = "active"
            save_pool(pool)
            print(f"OK {pool_name}/{key_id} usage={key['usage_count']}")
            return

    print(f"ERR Key '{key_id}' not found in pool '{pool_name}'", file=sys.stderr)
    sys.exit(1)


def cmd_fail(args):
    if len(args) < 3:
        print("Usage: fail <pool> <key_id> <error_type>", file=sys.stderr)
        sys.exit(1)

    pool_name, key_id, error_type = args[0], args[1], args[2]

    if error_type not in VALID_ERROR_TYPES:
        print(f"ERR Invalid error type: {VALID_ERROR_TYPES}", file=sys.stderr)
        sys.exit(1)

    pool = load_pool()

    status_map = {
        "rate_limit": "rate_limited",
        "exhausted": "exhausted",
        "invalid": "invalid",
    }

    for key in pool["pools"][pool_name]["keys"]:
        if key["id"] == key_id:
            key["status"] = status_map[error_type]
            key["last_used"] = datetime.now().isoformat()
            key["last_used_ts"] = time.time()
            save_pool(pool)
            print(f"WARN {pool_name}/{key_id} marked={status_map[error_type]}")
            return

    print(f"ERR Key '{key_id}' not found in pool '{pool_name}'", file=sys.stderr)
    sys.exit(1)


def cmd_list(args):
    pool = load_pool()

    if not pool.get("pools"):
        print("EMPTY No pools. Run 'init' or 'setup-mimo-or' first.")
        return

    for pool_name, pool_data in pool["pools"].items():
        strategy = pool_data.get("strategy", "round_robin")
        print(f"\n[{pool_name}] strategy={strategy}")
        print(f"  {'ID':<20} {'Key':<25} {'Provider':<15} {'Status':<15} {'Usage':<8} {'Last Used'}")
        print(f"  {'-'*20} {'-'*25} {'-'*15} {'-'*15} {'-'*8} {'-'*20}")

        for key in pool_data["keys"]:
            masked = mask_key(key["key"])
            status = key["status"]
            usage = key.get("usage_count", 0)
            last = key.get("last_used", "never") or "never"
            if last != "never":
                last = last[:19]
            provider = key.get("provider", "-")

            icon = {"active": "OK", "rate_limited": "WAIT", "exhausted": "DEAD", "invalid": "BAD"}.get(status, "?")
            print(f"  {key['id']:<20} {masked:<25} {provider:<15} {icon} {status:<12} {usage:<8} {last}")


def cmd_add(args):
    if len(args) < 3:
        print("Usage: add <pool> <key_id> <key> [base_url] [provider]", file=sys.stderr)
        sys.exit(1)

    pool_name = args[0]
    key_id = args[1]
    key_value = args[2]
    base_url = args[3] if len(args) > 3 else ""
    provider = args[4] if len(args) > 4 else pool_name
    model = args[5] if len(args) > 5 else ""

    pool = load_pool()

    if pool_name not in pool.get("pools", {}):
        pool["pools"][pool_name] = {"strategy": "round_robin", "current_index": 0, "keys": []}

    if any(k["id"] == key_id for k in pool["pools"][pool_name]["keys"]):
        print(f"ERR Key ID '{key_id}' already exists in pool '{pool_name}'", file=sys.stderr)
        sys.exit(1)

    pool["pools"][pool_name]["keys"].append({
        "id": key_id,
        "key": key_value,
        "base_url": base_url,
        "provider": provider,
        "model": model,
        "usage_count": 0,
        "last_used": None,
        "last_used_ts": 0,
        "status": "active",
        "source": "manual"
    })

    save_pool(pool)
    print(f"OK Added {key_id} to pool '{pool_name}'")


def cmd_remove(args):
    if len(args) < 2:
        print("Usage: remove <pool> <key_id>", file=sys.stderr)
        sys.exit(1)

    pool_name, key_id = args[0], args[1]
    pool = load_pool()

    if pool_name not in pool.get("pools", {}):
        print(f"ERR Pool '{pool_name}' not found", file=sys.stderr)
        sys.exit(1)

    keys = pool["pools"][pool_name]["keys"]
    new_keys = [k for k in keys if k["id"] != key_id]

    if len(new_keys) == len(keys):
        print(f"ERR Key '{key_id}' not found in pool '{pool_name}'", file=sys.stderr)
        sys.exit(1)

    pool["pools"][pool_name]["keys"] = new_keys
    save_pool(pool)
    print(f"OK Removed {key_id} from pool '{pool_name}'")


def cmd_reset(args):
    if len(args) < 2:
        print("Usage: reset <pool> <key_id>", file=sys.stderr)
        sys.exit(1)

    pool_name, key_id = args[0], args[1]
    pool = load_pool()

    for key in pool["pools"][pool_name]["keys"]:
        if key["id"] == key_id:
            key["status"] = "active"
            save_pool(pool)
            print(f"OK Reset {pool_name}/{key_id} to active")
            return

    print(f"ERR Key '{key_id}' not found in pool '{pool_name}'", file=sys.stderr)
    sys.exit(1)


def cmd_strategy(args):
    if len(args) < 2:
        print("Usage: strategy <pool> <strategy>", file=sys.stderr)
        sys.exit(1)

    pool_name, strategy = args[0], args[1]

    if strategy not in VALID_STRATEGIES:
        print(f"ERR Invalid strategy: {VALID_STRATEGIES}", file=sys.stderr)
        sys.exit(1)

    pool = load_pool()

    if pool_name not in pool.get("pools", {}):
        print(f"ERR Pool '{pool_name}' not found", file=sys.stderr)
        sys.exit(1)

    pool["pools"][pool_name]["strategy"] = strategy
    save_pool(pool)
    print(f"OK Set '{pool_name}' strategy to {strategy}")


def main():
    if len(sys.argv) < 2:
        print("API Key Rotator v2 — multi-provider pools")
        print("Commands: init | setup-mimo-or | get | success | fail | list | add | remove | reset | strategy")
        sys.exit(0)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "init": cmd_init,
        "setup-mimo-or": cmd_setup_mimo_or,
        "get": cmd_get,
        "success": cmd_success,
        "fail": cmd_fail,
        "list": cmd_list,
        "add": cmd_add,
        "remove": cmd_remove,
        "reset": cmd_reset,
        "strategy": cmd_strategy,
    }

    if command not in commands:
        print(f"ERR Unknown command: {command}", file=sys.stderr)
        sys.exit(1)

    commands[command](args)


if __name__ == "__main__":
    main()
