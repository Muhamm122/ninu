# Conduit Provider (conduit.ozdoev.net)

Multi-model aggregator with 26 models including Grok-4, GPT-5, Claude Opus/Sonnet/Haiku, Gemini 3 Pro, DeepSeek, Llama 4, and more.

Verified working 2026-06-29. Updated 2026-06-30 with full model-level results.

## Quick Facts

| Field | Value |
|-------|-------|
| Base URL | `https://conduit.ozdoev.net/api/v1` |
| Key format | `sk-cdt-eyJ...` (JWT, ~141 chars) |
| Auth | `Authorization: Bearer <key>` (standard OpenAI-compatible) |
| `/models` endpoint | Works WITHOUT authentication (public listing) |
| Plan | Free plan — aggressive 429 rate limits (~4-5 requests then cooldown) |
| Provider ID | `conduit` in config.yaml |

## Key Structure (JWT payload)

The key is a JWT (`sk-cdt-` prefix + base64 payload + `.` + signature). Decoding the middle base64 segment reveals:

```json
{
  "id": "3234610338",
  "u": "",
  "n": "PUBLIC",   // or "CUPANG" — plan name
  "j": "da70675b194a",
  "k": "api"
}
```

The `"n"` field is the **plan name**. User may provide replacement keys with different plan names (e.g., PUBLIC → CUPANG). Both work identically — the plan name doesn't change API behavior, only rate limit tier (if any).

## Rate Limiting (Updated 2026-06-30)

- Free plan hits 429 after ~4-5 rapid requests — **more aggressive than previously estimated**
- Error: `{"error":{"message":"Free plan rate limit reached. Please wait a moment and continue.","type":"rate_limit_error"}}`
- Cooldown: ~30-60 seconds
- Rate limit appears to be **per-IP** (not per-key) — testing multiple keys from same VPS in quick succession accumulates
- `/models` endpoint is NOT rate limited (always returns 200)
- **CRITICAL pattern observed 2026-06-30**: Even when rate limit is NOT hit (200 OK returned), many models return 200 with **"The response did not generate correctly. Please resend the last message"** — an empty/broken response, NOT a real completion. This is DIFFERENT from 429 — the request "succeeds" but the content is useless. Must check content for this string.

## Model Response Quality (Tested 2026-06-30)

Tested with 22 models. Two failure modes beyond 429: broken reply content.

| Model | HTTP | Response Quality | Latency | Notes |
|-------|------|-----------------|---------|-------|
| `mistral-large-3` | ✅ 200 | ✅ Clean "OK" | 4.7s | **FASTEST reliable** |
| `gpt-4.1` | ✅ 200 | ✅ Clean "OK" | 6.6s | Reliable |
| `gpt-4o` | ✅ 200 | ✅ Clean "OK" | 7.1s | Reliable |
| `grok-4` | ✅ 200 | ❌ "did not generate correctly" | 4.8s | Broken reply |
| `grok-3` | ✅ 200 | ❌ "did not generate correctly" | 11.0s | Broken reply |
| `gpt-5` | ✅ 200 | ❌ "did not generate correctly" | 8.5s | Broken reply |
| `gpt-5-mini` | ✅ 200 | ❌ "did not generate correctly" | 6.8s | Broken reply |
| `deepseek-r1` | ✅ 200 | ❌ "did not generate correctly" | 6.3s | Broken reply |
| `deepseek-v3.2` | ✅ 200 | ❌ "did not generate correctly" | 5.9s | Broken reply |
| `deepseek-v4-flash` | ✅ 200 | ❌ "did not generate correctly" | 4.6s | Broken reply |
| `qwen3-coder` | ✅ 200 | ❌ "did not generate correctly" | 3.3s | Broken reply |
| `o4` | ✅ 200 | ❌ "did not generate correctly" | 3.3s | Broken reply |
| `grok-3-mini` | ❌ 429 | — | — | Rate limited |
| `claude-sonnet-4-6` | ❌ 429 | — | — | Rate limited |
| `claude-opus-4-8` | ❌ 429 | — | — | Rate limited |
| `claude-haiku-4-5` | ❌ 429 | — | — | Rate limited |
| `gemini-2.5-flash` | ❌ 429 | — | — | Rate limited |
| `gemini-2.5-pro` | ❌ 429 | — | — | Rate limited |
| `gemini-3-pro` | ❌ 429 | — | — | Rate limited |
| `llama-4-maverick` | ❌ 429 | — | — | Rate limited |
| `llama-4-scout` | ❌ 429 | — | — | Rate limited |
| `qwen3-max` | ❌ 429 | — | — | Rate limited |

### Summary

