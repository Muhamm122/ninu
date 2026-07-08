---
name: superagent-llm-proxy
description: "Setup and manage local OpenAI-compatible LLM proxy (FreeLLMAPI) that aggregates free-tier providers behind a single endpoint. Covers install, systemd service, provider key management, Hermes custom provider configuration, and multi-provider fallback chain management."
---

# LLM Proxy & Provider Chain Management

Manage the full AI provider stack: FreeLLMAPI proxy, Hermes custom providers, lightweight upstream proxies, and the model fallback chain.

## When to Use

- Setting up FreeLLMAPI for the first time
- Adding/removing provider keys
- Configuring Hermes custom providers
- Debugging proxy connectivity
- Setting up lightweight single-upstream proxies
- **Adding new AI providers** (MiMo, Groq, Cerebras, Gemini, etc.)
- **User asks which model to use** or wants to optimize cost/quality

## The Model Chain

```
PRIMARY:   MiMo V2.5 Pro (xiaomi) — paid, fast, good reasoning
FALLBACK1: NVIDIA NIM (qwen3-coder-480b / deepseek-v4-flash) — free, fast
FALLBACK2: OpenRouter / owl-alpha — reliable, 346 models
FALLBACK3: FreeLLMAPI (freellmapi:3001) — FREE, 102 models
FALLBACK4: OpenCode Proxy (:19912) — FREE, 45 models
```

**Cost optimization**: Use MiMo for heavy reasoning tasks. Use NVIDIA NIM (`qwen3-coder-480b` ~350ms TTFT, or `deepseek-v4-flash`) for fast coding tasks. Use FreeLLMAPI for everything else free.

**MiMo models** (confirmed 2026-06-08):
| Model | Type | Notes |
|-------|------|-------|
| `mimo-v2.5-pro` | Chat | Best reasoning, 128k context |
| `mimo-v2.5` | Chat | Base model |
| `mimo-v2-pro` | Chat | Previous gen |
| `mimo-v2-omni` | Multimodal | Vision + chat |
| `mimo-v2.5-tts` | TTS | Text-to-speech |
| `mimo-v2.5-asr` | ASR | Speech recognition |

**MiMo key format**: `tp-...` (40+ chars). Base URL: `https://token-plan-sgp.xiaomimimo.com/v1`

**NVIDIA NIM free-tier models (tested 2026-06-06)**:
| Model | Status | Notes |
|-------|--------|-------|
| `qwen/qwen3-coder-480b-a35b-instruct` | ✅ Works | 354ms TTFT, best coding |
| `deepseek-ai/deepseek-v4-flash` | ✅ Works | Fast, strong reasoning |
| `moonshotai/kimi-k2.6` | ✅ Works | 128k context |
| `mistralai/mistral-large-3-675b-instruct-2512` | ⚠️ Cold start | 60s+ first request |
| `meta/llama-4-maverick-17b-128e-instruct` | ⚠️ Cold start | 60s+ first request |
| `nvidia/nemotron-3-super-120b-a12b` | ❌ 403 | Enterprise only |
| `nvidia/nemotron-3-nano-30b-a3b` | ❌ 403 | Enterprise only |

**NVIDIA NIM setup**: Sign up at https://build.nvidia.com (user must do from own device — hCaptcha blocks AWS IP). Get API key from avatar → "Get API Key". Key format: `nvapi-...`. Add to Hermes: `hermes config set providers.nvidia.base_url https://integrate.api.nvidia.com/v1` and `hermes config set providers.nvidia.api_key nvapi-...`.

## Prerequisites

- Node.js 20+ (`node --version`)
- npm 10+
- OpenSSL (for encryption key generation)

## FreeLLMAPI Install

### ⚠️ CRITICAL: PM2 Env Management

**`pm2 set` replaces the ENTIRE process env with a single JSON string — it does NOT merge.**

```bash
# ❌ WRONG — wipes ENCRYPTION_KEY, NODE_ENV, and ALL other env vars
pm2 set freellmapi:env '{"PROXY_RATE_LIMIT_RPM":"0"}'

# ✅ CORRECT — use ecosystem config file
cat > /opt/freellmapi/ecosystem.config.cjs << 'EOF'
module.exports = {
  apps: [{
    name: 'freellmapi',
    script: 'dist/index.js',
    cwd: '/opt/freellmapi/server',
    env: {
      ENCRYPTION_KEY: 'your-64-char-hex-key-here',
      PROXY_RATE_LIMIT_RPM: '0',
      NODE_ENV: 'production',
    },
  }],
};
EOF
pm2 start /opt/freellmapi/ecosystem.config.cjs
```

