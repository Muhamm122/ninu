#!/usr/bin/env python3
"""
CUPANG Gmail Tool — Full Gmail access via IMAP/SMTP
====================================================
Read, send, search, delete, star, label emails.

Usage:
  gmail.py read [N]           — Read N latest emails (default 10)
  gmail.py search QUERY [N]   — Search emails (Gmail IMAP syntax)
  gmail.py send TO SUBJECT    — Send email (body from stdin or --body)
  gmail.py read-msg ID        — Read full message by UID
  gmail.py delete ID          — Delete message by UID
  gmail.py folders            — List all folders/labels
  gmail.py unread [N]         — Read unread emails
  gmail.py from SENDER [N]    — Search by sender
  gmail.py since DATE [N]     — Search since date (DD-MMM-YYYY)
  gmail.py test               — Test connection

Environment:
  GMAIL_ADDRESS  — Gmail address (default: adibmuhadi@gmail.com)
  GMAIL_PASSWORD — App password (16 digits no spaces)
"""

import os, sys, imaplib, smtplib, email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

GMAIL_ADDR = os.environ.get('GMAIL_ADDRESS', 'adibmuhadi@gmail.com')
GMAIL_PASS = os.environ.get('GMAIL_PASSWORD', 'vnuqycxduiugyzxt')

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

def cmd_test():
    m = get_imap()
    m.select('INBOX')
    typ, data = m.search(None, 'ALL')
    count = len(data[0].split())
    m.logout()
    print(f"✅ Gmail connected: {GMAIL_ADDR}")
    print(f"   Inbox messages: {count}")

def cmd_folders():
    m = get_imap()
    typ, folders = m.list()
    m.logout()
    print(f"📁 Folders ({len(folders)}):")
    for f in folders:
        parts = str(f).split('"/"')
        name = parts[-1].strip().strip('"').strip("'") if len(parts) > 1 else str(f)
        print(f"   {name}")

def cmd_read(n=10, folder='INBOX', criteria='ALL'):
    m = get_imap()
    m.select(folder)
    typ, data = m.search(None, criteria)
    ids = data[0].split()
    
    if not ids:
        print("📭 No messages.")
        m.logout()
        return
    
    latest = ids[-n:] if len(ids) >= n else ids
    
    print(f"📬 {len(ids)} total | Showing latest {len(latest)}:")
    print()
    
    for mid in reversed(latest):
        typ, msg_data = m.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = decode_subj(msg['Subject'])
        from_addr = msg['From'] or ''
        date = msg['Date'] or ''
        flags_str = msg.get('X-GM-LABELS', '')
        
        # Truncate
        subject_display = subject[:55] + '...' if len(subject) > 55 else subject
        
        # Get snippet
        body = get_body(msg)
        snippet = body[:70].replace('\n', ' ') if body else ''
        
        is_unread = '\\Seen' not in str(msg_data[0][0])
        marker = '🔵' if is_unread else '⚪'
        
        print(f"  {marker} {subject_display}")
        print(f"     From: {from_addr[:45]}")
        print(f"     Date: {date[:30]}")
        if snippet:
            print(f"     >> {snippet}")
        print(f"     UID: {mid.decode()}")
        print()
    
    m.logout()

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                try: return part.get_payload(decode=True).decode(errors='replace')
                except: pass
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/html':
                try: return part.get_payload(decode=True).decode(errors='replace')
                except: pass
    else:
        try: return msg.get_payload(decode=True).decode(errors='replace')
        except: pass
    return ''

def cmd_search(query, n=10):
    m = get_imap()
    m.select('INBOX')
    
    # Convert common queries to IMAP
    criteria = f'({query})' if query.startswith('(') else query
    
    typ, data = m.search(None, criteria)
    ids = data[0].split()
    
    if not ids:
        print(f"📭 No results for: {query}")
        m.logout()
        return
    
    latest = ids[-n:] if len(ids) >= n else ids
    
    print(f"🔍 '{query}' — {len(ids)} results | Showing {len(latest)}:")
    print()
    
    for mid in reversed(latest):
        typ, msg_data = m.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        
        subject = decode_subj(msg['Subject'])
        from_addr = msg['From'] or ''
        date = msg['Date'] or ''
        
        print(f"  📧 {subject[:60]}")
        print(f"     From: {from_addr[:45]}")
        print(f"     Date: {date[:30]}")
        print(f"     UID: {mid.decode()}")
        print()
    
    m.logout()

def cmd_read_msg(uid, folder='INBOX'):
    m = get_imap()
    m.select(folder)
    
    typ, msg_data = m.fetch(uid.encode(), '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])
    
    print(f"📧 Message UID: {uid}")
    print(f"   From: {msg['From']}")
    print(f"   To: {msg['To']}")
    print(f"   Subject: {decode_subj(msg['Subject'])}")
    print(f"   Date: {msg['Date']}")
    print()
    
    body = get_body(msg)
    if body:
        print("─── Body ───")
        print(body[:5000])
        if len(body) > 5000:
            print(f"\n... ({len(body)} chars total)")
    
    m.logout()

def cmd_send(to, subject, body=None):
    if body is None:
        print("Enter email body (Ctrl+D to send):")
        body = sys.stdin.read()
    
    msg = MIMEText(body)
    msg['From'] = GMAIL_ADDR
    msg['To'] = to
    msg['Subject'] = subject
    
    s = get_smtp()
    s.send_message(msg)
    s.quit()
    
    print(f"✅ Email sent!")
    print(f"   From: {GMAIL_ADDR}")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")

def cmd_delete(uid, folder='INBOX'):
    m = get_imap()
    m.select(folder)
    m.store(uid.encode(), '+FLAGS', '\\Deleted')
    m.expunge()
    m.logout()
    print(f"🗑️ Message {uid} deleted.")

def cmd_unread(n=10):
    cmd_read(n, 'INBOX', 'UNSEEN')

def cmd_from(sender, n=10):
    cmd_search(f'FROM "{sender}"', n)

def cmd_since(date_str, n=10):
    cmd_search(f'SINCE {date_str}', n)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == 'test':
        cmd_test()
    elif cmd == 'read':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_read(n)
    elif cmd == 'unread':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_unread(n)
    elif cmd == 'search':
        if len(sys.argv) < 3:
            print("Usage: gmail.py search <QUERY> [MAX]")
            sys.exit(1)
        q = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        cmd_search(q, n)
    elif cmd == 'from':
        if len(sys.argv) < 3:
            print("Usage: gmail.py from <SENDER> [MAX]")
            sys.exit(1)
        cmd_from(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == 'since':
        if len(sys.argv) < 3:
            print("Usage: gmail.py since <DD-MMM-YYYY> [MAX]")
            sys.exit(1)
        cmd_since(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == 'read-msg':
        if len(sys.argv) < 3:
            print("Usage: gmail.py read-msg <UID>")
            sys.exit(1)
        cmd_read_msg(sys.argv[2])
    elif cmd == 'send':
        if len(sys.argv) < 4:
            print("Usage: gmail.py send <TO> <SUBJECT> [--body TEXT]")
            sys.exit(1)
        body = None
        if '--body' in sys.argv:
            idx = sys.argv.index('--body')
            body = ' '.join(sys.argv[idx+1:])
        cmd_send(sys.argv[2], sys.argv[3], body)
    elif cmd == 'delete':
        if len(sys.argv) < 3:
            print("Usage: gmail.py delete <UID>")
            sys.exit(1)
        cmd_delete(sys.argv[2])
    elif cmd == 'folders':
        cmd_folders()
    elif cmd in ('help', '-h', '--help'):
        print(__doc__)
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)
