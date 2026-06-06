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
FALLBACK1: OpenRouter / owl-alpha — reliable, 346 models
FALLBACK2: FreeLLMAPI (freellmapi:3001) — FREE, 102 models
FALLBACK3: OpenCode Proxy (:19912) — FREE, 45 models
```

**Cost optimization**: Use MiMo for heavy reasoning tasks. Switch to FreeLLMAPI (`llama-3.3-70b` or `deepseek-v4-flash-free`) for lighter tasks to save quota.

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
| Provider | Base URL |
|----------|----------|
| Groq | `https://api.groq.com/openai/v1` |
| Cerebras | `https://api.cerebras.ai/v1` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` |
| DeepSeek | `https://api.deepseek.com/v1` |
| SambaNova | `https://api.sambanova.ai/v1` |
| OpenCode | `https://opencode.ai/zen/v1` |

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

See `references/pitfalls.md` for extended troubleshooting.

## Current Setup (as of 2026-06-06)

| Service | Port | Manager | Models |
|---------|------|---------|--------|
| FreeLLMAPI | 3001 | systemd | 102 models (aggregated) |
| OpenCode Proxy | 19912 | PM2 | 45 models |
| Hermes Gateway | - | systemd | 5 custom providers |

**FreeLLMAPI Key**: `freellmapi-3f3ae86521eba8c49ec39d2380a632833b544bd927b3fde0`
**Admin**: admin@freellmapi.local / admin123

**Note**: User cannot check API key balances from Hermes session. Direct them to provider dashboards.

## Blocking Pattern — Move On Quickly

When blocked (missing creds, IP block, expired keys) and user told twice: **stop asking, offer alternative, move on**. User frustration signals ("oke tinggalkan", "lupakan") = drop immediately. Do NOT repeat the blocker.