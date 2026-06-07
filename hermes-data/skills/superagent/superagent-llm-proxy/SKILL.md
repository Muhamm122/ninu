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

```bash
git clone https://github.com/tashfeenahmed/freellmapi.git /opt/freellmapi
cd /opt/freellmapi
npm install && npm run build
ENCRYPTION_KEY=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" > .env
echo "PORT=3001" >> .env
```

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

## Adding New Providers (MiMo, Groq, Cerebras, etc.)

**Provider base URLs:**
| Provider | Base URL |\n|----------|----------|\n| Groq | `https://api.groq.com/openai/v1` |\n| Cerebras | `https://api.cerebras.ai/v1` |\n| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` |\n| DeepSeek | `https://api.deepseek.com/v1` |\n| SambaNova | `https://api.sambanova.ai/v1` |\n| OpenCode | `https://opencode.ai/zen/v1` |\n| NVIDIA NIM | `https://integrate.api.nvidia.com/v1` |

**Steps:**
1. Add key to FreeLLMAPI via admin API
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

See `references/pitfalls.md` for extended troubleshooting.

## Current Setup (as of 2026-06-06)

| Service | Port | Manager | Models |
|---------|------|---------|--------|
| FreeLLMAPI | 3001 | systemd | 102 models (aggregated) |
| OpenCode Proxy | 19912 | PM2 | 45 models |
| 9Router | 20128 | systemd | Unified dashboard + combo fallback |
| NVIDIA NIM | — | cloud | Free-tier serverless (qwen3-coder-480b, deepseek-v4-flash, kimi-k2.6) |
| Hermes Gateway | — | systemd | 6+ providers (MiMo, NVIDIA, OpenRouter, FreeLLMAPI, OpenCode, 9Router) |

**FreeLLMAPI Key**: `freellmapi-3f3ae86521eba8c49ec39d2380a632833b544bd927b3fde0`
**NVIDIA NIM Key**: `nvapi-...` (stored in Hermes config)
**9Router API Key**: `9r-...` (stored in `.env` as `NINEROUTER_API_KEY`)
**9Router Dashboard**: via Cloudflare tunnel (URL in tunnel log)
**Admin**: admin@freellmapi.local / admin123

**Note**: User cannot check API key balances from Hermes session. Direct them to provider dashboards.

## Blocking Pattern — Move On Quickly

When blocked (missing creds, IP block, expired keys) and user told twice: **stop asking, offer alternative, move on**. User frustration signals ("oke tinggalkan", "lupakan") = drop immediately. Do NOT repeat the blocker.