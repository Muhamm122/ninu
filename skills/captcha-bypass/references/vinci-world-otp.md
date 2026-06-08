# Vinci World OTP Login Flow

## Platform Info
- **URL**: https://vinciworld.xyz
- **Auth provider**: Privy.io
- **OTP sender**: `no-reply@privy.io`
- **OTP subject**: "Your login code for Renaiss" (Renaiss is the incubator)
- **OTP format**: 6-digit code in email body, regex `\b(\d{6})\b`
- **OTP expiry**: 10 minutes
- **Platform**: "Platform: Chrome Headless browser on Linux" appears in email body (no issue — works fine)

## DOM Structure

```
Main page:
  - button "Open login panel" [ref=e2]

Login dialog:
  - dialog "Log in to Vinci World"
    - textbox [ref=e14]  ← email input
    - button "Send OTP" [ref=e4]
    - button [ref=e5]    ← Google OAuth (icon-only)
    - button [ref=e6]    ← Twitter/X OAuth (icon-only)
    - button [ref=e7]    ← other social (icon-only)
    - button [ref=e8]    ← MetaMask (icon-only)
    - button "Binance Wallet" [ref=e9]
    - button [ref=e10]   ← another wallet
    - button "More" [ref=e11]

OTP input:
  - button "Back"
  - textbox "Digit 1 of 6" [ref=e5]
  - textbox "Digit 2 of 6" [ref=e6]
  - textbox "Digit 3 of 6" [ref=e7]
  - textbox "Digit 4 of 6" [ref=e8]
  - textbox "Digit 5 of 6" [ref=e9]
  - textbox "Digit 6 of 6" [ref=e10]

Waitlist form (post-login):
  - textbox "you@example.com" [auto-filled]
  - textbox "@vinciworld" [username input]
  - button "Join waitlist"
  - button "Log out"

Success state:
  - Text: "You're on the list!"
  - "Thanks for joining the Vinci World waitlist. We'll reach out when it's your turn to play."
  - button "Log out"
```

## Auto-OTP Technique (IMAP Polling)

The recommended approach is **fully automated** via IMAP polling — don't ask the user for the code.

### Prerequisites
- Gmail account with 2-FA enabled
- App Password created at myaccount.google.com/apppasswords
- App Password stored in himalaya config: `~/.config/himalaya/config.toml`

### Automated Flow

```bash
# 1. Browser: navigate to Vinci World
# 2. Click "Open login panel" 
# 3. Type email in textbox
# 4. Click "Send OTP"
# 5. Run IMAP poll script (see below)
# 6. Type 6 digits into OTP fields
# 7. Fill username + click "Join waitlist"
```

### IMAP Poll Script

```python
import imaplib, email, re, time

def poll_vinci_otp(email_addr, app_password, max_wait=90):
    """Poll Gmail for Vinci/Privy OTP. Returns 6-digit code or None."""
    seen = set()
    start = time.time()
    while time.time() - start < max_wait:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(email_addr, app_password)
        mail.select('INBOX')
        status, data = mail.search(None, '(FROM "privy.io")')
        for eid in reversed(data[0].split()):
            eid_str = eid.decode()
            if eid_str in seen:
                continue
            seen.add(eid_str)
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

### Successful Execution Log (2026-06-07)

```
1. Navigated to https://vinciworld.xyz         ✅
2. Clicked "Open login panel"                   ✅
3. Typed "adibmuhadi@gmail.com" in email field  ✅
4. Clicked "Send OTP"                          ✅
5. OTP email arrived from no-reply@privy.io    ✅
6. IMAP poll found OTP: 811247 (3s wait)       ✅
7. Typed digits 8-1-1-2-4-7 into 6 fields      ✅
8. Auto-logged in — waitlist form appeared      ✅
9. Typed username "cupang"                      ✅
10. Clicked "Join waitlist"                     ✅
11. Page: "You're on the list!"                 ✅
```

Total time: ~15 seconds from navigation to confirmed registration.

## Known Issues
- **Page timeout**: `browser_navigate` to vinciworld.xyz sometimes times out on initial load. Retry works.
- **Empty page after OTP click**: If browser snapshot shows empty, navigate again — page state is preserved in session cookies.
- **Privy.io sender filter**: Use `FROM "privy.io"` not `FROM "vinci"` — the email comes from Privy, not Vinci World directly.
- **Subject says "Renaiss"**: Don't be confused — Vinci World is incubated by Renaiss, so the OTP email subject is "Your login code for Renaiss".
