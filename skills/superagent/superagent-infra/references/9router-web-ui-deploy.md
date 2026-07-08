# 9Router Web UI — Standalone Deployment

## Overview
9router ships with a Next.js standalone web UI (dashboard) that can run independently from the CLI tray app. The UI provides provider management, connection CRUD, usage stats, and request history.

## Architecture
- **Framework**: Next.js 16 (standalone output mode)
- **Auth**: NextAuth v5 / Auth.js — password mode (bcrypt) or OIDC
- **DB**: SQLite at `~/.9router/db/data.sqlite`
- **Default port**: 3000 (env `PORT` overrides)
- **Install path**: `~/.hermes/node/lib/node_modules/.9router-QINSUkdo/app/`

## Start Command
```bash
cd ~/.hermes/node/lib/node_modules/.9router-QINSUkdo/app
node server.js
# Listens on http://0.0.0.0:3000
```

For systemd / PM2, use the full path to the hermes node binary:
```bash
# PM2
~/.hermes/node/bin/node ~/.hermes/node/lib/node_modules/.9router-QINSUkdo/app/server.js

# Systemd ExecStart
ExecStart=/home/ubuntu/.hermes/node/bin/node /home/ubuntu/.hermes/node/lib/node_modules/.9router-QINSUkdo/app/server.js
```

## Auth System

### Password Mode (default)
- `authMode: "password"` — stored in `settings` table (id=1, data={"password": "$2b$10..."})
- Login endpoint: `POST /api/auth/login` with `{"password": "..."}`
- **Default password**: `process.env.INITIAL_PASSWORD || "123456"` — only used when `settings.password` is null/undefined
- Rate limiting: 5 failed attempts → progressive lockout (30s → 2min → 10min → 30min)
- JWT: HS256 signed, 24h expiry, secret from `~/.9router/jwt-secret`

### Reset Password
```bash
# Generate new bcrypt hash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'NEW_PASSWORD', bcrypt.gensalt(10)).decode())"

# Update in DB
sqlite3 ~/.9router/db/data.sqlite "UPDATE settings SET data='{\"password\": \"\$2b\$10\$...\"}' WHERE id=1"
```

### OIDC Mode
- Configure via dashboard: Settings → Auth → OIDC
- Requires: issuer URL, client ID, client secret
- Endpoints: `/api/auth/oidc/start`, `/api/auth/oidc/callback`

### Auth Status API
```bash
curl http://localhost:3000/api/auth/status
# Returns: requireLogin, authMode, hasPassword, displayName, oidcConfigured
```

## Nginx Reverse Proxy

### Path-prefix deployment (e.g., `/9router/`)
```nginx
location /9router/ {
    proxy_pass http://127.0.0.1:3000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 90s;
    proxy_buffering off;
}
```

### Subdomain deployment (e.g., `9router.example.com`)
```nginx
server {
    listen 80;
    server_name 9router.example.com;
    location / {
        proxy_pass http://127.0.0.1:3000;
        # ... same proxy headers as above
    }
}
```

## Key Pitfalls

1. **Root path redirect strips prefix**: When deployed behind `/9router/` path prefix, Next.js redirect from `/` → `/dashboard` becomes `/9router/` → `/dashboard` (strips prefix). Users should access `/9router/login` or `/9router/dashboard` directly. A `basePath` config in Next.js would fix this but requires rebuild.

2. **npm global install quirk**: The real 9router install lives at `~/.hermes/node/lib/node_modules/.9router-QINSUkdo/` (not `~/.hermes/node/lib/node_modules/9router/` which may be an empty directory). Check and fix symlinks if `9router` command fails:
   ```bash
   rm -rf ~/.hermes/node/lib/node_modules/9router
   ln -s .9router-QINSUkdo ~/.hermes/node/lib/node_modules/9router
   ```

3. **better-sqlite3 native binary**: The Next.js app uses `better-sqlite3` which has a native `.node` binary. If Node.js version changes, the binary may need recompilation.

4. **Password is bcrypt, NOT plaintext**: The `settings.data` field stores `{"password": "$2b$10$..."}`. Never set plaintext — always use bcrypt hash. The login route compares via `bcrypt.compare()`.

5. **Auth cookie settings**: Cookie is `auth_token`, HttpOnly, SameSite=lax, 24h maxAge. Set `AUTH_COOKIE_SECURE=true` env var for HTTPS.

6. **9router CLI does NOT have password reset**: The CLI (`node cli.js`) only has server start options (port, host, tray, log). Password must be reset via direct DB update.

## DB Schema Quick Reference

```sql
-- Password hash
SELECT * FROM settings;  -- id=1, data={"password": "$2b$10$..."}

-- Provider nodes (API backends)
SELECT id, type, name, data FROM providerNodes;

-- Provider connections (API keys)
SELECT id, provider, name, priority, isActive, data FROM providerConnections;

-- Auth status (computed, not stored)
-- Check via /api/auth/status endpoint
```

## Domain Setup Checklist

1. Point DNS A record to VPS IP
2. Add `server_name` to nginx config
3. Start 9router web UI server (PM2 or systemd)
4. Configure nginx reverse proxy
5. SSL via certbot: `sudo certbot --nginx -d example.com`
6. Reset password in DB if needed
7. Test: `curl https://example.com/9router/api/auth/status`