**`pm2 start --env` flag does NOT work either** — process env vars are not set. Only ecosystem files reliably pass env vars.

**`pm2 restart --update-env`** is needed after `pm2 set` to pick up new env, but `pm2 set` replaces the whole env so it's still dangerous.

**dotenvx injection**: FreeLLMAPI uses `dotenvx` which scans `../.env` from working directory and **overrides** `process.env` vars. Even if PM2 sets ENCRYPTION_KEY, a `.env` file in parent dir can nullify it. Log line `◇ injected env (0) from ../.env` means 0 vars injected (safe). If count > 0, those vars are overriding PM2 env. Always check `/opt/freellmapi/.env` for unexpected overrides.

**Recovery if ENCRYPTION_KEY was wiped**:
1. Find the original key in DB: `SELECT value FROM settings WHERE key = 'encryption_key'`
2. If the DB key was also regenerated, you must re-insert all API keys (old encrypted keys are unrecoverable)
3. Use ecosystem file to restart with the correct ENCRYPTION_KEY

### ⚠️ CRITICAL: Shell Quoting with Secrets

**Bash expands `***` as glob pattern.** Any Bearer token containing `***` will be corrupted.

```bash
# ❌ WRONG — *** expanded by bash glob
curl -H "Authorization: Bearer *** -d '...'

# ✅ CORRECT — use Python
import urllib.request, json
KEY = "freellmapi-..."
req = urllib.request.Request(url, data=payload,
    headers={"Authorization": "Bearer " + KEY}, method="POST")
```

### ⚠️ CRITICAL: FreeLLMAPI Auth Check

**FreeLLMAPI Auth Key Format**: The unified API key is stored as **plaintext** in DB `settings` table (`key = 'unified_api_key'`). Format: `freellmapi-<64-hex-chars>` (total 59 chars). Example: `freellmapi-3f3ae86521eba8c49ec39d2380a632833b544bd927b3fde0`. To verify: `cd /opt/freellmapi/server && node -e "const Database = require('better-sqlite3')('./data/freeapi.db'); const row = Database.prepare('SELECT value FROM settings WHERE key = ?').get('unified_api_key'); console.log(row.value);"`

**Shell quoting**: NEVER use `Bearer ***` inline in bash curl — glob expansion corrupts tokens. Always use Python urllib for API calls with secrets.



## Systemd Service

**⚠️ CRITICAL**: Node.js is NOT at `/usr/bin/node`. Use `$(which node)` — typically `~/.local/bin/node`.

```bash
NODE_PATH=$(which node)
sudo tee /etc/systemd/system/freellmapi.service > /dev/null << EOF
[Unit]
Description=FreeLLMAPI - OpenAI-compatible proxy for free LLM providers
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/freellmapi
ExecStart=${NODE_PATH} /opt/freellmapi/server/dist/index.js
Environment=NODE_ENV=production
Environment=PORT=3001
Environment=ENCRYPTION_KEY=<your-key-here>
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && sudo systemctl enable --now freellmapi
```

**Verify**: `sudo systemctl status freellmapi --no-pager && curl -s http://127.0.0.1:3001/api/ping`

## Provider Key Management

### Setup admin → Login → Add keys → Get unified key
```bash
# Setup
curl -s -X POST http://127.0.0.1:3001/api/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@localhost", "password": "your-password"}'

# Login → get admin token
curl -s -X POST http://127.0.0.1:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@localhost", "password": "your-password"}'

# Add provider key (use admin token)
curl -s -X POST http://127.0.0.1:3001/api/keys \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"platform": "openrouter", "key": "sk-...", "label": "My Key"}'

# Get unified client key
curl -s http://127.0.0.1:3001/api/settings/api-key \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### Direct SQLite Key Insertion (When Admin API Unavailable)

FreeLLMAPI encrypts keys with AES-256-GCM. Insert directly via Node.js:

```bash
cd /opt/freellmapi/server  # MUST run from here (node_modules exists)

