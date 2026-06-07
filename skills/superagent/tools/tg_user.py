#!/usr/bin/env python3
"""
CUPANG Telegram User Account Tool — Telethon MTProto
=====================================================
Full Telegram user account access: read, send, search, channels, groups.

Usage:
  tg_user.py init           — Login with phone + code (first time)
  tg_user.py me             — Get account info
  tg_user.py dialogs        — List all chats/channels/groups
  tg_user.py read CHAT [N]  — Read N messages from chat
  tg_user.py send CHAT MSG  — Send message to chat
  tg_user.py search QUERY [N] — Global search
  tg_user.py channels       — List subscribed channels
  tg_user.py groups         — List groups
  tg_user.py join LINK      — Join channel/group by invite link
  tg_user.py leave CHAT     — Leave channel/group
  tg_user.py forward SRC DST ID — Forward message

Environment:
  TG_API_ID    — Telegram API ID (from my.telegram.org)
  TG_API_HASH  — Telegram API Hash
  TG_PHONE     — Phone number with country code (e.g. +62812...)
  TG_SESSION   — Session file path (default: ~/.hermes/tg_user.session)
"""

import os, sys, asyncio, json
from pathlib import Path

SESSION = os.environ.get('TG_SESSION', str(Path.home() / '.hermes' / 'tg_user.session'))
API_ID = os.environ.get('TG_API_ID', '')
API_HASH = os.environ.get('TG_API_HASH', '')
PHONE = os.environ.get('TG_PHONE', '')


async def get_client():
    from telethon import TelegramClient
    if not API_ID or not API_HASH:
        print("❌ Set TG_API_ID and TG_API_HASH env vars!")
        print("Get them at: https://my.telegram.org/apps")
        sys.exit(1)
    client = TelegramClient(SESSION, int(API_ID), API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Not authorized. Run 'tg_user.py init' first.")
        sys.exit(1)
    return client


async def cmd_init():
    from telethon import TelegramClient
    if not PHONE:
        phone = input("📱 Enter phone number (with country code, e.g. +62812...): ")
    else:
        phone = PHONE
    
    client = TelegramClient(SESSION, int(API_ID), int(API_HASH))
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Already authorized as: {me.first_name} ({me.phone})")
        await client.disconnect()
        return
    
    await client.send_code_request(phone)
    code = input("📧 Enter the code you received: ")
    
    try:
        await client.sign_in(phone, code)
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} ({me.phone})")
    except Exception as e:
        if '2FA' in str(e) or 'password' in str(e).lower():
            password = input("🔒 Enter 2FA password: ")
            await client.sign_in(password=password)
            me = await client.get_me()
            print(f"✅ Logged in as: {me.first_name} ({me.phone})")
        else:
            print(f"❌ Login failed: {e}")
    
    await client.disconnect()


async def cmd_me():
    client = await get_client()
    me = await client.get_me()
    print(f"👤 Account Info:")
    print(f"   Name: {me.first_name} {me.last_name or ''}")
    print(f"   Username: @{me.username or 'none'}")
    print(f"   Phone: {me.phone}")
    print(f"   ID: {me.id}")
    print(f"   Premium: {'Yes' if me.premium else 'No'}")
    print(f"   Verified: {'Yes' if me.verified else 'No'}")
    await client.disconnect()


async def cmd_dialogs():
    client = await get_client()
    dialogs = await client.get_dialogs(limit=50)
    
    print(f"💬 Chats ({len(dialogs)}):")
    print()
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
        marker = f'({unread} new)' if unread else ''
        username = f'@{entity.username}' if hasattr(entity, 'username') and entity.username else ''
        
        print(f"  {icon} {name} {marker}")
        print(f"     ID: {entity.id} {username}")
    
    await client.disconnect()


async def cmd_read(chat_id, n=10):
    client = await get_client()
    entity = await client.get_entity(int(chat_id))
    messages = await client.get_messages(entity, limit=n)
    
    name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
    print(f"📬 {name} — Latest {len(messages)} messages:")
    print()
    
    for msg in reversed(messages):
        if not msg.text:
            continue
        sender = 'Unknown'
        if msg.sender:
            sender = getattr(msg.sender, 'first_name', 'Unknown')
            if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                sender += f' {msg.sender.last_name}'
        
        time_str = msg.date.strftime('%H:%M') if msg.date else ''
        text = msg.text[:80].replace('\n', ' ')
        
        print(f"  [{time_str}] {sender}: {text}")
        print(f"     ID: {msg.id}")
        print()
    
    await client.disconnect()


