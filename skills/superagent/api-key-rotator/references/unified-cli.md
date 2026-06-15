# Unified CLI Design — `apikeys` Front-End

**Pattern**: One ergonomic CLI wrapping the JSON pool + YAML config + helper scripts. The operator-facing front-end is `apikeys`; the programmatic verb-based API is `api_key_rotator.py`.

## File Layout

```
~/bin/
├── apikeys                  # symlink/copy of apikeys_cli.py (executable)
├── rotate                   # auto-detect + rotate + hot-reload (existing)
├── switch-model             # per-key model switching (existing)
└── clipvault                # clipboard-hijacker control script

~/.hermes/
├── api-key-pool.json        # pool: strategies, keys, current_index
├── config.yaml              # hermes provider/model/base_url/api_key
├── scripts/
│   ├── api_key_rotator.py   # programmatic: add/remove/get/fail/success/reset/strategy
│   ├── auto_rotate.sh       # rotate by specific key + hot-reload
│   └── rotate_now.sh        # auto-detect current + rotate + hot-reload
```

## The Three Layers

| Layer | Tool | Used by | Style |
|-------|------|---------|-------|
| Interactive | `apikeys` | operator in chat | color, table, ergonomic |
| Scripted | `api_key_rotator.py <verb>` | automation, cron, hooks | JSON out, verb in |
| Hot-reload | `auto_rotate.sh` / `rotate_now.sh` | after a rotation | bash, calls `hermes config reload` |

All three read/write the same `~/.hermes/api-key-pool.json` so they don't conflict.

## `apikeys` Command Surface (canonical)

```bash
apikeys                    # default: list all (alias for `apikeys list`)
apikeys list               # all keys + status table
apikeys current            # show active key (model, URL, masked key, uses, last_used)
apikeys status             # pool summary (total, active, inactive, current idx)
apikeys stats              # usage bars per key (visual)

apikeys test <id>          # test a single key (HTTP probe, ~2s)
apikeys test-all           # test all keys, report working/failed counts

apikeys rotate             # rotate to next active key
apikeys switch <id>        # jump to specific key (updates current_index)
apikeys enable <id>        # mark key as active
apikeys disable <id>       # mark key as inactive

apikeys add                # interactive add new
apikeys remove <id>        # remove key from pool

apikeys models [id]        # list available models for a key (or all)
apikeys help               # full help
```

## Pool File Schema (canonical)

```json
{
  "pools": {
    "primary": {
      "strategy": "round_robin",
      "current_index": 0,
      "keys": [
        {
          "id": "mimo-3",
          "key": "tp-...",
          "base_url": "https://token-plan-sgp.xiaomimimo.com/v1",
          "provider": "mimo-3",
          "active_model": "mimo-v2.5-pro",
          "model": "mimo-v2.5-pro",
          "models": ["mimo-v2.5-pro"],
          "status": "active",
          "usage_count": 0,
          "last_used": null,
          "last_used_ts": 0
        }
      ]
    }
  }
}
```

### Required Fields per Key

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | unique within pool, kebab-case preferred |
| `key` | yes | full key value (chmod 600 on file) |
| `base_url` | yes | provider OpenAI-compatible base URL |
| `provider` | yes | matches `providers.<name>` in `config.yaml` |
| `model` | yes | default model for this key |
| `active_model` | recommended | currently selected model (when `models` list present) |
| `models` | optional | list of available models (for `apikeys models`) |
| `status` | yes | `active` / `inactive` / `rate_limited` / `exhausted` / `invalid` |
| `usage_count` | auto | incremented on each use |
| `last_used` | auto | ISO timestamp |
| `last_used_ts` | auto | unix timestamp (for cooldown calc) |

## When to Use Which Layer

| Scenario | Tool |
|----------|------|
| Operator wants to "see what's available" | `apikeys list` |
| Operator wants to test keys after a known outage | `apikeys test-all` then `apikeys disable <dead>` |
| Operator wants to switch to a specific provider | `apikeys switch mimo-3` |
| Cron / hook auto-rotates on error | `api_key_rotator.py fail primary <id> <error_type>` |
| Cron needs to test keys periodically | `apikeys test-all` (read stdout) |
| Need to hot-reload Hermes after config change | `hermes config reload` (called by rotate scripts) |

