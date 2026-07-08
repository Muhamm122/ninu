# LLM Provider Status (Verified 2026-06-30)

Comprehensive multi-provider test results. Testing methodology: POST /chat/completions with `max_tokens: 5` + `temperature: 0`, check for 200 + non-empty meaningful reply.

## Working Providers

| Provider | Base URL | Working Models | Latency | Notes |
|----------|----------|---------------|---------|-------|
| iamHC | https://api.iamhc.cn/v1 | Qwen3.5-397B-A17B, Qwen3.6-35B-A3B, glm-5.1 | 6-17s | Request with `verify=False` |
| iamHC | https://api.iamhc.cn/v1 | auto, step-router-v1 (200 OK but empty) | ~3s | Empty content — not usable |
| conduit | https://conduit.ozdoev.net/api/v1 | mistral-large-3, gpt-4.1, gpt-4o | 4.7-7.1s | Only 3 of 22 models work |

## Dead Providers

| Provider | Reason |
|----------|--------|
| Kimchi/CastAI (all 4 keys) | 402 "provider exhausted credits" — global CastAI upstream empty |
| OpenRouter | No key configured (key="" in config) |
| OWL (OpenRouter owl-alpha) | Key invalid (401 "User not found") |
| MiMo SG-9 | 401 Invalid API Key |
| Fastino | SSL cert verify failed |
| Aero | 200 but "Please use Claude Code CLI" — API blocked, CLI only |
| Kiro/OmniRoute | 530 Cloudflare block |
| conduit (grok-4, gpt-5, deepseek-*, etc.) | 200 OK but "did not generate correctly" — broken upstream |
| conduit (claude-*, gemini-*, llama-4-*, etc.) | 429 rate limit (free plan exhausted) |
| iamHC (Kimi-K2.6, gpt-4o, grok-3, etc.) | 200 OK but empty content OR 503 "No available channel" |

## Testing Methodology (two-phase)

### Phase 1: Auth Check (lightweight)
```python
req = requests.get(f"{base_url}/models", headers={"Authorization": f"Bearer {key}"})
# 200 OK = key valid, auth works
```

### Phase 2: Chat Completion (credit + routing check)
```python
resp = requests.post(f"{base_url}/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={"model": model, "messages": [{"role":"user","content":"OK"}], "max_tokens": 5},
    timeout=15, verify=False)
# Check: resp.status_code == 200 AND len(resp.json()["choices"][0]["message"]["content"].strip()) > 0
# AND "did not generate correctly" not in content
```

### Error Classification

| HTTP | Body Pattern | Meaning | Action |
|------|-------------|---------|--------|
| 200 | Non-empty clean reply | ✅ Live | Use |
| 200 | Empty/whitespace content | ⚠️ Broken routing | Don't use |
| 200 | "did not generate correctly" | ⚠️ Broken upstream | Don't use |
| 402 | "exhausted its credits" | Provider out of credits | Wait for refill |
| 401 | "Invalid API Key" / "User not found" | Key dead | Remove |
| 403 | "error code: 1010" | IP block | Keep, retry later |
| 410 | "Model X is no longer available" | Deprecated | Switch model |
| 503 | "No available channel for model" | Model unavailable | Try different model |
| SSL error | Handshake timeout | Infra issue | Use `verify=False` or retry |

## Provider-Specific Gotchas

### iamHC
- Use `requests` library with `verify=False` — `urllib` hits intermittent SSL handshake timeouts
- Only 3 models work: Qwen3.5-397B-A17B, Qwen3.6-35B-A3B, glm-5.1
- Kimi-K2.6 returns 200 but empty content (routing issue)

### Conduit
- Free plan: aggressive 429 after ~5 rapid requests
- Only 3 reliable models: mistral-large-3 (4.7s), gpt-4.1 (6.6s), gpt-4o (7.1s)
- grok-4 returns 200 but broken content — DO NOT USE

### Kimchi/CastAI
- All 4 keys return 402 (global credit exhaustion)
- `/models` returns 200 (auth works) but chat fails — two-phase test catches this
- Recovery: wait for CastAI to refill upstream vendor pool

### Aero
- Returns 200 with "Please use Claude Code CLI" — API blocked, only CLI works
- Not usable as OpenAI-compatible provider
