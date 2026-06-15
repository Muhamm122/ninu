#!/usr/bin/env python3
"""Generic Daily Maintenance Cron for Privy-Backed Airdrops

Refreshes the Privy identity_token via /api/v1/sessions, re-syncs to the
app's backend to get a fresh session cookie, and reports balance/status.
For apps with daily check-in or recurring tasks, add the per-app logic
in the APP-SPECIFIC HOOKS section below.

ADAPTATION — fill in these values for your airdrop:
  1. APP_DOMAIN  — frontend domain (e.g. 'rewards.pear.trade')
  2. APP_API     — backend API base (e.g. 'https://temp.pear.trade/api')
  3. PRIVY_APP_ID — from the target's auth.privy.io init params
                    (extract via JS chunk grep: privy-app-id pattern)
  4. OAUTH_FILE  — path to JSON with {token, refresh_token, privy_access_token}
  5. SESSION_FILE — path to JSON with {ua, cf_clearance, cookies: {pt_session}}
  6. SYNC_FIELD  — field name expected by /auth/privy/sync (usually 'token',
                    try alternatives if you get VALIDATION_ERROR: 'access_token',
                    'identity_token', 'id_token')
  7. If app has daily check-in: implement the POST in app_specific_daily()
  8. Adjust user-field reporting in report_status() per app's schema

Pattern reference: see captcha-bypass/references/privy-session-sync.md
"Daily Maintenance Cron" section (Pear case, 2026-06-14).
"""
import json
import os
import sys
from datetime import datetime

import requests

# ─── App config (FILL IN for your airdrop) ──────────────────────────────────
APP_DOMAIN    = 'YOUR-APP-DOMAIN.example.com'   # e.g. 'rewards.pear.trade'
APP_API       = 'https://YOUR-APP-API.example.com/api'  # backend base
PRIVY_APP_ID  = 'YOUR_27CHAR_PRIVY_APP_ID'      # e.g. 'cmmtgs24k01gi0cjfyfku199k'
PRIVY_BASE    = 'https://auth.privy.io'
SYNC_FIELD    = 'token'                          # field name for /auth/privy/sync

# Path to the JSON file holding Privy session data (saved after signup/oauth)
# Schema: {"token": "<identity_token>", "refresh_token": "...",
#          "privy_access_token": "...", "user_did": "did:privy:..."}
# Set via env var OAUTH_FILE, or hardcode below.
OAUTH_FILE=os.env...LE',   '/path/to/your/privy_oauth_session.json')

# Path to the JSON file holding app session data (saved after first /auth/privy/sync)
# Schema: {"ua": "<real Chrome UA from FlareSolverr>",
#          "cf_clearance": "<value>",
#          "cookies": {"pt_session": "<jwt>"}}
SESSION_FILE  = os.environ.get('SESSION_FILE', '/path/to/your/app_session.json')

# ─── Helpers ─────────────────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ─── 1. Refresh Privy identity_token ─────────────────────────────────────────
def refresh_privy_token(oauth):
    """Call /api/v1/sessions with current refresh_token + access_token.
    Returns (new_identity_token, success: bool).

    Endpoints/headers verified on Pear 2026-06-14:
      POST https://auth.privy.io/api/v1/sessions
      Headers: privy-app-id, Content-Type, Authorization: Bearer ***, Origin
      Body: {"refresh_token": "..."}
      Response 200: {token, privy_access_token, refresh_token} (all 3 rotate)
    """
    if not oauth.get('refresh_token') or not oauth.get('privy_access_token'):
        log('⚠️  missing refresh_token or privy_access_token, cannot refresh')
        return oauth.get('token'), False

    r = requests.post(f'{PRIVY_BASE}/api/v1/sessions',
        json={'refresh_token': oauth['refresh_token']},
        headers={
            'privy-app-id': PRIVY_APP_ID,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {oauth["privy_access_token"]}',
            'Origin': PRIVY_BASE,
        },
        timeout=15)

    if r.status_code == 200:
        new = r.json()
        oauth['token']              = new.get('token', oauth['token'])
        oauth['privy_access_token'] = new.get('privy_access_token', oauth['privy_access_token'])
        oauth['refresh_token']      = new.get('refresh_token', oauth['refresh_token'])
        save_json(OAUTH_FILE, oauth)
        log(f'  ✅ refreshed (token len={len(oauth["token"])})')
        return oauth['token'], True

    log(f'  ❌ refresh failed: HTTP {r.status_code} {r.text[:200]}')
    log('  falling back to current token (may still be valid for ~1h)')
    return oauth.get('token'), False

