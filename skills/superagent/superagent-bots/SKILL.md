---
name: superagent-bots
description: "Telegram bots, process orchestration, cron, webhooks, automation. Includes Kapso WhatsApp Cloud workflow deployment (see references/kapso-workflow-deployment.md)."
---

## Operator Profile

Automation architect. Production-grade bots, schedulers, webhooks. Anti-fragile by default. Thinks in flows, triggers, retries, idempotency.

---

## Kapso Workflow Deployment (WhatsApp Cloud)

For WhatsApp Business Cloud workflows via Kapso CLI (manages Cloudflare Workers + WhatsApp Business API). Workflows authored in TypeScript, deployed via `kapso push`. **See `references/kapso-workflow-deployment.md`** for the full playbook covering:

- Hermes CLI install location (`~/.hermes/node/bin/kapso`, NOT `/usr/local/bin`)
- Non-interactive auth via `KAPSO_API_KEY` env var
- SSH remote write pitfall: env-var assignment gets `***` redacted by transport — use SFTP to write `.kapso-env.sh`, then `source` it
- Workflow source layout: `workflows/<slug>/{workflow.ts, workflow.yaml, definition.json}`
- Why `function.yaml` not `metadata.yaml` (kapso push silently ignores the wrong name)
- Why Cloudflare function deployment is broken on this VPS IP (HTTP 403 error 1010) and how to rewrite workflows without functions
- Node type pitfalls (`set_variable` fields, `wait_for_response.timeoutSeconds`, `whatsapp_event` event-name allowlist)
- Error message decoder for the 6 most common kapso push failures
- Working starter: `templates/kapso-workflow.ts`
- Build script: `scripts/kapso-build.ts` (run with `npx tsx`)

**Triggers**: user says "kapso", "WhatsApp workflow", "WhatsApp bot", "kapso setup", or any task involving `api_call` / `inbound_message` / `send_text` nodes.

---

## Execution Layer Selection

```
Visual orchestration:   Make.com (no-code), n8n (self-hosted, recommended for VPS)
Scheduled execution:    Python/Node + cron, GitHub Actions (free tier)
Persistent process:     Node.js + pm2 OR systemd (production)
Command interface:      Telegram Bot API (lowest setup friction)
                        Discord.js (community bots)
                        WhatsApp Cloud API (business)
                        Kapso CLI (managed WhatsApp + workflows — see above)
Queue / background:     BullMQ (Redis), in-memory queue (simple), SQLite-backed
```

## Cron-Based Log → Telegram Relay

For forwarding log events (bot activity, price alerts, server health, etc.) to a Telegram group without modifying the source code, use a Hermes cron + state file + `send_message` tool. Deduplication via byte offset tracking.

**See `references/cron-log-to-telegram-relay.md`** for the full recipe including:
- State file schema (byte cursor + history)
- Self-contained cron prompt template
- Pitfalls (`tail -c` vs `tail -n`, log rotation handling, `PrivateTmp` hiding, cross-machine state drift)
- Variations: timestamp cursors, multi-source relays, conditional routing

**Triggers**: user says "relay this log to Telegram", "forward events to <group>", "alert <group> when <event>", "send every X event to <chat>", or wants to set up a watch-only notification system for any persistent log.

**Reference implementation**: cron `otwn-alert-relay` (job_id `753284cdb3a0`) — every 1m, delivers OTWN bot events to telegram:Mining / -1004410582846.

## Production Telegram Bot (Node — anti-duplicate, error-recovery)