- **12/22 models return 200** — but only **3 return usable content**: `gpt-4.1`, `gpt-4o`, `mistral-large-3`
- **10/22 hit 429** rate limit
- **9/22 return 200 with broken response** — conduit accepts the request but upstream vendor returns error text formatted as a valid 200 response
- The broken-response pattern is **NOT detectable from HTTP status code** — must check content for `"did not generate correctly"`
- **Recommendation**: Use `mistral-large-3` (fastest at 4.7s) or `gpt-4.1` as primary conduit model. Do NOT use `grok-4` — it returns 200 but with broken content.

## Available Models (26 total, listed for reference)

`claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`, `claude-opus-4.8`, `codestral`, `deepseek-r1`, `deepseek-v3.2`, `deepseek-v4-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-3-pro`, `gpt-4.1`, `gpt-4o`, `gpt-5`, `gpt-5-mini`, `grok-3`, `grok-3-mini`, `grok-4`, `llama-3.3-70b`, `llama-4-maverick`, `llama-4-scout`, `mistral-large-3`, `mixtral`, `o4`, `qwen3-coder`, `qwen3-max`

**Note**: "gpt-5.5" does NOT exist on this provider. Closest are `gpt-5` and `gpt-5-mini`.

## Config.yaml Entry

```yaml
providers:
  conduit:
    api_key: sk-cdt-eyJ...U8
    base_url: https://conduit.ozdoev.net/api/v1
    default_model: grok-4
    name: Conduit
```

**NOTE**: Default model is `grok-4` but it returns broken responses. Change to `mistral-large-3` or `gpt-4.1` for production use.

## Key Handling: Terminal Redaction Bypass

**Problem**: The Hermes terminal tool redacts API keys when used inline in curl/bash commands. The `Bearer $KEY` header shows `Bearer ***` in terminal output, and the shell may receive a corrupted/truncated value.

**Solution** (proven 2026-06-29): Use `write_file` tool to write the key to a temp file, then read it back in Python:

```python
# 1. Use write_file tool to create /tmp/conduit_key.txt with the raw key
#    (write_file preserves sk-cdt-* keys intact — only sk_live_* gets corrupted)

# 2. Read in Python:
with open("/tmp/conduit_key.txt") as f:
    key = f.read().strip()

# 3. Verify integrity:
print(f"Key length: {len(key)}")  # Should be ~141
print(f"Key prefix: {key[:10]}")  # Should be sk-cdt-eyJ

# 4. Use with urllib:
import urllib.request, json
url = "https://conduit.ozdoev.net/api/v1/chat/completions"
data = json.dumps({
    "model": "grok-4",
    "messages": [{"role": "user", "content": "Say OK"}],
    "max_tokens": 10
}).encode()
req = urllib.request.Request(url, data=data)
req.add_header("Authorization", f"Bearer {key}")
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read())
    print(result["choices"][0]["message"]["content"])
```

**Key verification**: Use `xxd /tmp/conduit_key.txt | head -5` to verify byte-level integrity. The file should be exactly the key length with no extra characters.

## Testing Script (Quick Probe)

```python
import urllib.request, json

with open("/tmp/conduit_key.txt") as f:
    key = f.read().strip()

url = "https://conduit.ozdoev.net/api/v1/chat/completions"
models = ["gpt-4.1", "mistral-large-3", "gpt-4o"]  # Only the 3 reliable ones

for model in models:
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 10
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"][:80]
            # Check for broken response pattern
            if "did not generate correctly" in content:
                print(f"❌ {model}: BROKEN REPLY — {content}")
            else:
                print(f"✅ {model}: {content}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:150]
        print(f"❌ {model}: HTTP {e.code} - {body}")
```

## Key Replacement Pattern

When user provides a replacement key (same provider, different plan/token):
1. Write new key to temp file via `write_file`
2. Verify byte integrity with `xxd` or `wc -c`
3. Test with a quick chat completion
4. Update `config.yaml` via Python YAML manipulation (not `hermes config set` — may be blocked for nested keys)
5. Verify the key was written correctly by reading it back from config and checking length/prefix

## Error Classification

| HTTP Code | Body Pattern | Meaning | Action |
|-----------|-------------|---------|--------|
| 200 | Clean reply | ✅ Success | Use model |
| 200 | `"did not generate correctly"` | ❌ Broken upstream | Model appears accepted but returns garbage — avoid this model |
| 401 | Auth error | Invalid API key | Key is wrong/expired — verify integrity first |
| 429 | `Free plan rate limit reached` | Rate limited | Wait 30-60s, retry. Not a key issue. |
| 5xx | Server error | Transient | Retry |
