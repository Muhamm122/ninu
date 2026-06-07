#!/usr/bin/env python3
"""
CUPANG Gmail OAuth Tool
=======================
Read, send, search, manage Gmail via Google OAuth2 API.

Usage:
  gmail_oauth.py setup          — Generate auth URL for OAuth consent
  gmail_oauth.py auth CODE      — Exchange auth code for tokens
  gmail_oauth.py local-auth     — Auto OAuth via local browser
  gmail_oauth.py profile        — Get profile info
  gmail_oauth.py labels         — List labels
  gmail_oauth.py read [MAX]     — Read recent emails
  gmail_oauth.py search QUERY [MAX] — Search emails
  gmail_oauth.py read-msg ID    — Read specific message
  gmail_oauth.py send TO SUBJECT BODY — Send email
  gmail_oauth.py delete ID      — Move to trash
  gmail_oauth.py star ID        — Star a message
  gmail_oauth.py unstar ID      — Unstar a message

Environment:
  GMAIL_CLIENT_ID     — OAuth2 Client ID from GCP
  GMAIL_CLIENT_SECRET — OAuth2 Client Secret from GCP
  GMAIL_TOKEN_FILE    — Token storage path (default: ~/.hermes/gmail_token.json)
"""

import os
import sys
import json
import base64
from pathlib import Path

# OAuth2 scopes
SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.readonly',
]

TOKEN_FILE = os.environ.get(
    'GMAIL_TOKEN_FILE',
    str(Path.home() / '.hermes' / 'gmail_token.json')
)
CREDENTIALS_FILE = str(Path.home() / '.hermes' / 'gmail_credentials.json')
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
REDIRECT_URI_LOCAL = 'http://localhost:8089'


def get_credentials_data():
    """Load client ID/secret from env or credentials file."""
    client_id = os.environ.get('GMAIL_CLIENT_ID')
    client_secret = os.environ.get('GMAIL_CLIENT_SECRET')

    if client_id and client_secret:
        return {
            "installed": {
                "client_id": client_id,
                "project_id": "ninu-498620",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": [REDIRECT_URI, REDIRECT_URI_LOCAL]
            }
        }

    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)

    return None


def get_auth_service():
    """Build and return authenticated Gmail service."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as f:
            json.dump(json.loads(creds.to_json()), f, indent=2)

    if not creds or not creds.valid:
        print("No valid token. Run 'gmail_oauth.py setup' first.")
        sys.exit(1)

    service = build('gmail', 'v1', credentials=creds)
    return service


def cmd_setup():
    """Generate OAuth2 authorization URL."""
    creds_data = get_credentials_data()
    if not creds_data:
        print("No credentials found!")
        print("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET env vars,")
        print("or create ~/.hermes/gmail_credentials.json")
        print()
        print("Steps to get credentials:")
        print("1. Open https://console.cloud.google.com/apis/credentials?project=ninu-498620")
        print("2. Click 'CREATE CREDENTIALS' -> 'OAuth client ID'")
        print("3. Application type: 'Desktop app'")
        print("4. Name: 'CUPANG Gmail OAuth'")
        print("5. Copy Client ID + Client Secret")
        sys.exit(1)

    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds_data, f, indent=2)
    print(f"Credentials saved to {CREDENTIALS_FILE}")

    client_id = creds_data["installed"]["client_id"]
    scope_str = ' '.join(SCOPES)
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope={scope_str}&"
        f"response_type=code&"
        f"access_type=offline&"
        f"prompt=consent"
    )

    print()
    print("Open this URL in your browser to authorize:")
    print()
    print(auth_url)
    print()
    print("After authorization, Google will show an authorization code.")
    print("Copy it and run:")
    print(f"  gmail_oauth.py auth <CODE>")
    print()
    print("--- OR: Auto-redirect (if you have a browser) ---")
    print("Run: gmail_oauth.py local-auth")


def cmd_auth(code):
    """Exchange authorization code for tokens."""
    import requests

    creds_data = get_credentials_data()
    if not creds_data:
        print("No credentials found. Run 'setup' first.")
        sys.exit(1)

    token_data = creds_data["installed"]
    resp = requests.post(token_data["token_uri"], data={
        'code': code,
        'client_id': token_data['client_id'],
        'client_secret': token_data['client_secret'],
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code',
    })

    if resp.status_code != 200:
        print(f"Token exchange failed: {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    tokens = resp.json()

    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

    print(f"Token saved to {TOKEN_FILE}")
    print(f"   Access token expires in: {tokens.get('expires_in', 'unknown')}s")
    print(f"   Has refresh token: {'Yes' if tokens.get('refresh_token') else 'No'}")

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=tokens.get('scope', '').split()
        )

        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        print(f"\nGmail Profile:")
        print(f"   Email: {profile.get('emailAddress')}")
        print(f"   Messages total: {profile.get('messagesTotal')}")
        print(f"   Threads total: {profile.get('threadsTotal')}")
    except Exception as e:
        print(f"\nProfile check failed: {e}")
        print("Token saved anyway - may need refresh")


def cmd_local_auth():
    """Run local server OAuth flow (needs browser)."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_data = get_credentials_data()
    if not creds_data:
        print("No credentials found. Run 'setup' first.")
        sys.exit(1)

    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds_data, f, indent=2)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8089)

    with open(TOKEN_FILE, 'w') as f:
        json.dump(json.loads(creds.to_json()), f, indent=2)

    print(f"Auth success! Token saved to {TOKEN_FILE}")


