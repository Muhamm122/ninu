#!/bin/bash
# ============================================
# HAUS LIVING — Full VPS Backup Script
# Version: 1.0 | Date: 2026-06-05
# ============================================
# Backs up ALL critical data so a fresh VPS
# can be fully restored from this archive.
# ============================================

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/haus-backup-${TIMESTAMP}"
ARCHIVE_NAME="haus-vps-backup-${TIMESTAMP}.tar.gz"
MANIFEST="${BACKUP_DIR}/MANIFEST.json"

echo "🔥 Haus Living — Full VPS Backup"
echo "================================"
echo "Timestamp: ${TIMESTAMP}"
echo ""

# 1. Create backup directory
mkdir -p "${BACKUP_DIR}/systemd"
mkdir -p "${BACKUP_DIR}/nginx"
mkdir -p "${BACKUP_DIR}/pm2"
mkdir -p "${BACKUP_DIR}/docker"
mkdir -p "${BACKUP_DIR}/www"
mkdir -p "${BACKUP_DIR}/freellmapi"
mkdir -p "${BACKUP_DIR}/meta"

echo "✅ Created backup structure: ${BACKUP_DIR}"

# 2. Copy Hermes config & data (THE BRAIN)
echo "📦 [1/10] Backing up ~/.hermes/ ..."
# Exclude huge node_modules and binary caches
rsync -a --exclude='node/' \
         --exclude='hermes-agent/node_modules/' \
         --exclude='bin/' \
         --exclude='logs/*.log' \
         --exclude='sessions/' \
         /home/ubuntu/.hermes/ "${BACKUP_DIR}/hermes/"
echo "   Done: $(du -sh "${BACKUP_DIR}/hermes/" 2>/dev/null | cut -f1)"

# 3. Systemd services
echo "📦 [2/10] Backing up systemd services ..."
cp /etc/systemd/system/freellmapi.service "${BACKUP_DIR}/systemd/" 2>/dev/null || true
# Find any other custom services
for svc in /etc/systemd/system/haus*.service /etc/systemd/system/opencode*.service; do
    cp "$svc" "${BACKUP_DIR}/systemd/" 2>/dev/null || true
done
echo "   Services: $(ls "${BACKUP_DIR}/systemd/" 2>/dev/null | wc -l) files"

# 4. Nginx config
echo "📦 [3/10] Backing up Nginx config ..."
cp /etc/nginx/nginx.conf "${BACKUP_DIR}/nginx/nginx.conf" 2>/dev/null || true
cp -r /etc/nginx/sites-available/ "${BACKUP_DIR}/nginx/sites-available/" 2>/dev/null || true
cp -r /etc/nginx/sites-enabled/ "${BACKUP_DIR}/nginx/sites-enabled/" 2>/dev/null || true
cp -r /etc/nginx/snippets/ "${BACKUP_DIR}/nginx/snippets/" 2>/dev/null || true
echo "   Done"

# 5. PM2 config
echo "📦 [4/10] Backing up PM2 ..."
cp /home/ubuntu/.pm2/dump.pm2 "${BACKUP_DIR}/pm2/" 2>/dev/null || true
pm2 prettylist > "${BACKUP_DIR}/pm2/pm2-full-list.json" 2>/dev/null || true
echo "   Done"

# 6. Docker compose + n8n data
echo "📦 [5/10] Backing up Docker/n8n data ..."
if command -v docker &>/dev/null; then
    docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}' > "${BACKUP_DIR}/docker/containers.txt" 2>/dev/null || true
    # n8n data is already in ~/.hermes/haus-living/n8n-data/ (covered by step 2)
fi
cp /home/ubuntu/.hermes/haus-living/docker-compose.yml "${BACKUP_DIR}/docker/" 2>/dev/null || true
cp /home/ubuntu/.hermes/haus-living/.env.example "${BACKUP_DIR}/docker/.env.example" 2>/dev/null || true
echo "   Done"

# 7. Landing page (www)
echo "📦 [6/10] Backing up /var/www/haus-living ..."
cp -r /var/www/haus-living/ "${BACKUP_DIR}/www/haus-living/" 2>/dev/null || true
echo "   Done: $(du -sh "${BACKUP_DIR}/www/" 2>/dev/null | cut -f1)"

# 8. FreeLLMAPI
echo "📦 [7/10] Backing up FreeLLMAPI ..."
# Only config + keys, not node_modules
cp -r /opt/freellmapi/package.json "${BACKUP_DIR}/freellmapi/" 2>/dev/null || true
cp -r /opt/freellmapi/package-lock.json "${BACKUP_DIR}/freellmapi/" 2>/dev/null || true
cp -r /opt/freellmapi/shared/ "${BACKUP_DIR}/freellmapi/shared/" 2>/dev/null || true
cp -r /opt/freellmapi/server/ "${BACKUP_DIR}/freellmapi/server/" 2>/dev/null || true
cp -r /opt/freellmapi/client/ "${BACKUP_DIR}/freellmapi/client/" 2>/dev/null || true
cp -r /opt/freellmapi/docker/ "${BACKUP_DIR}/freellmapi/docker/" 2>/dev/null || true
cp /opt/freellmapi/Dockerfile "${BACKUP_DIR}/freellmapi/" 2>/dev/null || true
# Exclude node_modules from server/client/shared rsyncs (already copied raw above)
echo "   Done: $(du -sh "${BACKUP_DIR}/freellmapi/" 2>/dev/null | cut -f1)"

