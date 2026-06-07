# Gmail App Password Setup

The fastest path to Gmail read/send access from a VPS. No GCP project, OAuth, or consent screen needed.

## Prerequisites

- **2-Step Verification MUST be enabled** on the Google account. App Password creation is greyed out/unavailable without it.
  - Enable at: https://myaccount.google.com/security

## Steps (user-side, 2 minutes)

1. Visit https://myaccount.google.com/apppasswords
2. Enter app name (e.g., "CUPANG")
3. Click **Create**
4. Google shows a 16-character password in format `xxxx xxxx xxxx xxxx`
5. Copy and provide to agent

## Agent Integration

### Python IMAP/SMTP (direct)

```python
import imaplib, smtplib
from email.mime.text import MIMEText

# Read
m = imaplib.IMAP4_SSL('imap.gmail.com', 993)
m.login('user@gmail.com', 'xxxxxxx')  # no spaces in password
m.select('INBOX')
typ, data = m.search(None, 'ALL')

# Send
smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465)
smtp.login('user@gmail.com', 'xxxxxxx')
msg = MIMEText('body')
msg['To'] = 'to@example.com'
msg['Subject'] = 'subject'
smtp.send_message(msg)
```

### Himalaya CLI

See the himalaya skill — Gmail App Password config section.

## Failure Modes

| Error | Cause | Fix |
|-------|-------|-----|
| `AUTHENTICATIONFAILED` | 2-FA not enabled | Enable at myaccount.google.com/security |
| `AUTHENTICATIONFAILED` | Wrong password format | Try both `xxxx xxxx xxxx xxxx` and `xxxxxxxxxxxxxxxx` |
| `AUTHENTICATIONFAILED` | Typo / partial copy | Regenerate app password |
| App Password page empty/error | 2-FA not enabled | Enable 2-FA first |

## vs OAuth Comparison

| | App Password | OAuth2 |
|---|---|---|
| **Setup time** | 2 min | 10-20 min |
| **GCP project** | Not needed | Required |
| **Consent screen** | Not needed | Required + test users |
| **VPS browser** | Not needed | Blocker (AWS IP) |
| **Scope** | Full IMAP/SMTP | Full Gmail API |
| **Google Workspace (business)** | May not work | Works via SA delegation |
| **Calendar/Drive** | ❌ No | ✅ Yes |
| **Token expiry** | Never (until revoked) | 1 hour (auto-refresh) |
| **Revocation** | myaccount.google.com/apppasswords | myaccount.google.com/permissions |

**Use App Password when**: email-only access, personal @gmail.com, VPS without browser.
**Use OAuth when**: need Calendar/Drive/Sheets, Google Workspace business account, programmatic per-scope control.
