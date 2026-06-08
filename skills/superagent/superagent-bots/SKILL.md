---
name: superagent-bots
description: "Telegram bots, process orchestration, cron, webhooks, automation."
---

## Operator Profile

Automation architect. Production-grade bots, schedulers, webhooks. Anti-fragile by default. Thinks in flows, triggers, retries, idempotency.

---

## Execution Layer Selection

```
Visual orchestration:   Make.com (no-code), n8n (self-hosted, recommended for VPS)
Scheduled execution:    Python/Node + cron, GitHub Actions (free tier)
Persistent process:     Node.js + pm2 OR systemd (production)
Command interface:      Telegram Bot API (lowest setup friction)
                        Discord.js (community bots)
                        WhatsApp Cloud API (business)
Queue / background:     BullMQ (Redis), in-memory queue (simple), SQLite-backed
```

---

## Production Telegram Bot (Node — anti-duplicate, error-recovery)

```javascript
// bot.js
require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');

const TOKEN = process.env.BOT_TOKEN;
const bot = new TelegramBot(TOKEN, { polling: { interval: 300, autoStart: true, params: { timeout: 10 } } });

// CRITICAL: dedupe by message_id (prevents duplicate replies on bot restart / polling overlap)
const seen = new Map();
const SEEN_TTL = 5 * 60 * 1000; // 5 min
setInterval(() => {
  const now = Date.now();
  for (const [k, t] of seen) if (now - t > SEEN_TTL) seen.delete(k);
}, 60 * 1000);

function isDuplicate(msg) {
  const key = `${msg.chat.id}:${msg.message_id}`;
  if (seen.has(key)) return true;
  seen.set(key, Date.now());
  return false;
}

// Wrap send with retry
async function safeSend(chatId, text, opts = {}, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await bot.sendMessage(chatId, text, { parse_mode: 'Markdown', ...opts });
    } catch (e) {
      if (e.response?.body?.error_code === 429) {
        const wait = (e.response.body.parameters?.retry_after || 1) * 1000;
        await new Promise(r => setTimeout(r, wait));
      } else if (i === retries - 1) {
        console.error('Send failed:', e.message);
        throw e;
      } else {
        await new Promise(r => setTimeout(r, 1000 * (i + 1)));
      }
    }
  }
}

// Handlers
bot.onText(/^\/start$/, async (msg) => {
  if (isDuplicate(msg)) return;
  await safeSend(msg.chat.id, '✅ Online.\nKetik /help buat lihat command.');
});

bot.onText(/^\/help$/, async (msg) => {
  if (isDuplicate(msg)) return;
  await safeSend(msg.chat.id, '*Available:*\n/start\n/status\n/run [arg]');
});

bot.onText(/^\/run (.+)/, async (msg, match) => {
  if (isDuplicate(msg)) return;
  const arg = match[1].trim();
  await safeSend(msg.chat.id, `🚀 Executing: \`${arg}\``);
  // ... do work
});

// Catch-all (only for non-command messages)
bot.on('message', async (msg) => {
  if (msg.text?.startsWith('/')) return;  // already handled by onText
  if (isDuplicate(msg)) return;
  await safeSend(msg.chat.id, `Got it: "${msg.text}"`);
});

// Polling error recovery
bot.on('polling_error', (err) => {
  console.error('[polling]', err.code, err.message);
  // 409 = another instance running → exit so pm2 doesn't loop
  if (err.code === 'ETELEGRAM' && err.response?.body?.error_code === 409) {
    console.error('Another bot instance is running. Exiting.');
    process.exit(1);
  }
});

console.log('Bot online.');
```

```
# .env.example
BOT_TOKEN=123456:ABC-DEF...
```

```
# Run with pm2
pm2 start bot.js --name mybot --max-memory-restart 200M
pm2 save
```

---

## Telegram Webhook Mode (production-scale, no polling)

```javascript
// webhook-bot.js
require('dotenv').config();
const express = require('express');
const TelegramBot = require('node-telegram-bot-api');

const TOKEN = process.env.BOT_TOKEN;
const URL = process.env.WEBHOOK_URL;   // https://yourdomain.com
const PORT = process.env.PORT || 3000;

const bot = new TelegramBot(TOKEN);
bot.setWebHook(`${URL}/bot${TOKEN}`);

const app = express();
app.use(express.json());

app.post(`/bot${TOKEN}`, (req, res) => {
  bot.processUpdate(req.body);
  res.sendStatus(200);
});