node --input-type=module -e '
import crypto from "crypto";
import Database from "better-sqlite3";
import dotenv from "dotenv";
dotenv.config({ path: "/opt/freellmapi/.env" });

const ALGO = "aes-256-gcm";
const db = new Database("/opt/freellmapi/server/data/freeapi.db");
let encKey = process.env.ENCRYPTION_KEY;
if (!encKey) {
    const row = db.prepare("SELECT value FROM settings WHERE key = ?").get("encryption_key");
    encKey = row ? row.value : crypto.randomBytes(32).toString("hex");
}
const kb = Buffer.from(encKey, "hex");

function encrypt(text) {
    const iv = crypto.randomBytes(16);
    const c = crypto.createCipheriv(ALGO, kb, iv);
    return { e: c.update(text, "utf8", "hex") + c.final("hex"), iv: iv.toString("hex"), at: c.getAuthTag().toString("hex") };
}

const now = new Date().toISOString().replace("T"," ").slice(0,19);
const [,, platform, label, key] = process.argv;
const enc = encrypt(key);
db.prepare("INSERT INTO api_keys (platform,label,encrypted_key,iv,auth_tag,status,enabled,created_at) VALUES (?,?,?,?,?,?,?,?)")
  .run(platform, label, enc.e, enc.iv, enc.at, "unknown", 1, now);
console.log("Added:", platform, label);
' <platform> <label> <key>
```

**Key insertion pitfalls**:
- Must run from `/opt/freellmapi/server` (NOT /tmp — `better-sqlite3` native module not found)
- Use `--input-type=module` for ESM imports
- DB path: `/opt/freellmapi/server/data/freeapi.db` (NOT `dist/db/freellmapi.db` — that's an empty placeholder)
- `execute_code` blocks subprocess calls; use `terminal()` for shell commands
- Shell quoting: write JSON payloads to file first (`/tmp/payload.json`), reference with `@` in curl

See `references/2026-06-08-keys-fallback.md` for detailed session notes.

## Adding New Providers (MiMo, Groq, Cerebras, etc.)

**Provider base URLs:**
| Provider | Base URL |
|----------|----------|
| MiMo | `https://token-plan-sgp.xiaomimimo.com/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| Cerebras | `https://api.cerebras.ai/v1` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` |
| DeepSeek | `https://api.deepseek.com/v1` |
| SambaNova | `https://api.sambanova.ai/v1` |
| OpenCode | `https://opencode.ai/zen/v1` |
| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` |

**Steps:**
1. Add key to FreeLLMAPI via admin API or direct SQLite insertion
2. Add to Hermes config via `hermes config set custom_providers` (include ALL existing!)
3. For paid providers, check quota on their dashboard — agent cannot check

## Hermes Custom Provider Config

**⚠️ SAFETY**: `hermes config set custom_providers` replaces ENTIRE array. Always include ALL existing providers.

### View current providers first
```bash
python3 -c "
import yaml, json
with open('/home/ubuntu/.hermes/config.yaml') as f:
    c = yaml.safe_load(f)
cp = c.get('custom_providers', [])
if isinstance(cp, str): cp = json.loads(cp)
for p in cp: print(f\"  {p['name']:20} {p['base_url']}\")
"
```

### Set providers (include ALL existing + new)
```bash
hermes config set custom_providers '[
  {"name":"ninu","base_url":"https://llm.g4rrzx.my.id/v1","api_key":"sk-syz...","model":"anthropic/claude-opus-4-7","api_mode":"chat_completions"},
  {"name":"mimu","base_url":"https://cc.freemodel.dev/v1","api_key":"fe_oa_...","model":"claude-sonnet-4-6"},
  {"name":"freellmapi","base_url":"http://127.0.0.1:3001/v1","api_key":"freellmapi-...","model":"auto","api_mode":"chat_completions"},
  {"name":"chatbai","base_url":"https://chat.b.ai/v1","api_key":"sk-...","model":"auto","api_mode":"chat_completions"},
  {"name":"opencode_free","base_url":"http://127.0.0.1:19912/v1","api_key":"sk-dummy","model":"deepseek-v4-flash-free","api_mode":"chat_completions"}
]'
```

**Use per-session**: `hermes -m freellmapi/auto` or `hermes -m opencode_free/deepseek-v4-flash-free`

## Cron Job Provider Pinning (CRITICAL)

**ALWAYS pin explicit provider/model for cron jobs.** Null resolves to "Stealth" → 400 error.

```python
# CORRECT
cronjob(action="create", schedule="0 8 * * *",
        model={"provider": "openrouter", "model": "openrouter/owl-alpha"},
        prompt="...")

