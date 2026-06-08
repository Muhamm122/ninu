# Airdrop Site API Discovery Pattern

Many airdrop sites (pimp.zone, etc.) expose REST APIs that are more reliable and faster than browser automation for checking status, getting stats, and registering.

## Pattern

1. **Navigate to the airdrop page in browser** — load the full SPA
2. **Check `window.performance.getEntriesByType('resource')`** — filter for paths containing `api`, `airdrop`, `register`, `stats`, `status`
3. **Call the API endpoints directly via `curl`** — often returns clean JSON without auth, or with simple session cookie

## pimp.zone Example (proven working)

```bash
# Airdrop stats (public, no auth)
curl -s 'https://pimp.zone/api/airdrop/stats'
# → {"poolBalance":15000000,"registrationCount":3000,"totalSlots":3000,"remainingSlots":0,...}

# Airdrop status (checks if current user is registered, needs auth)
curl -s 'https://pimp.zone/api/airdrop/status'
# → {"authenticated":false,"registered":false}

# Register (needs auth session)
curl -s -X POST 'https://pimp.zone/api/airdrop/register' -H 'Content-Type: application/json' -d '{}'
# → {"error":"Sign in first to register for the airdrop."}

# Auth check
curl -s 'https://pimp.zone/api/auth/me'
# → {"user":null}
```

## Why This Matters
- Browser snapshots of React SPAs are slow and brittle — API calls are instant
- Stats/status endpoints are often **unauthenticated** — free intel
- You can detect "pool full" / "0 slots remaining" in 1 second instead of loading the entire SPA
- Registration typically requires wallet signature or OAuth — that part needs browser

## General API Discovery Script

```javascript
// Run in browser console after page loads
const entries = performance.getEntriesByType('resource');
const apiCalls = entries
  .filter(e => e.name.includes('api') || e.name.includes('airdrop') || e.name.includes('register'))
  .map(e => e.name);
console.log(apiCalls);
```

## Tplus Waitlist Example (non-Web3)

```bash
# Found via browser: form submits to /api/waitlist
curl -s -X POST 'https://tplus.cx/api/waitlist' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}'
# → {"ok":true,"email":"user@example.com","joined_at":1780812120770}
```

The waitlist endpoint was discovered by reading the inline `<script>` that handles form submission — `fetch('/api/waitlist', {method:'POST', body: JSON.stringify({email})})`. Always check inline scripts for API endpoints before trying browser form submission.
