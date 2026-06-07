---
name: ig-brand-management
description: Full-stack Instagram brand management — strategy, content calendar, captions, style guide, landing page, logo, watermark, bots, cron automation, and infrastructure.
triggers:
  - IG brand setup
  - Instagram content strategy
  - Furniture/home decor IG
  - rebrand Instagram
  - content calendar generator
  - IG username check
---

# IG Brand Management

End-to-end workflow for setting up and managing an Instagram brand presence, from naming to automation.

## Phases (execute in order)

### Phase 1: Naming & Username
1. Brainstorm names matching the brand's aesthetic (dark/modern, warm, minimal, etc.)
2. Check username availability via IG API:
   ```
   curl -H "X-IG-App-ID: 936619743392459" \
     "https://i.instagram.com/api/v1/users/web_profile_info/?username=TARGET"
   ```
   - HTTP 200 + `"user":null` → ✅ AVAILABLE
   - HTTP 200 + `"id"` in response → ❌ TAKEN
   - HTTP 401 → rate limited (see Pitfalls)
3. Check domain availability via DNS: `curl "https://dns.google/resolve?name=DOMAIN&type=A"`
4. Present top 5 with pros/cons

### Phase 2: Strategy Files
Create these files under `~/.hermes/<brand-slug>/`:
- `content-calendar-30hari.md` — 30-day content plan (30% product, 23% edukasi, 17% lifestyle, 10% testimoni, 10% trust, 7% promo, 3% engagement)
- `30-caption-batch.md` — 30 captions ready to copy-paste (with hashtags)
- `sample-captions.md` — 8 sample captions + formula templates
- `style-guide.md` — colors, photo style, feed grid, reel, story guide
- `dm-wa-template.md` — 5 DM auto-reply + 5 WA messages + FAQ + lead tracking
- `product-catalog.md` — all products with prices, specs, categories, bundles

### Phase 3: Landing Page
- Build responsive HTML landing page (Tailwind CSS CDN)
- Include: navbar, hero, value props, product grid with filter, bundles, testimoni, CTA, floating WA button
- Serve via Nginx (copy to `/var/www/<brand>/`)

### Phase 4: Logo & Watermark
1. Create SVG logos (multiple variants: wordmark, monogram, icon-style)
2. Convert to PNG: `rsvg-convert -w 1080 -h 1080 logo.svg > logo.png`
3. Build watermark tool supporting 5 types:
   - `corner` — bottom-right, 15% opacity (catalog/website)
   - `bar` — full bottom bar, 65% opacity (IG feed)
   - `badge` — top-left corner badge (Reels/Stories)
   - `center` — centered large text, 12% opacity (copy protection)
   - `stripe` — diagonal repeating text, 7% opacity (anti-theft)
4. Generate 3 sizes: 1080px (IG post), 720px (Story), 400px (Thumbnail)

### Phase 5: Automation (Cron)
Set up 4 Hermes cron jobs:
- **Daily 08:00** — send today's caption (from batch file)
- **Evening 21:00** — prep tomorrow's content + photo checklist
- **Weekly Sunday 20:00** — review + KPI check + recommendations
- **Monthly 1st 10:00** — regenerate 30 captions for next month

### Phase 6: Bots & API
- **Telegram bot** — /start, /katalog, /harga, /order, /status, /promo (python-telegram-bot v20+)
- **Discord bot** — !katalog, !harga, !order, !promo, !help (discord.py)
- **Webhook API** — POST /webhook/order, /webhook/payment, /webhook/ig (FastAPI + uvicorn port 8000)
- **Scraper** — IG hashtag, price monitor (Tokopedia/Shopee), keyword trends, industry news

### Phase 7: Infrastructure
- Docker + Docker Compose for orchestration
- Nginx reverse proxy (see `references/nginx-multi-service.md`)
- n8n workflow automation (Docker, port 5678)
- Service manager script for start/stop/status/health/logs

### Phase 7.5: Security Hardening (run after Phase 7)
After all services are confirmed running, harden the VPS:

1. **UFW Firewall** — deny-all default, only allow 22/80/443. Backend ports (3001, 5678, 19912, 8000) become unreachable from internet (only via Nginx reverse proxy).
2. **Log Rotation** — Configure for PM2 (`/etc/logrotate.d/pm2` with `copytruncate`), FreeLLMAPI (journald drop-in, 500M max, 14d retention), Docker (`/etc/docker/daemon.json` with json-file driver, 50M max-size). Note: restarting Docker daemon restarts all containers.
3. **PM2 Startup** — `pm2 startup systemd -u ubuntu --hp /home/ubuntu` + follow printed sudo command + `pm2 save`. Ensures PM2 processes survive reboot.
4. **Remove temporary endpoints** — If backup was delivered via `/download/` Nginx location, remove it after user confirms download. Never leave unauthenticated file-serving endpoints open.
5. **Docker sudo** — If `ubuntu` user is not in docker group, prefix all `docker` commands with `sudo` in health/backup/service-manager scripts. Or run `sudo usermod -aG docker ubuntu` + re-login.

See `superagent-infra` skill → "Server Hardening Checklist" for full commands.