# WRONG — null → "Stealth" → 400 error
cronjob(action="create", schedule="0 8 * * *", prompt="...")
```

**Fix existing**: `cronjob(action="update", job_id="...", model={"provider": "openrouter", "model": "openrouter/owl-alpha"})`

**Rule of thumb**: LLM-needed cron → pin `openrouter/owl-alpha`. Script-only cron → use **systemd timer** (zero tokens, zero errors).

## 9Router — Unified AI Proxy Dashboard

9Router v0.4.71+ unifies all providers behind `localhost:20128` with a web dashboard, smart fallback combos, and built-in provider integrations (NVIDIA NIM, OpenRouter, Gemini, Groq, Cerebras, 30+ more).

**Headless VPS setup**: The CLI's interactive TUI menu auto-exits in non-TTY — must use `--tray --no-browser --skip-update --log` flags. The `--tray` flag spawns a background process that keeps the Next.js server alive; without it, the inquirer menu renders in non-TTY, auto-selects "exit", and the process dies after ~7 seconds. Systray2 native module must be pre-installed (`npm install systray2@2.1.4` inside 9router's node_modules) or the tray child process crashes.

**9Router systemd service**:
```bash
# MUST use full node path + cli.js path, NOT the symlink
# The symlink (../lib/node_modules/9router/cli.js) has #!/usr/bin/env node
# which fails in systemd because node isn't in the systemd PATH
ExecStart=/home/ubuntu/.local/bin/node /home/ubuntu/.hermes/node/lib/node_modules/9router/cli.js --tray --no-browser --skip-update --log
Environment=PATH=/home/ubuntu/.local/bin:/home/ubuntu/.hermes/node/bin:/usr/local/bin:/usr/bin:/bin
```

**9Router provider injection via SQLite**: The dashboard API requires httpOnly session cookies that browser tools can't extract. Direct SQLite injection into `/home/ubuntu/.9router/db/data.sqlite` is the reliable method:
```bash
sudo systemctl stop 9router
sqlite3 ~/.9router/db/data.sqlite "INSERT INTO providerNodes (id,type,name,data,createdAt,updatedAt) VALUES ('...','openai-compatible','MyProvider','{\"baseUrl\":\"...\"}','...','...');"
sqlite3 ~/.9router/db/data.sqlite "INSERT INTO providerConnections (id,provider,authType,name,priority,isActive,data,createdAt,updatedAt) VALUES ('...','<node_id>','api-key','ConnName',1,1,'{\"apiKey\":\"...\"}','...','...');"
sudo systemctl start 9router
```
Tables: `providerNodes`, `providerConnections`, `apiKeys`, `settings`, `combos`. Check schema with `.schema <table>` before inserting.

**9Router dashboard auth**: Default password is `123456`. Change immediately via Settings → Security → Set Password before enabling the Cloudflare tunnel. The tunnel URL is disposable — changes on tunnel restart; check `/tmp/9router-tunnel.log` for the new URL.

See `references/9router-setup.md` for full install and CF tunnel.

## Lightweight Single-Upstream Proxies

For free-tier access to a specific provider, use a minimal Node.js proxy instead of full FreeLLMAPI.

See: `references/opencode-free-proxy.md`

Pattern: `~/proxy-name/index.js` → Express + CORS → upstream API → PM2 → Hermes custom provider.

## Free LLM Provider Reference

See `references/free-providers.md` for full comparison (Cerebras, Groq, Gemini, DeepSeek, SambaNova, SiliconFlow, Mistral, Together AI).

**Quick picks**: Cerebras (fastest ~2000 tok/sec) → Groq (best free limits) → Gemini (instant key, strongest models).

## FreeLLMAPI Fallback Architecture (Confirmed 2026-06-08)

FreeLLMAPI has a **complete built-in fallback system** — no external retry logic needed.

**Source**: `/opt/freellmapi/server/dist/services/router.js` + `routes/proxy.js`

| Mechanism | Detail |
|-----------|--------|
| Retry loop | `MAX_RETRIES = 20` — tries up to 20 different model+key combos per request |
| Rate limit detection | `isRetryableError()` catches 429, 503, 500, 413, 404, timeout, connection errors |
| Cooldown | Failed model+key put on cooldown (duration from `getCooldownDurationForLimit`) |
| Penalty system | Each 429 adds +3 penalty to model priority (max 10). Penalty decays every 2 min. |
| Key round-robin | Multiple keys per platform are rotated via `roundRobinIndex` |
| Sticky sessions | Same conversation stays on same model (30-min TTL, keyed by first user message hash) |
| Skip tracking | `skipKeys` set tracks failed `platform:modelId:keyId` combos within a single request |
| IP rate limit | 120 req/min per IP (in-memory, `PROXY_RATE_LIMIT_RPM` to adjust, `0` to disable) |

**CRITICAL LIMITATION**: Fallback is per-model, but ALL models on the same platform share the same key(s). If OpenRouter key hits rate limit, ALL ~40 OpenRouter models fail together. **Solution**: Add multiple keys per platform, or add more providers with separate free keys.

**upstream vs IP rate limit**: After disabling IP rate limit (`PROXY_RATE_LIMIT_RPM=0`), you may still see 429 errors. These are from the **upstream provider** (OpenRouter, NVIDIA, etc.), not FreeLLMAPI. Verify by checking response body — upstream 429 includes provider-specific headers, FreeLLMAPI IP 429 says "Rate limit exceeded: more than N requests per minute".

**DB paths**:
- Actual data: `/opt/freellmapi/server/data/freeapi.db` (NOT `dist/db/freellmapi.db` which is empty)
- Schema: `api_keys`, `models`, `fallback_config`, `rate_limit_cooldowns`, `rate_limit_usage`, `requests`, `sessions`, `settings`

**Key insight**: If FreeLLMAPI returns 429 "All models exhausted", the issue is upstream provider keys — not the fallback logic. Add more keys via admin API or direct SQLite insertion.

See `references/pm2-env-gotchas.md` for PM2 env management (critical — `pm2 set` can wipe ENCRYPTION_KEY).


## ⚠️ CRITICAL: Provider Platform Routing

FreeLLMAPI registers built-in providers with **hardcoded base URLs**. Only the `custom` platform reads `base_url` from the `api_keys` DB row.

| Platform | Hardcoded Base URL | Uses DB base_url? |
|----------|-------------------|-------------------|
| `openrouter` | `https://openrouter.ai/api/v1` | ❌ No |
| `opencode` | `https://opencode.ai/zen/v1` | ❌ No |
| `nvidia` | `https://integrate.api.nvidia.com/v1` | ❌ No |
| `groq` | `https://api.groq.com/openai/v1` | ❌ No |
| `custom` | *(from api_keys.base_url)* | ✅ Yes |
| `kilo` | `https://api.kilo.ai/api/gateway/v1` | ❌ No |

