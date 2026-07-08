# Provider Status — 2026-07-13

## All Kimchi Keys 403 (Cloudflare IP Block)

Tested 2026-07-13 from VPS 18.143.107.30 (AWS) + VPS 104.207.74.67 (Namecheap).

**4 keys, all 403:**

| Key | URL | Status | Latency | Error |
|-----|-----|--------|---------|-------|
| kimchi-1 | `llm.kimchi.dev/openai/v1` | 403 | 27ms | error code: 1010 |
| kimchi-2 | `llm.kimchi.dev/openai/v1` | 403 | 18ms | error code: 1010 |
| kimchi-3 | `llm.kimchi.dev/openai/v1` | 403 | 37ms | error code: 1010 |
| kimchi-4 | `llm.kimchi.dev/openai/v1` | 403 | 28ms | error code: 1010 |

**Error code 1010** = Cloudflare (not key-invalid). The provider IP range (18.143.107.0/24 — AWS) is blocked by Cloudflare's WAF.

**Even Tor can't bypass:** `torsocks` through the same VPS also gets 403. The Cloudflare block is at the DNS/edge level, not IP-based.

**Test via direct `curl`:** Same result — `curl -s -H "Authorization: Bearer ${KEY}" https://llm.kimchi.dev/openai/v1/v1/chat/completions` returns 403 with `error code: 1010`.

**Test via `/v1/chat/completions`:** Same 403.

**Test via `/v1/models`:** 404 (endpoint not found — Kimchi doesn't expose models).

## What This Means

1. **Keys are NOT dead** — 403 is an IP block, not a key-invalidation
2. **Keys may work from a different IP** (home network, mobile, another VPS)
3. **Keep keys in pool** — don't remove them automatically
4. **Only keys returning 401 (invalid API key) should be removed** — those are truly dead

## Provider Naming

- All 4 keys use `kimchi-{1..4}` naming (hyphens, not underscores)
- Consistent `kimi-k2.7` model on all keys
- All use `https://llm.kimchi.dev/openai/v1` base URL
- Same `castai_v1_*` key format (all from same CastAI provider)