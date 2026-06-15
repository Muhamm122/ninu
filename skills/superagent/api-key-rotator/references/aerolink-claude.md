# Aerolink Claude API Integration

**Status (2026-06-15):** Active. Added to `~/.hermes/api-key-pool.json` primary pool, position 0 (`aero-1`).

## Endpoint

| Field | Value |
|-------|-------|
| Base URL | `https://capi.aerolink.lat/` |
| Models list | `GET https://capi.aerolink.lat/v1/models` |
| Chat endpoint | `POST https://capi.aerolink.lat/v1/messages` (Anthropic format) |
| OpenAI endpoint | `POST https://capi.aerolink.lat/v1/chat/completions` — **returns 305 redirect, not supported** |
| Key format | `aero_live_...` |
| Auth header | `x-api-key: <key>` (Anthropic style) — also accepts `Authorization: Bearer <key>` |

## Working Models (verified 2026-06-15)

| Model | Status | Notes |
|-------|--------|-------|
| `claude-haiku-4-5-20251001` | ✅ 200 OK | Fast, cheap (default choice) |
| `claude-sonnet-4-6` | ✅ 200 OK | Balanced |
| `claude-opus-4-7` | ✅ 200 OK | Smart, expensive |
| `claude-fable-5` | ❌ 400 | Listed in `/v1/models` but rejected at `/v1/messages` (unsupported) |
| `claude-opus-4-8` / `claude-opus-4-6` | untested | Likely works (same family as opus-4-7) |

## CRITICAL: Strict Anthropic Schema

Aerolink uses a strict Anthropic-compatible schema. It rejects:
- `extra_body.reasoning` (any value) → `400 "Extra inputs are not permitted"`
- `extra_body.provider` (OpenRouter-style)
- `extra_body.plugins`
- Other OpenRouter-specific extensions

The error format: `{"error":{"type":"<nil>","message":"reasoning: Extra inputs are not permitted (request id: ...)","type":"error"}}`

## Hermes `hermes chat` Integration — BROKEN by default

**Root cause:** Hermes agent auto-injects `extra_body.reasoning = {"enabled": True, "effort": "medium"}` for all Anthropic API calls (see `chat_completion_helpers.py:1343-1353` in `run_agent.py`). This is a hardcoded behavior to support OpenRouter's reasoning config; there is no flag to disable it per-provider.

**Symptoms:**
- Direct SDK call → 200 OK ✅
- `hermes chat` → 400 "Extra inputs are not permitted" ❌

**Workarounds:**

### Option A: Direct SDK wrapper (recommended, instant)
Bypass `hermes chat` for this provider. Use a small Python wrapper:

```python
import anthropic
c = anthropic.Anthropic(api_key="aero_live_...", base_url="https://capi.aerolink.lat")
r = c.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=4096,
    messages=[{"role":"user","content":"your prompt"}]
)
print(r.content[0].text)
```

A reusable script lives at `~/.hermes/scripts/aero_chat.py` (added 2026-06-15).

### Option B: Patch Hermes core
Not recommended (modifies bundled skill). If absolutely needed, patch `chat_completion_helpers.py:1343` to check for a per-provider disable flag. Hermes v0.16.0+ has a per-provider profile system that could host this flag, but no public config exposes it yet.

### Option C: Add a profile with `request_overrides` that strips the field
The `request_overrides` config option in Hermes strips/patches request fields per provider. Setting `request_overrides={"extra_body": {}}` may or may not be honored by the current implementation — untested as of 2026-06-15.

## Hermes `custom_providers` Config

```yaml
custom_providers:
  - name: aero
    base_url: https://capi.aerolink.lat
    api_key: aero_live_...
    model: claude-haiku-4-5-20251001
    api_mode: anthropic_messages   # MANDATORY — without this, OpenAI SDK appends /chat/completions → 305
```

The `api_mode: anthropic_messages` field is what triggers Anthropic SDK routing instead of OpenAI. Auto-detection in `runtime_provider.py:_detect_api_mode_for_url` does NOT match this URL (only matches `/anthropic` suffix or `api.kimi.com/coding`).

## Env Fallback (for built-in `anthropic` provider path)

```bash
# In ~/.hermes/.env
ANTHROPIC_API_KEY=aero_live_...
ANTHROPIC_BASE_URL=https://capi.aerolink.lat
```

This makes the built-in `anthropic` provider route to Aerolink, but **does not bypass the `extra_body.reasoning` injection** — same 400 error.

## Test Recipe

**Quick test (Python):**
```python
import anthropic, sys
KEY = "aero_live_..."  # from dashboard
c = anthropic.Anthropic(api_key=KEY, base_url="https://capi.aerolink.lat")
r = c.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=50,
    messages=[{"role":"user","content":"PONG"}]
)
print(r.content[0].text)  # "PING! 🏓\n..."
```

**Stream test:**
```python
with c.messages.stream(model="claude-haiku-4-5-20251001", max_tokens=50,
                       messages=[{"role":"user","content":"PONG"}]) as s:
    for chunk in s.text_stream:
        sys.stdout.write(chunk)
```

**List models:**
```python
# Aerolink has no /v1/models endpoint discovery for non-OAI APIs;
# use the static list above (haiku/sonnet/opus 4-5/4-6/4-7)
```

## Debugging: How to Confirm the `extra_body.reasoning` Blocker

When `hermes chat` fails with 400 and direct SDK works:

1. **Inspect the agent's request** by tailing `~/.hermes/logs/agent.log`. Look for `provider=custom base_url=https://capi.aerolink.lat model=...` and the `Streaming failed before delivery` line with the error.

2. **Test direct curl/SDK** with the EXACT body the agent sends (use `_supports_reasoning_extra_body` and `agent.reasoning_config` from `chat_completion_helpers.py:1343-1353`):
   ```python
   body = {"model": "...", "max_tokens": ..., "messages": [...], "reasoning": {"enabled": True, "effort": "medium"}}
   # → 400 "Extra inputs are not permitted"
   ```
   Confirms the field is the culprit.

3. **Test WITHOUT the field** — same body minus `reasoning`:
   ```python
   body = {"model": "...", "max_tokens": ..., "messages": [...]}
   # → 200 OK
   ```

4. **All other Anthropic-compatible fields** that might trigger 400:
   - `extra_body.provider` (OpenRouter-only)
   - `extra_body.plugins` (Pareto Code router)
   - `metadata.user_id` (sometimes rejected)
   - `stream_options.include_usage` (Anthropic doesn't use this)

## Use Cases for This Provider

- **Backup when Kimchi/CastAI is IP-blocked or out of credits** (Aerolink is on a different aggregator, different IP class)
- **Claude models specifically** (Sonnet/Opus/Haiku from Anthropic family)
- **High-volume tasks** that need Anthropic-format responses (Aerolink handles `messages.stream()` cleanly)

## Known Limitations

- No native OpenAI chat completions support (only Anthropic format)
- Strict schema — no OpenRouter-style extras
- Models list (`/v1/models`) is incomplete (some models listed don't work)
- Hermes `hermes chat` integration broken until upstream patch
- No vision/image inputs tested — may or may not work
- Rate limits undocumented — assume conservative
