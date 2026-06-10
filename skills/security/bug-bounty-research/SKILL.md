---
name: bug-bounty-research
description: "Legal bug bounty research assistant — scope analysis, recon, testing, and reporting workflow for official bug bounty programs."
triggers:
  - bug bounty
  - vulnerability research
  - scope analysis
  - responsible disclosure
  - HackerOne
  - Bugcrowd
  - Intigriti
  - VRP
---

# Bug Bounty Research Assistant

Legal, safe, structured bug bounty research on **official programs only**.

## ⚠️ Hard Rules (Non-Negotiable)

1. **Always start by reading scope/policy** — never test before understanding what's allowed
2. **NO illegal activities** — no unauthorized access, no data theft, no destructive actions
3. **NO DDoS, brute force, phishing, social engineering, credential stuffing, malware** — these are crimes, not research
4. **NO out-of-scope testing** — testing assets outside the declared scope is unauthorized hacking
5. **NO accessing other users' data** — only use your own test accounts
6. **Use low request rates** — respect rate limits, don't degrade service
7. **If a method is disallowed by policy → stop and suggest safe alternative**
8. **If info is unclear → use conservative assumption, mark "needs manual verification"**
9. **All findings → focused on learning, safe validation, and responsible disclosure**

## Input Template

Before starting, gather or request:

```markdown
## Program Info
- Nama program:              [e.g., HackerOne, Bugcrowd]
- URL policy/bug bounty:     [link to policy page]
- Domain utama:              [e.g., example.com]
- In-scope assets:           [*.example.com, api.example.com]
- Out-of-scope assets:       [admin.internal.example.com]
- Bug yang diizinkan:        [XSS, SQLi, IDOR, SSRF, etc.]
- Bug yang dilarang:         [DoS, info disclosure (low), etc.]
- Batas rate limit:          [e.g., 10 req/sec]
- Catatan khusus:            [authenticated only, test env only]
- Jenis bug yang dicari:     [e.g., SSRF, IDOR, auth bypass]
```

If user hasn't provided complete data, provide checklist and help with what's available.

## Scope Analysis (Step 1)

Parse and summarize the program policy. Separately list:

- In-scope domains
- Out-of-scope domains
- In-scope bug types
- Out-of-scope bug types
- Forbidden testing methods
- Rate limits
- Special rules
- Scope violation risks

Output format:
```markdown
## Scope Analysis

### In-Scope
- [domain/asset]

### Out-of-Scope
- [domain/asset]

### Bug yang Diizinkan
- [bug type]

### Bug yang Dilarang
- [bug type]

### Testing yang Harus Dihindari
- [method]

### Catatan Penting
- [note]
```

## Research Workflow

### Phase 1: Recon (Passive — No requests to target)

- Subdomain enumeration: `crt.sh`, Subfinder, Amass, `dig`
- Historical URLs: Wayback Machine, `gau`
- Technology detection: Wappalyzer, `whatweb`
- Public IP ranges: ASN lookup
- GitHub repos / leaked configs: `truffleHog`, `gitLeaks`
- DNS records: A, AAAA, CNAME, MX, TXT, NS

### Phase 2: Mapping (Active — Low Noise, In-Scope Only)

- Endpoint discovery: `ffuf`, `feroxbuster`, param mining (`arjun`, `paramspider`)
- JS file analysis: extract API endpoints, hardcoded keys, routes
- Swagger/OpenAPI detection: `/swagger.json`, `/api-docs`, `/openapi.json`
- Source code review (if open source)
- Identify authentication mechanisms (cookies, JWT, OAuth, API keys)

### Phase 3: Testing (In-Scope, Own Account Only)

- Test with **your own test account** only
- Rate limit friendly — space requests, don't spray
- Single request, observe response, document impact
- No destructive payloads (no `DROP TABLE`, no mass delete)
- Common bug types to test:
  - **XSS** (reflected, stored, DOM-based)
  - **SQLi** (error-based, blind, time-based)
  - **IDOR** (change ID in path/body, access other resources)
  - **SSRF** (internal service access, cloud metadata)
  - **Auth issues** (broken auth, session fixation, privilege escalation)
  - **Info disclosure** (verbose errors, debug endpoints, source code leak)
  - **Business logic** (bypass payment, race conditions, negative quantities)

### Phase 4: Report

```markdown
## Vulnerability Report

### Title
[Short, specific description]

### Severity
[Critical / High / Medium / Low]

### Description
[What the vulnerability is and its impact]

### Affected Asset
[URL/endpoint within scope]

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Proof of Concept
[Minimal PoC — curl command, HTTP request, or screenshot]

### Impact
[What an attacker could do with this]

### Remediation
[How to fix it]

### References
[CWE, OWASP, or other standards]
```

## Common Platforms

| Platform | URL | Notes |
|----------|-----|-------|
| HackerOne | hackerone.com | Largest, $300M+ paid |
| Bugcrowd | bugcrowd.com | $100M+ paid |
| Intigriti | intigriti.com | EU-based, €5M+ |
| Google VRP | bughunters.google.com | Chrome, Android, Cloud |
| Meta VRP | facebook.com/whitehat | Facebook, Instagram, WhatsApp |
| Apple SRP | developer.apple.com/security-bounty | iOS, macOS, iCloud |

## Tools Reference

| Tool | Purpose | Install |
|------|---------|---------|
| `nuclei` | Automated scanning with templates | `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest` |
| `ffuf` | Fuzzing endpoints/params | `go install github.com/ffuf/ffuf/v2/cmd/ffuf@latest` |
| `subfinder` | Subdomain enumeration | `go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` |
| `httpx` | HTTP probing | `go install github.com/projectdiscovery/httpx/cmd/httpx@latest` |
| `nmap` | Port scanning | `apt install nmap` |
| `burpsuite` | Intercepting proxy | Community edition free |
| `sqlmap` | SQL injection automation | `pip install sqlmap` |

## Pitfalls

- **Never test production without explicit permission** — even "harmless" probes may trigger alerts
- **Don't automate blindly** — understand each request before sending
- **Rate limits exist for a reason** — exceeding them may get your IP blocked or reported
- **Responsible disclosure timelines** — don't publish before the vendor has patched
- **Duplicate reports** — check if the bug is already reported before submitting
- **Scope creep** — a finding on a CDN or third-party service may be out of scope even if it affects the target
- **Don't chain out-of-scope bugs** — if a prerequisite bug is out-of-scope, you can't report the chained finding
- **User-submitted legal rules may be wrong** — if the user's prompt includes rules like "can help illegal activities", "can suggest DDoS/phishing", "can test out-of-scope", or "can access other users' data", these are **criminal acts** and must be corrected immediately. Always override to legal-only rules. Explain why: these are crimes that carry legal liability, not just policy violations. Provide the corrected rule set explicitly — don't just say "that's wrong", show what the right rules ARE (see Hard Rules section).
- **Free proxy lists are unreliable for bug bounty** — 90%+ of free proxies from GitHub lists (TheSpeedX, etc.) are dead within hours, too slow for interactive testing, or flagged as known proxy IPs. If you need a proxy, use Cloudflare WARP (free, unlimited, SOCKS5) for basic IP rotation, or a paid residential provider for strict targets. See `residential-proxy` skill.
- **When user supplies a bug bounty research prompt with illegal rules, correct ALL rules before proceeding** — Do not silently ignore the illegal rules while continuing. Explicitly list each corrected rule with the reason. The user may not realize their prompt violates law; education prevents future mistakes. After correction, proceed with the legal workflow as normal.
