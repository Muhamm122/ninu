# Airdrop Research Pattern

Reusable workflow for investigating and participating in Web3 airdrops.

## Step 1: Page Recon

1. Navigate to the airdrop page in browser.
2. Dismiss onboarding dialogs (welcome modal, cookie banners).
3. Extract key info from page text: pool size, reward per wallet, registered count, max slots, deadline, referral code, wallet address for "grow the pool".

## Step 2: API Discovery

Use browser console to find API endpoints:
```javascript
const entries = performance.getEntriesByType('resource');
const apiCalls = entries.filter(e => e.name.includes('api') || e.name.includes('airdrop') || e.name.includes('register')).map(e => e.name);
JSON.stringify(apiCalls);
```

Common endpoint patterns:
- `GET /api/airdrop/stats` — pool balance, registration count, slots, wallet address, mint, deadline
- `GET /api/airdrop/status` — authenticated status, registration status
- `POST /api/airdrop/register` — register for airdrop (requires auth session)
- `POST /api/waitlist` — whitelist/waitlist signup (usually just email, no auth)
- `GET /api/auth/me` — check if logged in

## Step 3: API Inspection

```bash
# Stats (usually public, no auth)
curl -s 'https://DOMAIN/api/airdrop/stats' | python3 -m json.tool

# Status (tells if current session is registered)
curl -s 'https://DOMAIN/api/airdrop/status' | python3 -m json.tool

# Try register without auth (reveals auth requirement message)
curl -s -X POST 'https://DOMAIN/api/airdrop/register' -H 'Content-Type: application/json' -d '{}'
```

## Step 4: Wallet Preparation

Generate wallets for the target chain. See SKILL.md for chain-specific instructions.

For Solana:
```python
from solders.keypair import Keypair
import base58, json
wallets = []
for i in range(N):
    kp = Keypair()
    wallets.append({
        'id': i + 1,
        'public_key': str(kp.pubkey()),
        'secret_base58': base58.b58encode(bytes(kp)).decode()
    })
```

For EVM:
```python
from eth_account import Account
Account.enable_unaudited_hdwallet_features()
acct, mnemonic = Account.create_with_mnemonic(num_words=24)
```

## Step 5: Anti-Sybil Analysis

Before multi-wallet registration, analyze the anti-sybil rules:

| Rule Type | Common Implementation | Impact on Multi-Wallet |
|-----------|----------------------|----------------------|
| **1 per identity** | X handle, Telegram, email, Discord | Need N separate accounts |
| **1 per wallet** | Solana/EVM address check | Need N wallets (easy) |
| **Duplicate rejection** | At signup AND distribution | Both must pass |
| **KYC** | ID verification / OTP | Very hard to multi-wallet |
| **On-chain activity** | Must have tx history / balance | Need to fund each wallet |
| **Token snapshot** | Must hold token at snapshot block | Buy token per wallet |

**Decision framework**:
- If anti-sybil is identity-only (no KYC): multi-wallet is possible but each needs a unique identity account.
- If anti-sybil is wallet-only: easy — just generate N wallets.
- If both: need N identities × N wallets, and must avoid correlation patterns.
- If KYC required: single-wallet only, not worth the effort/ethics.

## Step 6: Pool Status Decision

```
remainingSlots > 0  →  Register immediately
remainingSlots == 0 AND pool can grow  →  Send tokens to grow pool wallet → creates new slots
remainingSlots == 0 AND pool fixed  →  Check for waitlist, follow socials for pool expansion announcements
registration closed  →  Skip, look for next airdrop
```

## Step 7: Registration Pattern

Most airdrops follow this flow:
1. **Sign in** to the platform (X OAuth, wallet connect, email+OTP)
2. **Connect wallet** (Solana: sign message, no gas; EVM: sign EIP-712 message)
3. **Register** (POST to /api/airdrop/register with session cookie)
4. **Optional social tasks** (follow, like, retweet, tag friends)
5. **Wait for distribution** (usually after deadline/closes)

### ⚠️ X OAuth from Datacenter IP — Non-Functional

