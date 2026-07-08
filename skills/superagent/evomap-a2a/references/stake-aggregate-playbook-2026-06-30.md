# Multi-Node Stake Aggregate Playbook (2026-06-30)

**Problem:** When user asks "berapa total stake gue?" or "cek node mana aja yg udah stake", the obvious path — read `/a2a/nodes` and sum `validator.stake_amount` — returns **0 for every node**. The dashboard shows real stakes, the API lies. This reference captures the verified playbook for getting the truth.

## TL;DR — the working pattern

```python
import requests, json
from concurrent.futures import ThreadPoolExecutor

HUB = "https://evomap.ai"
HEADERS = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

# Step 1: discover user's nodes
nodes_resp = requests.get(
    f"{HUB}/a2a/nodes",
    headers=HEADERS,
    params={"limit": 200, "user_id": user_id},  # user_id from /a2a/identity/<nodeId>
    timeout=15,
).json()

nodes = nodes_resp.get("nodes") or nodes_resp.get("payload", {}).get("nodes") or []
print(f"Found {len(nodes)} nodes for user")

# Step 2: fan out /billing/stake/:nodeId calls in parallel
def get_stake(node):
    nid = node["node_id"]
    r = requests.get(
        f"{HUB}/billing/stake/{nid}",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=10,
    )
    return nid, r.json()

with ThreadPoolExecutor(max_workers=8) as ex:
    stakes = list(ex.map(get_stake, nodes))

# Step 3: filter real stakers
real_stakes = [(nid, s) for nid, s in stakes if s.get("staked")]
total = sum(s["stake_amount"] for _, s in real_stakes)
print(f"Staked: {len(real_stakes)}/{len(nodes)} nodes, total {total} credits")
```

**Verified 2026-06-30:** agussepte12 account has **101 nodes**, **37 staked**, **17,300 credits** total stake.

## The three traps that block naive implementations

### Trap #1: `/billing/stake/:nodeId` is auth-free and returns a TEMPLATE response for ANY string

```bash
# Any garbage returns the same template
curl https://evomap.ai/billing/stake/asdfasdfasdf
# → {"node_id":"asdfasdfasdf","staked":false,"stake_amount":0,"status":"none","min_for_eligibility":100}
```

The endpoint echoes back whatever you pass in `node_id` field and always returns `staked: false`. **It does NOT validate node existence.** This means:
- You cannot distinguish "node doesn't exist" from "node exists but unstaked"
- You MUST authenticate and pass a real `node_id` to get real data
- Real response shape when staked: `{"node_id":"node_xxx","staked":true,"stake_amount":500,"status":"active","staked_at":"2026-06-30T...","slash_count":0,...}`

### Trap #2: `/a2a/nodes` `validator.stake_amount` field is ALWAYS 0

```json
{
  "node_id": "node_04ac3dd013a9",
  "alias": "Hermes Agent v2",
  "validator": {
    "stake_amount": 0,        // ← LIES, real stake is 500
    "stake_status": "unknown", // ← also unreliable
    "eligible": true
  }
}
```

Even nodes with verified 500-credit stake return `validator.stake_amount: 0` from `/a2a/nodes`. The validator sub-object on the nodes listing is **stale or never written**. Do NOT trust it for stake aggregation.

The same `/billing/stake/:nodeId` endpoint that handles Trap #1 returns the real values when you pass the correct node_id. So:
- `/billing/stake/<fake>` → template (staked: false)
- `/billing/stake/<real-and-staked>` → real data (staked: true, amount: 500)
- `/billing/stake/<real-but-unstaked>` → real data (staked: false, amount: 0)

### Trap #3: User identity disambiguation — emails are NOT node_ids

User said "fokus ngerjain make node agussepte12". The natural read is "node with alias agussepte12". But:
- `agussepte12` is the user's **email/login handle** (matches the EvoMap account email field)
- It's also set as the **alias** on some nodes the user registered (visible in `/a2a/nodes` listing)
- But it is NOT a `node_id` — `node_id` always starts with `node_` followed by 12 hex chars

**Working pattern:** when user refers to themselves by name/email:
1. Pull `user_id` from `/a2a/identity/<any_owned_node_id>` — this is the canonical user identifier
2. Use `?user_id=<that_id>` filter on `/a2a/nodes` to get all 101 nodes
3. Don't try to resolve "agussepte12" → node_id directly; the alias field is set by `/a2a/hello` payload `name` and may match email, handle, or anything else

## Pagination gotcha

`/a2a/nodes` default limit returned 51 nodes for an account with 101 nodes (off-by-one pagination). Always pass `limit=200` for full enumeration of an active publisher account. The response includes a `total` field — use it to detect clipping:

```python
total = nodes_resp.get("total", 0)
if len(nodes) < total:
    print(f"WARNING: clipped, got {len(nodes)}/{total}, raise limit")
```

## Sequential-vs-parallel timing

- Sequential: 51 nodes × ~1s each = 51s — exceeds the 60s default client timeout
- Parallel (`ThreadPoolExecutor`, max_workers=8): completes in ~5-7s
- Tor route adds 500ms-1s per request (CloakBrowser pattern unnecessary — billing endpoints return 200 from VPS IP)

## Validation checks

After fetching stakes, sanity-check against expected ranges:

```python
# Each real stake should be a multiple of 100 (stake increments)
for nid, s in real_stakes:
    assert s["stake_amount"] % 100 == 0, f"weird stake: {nid} = {s['stake_amount']}"

# min_for_eligibility is 100 in the template, so amounts below that = no eligibility
# Common values seen: 100, 500, 1000
```

## Reference endpoints summary

| Endpoint | Returns real stake? | Auth needed? | Pagination reliable? |
|----------|---------------------|--------------|----------------------|
| `GET /a2a/nodes` | ❌ `validator.stake_amount: 0` for all | ✅ Bearer | ⚠️ clip at limit, use `total` field |
| `GET /billing/stake/:nodeId` (fake) | ⚠️ template only | ❌ no auth needed | N/A |
| `GET /billing/stake/:nodeId` (real + Bearer) | ✅ | ✅ Bearer | N/A |
| `GET /a2a/identity/:nodeId` | N/A (gives `user_id`) | ✅ Bearer | N/A |

## Use this playbook when

- User asks "cek stake" / "berapa stake gue" / "node mana yg udah stake"
- User asks "ada berapa node" / "list semua node"
- Dashboard shows different numbers from what the API returns
- Operator needs to reconcile multi-node stake accounting
- User switches identity context (new email/handle) and wants to verify

## Don't use this playbook when

- Single-node operation — just call `/billing/stake/<known_node_id>` directly
- User only needs heartbeat credit_balance — that's in `/a2a/heartbeat` response
- User wants reputation — that's in `onboarding.reputation` from heartbeat, not stake

## Related pitfalls in SKILL.md

- #23: `env_fingerprint` dedup returns existing node, not new one
- #33: Validator stake does NOT bypass publish queue
- #34: Credit topup is CF-blocked from VPS
- #36: per-endpoint body field name (sender_id vs node_id)
- #38: Reputation tiers from /economics
- #39: force_update directive unlocks ATP settlement
- #41: /billing/plans is canonical source for tier limits
- #45: /account/me returns 404, /account/balance returns 200 empty
- #49: owner_user_id: null is unclaimed state
- #52: /a2a/account/* and /a2a/credit/* are CF-blocked from VPS
