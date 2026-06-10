#!/bin/bash
# auto_rotate.sh — rotate to next key in pool + hot-reload Hermes config
# Usage: auto_rotate.sh <pool_name> <failed_key_id> <error_type>

set -euo pipefail

POOL="${1:?Usage: auto_rotate.sh <pool> <key_id> <error_type>}"
KEY_ID="${2:?Missing key_id}"
ERROR_TYPE="${3:?Missing error_type}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROTATOR="${SCRIPT_DIR}/api_key_rotator.py"

# Step 1: Report failure
python3 "$ROTATOR" fail "$POOL" "$KEY_ID" "$ERROR_TYPE"

# Step 2: Get next key
NEXT_JSON=$(python3 "$ROTATOR" get "$POOL")
NEXT_KEY=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['key'])")
NEXT_PROVIDER=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['provider'])")
NEXT_BASE_URL=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['base_url'])")
NEXT_MODEL=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('model',''))")
NEXT_KEY_ID=$(echo "$NEXT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['key_id'])")

echo "[auto_rotate] Switching to: $NEXT_KEY_ID ($NEXT_PROVIDER)"

# Step 3: Update Hermes config
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
else
  echo "[auto_rotate] Unknown provider: $NEXT_PROVIDER — skipping config update"
  exit 0
fi

echo "[auto_rotate] Done. Hermes hot-reloads on next request."
echo "[auto_rotate] Active: $NEXT_KEY_ID ($NEXT_PROVIDER) | Model: $NEXT_MODEL"
