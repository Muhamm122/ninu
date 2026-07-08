# 9Router Standalone Web UI — Setup Reference

## Architecture

9router bundles a Next.js 16 app with standalone output mode. The app directory contains:
- `app/server.js` — Next.js standalone server (reads `PORT` env, default 3000)
- `app/.next-cli-build/` — Pre-built production bundle
- `app/.next-cli-build/server/app/api/auth/` — NextAuth v5 auth routes (login, logout, OIDC, status)
- `app/.next-cli-build/server/app/dashboard/` — Dashboard pages (overview, endpoint, usage, settings/pricing, cli-tools)

## DB Schema (SQLite at `~/.9router/db/data.sqlite`)

### Auth-related tables

```sql
-- Password hash stored here (single row, id=1)
CREATE TABLE settings (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
-- data format: {"password": "$2b$10$...bcrypt_hash..."}

-- API keys for 9router itself
CREATE TABLE apiKeys (id TEXT PRIMARY KEY, key TEXT NOT NULL, name TEXT, ...);

-- Provider nodes (LLM backends)
CREATE TABLE providerNodes (id TEXT PRIMARY KEY, type TEXT, name TEXT, data TEXT, createdAt TEXT, updatedAt TEXT);

-- Provider connections (API keys for each node)
CREATE TABLE providerConnections (id TEXT PRIMARY KEY, provider TEXT NOT NULL, authType TEXT NOT NULL, name TEXT, priority INTEGER, isActive INTEGER DEFAULT 1, data TEXT NOT NULL, createdAt TEXT, updatedAt TEXT);

-- Other tables: _meta, combos, kv, proxyPools, requestDetails, usageDaily, usageHistory
```

### Key/Meta

```sql
SELECT * FROM _meta;  -- schemaVersion, appVersion
SELECT * FROM kv;     -- empty on fresh install
SELECT * FROM settings;  -- {id: 1, data: {"password": "$2b$10$..."}}
```

## Auth Internals

### Password Login Flow

1. `POST /api/auth/login` with `{"password": "..."}`
2. Server reads `settings.data.password` (bcrypt hash)
3. If hash exists: compare via `bcrypt.compare(password, hash)`
4. If NO hash: compare against `process.env.INITIAL_PASSWORD || "123456"`
5. On success: set `auth_token` cookie (HS256 JWT, 24h expiry, httpOnly, sameSite=lax)
6. JWT secret: read from `~/.9router/jwt-secret` or auto-generate 32-byte hex

### Rate Limiting

- Per-IP tracking via `x-forwarded-for` or `x-real-ip` headers
- 5 failed attempts → lockout with exponential backoff: 30s, 2m, 10m, 30m
- Lockout resets after 1 hour of no failures

### OIDC Mode

When `authMode === "oidc"` and OIDC is configured (issuerUrl, clientId, clientSecret):
- `/api/auth/oidc/start` → redirects to OIDC provider
- `/api/auth/oidc/callback` → handles callback, sets JWT
- Password login returns 403: "Password login is disabled. Use OIDC sign in."

### Tunnel Access Control

If request comes from `tunnelUrl` or `tailscaleUrl` hostname and `tunnelDashboardAccess !== true`, dashboard access is denied (403).

## Web UI Start Command

```bash
# Background process
cd /path/to/.9router-QINSUkdo/app
PORT=3000 node server.js &

# Systemd service example
[Unit]
Description=9Router Web UI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/.9router-QINSUkdo/app
Environment=PORT=3000
ExecStart=/home/ubuntu/.local/bin/node /path/to/.9router-QINSUkdo/app/server.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Dewabiz DNS API Pattern

Dewabiz (domain registrar for .my.id domains) has an API at `my.dewabiz.com/api/v1/`:

```
# Auth via custom headers
X-API-Key: <32-char hex>
X-API-Secret: <32-char hex>

# Response from non-whitelisted IP:
result=error;message=Invalid IP 18.143.107.30
```

**Key findings:**
- API exists and responds (not a 404)
- IP whitelist is enforced server-side — only IPs registered in the dewabiz dashboard can call it
- Cannot bypass via Tor (415 Unsupported Media Type from openresty)
- Cannot bypass via datacenter proxy (InstantProxies also blocked)
- Login page has captcha + 2FA — no browser automation possible from VPS
- To update DNS: must use dashboard from a whitelisted IP (user's local browser)

## Domain DNS Propagation Notes

For `.my.id` domains using dewabiz nameservers:
- NS: `NS1-4.DEWABIZ.CO.ID` (IP: 103.147.154.76, .77, etc.)
- SOA serial format: `YYYYMMDDNN` (e.g., `2026062801`)
- TTL: 3600s (1 hour)
- A record changes may take 5-60 minutes to propagate through Google/Cloudflare resolvers
- Domain must NOT have `clientTransferProhibited` + `serverTransferProhibited` for 60 days after creation (per ICANN rules)
