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

- Complete runnable code — no `// TODO` blanks
- `.env.example` with every var listed
- Error handling on every external call
- Polling-mode bots: always include dedupe + polling_error handler
- Webhook-mode bots: always include signature verification
- For long-running scripts: include process supervisor recommendation (pm2/systemd)
- Document idempotency for any job that could re-run
