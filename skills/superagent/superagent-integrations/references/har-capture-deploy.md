# HAR Capture Suite — Deploy & Usage

Repo: `github.com/waguriagentic/HAR` — auto-capture network traffic from Chrome (CDP/DevTools Protocol) including cross-origin iframes and workers.

## Architecture

```
Chrome MV3 Extension (extension/) ←→ WebSocket (ws://127.0.0.1:18080)
                                  ↓
                      Electron Desktop App (desktop-app/)
                      ├── Main process (bridge.ts + SQLite)
                      ├── Preload (renderer bridge)
                      └── Renderer (React + Mantine + virtualized table)
```

## Install & Build

```bash
git clone https://github.com/waguriagentic/HAR /tmp/har-capture
cd /tmp/har-capture
npm install
npm run build:extension    # Chrome MV3 → extension/dist/ (38KB)
npm run build:desktop     # Electron → desktop-app/out/ (881KB)
```

## Patch Port & Auth

**Port** (shared/src/index.ts):
- Default: `9876`
- Change: `export const BRIDGE_PORT = 18080`

**Auth** (desktop-app/src/main/index.ts):
- Token: `vpnwaguri:waguri` → WebSocket auth
- `bridge.setToken(token)` → extension `connect` + `retry`

## Export

- **HAR 1.2** — standard HAR, open in Chrome DevTools
- **ZIP** — per-request JSON + summary + metadata

## Redaction

- Headers: `authorization`, `cookie`, `set-cookie`, `x-api-key`, `x-auth-token`
- Body: `password`, `secret`, `access_token`, `refresh_token`, `id_token`
- Values → `<redacted>` in exported HAR/ZIP