## Key Patterns from Production (verified 2026-06-14)

### Pattern 1: `apikeys test-all` → identify dead → `apikeys disable` → re-test

```bash
$ apikeys test-all
🧪 Testing 8 keys

  Testing aero-1...    ❌ HTTP 305
  Testing mimo-3...    ✅ 1913ms
  Testing kimchi-1...  ❌ HTTP 403 ?
  Testing kimchi-2...  ❌ HTTP 403 ?
  Testing kimchi-3...  ❌ HTTP 403 ?
  Testing kimchi-4...  ❌ HTTP 403 ?
  Testing mimo-4...    ❌ HTTP 429 limitation
  Testing mimo-5...    ✅ 2080ms

  ✅ 2 working  |  ❌ 6 failed  |  Total: 8

$ for k in kimchi-1 kimchi-2 kimchi-3 kimchi-4; do apikeys disable $k; done
🔴 Disabled: kimchi-1
🔴 Disabled: kimchi-2
🔴 Disabled: kimchi-3
🔴 Disabled: kimchi-4
```

### Pattern 2: Status classification (don't auto-recover 402 exhausted)

| HTTP | Meaning | Action |
|------|---------|--------|
| 200 | healthy | leave as `active` |
| 401 | key dead/expired | `apikeys disable` (won't recover) |
| 402 | provider exhausted | `apikeys disable` (waits for upstream refill) |
| 403 | IP-blocked OR schema error | retry after cooldown; check UA header |
| 405 | wrong method | investigate (rare) |
| 429 | rate-limited | auto-recover after 60s; don't disable |
| 503 | server down | retry after cooldown; don't disable |

**`apikeys test-all` does not change status automatically** — it only reports. The operator decides what to disable. This matches the operator preference: "test, then disable if confirmed dead."

### Pattern 3: Switching back to working key after current is dead

```bash
$ apikeys current
⭐ Current Active: aero-1
$ apikeys test aero-1
  Testing aero-1... ❌ HTTP 305

$ apikeys switch mimo-3
✅ Switched to mimo-3 (index 1)
```

### Pattern 4: Hot-reload after every key change

The `apikeys` CLI calls `hermes config reload` automatically after `switch`, `rotate`, `enable`, `disable` — this triggers a hot-reload of the model config without restarting the gateway. For manual changes to `api-key-pool.json` (e.g., scripted edits), run `hermes config reload` separately.

## MiMo Endpoint Variants (new findings 2026-06-14)

| Region | Base URL | Provider IDs | Notes |
|--------|----------|--------------|-------|
| SG (Singapore) | `https://token-plan-sgp.xiaomimimo.com/v1` | mimo, mimo2, mimo3 | original |
| CN (China) | `https://token-plan-cn.xiaomimimo.com/v1` | mimo4, mimo5 | new endpoint, same `mimo-v2.5-pro` model, same `tp-...` key format |

**Critical**: The CN endpoint is a separate base URL → needs its own provider entry in `config.yaml`. Cannot just add new keys to `mimo3` provider, must create `mimo4`, `mimo5` with the CN URL.

**Provider naming**: Use kebab-case (`mimo-4`, NOT `mimo4`) to keep config naming consistent and avoid the `hermes config set` numeric-suffix block.

## CastAI Kimchi — 403 vs 402 Disambiguation

`apikeys test` returns 403 from direct IP, but the underlying cause matters:

| Symptom | True cause | Action |
|---------|-----------|--------|
| 403 "error code: 1010" from VPS IP | Cloudflare IP block | retry from Tor → may work |
| 402 "provider exhausted credits" via Tor | CastAI upstream empty | disable, wait for refill |
| 401 "Invalid API Key" | key dead/expired | disable permanently |
| 429 | rate limit | back off |

**Workflow for ambiguous Kimchi failures**:
```bash
apikeys test kimchi-1                   # if 403
torsocks curl ... /chat/completions     # if 402, provider exhausted → disable
                                       # if still 403, IP block → keep in pool, retry later
```

The Tor test distinguishes "we are blocked" (keep keys) from "provider has no money" (disable keys).