bot.onText(/\/start/, (msg) => bot.sendMessage(msg.chat.id, 'Hello via webhook'));

app.listen(PORT, () => console.log(`Webhook server on ${PORT}`));
```

Webhook setup needs Nginx → see m2 for proxy config.

---

## Telegraf (alternative — cleaner middleware API)

```javascript
const { Telegraf } = require('telegraf');
const bot = new Telegraf(process.env.BOT_TOKEN);

bot.use(async (ctx, next) => {
  console.log(`[${ctx.from?.username}] ${ctx.message?.text}`);
  await next();
});

bot.start((ctx) => ctx.reply('Welcome'));
bot.command('status', (ctx) => ctx.reply('🟢 OK'));
bot.on('text', (ctx) => ctx.reply(`Echo: ${ctx.message.text}`));

bot.launch();
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
```

---

## Schedule Patterns

### cron (system-wide)

```bash
crontab -e
# Format: min hour day month dow command
0 8 * * *       /usr/bin/python3 /opt/run/daily.py >> /var/log/run.log 2>&1
0 * * * *       /bin/bash /opt/run/check.sh
*/5 * * * *     /usr/bin/node /opt/run/monitor.js
@reboot         /opt/run/startup.sh
0 3 * * 0       /opt/run/weekly-backup.sh   # Sunday 3am
```

### Node-cron (in-process, for bots that need schedules)

```javascript
const cron = require('node-cron');
cron.schedule('*/15 * * * *', async () => {
  console.log('Running every 15 min');
  // ...
}, { timezone: 'Asia/Jakarta' });
```

### Python APScheduler (when running Python services)

```python
from apscheduler.schedulers.blocking import BlockingScheduler
sched = BlockingScheduler(timezone='Asia/Jakarta')

@sched.scheduled_job('cron', hour=8, minute=0)
def daily(): ...

@sched.scheduled_job('interval', minutes=5)
def heartbeat(): ...

