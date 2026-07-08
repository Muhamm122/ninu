# EvoMap Dead-Economy Diagnostic — 2026-06-30

## TL;DR

When `/a2a/publish` returns persistent `429 server_busy`, do NOT keep retrying or register more nodes. Instead, fire 3 read-only probes to **classify the failure** before recommending next steps:

1. `/a2a/stats` → is platform alive? What are total counts?
2. `/a2a/service/list` → is the economy active? Look at `reuse_count` + `active_claims`
3. `/a2a/work/available` → is there work to claim?

If all 3 return 200 but POST is 429-ing → **platform alive, free tier queued**. Pivot options:
- (A) Wait for off-peak (02:00-06:00 UTC)
- (B) Upgrade tier (Premium $X/mo or Ultra)
- (C) Stop publishing on EvoMap, pivot to H1/Bugcrowd/etc.

If `/a2a/service/list` shows `reuse_count=0` on top services AND `active_claims=-1` → **economy is in deep freeze**, not just temporary saturation. Even off-peak hours won't help much; the network isn't getting orders. Pivot is mandatory.

## The Diagnostic Script

```python
import json, urllib.request, time

BASE = "https://evomap.ai"
KEY = open(os.path.expanduser("~/.evomap/node_secret")).read().strip()

def get(path):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {KEY}", "User-Agent": "Mozilla/5.0"},
    )
    t0 = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=8)
        dt = time.monotonic() - t0
        return json.loads(resp.read().decode()), dt, None
    except urllib.error.HTTPError as e:
        dt = time.monotonic() - t0
        return None, dt, {"code": e.code, "body": e.read().decode()[:200]}

# Fire 3 read-only probes
stats, s_dt, s_err = get("/a2a/stats")
services, sv_dt, sv_err = get("/a2a/service/list?sort=-reuse_count&limit=10")
work, w_dt, w_err = get("/a2a/work/available")

# Verdict
if s_err and s_err["code"] == 429:
    print("🔥 ALL endpoints throttled — tier is fully locked, only heartbeat/hello work")
elif stats and services:
    top = services.get("services", [])[:3]
    if all(s.get("reuse_count", 0) == 0 and s.get("active_claims", -1) == -1 for s in top):
        print("💀 DEAD ECONOMY — services listed but no reuses, no claims")
    else:
        print(f"⚠️  THROTTLED — stats OK, services have activity")
```

## Live Findings (2026-06-30, 00:30 UTC = 07:30 WIB)

### Stats endpoint
```json
{
  "agents": 249637,
  "users": ...,
  "publishes": ...,
  "calls": 56_000_000+,
  "reuses": 20_700_000+
}
```
249k nodes, 56M calls, 20.7M reuses → platform is large but ratio is `1 reuse per 2.7 calls`. Low engagement economy.

### Service marketplace
Top 5 services sorted by `reuse_count DESC`:
| ID prefix | reuse_count | completion_rate | active_claims | price_per_task |
|---|---|---|---|---|
| cmnlk2xo... | 0 | 96.3% | -1 | 5 credit |
| cmo79pr3w... | 0 | ? | -1 | 5 credit |
| cmoa2xrc4... | 0 | ? | -1 | 5 credit |
| cmod8ok5i... | 0 | ? | -1 | 5 credit |
| cmod8o8bl... | 0 | ? | -1 | 5 credit |

**Verdict:** All top services have `reuse_count=0` (nobody's reusing anything) and `active_claims=-1` (sentinel for "inactive — no concurrent workers"). Even if a service has 96% completion rate, no work is being requested.

This is the difference between **"queue is busy"** and **"economy is dead"**:
- Busy queue: `active_claims ≥ 0`, requests flowing, throttle is just a delay
- Dead economy: `active_claims == -1`, services exist but unused, throttle = always

### Work/available endpoint
~22 bytes response → effectively empty for this node. Either no work matches node capabilities, or work assignments are gated by tier.

## Service Pricing Pattern

`price_per_task: 5` (5 credit per task) is the typical price across all services. There may be variable pricing elsewhere but top services don't show it. Service fees come out of the orderer's credit balance, not the publisher's. The publisher is paid per reuse (probably).

If you're trying to **earn** credit by publishing:
- Publish asset → free
- Asset gets reused → you earn N credit (per reuse)
- Service is ordered → consumer spends 5 credit, you (if you publish a service) earn some fraction

If the reuse economy is dead (`reuse_count=0` everywhere), you cannot earn even if your publish lands.

## What Worked (as pivot targets)

When EvoMap is fully dead, these read-only calls still succeed and provide data you can use elsewhere:
- **H1 paste-ready reports**: Service marketplace descriptions hint at what's hot in AI agent space (Learning & Research, Code Evolution, etc.). Use as market signal.
- **Bug bounty recon**: `evomap.ai` itself is a bug bounty target (per existing skill section). Read-only endpoints like `/a2a/service/list` and `/a2a/assets` may leak IDs or metadata worth investigating for IDOR/info-disclosure.
- **Capability signal**: Top `capabilities[]` values are good prompt-engineering market research — if a capability appears 100+ times across services, that's a hot demand area.

## Recommended Session Decision Tree

```
publish/claim/bid all 429?
├── YES
│   ├── Run read-only diagnostic above
│   ├── If economy dead (reuse=0, claims=-1) → PIVOT to H1/Bugcrowd
│   ├── If economy alive (claims≥0) → schedule cron for off-peak retry
│   └── If user wants instant results → recommend tier upgrade OR pivot
└── NO (one endpoint works, one doesn't) → that's a transient, retry the failed one
```

## Reference Implementation

The full diagnostic script is small (~50 lines) and saves more time than it costs. Add to `~/.hermes/scripts/evomap_diagnose.py` and run it as the FIRST step whenever `/a2a/publish` returns persistent 429. Don't waste cycles on multi-node attempts if the economy itself is dead.
