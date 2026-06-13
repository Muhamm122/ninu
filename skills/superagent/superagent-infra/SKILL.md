---
name: superagent-infra
description: "VPS, infrastructure, deployment, SSH, nginx, docker, systemd."
---

## VPS Quick-Start Checklist (Fresh Ubuntu 24.04)

When user asks "bantu setting VPS baru", run these in order:

### 1. Initial Access & Hardening
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Create non-root user (if root only)
adduser ubuntu && usermod -aG sudo ubuntu

# SSH hardening
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Firewall
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw --force enable

# fail2ban
sudo apt install -y fail2ban && sudo systemctl enable --now fail2ban

# Timezone
sudo timedatectl set-timezone Asia/Jakarta
```

### 2. Core Runtime
```bash
# Python 3.11 + venv
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential
python3 -m venv /opt/venv && echo 'source /opt/venv/bin/activate' >> ~/.bashrc

# Node.js 20 + PM2
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs && sudo npm install -g pm2

# Docker
curl -fsSL https://get.docker.com | sudo bash
sudo systemctl enable --now docker && sudo usermod -aG docker ubuntu

# Nginx + Certbot
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable --now nginx
```

### 3. Hermes Agent
```bash
# Install Hermes (adjust to current install method)
pip install hermes-agent  # or from source

# Hermes gateway
hermes gateway start
hermes gateway status
```

### 4. Verify
```bash
# All services running
sudo systemctl status nginx docker fail2ban
pm2 list
ufw status
python3 --version && node --version && docker --version
```

### Post-Setup Questions to Ask User
1. Provider? (AWS/DO/Vultr/Hetzner) — affects metadata
2. Purpose? (mining/trading/web/all-in-one) — affects service selection
3. Domain? — for Nginx + SSL config
4. Backup target? (GitHub SSH/S3/rclone)

## Operator Profile

Senior systems provisioner. Commands that execute correctly on first run. Zero theory padding. Production-aware defaults.

---

## Bootstrap (Debian-family, Ubuntu 22.04/24.04)

```bash
# System refresh
apt update && apt upgrade -y

# Core tooling
apt install -y curl wget git unzip nano htop ufw fail2ban build-essential \
               software-properties-common ca-certificates gnupg lsb-release

# Firewall (default deny inbound except SSH/HTTP/HTTPS)
ufw default deny incoming && ufw default allow outgoing
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp
ufw --force enable

# fail2ban for SSH protection
systemctl enable --now fail2ban

# Timezone (adjust)
timedatectl set-timezone Asia/Jakarta
```

---

## Runtime Provisioning

### Node.js v20 LTS + pm2

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
npm install -g pm2 yarn pnpm
pm2 startup systemd -u root --hp /root  # follow printed command
pm2 save
```

### Python 3.11+ with venv

```bash
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
python3.11 -m venv /opt/venv
echo 'source /opt/venv/bin/activate' >> ~/.bashrc
```

### Bun (faster Node alt, used for OpenClaw plugins)

```bash
curl -fsSL https://bun.sh/install | bash
echo 'export BUN_INSTALL="$HOME/.bun"' >> ~/.bashrc
echo 'export PATH="$BUN_INSTALL/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Docker

```bash
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker
usermod -aG docker $USER  # logout/login for group to apply
```

### Nginx + Certbot (Let's Encrypt)

```bash
apt install -y nginx certbot python3-certbot-nginx
systemctl enable --now nginx
# Per-domain cert (after DNS pointed):
certbot --nginx -d example.com -d www.example.com \
        --non-interactive --agree-tos -m operator@example.com --redirect