sched.start()
```

---

## Product Brand Bot Pattern (python-telegram-bot)

For e-commerce / product brands, build a structured bot with inline product data, WhatsApp conversion funnel, and order flow.

### Key features to implement:
- **Inline keyboard menus** — /start shows menu button grid (Katalog, Cek Harga, Order, Status, Promo, WA)
- **ConversationHandler flows** — /harga: pick product → see price + WA link; /order: pick → quantity → name → address → order ID
- **Order ID format** — `[BRAND_INITIALS]-[YYMM]-[NNNN]` (e.g., HL-2506-0001)
- **WhatsApp deep link** — every flow ends with `wa.me/[NUMBER]?text=[prefilled_message]`
- **Product data inline** — list of dicts with name, price, description, category, specs — no external DB needed for MVP
- **Error decorator** — `@catch_errors` on every handler + global `error_handler`

### Running:
```bash
export BOT_TOKEN="your_token"
python3 ~/.hermes/[brand]/bots/telegram-bot.py
```

### ⚠️ Hermes Token Masking (CRITICAL for deployment)
Hermes auto-masks API tokens/secrets before any file write — even via Python `open().write()`. The masked form `***` replaces the secret portion, making stored tokens invalid. **You cannot programmatically store bot tokens in files on this platform.**

**Workarounds** (in order of reliability):
1. **User SSH + manual launch**: `ssh ubuntu@host` then `export BOT_TOKEN='real_token' && python3 bot.py`
2. **Systemd service file**: User edits `Environment=BOT_TOKEN=real_token` line directly via `sudo nano /etc/systemd/system/bot.service`
3. **PM2 with env**: `BOT_TOKEN='real_token' pm2 start bot.py --interpreter python3 --name mybot && pm2 save` (user runs this themselves)
4. **Launcher script**: Create `run-bot.sh` that reads from a secrets file that the user creates manually: `echo 'TOKEN' > ~/.hermes/[brand]/secrets/tg_bot_token`

**Do NOT attempt**: `write_file`, Python file writes, or heredoc redirects to store tokens — Hermes will mask them. Always tell the user: "Paste your token and run this command yourself."

**Verify tokens before use**: `curl -s "https://api.telegram.org/bot${TOKEN}/getMe"` — this works because curl execution doesn't trigger the file-write mask.

### Discord bot equivalent (discord.py):
- Use **embed messages** with brand colors (e.g., `discord.Color(0xD4A574)` for gold, dark aesthetic)
- **Fuzzy product search** — aliases dict + partial matching so `!harga bed` matches "Bed Frame+Storage"
- **Command aliases** — `!catalog` → `!katalog`, `!price` → `!harga`, `!diskon` → `!promo`
- **Footer branding** — every embed: `footer.text="BrandName — @handle"`

### Task Tracker / CRUD API Pattern (FastAPI + SQLite)

When building a task tracker or CRUD API alongside an existing FastAPI service (e.g., Haus Living webhook server), see the **FastAPI + SQLite Task Tracker Micro-Pattern** in `superagent-infra` skill. Key points:
- Add endpoints to the existing FastAPI `app` instance (no separate server)
- SQLite with `PRAGMA journal_mode=WAL` for concurrent reads
- Auth via `X-API-Key` header with constant-time comparison
- Nginx location block: `location /task/ { proxy_pass http://haus_api/task/; }`
- Test with Python `urllib.request` — NOT curl (bash glob `***` corrupts tokens)

### python-telegram-bot v20+ Compatibility
- `allow_re_entry=True` is **NOT a valid ConversationHandler kwarg** — removed in v20+
- **Fix**: Use `per_user=True` instead (or omit entirely)
- Always verify bot code against installed library version: `python3 -c "import telegram; print(telegram.__version__)"`

---

## Webhook Server Pattern (FastAPI — production for product brand)

Full webhook server with multiple endpoints and signature verification:

### Endpoints:
```
GET  /                  — API info (brand, version, endpoint list)
POST /webhook/order     — new order notifications
POST /webhook/payment   — payment callbacks (Midtrans SHA512 / Xendit callback token)
POST /webhook/ig        — Instagram events + subscription challenge (X-Hub-Signature-256)
GET  /webhook/health    — health check with stored webhook count
```

### Hermes Security Masking — Token Handling

API tokens/keys are **auto-masked by Hermes** at the file-write and environment-variable level (not just chat output). Bot tokens CANNOT be stored in files or env vars from within Hermes.

**The user must set tokens directly via SSH:**
```bash
export BOT_TOKEN='***'
pm2 start bot.py --name my-bot
```

For systemd services, the user must edit the .env file or service file directly. Never attempt to write tokens to files from within Hermes — they will be masked (`***`) and the bot will fail to start.

### Systemd Timer vs Cron for Monitoring

For health-check or monitoring scripts that don't need LLM reasoning, prefer **systemd timer + service** over Hermes cron jobs:
- Zero token cost
- Zero LLM errors
- More reliable (no provider dependency)

```bash
# Create service
sudo tee /etc/systemd/system/haus-check.service << 'EOF'
[Unit]
Description=Haus Check
[Service]
Type=oneshot
User=ubuntu
ExecStart=/usr/bin/python3 /path/to/check.py --quiet
EOF

# Create timer
sudo tee /etc/systemd/system/haus-check.timer << 'EOF'
[Unit]
Description=Haus Check (every 6h)
[Timer]
OnCalendar=*-*-* 0,6,12,18:00
RandomizedDelaySec=300
Persistent=true
[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now haus-check.timer
```

Only use Hermes cron jobs when the task actually needs LLM reasoning (content generation, analysis, etc.).
- **IG**: HMAC-SHA256 of body with app secret, compare to `X-Hub-Signature-256`

### Persistence:
All incoming webhooks saved as timestamped JSON (e.g., `order_20260605T072901Z_559760.json`) to `~/.hermes/[brand]/webhooks/`

### Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY webhook-server.py .
RUN pip install fastapi uvicorn
EXPOSE 8000
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/webhook/health || exit 1
CMD ["uvicorn", "webhook-server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Webhook Receiver (FastAPI — production-ready)

```python
import os, hmac, hashlib
from fastapi import FastAPI, Request, HTTPException, Header

app = FastAPI()
SECRET = os.getenv('WEBHOOK_SECRET').encode()

def verify(sig: str, body: bytes) -> bool:
    expected = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)

@app.post('/webhook')
async def receive(request: Request, x_signature: str = Header(None)):
    body = await request.body()
    if not x_signature or not verify(x_signature, body):
        raise HTTPException(401, "Invalid signature")
    data = await request.json()
    handlers = {
        'payment.success': on_payment,
        'subscription.renewed': on_renewal,
    }
    h = handlers.get(data.get('type'))
    if h: await h(data)
    return {'ack': True}
```

---

## Idempotent Job Pattern (prevents duplicate work)

```javascript
// Simple file-backed idempotency
const fs = require('fs');
const PROCESSED = './.processed.json';
const seen = fs.existsSync(PROCESSED) ? new Set(JSON.parse(fs.readFileSync(PROCESSED))) : new Set();

function alreadyProcessed(id) { return seen.has(id); }
function markProcessed(id) {
  seen.add(id);
  fs.writeFileSync(PROCESSED, JSON.stringify([...seen]));
}

async function job(item) {
  if (alreadyProcessed(item.id)) return;
  await doWork(item);
  markProcessed(item.id);
}
```

For scale: swap Set → Redis SET, or use a column in postgres with UNIQUE constraint.

---

## Worker Queue (in-memory, no Redis)

```javascript
class Queue {
  constructor(concurrency = 3) {
    this.q = [];
    this.running = 0;
    this.concurrency = concurrency;
  }
  add(task) {
    return new Promise((resolve, reject) => {
      this.q.push({ task, resolve, reject });
      this.tick();
    });
  }
  async tick() {
    while (this.running < this.concurrency && this.q.length) {
      const { task, resolve, reject } = this.q.shift();
      this.running++;
      Promise.resolve(task())
        .then(resolve, reject)
        .finally(() => { this.running--; this.tick(); });
    }
  }
}

const q = new Queue(5);
items.forEach(i => q.add(() => process(i)));
```

For durable queues: BullMQ + Redis.

---

## Multi-bot Orchestration (single process, multiple tokens)

```javascript
const TelegramBot = require('node-telegram-bot-api');

const bots = {
  airdrop: new TelegramBot(process.env.AIRDROP_BOT_TOKEN, { polling: true }),
  alpha:   new TelegramBot(process.env.ALPHA_BOT_TOKEN,   { polling: true }),
};

for (const [name, b] of Object.entries(bots)) {
  b.onText(/\/start/, (msg) => b.sendMessage(msg.chat.id, `Hello from ${name} bot`));
  b.on('polling_error', (e) => console.error(`[${name}]`, e.message));
}
```

Important: each bot needs its own polling — running 2 instances of SAME token = 409 conflict.

---

## Hermes Cron Job Pattern

When creating cron jobs via the `cronjob` tool, **always pin explicit provider/model**:

```
# CORRECT — explicit provider
cronjob(action="create", schedule="0 8 * * *", model={"provider": "openrouter", "model": "openrouter/owl-alpha"}, prompt="...")

# WRONG — null provider can resolve to "Stealth" → error 400
cronjob(action="create", schedule="0 8 * * *", prompt="...")
```

**Why**: Leaving `model` and `provider` as `null` causes Hermes to resolve to a default provider that may not exist (e.g., "Stealth"), resulting in `RuntimeError: Error code: 400 - Provider returned error`. This affects ALL cron jobs — daily-post, evening-prep, weekly-review, monthly-refresh, health-check.

**Fix existing jobs**: `cronjob(action="update", job_id="...", model={"provider": "openrouter", "model": "openrouter/owl-alpha"})`

**For script-only monitoring** (health checks, log rotation, backups): Use **systemd timer** instead of cron — zero tokens, zero provider failures. See `superagent-infra` skill for systemd timer pattern.

**`no_agent=True` cron limitation**: Script paths must be relative to `~/.hermes/scripts/` — `~` and absolute paths are rejected. Prefer systemd timers for script-only jobs.

## Telegram User Account (Telethon MTProto)

When the task requires reading user messages, joining channels/groups, searching across chats, or acting as a **user** (not a bot), use Telethon with MTProto. Bot API cannot access user DMs, group history, or join channels as a member.

### Prerequisites

```bash
pip install telethon
```

Get API credentials at https://my.telegram.org/apps (one-time):
- `api_id` (integer) + `api_hash` (string)
- **Never share these** — they're tied to your phone number

### First-time Login (phone code flow)

```python
import asyncio
from telethon import TelegramClient

async def init_session():
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    
    if not await client.is_user_authorized():
        result = await client.send_code_request(phone)
        # Save phone_code_hash for sign_in
        with open('/tmp/tg_code_hash.txt', 'w') as f:
            f.write(result.phone_code_hash)
        # User checks Telegram app for 5-digit code
        code = input("Enter code from Telegram: ")
        await client.sign_in(phone, code, phone_code_hash=result.phone_code_hash)
    
    me = await client.get_me()
    print(f"Logged in: {me.first_name} (@{me.username})")
    await client.disconnect()
```

### Reuse Existing Session

```python
client = TelegramClient(session_path, api_id, api_hash)
await client.connect()
if not await client.is_user_authorized():
    # Session expired or wrong API_ID — re-login needed
    ...
me = await client.get_me()
```

**`client.start()` asks for phone even with valid session** — use `client.connect()` + `is_user_authorized()` instead to auto-detect existing sessions.

### Key Operations

```python
# List all chats/channels/groups
dialogs = await client.get_dialogs(limit=50)

# Read messages from a chat
messages = await client.get_messages(chat_entity, limit=10)

# Send message
await client.send_message(chat_entity, "Hello!")

# Global search
results = await client.search_global("query", limit=10)

# Join channel by invite link
from telethon.tl.functions.messages import ImportChatInviteRequest
await client(ImportChatInviteRequest(hash=invite_hash))

# Leave chat
await client.delete_dialog(entity)
```

### Session File Management

- Session stored at `~/.hermes/tg_user.session` (default)
- **If `send_code_request` throws `TypeError: bytes or str expected, not NoneType`** → delete the `.session` file and re-init. Stale sessions cause this.
- **`phone_code_hash` is single-use** — if code expires, you must `send_code_request` again (new hash).
- **2-FA accounts**: after `sign_in` with code, if `SESSION_PASSWORD_NEEDED` error, call `sign_in(password=cloud_password)`.

### User Account vs Bot Account — When to Use Which

| Need | Tool |
|------|------|
| Read user DMs / group history | **Telethon user account** |
| Join/leave channels as member | **Telethon user account** |
| Search across all chats | **Telethon user account** |
| Respond to commands (/start, /help) | **Bot API** (node-telegram-bot-api / python-telegram-bot) |
| Send to any user unsolicited | **Bot API** (users must start bot first) |
| Persistent always-on service | **Bot API** (polling/webhook) |
| Read airdrop/crypto groups | **Telethon user account** |
| Post to channel as admin | Either (bot if admin, user if member) |

### Environment Variables

```env
TG_API_ID=12345678
TG_API_HASH=abcdef1234567890...
TG_PHONE=+62812xxxxxxx
TG_SESSION=/home/ubuntu/.hermes/tg_user.session
```

### Pitfalls
- **Phone code hash expires** — don't store it long-term. If login fails, re-send code request.
- **Stale session file** — if Telethon throws cryptic TypeErrors on connect, delete `*.session*` files and re-auth.
- **AWS/VPS IP is fine** — unlike Google, Telegram does NOT block datacenter IPs for MTProto login. Phone codes arrive in the Telegram app itself (not SMS to the server).
- **Rate limits** — Telethon respects Telegram's flood limits automatically. For bulk operations, add `await asyncio.sleep(1)` between calls.
- **Session with wrong API_ID** — `is_user_authorized()` returns `False` even with a valid session file if the `api_id` doesn't match the one used to create the session. Session files are bound to the API_ID+API_HASH pair. If you get `False`, try the original API_ID or create a new session.

### python-telegram-bot v20+ Pattern (Bot API — recommended for new bots)

For new bots, prefer **python-telegram-bot** (v20+) over Telethon. No session management needed — just a bot token from @BotFather.

```bash
pip install python-telegram-bot
```

**Key pattern — Application builder with handlers:**

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "123456:ABC-DEF..."

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📋 List", callback_data="list")],
    ]
    await update.message.reply_text("Welcome!", reply_markup=InlineKeyboardMarkup(keyboard))

async def btn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "stats":
        await query.edit_message_text("Stats here...")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(btn_callback))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```

**PM2 deployment:**

```bash
cat > ecosystem.config.cjs << 'EOF'
module.exports = {
  apps: [{
    name: 'my-bot',
    script: '/home/ubuntu/bot.py',
    interpreter: 'python3',
    cwd: '/home/ubuntu',
    env: { NODE_ENV: 'production' },
    autorestart: true,
    max_restarts: 10,
    restart_delay: 5000,
  }],
};
EOF
pm2 start ecosystem.config.cjs
```

**Key differences from Telethon pattern:**
- No session file needed — bot token is enough
- `python-telegram-bot` uses `Application` builder (v20+), NOT `Updater`
- `CommandHandler("start", callback)` — command name without `/`
- `CallbackQueryHandler` for inline button presses
- `allowed_updates=Update.ALL_TYPES` for full event coverage
- Token in code is OK for PM2-managed bots (not exposed to Hermes file-write masking since PM2 reads from the file directly)

**Token security:** Bot tokens CAN be stored in `.py` files for PM2-managed bots. The Hermes masking only triggers on file-write operations from within Hermes sessions, not on files read by PM2 at runtime. However, still prefer env var `BOT_TOKEN` for production:

```python
import os
BOT_TOKEN=os.get...N", "fallback-token-here")
```

Then set in PM2: `BOT_TOKEN='***' pm2 start ecosystem.config.cjs`

### Telegram Bot API Limitations

**Bot API CANNOT create groups or channels.** Bots can only be added to groups/channels created by users. Flow for multi-group setup:

1. User creates groups/channels manually in Telegram
2. User adds bot as admin to each group
3. User sends `/getid` in each group → bot replies with chat ID
4. User forwards all chat IDs to operator → operator registers them in the bot's config

**Pre-register known groups** via JSON file loaded at startup:

```python
# groups.json — chat_id → topic mapping
{
  "-1003928436326": {"topic": "airdrop", "name": "🎁 Airdrop"},
  "-1004298792270": {"topic": "agent", "name": "⚙️ Pengaturan Agent"},
  "-1004295492283": {"topic": "trading", "name": "💰 Trading"},
  "-1003952018713": {"topic": "haus", "name": "🏠 Haus Living"}
}
```

Load at startup:
```python
import json, os
GROUPS_FILE = "/home/ubuntu/task_bot_groups.json"
def load_groups():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE) as f:
            return json.load(f)
    return {}
