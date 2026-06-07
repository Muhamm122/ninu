#!/bin/bash
# ============================================
# HAUS LIVING — Full VPS Restore Script
# Version: 1.0
# ============================================
# Restores a complete Haus Living + Hermes
# setup on a FRESH Ubuntu 22.04+ VPS.
# ============================================

set -euo pipefail

# --- Config ---
BACKUP_DIR=""  # Will be auto-detected from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/haus-restore.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"; }
err() { echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"; }

echo "🔥 Haus Living — Full VPS Restore"
echo "=================================="
echo "Backup source: ${SCRIPT_DIR}"
echo ""

# 0. Verify MANIFEST exists
if [ ! -f "${SCRIPT_DIR}/MANIFEST.json" ]; then
    err "MANIFEST.json not found! Is this a valid backup directory?"
    exit 1
fi
log "Manifest found. Backup version: $(grep backup_version "${SCRIPT_DIR}/MANIFEST.json" | cut -d'"' -f4)"

# 1. Install system dependencies
echo ""
echo "── Step 1/10: System Dependencies ──"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential python3 python3-pip python3-venv \
    nodejs npm curl wget git jq unzip \
    nginx certbot python3-certbot-nginx \
    docker.io docker-compose-plugin \
    rsync ca-certificates gnupg \
    2>/dev/null | tail -1
log "System packages installed"

# 2. Install PM2
echo ""
echo "── Step 2/10: PM2 Process Manager ──"
if ! command -v pm2 &>/dev/null; then
    sudo npm install -g pm2 2>/dev/null
fi
log "PM2 $(pm2 --version 2>/dev/null || echo 'installed')"

# 3. Restore Hermes
echo ""
echo "── Step 3/10: Hermes Config + Data ──"
if [ -d "${SCRIPT_DIR}/hermes/" ]; then
    mkdir -p /home/ubuntu/.hermes
    rsync -a "${SCRIPT_DIR}/hermes/" /home/ubuntu/.hermes/
    log "Hermes restored: $(du -sh /home/ubuntu/.hermes/ | cut -f1)"
else
    warn "No hermes/ directory in backup"
fi

# 4. Restore systemd services
echo ""
echo "── Step 4/10: Systemd Services ──"
if [ -d "${SCRIPT_DIR}/systemd/" ] && [ "$(ls -A "${SCRIPT_DIR}/systemd/" 2>/dev/null)" ]; then
    for svc in "${SCRIPT_DIR}/systemd/"*.service; do
        [ -f "$svc" ] || continue
        sudo cp "$svc" /etc/systemd/system/
        log "Installed: $(basename "$svc")"
    done
    sudo systemctl daemon-reload
else
    warn "No systemd services in backup"
fi

# 5. FreeLLMAPI — rebuild from source
echo ""
echo "── Step 5/10: FreeLLMAPI ──"
if [ -d "${SCRIPT_DIR}/freellmapi/" ]; then
    sudo mkdir -p /opt/freellmapi
    sudo cp -r "${SCRIPT_DIR}/freellmapi/"* /opt/freellmapi/
    sudo chown -R ubuntu:ubuntu /opt/freellmapi
    # Rebuild node_modules
    warn "Running npm install (this takes a minute)..."
    cd /opt/freellmapi && npm install --production 2>/dev/null && cd /home/ubuntu
    log "FreeLLMAPI source restored + deps installed"
    # Start service
    if [ -f /etc/systemd/system/freellmapi.service ]; then
        sudo systemctl enable freellmapi
        sudo systemctl start freellmapi
        log "FreeLLMAPI service started"
    fi
else
    warn "No FreeLLMAPI in backup"
fi

# 6. Restore Nginx
echo ""
echo "── Step 6/10: Nginx Configuration ──"
if [ -f "${SCRIPT_DIR}/nginx/nginx.conf" ]; then
    sudo cp "${SCRIPT_DIR}/nginx/nginx.conf" /etc/nginx/nginx.conf
    log "nginx.conf restored"
fi
if [ -d "${SCRIPT_DIR}/nginx/sites-available/" ]; then
    sudo cp -r "${SCRIPT_DIR}/nginx/sites-available/"* /etc/nginx/sites-available/ 2>/dev/null || true
    log "sites-available restored"
fi
if [ -d "${SCRIPT_DIR}/nginx/sites-enabled/" ]; then
    sudo cp -r "${SCRIPT_DIR}/nginx/sites-enabled/"* /etc/nginx/sites-enabled/ 2>/dev/null || true
    log "sites-enabled restored"
fi
if [ -d "${SCRIPT_DIR}/nginx/snippets/" ]; then
    sudo cp -r "${SCRIPT_DIR}/nginx/snippets/"* /etc/nginx/snippets/ 2>/dev/null || true
fi
# Test config
sudo nginx -t 2>/dev/null && sudo systemctl restart nginx && log "Nginx restarted" || warn "Nginx config issue — check manually"

# 7. Restore landing page
echo ""
echo "── Step 7/10: Landing Page ──"
if [ -d "${SCRIPT_DIR}/www/haus-living/" ]; then
    sudo mkdir -p /var/www/haus-living
    sudo cp -r "${SCRIPT_DIR}/www/haus-living/"* /var/www/haus-living/
    sudo chown -R www-data:www-data /var/www/haus-living
    log "Landing page restored"
else
    warn "No landing page in backup"
fi

# 8. Restore OpenCode Free Proxy
echo ""
echo "── Step 8/10: OpenCode Free Proxy ──"
if [ -d "${SCRIPT_DIR}/opencode-proxy/opencode-free-proxy/" ]; then
    mkdir -p /home/ubuntu/opencode-free-proxy
    cp -r "${SCRIPT_DIR}/opencode-proxy/opencode-free-proxy/"* /home/ubuntu/opencode-free-proxy/
    warn "Running npm install..."
    cd /home/ubuntu/opencode-free-proxy && npm install --production 2>/dev/null && cd /home/ubuntu
    # Start via PM2
    pm2 start /home/ubuntu/opencode-free-proxy/index.js --name opencode-free-proxy 2>/dev/null || true
    pm2 save 2>/dev/null || true
    log "OpenCode proxy restored + started"
else
    warn "No OpenCode proxy in backup"
fi

# 9. Restore Python packages
echo ""
echo "── Step 9/10: Python Packages ──"
if [ -f "${SCRIPT_DIR}/meta/pip-requirements.txt" ]; then
    pip3 install -r "${SCRIPT_DIR}/meta/pip-requirements.txt" 2>/dev/null | tail -1
    log "Python packages restored"
else
    warn "No pip requirements in backup"
fi

# 10. Docker + n8n
echo ""
echo "── Step 10/10: Docker + n8n ──"
# Ensure Docker is running
sudo systemctl enable docker
sudo systemctl start docker
# n8n data is already in ~/.hermes/haus-living/n8n-data/ (restored in step 3)
if [ -f "${SCRIPT_DIR}/docker/docker-compose.yml" ] || [ -f /home/ubuntu/.hermes/haus-living/docker-compose.yml ]; then
    log "Docker compose file present — n8n data in ~/.hermes/haus-living/n8n-data/"
    warn "Run 'docker compose up -d' in ~/.hermes/haus-living/ to start n8n + redis + postgres"
else
    warn "No docker-compose.yml found"
fi

# --- Post-restore summary ---
echo ""
echo "=================================="
echo "✅ RESTORE COMPLETE!"
echo "=================================="
echo ""
echo "📋 Post-restore checklist:"
echo "  □ Verify Hermes: ls ~/.hermes/config.yaml"
echo "  □ Verify FreeLLMAPI: curl -s http://localhost:3001/health"
echo "  □ Verify Nginx: curl -s http://localhost/health"
echo "  □ Verify n8n: sudo docker start n8n  # if container exists"
echo "  □ Set bot tokens: export BOT_TOKEN=... / export DISCORD_TOKEN=..."
echo "  □ Start bots: pm2 start ~/.hermes/haus-living/bots/telegram-bot.py --interpreter python3"
echo "  □ Start Haus API: pm2 start ~/.hermes/haus-living/api/webhook-server.py --interpreter python3"
echo "  □ Install Hermes Gateway (if not already): follow hermes docs"
echo "  □ Restore crontab: crontab ~/.hermes/haus-living/backup-meta/crontab.txt"
echo ""
echo "⚠️  Note: node_modules are rebuilt during restore (not backed up)."
echo "⚠️  Secrets/tokens must be set manually (Hermes auto-masks them)."
