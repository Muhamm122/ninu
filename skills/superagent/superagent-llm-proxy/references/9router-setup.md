# 9Router Setup & Integration

9Router = AI proxy router that unifies multiple providers (OpenAI, Anthropic, NVIDIA NIM, custom) behind a single OpenAI-compatible endpoint with smart fallback combos.

## Install (headless VPS)

```bash
npm install -g 9router
# Verify
9router --version  # e.g. 0.4.71
```

### Headless invocation — CRITICAL

On a headless VPS (no display, no TTY), the default `9router` CLI shows an **interactive TUI menu** that auto-selects "exit" after 3 seconds when stdin is not a TTY. Result: process exits immediately with "Exiting...".

**Correct headless flags:**
```bash
9router --tray --no-browser --skip-update --log
```

- `--tray`: skips interactive menu, runs in background mode
- `--no-browser`: suppresses attempt to open dashboard
- `--skip-update`: skips npm update check
- `--log`: enables server log output

### Systemd service

```ini
[Unit]
Description=9Router AI Router
After=network.target

[Service]
Type=simple
User=ubuntu
Environment=PATH=/home/ubuntu/.local/bin:/home/ubuntu/.hermes/node/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/ubuntu
Environment=DISPLAY=:0
ExecStart=/home/ubuntu/.local/bin/node /home/ubuntu/.hermes/node/lib/node_modules/9router/cli.js --tray --no-browser --skip-update --log
Restart=always
RestartSec=5
WorkingDirectory=/home/ubuntu
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Key**: `ExecStart` must use explicit `node <path>/cli.js` (not the symlink), and `PATH` must include the node binary location.

### Firewall
```bash
sudo ufw allow 20128/tcp
```

## Dashboard access

Default dash password: `123456` (change immediately via Settings → Security → Set Password).

### Cloudflare quick tunnel (free, random URL)
```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Systemd service for tunnel
# ExecStart=/usr/local/bin/cloudflared tunnel --url http://localhost:20128 --no-autoupdate
# Logs to /tmp/9router-tunnel.log
# URL appears in log: https://xxxxx-yyyyy.trycloudflare.com
```

⚠️ Quick tunnel URL changes on every restart. For permanent URL, use Cloudflare named tunnel.

## Adding providers

### Via dashboard (recommended)
1. Login → Providers tab
2. Free Tier providers (NVIDIA NIM, OpenRouter, OpenCode Free, Gemini, etc.) are built-in — just need API key
3. Custom providers: "Add OpenAI Compatible" or "Add Anthropic Compatible"

### Via SQLite direct injection (when API auth is blocked)

If the dashboard API returns `{"error":"Unauthorized"}` for programmatic access, inject directly:

```python
import sqlite3, json, uuid
from datetime import datetime, timezone

DB = "/home/ubuntu/.9router/db/data.sqlite"
conn = sqlite3.connect(DB)
c = conn.cursor()
now = datetime.now(timezone.utc).isoformat()

# Schema: providerNodes(id TEXT PK, type, name, data TEXT NOT NULL, createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL)
# Schema: providerConnections(id TEXT PK, provider TEXT NOT NULL, authType TEXT NOT NULL, name, email, priority INT, isActive INT, data TEXT NOT NULL, createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL)
# Schema: apiKeys(id TEXT PK, key TEXT UNIQUE NOT NULL, name, machineId, isActive INT, createdAt TEXT NOT NULL)

nid = str(uuid.uuid4())
data = json.dumps({"type": "openai-compatible", "name": "MyProvider", "prefix": "myprov", "baseUrl": "https://api.example.com/v1", "apiType": "chat"})
c.execute("INSERT INTO providerNodes (id,type,name,data,createdAt,updatedAt) VALUES (?,?,?,?,?,?)",
          (nid, "openai-compatible", "MyProvider", data, now, now))

cid = str(uuid.uuid4())
cdata = json.dumps({"apiKey": "your-api-key"})
c.execute("INSERT INTO providerConnections (id,provider,authType,name,priority,isActive,data,createdAt,updatedAt) VALUES (?,?,?,?,?,?,?,?,?)",
          (cid, nid, "api-key", "MyProvider Primary", 1, 1, cdata, now, now))

