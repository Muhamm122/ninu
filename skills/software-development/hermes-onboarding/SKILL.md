---
name: hermes-onboarding
description: "Onboard a Hermes agent using the SOUL Guide. Sets up SOUL.md, credential storage, and verifies configuration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [onboarding, SOUL, setup, configuration]
    related_skills: [hermes-agent, github-auth]
---

# Hermes Onboarding (SOUL Guide)

Onboard a Hermes agent using the SOUL Guide from https://guide.mahiru.my.id/id/. This skill captures the workflow for setting up a new agent with proper persona, credentials, and baseline verification.

## When to Use
- Starting with a fresh Hermes installation
- After resetting or cloning a Hermes environment
- When you want to ensure the agent follows the SOUL Guide principles

## Steps

### 1. Review the SOUL Guide
Navigate to the guide and absorb the principles:
- Agent identity, communication, capabilities, autonomy, boundaries, memory, verification, escalation, default disposition.
- Understand that agent development is iterative: small tasks → correction → save to SOUL.md/memory → repeat.

### 2. Update SOUL.md
Edit `~/.hermes/SOUL.md` to reflect your preferences. At minimum include:
- **Identity**: name, role, language register, relationship.
- **Communication**: language for chat vs files, emoji usage, technical terms, tone.
- **Capabilities**: list of accessible tools, wallets, platforms (note where credentials are stored, never in SOUL.md).
- **Autonomy & Boundaries**: fully autonomous actions, autonomous+log actions, actions requiring confirmation.
- **Memory Rules**: what to store (preferences, workflow, corrections) and what not to store (credentials, temporary data).
- **Verification & Escalation**: how to verify results and when to ask for help.
- **Resource Management**: start→use→stop pattern, avoid idle services.
- **Default Disposition**: assume user knows what they’re doing; ask clarifying questions instead of refusing.

### 3. Prepare Credential Storage
Create a secure directory for credentials (never store them in SOUL.md):
```bash
mkdir -p ~/.agent/credentials
```
Store API keys, tokens, etc., in `~/.hermes/.env` or in the credentials directory, and reference them by path.

### 4. Verify Configuration
Run diagnostics to ensure everything is working:
```bash
hermes doctor
```
Address any warnings (e.g., missing API keys, npm vulnerabilities). For npm vulnerabilities in the browser toolkit:
```bash
cd /home/ubuntu/.hermes/hermes-agent && npm audit fix
```

### 5. Test the Setup
Send a one‑shot query to confirm the persona is loaded:
```bash
hermes -z "Test: Balas dengan kalimat singkat dalam Bahasa Indonesia konfirmasi bahwa SOUL.md telah berhasil dimuat dan agent siap membantu."
```
You should receive a short Indonesian confirmation.

### 6. Iterate
Give the agent a small task, review the output, correct if needed, and save stable corrections to SOUL.md or memory. Repeat to build trust and autonomy.

## Pitfalls
- **Do not put credentials in SOUL.md** – they may leak into logs or context.
- **Avoid dumping project‑specific instructions into SOUL.md** – keep SOUL.md for permanent, cross‑context rules; use memory or separate files for task‑specific details.
- **Do not expect instant autonomy** – autonomy emerges through repeated small‑task cycles.
- **Remember to run `hermes doctor` after changes** to catch configuration issues early.

### Systemd Service Setup (Ubuntu/Linux)
When installing a Node.js app as a systemd service:
- **Always use the full path to `node`** — `$(which node)` — not `/usr/bin/node`. Hermes installs Node.js under `~/.local/bin/node` (symlink to `~/.hermes/node/bin/node`), and systemd's default `$PATH` won't include it.
- **Set `User=ubuntu` (or the actual user)** in the service file — otherwise the service runs as root and may not have access to files in the user's home.
- **Set `WorkingDirectory`** to the app's install directory (e.g., `/opt/appname`), not `/tmp` — `/tmp` may be cleaned on reboot.
- **Pass env vars directly** in the service file with `Environment=KEY=VALUE` rather than relying on `EnvironmentFile` if the `.env` file is in a non-standard location.
- **Test the service manually first**: `cd /opt/appname && node server/dist/index.js &` then `curl http://127.0.0.1:PORT/api/ping` before creating the systemd unit.
- **Check logs on failure**: `sudo journalctl -u servicename --no-pager -n 30` — exit code 203/EXEC usually means the binary path is wrong or the file isn't executable.

### Third-Party Tool Integration Pattern
When integrating an external tool (e.g., FreeLLMAPI) as a Hermes custom provider:
1. Install and test the tool standalone first
2. Create a systemd service for persistence
3. Add to `custom_providers` in `config.yaml` via `hermes config set custom_providers '[...]'`
4. The gateway auto-reloads config on restart — no manual restart needed in most cases
5. Test with a one-shot query through the new provider: `hermes -m providername/modelname -q "test"`

## References
- `references/guide-summary.md` – condensed summary of the SOUL Guide key points.
