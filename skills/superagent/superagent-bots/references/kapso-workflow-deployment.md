# Kapso Workflow Deployment

Lessons from the first production deploy of Kapso CLI (v0.16.0) — WhatsApp Business Cloud workflows, deployed from VPS 18.143.107.30 to project `muham.dev` (Customer ID `3ddb09d8-5ddf-4c3e-9c1c-cb50183aa901`, Sandbox phone_number_id `597907523413541`).

## When to use this reference

- User wants to deploy WhatsApp Cloud workflows (Kapso = managed Cloudflare Worker backend)
- User says "kapso", "WhatsApp workflow", "WhatsApp bot", "kapso setup"
- User wants `api_call` / `inbound_message` / `whatsapp_event` triggers with `send_text` / `function` nodes
- Setting up a new project, or pushing a workflow that won't go through

Skip this reference if: user just wants raw WhatsApp Cloud API direct calls (no Kapso layer), or is using Twilio / MessageBird / similar.

---

## 1. Install & Auth

### Install location on Hermes VPS

Kapso CLI installs to `~/.hermes/node/bin/kapso` (NOT `/usr/local/bin`). Same pattern as `pm2`, `9router`, `yarn` — Hermes keeps its own global npm prefix. Add to PATH in `~/.bashrc`:

```bash
export PATH=$HOME/.hermes/node/bin:$PATH
```

### Non-interactive auth (best for unattended VPS)

`kapso login` is interactive (browser flow). For VPS, set the API key directly:

```bash
# Get key from https://app.kapso.ai/settings/api-keys
export KAPSO_API_KEY='***'
echo "export KAPSO_API_KEY='***'" >> ~/.bashrc
```

Verify: `kapso status` returns `Authentication: api key, Project Access: ready`. **API key only works through the kapso CLI** — direct calls to `https://api.kapso.ai/platform/v1/*` with `X-API-Key` header get HTTP 403 error 1010 (Cloudflare IP block on this VPS).

### SSH remote write pitfall (CRITICAL for second VPS)

