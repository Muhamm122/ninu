# Gmail Access from VPS — OAuth vs App Password Failure Log

**Date**: 2026-06-07
**Server**: AWS Singapore (18.143.107.30), headless Chromium (CloakBrowser)

## OAuth Attempts — ALL FAILED

### Attempt 1: GCP Console Login from VPS
- Navigated to `console.cloud.google.com` in headless browser
- **Result**: "This browser or app may not be secure"
- Google blocks headless/datacenter browser login at the identity provider level
- No CAPTCHA even offered — hard block

### Attempt 2: OAuth OOB Flow (urn:ietf:wg:oauth:2.0:oob)
- Generated correct OAuth URL with Client ID `994716122927-...`
- User opened on phone → logged in → but got "access_denied"
- **Root cause**: App in Testing mode, user's email not in Test Users list
- OOB redirect is deprecated by Google — returns 403 for unverified/testing apps

### Attempt 3: Add Test User + Retry OAuth
- Guided user to OAuth Consent Screen → "Test users" section
- User couldn't find the section (consent screen not yet configured)
- Guided through External + Testing setup → user had trouble navigating GCP Console
- Eventually hit: **"You need additional access to the project"** — user wasn't owner

### Attempt 4: New Project + New OAuth Client ID
- User created new project `cupang-gmail`
- New Client ID + Client Secret obtained
- Auth URL opened on phone → still **403 access_denied**
- Consent screen still not properly configured with test user

### Attempt 5: OAuth from VPS browser directly
- Opened OAuth URL in headless browser on VPS
- Entered email → **"This browser or app may not be secure"**
- Same AWS IP block — cannot complete OAuth flow from server

## App Password — SUCCEEDED (2 minutes)

1. User enabled 2-FA at myaccount.google.com/security
2. Created App Password at myaccount.google.com/apppasswords (16-char `vnuq...yzxt`)
3. Python IMAP: `imaplib.IMAP4_SSL('imap.gmail.com', 993)` → `m.login(email, app_password)` → **SUCCESS**
4. Full inbox access: 410 messages, send/receive/search all working

## Key Insight

For personal Gmail from VPS, **do not attempt OAuth at all**. The path is:
1. Enable 2-FA (prerequisite — App Password unavailable without it)
2. Create App Password
3. Use IMAP/SMTP with `imaplib`/`smtplib` (stdlib, no dependencies)

OAuth is only needed if you require Calendar, Drive, or Sheets API access — and even then, the user must complete the auth flow on their own device (never from VPS).

## Credential Types That Don't Work for Gmail

| What user gives | Why it fails | Redirect to |
|-----------------|-------------|-------------|
| GCP API key (`AIzaSy...`) | Gmail API returns 401: "API keys are not supported by this API. Expected OAuth2 access token" | App Password |
| Service Account email (`x@proj.iam.gserviceaccount.com`) | Service Accounts only work with Google Workspace (business) via domain-wide delegation, NOT @gmail.com personal inboxes | App Password |
| Service Account numeric ID | Same as above — just a different identifier format | App Password |
| OAuth Client ID alone | Need Client Secret too for token exchange | Ask for Client Secret |
| OAuth Client ID + Secret from wrong project | User gets "You need additional access to the project" | Check project ownership or create new project |