**Implication**: To route models through a **local proxy** (e.g. OpenCode proxy at `localhost:19912`):
1. Set the model's platform to `custom` (NOT `opencode`)
2. Set the API key's platform to `custom`
3. Set the key's `base_url` to `http://localhost:19912/v1`
4. Re-encrypt the key with the **correct** ENCRYPTION_KEY (see below)

```sql
-- Fix: change model platform from 'opencode' to 'custom'
UPDATE models SET platform='custom' WHERE platform='opencode';
-- Fix: change key platform + set base_url
UPDATE api_keys SET platform='custom', base_url='http://localhost:19912/v1' WHERE id=4;
```

**Symptom**: FreeLLMAPI returns 502 "Provider error (X): API error 401: Invalid API key" even though the key works directly. Or returns 429 "All models exhausted" because no matching key exists for the model's platform.

**Verification**: After fix, `curl` test should return the model from the local proxy, NOT a fallback model from OpenRouter. Check `result.model` in response — if it's `openai/gpt-oss-120b:free` when you requested `mimo-v2.5-free`, the routing fell back to OpenRouter (platform mismatch still).

## ⚠️ CRITICAL: ENCRYPTION_KEY Dual Source

The ENCRYPTION_KEY may differ between:
- **systemd service**: `/etc/systemd/system/freellmapi.service` → `Environment=ENCRYPTION_KEY=...`
- **ecosystem config**: `/opt/freellmapi/ecosystem.config.cjs` → `env.ENCRYPTION_KEY`

