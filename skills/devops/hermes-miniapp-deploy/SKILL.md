---
name: hermes-miniapp-deploy
description: Deploy Hermes Mini App template — React+Vite frontend, Express backend, nginx proxy, Telegram menu button
tags: [telegram, miniapp, deploy, react, vite, nginx, cloudflare]
---

# Hermes Mini App Deployment

Deploy the `hermes-miniapp-template` from GitHub to VPS with nginx reverse proxy and Telegram Bot integration.

## Prerequisites
- Node.js 20+
- PM2 (`npm i -g pm2`)
- nginx installed and running
- (Optional) cloudflared for HTTPS tunnel

## Steps

### 1. Clone & Install
```bash
cd /home/ubuntu && git clone https://github.com/waguriagentic/hermes-miniapp-template.git hermes-miniapp
cd hermes-miniapp && npm install
cd server && npm install && cd ..
```

### 2. Customize
- `src/config.ts` — set `APP_NAME`, `APP_VERSION`, `DEFAULT_API_BASE`
- `src/App.tsx` — define tabs (primaryTabs / secondaryTabs)
- `src/pages/` — add page components
- `server/index.js` — add API endpoints
- `src/App.css` — styling (CSS variables for dark/light theme)

### 3. Build
```bash
cd /home/ubuntu/hermes-miniapp && npx vite build
# NOTE: `npm run build` runs `tsc -b && vite build` — tsc can timeout. Use `npx vite build` directly.
```

### 4. PM2 Start
```bash
pm2 start server/index.js --name "hermes-miniapp" --env PORT=9122
pm2 save
```

### 5. Nginx Reverse Proxy
Add location block to existing server config:
```nginx
location /miniapp/ {
    limit_req zone=general burst=20 nodelay;
    proxy_pass http://127.0.0.1:9122/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
}
```
Then: `sudo nginx -t && sudo systemctl reload nginx`

### 6. Telegram Menu Button
Telegram Mini App requires HTTPS. Use cloudflared quick tunnel:
```bash
cloudflared tunnel --url http://localhost:9122 --no-autoupdate
```
Then set menu button via Bot API:
```python
import urllib.request, json
token = "BOT_TOKEN_HERE"
tunnel_url = "https://xxx.trycloudflare.com"
url = f"https://api.telegram.org/bot{token}/setChatMenuButton"
data = json.dumps({
    "menu_button": {"type": "web_app", "text": "🚀 App", "web_app": {"url": tunnel_url}}
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=15)
```

## 9Router DB Integration

The miniapp can manage 9Router API keys directly. DB path: `/home/ubuntu/.9router/db/data.sqlite`

### Key Tables
- `providerNodes` — AI provider definitions (id, name, type, data JSON)
- `providerConnections` — API key connections (id, provider FK, authType, name, priority, isActive, data JSON)

### API Endpoints (add to server/index.js)
- `GET /api/9router/keys` — List all keys with provider info, masked
- `POST /api/9router/keys` — Add key to existing provider
- `POST /api/9router/providers` — Add new provider node + first key
- `PATCH /api/9router/keys/:id/toggle` — Toggle active/inactive
- `DELETE /api/9router/keys/:id` — Delete key
- `POST /api/9router/keys/:id/test` — Test key (sends actual API request)
- `GET /api/9router/nodes` — List provider nodes

### DB Helper
```js
import sqlite3 from 'better-sqlite3';
const DB_PATH = '/home/ubuntu/.9router/db/data.sqlite';
function getDB() { return sqlite3(DB_PATH); }
```

### Masking Keys
Always mask API keys in responses: `key.substring(0, 8) + '...' + key.substring(key.length - 4)`

## Cloudflare Tunnel Watchdog

Quick tunnel URL changes on restart. Setup auto-update:

### 1. PM2 for cloudflared
```bash
pm2 start "cloudflared tunnel --url http://localhost:9122 --no-autoupdate" --name "cloudflared"
pm2 save
```

### 2. Watchdog script (`~/.hermes/scripts/miniapp_watchdog.py`)
- Reads tunnel URL from PM2 logs
- Compares with saved URL (`~/.hermes/miniapp_tunnel_url.txt`)
- If changed, calls `setChatMenuButton` via Bot API

### 3. Cron job (every 5 min)
Set via Hermes cron: script=`miniapp_watchdog.py`, no_agent=true

## Pitfalls
- `tsc -b` hangs/slow — skip it, use `npx vite build` directly
- `patch()` on config.yaml blocked — use `hermes config set` instead
- Telegram requires HTTPS for Mini App — HTTP URLs rejected
- Quick tunnel URL changes on restart — use watchdog script + cron
- `better-sqlite3` needs native build — install with `npm install` in server/
- API base URL: use relative path (e.g. `/miniapp`) for nginx, empty string for direct access
- Auto-detect API base in `lib/api.ts` based on `window.location.pathname`
- `import { randomUUID } from 'crypto'` for generating new DB IDs
- SQLite: `prepare().run()` for INSERT/UPDATE, `prepare().get()` for SELECT one, `prepare().all()` for SELECT many
- Shell glob `***` corrupts tokens — use Python urllib, not curl inline
- **API keys in config.yaml get redacted by shell** — store keys in separate file (e.g. `~/.hermes/.or_key`), read with `$(cat file)` or Python `open()`. Never paste full keys inline in commands or config files that get logged.
- **9Router model routing**: 9Router uses provider prefixes (e.g. `openrouter/`, `freellmapi/`) to route models. If model not found, check provider node exists AND has active connection with valid API key. Model format: `prefix/model-name`.
- **OpenRouter direct vs via 9Router**: 9Router may misroute some providers. For OpenRouter, can bypass 9Router and call directly — set `model.base_url` and `model.api_key` in Hermes config.
- **execute_code blocked for cron** — cron jobs can't use `execute_code`. Use `terminal()` or script-based approach instead.
- **Vite build timeout**: foreground `vite build` may timeout. Use `background=true` with `notify_on_complete=true`, then `process(action='wait')`.
- **nginx `handle_path` vs `location`**: `handle_path /app/*` strips `/app` prefix. Use `location /miniapp/` with `proxy_pass http://127.0.0.1:9122/;` (trailing slash important).
- **Telegram Bot API `setChatMenuButton`**: requires `chat_id` param for per-user setting. Without it, sets default for all users.

## Verify
```bash
curl -s http://localhost:9122/api/health           # Backend
curl -s http://localhost/miniapp/api/health         # Via nginx
curl -s -o /dev/null -w "%{http_code}" http://localhost/miniapp/  # Frontend
```
