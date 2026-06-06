# SUPERAGENT v4.0 — File Manifest

## Core Files (~/.hermes/)
| File | Purpose |
|------|---------|
| AGENTS.md | Core brain, skill router, core rules R1-R10 |
| SOUL.md | Persona, tone, boundaries, operational rails |
| IDENTITY.md | Name (SUPERAGENT/IRONCLAW), character modes, response tiers |
| USER.md | Operator profile (adib), stack, trigger phrases |
| MEMORY.md | Long-term context, locked decisions, preferences |
| HEARTBEAT.md | Session continuity, time refresh, token discipline |
| TIME.md | 5-layer time awareness architecture |
| TOOLS.md | Agent-side vs operator-side execution |
| panduan.md | Operator usage guide with real examples |
| INDEX.md | Full index of all files and skills |
| README.md | Project overview and quick start |
| DEPLOY.md | Deployment guide |
| CHANGELOG.md | Version history |
| CONTRIBUTORS.md | Community credits |
| QUICKREF.md | Quick reference for providers, skills, commands |

## Skills (~/.hermes/skills/superagent/)
23 skills installed:
- superagent-registry (m0) — skill registry + reflection loop
- superagent-monetization (m1) — monetization, business ops
- superagent-infra (m2) — VPS, deployment, docker, systemd
- superagent-content (m3) — content creation, copywriting
- superagent-bots (m4) — Telegram bots, automation
- superagent-data (m5) — data handling, spreadsheets
- superagent-integrations (m6) — API, payments, webhooks
- superagent-ai-providers (m7) — multi-LLM, model registry
- superagent-documents (m8) — docx, xlsx, pptx, pdf
- superagent-frontend (m9) — landing pages, Web3 UI
- superagent-web3 (m10) — Web3 ops, on-chain, airdrop
- superagent-security (m11) — security audit, secret scan
- superagent-batch (m12) — batch operations, parallel exec
- superagent-nft (m13) — universal NFT minter
- superagent-briefing (m14) — daily briefing, alerts
- superagent-watchdog (m15) — watchdog, vault, triage
- superagent-software-eng (m16) — backend, DB, testing
- superagent-power-pack (m17) — planner, swarm, dashboard
- superagent-self-audit (x1) — self-audit, refinement
- superagent-strategy (x2) — deep decomposition, strategy
- superagent-debug (x3) — debug, fault diagnosis
- superagent-self-improve (x4) — self-improvement loop
- hermes-crypto-agent — deep crypto layer (H1-H10 dispatch)

## Hermes Crypto References (~/.hermes/skills/superagent/hermes-crypto/references/)
15 reference files:
- airdrop_automation.md, bridge.md, browser.md, contract_read.md, contract_write.md
- defi.md, deploy.md, governor.md, monitoring.md, nft.md
- security.md, sniping.md, swap.md, wallets.md, web3_connect.md

## Hermes Crypto Scripts (~/.hermes/skills/superagent/hermes-crypto/scripts/)
15 Python scripts:
- airdrop_runner.py, bridge_engine.py, browser_engine.py, contract_reader.py
- contract_writer.py, deploy_engine.py, governor.py, mev.py, monitoring.py
- monitoring_advanced.py, nft_engine.py, swap_engine.py, wallet_manager.py, web3_connect.py

## Tools (~/.hermes/skills/superagent/tools/)
18 Python tools:
- alerts.py, automation.py, backtest.py, briefing.py, dashboard.py, explain.py
- memory_engine.py, model_registry.py, multimodal.py, planner.py, reflection.py
- skill_forge.py, skill_integrity.py, swarm.py, triage.py, vault.py, voice.py, watchdog.py

## Services
| Service | Port | Manager | Status |
|---------|------|---------|--------|
| Hermes Gateway | - | systemd | running |
| FreeLLMAPI | 3001 | systemd | running |
| OpenCode Free Proxy | 19912 | PM2 | running |