# ─── 2. Re-sync to app backend ───────────────────────────────────────────────
def resync_app_session(id_token, sess):
    """POST /auth/privy/sync with the identity_token, get fresh session cookie.
    Returns (requests.Session, new_cookie) or (None, None) on failure.

    Endpoints/headers verified on Pear 2026-06-14:
      POST {APP_API}/auth/privy/sync
      Body: {"token": "<identity_token>"}   (field name = SYNC_FIELD constant)
      Headers: privy-app-id, User-Agent (real Chrome UA), Origin, Referer
      Cookies: cf_clearance=<fresh from FlareSolverr>
      Response 200: user data + Set-Cookie: pt_session=<JWT>
    """
    s = requests.Session()
    cf_clearance = sess.get('cf_clearance', '')
    if cf_clearance:
        s.cookies.set('cf_clearance', cf_clearance, domain=f'.{APP_DOMAIN}')

    # Clear any old session cookies to avoid CookieConflictError on resync
    for cookie_name in list(s.cookies.keys()):
        if 'session' in cookie_name.lower() or 'token' in cookie_name.lower():
            s.cookies.pop(cookie_name, None)

    r = s.post(f'{APP_API}/auth/privy/sync',
        json={SYNC_FIELD: id_token},
        headers={
            'privy-app-id': PRIVY_APP_ID,
            'User-Agent':   sess.get('ua', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
            'Origin':       f'https://{APP_DOMAIN}',
            'Referer':      f'https://{APP_DOMAIN}/dashboard',
        },
        timeout=10)

    if r.status_code != 200:
        log(f'❌ re-sync failed: HTTP {r.status_code} {r.text[:200]}')
        return None, None

    # Try common cookie names — most apps use {name}_session
    new_cookie = None
    for candidate in ('pt_session', 'session', f'{APP_DOMAIN.split(".")[0]}_session'):
        new_cookie = r.cookies.get(candidate)
        if new_cookie:
            break
    if not new_cookie:
        # Fallback: any Set-Cookie in response
        for c in r.cookies:
            if 'session' in c.name.lower() or 'token' in c.name.lower():
                new_cookie = c.value
                break
    if not new_cookie:
        log('⚠️  re-sync OK but no session cookie in response')
        return s, None

    s.cookies.set(new_cookie, new_cookie, domain=APP_DOMAIN) if False else None
    # Set on the right domain — best effort
    s.cookies.clear()
    s.cookies.set('cf_clearance', cf_clearance, domain=f'.{APP_DOMAIN}')
    # The cookie name is whatever we found
    for k in s.cookies.keys():
        s.cookies.pop(k, None)
    cookie_name = None
    for c in r.cookies:
        if c.value == new_cookie:
            cookie_name = c.name
            break
    if not cookie_name:
        cookie_name = 'pt_session'  # best guess
    s.cookies.set(cookie_name, new_cookie, domain=APP_DOMAIN)

    sess.setdefault('cookies', {})[cookie_name] = new_cookie
    save_json(SESSION_FILE, sess)
    log(f'  ✅ {cookie_name} refreshed (len={len(new_cookie)})')
    return s, new_cookie

# ─── 3. Verify session + report status ───────────────────────────────────────
def report_status(s, sess):
    """GET /auth/me, parse app-specific user schema, return user dict.
    Apps differ: Pear wraps in {data: {user: ...}}, others return user directly.
    """
    r = s.get(f'{APP_API}/auth/me',
        headers={'User-Agent': sess.get('ua', 'Mozilla/5.0 ...')},
        timeout=10)
    if r.status_code != 200:
        log(f'❌ /auth/me failed: HTTP {r.status_code}')
        return None
    body = r.json()
    user = body.get('data', body).get('user', body.get('data', body))
    return user

# ─── 4. APP-SPECIFIC HOOKS (override per airdrop) ────────────────────────────
def app_specific_daily(s, sess, user):
    """Override this for apps with daily check-in, recurring tasks, etc.
    Default: no-op (Pear case — no daily check-in exists).

    Example for an app with a daily check-in endpoint:
        r = s.post(f'{APP_API}/daily/checkin', json={}, timeout=10)
        log(f'  daily check-in: HTTP {r.status_code} {r.text[:120]}')

    Example for an app with a recurring claim task:
        r = s.post(f'{APP_API}/rewards/claim', json={'taskId': 'daily'}, timeout=10)
        log(f'  daily claim: {r.json()}')
    """
    return None

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    log('Daily login')

    try:
        oauth = load_json(OAUTH_FILE)
        sess  = load_json(SESSION_FILE)
    except FileNotFoundError as e:
        log(f'❌ missing file: {e}')
        log(f'   set OAUTH_FILE and SESSION_FILE env vars, or edit the constants')
        return 1

    # 1. Refresh Privy token
    log('=== Privy token refresh ===')
    id_token, refresh_ok = refresh_privy_token(oauth)
    if not id_token:
        log('❌ no identity_token available')
        return 1

    # 2. Re-sync to app backend
    log('=== App session resync ===')
    s, cookie = resync_app_session(id_token, sess)
    if not s:
        return 1

    # 3. Verify + report
    log('=== Status ===')
    user = report_status(s, sess)
    if user:
        for k in ('handle', 'username', 'email', 'points', 'streak',
                  'primaryAuthMethod', 'twitter', 'discord', 'wallet'):
            if k in user:
                v = user[k]
                if isinstance(v, dict):
                    v = v.get('connected', v)
                log(f'  {k}: {v}')

    # 4. App-specific daily tasks (override per airdrop)
    log('=== App-specific hooks ===')
    app_specific_daily(s, sess, user)

    log('✅ Daily login OK')
    return 0

if __name__ == '__main__':
    sys.exit(main())