def get_topic(chat_id):
    return load_groups().get(str(chat_id), {}).get("topic", "general")
```

**Group registration command:** `/register <topic>` — binds the current chat to a topic category. All tasks created in that group automatically use that topic as the category.

**Multi-topic task tracking:** Each group maps to a topic. `/list` and `/stats` auto-filter by the group's registered topic. No need for users to specify category manually.

### Task Tracker Bot Pattern (Telethon + #command syntax)

Build a task tracker that uses `#<topic> <subcommand>` commands via Telethon:

```python
# Bot parses: #task add <title> | <category> | <note>
#             #task list [N]
#             #task stats
#             #task done <id>
#             #task del <id>
#             #task update <id> | <title> | <cat> | <note>
#             #task help

from telethon import events

@client.on(events.NewMessage(pattern=r"^#", outgoing=True))
async def handle_command(event):
    text = event.raw_text
    parts = text[1:].split(None, 2)  # topic, subcommand, rest
    topic, sub, args = parts[0].lower(), parts[1].lower(), parts[2] if len(parts) > 2 else ""
    
    if topic in ("task", "tasks", "t"):
        if sub == "stats":
            # Call task API → format stats → edit message
            await event.edit(fmt_stats(api_get("/task/stats")))
        elif sub == "add":
            # Parse: title | category | note
            # Call POST /task/add → edit message with result
        # ... etc
```

