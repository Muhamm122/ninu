---
name: himalaya
description: "Himalaya CLI: IMAP/SMTP email from terminal."
version: 1.1.0
author: community
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Email, IMAP, SMTP, CLI, Communication]
    homepage: https://github.com/pimalaya/himalaya
prerequisites:
  commands: [himalaya]
---

# Himalaya Email CLI

Himalaya is a CLI email client that lets you manage emails from the terminal using IMAP, SMTP, Notmuch, or Sendmail backends.

This skill is separate from the Hermes Email gateway adapter. The gateway
adapter lets people email the agent and uses Hermes' built-in IMAP/SMTP
adapter; this skill lets the agent operate a mailbox from terminal tools and
requires the external `himalaya` CLI.

## References

- `references/configuration.md` (config file setup + IMAP/SMTP authentication)
- `references/message-composition.md` (MML syntax for composing emails)

## Prerequisites

1. Himalaya CLI installed (`himalaya --version` to verify)
2. A configuration file at `~/.config/himalaya/config.toml`
3. IMAP/SMTP credentials configured (password stored securely)

### Installation

```bash
# Pre-built binary (Linux/macOS — recommended)
curl -sSL https://raw.githubusercontent.com/pimalaya/himalaya/master/install.sh | PREFIX=~/.local sh

# macOS via Homebrew
brew install himalaya

# Or via cargo (any platform with Rust)
cargo install himalaya --locked
```

## Configuration Setup

Run the interactive wizard to set up an account:

```bash
himalaya account configure
```

Or create `~/.config/himalaya/config.toml` manually.

### Gmail via App Password (recommended for email-only)

This is the fastest path to Gmail access — no OAuth, no GCP project:

1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Create App Password: https://myaccount.google.com/apppasswords
3. Use the 16-char password in config

```toml
[accounts.gmail]
email = "you@gmail.com"
display-name = "Your Name"
default = true

[accounts.gmail.imap]
host = "imap.gmail.com"
port = 993
login = "you@gmail.com"
passwd-cmd = "echo YOUR_APP_PASSWORD_NO_SPACES"

[accounts.gmail.smtp]
host = "smtp.gmail.com"
port = 465
login = "you@gmail.com"
passwd-cmd = "echo YOUR_APP_PASSWORD_NO_SPACES"
```

**Heads up**: App Password creation **requires 2-FA enabled first**. If `AUTHENTICATIONFAILED` on connect, check 2-FA status. Use the password without spaces in `passwd-cmd`.

### Generic IMAP/SMTP config

```toml
[accounts.personal]
email = "you@example.com"
display-name = "Your Name"
default = true

[accounts.personal.imap]
host = "imap.example.com"
port = 993
login = "you@example.com"
passwd-cmd = "pass show email/imap"

[accounts.personal.smtp]
host = "smtp.example.com"
port = 587
login = "you@example.com"
passwd-cmd = "pass show email/smtp"
```

> **Config format note for v1.2.0+**: The flat `[accounts.X.imap]` / `[accounts.X.smtp]`
> syntax is **required** in himalaya v1.2.0+. The older `backend.type = "imap"` /
> `backend.host = "..."` nested format is **rejected** at parse time with
> `missing field 'auth'` or `invalid type` errors. Always use the flat form above.

## Hermes Integration Notes

- **Reading, listing, searching, moving, deleting** all work directly through the terminal tool
- **Composing/replying/forwarding** — piped input (`cat << EOF | himalaya template send`) is recommended for reliability. Interactive `$EDITOR` mode works with `pty=true` + background + process tool, but requires knowing the editor and its commands
- Use `--output json` for structured output that's easier to parse programmatically
- The `himalaya account configure` wizard requires interactive input — use PTY mode: `terminal(command="himalaya account configure", pty=true)`

## Common Operations

### List Folders

```bash
himalaya folder list
```

### List Emails

List emails in INBOX (default):

```bash
himalaya envelope list
```

List emails in a specific folder:

```bash
himalaya envelope list --folder "Sent"
```

List with pagination:

```bash
himalaya envelope list --page 1 --page-size 20
```

### Search Emails

```bash
himalaya envelope list from john@example.com subject meeting
```

### Read an Email

Read email by ID (shows plain text):

```bash
himalaya message read 42
```

Export raw MIME:

```bash
himalaya message export 42 --full
```

### Reply to an Email

To reply non-interactively from Hermes, read the original message, compose a reply, and pipe it:

```bash
# Get the reply template, edit it, and send
himalaya template reply 42 | sed 's/^$/\nYour reply text here\n/' | himalaya template send
```

Or build the reply manually:

```bash
cat << 'EOF' | himalaya template send
From: you@example.com
To: sender@example.com
Subject: Re: Original Subject
In-Reply-To: <original-message-id>

Your reply here.
EOF
```

Reply-all (interactive — needs $EDITOR, use template approach above instead):

```bash
himalaya message reply 42 --all
```

### Forward an Email

```bash
# Get forward template and pipe with modifications
himalaya template forward 42 | sed 's/^To:.*/To: newrecipient@example.com/' | himalaya template send
```

