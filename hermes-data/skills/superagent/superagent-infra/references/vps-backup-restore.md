# VPS Full Backup + Restore Scripts

Production-ready templates for backing up a Hermes + multi-service VPS and restoring it on fresh hardware.

## backup.sh

```bash
#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/haus-backup-${TIMESTAMP}"
ARCHIVE_NAME="haus-vps-backup-${TIMESTAMP}.tar.gz"
MANIFEST="${BACKUP_DIR}/MANIFEST.json"

echo "🔥 Full VPS Backup | ${TIMESTAMP}"

# 1. Create structure
for dir in systemd nginx pm2 docker www freellmapi meta; do
  mkdir -p "${BACKUP_DIR}/${dir}"
done

# 2. Hermes (THE BRAIN) — exclude huge dirs
rsync -a --exclude='node/' \
         --exclude='hermes-agent/node_modules/' \
         --exclude='bin/' \
         --exclude='logs/*.log' \
         --exclude='sessions/' \
         /home/ubuntu/.hermes/ "${BACKUP_DIR}/hermes/"

# 3. Systemd services
cp /etc/systemd/system/freellmapi.service "${BACKUP_DIR}/systemd/" 2>/dev/null || true
for svc in /etc/systemd/system/haus*.service /etc/systemd/system/opencode*.service; do
    cp "$svc" "${BACKUP_DIR}/systemd/" 2>/dev/null || true
done

# 4. Nginx
cp /etc/nginx/nginx.conf "${BACKUP_DIR}/nginx/" 2>/dev/null || true
cp -r /etc/nginx/sites-available/ "${BACKUP_DIR}/nginx/sites-available/" 2>/dev/null || true
cp -r /etc/nginx/sites-enabled/ "${BACKUP_DIR}/nginx/sites-enabled/" 2>/dev/null || true
cp -r /etc/nginx/snippets/ "${BACKUP_DIR}/nginx/snippets/" 2>/dev/null || true

# 5. PM2
cp /home/ubuntu/.pm2/dump.pm2 "${BACKUP_DIR}/pm2/" 2>/dev/null || true
pm2 prettylist > "${BACKUP_DIR}/pm2/pm2-full-list.json" 2>/dev/null || true

# 6. Docker
docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}' > "${BACKUP_DIR}/docker/containers.txt" 2>/dev/null || true
# n8n data is in ~/.hermes/ already

# 7. Landing page
cp -r /var/www/haus-living/ "${BACKUP_DIR}/www/haus-living/" 2>/dev/null || true

# 8. FreeLLMAPI source (no node_modules)
cp -r /opt/freellmapi/package.json /opt/freellmapi/package-lock.json "${BACKUP_DIR}/freellmapi/" 2>/dev/null || true
for sub in shared server client docker; do
    cp -r "/opt/freellmapi/${sub}/" "${BACKUP_DIR}/freellmapi/${sub}/" 2>/dev/null || true
done
cp /opt/freellmapi/Dockerfile "${BACKUP_DIR}/freellmapi/" 2>/dev/null || true

# 9. OpenCode proxy (no node_modules)
mkdir -p "${BACKUP_DIR}/opencode-proxy"
cp -r /home/ubuntu/opencode-free-proxy/ "${BACKUP_DIR}/opencode-proxy/" 2>/dev/null || true
rm -rf "${BACKUP_DIR}/opencode-proxy/node_modules" 2>/dev/null || true

# 10. System metadata
cat > "${BACKUP_DIR}/meta/system-info.json" << METAEOF
{
  "timestamp": "${TIMESTAMP}",
  "hostname": "$(hostname)",
  "ip": "$(curl -s ifconfig.me 2>/dev/null || echo 'unknown')",
  "python3": "$(python3 --version 2>/dev/null)",
  "node": "$(node --version 2>/dev/null)",
  "docker": "$(docker --version 2>/dev/null)",
  "nginx": "$(nginx -v 2>&1)",
  "pm2": "$(pm2 --version 2>/dev/null)"
}
METAEOF
dpkg --get-selections | grep -v deinstall | awk '{print $1}' > "${BACKUP_DIR}/meta/apt-packages.txt"
pip3 freeze > "${BACKUP_DIR}/meta/pip-requirements.txt" 2>/dev/null || true
npm ls -g --depth=0 > "${BACKUP_DIR}/meta/npm-global.txt" 2>/dev/null || true
crontab -l > "${BACKUP_DIR}/meta/crontab.txt" 2>/dev/null || true

# 11. MANIFEST
cat > "${MANIFEST}" << EOF
{
  "backup_version": "1.0",
  "timestamp": "${TIMESTAMP}",
  "hostname": "$(hostname)",
  "contents": {
    "hermes": "Full ~/.hermes/ (config, skills, brand, wallets, cron, memories)",
    "systemd": "Custom systemd services",
    "nginx": "Full nginx config",
    "pm2": "PM2 process dump",
    "docker": "Docker compose + container list + n8n data",
    "freellmapi": "Source (no node_modules)",
    "opencode_proxy": "Source (no node_modules)",
    "meta": "System info, packages, crontab"
  },
  "restore_note": "Run restore.sh on fresh Ubuntu 22.04+ VPS"
}
EOF

# 12. Compress + checksum
cd /home/ubuntu
tar -czf "${ARCHIVE_NAME}" -C /home/ubuntu "haus-backup-${TIMESTAMP}"
SHA256=$(sha256sum "/home/ubuntu/${ARCHIVE_NAME}" | awk '{print $1}')
echo "${SHA256}  ${ARCHIVE_NAME}" > "/home/ubuntu/${ARCHIVE_NAME}.sha256"

echo "✅ Done: /home/ubuntu/${ARCHIVE_NAME} ($(du -sh "/home/ubuntu/${ARCHIVE_NAME}" | cut -f1))"
echo "🔒 SHA256: ${SHA256}"
```

