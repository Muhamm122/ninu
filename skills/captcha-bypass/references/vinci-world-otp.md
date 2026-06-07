# Vinci World — OTP Login Reference

## Site
- URL: `https://www.vinciworld.xyz/`
- Title: "Vinci World"
- Type: Web3 / Genesis SBT claim
- Incubated by: Renaiss

## Login Methods (as of 2026-06-04)

| Method | Ref | Notes |
|--------|-----|-------|
| Email + OTP | textbox + "Send OTP" button | ✅ Works from AWS IP |
| Google social | button (Google icon) | ❌ Needs Google session |
| Other social | 2 more buttons | Unknown providers |
| Wallet connect | 4 buttons including Binance | Needs MetaMask extension |
| "More" wallets | button | Opens wallet list |

## OTP Flow

1. Click **"Open login panel"** button (main page has only this + Renaiss link)
2. Enter email in textbox
3. Click **"Send OTP"**
4. Page transitions to 6-digit input: `textbox "Digit 1 of 6"` through `textbox "Digit 6 of 6"`
5. Back button + Resend code (60s cooldown) appear
6. Enter each digit separately into its field
7. Page may auto-submit or may need explicit submit

## Key Findings (Session 2026-06-04)

- ✅ **No CAPTCHA** on email OTP login from AWS IP
- ⚠️ **OTP expires ~60 seconds** — resend invalidates previous code
- ⚠️ **Ref IDs expire quickly** — if page state changes or time passes, re-snapshot before entering OTP
- ⚠️ **Page goes empty** on navigation loss — must re-navigate and restart login flow
- ❌ Old OTP from a previous Send OTP request is **invalid** after resend — user must check for the LATEST email only
- Login panel is a modal dialog — closing it or navigating away loses the OTP session

## Failure Replay (Session 2026-06-04)

### What went wrong (3 failed attempts)
1. **Attempt 1**: Sent OTP, got code `550633` from user (old code from initial send). Resent OTP (which killed `550633`). Entered `550633` → "Invalid" (expected).
2. **Attempt 2**: Page reloaded (refs expired). Resent OTP again. User gave `424605` (from a PREVIOUS email). Entered `424605` → "Invalid".
3. **Attempt 3**: Resent OTP yet again. Entered `424605` still (from old email) → "Invalid" again.

### Root cause
- Every "Send OTP" click **generates a new code and invalidates all previous codes**.
- The user was reading old emails instead of the latest one.
- Multiple resends created confusion about which email contained the valid code.
- Page kept losing state (refs expiring), forcing reloads which reset the OTP session.

### Lessons learned
1. **Pre-coordinate with user** BEFORE sending OTP: "I will send the code now — check your email INBOX RIGHT AFTER and give me the 6-digit code. It expires in 60 seconds."
2. **Never re-enter a code from an old email.** If you had to resend or reload, tell the user: "That code is expired. A new email was just sent. Please find the LATEST email from Vinci World."
3. **Minimize resends.** Each resend kills the previous code. If the user is slow, one resend is OK; multiple resends in a row create chaos.
4. **After page reload, always re-snapshot BEFORE typing.** Refs from the pre-reload page are dead.
5. **Type digits one at a time into each field.** Don't try to paste the whole code into one field.
6. **If user provides a stale OTP (from a previous send), DON'T enter it.** Explain that resending invalidated the old code. Ask them to check for the LATEST email only. Entering a stale code wastes time and shows "Invalid" — it also costs another resend cycle.
7. **Tell the user to WAIT at their inbox before you send.** Then send OTP immediately. This maximizes the time window for them to receive and relay the code before expiry.

## Error Messages
- `"Invalid email and code combination"` — wrong/expired OTP entered

## GCP Console Login (Session 2026-06-04)

When user shared a GCP Service Account URL (`console.cloud.google.com/iam-admin/serviceaccounts/...`) and asked to "implement OAuth Gmail":

1. Navigated to GCP Console URL → redirected to Google Sign In
2. Entered email `muhammadadib1217@gmail.com` → clicked Next
3. **BLOCKED**: `"This browser or app may not be secure"` — Google rejects headless/automated browsers from datacenter IPs for account login
4. **Resolution**: Cannot create OAuth credentials from VPS. User must create credentials on their own device (phone/PC) and provide Client ID + Client Secret or Service Account JSON key to the agent.

**Key insight**: A URL containing `console.cloud.google.com` + `serviceaccounts` is a signal that the user wants **OAuth/API-based Gmail access**, not a new Gmail account creation. Route to `google-workspace` skill, not Gmail signup flow.

## DOM Structure (Login Panel)
```
dialog "Log in to Vinci World"
  heading "Log in to Vinci World" [level=1]
  button "Close login panel"
  ── Email tab ──
    textbox (email input)
    button "Send OTP"
  ── Social login ──
    button (Google)
    button (unknown icon)
    button (unknown icon)
  ── Wallet ──
    button (wallet 1)
    button "Binance Wallet"
    button (wallet 2)
    button "More"
  ── Footer ──
    link "Terms of Service"
    link "Privacy Policy"
```

## DOM Structure (OTP Entry)
```
dialog "Log in to Vinci World"
  heading "Log in to Vinci World" [level=1]
  button "Back"
  paragraph "Please check {email} and enter the code below"
  textbox "Digit 1 of 6"
  textbox "Digit 2 of 6"
  textbox "Digit 3 of 6"
  textbox "Digit 4 of 6"
  textbox "Digit 5 of 6"
  textbox "Digit 6 of 6"
  StaticText "Resend code ("
  StaticText "{countdown}s)"
```