def cmd_profile():
    """Show Gmail profile."""
    service = get_auth_service()
    profile = service.users().getProfile(userId='me').execute()
    print(f"Email: {profile.get('emailAddress')}")
    print(f"Messages total: {profile.get('messagesTotal')}")
    print(f"Threads total: {profile.get('threadsTotal')}")
    print(f"History ID: {profile.get('historyId')}")


def cmd_labels():
    """List Gmail labels."""
    service = get_auth_service()
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    print(f"Labels ({len(labels)}):")
    for label in sorted(labels, key=lambda x: x['name']):
        label_id = label['id']
        name = label['name']
        print(f"   {name:30s} [{label_id}]")


def cmd_read(max_results=10):
    """Read recent emails."""
    service = get_auth_service()
    results = service.users().messages().list(
        userId='me', maxResults=max_results
    ).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
        return

    print(f"Recent {len(messages)} messages:")
    print()

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId='me', id=msg_ref['id'], format='metadata',
            metadataHeaders=['From', 'To', 'Subject', 'Date']
        ).execute()

        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

        subject = headers.get('Subject', '(no subject)')
        sender = headers.get('From', '(unknown)')
        date_str = headers.get('Date', '')
        snippet = msg.get('snippet', '')[:80]

        if len(subject) > 60:
            subject = subject[:57] + '...'

        print(f"  Subject: {subject}")
        print(f"  From: {sender}")
        print(f"  Date: {date_str}")
        print(f"  Snippet: {snippet}")
        print(f"  ID: {msg_ref['id']}")
        print()


def cmd_search(query, max_results=10):
    """Search emails with Gmail query syntax."""
    service = get_auth_service()
    results = service.users().messages().list(
        userId='me', q=query, maxResults=max_results
    ).execute()
    messages = results.get('messages', [])

    if not messages:
        print(f"No results for: {query}")
        return

    print(f"Search: '{query}' - {len(messages)} results:")
    print()

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId='me', id=msg_ref['id'], format='metadata',
            metadataHeaders=['From', 'To', 'Subject', 'Date']
        ).execute()

        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

        subject = headers.get('Subject', '(no subject)')
        sender = headers.get('From', '(unknown)')
        date_str = headers.get('Date', '')
        snippet = msg.get('snippet', '')[:100]

        print(f"  Subject: {subject}")
        print(f"  From: {sender}")
        print(f"  Date: {date_str}")
        print(f"  Snippet: {snippet}")
        print(f"  ID: {msg_ref['id']}")
        print()