**Key design decisions:**
- Commands start with `#` (natural for Telethon outgoing message matching)
- Pipe `|` separator for multi-field input (avoids shell quoting issues)
- `events.NewMessage(outgoing=True)` catches messages from the user's own account (not bot)
- Edit the original message `event.edit()` instead of replying (cleaner UX)
- Backend API is FastAPI + SQLite on localhost (separate port, nginx proxied)

### Script

```
scripts/tg_user.py
```

Set `TG_API_ID`, `TG_API_HASH`, `TG_PHONE` env vars. Run `tg_user.py init` first time, then `tg_user.py dialogs`, `tg_user.py read CHAT_ID 10`, etc.

### Script

```
scripts/tg_user.py
```

Set `TG_API_ID`, `TG_API_HASH`, `TG_PHONE` env vars. Run `tg_user.py init` first time, then `tg_user.py dialogs`, `tg_user.py read CHAT_ID 10`, etc.

### File Sending

For sending local files (PDF, ZIP, images, etc.) to Telegram via Bot API, use the `telegram-file-sender` skill + `tg_file_sender.py` tool. This handles the Hermes cache directory requirement (files must be under `~/.hermes/cache/` or the gateway silently drops them).

```bash
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py /path/to/file.pdf --caption "Report"
```

See `telegram-file-sender` skill for full details.

### Task Tracker Reference

See `references/task-tracker.md` for the full FastAPI + SQLite + Telethon bot architecture deployed alongside Haus Living API.

---

- Complete runnable code — no `// TODO` blanks
- `.env.example` with every var listed
- Error handling on every external call
- Polling-mode bots: always include dedupe + polling_error handler
- Webhook-mode bots: always include signature verification
- For long-running scripts: include process supervisor recommendation (pm2/systemd)
- Document idempotency for any job that could re-run
