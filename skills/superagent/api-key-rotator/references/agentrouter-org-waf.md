# agentrouter.org — Aliyun WAF + Key Validation Diagnostic

**Verified 2026-06-29.** Probe pattern for the OpenAI-compatible endpoint at
`https://agentrouter.org/v1`. Distinct from Kimchi/CastAI: WAF is Aliyun slide
captcha, not Cloudflare.

## Layered Defense Pattern

The endpoint has TWO independent block layers:

| Layer | Trigger | Symptom | Bypass |
|-------|---------|---------|--------|
| 1. Aliyun WAF (slide captcha) | VPS IP / non-browser UA | HTTP 200 with HTML challenge page (`<meta name="aliyun_waf_aa" content="...">`) | Tor exit node (resets IP reputation) |
| 2. Auth layer (key check) | Invalid/blacklisted key | HTTP 401 `{"error":{"message":"unauthorized client detected, contact support for assistance at https://discord.gg/aYq5B4RW3"},"message":"UNAUTHENTICATED","success":false,"type":"unauthorized_client_error"}` | Need valid, activated key |

**Both layers can return 200 OK with HTML/JSON body — read the body, not just the status code.**

## Direct Probe (VPS, no proxy)

```python
import urllib.request, json
key = "<user_key>"
url = "https://agentrouter.org/v1/models"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
r = urllib.request.urlopen(req, timeout=20)
# → r.status == 200 but body is HTML Aliyun challenge page, NOT JSON
# → byte 0 is `<`, not `{` — that's the giveaway
```

The HTML contains `<meta name="aliyun_waf_aa">` and `<meta name="aliyun_waf_bb">`
markers. Page title is "Verification". The captcha JS is served from
`g.alicdn.com/captcha-frontend/dynamicJS/...` and requires slide interaction.

**Headless Playwright with `wait_until=networkidle` does NOT solve it** — the
WAF JS challenge expects user gesture (drag slider) and headless browsers
complete the network requests without satisfying the captcha logic. Result:
still served the challenge page.

## Tor Bypass (definitive test for layer 2)

Use Tor SOCKS5 (`127.0.0.1:9050`) to bypass the WAF IP filter:

```python
import socket, socks, urllib.request
socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
socket.socket = socks.socksocket

# PySocks required: pip install PySocks (already in hermes venv)
req = urllib.request.Request("https://agentrouter.org/v1/models",
    headers={"Authorization": f"Bearer {key}"})
r = urllib.request.urlopen(req, timeout=30)
body = r.read()
# If body[0] == "{": real API response → key issue, not WAF
# If body[0] == "<": still WAF (Tor exit is also flagged)
```

**Tested response on invalid key via Tor** (2026-06-29):
```json
{
  "error": {
    "message": "unauthorized client detected, contact support for assistance at https://discord.gg/aYq5B4RW3",
    "param": ""
  },
  "message": "UNAUTHENTICATED",
  "success": false,
  "type": "unauthorized_client_error"
}
```
HTTP 401, all models return the same error (gpt-4o-mini, gpt-3.5-turbo, claude-3-haiku, etc.).

## Diagnostic Decision Tree

```
probe /v1/models from VPS
    │
    ├─ body[0] == '<' (HTML) ──→ LAYER 1 WAF, can't bypass from VPS
    │                              │
    │                              ├─ retry via Tor ──→ body[0] == '<' → WAF also blocks Tor exit, give up
    │                              │                   └─ body[0] == '{' → WAF bypassed, see layer 2
    │                              └─ retry via real browser → may work if user solves slide
    │
    └─ body[0] == '{' ──→ LAYER 2 auth check
                              │
                              ├─ HTTP 200 with data[] ──→ key works
                              ├─ HTTP 401 "unauthorized_client_error" → key FLAGGED
                              │     ├─ Key format wrong? (51-char `sk-...` pattern)
                              │     ├─ Key needs activation on dashboard?
                              │     └─ Account banned → support at discord.gg/aYq5B4RW3
                              └─ HTTP 401 "Invalid API Key" → key expired/typo
```

## Provider Quirks

- **Registration** appears Discord-gated (the error message references
  `discord.gg/aYq5B4RW3`). Standard signup form may require Discord OAuth.
- **Key format** matches generic `sk-...` (51 chars in tested key). Same prefix
  as OpenRouter/sk_live style, but DIFFERENT service namespace.
- **Models advertised** (via Tor after bypass): gpt-4o-mini, gpt-3.5-turbo,
  gpt-4, claude-3-haiku-20240307, "auto" — standard OpenAI-compatible model
  names. Cannot confirm catalog completeness until a valid key is tested.
- **Error code 400 "content-blocked"** appears on chat completions with valid
  auth but flagged content. Different error family from key invalid — handled
  by content filter, not auth.

## Reusable Lessons (apply to ANY new provider behind aggressive WAF)

1. **Don't trust HTTP 200 alone** — always inspect body[:1]. `<` = WAF page,
   `{` = real API. False 200s waste time on a phantom "it works" before the
   real failure.
2. **Tor is the fastest WAF disambiguator** — `torsocks curl` (or Python
   `socks.set_default_proxy`) gives you a residential-IP request in 1 sec.
   If Tor returns real JSON, the issue is WAF not auth. If Tor also returns
   HTML, the WAF blocks Tor exit nodes too (rare).
3. **401 message tells you where to escalate** — the
   "contact support at <discord_url>" hint is a vendor-controlled message;
   it points to the actual human support channel, not a generic error.
4. **Slide captcha vs JS challenge vs Cloudflare Turnstile** — these are all
   different anti-bot mechanisms requiring different bypasses:
   - Aliyun slide → headless browsers can render but not solve (needs gesture)
   - CF Turnstile → FlareSolverr or ohmycaptcha can auto-solve
   - JS-only challenge (Aliyun JS challenge) → wait for JS execution, no
     gesture required (but Playwright may not wait long enough by default)
5. **Don't add to provider pool when key validation fails** — a 401
   `unauthorized_client_error` should halt registration. Adding a known-dead
   key to the pool pollutes the rotation chain with keys that fail on first
   try, wasting rotation cycles.