**Always check which one the RUNNING service uses** before re-encrypting keys:

```bash
# Check systemd key
grep ENCRYPTION_KEY /etc/systemd/system/freellmapi.service

# Check ecosystem key
grep ENCRYPTION_KEY /opt/freellmapi/ecosystem.config.cjs
```

If they differ, the systemd key wins (FreeLLMAPI runs via systemd in production). Re-encrypt with the systemd key:

```bash
node -e "
const crypto = require('crypto');
const ENCRYPTION_KEY = '<systemd-key-here>';
const key = Buffer.from(ENCRYPTION_KEY, 'hex');
const iv = crypto.randomBytes(16);
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
let encrypted = cipher.update('dummy-key-not-needed', 'utf8', 'hex');
encrypted += cipher.final('hex');
const authTag = cipher.getAuthTag().toString('hex');
console.log(JSON.stringify({encrypted, iv: iv.toString('hex'), authTag}));
"
```

Then update DB:
```python
import sqlite3
db = sqlite3.connect('/opt/freellmapi/server/data/freeapi.db')
db.execute("UPDATE api_keys SET encrypted_key=?, iv=?, auth_tag=?, status='healthy' WHERE id=?",
           (encrypted, iv, auth_tag, key_id))
db.commit()
```

**Restart**: `sudo systemctl restart freellmapi` (NOT `pm2 restart` — it runs via systemd).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| systemd exit 203/EXEC | Wrong node path — use `$(which node)` |
| Port not listening | Check `sudo journalctl -u freellmapi -n 30` |
| Key rejected | Verify format; test with curl first |
| `hermes config set` timeout | Run directly in session, needs interactive approval |
| Cron 400 "Stealth" error | Pin explicit `model`+`provider` in cron job |
| f-string with masked secrets → SyntaxError | Use string concatenation: `"Bearer " + token` |
| Shell quoting failures | Write payload to file first (`/tmp/payload.json`), reference with `@` |
| 9Router "Exiting..." immediately | Non-TTY mode — use `--tray --no-browser --skip-update --log` flags |
| 9Router 401 via dashboard API | Dashboard uses httpOnly session cookies; use SQLite direct injection instead |
| 9Router systray crash / "Exiting..." | Pre-install `systray2@2.1.4` in 9router node_modules; use `--tray --no-browser` flags |
| 9Router systemd exit 127 | Node not in PATH — add `Environment=PATH=...` to service file with full node path |
| NVIDIA NIM 403 Forbidden | Model is enterprise-only; use free-tier models (qwen3-coder-480b, deepseek-v4-flash) |
| NVIDIA NIM signup hCaptcha | Cannot automate from AWS IP; user signs up on own device |
| NVIDIA NIM cold start timeout | Large models (675B+) take 60s+ first request; use smaller models or pre-warm |
| FreeLLMAPI 429 "All models exhausted" | Add more provider keys; check key health in dashboard. **Also check platform mismatch**: model platform must match key platform. If model is `opencode` but key is `custom` (or vice versa), no key is found. |
| FreeLLMAPI 502 "Invalid API key" for local proxy | Platform mismatch or wrong ENCRYPTION_KEY. Model+key must both be `custom` platform. Re-encrypt key with systemd's ENCRYPTION_KEY (not ecosystem's). See Provider Platform Routing section. |
| FreeLLMAPI returns fallback model instead of requested | Model routing fell back to OpenRouter — the model's platform doesn't match any key's platform. Check: `SELECT platform FROM models WHERE model_id='X'` vs `SELECT platform FROM api_keys WHERE enabled=1`. |
| FreeLLMAPI chat returns "Service Unavailable" | Provider endpoint down; check if WARP proxy needed for that region |
| execute_code subprocess blocked | Use `terminal()` instead; `execute_code` blocks subprocess.run() |
| WARP exit region won't change | Disconnect/reconnect keeps same nearest exit node; need different proxy for region change |
| PM2 restart wrong process | `pm2 restart <id>` targets by ID not name — verify with `pm2 list` first |
| FreeLLMAPI key insert fails from /tmp | Must run from `/opt/freellmapi/server` (node_modules path) |
| IP rate limit blocks all requests | Wait 2+ min for 120 req/min window to reset; set `PROXY_RATE_LIMIT_RPM=0` to disable (via ecosystem file, NOT `pm2 set`) |
| FreeLLMAPI 401 after restart | ENCRYPTION_KEY wiped — `pm2 set` replaces ENTIRE env. Fix: use ecosystem.config.cjs with ENCRYPTION_KEY in env block. See PM2 Env section below. |
| Shell `***` glob expansion | Tokens with `***` expanded by bash glob. ALWAYS use Python (urllib/request) for API calls with secrets, NEVER inline curl with `Bearer ***` in shell. |
| MiMo 401 Invalid Key | Wrong base URL — use `https://token-plan-sgp.xiaomimimo.com/v1` (NOT `api.mimo.ai`). Test with Python urllib, not curl inline. |
| MiMo empty content | `reasoning_content` has text but `content` is empty — reduce `max_tokens` or lower `temperature` to ~0.1. |
| 429 after IP rate limit disabled | Upstream provider rate limit (OpenRouter key), not FreeLLMAPI. Add more keys from different providers. |

