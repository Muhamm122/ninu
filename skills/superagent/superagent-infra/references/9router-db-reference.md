# 9Router SQLite DB — Quick Reference

**DB Path:** `/home/ubuntu/.9router/db/data.sqlite`

## All Tables

```
_meta, apiKeys, combos, kv, providerConnections, providerNodes,
proxyPools, requestDetails, settings, usageDaily, usageHistory
```

## Key Tables

### providerNodes
```
id (TEXT PK), type (TEXT), name (TEXT), data (JSON), createdAt, updatedAt
```

### providerConnections
```
id (TEXT PK), provider (TEXT FK), authType (TEXT), name (TEXT),
priority (INTEGER), isActive (INTEGER), data (JSON), createdAt, updatedAt
```

### settings
```
id (INTEGER PK CHECK (id = 1), data (TEXT NOT NULL))
```
Single-row table. `data` is JSON, e.g. `{"password": "$2b$10$..."}`.
**CRITICAL**: Columns are `id` + `data`, NOT `key`/`value`.

### _meta
```
schemaVersion (TEXT), appVersion (TEXT)
```

### apiKeys
```
id (TEXT PK), key (TEXT), name (TEXT), email (TEXT),
isActive (INTEGER), createdAt (TEXT), updatedAt (TEXT)
```

## Node.js Queries (better-sqlite3)

### List with provider info
```js
const nodes = db.prepare('SELECT id, name, type, data FROM providerNodes').all();
const nodeMap = {};
nodes.forEach(n => { nodeMap[n.id] = { name: n.name, type: n.type }; });
const conns = db.prepare('SELECT * FROM providerConnections ORDER BY createdAt DESC').all();
const result = conns.map(c => {
  let d = {};
  try { d = JSON.parse(c.data); } catch {}
  const masked = d.apiKey ? d.apiKey.substring(0, 8) + '...' + d.apiKey.substring(d.apiKey.length - 4) : null;
  return { ...c, providerName: nodeMap[c.provider]?.name, maskedKey: masked, hasKey: !!d.apiKey };
});
```

### Add connection
```js
import { randomUUID } from 'crypto';
const id = randomUUID();
const now = new Date().toISOString();
db.prepare(`INSERT INTO providerConnections (id, provider, authType, name, priority, isActive, data, createdAt, updatedAt)
  VALUES (?, ?, 'api-key', ?, ?, 1, ?, ?, ?)`).run(id, providerId, name, priority, JSON.stringify({ apiKey }), now, now);
```

### Toggle / Delete
```js
db.prepare('UPDATE providerConnections SET isActive = ?, updatedAt = ? WHERE id = ?').run(isActive ? 1 : 0, new Date().toISOString(), id);
db.prepare('DELETE FROM providerConnections WHERE id = ?').run(id);
```

### Reset password (auth mode: password)
```python
import bcrypt, sqlite3
new_hash = bcrypt.hashpw(b'NEW_PASSWORD', bcrypt.gensalt(rounds=10)).decode()
db = sqlite3.connect('/home/ubuntu/.9router/db/data.sqlite')
db.execute("UPDATE settings SET data=? WHERE id=1", [json.dumps({"password": new_hash})])
db.commit()
```

## Auth Notes
- Default auth: `password` mode (bcrypt hash in `settings.data`)
- If `settings.data.password` is null/missing, fallback = `process.env.INITIAL_PASSWORD || "123456"`
- Rate limiting: 5 failed attempts → lockout (30s→2min→10min→30min escalation)
- OIDC mode also available if configured
- Auth status endpoint: `GET /api/auth/status`
- Auth mode stored in `settings.data.authMode` ("password" | "oidc" | "both")

### settings (auth password)
```
id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL
-- Single row: data = {"password": "$2b$10$...bcrypt_hash..."}
-- Reset password: UPDATE settings SET data='{"password": "$2b$10$NEW_HASH"}' WHERE id=1
-- Default when empty: process.env.INITIAL_PASSWORD || "123456"
```

### _meta
```
schemaVersion INTEGER, appVersion TEXT
```

### Other tables
```
apiKeys, combos, kv, proxyPools, requestDetails, usageDaily, usageHistory
```

## Rules
1. Never expose full API keys — mask: `abcd1234...xyz9`
2. Validate provider exists before adding connection
3. Use `isActive` to disable without deleting
4. Lower priority number = tried first
5. Use `randomUUID()` for new IDs (built-in, no package needed)
6. Password reset: generate bcrypt hash, UPDATE settings table (id=1, data={"password":"$2b$10$..."})
7. Auth check endpoint: `GET /api/auth/status` → `{"requireLogin":true,"authMode":"password","hasPassword":true}`
6. `settings` table uses `id=1` + `data` JSON, NOT `key`/`value` columns
