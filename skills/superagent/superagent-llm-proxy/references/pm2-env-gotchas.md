# PM2 Env Management — Critical Gotchas

## `pm2 set` Replaces ENTIRE Env

`pm2 set <app>:env '<json>'` replaces the **whole** process env with that single JSON object.
It does NOT merge. Any existing env vars (ENCRYPTION_KEY, NODE_ENV, etc) are **gone**.

```bash
# ❌ CATASTROPHIC — wipes everything
pm2 set freellmapi:env '{"PROXY_RATE_LIMIT_RPM":"0"}'
# Process env is now ONLY {"PROXY_RATE_LIMIT_RPM":"0"}
# ENCRYPTION_KEY gone → all encrypted API keys unrecoverable
```

## `pm2 start --env` Does NOT Work

The `--env` flag on `pm2 start` does NOT set env vars to the child process.

```bash
# ❌ WRONG — ENCRYPTION_KEY not in process env
pm2 start dist/index.js --name freellmapi --env '{"ENCRYPTION_KEY":"..."}'
```

## Correct Method: Ecosystem Config File

```javascript
// /opt/freellmapi/ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'freellmapi',
    script: 'dist/index.js',
    cwd: '/opt/freellmapi/server',
    env: {
      ENCRYPTION_KEY: 'your-64-char-hex-key',
      PROXY_RATE_LIMIT_RPM: '0',
      NODE_ENV: 'production',
    },
  }],
};
```

Verify: `cat /proc/<pid>/environ | tr '\0' '\n' | grep ENCRYPT`

## Recovery if ENCRYPTION_KEY Wiped

1. Check DB: `SELECT value FROM settings WHERE key = 'encryption_key'`
2. If old key persists in DB → restart via ecosystem file with that key → keys recoverable
3. If DB key also regenerated → old encrypted api_keys UNRECOVERABLE → re-insert all keys

## FreeLLMAPI IP Rate Limit

- Default: 120 req/min per IP (in-memory fixed window)
- `PROXY_RATE_LIMIT_RPM=0` disables entirely — MUST be set via ecosystem file (not `pm2 set`)
- 429 AFTER disabling IP rate limit = upstream provider (OpenRouter), not FreeLLMAPI

## Shell Glob Expansion with Secrets

- Bash expands `***` as glob in double-quoted strings
- Bearer tokens containing `***` get corrupted
- ALWAYS use Python `urllib.request` for API calls with secrets
- For curl: write payload to file first, use `@/tmp/payload.json`