def cmd_read_message(msg_id):
    """Read a specific message by ID."""
    service = get_auth_service()
    msg = service.users().messages().get(
        userId='me', id=msg_id, format='full'
    ).execute()

    headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

    print(f"Message: {msg_id}")
    print(f"From: {headers.get('From', '')}")
    print(f"To: {headers.get('To', '')}")
    print(f"Subject: {headers.get('Subject', '')}")
    print(f"Date: {headers.get('Date', '')}")
    print(f"Labels: {', '.join(msg.get('labelIds', []))}")
    print()

    body = extract_body(msg.get('payload', {}))
    if body:
        print("--- Body ---")
        print(body[:5000])
        if len(body) > 5000:
            print(f"\n... (truncated, {len(body)} total chars)")
    else:
        print("(No readable body)")


def extract_body(payload):
    """Extract plain text body from message payload."""
    if payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

    if payload.get('mimeType') == 'multipart/alternative':
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        for part in parts:
            if part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')

    for part in payload.get('parts', []):
        body = extract_body(part)
        if body:
            return body

    return None


def cmd_send(to, subject, body):
    """Send an email."""
    from email.mime.text import MIMEText

    service = get_auth_service()

    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    result = service.users().messages().send(
        userId='me', body={'raw': raw}
    ).execute()

    print(f"Email sent!")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")
    print(f"   Message ID: {result['id']}")
    print(f"   Thread ID: {result['threadId']}")


def cmd_delete(msg_id):
    """Move message to trash."""
    service = get_auth_service()
    service.users().messages().trash(userId='me', id=msg_id).execute()
    print(f"Message {msg_id} moved to trash.")


def cmd_star(msg_id):
    """Star a message."""
    service = get_auth_service()
    service.users().messages().modify(
        userId='me', id=msg_id,
        body={'addLabelIds': ['STARRED']}
    ).execute()
    print(f"Message {msg_id} starred.")


def cmd_unstar(msg_id):
    """Unstar a message."""
    service = get_auth_service()
    service.users().messages().modify(
        userId='me', id=msg_id,
        body={'removeLabelIds': ['STARRED']}
    ).execute()
    print(f"Message {msg_id} unstarred.")


def cmd_help():
    """Show help."""
    print(__doc__)
    print()
    print("Available commands:")
    cmds = [
        ('setup', 'Generate OAuth2 auth URL'),
        ('auth CODE', 'Exchange auth code for tokens'),
        ('local-auth', 'Auto OAuth via local browser'),
        ('profile', 'Show Gmail profile'),
        ('labels', 'List all labels'),
        ('read [N]', 'Read N recent emails (default 10)'),
        ('search QUERY [N]', 'Search emails (Gmail syntax)'),
        ('read-msg ID', 'Read specific message'),
        ('send TO SUBJECT BODY', 'Send email'),
        ('delete ID', 'Move to trash'),
        ('star ID', 'Star a message'),
        ('unstar ID', 'Unstar a message'),
    ]
    for cmd, desc in cmds:
        print(f"  {cmd:25s} - {desc}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == 'setup':
        cmd_setup()
    elif command == 'auth':
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py auth <CODE>")
            sys.exit(1)
        cmd_auth(sys.argv[2])
    elif command == 'local-auth':
        cmd_local_auth()
    elif command == 'profile':
        cmd_profile()
    elif command == 'labels':
        cmd_labels()
    elif command == 'read':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_read(n)
    elif command == 'search':
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py search <QUERY> [MAX]")
            sys.exit(1)
        q = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        cmd_search(q, n)
    elif command == 'read-msg':
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py read-msg <ID>")
            sys.exit(1)
        cmd_read_message(sys.argv[2])
    elif command == 'send':
        if len(sys.argv) < 5:
            print("Usage: gmail_oauth.py send <TO> <SUBJECT> <BODY>")
            sys.exit(1)
        cmd_send(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py delete <ID>")
            sys.exit(1)
        cmd_delete(sys.argv[2])
    elif command == 'star':
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py star <ID>")
            sys.exit(1)
        cmd_star(sys.argv[2])
    elif command == 'unstar':
        if len(sys.argv) < 3:
            print("Usage: gmail_oauth.py unstar <ID>")
            sys.exit(1)
        cmd_unstar(sys.argv[2])
    elif command in ('help', '-h', '--help'):
        cmd_help()
    else:
        print(f"Unknown command: {command}")
        cmd_help()
        sys.exit(1)
