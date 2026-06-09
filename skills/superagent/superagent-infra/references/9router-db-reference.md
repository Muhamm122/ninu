# 9Router SQLite DB — Quick Reference

**DB Path:** `/home/ubuntu/.9router/db/data.sqlite`

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

## Rules
1. Never expose full API keys — mask: `abcd1234...xyz9`
2. Validate provider exists before adding connection
3. Use `isActive` to disable without deleting
4. Lower priority number = tried first
5. Use `randomUUID()` for new IDs (built-in, no package needed)