Many airdrops require X/Twitter as the identity check. From a datacenter VPS:
- The X login form renders (email textbox, "Continue" button visible), but the **"Continue" button does nothing** when clicked — no network request, no DOM change
- This is different from a CAPTCHA block or error message — the form is **decorative**
- All X OAuth flows ("Continue with Google", "Continue with Apple") are similarly non-functional
- **Workarounds**:
  - Use residential proxy in browser → X login works
  - Use `x_tool.py` (requests-based) for X API operations without browser
  - If the airdrop accepts alternative auth (Telegram, email+OTP), use that instead
  - If X OAuth is mandatory, the user must complete this step on their device

## Step 7b: Browser Form → Curl Fallback

When a browser `click` on Submit doesn't produce visible feedback (no DOM change, no network call intercepted):

1. **Inspect inline `<script>` blocks** for the form handler — look for `form.addEventListener('submit', ...)` or `fetch('/api/...')` patterns.
   ```javascript
   // Find the waitlist handler script
   const scripts = Array.from(document.querySelectorAll('script:not([src])'));
   const handler = scripts.find(s => s.textContent.includes('waitlist'));
   handler.textContent  // Read the full handler code
   ```
2. **Extract the endpoint, method, headers, and body shape** from the JS source.
3. **Use `curl` directly** — faster, more reliable, bypasses browser rendering entirely.
4. **Pattern**: Most waitlist/whitelist forms POST JSON to `/api/waitlist` with `{ "email": "..." }`.

```bash
# After discovering endpoint from inline JS:
curl -s -X POST 'https://DOMAIN/api/waitlist' \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}'
# Success: {"ok":true,"email":"user@example.com","joined_at":...}
# Already joined: {"ok":true,"already_joined":true}
# Error: {"error":"..."}
```

**Why this works**: Browser form handlers often use `event.preventDefault()` + `fetch()` in inline scripts. The snapshot may not reflect the response. `performance.getEntriesByType('resource')` can miss calls if the page uses `XMLHttpRequest` or the handler hasn't fired yet. Reading the source JS is the most reliable discovery method.

**When to use this pattern**:
- Browser `click` on submit doesn't change the DOM or show feedback
- Form uses `fetch()` or `XMLHttpRequest` in an inline `<script>`
- Page is a simple waitlist/whitelist (email-only signup)
- You need to register multiple emails quickly

## Step 7c: Auto-OTP via IMAP (Email OTP Auth)

When the platform uses email OTP auth **and** you have IMAP access (Gmail App Password), you can automate the full login flow without asking the user for the code.

### Auto-OTP Flow

1. **Browser**: Open login dialog → enter email → click "Send OTP"
2. **IMAP**: Poll inbox for the OTP email (loop every 5s, max 90s)
3. **Parse**: Extract 6-digit code from email body with regex `\b(\d{6})\b`
4. **Input**: Type code digit-by-digit into the OTP fields
5. **Done**: Login succeeds without user intervention

### IMAP OTP Polling Script (Reusable)

```python
import imaplib, email, re, time

def poll_otp(email_addr, app_password, from_filter="privy.io", max_wait=90, seen_ids=None):
    """Poll IMAP for OTP from a specific sender. Returns 6-digit code or None.
    
    Args:
        email_addr: Gmail address
        app_password: Gmail App Password (not regular password)
        from_filter: Filter emails from this sender domain
        max_wait: Maximum seconds to wait
        seen_ids: Set of already-seen email IDs to skip (prevents returning stale OTPs)
    """
    if seen_ids is None:
        seen_ids = set()
    start = time.time()
    while time.time() - start < max_wait:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_addr, app_password)
        mail.select('INBOX')
        status, data = mail.search(None, f'(FROM "{from_filter}")')
        ids = data[0].split()
        for eid in reversed(ids):  # newest first
            eid_str = eid.decode()
            if eid_str in seen_ids:
                continue
            seen_ids.add(eid_str)
            status, msg_data = mail.fetch(eid, '(RFC822)')
            if status == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ('text/plain','text/html'):
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                otp = re.search(r'\b(\d{6})\b', body)
                if otp:
                    mail.logout()
                    return otp.group(1)
        mail.logout()
        time.sleep(5)
    return None
```

### When Auto-OTP Works vs Doesn't