### Write a New Email

**Non-interactive (use this from Hermes)** — pipe the message via stdin:

```bash
cat << 'EOF' | himalaya template send
From: you@example.com
To: recipient@example.com
Subject: Test Message

Hello from Himalaya!
EOF
```

Or with headers flag:

```bash
himalaya message write -H "To:recipient@example.com" -H "Subject:Test" "Message body here"
```

Note: `himalaya message write` without piped input opens `$EDITOR`. This works with `pty=true` + background mode, but piping is simpler and more reliable.

### Move/Copy Emails

Move to folder:

```bash
himalaya message move 42 "Archive"
```

Copy to folder:

```bash
himalaya message copy 42 "Important"
```

### Delete an Email

```bash
himalaya message delete 42
```

### Manage Flags

Add flag:

```bash
himalaya flag add 42 --flag seen
```

Remove flag:

```bash
himalaya flag remove 42 --flag seen
```

## Multiple Accounts

List accounts:

```bash
himalaya account list
```

Use a specific account:

```bash
himalaya --account work envelope list
```

## Attachments

Save attachments from a message:

```bash
himalaya attachment download 42
```

Save to specific directory:

```bash
himalaya attachment download 42 --dir ~/Downloads
```

## Output Formats

Most commands support `--output` for structured output:

```bash
himalaya envelope list --output json
himalaya envelope list --output plain
```

## Debugging

Enable debug logging:

```bash
RUST_LOG=debug himalaya envelope list
```

Full trace with backtrace:

```bash
RUST_LOG=trace RUST_BACKTRACE=1 himalaya envelope list
```

## Python IMAP/SMTP Script

For programmatic Gmail access (no CLI dependency, faster for batch ops):

```
scripts/gmail.py
```

Set `GMAIL_ADDRESS` and `GMAIL_PASSWORD` (App Password, no spaces) env vars.

```bash
GMAIL_ADDRESS=you@gmail.com GMAIL_PASSWORD=abcdabcdabcdabcd python3 scripts/gmail.py test
GMAIL_ADDRESS=you@gmail.com GMAIL_PASSWORD=abcdabcdabcdabcd python3 scripts/gmail.py read 10
GMAIL_ADDRESS=you@gmail.com GMAIL_PASSWORD=abcdabcdabcdabcd python3 scripts/gmail.py send to@example.com "Subject" --body "Body text"
GMAIL_ADDRESS=you@gmail.com GMAIL_PASSWORD=abcdabcdabcdabcd python3 scripts/gmail.py search 'FROM "discord"' 5
GMAIL_ADDRESS=you@gmail.com GMAIL_PASSWORD=abcdabcdabcdabcd python3 scripts/gmail.py unread 5
```

Use this when you need fast read/send/search without Himalaya CLI quirks (envelope listing, MML compose, etc.). The script uses stdlib `imaplib` + `smtplib` only — no extra dependencies.

### gmail.py + Telegram user account (tg_user.py)

If the user also has a Telegram account, both tools work together:
- `gmail.py` — read/send/search email
- `tg_user.py` — read/send/search Telegram (via Telethon MTProto)

Both use App Password / API credentials stored in `~/.hermes/accounts.env`.

## Gmail App Password — Complete Path (fastest to working Gmail)

OAuth is a dead end from VPS (Google blocks datacenter IPs with "This browser or app may not be secure"). The App Password path works in 2 minutes:

1. **Enable 2-FA**: https://myaccount.google.com/security → 2-Step Verification → ON
   - ⚠️ If user gets "The setting is not available" at apppasswords URL → 2-FA is OFF
   - ⚠️ `AUTHENTICATIONFAILED` on IMAP login → 99% chance 2-FA is OFF
2. **Create App Password**: https://myaccount.google.com/apppasswords → App name → Create
3. **Use 16-char password** (remove spaces) in `passwd-cmd` or `GMAIL_PASSWORD` env var
4. **Test**: `python3 scripts/gmail.py test`

### Why NOT OAuth for personal Gmail from VPS
- Google blocks headless/datacenter browser login: "This browser or app may not be secure"
- OOB redirect (`urn:ietf:wg:oauth:2.0:oob`) → `access_denied` for unverified/test-mode apps
- localhost redirect → code goes to user's machine, not VPS
- Service Account → only works with Google Workspace (business), NOT @gmail.com
- GCP API key (`AIzaSy...`) → NOT accepted by Gmail API (needs OAuth2 access token)
- OAuth Consent Screen test users → user must add their email (extra step, still blocked from VPS)
- **Bottom line**: If you only need email (read/send/search), App Password wins every time.

## Tips

- Use `himalaya --help` or `himalaya <command> --help` for detailed usage.
- Message IDs are relative to the current folder; re-list after folder changes.
- For composing rich emails with attachments, use MML syntax (see `references/message-composition.md`).
- Store passwords securely using `pass`, system keyring, or a command that outputs the password.
- **Prefer `scripts/gmail.py`** for quick read/send/search from Hermes — zero CLI ceremony, stdlib only.
