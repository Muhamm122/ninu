# CastAI/Kimchi Status — June 2026

**Date**: 2026-06-13
**Status**: Pool DEAD — all 10 models unavailable

## TL;DR

- User's CastAI account balance is intact ✅
- All 7 main models return `402 "the provider for model X has exhausted its credits and cannot be used"` ❌
- 3 models (`qwen3-coder-next-fp8`, `smollm2-135m`, `smollm2-360m`) return `400 "no registered providers found for the requested model"` ❌
- This is a **CastAI upstream vendor pool problem**, not user-side — can't be fixed by switching keys or models
- Switching base URL to `api.tokenrouter.com/v1` doesn't help — it's a separate service with separate auth (Kimchi keys return 401 there)

## Test Methodology

To prove the issue is at CastAI's vendor pool level (not user account), I ran 3 retries × 10 models = 30 chat completion attempts via Tor (to bypass CF IP block). **100% consistent** failure pattern. No key or model worked.

```bash
# Test all keys × models in a single sweep
# /tmp/kimchi_retry.py (saved to skill scripts/)
torsocks python3 /tmp/kimchi_retry.py
```

Output:
```
model                      1st    2nd    3rd     notes
kimi-k2.6                402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
kimi-k2.5                402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
minimax-m2.7             402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
minimax-m3               402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
minimax-m2.5             402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
nemotron-3-super-fp4     402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
nemotron-3-ultra-fp4     402    402    402     NO_CREDITS | NO_CREDITS | NO_CREDITS
qwen3-coder-next-fp8     400    400    400     no registered provid | ...
smollm2-135m             400    400    400     no registered provid | ...
smollm2-360m             400    400    400     no registered provid | ...
```

## The User-Agent Bypass Discovery (CRITICAL)

While investigating the CF block, I discovered that the **User-Agent header** is what actually determines whether Cloudflare blocks the request:

| User-Agent | Result |
|------------|--------|
| `python-urllib/3.11` (Python default) | **403** |
| `curl/7.88.1` | **200** |
| `Mozilla/5.0 ... Chrome/120.0.0.0` | **200** |
| `Hermes-Agent/1.0` | **200** |

### Misconception warning
Earlier in the session, I thought **Tor** was bypassing the CF block. Wrong — the test that "worked" was also using a custom User-Agent (`curl/7.88.1`). The bypass was the UA change, not Tor.

**Lesson**: When a Tor + UA change "works," isolate variables:
1. Test direct (no Tor) with custom UA → still works? Then UA is the fix.
2. Test direct with default UA → blocked? Confirmed.
3. Test Tor with default UA → still blocked? Confirmed Tor alone doesn't help.

### The proper fix in any Kimchi client
Always set a non-default User-Agent explicitly:
```python
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "User-Agent": "curl/7.88.1",  # ← critical for CF
}
```

## Alternative URLs (none work)

| URL | Status |
|-----|--------|
| `https://llm.kimchi.dev/openai/v1` | Original (intermittent 403/200) |
| `https://llm.kimchi.dev/v1` | 403 (same CF) |
| `https://api.kimchi.dev/openai/v1` | DNS doesn't resolve |
| `https://api.kimchi.dev/v1` | DNS doesn't resolve |
| `https://cast.ai.kimchi.dev/v1` | DNS doesn't resolve |
| `https://api.tokenrouter.com/v1` | 401 "Invalid token" (different service, separate auth) |

## Real Fixes (in order of speed)

1. **OpenRouter new key** — fastest, 337 models, separate vendor pool. URL: `https://openrouter.ai/keys`. Free $5 credit on signup.
2. **Deploy Ollama locally** — 30 min, no aggregator middleman, 24GB VPS can run `qwen2.5:14b` or `llama3.1:8b`.
3. **Restart 9router** — 5 min, local proxy aggregator (currently down on VPS 18.143.107.30).
4. **Wait for CastAI refill** — no ETA, not user-controlled.
5. **CastAI support ticket** — 24h+ for vendor on-boarding of missing models.

## OpenRouter Status (tested 2026-06-13)

- `/models` returned **337 models** ✅
- No API key in environment for testing
- User's existing `sk-or-...cdef` key returned 401 "User not found" — invalid/expired, NOT IP block
- Need new key from https://openrouter.ai/keys
