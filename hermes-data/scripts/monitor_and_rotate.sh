#!/bin/bash
# monitor_and_rotate.sh — monitor Hermes error logs + auto-rotate on rate-limit/auth errors
# Run via cron every 1-2 minutes

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROTATOR="${SCRIPT_DIR}/api_key_rotator.py"
AUTO_ROTATE="${SCRIPT_DIR}/auto_rotate.sh"
LOG_DIR="${HOME}/.hermes/logs"
POOL="primary"

# Error patterns to detect (case-insensitive)
# 429 = rate limit, 401/403 = auth error, 402 = quota exhausted
ERROR_PATTERNS="429|rate.limit|401|403|quota|exhausted|invalid.key|auth.fail"

# Check recent errors in Hermes logs (last 2 minutes)
check_errors() {
  local since_time
  since_time=$(date -d '2 minutes ago' '+%Y-%m-%d %H:%M' 2>/dev/null || date -v-2M '+%Y-%m-%d %H:%M' 2>/dev/null)

  # Scan error log
  if [ -f "${LOG_DIR}/errors.log" ]; then
    grep -iE "$ERROR_PATTERNS" "${LOG_DIR}/errors.log" 2>/dev/null | tail -5
  fi

  # Also check gateway log
  if [ -f "${LOG_DIR}/gateway.log" ]; then
    grep -iE "$ERROR_PATTERNS" "${LOG_DIR}/gateway.log" 2>/dev/null | tail -5
  fi
}

# Detect which provider failed based on error context
detect_failed_provider() {
  local error_log="$1"

  if echo "$error_log" | grep -qi "mimo\|xiaomi\|token-plan-sgp"; then
    # Find which mimo key is currently active
    local current_key_id
    current_key_id=$(python3 -c "
import json, os
pool_file = os.path.expanduser('~/.hermes/api-key-pool.json')
with open(pool_file) as f:
    pool = json.load(f)
keys = pool.get('pools', {}).get('primary', {}).get('keys', [])
idx = pool.get('pools', {}).get('primary', {}).get('current_index', 0)
active_keys = [k for k in keys if k['status'] == 'active']
if active_keys:
    # The current_index points to the NEXT key to use, so the one just used is (idx-1)
    prev_idx = (idx - 1) % len(keys)
    print(keys[prev_idx]['id'])
" 2>/dev/null)
    echo "$current_key_id"

  elif echo "$error_log" | grep -qi "openrouter\|owl"; then
    echo "openrouter-1"

  else
    # Unknown — rotate anyway using current active key
    python3 -c "
import json, os
pool_file = os.path.expanduser('~/.hermes/api-key-pool.json')
with open(pool_file) as f:
    pool = json.load(f)
keys = pool.get('pools', {}).get('primary', {}).get('keys', [])
idx = pool.get('pools', {}).get('primary', {}).get('current_index', 0)
active_keys = [k for k in keys if k['status'] == 'active']
if active_keys:
    prev_idx = (idx - 1) % len(keys)
    print(keys[prev_idx]['id'])
" 2>/dev/null
  fi
}

# Determine error type from log
get_error_type() {
  local error_log="$1"
  if echo "$error_log" | grep -qi "429\|rate.limit\|too.many"; then
    echo "rate_limit"
  elif echo "$error_log" | grep -qi "401\|403\|auth\|invalid.key\|unauthorized"; then
    echo "invalid"
  elif echo "$error_log" | grep -qi "402\|quota\|exhausted\|billing"; then
    echo "exhausted"
  else
    echo "rate_limit"  # default
  fi
}

# Main
ERRORS=$(check_errors)

if [ -z "$ERRORS" ]; then
  # No errors — check if any keys are rate_limited past cooldown and reset them
  python3 -c "
import json, os, time
pool_file = os.path.expanduser('~/.hermes/api-key-pool.json')
with open(pool_file) as f:
    pool = json.load(f)
changed = False
for pool_name, pool_data in pool.get('pools', {}).items():
    for key in pool_data.get('keys', []):
        if key['status'] == 'rate_limited':
            last_used = key.get('last_used_ts', 0) or 0
            if time.time() - last_used >= 60:
                key['status'] = 'active'
                changed = True
                print(f'[monitor] Reset {pool_name}/{key[\"id\"]} to active (cooldown expired)')
if changed:
    with open(pool_file, 'w') as f:
        json.dump(pool, f, indent=2)
" 2>/dev/null
  exit 0
fi

echo "[monitor] Detected errors:"
echo "$ERRORS" | tail -3

# Detect which key failed
FAILED_KEY=$(detect_failed_provider "$ERRORS")
ERROR_TYPE=$(get_error_type "$ERRORS")

if [ -z "$FAILED_KEY" ]; then
  echo "[monitor] Could not determine failed key — skipping rotation"
  exit 0
fi

echo "[monitor] Failed key: $FAILED_KEY | Error type: $ERROR_TYPE"

# Auto-rotate
bash "$AUTO_ROTATE" "$POOL" "$FAILED_KEY" "$ERROR_TYPE"
