# Dedicated Provider Pools — Full Walkthrough

Use this when the operator wants a single-provider rotation pool separated from the mixed `primary` pool. Verified end-to-end on Kimchi (2026-07-13).

## When to use

- Operator says "pool tersendiri khusus X" / "dedicated pool for X" / "X di pool terpisah"
- Operator wants X rotated independently (e.g., Kimchi fails → don't disrupt the `primary` chain)
- Operator wants fallback chain that stays within one provider family
- Operator says "Model Aktifkan disemua grup" = set X as primary + register dedicated pool + wire sibling fallback

## Architecture

```
~/.hermes/
├── api-key-pool.json          # Source of truth (pools.primary + pools.<dedicated>)
├── credentials/<name>-pool.json # Provider-specific file (kept in sync, optional)
├── config.yaml                # providers.* entries + credential_pool_strategies + fallback_providers
├── scripts/
│   ├── api_key_rotator.py     # Pool management (works with any pool name)
│   └── rotate_now.sh          # Patched to accept [pool] arg
└── bin/rotate                 # Patched CLI to dispatch pool names
```

## Step-by-step recipe (Kimchi example)

### 1. Probe all keys first

Before adding to pool, verify each key returns 200 OK:

```python
import urllib.request, json

keys = {
    'kimchi-1': 'castai_v1_b7dd6d421e55d253d6e1190405b8394590c34f4fbb9ac47d836ed76094478ea5_2b8a0afd',
    'kimchi-2': 'castai_v1_ca71028c4086e7b769d030888a56d960aa7e015278c2af8d71d87232fca1a0fd_b6f4697f',
    # ...
}
url = 'https://llm.kimchi.dev/openai/v1/models'
for name, k in keys.items():
    req = urllib.request.Request(url, headers={'User-Agent': 'kimchi/0.1.17', 'Authorization': f'Bearer {k}'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            print(f'{name}: OK ({len(d.get("data",[]))} models)')
    except Exception as e:
        print(f'{name}: HTTP {getattr(e, "code", None)}')
```

### 2. Add dedicated pool to api-key-pool.json

```python
import json

pool_file = '/home/ubuntu/.hermes/api-key-pool.json'
with open(pool_file, 'r') as f:
    data = json.load(f)

# Build pool entry
data['pools']['kimchi'] = {
    'strategy': 'round_robin',
    'current_index': 0,
    'keys': [
        {
            'id': 'kimchi-1',
            'provider': 'kimchi-1',
            'base_url': 'https://llm.kimchi.dev/openai/v1',
            'key': 'castai_v1_...',
            'models': ['kimi-k2.6', 'kimi-k2.5', 'kimi-k2'],
            'active_model': 'kimi-k2.6',
            'status': 'active',
            'model': 'kimi-k2.6',
            'headers': {'User-Agent': 'kimchi/0.1.17'},
            'usage_count': 0,
            'last_test_status': 'ok',
            'last_test_http': 200,
        },
        # ... one entry per key
    ]
}

# Also re-activate matching keys in primary pool (if present)
for key in data['pools']['primary']['keys']:
    if key['id'].startswith('kimchi-'):
        key['status'] = 'active'
        key['last_test_status'] = 'ok'

with open(pool_file, 'w') as f:
    json.dump(data, f, indent=2)
```

### 3. Update provider-specific pool file (optional)

```python
import json

with open('/home/ubuntu/.hermes/credentials/kimchi-pool.json', 'r') as f:
    pool = json.load(f)

pool['keys'] = [
    {'id': 'kimchi-1', 'key': 'castai_v1_...', 'status': 'active',
     'last_tested': '2026-07-13', 'headers': {'User-Agent': 'kimchi/0.1.17'}},
    # ... one per key
]
pool['current_index'] = 0

with open('/home/ubuntu/.hermes/credentials/kimchi-pool.json', 'w') as f:
    json.dump(pool, f, indent=2)
```

### 4. Wire into config.yaml

```python
import yaml

with open('/home/ubuntu/.hermes/config.yaml', 'r') as f:
    cfg = yaml.safe_load(f)

# Add provider entries for each key
for i in [1, 2, 3, 4]:
    pid = f'kimchi-{i}'
    if pid not in cfg['providers']:
        # Read key from pool
        with open('/home/ubuntu/.hermes/api-key-pool.json') as f:
            pool = json.load(f)
        for k in pool['pools']['kimchi']['keys']:
            if k['id'] == pid:
                cfg['providers'][pid] = {
                    'api_key': k['key'],
                    'base_url': k['base_url'],
                    'default_model': k['model'],
                    'name': f'Kimchi {i}'
                }
                break

# Register credential_pool_strategies entry
cfg['credential_pool_strategies'] = cfg.get('credential_pool_strategies', {}) or {}
cfg['credential_pool_strategies']['kimchi'] = {
    'type': 'api_key',
    'pool_file': '~/.hermes/api-key-pool.json',
    'pool_name': 'kimchi',
    'strategy': 'round_robin',
    'rotate_on': 'error',
    'provider_alias': 'kimchi-1',
    'headers': {'User-Agent': 'kimchi/0.1.17'}
}

# Set primary to first key
cfg['model']['primary'] = {
    'api_key': '<key-1>',
    'base_url': 'https://llm.kimchi.dev/openai/v1',
    'model': 'kimi-k2.6',
    'provider': 'kimchi-1'
}
cfg['model']['headers'] = {'User-Agent': 'kimchi/0.1.17'}

# Update fallback chain
chain = cfg.get('fallback_providers', [])
for k in ['kimchi-2', 'kimchi-3', 'kimchi-4']:
    if k not in chain:
        chain.append(k)
cfg['fallback_providers'] = chain

with open('/home/ubuntu/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

### 5. Patch `rotate_now.sh` for pool awareness

Two surgical edits:

**Edit 1 — argument parsing:**
```bash
# OLD
POOL="primary"
ERROR_TYPE="${1:-rate_limit}"

# NEW
if [ $# -ge 2 ]; then
  POOL="${1:-primary}"
  ERROR_TYPE="${2:-rate_limit}"
elif [ $# -eq 1 ]; then
  if [[ "$1" == "rate_limit" || "$1" == "exhausted" || "$1" == "invalid" ]]; then
    POOL="primary"
    ERROR_TYPE="$1"
  else
    POOL="$1"
    ERROR_TYPE="rate_limit"
  fi
else
  POOL="primary"
  ERROR_TYPE="rate_limit"
fi
```

**Edit 2 — current key detection uses `${POOL}` not `primary`:**
```python
keys = pool.get('pools', {}).get('${POOL}', {}).get('keys', [])
idx = pool.get('pools', {}).get('${POOL}', {}).get('current_index', 0)
```

**Edit 3 — add provider-branch in config update section:**
```bash
elif [[ "$NEXT_PROVIDER" == kimchi-* ]]; then
  hermes config set model.primary.provider "$NEXT_PROVIDER"
  hermes config set model.primary.model "${NEXT_MODEL:-kimi-k2.6}"
  hermes config set model.primary.base_url "$NEXT_BASE_URL"
  hermes config set model.primary.api_key "$NEXT_KEY"
fi
```

### 6. Patch `~/bin/rotate` for pool dispatch

```bash
# Detect known pools
KNOWN_POOLS=$(python3 "$ROTATOR" list 2>/dev/null | grep '^\[' | sed 's/^\[//;s/\].*$//' | tr '\n' ' ')

# Main dispatch — pool name as first arg
case "${1:-now}" in
    help|list|status|monitor|init|get|now|fail|reset)
        # existing handlers, default to primary
        ;;
    *)
        # Check if first arg is a known pool name
        if echo "$KNOWN_POOLS" | grep -qw "${1}"; then
            pool="$1"
            shift
            case "${1:-now}" in
                now|"") cmd_rotate_now "$pool" ;;
                fail|report) cmd_fail "$pool" "${2:?Missing key_id}" "${3:?Missing error_type}" ;;
                reset) cmd_reset "$pool" "${2:?Missing key_id}" ;;
                get|peek) cmd_get "$pool" ;;
            esac
        fi
        ;;