See `references/pitfalls.md` for extended troubleshooting.

## Current Setup (as of 2026-06-08)

| Service | Port | Manager | Models |
|---------|------|---------|--------|
| FreeLLMAPI | 3001 | **systemd** | 102 models (aggregated) |
| OpenCode Proxy | 19912 | PM2 | 45 models |
| 9Router | 20128 | systemd | Unified dashboard + combo fallback |
| NVIDIA NIM | — | cloud | Free-tier serverless (qwen3-coder-480b, deepseek-v4-flash, kimi-k2.6) |
| Hermes Gateway | — | systemd | 7+ providers (MiMo, NVIDIA, OpenRouter, FreeLLMAPI, OpenCode, 9Router) |

**MiMo API Key**: `tp-s498deb...` (stored in Hermes config)
**FreeLLMAPI Key**: `freellmapi-3f3ae86521eba8c49ec39d2380a632833b544bd927b3fde0`
**NVIDIA NIM Key**: `nvapi-...` (stored in Hermes config)
**9Router API Key**: `9r-...` (stored in `.env` as `NINEROUTER_API_KEY`)
**9Router Dashboard**: via Cloudflare tunnel (URL in tunnel log)
**Admin**: admin@freellmapi.local / admin123

**FreeLLMAPI registered keys (6 total)**:
| # | Platform | Label | Status |
|---|----------|-------|--------|
| 1 | openrouter | OpenRouter Main | healthy |
| 2 | custom | chat.b.ai key 1 | unknown |
| 3 | custom | chat.b.ai key 2 | unknown |
| 4 | custom | opencode-free-proxy | healthy |
| 5 | nvidia | nvidia-direct | unknown |
| 6 | openrouter | openrouter-direct | unknown |

**Note**: User cannot check API key balances from Hermes session. Direct them to provider dashboards.

## Blocking Pattern — Move On Quickly

When blocked (missing creds, IP block, expired keys) and user told twice: **stop asking, offer alternative, move on**. User frustration signals ("oke tinggalkan", "lupakan") = drop immediately. Do NOT repeat the blocker.

## Provider Registration Blockers

Some providers require auth flows that cannot be completed from a headless VPS. See `references/provider-registration-blockers.md` for the full catalog.

**Quick reference:**
| Blocker | Affected Providers | Workaround |
|---------|-------------------|------------|
| Alibaba Cloud SSO | Qwen Cloud, DashScope | Register from local browser + phone |
| Clerk Auth | Cambrian, many Web3 startups | Register from local browser |
| Discord OAuth | Airdrop/gaming platforms | Connect from local browser |
| hCaptcha/Turnstile | NVIDIA NIM, Cloudflare signups | User registers from own device |

**Decision rule**: If 2+ attempts fail within 5 minutes, report blocker to user with alternatives. Don't grind on VPS-impossible registrations.