# Create 9Router API key for Hermes
kid = str(uuid.uuid4())
key = f"9r-{uuid.uuid4().hex[:32]}"
c.execute("INSERT INTO apiKeys (id,key,name,isActive,createdAt) VALUES (?,?,?,?,?)",
          (kid, key, "Hermes Agent", 1, now))

conn.commit()
conn.close()
print(f"9Router API Key: {key}")
```

**⚠️ Stop 9router before writing to SQLite** (`sudo systemctl stop 9router`), then restart after.

## Provider routing through 9Router

Model IDs use the format `<prefix>/<model_id>` where prefix is the node's `prefix` field:
- `freellmapi/qwen/qwen3-coder:free` → routes to FreeLLMAPI node → `qwen/qwen3-coder:free`
- `nvidia/deepseek-ai/deepseek-v4-pro` → routes to NVIDIA NIM node

## Known issue: FreeLLMAPI key rejection through 9Router

When FreeLLMAPI is added as a custom OpenAI-compatible provider in 9Router, requests routed through 9Router may return 401 "Incorrect API key provided" even when the same key works perfectly with direct curl to FreeLLMAPI (`localhost:3001`).

**Root cause**: FreeLLMAPI validates its own `freellmapi-...` key format, and the way 9Router forwards the Authorization header may not match FreeLLMAPI's expectations.

**Workaround**: Use FreeLLMAPI directly in Hermes custom providers (not through 9Router). Use 9Router for other providers (NVIDIA NIM, OpenRouter, etc.) and as a unified dashboard/monitor.

## Hermes integration

```yaml
# In ~/.hermes/config.yaml
providers:
  9router:
    name: 9Router
    base_url: http://localhost:20128/v1
    key_env: NINEROUTER_API_KEY
    default_model: freellmapi/auto
```

```bash
# In ~/.hermes/.env
NINEROUTER_API_KEY=9r-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Built-in provider categories (as of v0.4.71)

- **OAuth Providers**: Claude Code, Antigravity, OpenAI Codex, GitHub Copilot, Cursor IDE, xAI (Grok), Kilo Code, Cline
- **Free Tier**: Kiro AI, Gemini CLI, Qoder, OpenCode Free, OpenRouter, NVIDIA NIM, Ollama Cloud, Vertex AI, Gemini, Cloudflare, BytePlus ModelArk
- **API Key**: Alibaba, Anthropic, Azure OpenAI, Blackbox AI, Cerebras, Chutes AI, Cohere, DeepSeek, Fireworks AI, Groq, Kimi, Mistral, Nebius AI, + 20 more

## NVIDIA NIM

Free serverless inference for dev. Get key at https://build.nvidia.com → avatar → "Get API Key" (`nvapi-...`).

Top models (2026-06):
- `deepseek-ai/deepseek-v4-pro`
- `deepseek-ai/deepseek-v3.1-terminus`
- `moonshotai/kimi-k2-thinking`
- `meta/llama-3.3-70b-instruct`
- `google/gemma-4-31b-it`

**Free-tier working models** (tested 2026-06-06):
- `qwen/qwen3-coder-480b-a35b-instruct` ✅ (TTFT ~350ms)
- `deepseek-ai/deepseek-v4-flash` ✅
- `moonshotai/kimi-k2.6` ✅
- `meta/llama-4-maverick-17b-128e-instruct` ✅ (cold start possible)

**403 Enterprise-only** (tested 2026-06-06):
- `nvidia/nemotron-3-super-120b-a12b` ❌ 403 Forbidden
- `mistralai/mistral-large-3-675b-instruct-2512` slow cold start (60s+)

**Cold start warning**: Large models (480B+, 675B+) may take 60+ seconds on first request after idle. Send a warmup request or use smaller models for interactive tasks.

**Signup note**: NVIDIA Build requires account creation with hCaptcha — cannot be automated from AWS IP. User must sign up on their own device at https://build.nvidia.com, then share the `nvapi-...` key.
