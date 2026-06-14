# API Key Management — Patterns & Lessons (2026-06-13/14)

## Provider Error Code Reference

### CastAI/Kimchi (`https://llm.kimchi.dev/openai/v1`)
| HTTP | Error Code | Meaning | Action |
|------|-----------|---------|--------|
| 200 | — | Working | Use |
| 403 | 1010 | IP-based block | Keys are VALID. Keep in pool. Try from different IP. |
| 401 | — | Key invalid/dead | Remove from pool immediately |
| 402 | NO_CREDITS | **Upstream vendor pool empty** (not a key issue) | Wait for CastAI refill OR switch to OpenRouter/Ollama. Keys are valid, balance intact — CastAI's resold-vendor credits are exhausted. |
| 429 | — | Rate limit | Rotate to next key, retry later |

**Key insight:** 403 ≠ dead key. CastAI blocks VPS/data-center IPs. Same key may work from residential IP. Do NOT remove 403 keys — they're still valid.

**402 ≠ dead key either.** CastAI is a model aggregator — your balance is intact, but their upstream GPU vendors (the actual inference providers they resell) are out of credits. Confirmed via Tor bypass (CF block is intermittent and irrelevant). Don't waste time switching models or keys — all paths hit 402 until CastAI refills upstream. Real fixes: wait for CastAI refill, get a new OpenRouter key (337 models, OpenRouter's own vendor pool), or deploy Ollama locally. See `references/vps-setup-lessons.md` "CastAI Kimchi 402 NO_CREDITS" for full diagnosis.

### MiMo (`https://token-plan-sgp.xiaomimimo.com/v1`)
| HTTP | Meaning | Action |
|------|---------|--------|
| 200 | Working | Use |
| 401 | Key invalid | Remove from pool |
| 429 | Rate limit | Wait, retry later |

### OpenRouter (`https://openrouter.ai/api/v1`)
| HTTP | Meaning | Action |
|------|---------|--------|
| 200 | Working | Use |
| 401 "User not found" | Key expired/invalid | Get new key from openrouter.ai/keys |

## Pool Management Rules

1. **401 = REMOVE immediately** — key is dead
2. **403 = KEEP** — key is valid, IP is blocked
3. **429 = ROTATE** — rate limited, try next key
4. **Round robin** — rotate on error, cycle through all keys
5. **Model switching** — use `~/bin/switch-model <key_id> <model>` for per-key model changes

## Pool File Location
`~/.hermes/api-key-pool.json`

## Config File Location  
`~/.hermes/config.yaml` → `model.primary.*` and `providers.*`

## Key Format Reference
- **CastAI/Kimchi:** `castai_v1_<hash>_<suffix>` (83 chars)
- **MiMo:** `tp-<alphanumeric>` (40+ chars)
- **OpenRouter:** `sk-or-v1-<hash>` (60+ chars)

## Testing Keys
```python
import urllib.request, json

def test_key(url, key, model):
    req = urllib.request.Request(
        f'{url}/chat/completions',
        data=json.dumps({
            'model': model,
            'messages': [{'role': 'user', 'content': 'OK'}],
            'max_tokens': 3
        }).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return f'✅ HTTP {resp.status}'
    except urllib.error.HTTPError as e:
        return f'❌ HTTP {e.code}: {e.read().decode()[:100]}'
    except Exception as e:
        return f'⚠️ {e}'
```
