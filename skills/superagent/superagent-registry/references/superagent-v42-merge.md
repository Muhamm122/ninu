# Superagent v4.2 — Merge Notes (2026-06-13)

## What's New in v4.2 (vs v4.0)

### 19 New Skills (m30-m48)
| ID | Name | Domain |
|----|------|--------|
| m30 | Client Revenue Engine | Bulk gig automation |
| m31 | Airdrop Intelligence | Eligibility, sybil, claim calendar |
| m32 | CTF / Whitehat Toolkit | Bug bounty, crypto challenges |
| m33 | Pre-TGE Alpha Radar | Early airdrop detection |
| m34 | Farming Portfolio & ROI Optimizer | Yield optimization |
| m35 | Auto Guide Studio | Tutorial generation |
| m36 | Tokenomics & Unlock Pressure Engine | Vesting analysis |
| m37 | Anti-Scam Sentinel | Phishing/scam detection |
| m38 | Contract-Change Watcher | Proxy upgrade monitoring |
| m39 | Community Intelligence | Social sentiment |
| m40 | Omni-Repurpose Engine | Multi-platform content |
| m41 | Video Script-to-Screen Pipeline | Video production |
| m42 | Hook A/B Lab | Headline testing |
| m43 | CTF Web Exploitation | SQLi, SSTI, SSRF, etc |
| m44 | CTF Binary Exploitation | pwn, ROP, heap |
| m45 | CTF Reverse Engineering | angr, Ghidra |
| m46 | CTF Cryptography | RSA, padding oracle |
| m47 | CTF Forensics & Stego | pcap, memory dump |
| m48 | CTF Prompt-Injection / LLM Red-Teaming | Gandalf, jailbreak |

### New Tools (21 scripts)
alpha_radar.py, api_harvester.py, claim_watcher.py, community_intel.py,
contract_watch.py, cost_ledger.py, ctf.py, dryrun.py, exit_planner.py,
farm_roi.py, guide_studio.py, hook_lab.py, repurpose.py, revenue_engine.py,
router_log.py, rugcheck.py, scam_sentinel.py, secret_tripwire.py,
sybil_audit.py, unlock_engine.py, video_pipeline.py

### CTF Module (21 files)
Full CTF framework with coordinator, sandbox, swarm solver, templates.

### Rebuilt HerMES Package
- pyproject.toml (installable package)
- requirements-dev.txt
- tests/ (8 test files)

### New Core Docs
CHANGELOG.md, CONTRIBUTORS.md, DEPLOY.md, HEARTBEAT.md, INDEX.md,
README.md, REVIEW.md, STANDARD.md, TIME.md, panduan.md (Indonesian)

## Skill Name Collision Warning
Both `superagent/` and `superagent-v4.2/` contain skills with identical names
(e.g., `superagent-infra`). The system refuses to load either when names collide.
Use full paths or rename to resolve.

## Full Index
See `superagent-v4.2/SKILL_INDEX.md` for complete 319-file inventory.
