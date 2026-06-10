---
name: api-key-rotator
description: Multi-provider API key rotation for Hermes. Manages a pool of keys across providers (MiMo, OpenRouter, Kimchi, NVIDIA, custom) with round_robin, least_used, or random strategies. Rotate-on-error only — no continuous monitoring. Supports hot-reload of Hermes config without gateway restart.
---

# API Key Rotator v2

Multi-provider API key rotation. Rotate keys when errors occur — no continuous monitoring.

## Architecture

```
~/.hermes/
├── api-key-pool.json          # Pool file (chmod 600)
├── scripts/
│   ├── api_key_rotator.py    # Pool management (add/remove/get/list/fail/reset/strategy)
│   ├── auto_rotate.sh        # Rotate specific key by ID + hot-reload Hermes
│   └── rotate_now.sh         # Auto-detect current key + rotate + hot-reload
└── config.yaml               # Hermes config (auto-updated on rotation)
```

## Pool File Format

`~/.hermes/api-key-pool.json`:

```json
{
  "pools": {
    "primary": {
      "strategy": "round_robin",
      "current_index": 0,
      "keys": [
        {
          "id": "mimo-1",
          "key": "tp-...",
          "base_url": "https://token-plan-sgp.xiaomimimo.com/v1",
          "provider": "mimo",
          "model": "mimo-v2.5-pro",
          "usage_count": 0,
          "last_used": null,
          "last_used_ts": 0,
          "status": "active"
        }
      ]
    }
  }
}
```

### Key Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✅ | Unique identifier within pool |
| `key` | ✅ | API key value |
| `base_url` | ✅ | Provider base URL |
| `provider` | ✅ | Provider name (mimo, openrouter, kimchi, nvidia, custom) |
| `model` | ✅ | Model ID for this key |
| `status` | ✅ | active, rate_limited, exhausted, invalid |
| `usage_count` | Auto | Incremented on each use |
| `last_used` | Auto | ISO timestamp |
| `last_used_ts` | Auto | Unix timestamp (for cooldown calc) |

### Key Status

| Status | Meaning | Auto-recover |
|--------|---------|--------------|
| `active` | Healthy, can be used | — |
| `rate_limited` | Hit 429, cooldown 60s | ✅ After 60s |
| `exhausted` | Quota depleted / 402 | ❌ Manual reset |
| `invalid` | 401/403, key is dead | ❌ Manual reset |

## Rotation Strategies

| Strategy | Behavior |
|----------|----------|
| `round_robin` | Cycle through active keys in order, wrap around (default) |
| `least_used` | Always pick key with lowest `usage_count` |
| `random` | Pick random active key |

## Workflows

### Rotate on Error (Primary Workflow)

**When user reports error** (rate limit, auth fail, etc.):

```bash
# Auto-detect current key + rotate
bash ~/.hermes/scripts/rotate_now.sh [error_type]
```

Error types: `rate_limit` (default), `exhausted`, `invalid`

The script:
1. Detects current key from pool (current_index - 1)
2. Marks key as failed
3. Picks next active key
4. Updates `~/.hermes/config.yaml` (provider, model, base_url, api_key)
5. Hermes hot-reloads on next request (no gateway restart needed)

### Manual Pool Management

```bash
# Initialize pool from existing config
python3 ~/.hermes/scripts/api_key_rotator.py init

# Quick setup: 2 MiMo + 1 OpenRouter
python3 ~/.hermes/scripts/api_key_rotator.py setup-mimo-or

# Get next key (prints JSON)
python3 ~/.hermes/scripts/api_key_rotator.py get primary

# Report failure
python3 ~/.hermes/scripts/api_key_rotator.py fail primary <key_id> <error_type>

# Report success
python3 ~/.hermes/scripts/api_key_rotator.py success primary <key_id>

# List all keys
python3 ~/.hermes/scripts/api_key_rotator.py list

# Add key
python3 ~/.hermes/scripts/api_key_rotator.py add primary <id> <key> <base_url> <provider> [model]

# Remove key
python3 ~/.hermes/scripts/api_key_rotator.py remove primary <id>

# Reset key status
python3 ~/.hermes/scripts/api_key_rotator.py reset primary <id>

# Change strategy
python3 ~/.hermes/scripts/api_key_rotator.py strategy primary <round_robin|least_used|random>
```