### Phase 8: Disaster Recovery (Backup + Restore)
After all services are running, create a full VPS backup so the entire setup can be restored on a fresh VPS if the current one dies.

**Use the VPS backup workflow from `superagent-infra`** → see `superagent-infra/references/vps-backup-restore.md` for full script templates.

Key points:
- Backup script collects 10 categories: hermes, systemd, nginx, pm2, docker, www, freellmapi, opencode-proxy, meta, MANIFEST
- Excludes rebuildable artifacts: `node_modules/`, `sessions/`, `logs/`
- Stores system metadata: apt/pip/npm package lists, Python/Node versions, crontab
- Creates self-contained `.tar.gz` archive with SHA256 checksum + restore.sh inside
- Restore runs `npm install --production` to rebuild node_modules
- Typical archive size: ~500MB for full Hermes + multi-service VPS
- Bot tokens are NOT in backup (Hermes auto-masks them) — user sets manually on new VPS
- **Delivering backup to user**: Free file hosts fail for 500MB+. Use Nginx `/download/` pattern (see `superagent-infra` → "Delivering backup to user" section) — add temp location, give URL, remove after confirmed download

## Rebrand Checklist
When changing brand name:
1. Rename directory: `mv ~/.hermes/old-slug ~/.hermes/new-slug`
2. sed-replace all brand references in every file
3. Update landing page (logo initials, brand name, title)
4. Update all 4 cron job prompts (name + file paths)
5. Create announcement captain (feed, story, reel, DM, WA)
6. Update persistent memory with new brand name

## Pitfalls

### IG API Rate Limiting
- The `web_profile_info` endpoint rate-limits aggressively (~20 requests from same IP)
- After hitting 401, you must wait 5+ minutes before retrying
- Rotate `X-IG-App-ID` values: `936619743392459`, `735923892429730`, `567067343354431`
- AWS/datacenter IPs may get rate-limited faster than residential
- **Workaround**: Check username availability in batches with 5-10s delays between each

### Hermes Token Masking
- Hermes auto-masks API tokens before any file write
- You CANNOT store tokens in files via write_file or Python file writes
- **Workaround**: User must paste token directly via SSH, OR use systemd service file where user edits `Environment=` line themselves
- Verify tokens via curl BEFORE trying to store them

### n8n Docker Permissions
- n8n container will fail with `EACCES: permission denied` on `/home/node/.n8n/config`
- **Fix**: `sudo chown -R 1000:1000 <volume-dir>` before starting container

### python-telegram-bot ConversationHandler
- `allow_re_entry=True` is NOT a valid kwarg (removed in v20+)
- **Fix**: Use `per_user=True` instead
- Always verify bot code against installed library version

### Hermes Token Masking (CRITICAL)
Hermes auto-masks API tokens before ANY file write — `write_file`, Python `open().write()`, shell redirects. The secret portion becomes `***`, making stored tokens invalid.
- **You cannot store Telegram/Discord bot tokens in files programmatically**
- **Workarounds**:
  1. User creates systemd service file and pastes token in `Environment=` line directly
  2. User runs `BOT_TOKEN='real_token' pm2 start bot.py --interpreter python3 --name bot`
  3. Bot code reads from secrets file (`~/.hermes/<brand>/secrets/tg_bot_token`) that user creates manually via SSH
- **Always verify tokens via curl first**: `curl -s "https://api.telegram.org/bot${TOKEN}/getMe"` (curl doesn't trigger the mask)
- **Tell user**: "I built the bot. You paste the token and run it yourself." — do NOT attempt to store tokens for them

### AWS IP Limitations
- Cannot access IG login from AWS datacenter IP (flagged by Meta)
- Cannot create Google/Gmail accounts from AWS IP
- Cannot reliably interact with OAuth flows from datacenter IPs
- Recommend: user handles all login/OAuth manually; agent handles content prep only

### Docker `sudo` Required
- `docker` commands fail with "permission denied" for non-root user not in docker group
- Affects: service manager (`services.py`), health monitor (`health-monitor.py`), backup scripts
- **Fix**: Use `sudo docker ...` in all scripts, or add user to docker group: `sudo usermod -aG docker ubuntu` then re-login

### Nginx sites-enabled Not Always a Symlink
- On some setups, `/etc/nginx/sites-enabled/haus-living` is a **separate file** (not a symlink to `sites-available/`)
- Editing only one may leave them inconsistent
- **Fix**: Always check and edit both, or convert to symlink: `sudo rm sites-enabled/haus-living && sudo ln -s /etc/nginx/sites-available/haus-living sites-enabled/`

## Skill Overlap Note

`ig-brand-management` (this skill) and `instagram-brand-management` (social-media category) overlap significantly. Both cover content calendar, captions, style guide, DM/WA funnel, logo/watermark, and automation. The `instagram-brand-management` skill is more detailed with templates/references/scripts; this skill is more concise with inline patterns. Prefer `instagram-brand-management` for full brand setup from scratch; use this skill for quick reference on specific phases (Phase 1-8).

**Consider consolidating** these two skills when the curator takes a pass — they serve the same class of work and having both creates confusion about which to load.
