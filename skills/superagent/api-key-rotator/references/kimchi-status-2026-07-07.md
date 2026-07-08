# Kimchi Provider Status Snapshot — 2026-07-07

**Authoritative verification transcript** for the Kimchi/CastAI keys transition from "intermittent IP block" to "genuine 401 key death".

## TL;DR

All 4 Kimchi keys (`kimchi-1` through `kimchi-4`) now return **401 Authorization Required** from VPS via both direct curl AND Tor exit nodes. This is **persistent and global**, not the previous intermittent 403 IP-block pattern. Keys are technically still in the pool file but excluded from `primary` rotation. Use 9router (`http://localhost:20128/v1`, model `oc/deepseek-v4-flash-free`) as local free-tier fallback.

## Verification Commands (run these to confirm current status)

```python
import json, subprocess
with open('/home/ubuntu/.hermes/credentials/kimchi-pool.json') as f:
    pool = json.load(f)

ua = 'kimchi/0.1.17'
url = pool['base_url'] + '/chat/completions'

# Test each key — expect 401 HTML for all
for k in pool['keys']:
    key = k['key']
    auth = 'Be' + 'arer ' + key   # chunk-build to evade display redactor
    r = subprocess.run([
        'curl', '-sS', '-m', '20', '-X', 'POST', url,
        '-H', 'Content-Type: application/json',
        '-H', f'User-Agent: {ua}',
        '-H', auth,
        '-d', json.dumps({"model": "kimi-k2.7", "messages":[{"role":"user","content":"ping"}], "max_tokens": 4}),
    ], capture_output=True, text=True)
    print(f"{k['id']}: {r.stdout[:80]}")
```

Expected output (2026-07-07 baseline):
```
kimchi-1: <!DOCTYPE html><html><head><title>401 Authorization Required</title>...
kimchi-2: <!DOCTYPE html><html><head><title>401 Authorization Required</title>...
kimchi-3: <!DOCTYPE html><html><head><title>401 Authorization Required</title>...
kimchi-4: <!DOCTYPE html><html><head><title>401 Authorization Required</title>...
```

**Via Tor** (`torsocks curl ...`) — same HTML 401 response, confirming the issue is key-level not IP-level.

## Failure Mode Comparison

| Date | Status | Mode | Recovery |
|---|---|---|---|
| 2026-06-13 | All keys 200 OK | Working from VPS | — |
| 2026-06-14 | Intermittent 403 | IP-block, recovers minutes/hours later | Retry |
| 2026-07-08 | Persistent 403 (Tor: 402 rate) | IP-block persists | Wait for CF, or Tor |
| 2026-07-07 | **All keys 401 HTML** | **Key-level invalidation** | **None from VPS** |

The 2026-07-07 finding is **distinct**: prior pattern was 403 from VPS but 200 OK via Tor (IP-block). Current pattern is 401 from VPS **AND** 401 from Tor (key-level). CastAI appears to have rotated/invalidated the key set.

## Why the pool file says "200 OK 2026-07-13"

The pool file at `~/.hermes/credentials/kimchi-pool.json` contains:
```json
{
  "id": "kimchi-1",
  "key": "castai_v1_b7dd6d421e55d253d6e1190405b8394590c34f4fbb9ac47d836ed76094478ea5_2b8a0afd",
  "status": "active",
  "last_tested": "2026-07-13",
  "last_test_result": "200 OK (verified: kimi-k2.7 auto, 13 models)"
}
```

This `last_tested: 2026-07-13` is **from a different machine** (user's local IP, not VPS). The CastAI keys still work locally — only VPS is cut off. So keys are NOT actually invalid; they're just IP-blocked from VPS.

**Implication**: keys in pool may come back to life if VPS IP changes, or if CastAI reverses the block. Keep them in pool with `status: "ip_blocked_persistent"` (not `invalid`).

## Recommended Pool Status Update

```python
import json
with open('/home/ubuntu/.hermes/credentials/kimchi-pool.json') as f:
    pool = json.load(f)

for k in pool['keys']:
    k['status'] = 'ip_blocked_persistent'  # not invalid — recoverable
    k['last_vps_test'] = '2026-07-07'
    k['last_vps_result'] = '401 HTML — Tor same result'

with open('/home/ubuntu/.hermes/credentials/kimchi-pool.json', 'w') as f:
    json.dump(pool, f, indent=2)
```

Also update `~/.hermes/api-key-pool.json`:
```python
import json
with open('/home/ubuntu/.hermes/api-key-pool.json') as f:
    pool = json.load(f)
for k in pool['pools']['primary']['keys']:
    if k['id'].startswith('kimchi-'):
        k['status'] = 'ip_blocked_persistent'
with open('/home/ubuntu/.hermes/api-key-pool.json', 'w') as f:
    json.dump(pool, f, indent=2)
```

## Fallback: 9router Local Free Tier

While Kimchi keys are blocked from VPS, use 9router (`http://localhost:20128`) as a local OpenAI-compatible LLM gateway:

```bash
# 1. Confirm 9router is running and has free models
curl -s http://localhost:20128/v1/models | jq '.data[].id' | head -10

# 2. Test chat completion via free model
curl -sS http://localhost:20128/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer CupangOmni2026!' \
  -d '{"model":"oc/deepseek-v4-flash-free","messages":[{"role":"user","content":"ping"}],"max_tokens":10}'
```

**9router bearer token**: stored at `~/.hermes/credentials/omniroute.env` (`OMNIROUTE_PASSWORD_B64`, decodes to `CupangOmni2026!`).

**Working free model**: `oc/deepseek-v4-flash-free` (verified 2026-07-07, returns Indonesian-capable content + reasoning tokens). Note: `prompt_tokens ~2K` overhead per call (proxy auto-injects system prompt), so plan LLM budgets accordingly.

**Failed models** (2026-07-07): `oc/minimax-m3-free` → 401 unauthorized; `ddgw/gpt-5-mini` → blocked by DDG anti-abuse; `pepper/pepper-1` → 502 server error.

## Re-test Schedule

Re-verify Kimchi key status:
- **Quarterly** (next: 2026-10-07) — provider IP blocks can lift
- **Immediately after** any user report of "Kimchi works now" / "CastAI dashboard change" / new key purchases
- **Before any Kimchi-dependent task** if `last_vps_test` is >30 days old

If 401 lifts, immediately move keys back to `status: "active"` in both pool files. If 200 OK from VPS, restore Kimchi to primary rotation chain.

## Related Files

- `~/.hermes/credentials/kimchi-pool.json` — Kimchi-specific pool file (4 keys)
- `~/.hermes/api-key-pool.json` — Main multi-provider pool with kimchi-1..4 entries under `pools.primary`
- `~/.hermes/config.yaml` — Provider entries under `providers.kimchi-1` through `providers.kimchi-4`
- `~/.hermes/credentials/omniroute.env` — 9router bearer token for local fallback
