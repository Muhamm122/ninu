# 9Router Integration Reference

## Config Location
- Config dir: `~/.9router/`
- DB: `~/.9router/db/data.sqlite`
- Auth: `~/.9router/auth/`
- Logs: `~/.9router/logs/`

## Environment
- API key env var: `NINEROUTER_API_KEY`
- Default port: `20128`

## Running 9Router

```bash
# Background/headless mode (for systemd)
9router --tray --no-browser --skip-update --log

# Check status
curl -s http://localhost:20128/v1/models
```

## Systemd Service

```ini
[Unit]
Description=9Router LLM API Proxy
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/local/bin/9router --tray --no-browser --skip-update --log
Restart=always
RestartSec=5
Environment=NINEROUTER_API_KEY=9r-......
```

## Integration with Hermes

In `~/.hermes/config.yaml`:

```yaml
providers:
  9router:
    base_url: http://localhost:20128/v1
    default_model: freellmapi/qwen3-coder-480b
    key_env: NINEROUTER_API_KEY
    name: 9Router
```

## Cookie vs API Key (IMPORTANT)

Users may confuse browser cookies with API keys. Always clarify:

| | Cookies | API Key |
|---|---|---|
| **Format** | `__Secure-next-auth.session-token=eyJ...` | `sk-...` |
| **Source** | Browser dev tools | Provider dashboard (platform.openai.com) |
| **Expires** | Session-based, days-weeks | Permanent until revoked |
| **Use case** | Web login only | API authentication |
| **Security** | Session hijack risk | Credential theft risk |

**When user shares cookies as "API key":**
1. Explain cookies ≠ API keys
2. Guide user to get real API key from provider dashboard
3. NEVER use cookies as API keys — it's unreliable and against ToS
4. GPT Plus subscription does NOT include API key — need separate credits purchase

## Gotchas

- Interactive TUI auto-exits on headless VPS — always use `--tray` flag
- `systray2` dep may be missing on headless — install with `npm install systray2@2.1.4`
- Models list empty until providers configured
- User may confuse browser cookies with API key — cookies are NOT API keys. API keys are `sk-...` format from provider dashboard.
