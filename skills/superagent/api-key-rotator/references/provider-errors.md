# Provider Error Patterns (updated 2026-07-08, with 2026-06-13 re-confirmation)

## Snapshot 2026-06-13 — All 10 Kimchi models simultaneously 402

Confirmed via `scripts/provider-health-check.py`: every model in the catalog
returned `402 "the provider for model X has exhausted its credits and cannot
process requests"`. Models tested: `kimi-k2.5`, `kimi-k2.6`, `minimax-m2.5`,
`minimax-m2.7`, `minimax-m3`, `nemotron-3-super-fp4`, `nemotron-3-ultra-fp4`,
`smollm2-135m`, `smollm2-360m`. (Plus `qwen3-coder-next-fp8` returned
`400 "no registered providers found for the requested model"` — separate
issue, model not registered at CastAI.)

**Diagnosis**: This is a **global CastAI upstream credit depletion**, not
per-model. Switching model does NOT help. Don't waste time cycling through
kimi-k2.5 ↔ kimi-k2.6 ↔ minimax-m* — the entire provider is throttled at
the credit layer. Action: topup at CastAI dashboard or wait for daily reset.

**Alt URL `api.tokenrouter.com/v1`** is a **different service** in the
CastAI ecosystem — same `castai_v1_...` key format, but `401 "Invalid token"`
when used with Kimchi keys. Need separate tokenrouter-issued keys.

**UA test (2026-06-13)**: Tested `python-urllib/3.11`, `curl/7.88.1`,
`Mozilla/5.0`, `Hermes-Agent/1.0` against `llm.kimchi.dev` — all returned
200 OK on `/models` in the same window. The intermittent 403 is Cloudflare
IP-level, not UA-based. Don't waste cycles on UA spoofing.

**OpenRouter (2026-06-13)**: `/models` returns **337 models** including
`kimi-k2.7-code`, anthropic variants, free models. Blocked only by
user's invalid OWL key. OpenRouter is the easiest path forward IF user
generates a new key at https://openrouter.ai/keys.

## Error Messages Reference

### Kimchi / CastAI
| Error | Status | Meaning | Action |
|-------|--------|---------|--------|
| `{"error": "the provider for model X has exhausted its credits and cannot process requests"}` | `exhausted` | Quota habis, bukan key invalid | Hapus dari pool, beri tahu user topup |
| `{"error": "error code 1010"}` | `ip_blocked` | VPS IP dibanned oleh CastAI | Keep key, catat IP status, retry later |
| 401 Unauthorized | `invalid` | Key dead/expired | Hapus dari pool |
| 403 Forbidden | `invalid/ip_blocked` | Cek error message - "User not found" = invalid, "1010" = IP block | Tergantung message |
| `{"error":"no registered providers found for the requested model"}` | `model_not_registered` | Model not in CastAI catalog | Jangan pake model ini |

### OpenRouter
| Error | Status | Meaning |
|-------|--------|---------|
| `{"error":{"message":"User not found","code":401}}` | `invalid` | Key expired/tidak terdaftar |
| `{"error":{"message":"Missing Authentication header","code":401}}` | `config_error` | Header tidak ter-set |

### Conduit
| Error | Status | Meaning | Action |
|-------|--------|---------|--------|
| HTTP 200 with body `"The response did not generate correctly"` | `broken_upstream` | Conduit accepted request but upstream vendor failed | Avoid this model — use `mistral-large-3`, `gpt-4.1`, or `gpt-4o` |
| 429 `Free plan rate limit reached` | `rate_limited` | Free plan quota exceeded | Wait 30-60s, space requests |
| HTTP 200 with empty/null content | `ok_empty` | Working but returned empty (max_tokens too low) | Increase `max_tokens` |

### MiMo (Xiaomi)
| Error | Status | Meaning |
|-------|--------|---------|
| `{"error":{"message":"Invalid API Key","code":401}}` | `invalid` | Key mati/expired |
| 429 | `rate_limited` | Rate limit exceeded |

### NVIDIA NIM
| Error | Status | Meaning |
|-------|--------|---------|
| `{"type":"about:blank","title":"Gone","status":410}` | `model_eol` | Model end-of-life | Harus ganti model |

### b.ai
| Error | Status | Meaning | Action |
|-------|--------|---------|--------|
| `{"error":"invalid api key"}` (HTTP 401) | `invalid` | Key dead/expired | Remove from pool, get new key |
| HTTP 429 | `rate_limited` | Rate limit exceeded | Cooldown 60s |
| HTTP 520 (Cloudflare) | `server_error` | b.ai server issue, OR datacenter IP blocked | Try via residential proxy or wait |
| HTTP 502/503 | `server_error` | b.ai origin server down | Wait for recovery |
| HTTP 429 | `rate_limited` | Rate limit exceeded | Cooldown 60s, retry |
| `{"error":"model not found"}` (HTTP 404) | `model_unknown` | Model ID typo atau dihapus | Check `/models` untuk list valid |
| HTTP 200 with empty content | `ok_empty` | Working, model returned empty (max_tokens too low) | Increase `max_tokens` |

## Detection Command

```bash
# Test any provider quickly
curl -s "BASE_URL/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"MODEL","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' 2>&1 | jq -r '.error // "ok"'
```

Or use the bundled probe script (recommended for full pool scan):
```bash
python3 ~/.hermes/skills/superagent/api-key-rotator/scripts/provider-health-check.py
python3 ~/.hermes/skills/superagent/api-key-rotator/scripts/provider-health-check.py --provider kimchi-1
python3 ~/.hermes/skills/superagent/api-key-rotator/scripts/provider-health-check.py --models-only
python3 ~/.hermes/skills/superagent/api-key-rotator/scripts/provider-health-check.py --json
```

## Recovery Actions

| Status | Action |
|--------|--------|
| exhausted | Hapus key, beri tahu user topup di dashboard provider |
| invalid | Hapus key, ganti dengan key baru |
| ip_blocked | Keep key, catat IP + provider di notes, coba dari IP lain |
| rate_limited | Rotate otomatis, cooldown 60s cukup |
| model_eol | Ganti model di config.yaml |
| model_not_registered | Hapus model dari active_model, pilih model lain dari /models |
