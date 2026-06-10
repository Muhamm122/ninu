#!/usr/bin/env python3
"""
Gmail IMAP/SMTP tool — direct Python access without CLI dependency.
Use when you need fast programmatic email access from Hermes.

Usage:
  gmail.py read [N]           — Read N latest emails (default 10)
  gmail.py search QUERY [N]   — Search emails (IMAP search syntax)
  gmail.py send TO SUBJECT    — Send email (body from --body flag or stdin)
  gmail.py read-msg UID       — Read full message by UID
  gmail.py delete UID         — Delete message by UID
  gmail.py folders            — List all folders/labels
  gmail.py unread [N]         — Read unread emails only
  gmail.py from SENDER [N]    — Search by sender
  gmail.py since DATE [N]     — Search since date (DD-MMM-YYYY)
  gmail.py test               — Test IMAP connection

Environment:
  GMAIL_ADDRESS  — Gmail address
  GMAIL_PASSWORD — Gmail App Password (16 digits, no spaces)
"""

import os, sys, imaplib, smtplib, email
from email.header import decode_header
from email.mime.text import MIMEText
from datetime import datetime

GMAIL_ADDR = os.environ.get('GMAIL_ADDRESS', '')
GMAIL_PASS = os.environ.get('GMAIL_PASSWORD', '')

if not GMAIL_ADDR or not GMAIL_PASS:
    print("Set GMAIL_ADDRESS and GMAIL_PASSWORD environment variables.")
    sys.exit(1)

def decode_subj(s):
    if not s: return '(no subject)'
    decoded = decode_header(s)
    return ''.join(part.decode(charset or 'utf-8') if isinstance(part, bytes) else part for part, charset in decoded)

def get_imap():
    m = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    m.login(GMAIL_ADDR, GMAIL_PASS)
    return m

def get_smtp():
    s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    s.login(GMAIL_ADDR, GMAIL_PASS)
    return s

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                try: return part.get_payload(decode=True).decode(errors='replace')
                except: pass
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                try: return part.get_payload(decode=True).decode(errors='replace')
                except: pass
    else:
        try: return msg.get_payload(decode=True).decode(errors='replace')
        except: pass
    return ''

def cmd_test():
    m = get_imap()
    m.select('INBOX')
    typ, data = m.search(None, 'ALL')
    count = len(data[0].split())
    m.logout()
    print(f"✅ Connected: {GMAIL_ADDR} ({count} inbox messages)")

def cmd_folders():
    m = get_imap()
    typ, folders = m.list()
    m.logout()
    for f in folders:
        parts = str(f).split('"/"')
        name = parts[-1].strip().strip('"').strip("'") if len(parts) > 1 else str(f)
        print(name)

def cmd_read(n=10, criteria='ALL'):
    m = get_imap()
    m.select('INBOX')
    typ, data = m.search(None, criteria)
    ids = data[0].split()
    if not ids:
        print("No messages."); m.logout(); return
    latest = ids[-n:]
    for mid in reversed(latest):
        typ, msg_data = m.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_subj(msg['Subject'])[:60]
        from_addr = (msg['From'] or '')[:45]
        date = (msg['Date'] or '')[:30]
        snippet = get_body(msg)[:70].replace('\n', ' ')
        print(f"UID:{mid.decode()} | {subject}")
        print(f"  From: {from_addr} | {date}")
        if snippet: print(f"  >> {snippet}")
        print()
    m.logout()

def cmd_search(query, n=10):
    m = get_imap()
    m.select('INBOX')
    typ, data = m.search(None, query)
    ids = data[0].split()
    if not ids:
        print(f"No results for: {query}"); m.logout(); return
    latest = ids[-n:]
    for mid in reversed(latest):
        typ, msg_data = m.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_subj(msg['Subject'])[:60]
        from_addr = (msg['From'] or '')[:45]
        print(f"UID:{mid.decode()} | {subject} | {from_addr}")
    m.logout()

def cmd_read_msg(uid):
    m = get_imap()
    m.select('INBOX')
    typ, msg_data = m.fetch(uid.encode(), '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"From: {msg['From']}\nTo: {msg['To']}\nSubject: {decode_subj(msg['Subject'])}\nDate: {msg['Date']}\n")
    body = get_body(msg)
    if body: print(body[:5000])
    m.logout()

def cmd_send(to, subject, body=None):
    if body is None:
        body = sys.stdin.read()
    msg = MIMEText(body)
    msg['From'] = GMAIL_ADDR
    msg['To'] = to
    msg['Subject'] = subject
    s = get_smtp()
    s.send_message(msg)
    s.quit()
    print(f"✅ Sent to {to}: {subject}")

def cmd_delete(uid):
    m = get_imap()
    m.select('INBOX')
    m.store(uid.encode(), '+FLAGS', '\\Deleted')
    m.expunge()
    m.logout()
    print(f"Deleted UID {uid}")

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == 'test': cmd_test()
    elif cmd == 'read': cmd_read(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == 'unread': cmd_read(int(sys.argv[2]) if len(sys.argv) > 2 else 10, 'UNSEEN')
    elif cmd == 'search':
        if len(sys.argv) < 3: print("Usage: gmail.py search QUERY [MAX]"); sys.exit(1)
        cmd_search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == 'from':
        if len(sys.argv) < 3: print("Usage: gmail.py from SENDER [MAX]"); sys.exit(1)
        cmd_search(f'FROM "{sys.argv[2]}"', int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == 'since':
        if len(sys.argv) < 3: print("Usage: gmail.py since DD-MMM-YYYY [MAX]"); sys.exit(1)
        cmd_search(f'SINCE {sys.argv[2]}', int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == 'read-msg':
        if len(sys.argv) < 3: print("Usage: gmail.py read-msg UID"); sys.exit(1)
        cmd_read_msg(sys.argv[2])
    elif cmd == 'send':
        if len(sys.argv) < 4: print("Usage: gmail.py send TO SUBJECT [--body TEXT]"); sys.exit(1)
        body = None
        if '--body' in sys.argv:
            idx = sys.argv.index('--body')
            body = ' '.join(sys.argv[idx+1:])
        cmd_send(sys.argv[2], sys.argv[3], body)
    elif cmd == 'delete':
        if len(sys.argv) < 3: print("Usage: gmail.py delete UID"); sys.exit(1)
        cmd_delete(sys.argv[2])
    elif cmd == 'folders': cmd_folders()
    else: print(f"Unknown: {cmd}"); print(__doc__)