| Condition | Auto-OTP | Manual |
|-----------|----------|--------|
| Have IMAP access + App Password | ✅ Fully automated | — |
| Only have browser, no IMAP | ❌ | Ask user for code |
| Gmail + 2-FA + App Password set | ✅ Works reliably | — |
| OTP expires in <30s | ⚠️ Tight — may need faster polling | Safer |
| Sender filter unknown | ⚠️ Poll `UNSEEN` recent emails instead | — |
| Multiple OTP emails (stale ones) | ✅ Use `seen_ids` set to skip old | — |

**Key insight**: Auto-OTP is most valuable for **Web3/Privy.io sites** which commonly use email OTP. With Gmail IMAP + App Password already configured (see captcha-bypass skill), the entire login flow can be automated without user involvement.

### OTP Timing Pitfalls
- ⚠️ **OTP expires fast** — typically 60–120 seconds for Privy.io (10 min for Vinci World). Poll ASAP.
- ⚠️ **Resend invalidates old code** — if you click "Resend", the previous code is dead.
- ⚠️ **Page navigation loses state** — if you navigate away, the OTP session may reset.
- ⚠️ **Ref IDs expire** — OTP digit fields may lose their ref IDs after a few seconds. Re-snapshot before typing.
- ⚠️ **Read NEWEST email only** — IMAP search returns all matching emails. Process in reverse order and track seen IDs.

## Case Study: pimp.zone (2026-06)

- **Token**: $PIMPZONE (mint: `DBF1Qcs9qpYFnrpJxmcFt2rNtSAE1eNHa6PrJEi9AKaU`)
- **Reward**: 5,000 per wallet
- **Pool**: 15,000,000 (3,000 slots)
- **Anti-sybil**: 1 per X handle, 1 per wallet, duplicate rejection at signup AND distribution
- **Status**: Full (3,000/3,000) — `remainingSlots: 0` in API response
- **Grow the pool**: Send $PIMPZONE to `DBvW3yVzUDY6aSWANKNPHmrQysZzHDNVa39buAosCBgq` — each token sent creates a new registration slot at distribution
- **Close**: 2026-06-17T23:59:59Z
- **Auth**: X, Telegram, or email+password (any works as identity check)
- **Referral**: `?ref=CODE` in URL
- **API discovery**: `performance.getEntriesByType('resource')` revealed `/api/airdrop/stats`, `/api/airdrop/status`, `/api/airdrop/register`, `/api/auth/me`
- **Key lesson**: Even when slots are full, check if the program supports "grow the pool" (dynamic slot creation via token deposits). Also check `isOpen` in API — pool can be full but still open to new deposits.

### pimp.zone Auth Flow (Solana Nonce-Based)

pimp.zone uses Solana wallet nonce-based auth. The full flow:

```
1. POST /api/auth/nonce  {wallet: base58_pubkey}
   → {message: "Sign in to pimp.zone\n\nNonce: XXX\nTimestamp: YYY", nonce: "XXX", expiresAt: "..."}

2. Sign the FULL message string (not just nonce) with Solana keypair
   → signature must be base58-encoded (NOT base64, NOT hex)

3. POST /api/auth/login  {wallet, signature: base58(sig_bytes), nonce}
   → {user: {...}} on success
   → {"error": "Invalid signature"} if encoding is wrong
   → {"error": "Signups from your region aren't supported..."} if IP is blocked
```

**Region block**: pimp.zone blocks signups from certain regions (e.g., Singapore). The check is IP-based at the middleware level — `X-Forwarded-For` and `CF-IPCountry` headers are ignored. WARP proxy also exits from nearest region (SG for AWS SG), so it doesn't help. Only residential proxy from allowed region (US/EU) works.

**Signature encoding discovery**: The frontend code (`6ce4e3c0f7cd9598.js` chunk) shows:
```javascript
let o = new TextEncoder().encode(n),  // encode message to bytes
    d = await t(o),                    // signMessage(bytes)
    c = tR.default.encode(d);          // encode signature — this is base58!
```
The `tR.default.encode` is bs58's `encode()` function. Sending base64 or hex results in "Invalid signature".

