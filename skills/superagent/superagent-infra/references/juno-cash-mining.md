# Juno Cash (JUNO) Mining Reference

## What is Juno Cash?

Juno Cash is a **Zcash fork** (Zerocash protocol) with:
- **RandomX PoW** (NOT Equihash — despite being a Zcash fork, Juno Cash uses RandomX)
- **Shielded-by-default** transactions (Orchard pool)
- **Transparent addresses only for mining** (coinbase rewards)
- Mined coins must be shielded via `z_shieldcoinbase` before spending
- No trusted setup
- NU6.2 hard fork (Orchard re-enabled at block 296000 mainnet)
- Protocol version 170150

⚠️ **CORRECTION:** Earlier reference said Equihash — Juno Cash actually uses **RandomX** (like Monero). Confirmed from debug log: `RandomX: Auto-enabling fast mode for mining`.

## Binary Installation (v0.9.12, June 2026)

```bash
cd /tmp
wget "https://github.com/juno-cash/junocash/releases/download/v0.9.12/junocash-0.9.12-linux64.tar.gz"
tar xzf junocash-0.9.12-linux64.tar.gz
# Extracts to /tmp/junocash-0.9.12/ (NOT junocash-0.9.12-linux64/)
cp /tmp/junocash-0.9.12/bin/* /usr/local/bin/
chmod +x /usr/local/bin/junocash*
```

⚠️ **Pitfall:** Tar extracts to `junocash-0.9.12/` not `junocash-0.9.12-linux64/`.

Binaries: `junocashd`, `junocash-cli`, `junocashd-wallet-tool`, `junocash-tx`

## ⚠️ Critical Pitfall: Config File Name

junocashd looks for **`junocashd.conf`** (NOT `junocash.conf`) in the datadir. Using the wrong name causes RPC auth failures.

```bash
# Correct config location:
/root/.junocash/junocashd.conf

# Config content:
server=1
rpcuser=junorpc
rpcpassword=<random-hex>
rpcport=8232
rpcallowip=127.0.0.1
listen=1
daemon=0
txindex=1
addressindex=1
timestampindex=1
spentindex=1
```

## Wallet & Mining Address

```bash
# Start daemon first
junocashd -datadir=/root/.junocash -daemon &
sleep 10

# Get mining address (transparent, for coinbase rewards)
junocash-cli -datadir=/root/.junocash t_getminingaddress

# Get shielded address (for receiving funds)
junocash-cli -datadir=/root/.junocash z_getnewaccount
junocash-cli -datadir=/root/.junocash z_getaddressforaccount 0

# Dump private key
junocash-cli -datadir=/root/.junocash dumpprivkey <t-address>
```

⚠️ **Pitfall:** `getnewaddress` is DEPRECATED and DISABLED. Returns error about using `t_getminingaddress` for mining and `z_getnewaddress` for shielded.

⚠️ **Pitfall:** `generate` RPC method only works on regtest chain. On mainnet, use `-gen` daemon flag instead.

## Mining Setup

### Start Mining (Correct Way)

```bash
# Stop existing
pkill -9 junocashd 2>/dev/null
sleep 2
rm -f /root/.junocash/.lock /root/.junocash/junocashd.pid 2>/dev/null

# Start with -gen flag (NOT setgenerate)
junocashd -datadir=/root/.junocash \
  -gen \
  -genproclimit=12 \
  -equihashsolver=default \
  -mineraddress=t1YOURADDRESS \
  -daemon &
```

### Systemd Service

```ini
[Unit]
Description=Juno Cash Daemon
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/junocashd -datadir=/root/.junocash \
  -gen \
  -genproclimit=12 \
  -equihashsolver=default \
  -mineraddress=t1YOURADDRESS
Restart=always
RestartSec=10
LimitNOFILE=65536
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Verify Mining

```bash
# Check mining status
junocash-cli -datadir=/root/.junocash getmininginfo
# Look for: "generate": true, "genproclimit": 12

# Check debug log for mining threads
grep "JunoMonetaMiner started" /root/.junocash/debug.log | wc -l
grep "RandomX: Auto-enabling fast mode" /root/.junocash/debug.log

# Check CPU usage (should show mining threads)
sar -u 1 3
```

⚠️ **Pitfall:** `localhashps` may show 0 H/s during initial sync. This is normal — mining threads start but hashrate isn't reported until node is fully synced. Debug log will show mining threads running regardless.

## Telegram Monitoring & Alerts

### Bot Cannot Create Groups Programmatically

⚠️ **Pitfall:** Telegram Bot API has no `createChat` endpoint. Bots **cannot create groups**. User must:
1. Create group manually in Telegram
2. Add the bot (`@cupang_task_bot`) to the group
3. Send the chat ID to the agent

Extract bot token from environment:
```bash
grep -r "TELEGRAM_BOT_TOKEN" /etc/environment ~/.hermes/.env 2>/dev/null
# Or from service file:
grep -o 'TELEGRAM_BOT_TOKEN=*** /path/to/service
```

### Telegram Alert Script Pattern

Create `/usr/local/bin/juno-monitor` on the mining VPS that sends HTML messages to a Telegram chat:

```bash
#!/bin/bash
# Usage: juno-monitor <check|block> <chat_id>
BOT_TOKEN="YOUR...tg() {
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": ${CHAT_ID}, \"text\": \"$1\", \"parse_mode\": \"HTML\"}" \
        > /dev/null 2>&1
}

