# OhMyCaptcha v3 Setup & Troubleshooting

**Updated**: 2026-07-25 — Added proxy integration, start.sh pattern, MiMo key expiry note.

## Quick Commands

```bash
systemctl status ohmycaptcha.service
curl http://localhost:8765/api/v1/health
journalctl -u ohmycaptcha.service -n 50 --no-pager
```

## Installation

```bash
cd /tmp
git clone https://github.com/shenhao-stu/ohmycaptcha.git
cd ohmycaptcha
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Systemd + start.sh Setup

Create `/tmp/ohmycaptcha/start.sh`:

```bash
#!/bin/bash
# OhMyCaptcha start.sh — extracts MiMo credentials from Hermes config at runtime
# Allows key rotation without touching systemd

export CLIENT_KEY="cupang_ohmycaptcha_2026"
export HOST="0.0.0.0"
export PORT="8765"
export PYTHONUNBUFFERED=1
export PLAYWRIGHT_BROWSERS_PATH="/root/.cache/ms-playwright"

# Load MiMo API key from Hermes config.yaml (runtime, not hardcoded)
CONFIG="$HOME/.hermes/config.yaml"
if [ -f "$CONFIG" ]; then
    API_KEY=*** -c "
import yaml
with open('$CONFIG') as f:
    d = yaml.safe_load(f)
for provider, cfg in d.get('providers', {}).items():
    key = cfg.get('api_key', '')
    if key and 'mimo' in provider.lower():
        print(key)
        break
" 2>/dev/null)
    [ -n "$API_KEY" ] && export CLOUD_API_KEY=***    export CLOUD_BASE_URL="https://token-plan-sgp.xiaomimimo.com/v1"
    export CLOUD_MODEL="mimo-v2.5-pro"
fi

# Optional: route through residential proxy for browser-based solvers
# export HTTP_PROXY="http://user:pass@host:port"
# export HTTPS_PROXY="http://user:pass@host:port"

exec /tmp/ohmycaptcha/.venv/bin/python /tmp/ohmycaptcha/main.py
```

Create `/etc/systemd/system/ohmycaptcha.service`:

```ini
[Unit]
Description=OhMyCaptcha Self-Hosted Solver
After=network.target

[Service]
Type=simple
WorkingDirectory=/tmp/ohmycaptcha
ExecStart=/tmp/ohmycaptcha/start.sh
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
chmod +x /tmp/ohmycaptcha/start.sh
systemctl daemon-reload
systemctl enable --now ohmycaptcha.service
```

## Testing

```bash
# Health check
curl http://localhost:8765/api/v1/health

# Create a Turnstile task
curl -s -X POST http://localhost:8765/api/v1/createTask \
  -H "Content-Type: application/json" \
  -d '{"clientKey":"cupang_ohmycaptcha_2026","task":{"type":"TurnstileTaskProxyless","websiteURL":"https://example.com","siteKey":"0x4AAAAAAA..."}}'

# Get result
curl -s -X POST http://localhost:8765/api/v1/getTaskResult \
  -H "Content-Type: application/json" \
  -d '{"clientKey":"cupang_ohmycaptcha_2026","taskId":"TASK_ID"}'
```

## Known Issues

1. **MiMo keys expired** (all 401) — ImageToText tasks will fail. Browser solvers (Turnstile, reCAPTCHA, hCaptcha) work without cloud keys.
2. **Turnstile from datacenter IP** — Cloudflare blocks the challenge before Chromium can solve it. The solver retries 3x then times out. This is an IP reputation issue, not a solver bug.
3. **Memory usage** — ~345MB RSS idle, ~500MB during solving. On 2GB VPS, this is ok as long as no other memory-heavy process runs concurrently.
4. **Browser tasks without residential proxy** — If `HTTP_PROXY`/`HTTPS_PROXY` are not set in start.sh, browser-based solvers use the VPS datacenter IP directly, which gets blocked by strict Cloudflare/Google sites.

## When to Use

| Scenario | Best Tool |
|----------|-----------|
| reCAPTCHA/hCaptcha/Turnstile widget (non-datacenter IP or via proxy) | OhMyCaptcha — free, self-hosted |
| Cloudflare challenge page blocking access | Residential proxy — no solver helps |
| No local resources (RAM/CPU) | YesCaptcha/SCTG — cloud solvers |
| Image/text CAPTCHA with valid cloud API key | OhMyCaptcha ImageToTextTask |
| Datacenter IP with strict CF/Google | SCTG or YesCaptcha (may still fail) |