async def cmd_send(chat_id, text):
    client = await get_client()
    entity = await client.get_entity(int(chat_id))
    msg = await client.send_message(entity, text)
    
    name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
    print(f"✅ Sent to {name}:")
    print(f"   Message: {text[:100]}")
    print(f"   ID: {msg.id}")
    
    await client.disconnect()


async def cmd_search(query, n=10):
    client = await get_client()
    results = await client.search_global(query, limit=n)
    
    print(f"🔍 '{query}' — {len(results)} results:")
    print()
    
    for msg in results:
        sender = 'Unknown'
        if msg.sender:
            sender = getattr(msg.sender, 'first_name', 'Unknown')
        
        chat = 'Unknown'
        if msg.chat:
            chat = getattr(msg.chat, 'title', None) or getattr(msg.chat, 'first_name', 'Unknown')
        
        print(f"  📧 {chat} — {sender}: {msg.text[:60]}")
        print(f"     ID: {msg.id}")
        print()
    
    await client.disconnect()


async def cmd_channels():
    client = await get_client()
    dialogs = await client.get_dialogs(limit=200)
    
    channels = [d for d in dialogs if hasattr(d.entity, 'broadcast') and d.entity.broadcast]
    print(f"📢 Channels ({len(channels)}):")
    print()
    for d in channels:
        entity = d.entity
        name = d.name or 'Unknown'
        username = f'@{entity.username}' if hasattr(entity, 'username') and entity.username else ''
        members = getattr(entity, 'participants_count', '?')
        print(f"  {name} ({members} members) {username}")
        print(f"     ID: {entity.id}")


async def cmd_groups():
    client = await get_client()
    dialogs = await client.get_dialogs(limit=200)
    
    groups = [d for d in dialogs if hasattr(d.entity, 'megagroup') and d.entity.megagroup]
    print(f"👥 Groups ({len(groups)}):")
    print()
    for d in groups:
        entity = d.entity
        name = d.name or 'Unknown'
        username = f'@{entity.username}' if hasattr(entity, 'username') and entity.username else ''
        members = getattr(entity, 'participants_count', '?')
        print(f"  {name} ({members} members) {username}")
        print(f"     ID: {entity.id}")


async def cmd_join(link):
    client = await get_client()
    result = await client(functions.messages.ImportChatInviteRequest(
        hash=link.split('/')[-1] if '/' in link else link
    ))
    print(f"✅ Joined: {result}")


async def cmd_leave(chat_id):
    client = await get_client()
    entity = await client.get_entity(int(chat_id))
    await client.delete_dialog(entity)
    name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
    print(f"👋 Left: {name}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == 'init':
        asyncio.run(cmd_init())
    elif cmd == 'me':
        asyncio.run(cmd_me())
    elif cmd == 'dialogs':
        asyncio.run(cmd_dialogs())
    elif cmd == 'read':
        chat = sys.argv[2] if len(sys.argv) > 2 else 'me'
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        asyncio.run(cmd_read(chat, n))
    elif cmd == 'send':
        if len(sys.argv) < 4:
            print("Usage: tg_user.py send <CHAT_ID> <MESSAGE>")
            sys.exit(1)
        asyncio.run(cmd_send(sys.argv[2], sys.argv[3]))
    elif cmd == 'search':
        if len(sys.argv) < 3:
            print("Usage: tg_user.py search <QUERY> [MAX]")
            sys.exit(1)
        q = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        asyncio.run(cmd_search(q, n))
    elif cmd == 'channels':
        asyncio.run(cmd_channels())
    elif cmd == 'groups':
        asyncio.run(cmd_groups())
    elif cmd == 'join':
        if len(sys.argv) < 3:
            print("Usage: tg_user.py join <INVITE_LINK>")
            sys.exit(1)
        asyncio.run(cmd_join(sys.argv[2]))
    elif cmd == 'leave':
        if len(sys.argv) < 3:
            print("Usage: tg_user.py leave <CHAT_ID>")
            sys.exit(1)
        asyncio.run(cmd_leave(sys.argv[2]))
    elif cmd in ('help', '-h', '--help'):
        print(__doc__)
    else:
        print(f"Unknown: {cmd}")
