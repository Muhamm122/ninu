# Discord Login — Concrete Fallback Paths (When Automation Is Unattainable)

> Verified 2026-06-19 on Discord login flow. Cloud solver (SCTG, YesCaptcha) returns `ERROR_CAPTCHA_UNSOLVABLE` because Discord's hCaptcha binds the captcha solution to the browser fingerprint (IP+TLS+device+cookies) that solved it. Even a valid token is rejected by `/api/v9/auth/login` with `{"errors": {"captcha_key": {"_errors": [{"code": "CAPTCHA_INVALID"}]}}}`.

When the user asks for Discord login/signup from VPS, **do not start the automation**. Present the 3 paths below, ordered by speed. Let the user pick. This is the canonical 5-minute path; cloud-solver grinding wastes 30+ minutes for zero progress.

---

## Path A — QR Code Login (⭐ FASTEST, ~30 seconds)

Discord login page has a "Sign in with QR code" option (on desktop, look for the QR icon next to the password field; in mobile, the "Scan QR code" tab).

**Flow:**
1. Open `https://discord.com/login` in any browser (Playwright, CloakBrowser, or user's local browser)
2. Click the QR icon / "Sign in with another device" → Discord displays a unique QR
3. User opens Discord mobile app (already logged in) → tap Settings → "Scan QR Code" → scan
4. Desktop browser auto-redirects to `/channels/@me` with full session
5. Export cookies + localStorage tokens to `~/.hermes/credentials/discord/storage.json`

**Agent can fully automate steps 1, 2, 4, 5.** User only needs to scan with their phone (5 sec). After scan, the browser session is fully authenticated.

**Sample Playwright + CloakBrowser pattern:**
```python
from cloakbrowser import launch
import json

browser = launch(headless=True, humanize=True, proxy="http://user:pass@resi:port")
page = browser.new_page()
page.goto("https://discord.com/login", wait_until="networkidle")

# Click "Sign in with QR code" tab
qr_button = page.get_by_text("Sign in with a QR code")  # or use ref from snapshot
qr_button.click()

# Wait for QR to render
page.wait_for_selector('canvas[aria-label="QR Code"]', timeout=10000)

# Save QR screenshot for user (so they can scan from phone easily)
page.locator('canvas[aria-label="QR Code"]').screenshot(path="/tmp/discord_qr.png")

# Poll for session: after user scans, Discord sets localStorage tokens + redirects
import time
start = time.time()
while time.time() - start < 60:
    token = page.evaluate("() => localStorage.getItem('token')")
    if token and token.startswith('"') and len(token) > 50:
        print("[+] QR scan detected! Token:", token[:30] + "...")
        break
    time.sleep(2)

# Export full session
storage = {
    "cookies": page.context.cookies(),
    "localStorage": page.evaluate("() => Object.fromEntries(Object.entries(localStorage))"),
    "token": page.evaluate("() => localStorage.getItem('token')").strip('"'),
}
with open("/home/ubuntu/.hermes/credentials/discord/storage.json", "w") as f:
    json.dump(storage, f, indent=2)
```

**QR refreshes every ~60 seconds.** If the user takes too long, the page will show a new QR. Save fresh screenshot, user re-scans.

---

## Path B — Cookie Export from User's Own Browser (~2 minutes)

User logs into Discord in their own Chrome/Firefox/Edge on laptop or phone, then exports cookies. Fully remote (VPS gets the cookies, no browser automation needed).

**Steps for user:**
1. Open `https://discord.com` in a logged-in browser tab
2. Open DevTools: F12 (Windows/Linux) or Cmd+Opt+I (Mac)
3. Go to **Application** tab → **Storage** → **Cookies** → `https://discord.com`
4. Right-click → "Select all" → "Delete" (clear stale entries) — optional, skip if not stale
5. Install the "Cookie Editor" extension (Chrome/Edge/Firefox) → click icon on Discord tab → "Export" → "Header string" or "JSON"
6. Paste the export in chat

**OR for token-based export (cleaner):**
1. In Discord web, open DevTools → **Console** tab
2. Paste and run:
   ```js
   const token = localStorage.getItem('token').replace(/"/g, '');
   const userId = localStorage.getItem('user_id_cache').replace(/"/g, '');
   JSON.stringify({token, userId, source: "discord-web-cookie-export"})
   ```
3. Copy the JSON output and paste in chat

**VPS-side import pattern:**
```python
import json, requests
from pathlib import Path

# Save the user's pasted JSON
Path("/home/ubuntu/.hermes/credentials/discord/storage.json").write_text(json.dumps({
    "token": "<USER_TOKEN>",
    "userId": "<USER_ID>",
    "source": "manual-cookie-export"
}))

# Verify with a no-auth API call
headers = {"Authorization": f"<USER_TOKEN>"}  # Discord tokens are unprefixed
r = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=10)
print(r.status_code, r.json().get("username", "?"))
```

**Warning Discord displays:** "Hold up! ... Your account may be compromised." when a new device/IP logs in with just a token. This is informational only — login still works. User can dismiss from phone notification.

---

## Path C — Discord Desktop Client Token Dump (~1 minute)

User opens Discord desktop app → Settings → Advanced → enable **Developer Mode** → close settings → click the gear icon next to username → "Copy User Token" → paste in chat.

**Token alone is sufficient for ALL Discord API calls.** No need for cookies, hCaptcha, or password. Token = full account access from API.

**Limitation:** Discord periodically invalidates tokens flagged for "suspicious" use. A token from desktop app used 1 hour later from a different IP may trigger email verification. Mitigation: use the token quickly, or chain to Path A for fresh cookies.

**Sample usage:**
```python
import requests

TOKEN = "<USER_PASTED_TOKEN>"
headers = {"Authorization": TOKEN}

# Get user info
r = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
print(f"User: {r.json()['username']}#{r.json()['discriminator']}")

# List guilds
r = requests.get("https://discord.com/api/v9/users/@me/guilds", headers=headers)
print(f"Guilds: {len(r.json())}")

# Send message to channel
r = requests.post(
    f"https://discord.com/api/v9/channels/<CHANNEL_ID>/messages",
    headers=headers,
    json={"content": "Hello from VPS"},
)
```

---

## Cleanup Pattern (Mandatory, Run After All Paths)

When automation is aborted (fingerprint-bound, user chose manual path, etc.), always:

```bash
# Delete temporary credential files
rm -f /tmp/.dc_creds /tmp/.hcaptcha_solution /tmp/discord_qr.png

# Cancel any pending captcha solver tasks (avoid billing)
# SCTG: curl "https://api.sctg.xyz/res.php?key=$SCTG_KEY&action=get&id=$TASK_ID"
# Check response for ERROR_CAPTCHA_UNSOLVABLE — if so, no charge

# Close browser session
pkill -f "chrome.*discord" 2>/dev/null  # or use browser.close() in script
```

**Storage directory convention:** `~/.hermes/credentials/discord/`
- `storage.json` — current session (cookies + token + userId)
- `.last_login_attempt` — text file with timestamp + method used + outcome (for debugging)

**Permissions:** `chmod 600` on all files. Never echo token in chat logs.

---

## When Each Path Fails

| Failure | Diagnosis | Next move |
|---|---|---|
| QR scan: page just reloads, no session | QR expired (60s limit) | Re-screenshot, user re-scans |
| QR scan: shows "QR code invalid" | User scanned wrong QR (e.g. screenshot of older QR) | User re-scans, or pick Path B |
| Cookie import: 401 with "401: Unauthorized" | Token expired between user export and VPS import | Repeat Path B with fresh token |
| Token dump: "Invalid token" from API | Token was already invalidated (Discord forced logout) | Pick Path A (QR is most reliable for fresh) |
| All paths fail: 2FA / "verify it's you" | User account has 2FA enabled on new device | User must approve from phone, then repeat Path A |

---

## Discord API Endpoints Reference

| Endpoint | Purpose |
|---|---|
| `GET /api/v9/users/@me` | Verify token, get user info |
| `GET /api/v9/users/@me/guilds` | List joined guilds (server IDs) |
| `GET /api/v9/guilds/{guild.id}/channels` | List channels in a guild |
| `POST /api/v9/channels/{channel.id}/messages` | Send a message |
| `POST /api/v9/guilds/{guild.id}/members/{user.id}` | Join a guild (needs invite) |
| `GET /api/v9/guilds/{guild.id}/members/search?query=` | Search members |
| `POST /api/v9/invites/{code}` | Accept invite (returns new guild) |

**Rate limit headers:** `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`. Discord enforces 5 req/2s per route — back off on 429.

**Token format:** base64url, 3 segments (header.payload.signature), ~88 chars, no prefix (just `Authorization: <token>` not `Bearer <token>`).
