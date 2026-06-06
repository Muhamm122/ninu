# OpenCode.ai Free Proxy

Minimal reverse proxy to access opencode.ai free models without API key.

## Upstream
- URL: `https://opencode.ai/zen/v1`
- Auth: Header `x-opencode-client: desktop` (no API key needed)
- Models: 45 free models including Claude Opus/Sonnet, GPT, Gemini, DeepSeek

## Free Models
- `deepseek-v4-flash-free` — default
- `mimo-v2.5-free` — Xiaomi MiMo
- `minimax-m3-free` — MiniMax
- `nemotron-3-super-free` — NVIDIA

## Install Pattern

```bash
# Create proxy directory
mkdir -p ~/opencode-free-proxy
cd ~/opencode-free-proxy

# Write index.js (Express + CORS, proxies /v1/models and /v1/chat/completions)
# Set UPSTREAM=https://opencode.ai/zen/v1
# Set DEFAULT_MODELS to free model list
# Headers: x-opencode-client: desktop

# Install
npm init -y && npm install express cors

# Run with PM2
pm2 start index.js --name opencode-free-proxy
pm2 save
```

## Hermes Integration

```bash
hermes config set custom_providers '[..., {"name":"opencode_free","base_url":"http://127.0.0.1:19912/v1","api_key":"sk-dummy","model":"deepseek-v4-flash-free","api_mode":"chat_completions"}]'
```

## FreeLLMAPI Integration

Add as custom provider key (key is `sk-dummy` since proxy needs no auth):

```bash
curl -s -X POST http://127.0.0.1:3001/api/keys \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{"platform": "custom", "key": "sk-dummy", "label": "opencode-free-proxy", "baseUrl": "http://127.0.0.1:19912/v1"}'
```

## Port
- 19912 (localhost only)

## Troubleshooting
- `pm2 list` to check status
- `pm2 logs opencode-free-proxy` for logs
- Test: `curl -s http://127.0.0.1:19912/health`
