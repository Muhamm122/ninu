# Cavoti API Provider Notes

**Discovered**: 2026-06-30  
**Site**: https://cavoti.com  
**Type**: Chinese LLM API gateway / aggregator (大模型 API 中转站)  
**API Style**: OpenAI-compatible (`/v1/models`, `/v1/chat/completions`)

## Config

```yaml
providers:
  cavoti:
    api_key: sk-...
    base_url: https://api.cavoti.com/v1
    default_model: auto
    name: Cavoti
```

Add via Hermes CLI:

```bash
hermes config set providers.cavoti.api_key "sk-..."
hermes config set providers.cavoti.base_url "https://api.cavoti.com/v1"
hermes config set providers.cavoti.default_model "auto"
hermes config set providers.cavoti.name "Cavoti"
```

## Key Format

- Prefix: `sk-`
- Length observed: 64 hex chars after prefix
- Example: `sk-6de0217d2e46bef5ccf8b013c77479ee500f9a2a90e2ebf988f5b8e5b026be5c`

## Health Check

### Phase 1 — Auth / catalog

```bash
curl -s -H "Authorization: Bearer $CAVOTI_KEY" https://api.cavoti.com/v1/models
```

Expected responses:

| HTTP | Body | Meaning |
|------|------|---------|
| 200 | model list | ✅ Key valid, account recognized |
| 401 | `{"code":"INVALID_API_KEY"}` | ❌ Key dead / malformed |

### Phase 2 — Credit check

```bash
curl -s -X POST https://api.cavoti.com/v1/chat/completions \
  -H "Authorization: Bearer $CAVOTI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

Expected responses:

| HTTP | Body | Meaning |
|------|------|---------|
| 200 | `choices[0].message.content` | ✅ Live, has balance |
| 401 | `INVALID_API_KEY` | ❌ Key dead |
| 402 | `INSUFFICIENT_BALANCE` | ⚠️ Key valid but account has zero / depleted balance |

## Distinction: `INVALID_API_KEY` vs `INSUFFICIENT_BALANCE`

Cavoti returns different codes for auth vs balance:

- `INVALID_API_KEY` → key itself is bad. Remove from pool.
- `INSUFFICIENT_BALANCE` → key is accepted, account recognized, but no credits. **Keep the provider entry** — it becomes usable immediately after top-up without reconfiguring.

Do not confuse the two. If `/v1/models` returns a model list but `/chat/completions` returns `INSUFFICIENT_BALANCE`, the key is fine.

## Models

Cavoti advertises access to Claude, GPT, Gemini, DeepSeek, Grok, etc. Use `default_model: auto` unless a specific model is required. Probe `/v1/models` after adding the key to see the live catalog.

## Base URL Gotcha

Cavoti has TWO domains that behave differently:

| URL | Result |
|-----|--------|
| `https://api.cavoti.com/v1` | ✅ Correct endpoint. Recognizes valid keys. |
| `https://cavoti.com/v1` | ❌ Returns `INVALID_API_KEY` even for valid keys. |

Always use `https://api.cavoti.com/v1` as `base_url`. If you see `INVALID_API_KEY` for a key that should be valid, double-check the domain.

## Masked Keys

If the user pastes a key that looks like `sk-6de...be5c` (with `...` ellipsis), it is **masked/truncated**, not the real key. The API will either reject it or, in Cavoti's case, return `INSUFFICIENT_BALANCE` because the placeholder happens to pass format validation.

**Detection:**
- Length of a full Cavoti key is **67 characters** (`sk-` + 64 hex chars).
- A masked key is much shorter (e.g., 13 chars).
- Always ask the user for the full key if you see `...` in the middle.

## Verifying the Saved Key (Tool Redaction)

Hermes terminal and `write_file` tools may redact API keys in their display output (showing `***` or a masked string). The actual value on disk may still be correct, but you must verify — especially after a user correction.

Use Python to inspect the real stored key length without exposing it:

```python
import yaml
cfg = yaml.safe_load(open('/home/ubuntu/.hermes/config.yaml'))
k = cfg['providers']['cavoti']['api_key']
print('len:', len(k), 'prefix:', k[:7], 'suffix:', k[-6:])
```

Expected for Cavoti: `len: 67`. If the length is wrong, the key was corrupted by redaction and must be re-saved.

## Status (2026-06-30)

- Key added to `~/.hermes/config.yaml` as provider `cavoti`
- `/v1/models` ✅ 200 OK
- `/v1/chat/completions` ⚠️ `INSUFFICIENT_BALANCE`
- Not added to `fallback_providers` pending top-up
