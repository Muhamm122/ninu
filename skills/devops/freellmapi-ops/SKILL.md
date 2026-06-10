---
name: freellmapi-ops
description: FreeLLMAPI operations — PM2 env management, encryption key recovery, rate limit config, shell token safety.
triggers:
  - freellmapi
  - freellm
  - llm proxy
  - openrouter proxy
  - model fallback
  - rate limit
---

# FreeLLMAPI Ops

## ⚠️ PM2 ENV — CRITICAL

**NEVER use `pm2 set`** — it replaces the ENTIRE process env with a single JSON string, wiping ENCRYPTION_KEY and all other vars. All encrypted API keys become **unrecoverable**.

**NEVER use `pm2 start --env '{...}'`** — this flag does NOT actually pass env vars to the process.

**ONLY reliable method:** ecosystem `.config.cjs` file:

```js
// ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'freellmapi',
    script: 'dist/index.js',
    cwd: '/opt/freellmapi/server',
    env: {
      ENCRYPTION_KEY: '64-char-hex-here',
      PROXY_RATE_LIMIT_RPM: '0',
      NODE_ENV: 'production',
    },
  }],
};
```

Then: `pm2 start ecosystem.config.cjs`

## ENCRYPTION_KEY Recovery

If ENCRYPTION_KEY is lost, find the original in SQLite DB:

```bash
node -e "
const Database = require('better-sqlite3')('/opt/freellmapi/server/data/freeapi.db');
const row = Database.prepare('SELECT value FROM settings WHERE key = ?').get('encryption_key');
console.log(row.value);
"
```

If the DB key was overwritten by auto-generation, encrypted keys are **gone**. No recovery possible.

## dotenvx Override

FreeLLMAPI uses **dotenvx** which scans `../.env` (parent of cwd) and overrides PM2 env vars. Check for rogue `.env` files:

```bash
ls -la /opt/freellmapi/.env /opt/freellmapi/server/.env 2>/dev/null
```

## IP Rate Limit

Default: 120 requests/minute per IP. Disable:

```js
// In ecosystem.config.cjs env:
PROXY_RATE_LIMIT_RPM: '0'
```

After disabling, 429 errors = **upstream provider** rate limit (e.g. OpenRouter), not FreeLLMAPI.

## Shell Token Safety

**NEVER pass API keys in shell curl commands** — `***` gets glob-expanded by bash, corrupting the token.

**Always use Python urllib:**

```python
import urllib.request, json
KEY = "freellmapi-3f3ae86521eba8c49ec39d2380a632833b544bd927b3fde0"
req = urllib.request.Request(url, data=payload,
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY},
    method="POST")
```

## Unified API Key

Stored as **plaintext** in DB `settings` table:

```bash
node -e "
const Database = require('better-sqlite3')('/opt/freellmapi/server/data/freeapi.db');
const row = Database.prepare('SELECT value FROM settings WHERE key = ?').get('unified_api_key');
console.log(row.value);
"
```

## Provider Platform Routing (CRITICAL)

Built-in providers have **hardcoded base URLs**. Only `custom` platform reads `base_url` from DB.

**Symptom**: Request for `mimo-v2.5-free` returns `openai/gpt-oss-120b:free` (fallback), or 502 "Invalid API key", or 429 "All models exhausted".

**Root cause**: Model platform (`opencode`) doesn't match any key platform. The `opencode` provider is hardcoded to `https://opencode.ai/zen/v1`, not your local proxy.

**Fix**:
```sql
-- Both model and key must be 'custom' platform
UPDATE models SET platform='custom' WHERE platform='opencode';
UPDATE api_keys SET platform='custom', base_url='http://localhost:19912/v1' WHERE id=4;
```

**Verify**: After restart, test and check `result.model` matches the requested model (not a fallback).

## ENCRYPTION_KEY Dual Source

systemd service (`/etc/systemd/system/freellmapi.service`) and ecosystem config may have **different** ENCRYPTION_KEYs. Always re-encrypt keys with the **systemd** key (that's what runs in production). Check with: `grep ENCRYPTION_KEY /etc/systemd/system/freellmapi.service`

## Fallback Behavior

FreeLLMAPI fallback is **per-model**, not per-key. All OpenRouter models share one OpenRouter key → if that key is rate-limited, ALL OpenRouter models fail together. Add multiple keys per platform for true redundancy.

## Version Check

```bash
cd /opt/freellmapi/server && cat package.json | grep version
# Current: 0.2.1 (as of 2026-06-08)
```

## Quick Troubleshooting

| Symptom | Fix |
|---------|-----|
| 429 "All models exhausted" | Platform mismatch or all keys rate-limited. Check `SELECT platform, model_id FROM models WHERE model_id='X'` matches a key's platform. |
| 502 "Invalid API key" for local proxy | Re-encrypt key with systemd's ENCRYPTION_KEY. Model+key must both be `custom` platform. |
| Request returns wrong/fallback model | Model platform doesn't match any key → falls back to OpenRouter. Set both to `custom`. |
| `sudo systemctl restart freellmapi` needed | FreeLLMAPI runs via systemd, NOT PM2. Always use systemctl. |
