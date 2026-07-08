# Provider Health Session — 2026-06-25

## Summary

ALL external providers were dead simultaneously. Only FreeLLMAPI (local proxy) worked.
User complained "model lu tolol bgt" — primary provider was set to EvoMap but its key was invalid, causing silent fallback to FreeLLMAPI with potentially wrong model.

## Provider Status Dump

```
Provider       Endpoint                           Status    Details
───────        ────────                            ──────    ───────
EvoMap         api.evomap.ai/v1                   🔴 401    "invalid token" — key format valid but expired
OpenModel      api.openmodel.ai/v1                 🔴 401    invalid_api_key — needs dashboard activation
MiMo SG        token-plan-sgp.xiaomimimo.com/v1    🔴 401    All 5 keys returned Invalid API Key
MiMo CN        token-plan-cn.xiaomimimo.com/v1     🔴 401    Same issue
Kimchi/CastAI  llm.kimchi.dev/openai/v1            🔴 402    Provider exhausted credits
OpenRouter     openrouter.ai/api/v1                 🔴 401    sk-or key invalid
NVIDIA NIM     integrate.api.nvidia.com/v1          🔴 410    qwen3-coder-480b EOL 2026-06-11
Zyloo          api.zyloo.io/v1                     🔴 500    Overloaded
Aero Link      capi.aerolink.lat                   🔴 401    Invalid token
FreeLLMAPI     http://127.0.0.1:3001/v1            🟢 200    106 free models available
```

## Root Cause Chain

1. EvoMap key was set as primary but returned "invalid token" (expired)
2. Hermes fallback chain kicked in silently — tried MiMo (401), OpenRouter (401), etc.
3. Eventually fell through to FreeLLMAPI which worked
4. But user was on session started with EvoMap as primary — model mismatch
5. User got model quality that was worse than expected → frustration

## Fix Applied

1. Tested all providers systematically via Python urllib
2. Confirmed only FreeLLMAPI worked
3. Updated config.yaml:
   - `model.default_model` → `freellmapi/deepseek-v4-flash-free`
   - `model.model` → matched the model name
   - `model.provider` → `freellmapi`
   - `fallback_providers` → `["freellmapi", "mimo", "mimo2", "mimo3"]`
4. Verified with direct curl test against FreeLLMAPI

## Prevention

- Run provider health audit monthly
- Test ALL configured providers at once (not just the primary)
- Keep FreeLLMAPI as first fallback since it's local and stable
- When user complains about model quality, check provider health FIRST