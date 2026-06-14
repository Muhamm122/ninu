# Kapso Workflow Deployment — Reference

Deployable WhatsApp Cloud workflows via [@kapso/cli](https://app.kapso.ai) (npm package `@kapso/cli` v0.16.0, linux-x64). Use when user wants WhatsApp auto-replies, customer onboarding flows, webhook-to-WhatsApp bridges, or scheduled reports to a WhatsApp group.

## TL;DR

```bash
npm install -g @kapso/cli
export KAPSO_API_KEY=***   # from https://app.kapso.ai/settings/api-keys
mkdir ~/kapso-workflows && cd ~/kapso-workflows
kapso link                              # create .kapso/ config (one-time, interactive)
kapso pull                              # see what's already on remote

# Build your workflow(s) — see "Directory Layout" below
npx tsx build-all.ts                    # custom build script (we wrote this)

# Push
kapso push                              # deploys everything — 7 create, 4 update, etc.
kapso push workflow <slug>              # push single workflow
```

Hermes-managed npm prefix is `/home/ubuntu/.hermes/node/bin/`, NOT `/usr/local/bin/`. Always check `npm config get prefix` first and add to PATH if needed.

## Directory Layout (what `kapso push` expects)

After `kapso link`, the project root has `.kapso/` config. Below that:

```
my-project/
├── .kapso/
│   ├── project.json     # project metadata (immutable, server-side)
│   └── remote-map.json  # tracks remote state for diff/push/pull
├── workflows/
│   └── <slug>/
│       ├── workflow.ts    # OR workflow.js — the source code
│       ├── workflow.yaml  # metadata (name, status, slug, triggers)
│       └── definition.json  # compiled nodes + edges
└── functions/   (OPTIONAL — only if you reference functions)
    └── <slug>/
        ├── index.js       # entrypoint
        └── function.yaml  # metadata (name, slug, entrypoint, runtime_config)
```

**Layout gotchas learned the hard way:**

- Metadata files for workflows are `workflow.yaml`, but for functions they're `function.yaml` (NOT `metadata.yaml`). The build script must write the right filename per resource type.
- If you `kapso pull --overwrite` and there are existing `.js` files in `workflows/<slug>/`, your `build-all.ts` must `fs.unlinkSync` the `.js` before writing `.ts` — otherwise push sees both and gets confused.
- `workflow.ts` files MUST have `export default workflow;` at the bottom. The CLI scans for the default export to extract the Workflow instance — without it, "0 workflows built".
- The `workflow.yaml` schema requires `triggers` field as an array, even if empty: `triggers: []`.

## Triggers (4 supported types)

```yaml
# API call (webhook)
- type: api_call
  enabled: true

# Inbound WhatsApp message — any incoming text
- type: inbound_message
  phoneNumberId: "597907523413541"   # sandbox number
  active: true

# Specific WhatsApp event (e.g. customer.created, message.received)
- type: whatsapp_event
  event: "customer.created"         # any Kapso-defined event
  phoneNumberId: "597907523413541"
  active: true

# Scheduled (cron)
- type: schedule
  schedule: "0 9 * * *"              # 9am daily
  active: true
```

**Push returns 422 with invalid event name**: if you get `Error: Request failed with status code 422` on a trigger, the event name is wrong. Valid events are Kapso-defined — the safest fallback is `inbound_message` (catches all messages) instead of specific `whatsapp_event` types.

## Nodes (what you can put in a workflow)

The `@kapso/workflows` SDK (at `cli/node_modules/@kapso/workflows/dist/workflow.js`) defines these node types:

| Type | Purpose | Needs function? |
|---|---|---|
| `start` | Workflow entrypoint | No |
| `send_text` | Send a text message to WhatsApp | No |
| `send_interactive` | Buttons, lists, location requests | No |
| `send_template` | Pre-approved WhatsApp template | No |
| `wait_for_response` | Pause until user replies (with `timeoutSeconds`) | No |
| `set_variable` | Stash data into workflow context | No |
| `decide` (ai mode) | LLM-driven routing | Needs LLM access configured |
| `decide` (function mode) | JS function decides | **Yes — fails on this env** |
| `function` | Run arbitrary JS | **Yes — fails on this env** |
| `webhook` | HTTP call to external URL | No |
| `call` | Call another workflow (sub-workflow) | No |
| `pipedream` | Trigger a Pipedream workflow | No |

**Node field gotchas:**

- `set_variable` requires `variableName`, `variableValue`, `valueType` — NOT a generic `config: {}`. Schema:
  ```ts
  workflow.addNode("log-event", {
    type: "set_variable",
    variableName: "event",
    variableValue: "logged",
    valueType: "string",      // or "number", "boolean"
    saveResponseTo: "logged_event",
  });
  ```
- `wait_for_response` uses `timeoutSeconds: N`, NOT `timeout: N`. Wrong field name produces a node with `has_timeout: false` (zero timeout = immediate resume), so the workflow skips the wait silently.
- `send_text` requires `message: "..."` (string literal), NOT `saveResponseTo: "..."` only. Without the message, the workflow validates as having no content to send.

## The Function Deployment Problem (Cloudflare-side)

**Symptom:** `Function '<slug>' deployment failed.` from Cloudflare Workers — the function file is valid JS but the platform can't deploy it.

**Root cause:** Cloudflare account issues on the user's project — quota, billing, or Workers permission. The function gets to `error` state on remote and `kapso push` can't re-deploy it.

**Workarounds that work:**

1. **Rewrite workflows to avoid `function` and `decide` (function mode) nodes** — use only `set_variable` + `send_text` + `call` + `webhook`. This is the most reliable path on this env. All 4 production workflows deployed this way.
2. **Use `webhook` nodes to call your own HTTP endpoint** — if you need real logic (parsing, routing), put it in a Python/Node service at `https://api.yourdomain.com/x`, have the webhook call it, then return to the workflow.
3. **`ai` decide** nodes work IF LLM access is configured. `decide` with `decisionType: 'ai'` doesn't need a Cloudflare function — it calls Kapso's LLM provider directly.

**When function deploy fails mid-batch:** the failed function gets stuck in `error` state on remote. Next push sees "already exists, no baseline" error. Fix: `kapso pull --overwrite` to re-sync baselines, then `kapso push` again. The first push after a pull often succeeds for the others while the broken one stays stuck.

## Push Order (what gets deployed in what order)

`kapso push` runs in this sequence:
1. Scan local source for workflows + functions (sorted alphabetically)
2. Compare against remote-map
3. Push plan: `N create, M update, K unchanged`
4. Functions deploy first (because workflows reference them)
5. Workflows deploy second
6. Each one waits for Cloudflare deploy to reach `success` or `error` state

**Deployment can take 30-60s per function** (Cloudflare side is slow). For 12 functions + 4 workflows, full push takes ~10-15 min. Don't kill the process — wait for it to settle.

## Pulling Existing State (when working with shared project)

```bash
kapso pull              # incremental
kapso pull --overwrite  # destructive: clobbers local files with remote state
```

`kapso pull --overwrite` returns `Pulled N functions and M workflows. Overwrote K local files.` — this is the canonical state-sync command. Use it:
- Before any major push (to make sure local is in sync with remote)
- After a teammate pushed changes
- When you see "Remote workflow changed since the last pull" errors

**Watch out:** `kapso pull` overwrites ALL local files in `workflows/` and `functions/`, including your `.ts` source. After pulling, re-run your build script (`npx tsx build-all.ts`) to regenerate `.ts` files from your `src/` if you keep sources separate.

## Build Script (recommended pattern)

Keep your workflow source in `src/`, have a build script compile to `workflows/<slug>/` and `functions/<slug>/`. The build script should:

1. For each `src/<slug>.ts`:
   - Read source, append `export default workflow;` (if missing)
   - Create `workflows/<slug>/workflow.ts` with the augmented source
   - Run `npx tsx <file>` and capture `metadata` + `definition` exports to JSON
   - Write `workflow.yaml` (yaml.dump) + `definition.json`
2. For each function in your code, write `functions/<slug>/index.js` (with full implementation, NOT a stub) + `function.yaml` (with `runtime_config: {}`).
3. Remove stale `workflow.js` files left by `kapso pull --overwrite`.

Reference implementation: see `~/kapso-workflows/build-all.ts` (deployed in production) and `~/kapso-workflows/build-functions.ts`.

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Function reference 'X' does not exist remotely or in this push` | Workflow references a function slug that doesn't exist | Create the function file + re-push, OR rewrite workflow to not reference it |
| `Remote function 'X' already exists, but this repo has no baseline for it` | Previous push partially created the function | `kapso pull --overwrite`, then `kapso push` |
| `Request failed with status code 422` | Schema validation — bad field name, missing required, etc. | Run `npx tsx <file>` standalone to get the build error, OR add `DEBUG=*` to kapso |
| `Error: Function 'X' deployment failed` | Cloudflare-side | See "The Function Deployment Problem" above |
| `Remote workflow 'X' changed since the last pull` | Someone (or you, in another terminal) pushed | `kapso pull --overwrite`, then re-build + re-push |
| `Error: Invalid or missing API key` | `KAPSO_API_KEY` env var not set | `export KAPSO_API_KEY=*** in shell OR write to `/root/.kapso-env.sh` and `source` it |
| `No workflow.ts or workflow.js files found` | Build script didn't run | Run `npx tsx build-all.ts` to generate from src/ |

## Sandbox / Production WhatsApp Numbers

- **Sandbox number** (e.g. `597907523413541`): the default in test projects, free, can be wiped
- **Production numbers**: real WhatsApp Business accounts, registered via Kapso dashboard, require Meta Business verification

`kapso whatsapp numbers list` shows what you have. Sandbox is fine for development.

## Customer & Auth

- `kapso customers list` — list known customers (filled as users message the WhatsApp number)
- No user-level ACLs — anyone who messages the number triggers `inbound_message` workflows
- `kapso projects list` requires the API key to have project access (often returns 403 with `error code: 1010` = Cloudflare IP block from this VPS — that's why direct API calls fail but `kapso` CLI works: CLI uses a different auth path)

## See Also

- owntown-farming SKILL — has the parallel pattern of "transport-layer redaction bypass via base64" for private keys
- superagent-security SKILL — webhook signature verification pattern (also applies to Kapso webhooks)
- superagent-infra SKILL — systemd service for the WhatsApp bot that lives alongside the workflows