```

---

## Persistent Process Patterns (choose one)

### A. pm2 — simplest, restart on reboot

```bash
pm2 start app.js --name "myapp"
pm2 start "python -u main.py" --name "myapp-py" --interpreter none
pm2 save           # persist process list
pm2 logs myapp    # tail logs
pm2 monit          # interactive monitor
pm2 restart myapp
pm2 delete myapp
```

### B. systemd service — most durable

```bash
cat > /etc/systemd/system/myapp.service <<'EOF'
[Unit]
Description=MyApp
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/node /opt/myapp/index.js
Restart=always
RestartSec=5
StandardOutput=append:/var/log/myapp.log
StandardError=append:/var/log/myapp.err
Environment="NODE_ENV=production"
EnvironmentFile=/opt/myapp/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now myapp
systemctl status myapp
journalctl -fu myapp     # follow logs
```

### C. screen — interactive, survives SSH disconnect

```bash
screen -S myapp                  # create named session
# (run command inside)
# Detach: Ctrl-A then D
screen -ls                       # list sessions
screen -r myapp                  # reattach
screen -X -S myapp quit          # kill session
```

### D. tmux — modern alternative to screen

```bash
tmux new -s myapp                # create named session
# Detach: Ctrl-B then D
tmux ls                          # list
tmux attach -t myapp             # reattach
tmux kill-session -t myapp       # kill
```

---

## Multi-Service VPS Deployment Pattern

When deploying multiple services on a single VPS (API, webhook, n8n, bots, landing page), use this composed pattern:

### Directory layout
```
~/.hermes/[brand]/
├── bots/           # telegram-bot.py, discord-bot.py
├── api/            # webhook-server.py + Dockerfile
├── scraper/        # scraper.py (competitor/price/trend monitoring)
├── logo/           # SVG logos + PNG watermarks
├── landing-page/   # index.html (served by Nginx directly)
├── n8n-data/       # n8n persistent workspace
├── webhooks/       # incoming webhook JSON storage
├── data/           # redis + postgres volumes
├── docker-compose.yml
├── .env.example
└── services.py     # service manager CLI (start/stop/status/health/logs)
```

### Nginx config — multi-upstream with rate limiting
Define all upstreams in nginx.conf, then route in sites-available:
```nginx
# /etc/nginx/nginx.conf — upstream block
upstream haus_api   { server 127.0.0.1:8000; }
upstream n8n        { server 127.0.0.1:5678; }
upstream freellmapi { server 127.0.0.1:3001; }

