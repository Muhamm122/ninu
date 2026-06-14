# Cron-Based Log → Telegram Relay Pattern

**Class-level pattern.** A Hermes cron job + a state file (byte-offset cursor) + the `send_message` tool = a log-file watcher that forwards events to a Telegram group, deduplicated, on a fixed schedule.

**Use when:** any persistent log file (bot, app, daemon) where you want new events routed to a Telegram group without modifying the source code, and a delay of `cron_interval` is acceptable.

**Reference implementation:** `cron 753284cdb3a0` (`otwn-alert-relay`, every 1m, delivers to telegram:Mining / -1004410582846, source = owntown bot log).

---

## Why this pattern (vs alternatives)

| Alternative | Problem |
|---|---|
| Modify source code to call Telegram API | Couples log producer to Telegram; redeploy needed to add a channel |
| `tail -F` piped to a script | Dies on reboot; no deduplication; no delivery confirmation |
| inotifywait-based watcher | Per-service process, fragile across reboots, no agent intelligence |
| logstash / fluentd | Overkill, needs Elasticsearch or similar sink |
| **Cron + state file + send_message** | Self-healing, dedup'd, uses agent for filtering/formatting, zero source changes |

The cron + state file + send_message pattern is the lowest-friction way to forward log events to Telegram, and it gets free filtering and formatting from the agent loop.

---

## Recipe (5 steps)

### 1. Pick a state file

Store the byte offset cursor in a small JSON file. Path: `~/.hermes/data/<relay-name>_state.json`. Shape:

```json
{
  "last_byte_offset": 0,
  "last_run_at": null,
  "last_event_count": 0,
  "history": []
}
```

`last_byte_offset` is the only required field. `history` is optional (last 5-10 runs for debugging).

### 2. Pick the source log

Use any persistent log file written by the service you want to monitor. Examples from this session:
- `~/.hermes/skills/owntown-farming-antidetect/logs/bot.log` (game bot events)
- A systemd service's `journalctl -u <service> --since=...` output (system events)
- A custom app's `app.log` (app events)

### 3. Write the cron prompt

The prompt must be **self-contained** (cron sessions have no chat context). Give the agent:
- Source log path
- State file path
- Destination Telegram target (chat_id or named channel)
- Filter rules (regex/event types to forward)
- Format rules (one-line vs block, emoji, header)
- Deduplication rule (byte offset)
- "Send nothing if no new events" (silent mode)

Example prompt skeleton:

```
You are the X relay. Every tick:

1. Read state file `~/.hermes/data/x_state.json` → get `last_byte_offset` (or 0).
2. Run: `wc -c <source_log_path>` to get current size.
3. If size > last_byte_offset:
     tail -c +$((last_byte_offset + 1)) <source_log_path> > /tmp/x_new.log
     Update state: last_byte_offset = current size.
4. Filter /tmp/x_new.log for events matching: <regex_or_keywords>
5. If matches > 0, format and send to telegram:<target> via send_message tool.
6. Append to state.history: { run_at, byte_offset, events, delivered }.
7. Write updated state file.
8. If no events: exit silently. Do not send a "no events" message.
```

### 4. Schedule the cron

```
cronjob(
    action="create",
    name="<relay-name>",
    schedule="every 1m",     # 1m for real-time, 5m for low-priority
    deliver="local",          # delivery controlled by prompt's send_message
    enabled_toolsets=["file", "terminal"],
    prompt=<prompt>
)
```

**Why `deliver="local"`:** the cron delivers the agent's output nowhere. The prompt explicitly calls `send_message` with the right target. This gives you routing control (different relays → different groups) without creating per-target crons.

**Why `enabled_toolsets=["file", "terminal"]`:** minimal scope, faster cold start. Don't grant `web`/`browser` to a relay that only reads files.

### 5. Verify on first run

After `cronjob action="run" job_id=...`, check:
- `state.last_byte_offset` increased
- `state.last_run_at` set
- `state.history` has the entry
- Telegram group received the message (visible msg_id in send_message response)

If `last_byte_offset` is unchanged, the prompt failed to read the log. Read the agent's delivered output (or `journalctl` if Hermes logs to journal) to debug.

---

## Pitfalls

### ⛔ Use `tail -c +$((offset + 1))` not `tail -n +<line>`

Byte offsets are stable across log rotations. Line numbers reset to 1 after rotation. If the log rotates, the next tick will skip the old lines (good) and start reading from offset 0 of the new file (also good, because new file = size 0 ≈ old offset → no double-read).

`tail -c +N` reads from byte N onwards (1-indexed). `tail -n +N` reads from line N. Always use byte offset.

### ⛔ Truncate the log → state file becomes invalid

If the source log is truncated (e.g. `> bot.log` for some reason) while the cron is reading, the new size will be smaller than `last_byte_offset`. The cron will read 0 new bytes (correct), but the next rotation will look like a giant new log. Fix: on each run, also handle the case where `size < last_byte_offset` (log rotated/truncated) by resetting `last_byte_offset = 0`.

