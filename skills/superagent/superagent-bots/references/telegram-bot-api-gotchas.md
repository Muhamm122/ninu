# Telegram Bot API Gotchas

## Bot Cannot Create Groups

Bot API **cannot create groups/channels programmatically**. The bot must be **added by the user** to a group they created.

**Workaround flow:**
1. User creates group manually in Telegram
2. User adds bot as admin
3. User sends `/getid` in group → bot replies with chat ID
4. Developer registers chat ID in bot's group registry

## Bot Cannot Receive Group Messages Unless:

1. Bot is added as member/admin, AND
2. Privacy mode is disabled (via @BotFather → Bot Settings → Group Privacy → Turn off), OR
3. Message mentions the bot (@botname)

## Telethon Session Pattern

Use `client.connect()` + `is_user_authorized()` — NOT `client.start()`:

```python
await client.connect()
if not await client.is_user_authorized():
    log.error("Session not authorized!")
    return
me = await client.get_me()
```

`client.start()` without phone/token raises `ValueError`.

## Session API ID Mismatch

If `is_user_authorized()` returns `False` despite valid session file, the API_ID doesn't match the session. Session files are bound to the API_ID used during creation.