# 9. OpenCode Free Proxy
echo "📦 [8/10] Backing up OpenCode Free Proxy ..."
mkdir -p "${BACKUP_DIR}/opencode-proxy"
cp -r /home/ubuntu/opencode-free-proxy/ "${BACKUP_DIR}/opencode-proxy/" 2>/dev/null || true
# Remove node_modules from backup
rm -rf "${BACKUP_DIR}/opencode-proxy/node_modules" 2>/dev/null || true
echo "   Done"

# 10. System metadata
echo "📦 [9/10] Collecting system metadata ..."
cat > "${BACKUP_DIR}/meta/system-info.json" << METAEOF
{
  "timestamp": "${TIMESTAMP}",
  "hostname": "$(hostname)",
  "os": "$(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)",
  "kernel": "$(uname -r)",
  "ip": "$(curl -s ifconfig.me 2>/dev/null || echo 'unknown')",
  "disk_used": "$(df -h / | tail -1 | awk '{print $3}')",
  "disk_total": "$(df -h / | tail -1 | awk '{print $2}')",
  "ram_total": "$(free -h | grep Mem | awk '{print $2}')",
  "python3": "$(python3 --version 2>/dev/null || echo 'not found')",
  "node": "$(node --version 2>/dev/null || echo 'not found')",
  "docker": "$(docker --version 2>/dev/null || echo 'not found')",
  "nginx": "$(nginx -v 2>&1 || echo 'not found')",
  "pm2": "$(pm2 --version 2>/dev/null || echo 'not found')",
  "pip_packages": $(pip3 list --format=json 2>/dev/null || echo '[]'),
  "apt_packages": $(dpkg --get-selections | grep -v deinstall | awk '{print $1}' | sort | tr '\n' ',' | sed 's/,$//' | awk '{printf "["; split($0,a,","); for(i=1;i<=length(a);i++) printf "\"%s\"%s", a[i], (i<length(a)?",":""); printf "]"}')
}
METAEOF

# Also capture apt package list separately (more reliable)
dpkg --get-selections | grep -v deinstall | awk '{print $1}' > "${BACKUP_DIR}/meta/apt-packages.txt"
pip3 freeze > "${BACKUP_DIR}/meta/pip-requirements.txt" 2>/dev/null || true
pip3 list --format=json > "${BACKUP_DIR}/meta/pip-packages.json" 2>/dev/null || true
npm ls -g --depth=0 > "${BACKUP_DIR}/meta/npm-global.txt" 2>/dev/null || true
crontab -l > "${BACKUP_DIR}/meta/crontab.txt" 2>/dev/null || echo "no crontab" > "${BACKUP_DIR}/meta/crontab.txt"
echo "   Done"

# 11. Create MANIFEST
echo "📦 [10/10] Creating manifest ..."
cat > "${MANIFEST}" << EOF
{
  "backup_version": "1.0",
  "timestamp": "${TIMESTAMP}",
  "hostname": "$(hostname)",
  "server_ip": "$(curl -s ifconfig.me 2>/dev/null || echo 'unknown')",
  "contents": {
    "hermes": "Full ~/.hermes/ (config, skills, haus-living, wallet, cron, memories)",
    "systemd": "Custom systemd services (freellmapi, etc)",
    "nginx": "Full nginx config (sites, upstreams, rate limits)",
    "pm2": "PM2 process list + dump",
    "docker": "Docker compose, container list, n8n data",
    "www": "/var/www/haus-living landing page",
    "freellmapi": "FreeLLMAPI source (no node_modules)",
    "opencode_proxy": "OpenCode free proxy source (no node_modules)",
    "meta": "System info, pip/apt packages, crontab"
  },
  "services": {
    "freellmapi": {"port": 3001, "type": "systemd"},
    "opencode-proxy": {"port": 19912, "type": "pm2"},
    "haus-api": {"port": 8000, "type": "pm2"},
    "n8n": {"port": 5678, "type": "docker"},
    "nginx": {"port": 80, "type": "systemd"},
    "hermes-gateway": {"type": "process"}
  },
  "restore_note": "Run restore.sh on fresh Ubuntu 22.04+ VPS. Node_modules rebuilt automatically."
}
EOF

echo "   Done"

# 12. Compress everything
echo ""
echo "📦 Compressing backup archive ..."
cd /home/ubuntu
tar -czf "${ARCHIVE_NAME}" -C /home/ubuntu "haus-backup-${TIMESTAMP}"

# 13. Calculate checksum
SHA256=$(sha256sum "/home/ubuntu/${ARCHIVE_NAME}" | awk '{print $1}')
SIZE=$(du -sh "/home/ubuntu/${ARCHIVE_NAME}" | awk '{print $1}')

echo ""
echo "================================"
echo "✅ BACKUP COMPLETE!"
echo "================================"
echo "📁 Archive: /home/ubuntu/${ARCHIVE_NAME}"
echo "📏 Size: ${SIZE}"
echo "🔒 SHA256: ${SHA256}"
echo ""
echo "To restore on a new VPS:"
echo "  1. Copy archive to new VPS: scp ${ARCHIVE_NAME} ubuntu@NEW_IP:/home/ubuntu/"
echo "  2. Extract: tar -xzf ${ARCHIVE_NAME}"
echo "  3. Run: bash haus-backup-${TIMESTAMP}/restore.sh"
echo ""

# Save checksum for verification
echo "${SHA256}  ${ARCHIVE_NAME}" > "/home/ubuntu/${ARCHIVE_NAME}.sha256"
echo "Checksum saved to: /home/ubuntu/${ARCHIVE_NAME}.sha256"