## restore.sh

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔥 Full VPS Restore | Source: ${SCRIPT_DIR}"

# 1. System deps
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential python3 python3-pip python3-venv \
    nodejs npm curl wget git jq unzip nginx certbot python3-certbot-nginx \
    docker.io docker-compose-plugin rsync ca-certificates gnupg

# 2. PM2
command -v pm2 &>/dev/null || sudo npm install -g pm2

# 3. Restore Hermes
rsync -a "${SCRIPT_DIR}/hermes/" /home/ubuntu/.hermes/

# 4. Systemd services
for svc in "${SCRIPT_DIR}/systemd/"*.service; do
    [ -f "$svc" ] || continue
    sudo cp "$svc" /etc/systemd/system/
done
sudo systemctl daemon-reload

# 5. FreeLLMAPI rebuild
sudo mkdir -p /opt/freellmapi
sudo cp -r "${SCRIPT_DIR}/freellmapi/"* /opt/freellmapi/
sudo chown -R ubuntu:ubuntu /opt/freellmapi
cd /opt/freellmapi && npm install --production && cd /home/ubuntu
[ -f /etc/systemd/system/freellmapi.service ] && sudo systemctl enable --now freellmapi

# 6. Nginx
sudo cp "${SCRIPT_DIR}/nginx/nginx.conf" /etc/nginx/nginx.conf 2>/dev/null || true
sudo cp -r "${SCRIPT_DIR}/nginx/sites-available/"* /etc/nginx/sites-available/ 2>/dev/null || true
sudo cp -r "${SCRIPT_DIR}/nginx/sites-enabled/"* /etc/nginx/sites-enabled/ 2>/dev/null || true
sudo nginx -t && sudo systemctl restart nginx

# 7. Landing page
sudo mkdir -p /var/www/haus-living
sudo cp -r "${SCRIPT_DIR}/www/haus-living/"* /var/www/haus-living/ 2>/dev/null || true
sudo chown -R www-data:www-data /var/www/haus-living

# 8. OpenCode proxy
cp -r "${SCRIPT_DIR}/opencode-proxy/opencode-free-proxy/"* /home/ubuntu/opencode-free-proxy/ 2>/dev/null || true
cd /home/ubuntu/opencode-free-proxy && npm install --production && cd /home/ubuntu
pm2 start /home/ubuntu/opencode-free-proxy/index.js --name opencode-free-proxy 2>/dev/null || true
pm2 save

# 9. Python packages
pip3 install -r "${SCRIPT_DIR}/meta/pip-requirements.txt" 2>/dev/null || true

# 10. Docker + n8n
sudo systemctl enable --now docker

echo "✅ Restore complete. Post-restore checklist:"
echo "  □ Verify: curl localhost:3001/health && curl localhost/health"
echo "  □ Set bot tokens manually (Hermes auto-masks them)"
echo "  □ Start bots: pm2 start ~/.hermes/[brand]/bots/telegram-bot.py"
echo "  □ Start n8n: cd ~/.hermes/[brand] && docker compose up -d"
```

## Offsite upload options

```bash
# AWS S3
aws s3 cp archive.tar.gz s3://BUCKET/backups/

# SCP to another server
scp archive.tar.gz ubuntu@OTHER:/backups/

# rclone to Google Drive
rclone copy archive.tar.gz gdrive:backups/
```

**⚠️ Free file hosts fail for large files**: file.io, transfer.sh, and gofile.io all reject or time out for archives >500MB uploaded from VPS. Use the Nginx download pattern or S3 instead.

## Delivering backup to user (when user is on Telegram/messaging)

Users cannot run `scp` from a messaging app. Free file hosts fail for 500MB+ archives. Serve the backup via Nginx on port 80 (already open in AWS SG):

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

## Verification checklist

After restore, check:
```bash
sha256sum -c archive.tar.gz.sha256           # Archive integrity
curl -s http://localhost:3001/v1/models      # FreeLLMAPI
curl -s http://localhost/health               # Nginx
curl -s http://localhost:5678/healthz         # n8n
python3 ~/.hermes/[brand]/services.py health  # All services
ls ~/.hermes/config.yaml                      # Hermes config
ls ~/.hermes/wallets.enc                      # Wallet
```

## Offsite upload options

```bash
# AWS S3
aws s3 cp archive.tar.gz s3://BUCKET/backups/

# SCP to another server
scp archive.tar.gz ubuntu@OTHER:/backups/

# rclone to Google Drive
rclone copy archive.tar.gz gdrive:backups/
```
