#!/usr/bin/env python3
"""
monitor_and_rotate.py — monitor Hermes error logs + auto-rotate on API errors
Run via cron every 1 minute: * * * * * python3 ~/.hermes/scripts/monitor_and_rotate.py

Detects: 429 (rate limit), 401/403 (auth), 402 (quota), timeout
Auto-rotates to next key in pool + hot-reloads Hermes config.
Cooldown: won't rotate more than once per 30s to prevent flip-flopping.
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path.home()
LOG_DIR = HOME / ".hermes" / "logs"
POOL_FILE = HOME / ".hermes" / "api-key-pool.json"
COOLDOWN_FILE = HOME / ".hermes" / ".rotate_cooldown"
POOL_NAME = "primary"

# Only trigger on these specific API error patterns
ERROR_REGEX = re.compile(
    r"(?:"
    r"status[_\s]?code[:\s]*(?:429|401|403|402)"  # HTTP status codes
    r"|429[:\s]+too[_\s]?many[_\s]?requests"        # rate limit text
    r"|rate[_\s]?(?:limit|exceeded)"                  # rate limit
    r"|quota[_\s]?(?:exhausted|exceeded|depleted)"   # quota
    r"|api[_\s]?key[_\s]?(?:invalid|expired|revoked)" # bad key
    r"|authentication[_\s]?(?:failed|error|invalid)"  # auth fail
    r"|unauthorized"                                    # 401
    r"|forbidden"                                       # 403
    r"|billing[_\s]?(?:error|failed|issue)"            # billing
    r")",
    re.IGNORECASE,
)

# But ignore these benign patterns
IGNORE_REGEX = re.compile(
    r"(?:"
    r"rate[_\s]?limit[:\s]*false"      # rate_limit: false in config
    r"|rate[_\s]?limit[:\s]*off"       # rate limiting disabled
    r"|el.rate\."                      # team el rate (not API)
    r"|errore"                         # not error
    r"|no[_\s]?errors"                 # "no errors"
    r"|error[_\s]?free"                # "error free"
    r"|error[_\s]?count[:\s]*0"        # zero errors
    r"|success"                        # success lines
    r"|flush"                          # Telegram flush
    r"|inbound"                        # inbound messages
    r"|response[_\s]?ready"            # response ready
    r")",
    re.IGNORECASE,
)

PROVIDER_KEYWORDS = {
    "mimo": ["mimo", "xiaomi", "token-plan-sgp"],
    "mimo2": ["mimo2", "mimo", "xiaomi", "token-plan-sgp"],
    "openrouter": ["openrouter", "owl"],
}


def get_cooldown() -> float:
    """Return timestamp of last rotation, or 0."""
    if COOLDOWN_FILE.exists():
        try:
            return float(COOLDOWN_FILE.read_text().strip())
        except (ValueError, OSError):
            return 0
    return 0


def set_cooldown():
    """Set cooldown timestamp to now."""
    COOLDOWN_FILE.write_text(str(time.time()))


def in_cooldown(period: float = 30.0) -> bool:
    """Check if we rotated within the cooldown period."""
    last = get_cooldown()
    return (time.time() - last) < period


def load_pool() -> dict:
    if POOL_FILE.exists():
        return json.loads(POOL_FILE.read_text())
    return {}  # nosec


def save_pool(pool: dict):
    POOL_FILE.write_text(json.dumps(pool, indent=2))
    os.chmod(str(POOL_FILE), 0o600)


def get_current_key_id(pool: dict) -> str | None:
    """Get the key that was most recently used (current_index - 1)."""
    p = pool.get("pools", {}).get(POOL_NAME, {})
    keys = p.get("keys", [])
    idx = p.get("current_index", 0)
    if not keys:
        return None
    prev_idx = (idx - 1) % len(keys)
    return keys[prev_idx]["id"]


def detect_failed_key(error_line: str, pool: dict) -> str | None:
    """Determine which key failed based on error context."""
    error_lower = error_line.lower()

    # Check provider keywords
    for provider, keywords in PROVIDER_KEYWORDS.items():
        for kw in keywords:
            if kw in error_lower:
                # Find which key matches this provider
                current_id = get_current_key_id(pool)
                if current_id:
                    return current_id

    # Fallback: assume current active key failed
    current_id = get_current_key_id(pool)
    if current_id:
        return current_id

    # Last resort: first active key
    p = pool.get("pools", {}).get(POOL_NAME, {})
    for key in p.get("keys", []):
        if key["status"] == "active":
            return key["id"]

    return None


def get_error_type(error_line: str) -> str:
    """Classify error type."""
    line = error_line.lower()
    if "429" in line or "rate" in line or "too many" in line:
        return "rate_limit"
    if "401" in line or "403" in line or "auth" in line or "unauthorized" in line:
        return "invalid"
    if "402" in line or "quota" in line or "billing" in line:
        return "exhausted"
    return "rate_limit"  # default


def scan_logs(minutes: int = 2) -> list[str]:
    """Scan Hermes logs for API errors in the last N minutes."""
    errors = []
    cutoff = datetime.now() - timedelta(minutes=minutes)

    for log_name in ["errors.log", "gateway.log"]:
        log_path = LOG_DIR / log_name
        if not log_path.exists():
            continue

        try:
            with open(log_path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue

        for line in lines[-200:]:  # Last 200 lines only
            # Quick timestamp check (format: YYYY-MM-DD HH:MM)
            ts_match = re.match(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", line)
            if ts_match:
                try:
                    ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M")
                    if ts < cutoff:
                        continue
                except ValueError:
                    pass

            # Check error patterns
            if ERROR_REGEX.search(line) and not IGNORE_REGEX.search(line):
                errors.append(line.strip())

    return errors


def rotate_key(pool: dict, failed_key_id: str, error_type: str) -> dict:
    """Mark key as failed and pick next key."""
    p = pool["pools"][POOL_NAME]

    # Mark failed key
    for key in p["keys"]:
        if key["id"] == failed_key_id:
            status_map = {
                "rate_limit": "rate_limited",
                "exhausted": "exhausted",
                "invalid": "invalid",
            }
            key["status"] = status_map.get(error_type, "rate_limited")
            key["last_used"] = datetime.now().isoformat()
            key["last_used_ts"] = time.time()
            break

    save_pool(pool)
    return pool


def get_next_active_key(pool: dict) -> dict | None:
    """Get next active key after the failed one."""
    p = pool["pools"][POOL_NAME]
    active_keys = [k for k in p["keys"] if k["status"] == "active"]

    if not active_keys:
        return None

    strategy = p.get("strategy", "round_robin")
    if strategy == "round_robin":
        idx = p.get("current_index", 0)
        if idx >= len(active_keys):
            idx = 0
        selected = active_keys[idx]
        p["current_index"] = (idx + 1) % len(active_keys)
        return selected
    elif strategy == "least_used":
        return min(active_keys, key=lambda k: k.get("usage_count", 0))
    else:
        import random
        return random.choice(active_keys)


def update_hermes_config(key_entry: dict):
    """Update Hermes config.yaml with new key — triggers hot-reload."""
    provider = key_entry.get("provider", "")
    key = key_entry["key"]
    model = key_entry.get("model", "")
    base_url = key_entry.get("base_url", "")

    def run(cmd):
        subprocess.run(cmd, shell=True, check=True, capture_output=True)

    if provider in ("mimo", "mimo2"):
        run("hermes config set model.primary.provider mimo")
        run("hermes config set model.primary.model mimo-v2.5-pro")
        run(f'hermes config set model.primary.base_url {base_url}')
        run(f'hermes config set model.primary.api_key {key}')
    elif provider == "openrouter":
        run("hermes config set model.primary.provider openrouter")
        if model:
            run(f'hermes config set model.primary.model {model}')
        else:
            run("hermes config set model.primary.model openrouter/owl-alpha")
        run(f'hermes config set model.primary.base_url {base_url}')
        run(f'hermes config set model.primary.api_key {key}')


def reset_expired_keys(pool: dict) -> bool:
    """Reset rate_limited keys past cooldown."""
    now = time.time()
    changed = False
    for key in pool.get("pools", {}).get(POOL_NAME, {}).get("keys", []):
        if key["status"] == "rate_limited":
            last = key.get("last_used_ts", 0) or 0
            if now - last >= 60:
                key["status"] = "active"
                changed = True
                print(f"[monitor] Reset {key['id']} to active (cooldown expired)")
    if changed:
        save_pool(pool)
    return changed


def main():
    pool = load_pool()

    if not pool.get("pools", {}).get(POOL_NAME):
        print(f"[monitor] Pool '{POOL_NAME}' not found. Run setup first.")
        sys.exit(0)

    # Reset expired keys
    reset_expired_keys(pool)

    # Check cooldown
    if in_cooldown(period=30):
        last = get_cooldown()
        ago = time.time() - last
        print(f"[monitor] In cooldown ({ago:.0f}s ago). Skipping.")
        sys.exit(0)

    # Scan for errors
    errors = scan_logs(minutes=2)

    if not errors:
        sys.exit(0)

    error_line = errors[-1]
    print(f"[monitor] API error detected: {error_line[:120]}")

    # Detect failed key
    failed_key_id = detect_failed_key(error_line, pool)
    if not failed_key_id:
        print("[monitor] Could not determine failed key. Skipping.")
        sys.exit(0)

    error_type = get_error_type(error_line)
    print(f"[monitor] Failed: {failed_key_id} | Type: {error_type}")

    # Rotate
    pool = rotate_key(pool, failed_key_id, error_type)
    next_key = get_next_active_key(pool)

    if not next_key:
        print("[monitor] No active keys available!")
        sys.exit(1)

    print(f"[monitor] Rotating to: {next_key['id']} ({next_key.get('provider', '?')})")
    update_hermes_config(next_key)
    set_cooldown()

    # Update usage for new key
    for i, k in enumerate(pool["pools"][POOL_NAME]["keys"]):
        if k["id"] == next_key["id"]:
            pool["pools"][POOL_NAME]["keys"][i]["usage_count"] = k.get("usage_count", 0) + 1
            pool["pools"][POOL_NAME]["keys"][i]["last_used"] = datetime.now().isoformat()
            pool["pools"][POOL_NAME]["keys"][i]["last_used_ts"] = time.time()
            break
    save_pool(pool)

    print(f"[monitor] ✅ Active: {next_key['id']} ({next_key.get('provider', '?')}) | Model: {next_key.get('model', 'default')}")


if __name__ == "__main__":
    main()
