#!/bin/bash
# ============================================
# NINU Auto-Sync → GitHub
# Runs daily via cron to sync all changes
# ============================================

set -euo pipefail

REPO_DIR="/home/ubuntu/ninu-repo"
HERMES_DIR="/home/ubuntu/.hermes"
X_ACTIONS_DIR="/home/ubuntu/x-actions"
LOG_FILE="/tmp/ninu-sync.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

log "🔄 Starting NINU auto-sync..."

cd "$REPO_DIR"

# 1. Sync core files
log "📦 Syncing core files..."
cp "$HERMES_DIR/SOUL.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/IDENTITY.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/USER.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/MEMORY.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/AGENTS.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/TOOLS.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/TIME.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/STANDARD.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/HEARTBEAT.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/panduan.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/MANIFEST.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/CHANGELOG.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/DEPLOY.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/README.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/QUICKREF.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/INDEX.md" superagent-core/ 2>/dev/null || true
cp "$HERMES_DIR/CONTRIBUTORS.md" superagent-core/ 2>/dev/null || true

# 2. Sync ALL skills (not just superagent and captcha-bypass)
log "🧠 Syncing all skills..."
rsync -a --delete "$HERMES_DIR/skills/" skills/ 2>/dev/null || true

# 3. Sync memory files
log "💾 Syncing memory files..."
mkdir -p hermes-data/memory
cp "$HERMES_DIR/memory/"*.md hermes-data/memory/ 2>/dev/null || true
cp "$HERMES_DIR/memory/"*.json hermes-data/memory/ 2>/dev/null || true

# 4. Sync custom scripts
log "📜 Syncing custom scripts..."
mkdir -p hermes-data/scripts
cp "$HERMES_DIR/scripts/"*.py hermes-data/scripts/ 2>/dev/null || true
cp "$HERMES_DIR/scripts/"*.sh hermes-data/scripts/ 2>/dev/null || true

# 5. Sync haus-living (exclude secrets and large binaries)
log "🏠 Syncing haus-living..."
rsync -a --delete \
    --exclude='secrets/' \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='n8n-data/database.sqlite*' \
    --exclude='*.tar.gz' \
    "$HERMES_DIR/haus-living/" haus-living/ 2>/dev/null || true

# 6. Sync x-actions
log "🐦 Syncing x-actions..."
rsync -a --delete "$X_ACTIONS_DIR/" x-actions/ 2>/dev/null || true

# 7. Sync tools
log "🛠️ Syncing tools..."
cp "$HERMES_DIR/skills/superagent/tools/"*.py tools/ 2>/dev/null || true

# 8. Check for changes
CHANGES=$(git status --porcelain | wc -l)
log "📊 Changes detected: $CHANGES files"

if [ "$CHANGES" -gt 0 ]; then
    # 9. Commit and push
    git add -A
    git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M') — $CHANGES files updated

- Core files synced from ~/.hermes/
- All skills synced (37+ skills)
- Memory files synced
- Custom scripts synced (stock_complete.py, stock_chart.py, stock_deep.py)
- Haus Living assets synced
- X Actions synced
- Tools synced" 2>&1 | tail -3
    
    git push origin master 2>&1 | tail -3
    log "✅ Push successful! $CHANGES files updated."
else
    log "✅ No changes — repo is up to date."
fi

log "🏁 Sync complete."