```bash
NEW_SIZE=$(wc -c < log)
if [ "$NEW_SIZE" -lt "$LAST_OFFSET" ]; then
  echo "Log rotated/truncated. Resetting offset."
  LAST_OFFSET=0
fi
```

### ⛔ Don't trust the agent to send to the right group

The agent has `send_message` tool which can route to any connected platform. In the prompt, be EXPLICIT about the target:

```
Send to: telegram:-1004410582846 (Mining group) ONLY.
Do NOT send to the current chat, the home channel, or any other group.
```

Without this, the agent may default to `deliver="origin"` behavior and spam the wrong group.

### ⛔ Filtering happens in the prompt, not in cron schedule

If you want only fish-catch events but the bot logs 30 other event types, the filtering is in the prompt, not the cron schedule. Don't try to schedule more frequently and hope to filter at the source — the agent does the regex.

### ⛔ For "every event" promises, set cron to 1m

5 min latency for a "real-time" alert feels broken. Use `every 1m` for events the user wants immediately. Use `every 5m` or `every 15m` for less urgent monitoring.

### ⛔ Systemd `PrivateTmp=true` can hide log file paths

If the source service has `PrivateTmp=true` (owntown bot does), the log file is in a per-service `/tmp` namespace. `cron` runs in the global `/tmp`. If you set the source path to `/tmp/something.log`, the cron can't see it. Solution: log to a non-PrivateTmp path (e.g. `~/.hermes/skills/<name>/logs/`) and have the service write to that.

### ⛔ State file drift across machines

If the source log lives on VPS A and the cron runs on VPS B, the state file's byte offset is wrong (VPS A's log size differs from VPS B's view). Either:
- Run the cron ON the same machine as the source log
- Or use a network-shared state file (S3, NFS) — overkill for most cases
- Or use the `last_run_at` timestamp as the cursor instead of bytes (works for services that don't truncate)

For cross-machine setups, prefer timestamp cursors (`mtime` of log file, or "events since 5min ago") over byte offsets.

---

## Variations

### Timestamp-based cursor (for cross-machine or rotated logs)

Replace byte offset with:
```json
{ "last_seen_mtime": "2026-06-14T05:30:00Z" }
```
On each run, find log lines with mtime > last_seen_mtime. Works across log rotation. Less precise than bytes (subject to filesystem mtime resolution), but more portable.

### Multi-source relay (one cron, many log files)

State file with per-source offsets:
```json
{
  "sources": {
    "bot.log": 44786,
    "error.log": 1203,
    "trade.log": 0
  }
}
```
Prompt iterates sources, accumulates events into one Telegram message (with source tag per event).

### Conditional routing (different events → different groups)

In the prompt, branch on event type:
```
If event matches "fish" → send to telegram:Mining
If event matches "trade" → send to telegram:Trading
If event matches "pvp" → send to telegram:Combat
```
Achieved via 1 cron with multi-call send_message. Don't create N crons for N event types.

### Bidirectional (read + acknowledge)

For alerts that need acknowledgment, use inline keyboards. Not directly supported by `send_message` (which is one-shot), but you can:
- Have the cron poll a callback endpoint (overkill)
- Or accept acknowledgment via another cron that scans recent chat messages
- Or just don't ack — alerts are fire-and-forget

---

## Worked example: owntown bot event relay

State: `~/.hermes/data/otwn_alert_state.json`
```json
{
  "last_byte_offset": 0,
  "last_run_at": null,
  "last_event_count": 0,
  "history": []
}
```

Cron: `otwn-alert-relay` (job_id `753284cdb3a0`), schedule `every 1m`, deliver `local`.

Prompt instructions (the agent reads this every tick):
1. Read `~/.hermes/data/otwn_alert_state.json` for `last_byte_offset`
2. Get current size of `~/.hermes/skills/owntown-farming-antidetect/logs/bot.log`
3. If size > offset: read `tail -c +$((offset + 1))` of log, filter for: `🎣|Bal:|Disconnected|🧅|=== Cycle|❌|Account frozen`
4. Format matched lines as Telegram message (compact, with header + timestamp)
5. Send via `send_message(target="telegram:Mining")` to chat_id `-1004410582846`
6. Update state file with new offset, run metadata, append to history
7. Silent if no matches

Result: every minute, Mining group receives a compact summary of any new OTWN bot events. No source code changes. No daemon process. Self-healing across reboots.

---

## When NOT to use this pattern

- **Sub-second latency required** — cron min interval is 1m. Use a true watcher (inotifywait, socket-server, webhook) instead.
- **Need to react to event content (auto-actions)** — relays are fire-and-forget. For "if X then Y" logic, embed the action in the source code or use a webhook subscriber.
- **High event volume (>100/min)** — Telegram rate limits (~30 msg/min per bot, ~20/sec global). Aggregate at the source first.
- **Cross-machine state sync** — use a real event bus (Redis, Kafka, NATS), not a file cursor.
- **Need 100% delivery guarantee** — file cursors can miss events on rotation/crash. Use a proper queue.

For 95% of "I want my Telegram group to know when X happens in my service" use cases, this pattern is the right answer.