**Python implementation**:
```python
import base58, json, subprocess
from solders.keypair import Keypair

# Load wallet from JSON (32-byte seed array)
with open('.sol_wallets.json') as f:
    wallets = json.load(f)
kp = Keypair.from_seed(bytes(wallets[0]['secret_key']))

# Get nonce
r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://pimp.zone/api/auth/nonce',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps({'wallet': str(kp.pubkey())})],
    capture_output=True, text=True)
data = json.loads(r.stdout)

# Sign and login
sig = kp.sign_message(data['message'].encode('utf-8'))
sig_b58 = base58.b58encode(sig.to_bytes()).decode()

r2 = subprocess.run(['curl', '-s', '-X', 'POST', 'https://pimp.zone/api/auth/login',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps({'wallet': str(kp.pubkey()), 'signature': sig_b58, 'nonce': data['nonce']})],
    capture_output=True, text=True)
print(r2.stdout)
```

## Case Study: Tplus (2026-06)

- **What**: Prime Exchange — CLOB in TEE (Trusted Execution Environment), decentralized, composable with onchain liquidity
- **URL**: https://tplus.cx/
- **Waitlist**: Email-only, no auth required
- **API**: `POST /api/waitlist` with `{ "email": "..." }`
- **Registration method**: Browser form click didn't show feedback. Inspected inline `<script>` → found `fetch('/api/waitlist', ...)` handler. Switched to curl: instant success.
- **Response**: `{"ok":true,"email":"...","joined_at":1740000000000}`
- **Multiple emails**: Second email registered just as fast — no rate limit, no CAPTCHA
- **X**: @Tplus_cx

## Case Study: Vinci World (2026-06)

- **What**: Web3 world/platform incubated by Renaiss. Genesis SBT for early registrants.
- **URL**: https://vinciworld.xyz
- **Auth**: Privy.io (email OTP, Google OAuth, wallet connect — MetaMask, Binance, etc.)
- **Registration flow**: Login → Join waitlist with username → "You're on the list!"
- **Key technique**: Auto-OTP via IMAP polling (see Step 7c above) — fully automated login without asking user for the code.

### Vinci World DOM Structure (for browser automation)

- Login button: `button "Open login panel"` → opens dialog
- Dialog: `dialog "Log in to Vinci World"` with email textbox + "Send OTP" button
- OTP view: 6 separate `textbox "Digit N of 6"` fields (auto-advances)
- Post-login: `textbox "@vinciworld"` for username + `button "Join waitlist"`
- Success text: `"You're on the list!"`
- Auth provider: Privy.io (email from `no-reply@privy.io`, subject: "Your login code for Renaiss")
- OTP expiry: 10 minutes (generous — most Privy.io sites use 10 min)

### Full Automation Sequence (Vinci World)

```
1. Navigate to vinciworld.xyz
2. Click "Open login panel"
3. Type email in textbox → click "Send OTP"
4. Run poll_otp() with from_filter="privy.io" → get code in ~10s
5. Type 6 digits into separate "Digit N of 6" fields
6. Page auto-submits → waitlist form appears
7. Type desired username → click "Join waitlist"
8. Verify: page shows "You're on the list!"
```

Total time: ~15 seconds (vs 2+ minutes if waiting for user to check email manually).

## Case Study: DOR Airdrop (2026-06)

- **Token**: $DOR, pool 60,000 (~$3,000), 5 winners + top 20 referrers
- **Bot**: @DORAirdropBot on Telegram, referral: `?start=ref_5672126626`
- **Tasks**: Join TG group + channel (mandatory), Follow @dormanager06 + RT pinned (mandatory), Join Discord (optional), Follow @AirdropDet + RT (optional), Join @AirdropDetective (optional)
- **Submission flow**: Math captcha → click task buttons → Twitter profile link → Discord link (or skip) → @AirdropDet Done/Yes → email → BEP20 wallet
- **Key technique**: Fully automated via Telethon — math captcha solve (45+36=81), sequential button clicks with sleep between, skip Discord (no account), submit X profile link as text, submit email and EVM wallet
- **Bot button pattern**: 7 rows of single-column buttons. Click each button to trigger verification → bot asks for proof (profile link, etc.) → submit as text message → bot advances to next task
- **Referral reward**: Top 20 referrers share 20,000 DOR ($1,000). 1st: 3000 DOR
- **X follow executed**: Used x-actions `airdrop_follow('dormanager06')` and `airdrop_follow('AirdropDet')` — API-based, no browser needed

## Step 7f: Website WL Form with Toggle-Done Checkboxes

Some airdrop/waitlist sites use a **self-reported task completion** model where:

1. The form has input fields (X username, EVM wallet, etc.) — these may be validated server-side
2. Each task has a **toggle-done checkbox** (CSS class `.task-check`) + a **go button** ("FOLLOW", "LIKE + RT", "COMMENT") that opens the social link
3. Clicking the checkbox marks the task as done — **no actual verification** that you followed/liked
4. A **progress bar** tracks completion (e.g., 0% → 40% per verified field → 100% when all toggles checked)
5. The submit button unlocks at 100% and fires a `fetch('/api/apply', ...)` POST

### Automation Flow

```
1. Navigate to the apply page
2. Fill X username + EVM wallet fields (these MAY be validated server-side — wait for ✓)
3. For each social task:
   a. Optionally do the task for real (via x_auto API: airdrop_follow, like, retweet)
   b. Click the .task-check button to mark done (even if you already did it via API)
4. Wait for progress bar to reach 100%
5. Click submit button → POST /api/apply with {xUser, wallet, followed, liked, commented, referredBy}
6. Check for success alert ("APPLICATION RECEIVED")
```

### Key Observation

- The Go buttons ("FOLLOW", "LIKE + RT") open X in a new tab — they don't verify anything
- The checkboxes are self-reported — anyone can toggle them without doing the tasks
- BUT: some sites add server-side follow verification AFTER submission (check if @user follows @them). If they do, the airdrop may be revoked later
- **Recommendation**: Always actually do the social tasks via API AND toggle the checkboxes. This covers both immediate form completion AND potential post-submission audits.

### DOM Pattern (Dumbois-style)

```html
<button class="task-check"></button>    <!-- toggle-done checkbox -->
<button class="btn btn--x task-go">FOLLOW</button>  <!-- opens social link -->
```

Interact with JS:
```javascript
// Toggle all task checkboxes
document.querySelectorAll('.task-check').forEach(c => c.click());

// Check submission payload by intercepting fetch
const origFetch = window.fetch;
window.__fetchLog = [];
window.fetch = function(...args) {
    window.__fetchLog.push({url: args[0], opts: args[1]});
    return origFetch.apply(this, args);
};
// Then click submit and read window.__fetchLog
```

## Case Study: Dumbois WL (2026-06)

- **What**: NFT/ WL — "797 dumbois" collection, apply-to-allowlist model
- **URL**: https://dumbois.xyz → /apply page
- **Auth**: None — just X username + EVM wallet + self-reported task toggles
- **Tasks**: Follow @thedumbois, Like+RT pinned tweet, Comment "I am Dumb" + tag 2 friends
- **Form pattern**: Toggle-done checkboxes (`.task-check` class) — 3 tasks, each with a go button + toggle
- **Progress**: 40% (username+wallet verified) → 100% (all 3 task toggles checked)
- **Submission**: `POST /api/apply` with `{xUser, wallet, followed, liked, commented, referredBy}`
- **Result**: "APPLICATION RECEIVED" alert with referral link
- **X follow**: Executed via `airdrop_follow('thedumbois')` from x_auto.py — API-based
- **Key technique**: Click all `.task-check` elements in JS to mark tasks done, then submit. Username and wallet were server-validated (showed "✓ dumb"), but task completions were self-reported.
- **Referral**: Post-submission referral link for recruiting others to "the mold"

## X API Deprecation Notes (2026-06)

⚠️ **v1.1 REST API is fully dead** — `api.x.com/1.1/statuses/user_timeline.json` returns `{"errors":[{"code":34,"message":"Sorry, that page does not exist"}]}` (404, not 401). This is a new change from earlier behavior (was 401/unauthorized). Do NOT attempt v1.1 endpoints.

⚠️ **GraphQL QID discovery from HTML blocked** — `requests.get('https://x.com', headers=api_headers)` returns 401 even with valid auth tokens. The HTML page requires browser rendering to get JS bundle URLs. Alternative: Use Playwright + CDP to intercept the JS bundles, or use cached/known QIDs.

⚠️ **Telegram session files** — Multiple session files may exist. Always check all of them:
- `/home/ubuntu/.hermes/tg_user.session` (primary — works)
- `/home/ubuntu/.hermes/tg-user-session.session`
- `/home/ubuntu/adib_session.session` (may be stale/unauthorized)
- Always call `await client.is_user_authorized()` after connecting — don't assume the session is valid