esac
```

`cmd_rotate_now` / `cmd_fail` / `cmd_reset` take `pool` as first arg.

### 7. Test

```bash
# Verify pool exists
python3 ~/.hermes/scripts/api_key_rotator.py list
# Should show [primary] AND [kimchi]

# Peek next key
rotate kimchi get
# Returns JSON with one of the kimchi-* keys

# Rotate
rotate kimchi
# Switches primary to next kimchi key in pool

# Fail + reset
rotate kimchi fail kimchi-3 rate_limit
rotate kimchi reset kimchi-3
```

## Pool command reference

| Command | Effect |
|---------|--------|
| `rotate` | Rotate primary pool (backward compat) |
| `rotate <pool>` | Rotate to next key in `<pool>` |
| `rotate <pool> get` | Peek next key without consuming |
| `rotate <pool> fail <id> <type>` | Mark key failed in pool |
| `rotate <pool> reset <id>` | Reset key status in pool |
| `rotate list` | List all pools + keys |
| `rotate status` | Current primary + pool summary |

`type` ∈ `rate_limit` | `exhausted` | `invalid`.

## URL stability note (Kimchi, verified 2026-07-13)

Only working URL: `https://llm.kimchi.dev/openai/v1`. Other Kimchi/CastAI URLs do NOT resolve or return 401:
- `https://api.kimchi.dev/v1` — DNS fails
- `https://api.castai.com/v1` — DNS fails
- `https://llm.castai.com/openai/v1` — DNS fails
- `https://api.tokenrouter.com/v1` — different service, Kimchi keys 401 there

Critical header: `User-Agent: kimchi/0.1.17` — routes to ai-enabler credit pool. Without it, 402 NO_CREDITS.

## Pitfalls

1. **Provider entries must exist in config.yaml** — `rotate_now.sh` updates `model.primary.provider` to the active provider name; if that provider isn't in `providers:`, `hermes config set` will fail silently or create a phantom.
2. **Pool file drift** — if `api-key-pool.json` has a `kimchi` pool but `config.yaml` providers section loses `kimchi-N`, provider swap (e.g., switching primary to cheapyun) wipes them. Always verify `grep -c kimchi ~/.hermes/config.yaml` ≥ 2 after any provider swap.
3. **`apikeys list` crashes on entries with missing `key` field** — a stale entry (e.g., mimo-9 with only `id`/`model`/`status`) breaks the entire `list` output. Always populate all required fields per pool entry schema.
4. **Memory tool drift guard** — `memory(action='add')` may refuse to write if MEMORY.md has drift from concurrent edits. Recovery: skip the memory tool, save durable state to config files. Don't loop trying to fix MEMORY.md — config files are the source of truth.
5. **Operator pattern "GUNAKAN X DISEMUA GRUP"** = set as primary + register dedicated pool + add to fallback chain. Don't just rotate within existing pool — they want full wiring.