When deploying the same auth to a second VPS via SSH, **env-var assignment via shell (`export KAPSO_API_KEY=*** gets `***` redacted by the transport layer**. Result: `kapso status` → "Invalid or missing API key" even though the var is "set" in `~/.bashrc`.

**Fix — write to a separate file via SFTP, then `source` it:**

```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file('/home/ubuntu/.ssh/vps_mining2')
client.connect(host, username='root', pkey=pkey)
sftp = client.open_sftp()
sftp.file('/root/.kapso-env.sh', 'w').write("export KAPSO_API_KEY='***'\...v.sh', 0o600)
sftp.close()
# Then in any shell:
#   source /root/.kapso-env.sh && kapso status
```

`source /root/.kapso-env.sh && kapso status` works. Re-checking `~/.bashrc` will show empty/masked value — that's the transport layer, not a real bug.

---

## 2. Workflow Source Layout

The kapso CLI does NOT use a single root `workflow.ts` for multi-workflow repos. Each workflow lives in its own subdirectory:

```
~/kapso-workflows/
├── src/                            (TypeScript sources — your code)
│   ├── webhook-handler.ts
│   ├── owntown-alerts.ts
│   └── daily-report.ts
├── workflows/<slug>/               (built artifacts — kapso reads these)
│   ├── workflow.ts                 (your source, with `export default workflow` appended)
│   ├── workflow.yaml               (metadata: name, slug, status, triggers)
│   └── definition.json             (nodes + edges graph)
├── functions/<slug>/               (Cloudflare Workers, see §4)
│   ├── index.js                    (entrypoint)
│   └── function.yaml               (NOT metadata.yaml — see pitfall)
├── build-all.ts                    (restructure script — see §3)
└── package.json
```

### Single-workflow `kapso build` vs multi-workflow custom build

- `kapso build` (built-in) compiles **a single** `workflow.ts` / `workflow.js` in the repo root. Won't work for multi-workflow repos.
- For multi-workflow repos, write your own build script that imports each workflow, calls `workflow.toSourceFiles()`, and writes the trio (`workflow.ts` + `workflow.yaml` + `definition.json`) to the right slug directory.

`workflow.toSourceFiles()` returns:
```ts
const { metadata, definition, definitionJson } = workflow.toSourceFiles();
```

`metadata` is the YAML frontmatter (slug, name, status, triggers). `definition` is the nodes/edges graph (TypeScript object). `definitionJson` is the serialized JSON.

---

## 3. Build Script Pattern

See `scripts/kapso-build.ts` for a complete reference implementation. Key points:

1. **Add `export default workflow`** to each source file (the build script appends this if missing). Kapso CLI uses this to re-import the workflow definition.
2. **Remove any stale `workflow.js`** left over from `kapso pull --overwrite` (which always writes `.js` not `.ts`). The build script overwrites `.ts` but doesn't remove `.js` — `kapso push` may pick up the wrong file.
3. **Convert `metadata` object → YAML** with `yaml` package (`YAML.stringify(meta)`). Don't write it as JSON.
4. **Run with `npx tsx`** (not `tsc`) — kapso workflow source is TypeScript with `.ts` files, but `tsx` doesn't strict-typecheck. `npx tsc` is unnecessary and slow.

---

## 4. Functions (Cloudflare Workers)

Functions are Cloudflare Workers managed by Kapso. They back `function`, `decide` (decisionType: 'function'), and other compute nodes. **WARNING: function deployment is broken on the current VPS IP range** (Cloudflare returns HTTP 403 error 1010 — same block that affects Kimchi API and other CF-fronted services). All function deployments fail with:

```
›   Error: Function "owntown-intent" deployment failed.
```

The remote function record IS created, but its `status: "error"` prevents `kapso push` from succeeding for any workflow that references it (you'll get "Function reference 'X' does not exist remotely or in this push").

**Workarounds in priority order:**

1. **Rewrite workflows without functions.** Use only the following node types — none require a function:
   - `send_text` (most common — WhatsApp text replies)
   - `send_interactive` (buttons, lists, location request)
   - `send_template` (pre-approved templates)
   - `set_variable` (local state for routing)
   - `call` (call another workflow by slug)
   - `wait_for_response` (pause for user reply)
   - `webhook` (HTTP request to external URL)
   - `decide` with `decisionType: 'ai'` (LLM-based routing, no function needed)
2. **Fix the IP block** — switch VPS provider (the current one is on Cloudflare's IP block list), or use Cloudflare WARP/exit node to get a non-blocked egress IP.
3. **Create functions via kapso dashboard** manually if you have access — the dashboard might bypass the API IP block.

### Function directory structure (when you DO need them)

```
functions/<slug>/
├── index.js          # entrypoint (export default async function handler(input))
└── function.yaml     # METADATA FILE — must be function.yaml, NOT metadata.yaml
```

**Pitfall**: if you create `metadata.yaml` (matching workflow conventions), `kapso push` silently ignores the function directory (treats it as 0 functions to deploy). The function is never uploaded. Same for workflows: `workflow.yaml`, not `metadata.yaml`. Naming is inconsistent.

`function.yaml` schema:
```yaml
entrypoint: index.js
function_type: cloudflare_worker
invoke_response_mode: passthrough
name: Display Name
public_endpoint: false
runtime_config: {}
slug: <slug>
```

---

## 5. Node Type Pitfalls

These are real schema validation errors that return HTTP 422 from kapso push. Each took 5-15 minutes to diagnose.

### `set_variable` — full required fields
```ts
// ❌ WRONG — kapso push: 422 validation error
workflow.addNode("log", {
  type: "set_variable",
  config: {},
  saveResponseTo: "logged",
});

// ✅ CORRECT
workflow.addNode("log", {
  type: "set_variable",
  variableName: "event",
  variableValue: "logged",
  valueType: "string",
  saveResponseTo: "logged",
});
```

Required: `variableName`, `variableValue`, `valueType` (one of `boolean` | `json` | `number` | `string`).

### `wait_for_response` — uses `timeoutSeconds`, not `timeout`
```ts
// ❌ WRONG
{ type: "wait_for_response", timeout: 86400 }
// → compiled to config: { has_timeout: false }, 422 on push

// ✅ CORRECT
{ type: "wait_for_response", timeoutSeconds: 86400 }
```

### `whatsapp_event` trigger — unknown event names fail 422
```ts
// ❌ WRONG — `customer.created` isn't in kapso's allowlist
workflow.addTrigger({
  type: "whatsapp_event",
  event: "customer.created",
  phoneNumberId: PHONE_ID,
  active: true,
});

// ✅ WORKAROUND — use inbound_message for any "new chat" trigger
workflow.addTrigger({
  type: "inbound_message",
  phoneNumberId: PHONE_ID,
  active: true,
});
```

**How to diagnose**: If `whatsapp_event` returns 422 with no body, it's almost always the event name. Switch to `inbound_message` (which fires on any incoming WhatsApp message) as a working substitute. Real `whatsapp_event` enum values aren't documented in the SDK — check the kapso dashboard or contact support for the canonical list.

### `decide` with functions — fails when functions can't deploy
```ts
// ❌ Requires function deployment (broken on this IP)
workflow.addNode("router", {
  type: "decide",
  decisionType: "function",
  functionSlug: "intent-detector",
  conditions: [
    { label: "high_value" },
    { label: "low_value" },
  ],
});

// ✅ No function needed — uses Kapso's LLM routing
workflow.addNode("router", {
  type: "decide",
  decisionType: "ai",
  conditions: [
    { label: "high_value" },
    { label: "low_value" },
  ],
  providerModel: "openai/gpt-4o-mini",  // optional override
});
```

### Multi-edge from non-decision node — warning, not error
```ts
// ⚠️ Warning: "Non-decision node 'log-event' has multiple outgoing edges"
// But push succeeds. To suppress, set a label on the edge.
workflow.addEdge("log-event", "forward-a", { label: "branch a" });
workflow.addEdge("log-event", "forward-b", { label: "branch b" });
```

---

## 6. Push Workflow

### Always `kapso pull --overwrite` before push
Remote-side changes (dashboard edits, prior failed pushes) make the local baseline stale. Push will fail with "Remote workflow 'X' changed since the last pull":

```bash
kapso pull --overwrite       # fetch latest remote state, overwriting local
npx tsx build-all.ts         # regenerate workflow artifacts
kapso push workflow <slug>   # one workflow at a time
```

### Push one workflow at a time
`kapso push` (no args) tries to push everything — functions and all. If function deployment is broken, the whole push fails. Push workflows individually:

```bash
for slug in webhook-handler owntown-alerts customer-onboarding daily-report; do
  kapso push workflow $slug
done
```

Workflows are pushed as **draft**. You must activate them in the kapso dashboard (https://app.kapso.ai/workflows/{id}/canvas). There's no CLI subcommand to activate — must click through UI.

### Common error messages decoded

| Error | Cause | Fix |
|---|---|---|
| `Function "X" already exists, but this repo has no baseline for it. Run 'kapso pull' first.` | Remote has the function but local doesn't have a baseline record | `kapso pull --overwrite` |
| `Local workflow "X" not found.` | Build script didn't generate the slug dir | Run `npx tsx build-all.ts` and check output |
| `Remote workflow "X" changed since the last pull.` | Someone (you, dashboard) edited it remotely | `kapso pull --overwrite` then push again |
| `Request failed with status code 422` | Node schema invalid (see §5) or stale baseline | Pull first, then check node type fields |
| `Function "X" deployment failed.` | CF Worker deploy blocked on this IP | Rewrite workflow without function refs (see §4) |
| `Function reference "X" does not exist remotely or in this push.` | Workflow refs a function that's not deployed | Remove the function node, or use decisionType: 'ai' |

---

## 7. 4 Workflows Deployed (Session 2026-06-13/14)

All pushed to kapso project (Customer `3ddb09d8...`, sandbox phone `597907523413541`):

1. **webhook-handler** — `api_call` trigger → `set_variable` log → `call` owntown-alerts + daily-report. URL: https://app.kapso.ai/workflows/e7dc3a7a-cfa8-45e3-a48e-81656a4cf9e9/canvas
2. **owntown-alerts** — `inbound_message` trigger → 5 `send_text` branches (welcome/status/earnings/stop/start). URL: https://app.kapso.ai/workflows/7dff15cd-7700-445c-b3a0-0fa172016afd/canvas
3. **customer-onboarding** — `inbound_message` trigger → `send_text` welcome → `wait_for_response` (24h) → `send_text` followup. URL: https://app.kapso.ai/workflows/1c6176a2-ec47-4b85-93ed-a00a29ca62e6/canvas
4. **daily-report** — `api_call` trigger → `webhook` (GET `https://api.muham.dev/v1/stats/daily`) → `send_text` formatted report. URL: https://app.kapso.ai/workflows/bce6e147-99b5-4513-afef-f46115ce20b1/canvas

All in **draft** status as of session end — need user to click "Activate" in dashboard.

---

## 8. Files

- Project root: `~/kapso-workflows/`
- Source TS: `~/kapso-workflows/src/*.ts`
- Build script: `~/kapso-workflows/build-all.ts` (also see `scripts/kapso-build.ts` template)
- kapso CLI: `~/.hermes/node/bin/kapso` (v0.16.0 as of 2026-06-13)
- Project ID is implicit (API key scope)
- Customer: `3ddb09d8-5ddf-4c3e-9c1c-cb50183aa901`
- WhatsApp number (sandbox): `597907523413541`
- `.kapso/remote-map.json` tracks local→remote ID mapping (do NOT delete — needed for push)
- `.kapso/project.json` binds the local dir to the kapso project

---

## 9. Quick Reference: kapso CLI commands

```bash
# Setup
kapso setup                                       # guided first-time setup
kapso link                                        # bind cwd to kapso project
kapso login                                       # interactive (browser)
export KAPSO_API_KEY=*** kapso status            # non-interactive

# Pull / push
kapso pull --overwrite                            # fetch + overwrite local
kapso push                                        # push everything
kapso push workflow <slug>                        # push one workflow
kapso push function <slug>                        # push one function (CF Worker)
kapso push --dry-run                              # show push plan, no changes

# Inspect
kapso status                                      # project + auth status
kapso whatsapp numbers list                       # list WA numbers
kapso customers list                              # list customers
kapso projects list                               # list projects (needs interactive login)

# Workflows (after push)
# Activate: open the canvas URL in dashboard, click "Activate"
```