### Rotate Specific Key by ID

```bash
bash ~/.hermes/scripts/auto_rotate.sh primary <key_id> <error_type>
```

## Provider Config Reference

### MiMo (Xiaomi)

```bash
base_url: https://token-plan-sgp.xiaomimimo.com/v1
model: mimo-v2.5-pro
key_format: tp-...
```

### OpenRouter

```bash
base_url: https://openrouter.ai/api/v1
model: openrouter/owl-alpha
key_format: sk-or-...
```

### Kimchi

```bash
base_url: https://llm.kimchi.dev/openai/v1
model: kimi-k2.6 (or kimi-k2.5, minimax-m2.7, nemotron-3-super-fp4)
key_format: castai_v1_...
auth: Authorization: Bearer <key>
```

### NVIDIA

```bash
base_url: https://integrate.api.nvidia.com/v1
model: qwen/qwen3-coder-480b-a35b-instruct
key_format: nvapi-...
```

## Quick Command

Hermes quick command `rotate` is configured:

```yaml
quick_commands:
  rotate:
    type: exec
    command: bash ~/.hermes/scripts/rotate_now.sh
```

User can type "rotate" or "ganti key" in chat → agent triggers rotation.

## Integration with Hermes

### Hot-Reload Behavior

Editing `config.yaml` triggers hot-reload for:
- `model.primary.*` (provider, model, base_url, api_key)
- `compression.*`
- `display.*`

**No gateway restart needed** for model/key changes.

### Gateway Restart

Gateway restart from inside the agent **always fails** (self-restart prevention).
User must restart from VPS shell:
```bash
hermes gateway restart
```

## Security

- Pool file: `~/.hermes/api-key-pool.json` with `chmod 600`
- Never log full key values — only show first 8 + last 4 chars
- Keys stored in plaintext — ensure file permissions are tight
- `auto_rotate.sh` and `rotate_now.sh` should be `chmod +x` (700)

## Provider Reference

See `references/providers.md` for provider-specific details:
- Kimchi: base URL `https://llm.kimchi.dev/openai/v1`, model `kimi-k2.6`, key format `castai_v1_...`
- MiMo: base URL `https://token-plan-sgp.xiaomimimo.com/v1`, NOT `api.mimo.ai`
- OpenRouter: `https://openrouter.ai/api/v1`
- NVIDIA: `https://integrate.api.nvidia.com/v1`

## Provider Quirks

### Kimchi
- Keys MUST be activated on dashboard before use (401 if not)
- May block/rate-limit data center IPs (403 from VPS)
- Dashboard is JS SPA — headless browser can't render
- CLI setup uses RTK TUI — can't be piped. Write `~/.config/kimchi/config.json` directly
- Install script repo: `castai/kimchi` (NOT `getkimchi/kimchi`)

### MiMo
- Base URL: `https://token-plan-sgp.xiaomimimo.com/v1` (NOT `api.mimo.ai` — DNS fails)
- Two providers (`mimo`, `mimo2`) — add both keys to same pool

### Shell Quoting
- Keys with underscores/slashes cause `unexpected EOF` in curl. Use `-d @/tmp/payload.json` or Python urllib.

## Pitfalls

1. **Don't continuous-monitor** — rotate only on error
2. **Rate limit cooldown** — 60s auto-recovery. Don't manually reset before
3. **Deduplicate keys** — same key twice wastes slots
4. **Provider mismatch** — rotating updates ALL config fields per entry
5. **Gateway restart** — from inside agent ALWAYS fails. User restarts from VPS shell
6. **skill_manage write_file** may fail in background review mode — use terminal + write_file tool

## Reference Files

See `references/providers.md` for detailed provider-specific documentation.
7. **Provider mismatch** — when rotating, the script updates ALL of provider/model/base_url/api_key in config.yaml. Ensure each pool entry has correct provider-specific values.