# ... (check/block cases)
```

**Pitfall — Emoji in Bash Heredoc:** Writing bash scripts with emoji (⛏️🟢🔴🎉) via heredoc or `write_file` causes syntax errors. **Workaround:** Use Python to write the file locally, then `scp` to VPS:
```python
with open('/tmp/juno-monitor.sh', 'w') as f:
    f.write(script_content)
```

**Pitfall — `write_file` Token Masking:** Hermes auto-masks API tokens (`BOT_TOKEN=*** You CANNOT write a script containing a bot token via `write_file`. **Workaround:** User sets token directly via SSH, or script reads from env var on the VPS itself.

### Cron Jobs for Monitoring

```bash
# /etc/cron.d/juno-mining
# Status report every 6 hours
0 */6 * * * root /usr/local/bin/juno-monitor check CHAT_ID >> /root/.junocash/cron.log 2>&1
# Block check every 5 minutes
*/5 * * * * root /usr/local/bin/juno-block-check CHAT_ID >> /root/.junocash/cron.log 2>&1
```

### Wallet.dat Backup

Always backup `wallet.dat` immediately after wallet generation:
```bash
# From agent VPS:
sshpass -p 'PASSWORD' scp root@MINING_IP:/root/.junocash/wallet.dat \
    ~/.hermes/data/junocash_wallet_backup.dat
```

⚠️ **Pitfall — Seed Phrase:** junocashd auto-generates mnemonic seed on first launch but **never displays it**. Only `wallet.dat` contains the keys. To get seed phrase, use `junocashd-wallet-tool`. Private keys per address can be obtained via `dumpprivkey`.

## Node Sync

```bash
# Check sync progress
junocash-cli -datadir=/root/.junocash getblockchaininfo
# Look for: verificationprogress (0.0 to 1.0)

# Check connections
junocash-cli -datadir=/root/.junocash getconnectioncount
```

Juno Cash network has ~400K+ blocks. Fresh sync takes several hours.

## Security: Backup Private Keys

Always dump and backup private keys for ALL transparent addresses:

```bash
for addr in $(junocash-cli -datadir=/root/.junocash listaddresses | grep "t1" | tr -d " \","); do
  echo "Address: $addr"
  junocash-cli -datadir=/root/.junocash dumpprivkey "$addr"
done
```

Also backup `wallet.dat`:
```bash
scp root@VPS_IP:/root/.junocash/wallet.dat ~/.hermes/data/junocash_wallet_backup.dat
```

## ⚠️ Pitfall: Lock File

If junocashd was killed ungracefully, `.lock` file remains and prevents restart:
```bash
rm -f /root/.junocash/.lock /root/.junocash/junocashd.pid
```

## Status Script

Create `/usr/local/bin/juno-status`:
```bash
#!/bin/bash
echo "========== JUNO CASH MINING STATUS =========="
echo "Time: $(date)"
echo "---"
junocash-cli -datadir=/root/.junocash getmininginfo 2>&1 | grep -E "blocks|difficulty|localhashps|localsolps|networkhashps|generate"
echo "---"
junocash-cli -datadir=/root/.junocash getblockchaininfo 2>&1 | grep -E "blocks|headers|verificationprogress"
echo "---"
echo "CPU: $(ps aux | grep junocashd | grep -v grep | awk '{sum+=$3} END {printf "%.1f%%", sum}')"
echo "Mining Threads: $(grep -c 'JunoMonetaMiner started' /root/.junocash/debug.log 2>/dev/null)"
echo "Connections: $(junocash-cli -datadir=/root/.junocash getconnectioncount 2>/dev/null)"
echo "=============================================="
```

## Profitability Notes

- **CPU mining only** — RandomX is CPU-friendly but VPS CPU hashrate is low
- Network hashrate is small (~400-900 H/s) — solo mining viable with enough CPU
- 12-core VPS might get ~200-500 H/s on RandomX with fast mode (2GB dataset)
- No major pools support Juno Cash — solo mining only
- For consistent payout, consider Monero (XMR) via XMRig pool instead

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `generate: false` in getmininginfo | Using `setgenerate` RPC (regtest only) | Use `-gen` daemon flag |
| `localhashps: 0` | Normal during sync | Wait for full sync; check debug log for mining threads |
| RPC error -28 "Loading wallet" | Wallet still loading on first run | Wait and retry |
| `error code: -28 "disabled while reindexing"` | Node is reindexing/syncing | Wait for sync to complete |
| Lock file prevents restart | Ungraceful shutdown | Remove `.lock` and `.pid` files |
