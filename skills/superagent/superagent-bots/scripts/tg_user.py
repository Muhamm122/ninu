#!/usr/bin/env python3
"""
Telegram User Account Tool — Telethon MTProto
=====================================================
Read, send, search, join/leave channels and groups as a USER (not bot).

Usage:
  tg_user.py init           — Login with phone + code (first time)
  tg_user.py me             — Get account info
  tg_user.py dialogs [N]    — List N chats/channels/groups (default 30)
  tg_user.py read CHAT [N]  — Read N messages from chat (by ID)
  tg_user.py send CHAT MSG  — Send message to chat (by ID)
  tg_user.py search QUERY [N] — Global search
  tg_user.py channels       — List subscribed channels
  tg_user.py groups         — List groups
  tg_user.py join LINK      — Join channel/group by invite link
  tg_user.py leave CHAT     — Leave channel/group (by ID)

Environment:
  TG_API_ID    — Telegram API ID (from my.telegram.org/apps)
  TG_API_HASH  — Telegram API Hash
  TG_PHONE     — Phone number with country code (e.g. +62812...)
  TG_SESSION   — Session file path (default: ~/.hermes/tg_user.session)
"""

import os, sys, asyncio
from pathlib import Path

SESSION = os.environ.get('TG_SESSION', str(Path.home() / '.hermes' / 'tg_user.session'))
API_ID = os.environ.get('TG_API_ID', '')
API_HASH = os.environ.get('TG_API_HASH', '')
PHONE = os.environ.get('TG_PHONE', '')


