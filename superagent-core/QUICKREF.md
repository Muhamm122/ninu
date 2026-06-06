# HERMES QUICK REFERENCE

## Custom Providers

| Name | Base URL | Model | Auth |
|------|----------|-------|------|
| `ninu` | https://llm.g4rrzx.my.id/v1 | anthropic/claude-opus-4-7 | API Key |
| `mimu` | https://cc.freemodel.dev/v1 | claude-sonnet-4-6 | API Key |
| `freellmapi` | http://127.0.0.1:3001/v1 | auto (router) | Unified Key |
| `chatbai` | https://chat.b.ai/chat | auto | API Key |
| `opencode_free` | http://127.0.0.1:19912/v1 | deepseek-v4-flash-free | No key needed |

## FreeLLMAPI Local Proxy
- Port: 3001
- Dashboard: http://127.0.0.1:3001
- Admin: admin@freellmapi.local / admin123
- Unified Key: freellmapi-3f3ae86521eba8c49ec39d2380a632833b544bd927b3fde0
- Keys: OpenRouter, chat.b.ai (x2), opencode-free-proxy

## OpenCode Free Proxy
- Port: 19912
- Upstream: https://opencode.ai/zen/v1
- PM2: opencode-free-proxy
- Free models: deepseek-v4-flash-free, mimo-v2.5-free, minimax-m3-free, nemotron-3-super-free

## Superagent Skills (23)
Directory: ~/.hermes/skills/superagent/

### On-Demand Skills
| ID | Name | Trigger |
|----|------|---------|
| m1 | monetization | monetize, pricing, jual, cuan |
| m2 | infra | VPS, deploy, SSH, docker, systemd |
| m3 | content | viral, hook, caption, konten |
| m4 | bots | telegram bot, cron, webhook, automate |
| m5 | data | spreadsheet, excel, csv, dataset |
| m6 | integrations | API, REST, webhook, integrasi |
| m7 | ai-providers | LLM, prompt, agent, add model |
| m8 | documents | PDF, DOCX, XLSX, PPTX |
| m9 | frontend | landing page, react, tailwind |
| m10 | web3 | wallet, airdrop, on-chain, crypto |
| m11 | security | audit, vulnerability, exploit |
| m12 | batch | batch, parallel, bulk, mass |
| m13 | NFT | mint, opensea, NFT, claim |
| m14 | briefing | briefing, ringkasan harian, alert |
| m15 | watchdog | watchdog, triage, vault, voice |
| m16 | software-eng | coding, backend, API, testing |
| m17 | power-pack | planner, swarm, dashboard, voice |

### Crypto H-Skill Dispatch
| H | Topic | Reference |
|---|-------|-----------|
| H1 | Swap & Sell | swap.md |
| H2 | Bridge | bridge.md |
| H3 | DeFi | defi.md |
| H4 | Sniping | sniping.md |
| H5 | Monitoring | monitoring.md |
| H6 | NFT | nft.md |
| H7 | Web3 Connect | web3_connect.md |
| H8 | Browser dApp | browser.md |
| H9 | Contract Read/Write | contract_read.md, contract_write.md |
| H10 | Deploy | deploy.md |

### Audit & Strategy (x-skills)
| ID | Name | Trigger |
|----|------|---------|
| x1 | self-audit | improve system, self-audit |
| x2 | strategy | strategy, architecture, decompose |
| x3 | debug | error, bug, debug, gagal |
| x4 | self-improve | self improve, belajar, upgrade |

## Commands

```bash
# Switch model per session
hermes -m opencode_free/deepseek-v4-flash-free

# FreeLLMAPI health
curl http://127.0.0.1:3001/api/ping

# OpenCode proxy health
curl http://127.0.0.1:19912/health

# PM2 status
pm2 list

# FreeLLMAPI keys
curl -s http://127.0.0.1:3001/api/keys -H "Authorization: Bearer <token>"
```
