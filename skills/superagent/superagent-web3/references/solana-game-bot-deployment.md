# Solana Game Bot Deployment — Full Reference

This document captures the **end-to-end workflow** for taking a community-maintained Node.js + socket.io game bot (like `owntown-farming-bot`) from GitHub to a self-hosted systemd service on a VPS, plus troubleshooting the most common anti-bot patterns.

## When to Use This Guide

- User pastes a GitHub link to a game bot and says "deploy this" / "jalankan ini"
- A bot is auth'd but disconnects immediately (anti-bot gates)
- Bot works locally but fails on VPS (IP / region / captcha block)
- User wants to scale a single bot to multiple wallets or processes

## Class of Bots Covered

- **Solana MMO / clicker / farming games** (owntown.fun, pimp.zone, similar)
- **socket.io client + REST auth** (typical pattern)
- **Wallet-based auth** (sign nonce, get JWT, connect with token)
- **Hardcoded wallet in source** (author's own wallet, must be replaced)
- **Single-file bot.js** with npm dependencies

Not covered: Python bots, headless browser automation for dApps, browser-extensions (Phantom/MetaMask flow), flashbots/sniping.

## Deployment Recipe (Full)

### Step 1: Clone and Inspect

```bash
cd /tmp
git clone <repo-url> <game>-bot
cd <game>-bot
cat README.md   # Check for: required env vars, account setup, deposit requirements
```

Look for:
- Required SOL/token balance
- Discord/Telegram account prerequisites
- Referral codes needed
- System requirements (RAM, CPU)

### Step 2: Identify Hardcoded Values to Patch

```bash
# Find hardcoded wallet addresses (88-char base58 strings)
grep -nE "[1-9A-HJ-NP-Za-km-z]{43,88}" bot.js | head
# Find hardcoded paths to /root/ or author-specific dirs
grep -nE "/root/|\.junocash|owntown-attack" bot.js | head
# Find const MY_PLAYER_ID
grep -n "MY_PLAYER_ID" bot.js | head
# Find TOKEN_PATH
grep -n "TOKEN_PATH" bot.js | head
# Find bs58 import
grep -n "bs58" bot.js | head
# Check if dotenv is used
head -3 bot.js
```

### Step 3: Install Deps

```bash
npm install
# If package.json missing dotenv:
npm install dotenv
```

### Step 4: Apply Patches

Run `scripts/patch-game-bot.py` from the scripts/ directory. The script:
1. Fixes bs58 import (`.default` → bare `require`)
2. Adds `require('dotenv').config();` at line 1
3. Replaces hardcoded WALLET_ADDR with env-driven
4. Replaces hardcoded WALLET_FILE with env-driven
5. Converts `const MY_PLAYER_ID` to `let` with env fallback
6. Moves TOKEN_PATH from `/tmp/` to `./data/` (PrivateTmp-safe)

Verify syntax after:
```bash
node -c bot.js
```

### Step 5: Generate Wallet

Use the wallet generation snippet in the SKILL.md "Standard Deployment Recipe" Step 5. Save to `data/wallet.json` with `chmod 600`.

### Step 6: Create .env

```bash
WALLET_PRIVATE_KEY=<base58 88-char>
WALLET_ADDRESS=<base58 32-44 char>
WALLET_FILE=/home/ubuntu/.hermes/skills/<game>/data/wallet.json
RPC_URL=https://api.mainnet-beta.solana.com
INTERVAL_SEC=30
LOG_LEVEL=info
# Optional: MY_PLAYER_ID=<your-uuid>  (usually auto-set by server on first profile event)
```

`chmod 600` the .env. **Do not** rely on systemd `EnvironmentFile` to source .env — bot must explicitly `require('dotenv').config()`.

### Step 7: Install Systemd Service

Copy the template from `templates/game-bot-systemd.service`. Edit:
- `<GAME_NAME>` → actual directory name
- `User=ubuntu` → your service user
- `WorkingDirectory`, `ReadWritePaths` → match your install path

```bash
sudo cp /home/ubuntu/.hermes/skills/<game>/scripts/<game>.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now <game>
sudo systemctl status <game>
```

### Step 8: Verify

```bash
tail -f /home/ubuntu/.hermes/skills/<game>/logs/bot.log
# Look for: "Auth OK", "Connected", "Profile received"
# Not look for: "toast: Account frozen", "CAPTCHA_REQUIRED", "INSUFFICIENT_*"
```

## Anti-Bot Gate Diagnostic Flow

When the bot loops through connect → disconnect:

```
Bot started
    ↓
auth/verify → 200 OK (got JWT)
    ↓
socket connect
    ↓
socket.on('disconnect') reason='io server disconnect'  ← STOP here
    ↓
Did you get a `toast` event right before? Check your disconnect handler.
    ↓
    ├── "Account frozen pending review" → wallet banned. Generate new wallet + fund + restart
    ├── "INSUFFICIENT_OTWN balance=0 required=5000" → token gate. Swap SOL→OTWN via Jupiter
    ├── "CAPTCHA_REQUIRED" → server needs Turnstile. See Turnstile section below
    └── (no toast) → check rate limit, IP block, or stale token
```

### Verifying token holdings before auth

```javascript
const solana = require('@solana/web3.js');
const spl = require('@solana/spl-token');

async function checkTokenGate(wallet, mint, minAmount) {
  // Use mint filter, NOT programId — works for Token-2022
  const res = await fetch('https://api.mainnet-beta.solana.com', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      jsonrpc: '2.0', id: 1, method: 'getTokenAccountsByOwner',
      params: [wallet, {mint}, {encoding: 'jsonParsed'}]
    })
  }).then(r => r.json());
  const accounts = res.result.value;
  if (accounts.length === 0) return {ok: false, balance: 0};
  const balance = accounts[0].account.data.parsed.info.tokenAmount.uiAmount;
  return {ok: balance >= minAmount, balance};
}
```

### Cloudflare Turnstile Integration (via 2captcha)

```javascript
const https = require('https');

async function getTurnstileToken(sitekey, pageUrl, apiKey) {
  // 1. Submit task
  const taskId = await new Promise((resolve, reject) => {
    const req = https.request({
      hostname: '2captcha.com',
      path: `/in.php?key=${apiKey}&method=turnstile&sitekey=${sitekey}&pageurl=${encodeURIComponent(pageUrl)}&json=1`,
      method: 'GET'
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve(JSON.parse(data).request));
    });
    req.on('error', reject);
    req.end();
  });
  // 2. Poll for result (typically 5-20s)
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 5000));
    const result = await new Promise((resolve, reject) => {
      const req = https.request({
        hostname: '2captcha.com',
        path: `/res.php?key=${apiKey}&action=get&id=${taskId}&json=1`,
        method: 'GET'
      }, res => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => resolve(JSON.parse(data)));
      });
      req.on('error', reject);
      req.end();
    });
    if (result.status === 1) return result.request;  // token
    if (result.request !== 'CAPCHA_NOT_READY') throw new Error(result.request);
  }
  throw new Error('Turnstile solve timeout');
}

// In your auth flow:
const token = await getTurnstileToken(
  '0x4AAAAAADkUP4PC2himgsCK',  // sitekey
  'https://owntown.fun',
  process.env.TWOCAPTCHA_KEY
);
const verify = await fetch('https://api.owntown.app/api/auth/verify', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({wallet, nonce, signature, captchaToken: token})
});
```

### Re-Triggering 2captcha Failures

If Turnstile token is rejected:
- Token may have expired (TTL ~120s)
- Sitekey may have rotated (re-extract from JS bundle)
- 2captcha account balance may be low (check `/res.php?action=getbalance`)
- Game server may have a per-IP quota — wait an hour before retrying

## Common Bot Architecture Patterns

### Token persistence

```javascript
const fs = require('fs');
const TOKEN_PATH = './data/bot-token.txt';
function saveToken(t) { fs.writeFileSync(TOKEN_PATH, t); }
function loadToken() {
  try { return fs.readFileSync(TOKEN_PATH, 'utf8').trim(); }
  catch { return null; }
}
```

### Exponential backoff on disconnect

```javascript
let backoff = 1000;
socket.on('disconnect', () => {
  setTimeout(() => connect(), backoff);
  backoff = Math.min(backoff * 2, 60000);  // cap at 60s
});
socket.on('connect', () => { backoff = 1000; });
```

### Cycle game actions (mining → fishing → combat)

```javascript
const CYCLES = ['MINING', 'FISHING', 'COMBAT'];
let cycleIndex = 0;
setInterval(() => {
  const action = CYCLES[cycleIndex % CYCLES.length];
  socket.emit('action', {type: action, timestamp: Date.now()});
  cycleIndex++;
}, 30_000);  // every 30s
```

### Antidetect modules (humanize.js pattern)

For high-detection games, the bot can include a `humanize.js` module that:
- Uses `crypto.randomInt` instead of `Math.random` for jittered intervals
- Rotates User-Agent strings (pool of 7+ fingerprints)
- Inserts "session breaks" of 20-90 minutes every few hours
- Adds micro-delays of 200-1200ms between actions
- Simulates idle animation patterns
- Gates activity by time-of-day (active hours vs sleep)

This is **not a real bypass** of Cloudflare Turnstile or fingerprinting — but it raises the baseline effort needed for anti-cheat to flag. Combine with residential proxy for serious work.

## Failure Modes & Diagnoses

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Bot loops every 30s, no auth attempt | .env not loaded, WALLET_PRIVATE_KEY undefined | Add `require('dotenv').config()` at line 1 |
| "Cannot read properties of undefined (reading 'encode')" | bs58 v5+ import pattern | Use `require('bs58')` not `.default` |
| Auth OK but socket disconnects with "Account frozen" | Server-side ban on this wallet | Generate new wallet, fund, retry |
| Auth returns "CAPTCHA_REQUIRED" (not "INSUFFICIENT_OTWN") | Multiple failed auths from this IP/wallet | Wait 1+ hour, switch IP, or use 2captcha |
| Bot runs locally, fails on VPS | IP region block | Residential proxy from allowed region |
| Token-2022 always shows balance 0 | Wrong programId filter | Use `{"mint": mint}` not `programId: "TokenkegQ..."` |
| Author's wallet used by bot, no control | Missing patches | Run `scripts/patch-game-bot.py` |
| "Cannot find module 'dotenv'" | Missing dependency | `npm install dotenv` from scripts/ dir |
| Token file disappears on every restart | `PrivateTmp=true` in systemd | Move TOKEN_PATH to ./data/ AND set `PrivateTmp=false` |
| Bot connects, gets `inventory:update`, but actions don't progress | Token gate failed silently | Check log for `toast: INSUFFICIENT_*` |
| Multiple wallets from same author GitHub | Each bot is hardcoded to one wallet | Each needs its own .env + wallet.json + service |

## Re-Deploying the Same Bot to Multiple Wallets

```bash
# Generate wallet 2
node -e "..." > data/wallet2.json
# Create .env2 with WALLET_FILE pointing to wallet2.json
# Create second service
cp /etc/systemd/system/<game>.service /etc/systemd/system/<game>-2.service
# Edit to use .env2 and different log file
sudo systemctl daemon-reload
sudo systemctl enable --now <game>-2
```

Each instance needs its own port (if the bot listens) and its own log file. Each wallet has its own token file at `./data/wallet<id>-token.txt`.

## What Not To Do (Hard-Won Lessons)

1. **Don't spam auth** — every failed auth tightens the server-side block. Once you see "CAPTCHA_REQUIRED" with the right wallet+IP+token combo, stop and switch strategy.
2. **Don't rely on Tor** — Cloudflare Turnstile rejects Tor exit nodes 90%+ of the time.
3. **Don't use the author's hardcoded wallet** — your funds are at risk, and the wallet is likely already flagged.
4. **Don't store token in `/tmp/` with `PrivateTmp=true`** — token gets wiped on every restart, causing infinite re-auth loop.
5. **Don't check Token-2022 balances with `programId` filter** — always use mint filter.
6. **Don't expect antidetect to bypass Cloudflare** — it raises the bar but doesn't clear it. Use paid captcha service for production.
7. **Don't trust "solved 5000 captchas" success rate** — Turnstile solve rate is ~95% with 2captcha but tokens can still be rejected server-side if quota is exhausted.
8. **Don't use the same wallet across multiple bots** — each bot needs its own wallet. Multi-bot on same wallet triggers immediate account freeze.