# Rate limit zones
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
```

```nginx
# /etc/nginx/sites-available/[brand]
server {
    listen 80 default_server;
    # Landing page served directly by Nginx (zero backend needed)
    location / {
        root /var/www/[brand];
        index index.html;
    }
    # API + webhooks
    location /api/     { limit_req zone=api; proxy_pass http://haus_api/; }
    location /webhook/ { limit_req zone=api; proxy_pass http://haus_api/webhook/; }
    # n8n (websocket upgrade needed)
    location /workflow/ {
        proxy_pass http://n8n/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    # Health check
    location /health { return 200 '{"status":"ok"}'; add_header Content-Type application/json; }
    # Block attack paths
    location ~ /\.git { return 404; }
    location ~ /\.env { return 404; }
}
```

### Service Manager CLI pattern
Create `services.py` that wraps all services:
```bash
python3 services.py status   # check all (systemd + pm2 + docker + port + pid)
python3 services.py health   # curl health endpoints
python3 services.py start    # start all
python3 services.py stop     # stop all
```
Each service type uses different status detection: systemd (`systemctl is-active`), pm2 (`pm2 jlist`), docker (`docker inspect`), port (`ss -tlnp`), pid (`pgrep`).

### Docker Compose for brand infrastructure
```yaml
services:
  api:       # FastAPI webhook server
  n8n:       # workflow automation (image: n8nio/n8n:latest)
  redis:     # session cache + rate limit
  postgres:  # orders + analytics
```

### n8n via Docker — gotcha
n8n container writes to `/home/node/.n8n/config`. If volume mount has wrong permissions, n8n crashes with `EACCES: permission denied`. Fix:
```bash
sudo chown -R 1000:1000 ~/.hermes/[brand]/n8n-data
sudo docker restart n8n
```
n8n health check: `curl http://localhost:5678/healthz` → `{"status":"ok"}`

### Bot deployment — Hermes token masking
Hermes auto-masks API tokens before any file write (`write_file`, Python `open()`, shell redirects). The masked form `***` replaces the secret portion, making stored tokens invalid. **Cannot store tokens programmatically.**

**Working deployment methods** (user must be involved):
1. `BOT_TOKEN='***' pm2 start bot.py --interpreter python3 --name brand-bot && pm2 save` (user runs directly)
2. Systemd service file where user edits `Environment=BOT_TOKEN=***` line manually
3. Launcher script that reads from secrets file (`~/.hermes/<brand>/secrets/tg_bot_token`) that user creates via SSH

**Do NOT attempt**: `write_file`, Python `open().write()`, or heredoc to store tokens — Hermes will mask them every time.

### Full deployment command sequence
```bash
# 1. Install infra
sudo apt install -y nginx certbot python3-certbot-nginx
# Docker already installed via get.docker.com (see Docker section above)

# 2. Copy landing page to Nginx root
sudo mkdir -p /var/www/[brand]
sudo cp ~/.hermes/[brand]/landing-page/index.html /var/www/[brand]/
sudo chown -R www-data:www-data /var/www/[brand]/

# 3. Configure Nginx (see multi-upstream config above)
sudo nginx -t && sudo systemctl reload nginx

# 4. Start n8n
sudo docker run -d --name n8n --restart unless-stopped \
  -p 5678:5678 -v ~/.hermes/[brand]/n8n-data:/home/node/.n8n \
  -e GENERIC_TIMEZONE=Asia/Jakarta n8nio/n8n:latest
sudo chown -R 1000:1000 ~/.hermes/[brand]/n8n-data  # fix perms

# 5. Start API (background via Hermes terminal(background=true))
# 6. Verify all: python3 services.py health
```

---

## Nginx Reverse Proxy Template

```nginx
# /etc/nginx/sites-available/myapp
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;
    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Sec headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header Strict-Transport-Security "max-age=63072000" always;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90s;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

## Deployment Sequences

### Node app

```bash
cd /opt && git clone https://github.com/user/repo.git myapp && cd myapp
cp .env.example .env && nano .env
npm ci --production        # ci > install for reproducibility
pm2 start ecosystem.config.js   # or: pm2 start index.js --name myapp
pm2 save
```

### Python ASGI (FastAPI / Starlette)

```bash
cd /opt && git clone ... && cd myapp
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pm2 start "gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000" \
       --name myapp-py --interpreter none
pm2 save
```

---

## Fault Isolation Protocol

```
1. Collect:  exact error + last command + env (OS, version, package versions)
2. Inspect:  journalctl -xe -n 100  |  pm2 logs myapp --lines 100
             nginx -t  |  ss -tlnp  |  df -h  |  free -h
3. Diagnose: root cause in 1 sentence
4. Resolve:  exact corrective command(s)
5. Verify:   confirmation command (curl, ps, systemctl status)
6. Harden:   config delta to prevent recurrence
```

---

## Monitoring & Health

```bash
# Resource snapshot
htop                              # interactive
df -h && free -h && uptime         # one-liner
pm2 monit                         # pm2 dashboard

# Logs
tail -f /var/log/nginx/error.log
journalctl -fu myapp
pm2 logs myapp --lines 200

# Network
ss -tlnp                          # listening ports
ss -tnp | head -20                # active connections

# Disk usage hotspots
du -h --max-depth=1 /var | sort -h | tail
```

---

## Backup Strategy

### Minimal (single app)

```bash
# /opt/backup.sh
#!/usr/bin/env bash
set -euo pipefail
DATE=$(date +%F)
DEST=/opt/backups
mkdir -p "$DEST"

# Files
tar czf "$DEST/files-$DATE.tar.gz" /opt/myapp --exclude=node_modules --exclude=venv

# Postgres
sudo -u postgres pg_dumpall | gzip > "$DEST/pg-$DATE.sql.gz"

# Rotate (keep 7 days)
find "$DEST" -type f -mtime +7 -delete

# Optional: rclone to remote
# rclone copy "$DEST" remote:backups/myapp
```

```bash
chmod +x /opt/backup.sh
crontab -e
# 0 3 * * *  /opt/backup.sh >> /var/log/backup.log 2>&1
```

### Full VPS Backup (multi-service disaster recovery)

For VPS running Hermes + multiple services (FreeLLMAPI, Nginx, Docker/n8n, PM2 apps, bots, webhook API, landing page), a full backup must capture config, source, and metadata — but **exclude rebuildable artifacts** (node_modules, sessions, logs) to keep the archive small.

**10-step backup directory structure:**
```
haus-backup-TIMESTAMP/
├── hermes/          # ~/.hermes/ (config, skills, brand data, wallets, cron, memories)
├── systemd/         # /etc/systemd/system/*.service (custom services)
├── nginx/           # /etc/nginx/ (nginx.conf, sites-available/enabled, snippets)
├── pm2/             # PM2 dump + process list JSON
├── docker/          # docker-compose.yml, container list, .env.example
├── www/             # /var/www/[brand]/ (landing page)
├── freellmapi/      # /opt/freellmapi/ source (server+client+shared, NO node_modules)
├── opencode-proxy/  # OpenCode proxy source (NO node_modules)
├── meta/            # System info JSON, apt-packages.txt, pip-requirements.txt, npm-global.txt, crontab.txt
├── MANIFEST.json    # Backup metadata (timestamp, IP, service list, version)
├── backup.sh        # Self-contained backup script
└── restore.sh       # Self-contained restore script
```

**Key exclusion patterns (rsync):**
```bash
rsync -a --exclude='node/' \
         --exclude='hermes-agent/node_modules/' \
         --exclude='bin/' \
         --exclude='logs/*.log' \
         --exclude='sessions/' \
         /home/ubuntu/.hermes/ "${BACKUP_DIR}/hermes/"
```

**Post-backup verification:**
```bash
# Create archive + SHA256
tar -czf archive.tar.gz haus-backup-TIMESTAMP/
sha256sum archive.tar.gz > archive.tar.gz.sha256

# Verify integrity
sha256sum -c archive.tar.gz.sha256  # → OK

# Verify critical files present
tar -tzf archive.tar.gz | grep -E "(config\.yaml|wallets\.enc|jobs\.json|nginx\.conf|freellmapi\.service|docker-compose\.yml|restore\.sh)"
```

**Restore on fresh VPS (3 commands):**
```bash
scp archive.tar.gz ubuntu@NEW_IP:/home/ubuntu/
ssh ubuntu@NEW_IP "tar -xzf archive.tar.gz && bash haus-backup-*/restore.sh"
```

**Restore script auto-installs:** system deps (Python, Node, Docker, Nginx, PM2, Certbot), restores all dirs, runs `npm install --production` for FreeLLMAPI + OpenCode proxy, restarts Nginx, reinstalls pip packages, starts Docker/n8n.

**Typical archive size:** ~500MB for a full Hermes + multi-service VPS (1.1GB hermes data compresses well, node_modules excluded).

**What is NOT backed up (by design):**
- `node_modules/` — rebuilt via `npm install` during restore
- `sessions/` — chat logs, not critical
- `logs/` — rotated logs, not needed
- Bot tokens — Hermes auto-masks them; user sets manually on new VPS
- Hermes binary — reinstalled during restore

See `references/hermes-miniapp-deploy.md` for deploying React+Vite+Express Telegram Mini Apps behind nginx subpath.
See `references/9router-db-reference.md` for 9Router SQLite DB schema, queries, and key management rules.
See `references/vps-backup-restore.md` for full script templates.
See `references/freellmapi-key-management.md` for adding API keys, version checks, and fallback chain details.
See `references/juno-cash-mining.md` for Juno Cash (JUNO) Zcash-fork mining — junocashd config pitfalls, solo mining, wallet generation, and profitability notes.
See `references/juno-cash-mining.md` for Juno Cash (JUNO) Zcash-fork mining setup — junocashd config pitfalls, solo mining, wallet generation, and profitability notes.
See `scripts/health-monitor.py` for a ready-to-use multi-service health checker (systemd + PM2 + Docker + resource alerts).

## FastAPI + SQLite Task Tracker Micro-Pattern

When adding a task/audit log API to an existing FastAPI service, use this pattern:

```python
# DB helper (call per-request, close in finally)
def _get_task_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT DEFAULT 'general', status TEXT DEFAULT 'done', note TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    db.commit()
    return db

# Auth: constant-time header compare
def _validate_api_key(x_api_key):
    return hmac.compare_digest(x_api_key.strip(), os.getenv("TASK_API_KEY", "change-me")) if x_api_key else False

# CRUD: POST /task/add, GET /task/list?status=done&category=x&limit=50, PUT /task/{id}, DELETE /task/{id}, GET /task/stats
```

Key: SQLite for <10k rows (zero config), `PRAGMA journal_mode=WAL` for concurrent reads, ISO 8601 string timestamps, status enum (`done`/`pending`/`cancelled`), always `db.close()` in `finally`.

**Test with Python urllib** — NOT curl (bash glob `***` corrupts Bearer tokens).

### Delivering backup to user (when user is on Telegram/messaging)

Users cannot run `scp` from a messaging app. Free file hosts (file.io, transfer.sh, gofile.io) fail for 500MB+ archives. Serve the backup via Nginx on port 80 (already open in AWS SG):

```bash
# 1. Copy backup to Nginx-accessible path
sudo mkdir -p /var/www/[brand]/backup
sudo cp haus-vps-backup-*.tar.gz /var/www/[brand]/backup/
sudo cp haus-vps-backup-*.tar.gz.sha256 /var/www/[brand]/backup/

# 2. Add /download/ location to existing Nginx site config
sudo sed -i '/^}$/i\    location /download/ {\n        alias /var/www/[brand]/backup/;\n        autoindex on;\n        sendfile on;\n        tcp_nopush on;\n    }' /etc/nginx/sites-enabled/[brand]

# 3. Reload and verify
sudo nginx -t && sudo systemctl reload nginx
curl -sI http://localhost/download/haus-vps-backup-*.tar.gz | head -3  # should be 200 OK

# 4. Give user the download link
echo "Download: http://$(curl -s ifconfig.me)/download/haus-vps-backup-TIMESTAMP.tar.gz"

# 5. AFTER user confirms download — REMOVE the endpoint + files for security
sudo rm -rf /var/www/[brand]/backup/
# Remove the /download/ location block from Nginx config
sudo systemctl reload nginx
```

**Security**: The `/download/` endpoint is an unauthenticated backdoor. ALWAYS remove it after the user confirms download. Tell the user: "⚠️ Link ini temporary — gua bakal hapus setelah lo konfirm udah download."

---

## SSH Access Patterns

### Password Auth — Often Disabled by Default

Modern VPS providers (AWS, Vultr, DigitalOcean, Linode) often disable password auth via SSH by default. If SSH with password fails:

**Symptoms**: `Permission denied (publickey,password)` even with correct password.

**Solutions** (pick one):
1. **Key-based auth** (preferred): Generate SSH key pair, add public key to VPS via provider dashboard
2. **sshpass**: Install on agent VPS first: `apt install -y sshpass`, then: `sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no user@IP "command"`
3. **expect script**: Install `expect`, automate password entry
4. **Provider console**: Use VPS provider's web console (VNC/serial) to enable password auth

**Agent limitation**: If agent VPS doesn't have `sshpass`/`expect` installed and can't install (no root), agent cannot SSH to target VPS with password. User must either:
- Install `sshpass` on agent VPS first
- Use key-based auth
- Run setup script directly on target VPS via provider web console

### SSH Key Setup (Recommended)

```bash
# On agent VPS (one-time)
ssh-keygen -t ed25519 -C "hermes-agent" -f ~/.ssh/id_ed25519 -N ""

# Copy public key to target VPS
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@TARGET_IP

# Test
ssh -i ~/.ssh/id_ed25519 user@TARGET_IP "echo OK"
```

### Non-Root User Setup

```bash
# On target VPS (as root)
adduser agent
usermod -aG sudo agent
mkdir -p /home/agent/.ssh
cp ~/.ssh/authorized_keys /home/agent/.ssh/
chown -R agent:agent /home/agent/.ssh
chmod 700 /home/agent/.ssh
chmod 600 /home/agent/.ssh/authorized_keys

# Disable root SSH (after confirming agent user works)
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd
```

---

## Security Hardening (production checklist)

```
✅ SSH: disable password auth, key-only, change port (>1024)
✅ SSH: PermitRootLogin prohibit-password (or no, if non-root user setup)
✅ ufw: deny-all default, explicit allows only
✅ fail2ban: enabled with SSH jail
✅ Updates: unattended-upgrades for security patches
✅ Secrets: .env mode 600, never in git, never in shell history
✅ Nginx: HSTS, security headers, hide version (server_tokens off)
✅ Database: bind to localhost only unless intentional
✅ Backup: automated daily, rotated, tested restore
✅ Monitor: log rotation configured (/etc/logrotate.d/)
```

---

## Common OpenClaw/Hermes VPS Patterns

```bash
# Run agent + telegram bot in screen session
screen -S claude-bot
cd ~/.openclaw/workspace
claude --resume                    # or: bun run telegram
# Ctrl-A D to detach

# Tail openclaw logs while in another session
tail -f ~/.openclaw/logs/*.log

# Check active agents
ps aux | grep -E 'claude|openclaw|hermes' | grep -v grep
```

---

## Systemd + Node.js Path Pitfall

**CRITICAL**: Node.js installed via Hermes lives at `~/.local/bin/node` (symlink to `~/.hermes/node/bin/node`), NOT at `/usr/bin/node`. Systemd services fail with exit code 203/EXEC if using wrong path.

**Fix**: Always use `$(which node)` in systemd service files:
```bash
NODE_PATH=$(which node)
# Use $NODE_PATH in ExecStart, NOT /usr/bin/node
```

**Also**: When running systemd as non-root user, set `User=ubuntu` and `Group=ubuntu` in the service file. WorkingDirectory must be accessible by that user (not `/tmp` — use `/opt/` or `/home/ubuntu/`).

**Debug systemd failures**:
```bash
sudo journalctl -u <service> --no-pager -n 30   # check logs
systemctl status <service> --no-pager            # check status
```

---

## Node.js CLI Tools with Interactive TUI on Headless VPS

Many Node.js CLI tools (9router, etc.) show an interactive terminal menu. On headless VPS (no TTY, no display), the menu auto-selects "exit" after a timeout, causing the process to die immediately.

**Pattern**: Check for `--tray`, `--no-browser`, `--skip-update`, `--daemon`, or `--headless` flags. Use them in systemd `ExecStart`:

```ini
# ✅ Correct — runs in background/tray mode
ExecStart=/path/to/node /path/to/cli.js --tray --no-browser --skip-update --log

# ❌ Wrong — interactive TUI auto-exits in non-TTY
ExecStart=/path/to/node /path/to/cli.js
```

**Symptom**: Service starts, prints "Ready in 0ms", then immediately "Exiting..." and exits 0. Journal shows no error — just a clean shutdown.

**Fix for systray deps**: Some tools try to init a system tray icon (systray2 on Linux). If missing, install it: `cd <tool_dir> && npm install systray2@2.1.4`. The `--tray` flag usually handles this gracefully on headless.

---

## SUPERAGENT Version Upgrade

When user sends a newer SUPERAGENT ZIP (vX.Y):

```bash
# 1. Extract
mkdir -p /tmp/superagent-vX.Y && cd /tmp/superagent-vX.Y
unzip -o <zip-path>

# 2. Install core files (overwrite)
cp openclaw/{AGENTS.md,panduan.md,STANDARD.md,TOOLS.md,IDENTITY.md,SOUL.md,USER.md,MEMORY.md,TIME.md,HEARTBEAT.md,CHANGELOG.md,SKILLS.lock,.env.example} ~/.hermes/

# 3. Install skills (merge — keeps user-created skills)
cp -r openclaw/skills/* ~/.hermes/skills/superagent/

# 4. Install tools (merge — keeps user-created tools like cc_gen.py, pioneer_agent.py)
cp -r openclaw/tools/* ~/.hermes/skills/superagent/tools/

# 5. Verify
# - Core files present and non-empty
# - Skill count (should be 30+ for v4.1+)
# - hermes-crypto-agent: 15 references + 14 scripts
# - Services still running: freellmapi, opencode-free-proxy

# 6. Don't overwrite user-created additions:
# - browser-agent/ skill (installed separately)
# - cc_gen.py, pioneer_agent.py (custom tools)
# - wallets.enc (encrypted wallet storage)
```

v4.1 deltas over v4.0: STANDARD.md, skills m19-m29 + x4-x7, tools skill_market/mcp_builder/reflection/research_q/prd/scene_prep/eval/hids/desktop_control/content/backtest/humanizer.

---

## Competitor & Market Monitoring Scraper Pattern

For brand/product companies, build a multi-mode scraper toolkit:

```bash
python3 scraper.py ig --hashtag "mebelminimalis" --limit 20     # IG competitor posts
python3 scraper.py price --keyword "sofa minimalis" --marketplace tokopedia  # Price monitoring
python3 scraper.py trend --keyword "furniture jakarta"           # Keyword research + autocomplete
python3 scraper.py news --limit 10                              # Industry news
python3 scraper.py monitor --config monitor.json                # Batch all from config
```

### Scraper modes:
- **ig** — IG hashtag monitor via mobile API endpoint (limited; falls back to DuckDuckGo search)
- **price** — Tokopedia/Shopee price monitoring (API or web fallback)
- **trend** — DuckDuckGo autocomplete + related search + news
- **news** — Furniture/industry news via search
- **monitor** — JSON config driving all scrapers with delay between tasks

### Output patterns:
- Each run saves timestamped JSON to `scraper-data/` (e.g., `price_tokopedia_sofa_minimalis_20260605T073502Z.json`)
- Results include `scraped_at` ISO timestamp, `count`, and `results` array

### Marketplace API notes:
- Tokopedia: `ace.tokopedia.com/search/v2.5/product/v4` may return 503 from server IPs — fall back to DuckDuckGo `site:tokopedia.co.id` search
- Shopee: API requires specific headers (`X-Shopee-Language`, `X-API-SOURCE`) and prices are stored ×100000

---

## Server Hardening Checklist (post-deploy)

After all services are running, apply these in order:

### 1. UFW Firewall
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Nginx)
sudo ufw allow 443/tcp   # HTTPS (Nginx)
sudo ufw --force enable
```
All backend ports (3001, 5678, 19912, 8000) become unreachable from internet — only via Nginx reverse proxy on 80/443.

### ⚠️ Temporary File Serving — Remove After Use

If you need to serve a file temporarily via Nginx (e.g., backup download):
1. Create the endpoint with a `location /download/` block
2. **Remove it immediately after download** — don't leave it as a persistent backdoor
3. Remember: `sites-enabled/` may be a separate copy, not a symlink — edit both!

Removing a temporary download endpoint:
```bash
sudo sed -i '/location \/download\//,/^    }/d' /etc/nginx/sites-available/yoursite
sudo sed -i '/location \/download\//,/^    }/d' /etc/nginx/sites-enabled/yoursite
sudo nginx -t && sudo systemctl reload nginx
```

### 2. Log Rotation
| Service | Method | Config path |
|---------|--------|-------------|
| Nginx | Built-in logrotate | `/etc/logrotate.d/nginx` (daily, rotate 14, compress) |
| PM2 | Custom logrotate | `/etc/logrotate.d/pm2` — `copytruncate` to avoid file-handle issues |
| FreeLLMAPI | journald drop-in | `/etc/systemd/journald.conf.d/haus-living.conf` — 500M max, 14 day retention, compressed |
| Docker/n8n | Docker daemon config | `/etc/docker/daemon.json` — json-file driver, 50M max-size, 5 files max |

PM2 logrotate config example:
```
/home/ubuntu/.pm2/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

Docker daemon.json example:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
```

**After changing Docker daemon.json**: `sudo systemctl restart docker` (this restarts all containers — n8n will auto-restart if `--restart unless-stopped`)

### 3. PM2 Startup (auto-start on reboot)
```bash
pm2 startup systemd -u ubuntu --hp /home/ubuntu
# Run the sudo command PM2 prints
pm2 save
```

### 4. Remove temporary endpoints
After backup delivery via `/download/`, remove from Nginx config and reload. Do NOT leave unauthenticated file-serving endpoints open.

### Docker `sudo` requirement
On many VPS setups, `ubuntu` user is NOT in the `docker` group. All `docker` commands require `sudo`. This affects:
- Service manager scripts (`services.py`)
- Health monitor scripts (`health-monitor.py`)
- Backup scripts that capture container lists

**Fix (pick one)**:
- `sudo usermod -aG docker ubuntu` then logout/login (preferred for single-user VPS)
- Prefix all docker commands with `sudo` in scripts (works without group change)
- `sudo chmod 666 /var/run/docker.sock` (temporary, resets on reboot — NOT recommended)

### ⚠️ Nginx sites-enabled/ May NOT Be a Symlink

On some VPS setups (especially those created by AI agents or non-standard provisioning), `/etc/nginx/sites-enabled/` contains **separate file copies**, not symlinks to `sites-available/`.

**Consequence**: Editing `sites-available/myapp` does NOT affect `sites-enabled/myapp`. Both must be independently edited.

**Diagnose**:
```bash
# Check if sites-enabled is a symlink
ls -la /etc/nginx/sites-enabled/myapp
# If it shows a regular file (not "-> ../sites-available/myapp"), it's a copy
```

**Fix when removing a config block**:
```bash
# Must edit BOTH files
sudo sed -i '/location \\/download\\//,/^    }/d' /etc/nginx/sites-available/myapp
sudo sed -i '/location \\/download\\//,/^    }/d' /etc/nginx/sites-enabled/myapp
sudo nginx -t && sudo systemctl reload nginx
```

**Prevention**: When adding a new site config, create a proper symlink:
```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/myapp
```

See `references/pitfalls.md` (in superagent-llm-proxy skill) for additional gotchas: Nginx symlink diagnostic, Docker sudo fix, `intensity()` vs `int()` typo, and Pillow deprecation notes.

---

## Health Monitor Pattern

For multi-service VPS (Nginx + FreeLLMAPI + PM2 apps + Docker/n8n), build a Python health checker:

```python
# health-monitor.py — run standalone or via systemd timer
SERVICES = {
    "nginx":        {"type": "systemd", "health_url": "http://localhost/health"},
    "freellmapi":   {"type": "systemd", "health_url": "http://localhost:3001/v1/models"},
    "opencode-proxy":{"type": "pm2", "pm2_name": "opencode-free-proxy", "health_url": "http://localhost:19912/health"},
    "haus-api":     {"type": "pm2", "pm2_name": "haus-api", "health_url": "http://localhost:8000/webhook/health"},
    "n8n":          {"type": "docker", "container": "n8n", "health_url": "http://localhost:5678/healthz"},
}
THRESHOLDS = {"warn_disk_pct": 80, "crit_disk_pct": 90, "warn_ram_pct": 80, "crit_ram_pct": 90}
```

**Service type detection:**
- `systemd`: `systemctl is-active <name>` → "active" = running
- `pm2`: `pm2 show <name> | grep status` → "online" = running
- `docker`: `sudo docker inspect -f '{{.State.Status}}' <container>` → "running" = running

**Health check**: HTTP GET to health_url, expect 200 OK.

**Output formats**: `--json` for programmatic use, `--quiet` for script/cron use (exit code 1 = CRIT alerts), text (default) for human reading.

### Scheduling: systemd timer (preferred) vs cron

**For script-only monitoring (no LLM needed):** Use **systemd timer** — zero tokens, zero provider failures:
```bash
# /etc/systemd/system/haus-health-check.service
[Unit]
Description=Haus Living Health Check
[Service]
Type=oneshot
User=ubuntu
ExecStart=/usr/bin/python3 /home/ubuntu/.hermes/haus-living/health-monitor.py --quiet
StandardOutput=journal
StandardError=journal

# /etc/systemd/system/haus-health-check.timer
[Unit]
Description=Haus Living Health Check (every 6 hours)
[Timer]
OnCalendar=*-*-* 0,6,12,18:00
RandomizedDelaySec=300
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now haus-health-check.timer
```

**For LLM-powered monitoring (needs reasoning/interpretation):** Use **Hermes cron job** with **explicit provider/model pinned**:
```bash
# CRITICAL: Always pin provider/model — leaving them null can resolve to
# "Stealth" or other non-existent providers → error 400
hermes cron create "every 6 hours" \
  --model "openrouter/owl-alpha" \
  --prompt "Run health monitor and report alerts"
```

**Do NOT use `no_agent=True` cron for health checks**: The script path must be relative to `~/.hermes/scripts/` (not `~` or absolute paths), requiring unnecessary file relocation. Systemd timer is simpler and more reliable.

**Alerts**: CRIT (service down, disk >90%, RAM >90%, load >4.0), WARN (disk >80%, RAM >80%, load >2.0).

---

## GitHub SSH Backup Pattern

For automated GitHub backups from VPS (no token needed):

```bash
# 1. Generate SSH key
ssh-keygen -t ed25519 -C "agent-name" -f ~/.ssh/id_ed25519 -N ""

# 2. Add public key to GitHub → Settings → SSH Keys → New SSH key
# Copy: cat ~/.ssh/id_ed25519.pub

# 3. Test connection
ssh -T git@github.com -o StrictHostKeyChecking=no
# Expected: "Hi USERNAME! You've successfully authenticated..."

# 4. Create repo on GitHub first (manual step — user creates repo via web)
# Then:
git init /home/ubuntu/repo
cd /home/ubuntu/repo
git config user.name "agent-name"
git config user.email "agent@hermes.local"
git remote add origin git@github.com:USERNAME/REPO.git

# 5. Create .gitignore for secrets
cat > .gitignore << 'EOF'
*.env
.env*
wallets.enc
*.key
*.pem
secrets/
node_modules/
__pycache__/
*.pyc
*.tar.gz
EOF

# 6. First commit + push
git add -A
git commit -m "Initial commit"
git push -u origin master

# 7. Auto-sync script (run via cron daily)
#!/bin/bash
cd /home/ubuntu/repo
# Sync files from source dirs
cp ~/.hermes/SOUL.md superagent-core/ 2>/dev/null || true
# ... (copy other files)
git add -A
CHANGES=$(git status --porcelain | wc -l)
if [ "$CHANGES" -gt 0 ]; then
    git commit -m "Auto-sync: $(date '+%Y-%m-%d') — $CHANGES files"
    git push origin master
fi
```

**Key advantage over token-based auth**: SSH keys don't expire (unless revoked), no PAT rotation needed, works with `git push` without embedding credentials.

**Security**: Private key stays on VPS only (`~/.ssh/id_ed25519`, mode 600). Public key on GitHub can be revoked anytime.

## Telegram Group Creation — Bot Limitation

Telegram Bot API **cannot create groups**. There is no `createChat` endpoint. When the user asks to "create a group":

1. Ask the user to create the group manually in Telegram
2. Have them add the bot (`@cupang_task_bot`) to the group
3. User sends the chat ID (via `@userinfobot` or by forwarding a group message)

The agent can then send messages to that chat ID via `curl` to `sendMessage` API.

**Extract bot token** from environment when needed:
```bash
grep -o 'TELEGRAM_BOT_TOKEN=*** /etc/environment 2>/dev/null
# or
grep /proc/1/environ 2>/dev/null | tr '\0' '\n' | grep TELEGRAM_BOT_TOKEN
```

## Bash Script Writing — Heredoc & Emoji Pitfall

Writing bash scripts containing emoji via heredoc or `write_file` causes syntax errors. **Workaround:** Use Python to write the file:
```python
with open('/tmp/script.sh', 'w') as f:
    f.write(script_content)
```
Then transfer via `scp`. Alternatively, avoid emoji entirely in bash string literals.

**Also:** `write_file` auto-masks secrets (API tokens, passwords → `***`). Scripts requiring tokens must have them set directly by the user via SSH or read from environment variables on the target machine.

## Constraints

- Executable commands only — no illustrative pseudocode
- Inline comment on every non-obvious instruction
- Include rollback or recovery step for destructive ops
- **Scope deletions precisely**: When user asks to delete category A, do NOT also delete related-but-different category B without explicit confirmation. Example: user asked to remove miniapp data — cloakbrowser was a separate tool that should not have been touched. When in doubt, ask before extending the scope of a destructive operation.
- Mark sudo requirement explicitly
- Specify which process supervisor (pm2/systemd/screen) per scenario
- Never `chmod 777` unless explicitly justified
- **Always use `$(which node)` for Node.js path in systemd, never hardcode `/usr/bin/node`**
- **Never attempt to write to `~/.hermes/config.yaml` via `patch()` or `write_file()` — Hermes security blocks all writes. Tell user to edit via SSH: `nano ~/.hermes/config.yaml`**