async def get_client():
    from telethon import TelegramClient
    if not API_ID or not API_HASH:
        print("Set TG_API_ID and TG_API_HASH env vars!")
        print("Get them at: https://my.telegram.org/apps")
        sys.exit(1)
    client = TelegramClient(SESSION, int(API_ID), API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Not authorized. Run 'tg_user.py init' first.")
        sys.exit(1)
    return client


async def cmd_init():
    from telethon import TelegramClient
    phone = PHONE or input("Enter phone (with country code, e.g. +62812...): ")

    client = TelegramClient(SESSION, int(API_ID), API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already authorized: {me.first_name} (@{me.username})")
        await client.disconnect()
        return

    result = await client.send_code_request(phone)
    code = input("Enter the code from Telegram: ")

    try:
        await client.sign_in(phone, code, phone_code_hash=result.phone_code_hash)
        me = await client.get_me()
        print(f"Logged in: {me.first_name} (@{me.username})")
    except Exception as e:
        if 'SESSION_PASSWORD_NEEDED' in str(e) or 'password' in str(e).lower():
            pw = input("Enter 2FA cloud password: ")
            await client.sign_in(password=pw)
            me = await client.get_me()
            print(f"Logged in: {me.first_name} (@{me.username})")
        else:
            print(f"Login failed: {e}")

    await client.disconnect()


async def cmd_me():
    client = await get_client()
    me = await client.get_me()
    print(f"Name: {me.first_name} {me.last_name or ''}")
    print(f"Username: @{me.username or 'none'}")
    print(f"Phone: {me.phone}")
    print(f"ID: {me.id}")
    print(f"Premium: {'Yes' if me.premium else 'No'}")
    await client.disconnect()


async def cmd_dialogs(n=30):
    client = await get_client()
    dialogs = await client.get_dialogs(limit=n)

    for d in dialogs:
        entity = d.entity
        name = d.name or 'Unknown'
        if hasattr(entity, 'megagroup') and entity.megagroup:
            icon = '👥'
        elif hasattr(entity, 'broadcast') and entity.broadcast:
            icon = '📢'
        elif hasattr(entity, 'username') and entity.username:
            icon = '👤'
        else:
            icon = '💬'
        unread = d.unread_count
        marker = f' ({unread} new)' if unread else ''
        username = f'@{entity.username}' if hasattr(entity, 'username') and entity.username else ''
        print(f"{icon} {name}{marker} — ID:{entity.id} {username}")

    await client.disconnect()


async def cmd_read(chat_id, n=10):
    client = await get_client()
    entity = await client.get_entity(int(chat_id))
    messages = await client.get_messages(entity, limit=n)

    for msg in reversed(messages):
        if not msg.text:
            continue
        sender = 'Unknown'
        if msg.sender:
            sender = getattr(msg.sender, 'first_name', 'Unknown')
        time_str = msg.date.strftime('%H:%M') if msg.date else ''
        print(f"[{time_str}] {sender}: {msg.text[:80]}")

    await client.disconnect()


async def cmd_send(chat_id, text):
    client = await get_client()
    entity = await client.get_entity(int(chat_id))
    msg = await client.send_message(entity, text)
    name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
    print(f"Sent to {name}: {text[:60]}")
    await client.disconnect()


async def cmd_search(query, n=10):
    client = await get_client()
    results = await client.search_global(query, limit=n)

    for msg in results:
        sender = getattr(msg.sender, 'first_name', '?') if msg.sender else '?'
        chat = getattr(msg.chat, 'title', None) or getattr(msg.chat, 'first_name', '?') if msg.chat else '?'
        print(f"{chat} — {sender}: {msg.text[:60]}")

    await client.disconnect()


async def cmd_channels():
    client = await get_client()
    dialogs = await client.get_dialogs(limit=200)
    for d in dialogs:
        if hasattr(d.entity, 'broadcast') and d.entity.broadcast:
            members = getattr(d.entity, 'participants_count', '?')
            username = f'@{d.entity.username}' if hasattr(d.entity, 'username') and d.entity.username else ''
            print(f"📢 {d.name} ({members}) {username} — ID:{d.entity.id}")
    await client.disconnect()


async def cmd_groups():
    client = await get_client()
    dialogs = await client.get_dialogs(limit=200)
    for d in dialogs:
        if hasattr(d.entity, 'megagroup') and d.entity.megagroup:
            members = getattr(d.entity, 'participants_count', '?')
            username = f'@{d.entity.username}' if hasattr(d.entity, 'username') and d.entity.username else ''
            print(f"👥 {d.name} ({members}) {username} — ID:{d.entity.id}")
    await client.disconnect()


async def cmd_join(link):
    from telethon.tl.functions.messages import ImportChatInviteRequest
    client = await get_client()
    hash_val = link.split('/')[-1] if '/' in link else link
    result = await client(ImportChatInviteRequest(hash=hash_val))
    print(f"Joined: {result}")
    await client.disconnect()


async def cmd_leave(chat_id):
    client = await get_client()
    entity = await client.get_entity(int(chat_id))
    name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
    await client.delete_dialog(entity)
    print(f"Left: {name}")
    await client.disconnect()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == 'init': asyncio.run(cmd_init())
    elif cmd == 'me': asyncio.run(cmd_me())
    elif cmd == 'dialogs': asyncio.run(cmd_dialogs(int(sys.argv[2]) if len(sys.argv) > 2 else 30))
    elif cmd == 'read':
        if len(sys.argv) < 3: print("Usage: tg_user.py read <CHAT_ID> [N]"); sys.exit(1)
        asyncio.run(cmd_read(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10))
    elif cmd == 'send':
        if len(sys.argv) < 4: print("Usage: tg_user.py send <CHAT_ID> <MSG>"); sys.exit(1)
        asyncio.run(cmd_send(sys.argv[2], sys.argv[3]))
    elif cmd == 'search':
        if len(sys.argv) < 3: print("Usage: tg_user.py search <QUERY> [N]"); sys.exit(1)
        asyncio.run(cmd_search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10))
    elif cmd == 'channels': asyncio.run(cmd_channels())
    elif cmd == 'groups': asyncio.run(cmd_groups())
    elif cmd == 'join':
        if len(sys.argv) < 3: print("Usage: tg_user.py join <INVITE_LINK>"); sys.exit(1)
        asyncio.run(cmd_join(sys.argv[2]))
    elif cmd == 'leave':
        if len(sys.argv) < 3: print("Usage: tg_user.py leave <CHAT_ID>"); sys.exit(1)
        asyncio.run(cmd_leave(sys.argv[2]))
    elif cmd in ('help', '-h', '--help'): print(__doc__)
    else: print(f"Unknown: {cmd}")
