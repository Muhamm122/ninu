#!/bin/bash
# rotate_now.sh — rotate to next key in pool "primary"
# Auto-detects current key from pool and rotates to next
# Usage: bash rotate_now.sh [error_type]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROTATOR="${SCRIPT_DIR}/api_key_rotator.py"
POOL="primary"
ERROR_TYPE="${1:-rate_limit}"

# Get current active key (the one that was just used)
CURRENT_KEY_ID=$(python3 -c "
import json, os
pool_file = os.path.expanduser('~/.hermes/api-key-pool.json')
with open(pool_file) as f:
    pool = json.load(f)
keys = pool.get('pools', {}).get('primary', {}).get('keys', [])
idx = pool.get('pools', {}).get('primary', {}).get('current_index', 0)
if keys:
    prev_idx = (idx - 1) % len(keys)
    print(keys[prev_idx]['id'])
" 2>/dev/null)

if [ -z "$CURRENT_KEY_ID" ]; then
  echo "[rotate] ERROR: Could not detect current key"
  exit 1
fi

echo "[rotate] Current key: $CURRENT_KEY_ID | Error: $ERROR_TYPE"

# Report failure + get next key
python3 "$ROTATOR" fail "$POOL" "$CURRENT_KEY_ID" "$ERROR_TYPE"

# Get next key details
NEXT_JSON=$(python3 "$ROTATOR" get "$POOL")
NEXT_KEY=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])")
NEXT_PROVIDER=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['provider'])")
NEXT_BASE_URL=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['base_url'])")
NEXT_MODEL=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model',''))")
NEXT_KEY_ID=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['key_id'])")

echo "[rotate] Switching to: $NEXT_KEY_ID ($NEXT_PROVIDER)"

# Update Hermes config
if [ "$NEXT_PROVIDER" = "mimo" ] || [ "$NEXT_PROVIDER" = "mimo2" ]; then
  hermes config set model.primary.provider mimo
  hermes config set model.primary.model mimo-v2.5-pro
  hermes config set model.primary.base_url https://token-plan-sgp.xiaomimimo.com/v1
  hermes config set model.primary.api_key "$NEXT_KEY"
elif [ "$NEXT_PROVIDER" = "openrouter" ]; then
  hermes config set model.primary.provider openrouter
  if [ -n "$NEXT_MODEL" ] && [ "$NEXT_MODEL" != "None" ] && [ "$NEXT_MODEL" != "" ]; then
    hermes config set model.primary.model "$NEXT_MODEL"
  else
    hermes config set model.primary.model openrouter/owl-alpha
  fi
  hermes config set model.primary.base_url https://openrouter.ai/api/v1
  hermes config set model.primary.api_key "$NEXT_KEY"
fi

echo "[rotate] ✅ Active: $NEXT_KEY_ID ($NEXT_PROVIDER) | Model: $NEXT_MODEL"
echo "[rotate] Hermes hot-reloads on next request."
