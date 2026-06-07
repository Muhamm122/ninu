# Full-Stack Brand Deployment — Haus Living Example

Deployed June 2026 on AWS Singapore (t3.small, 1.9GB RAM, 145GB disk).

## Architecture

```
Internet → Nginx (80/443)
  ├── /            → Landing page (static HTML, served by Nginx directly)
  ├── /api/        → FastAPI webhook server (port 8000)
  ├── /webhook/    → FastAPI webhook endpoints
  ├── /workflow/   → n8n automation UI (port 5678, Docker)
  ├── /llm/        → FreeLLMAPI (port 3001, systemd)
  └── /health      → Nginx health check

Background services:
  ├── opencode-free-proxy (port 19912, PM2)
  ├── Hermes Gateway (pid-managed)
  └── Cron jobs (4x Hermes cron for content automation)
```

## Services Installed

| Service | Manager | Port | Install Method |
|---------|---------|------|----------------|
| Nginx | systemd | 80 | apt install nginx |
| Certbot | - | - | apt install certbot python3-certbot-nginx |
| Docker | systemd | - | apt install docker-ce (via get.docker.com) |
| n8n | Docker | 5678 | docker run n8nio/n8n:latest |
| Haus API | background | 8000 | python3 webhook-server.py (FastAPI+uvicorn) |
| FreeLLMAPI | systemd | 3001 | Node.js service |
| OpenCode Proxy | PM2 | 19912 | PM2 start |
| Hermes Gateway | pid | - | Hermes internal |

## Bots Built

| Bot | File | Lines | Key Commands |
|-----|------|-------|--------------|
| Telegram | `bots/telegram-bot.py` | 768 | /start /katalog /harga /order /status /promo |
| Discord | `bots/discord-bot.py` | ~400 | !katalog !harga !order !promo !help + aliases |

Both bots: product data inline, WhatsApp deep-link integration, ConversationHandler for order flow, error decorator, Indonesian language.

## Scraper Toolkit

`scraper/scraper.py` — 5 modes:
- `ig` — IG hashtag competitor monitoring
- `price` — marketplace price monitoring (Tokopedia/Shopee)
- `trend` — keyword research + autocomplete
- `news` — furniture industry news
- `monitor` — batch run from JSON config

## Service Manager

`services.py` — CLI wrapper for start/stop/status/health/logs across all service types (systemd, pm2, docker, port, pid).

## Key Install Commands

```bash
# Nginx + Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Docker
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker ubuntu

# n8n
sudo docker run -d --name n8n --restart unless-stopped \
  -p 5678:5678 -v ~/.hermes/haus-living/n8n-data:/home/node/.n8n \
  -e GENERIC_TIMEZONE=Asia/Jakarta n8nio/n8n:latest
sudo chown -R 1000:1000 ~/.hermes/haus-living/n8n-data

# Landing page to Nginx root
sudo mkdir -p /var/www/haus-living
sudo cp ~/.hermes/haus-living/landing-page/index.html /var/www/haus-living/
sudo chown -R www-data:www-data /var/www/haus-living/
```

## SSL Setup (when domain is ready)

```bash
# Point DNS A record to server IP first
sudo certbot --nginx -d hausliving.id -d www.hausliving.id \
  --non-interactive --agree-tos -m admin@hausliving.id --redirect
```

## Resource Usage

- Total RAM: ~900MB with all services running
- n8n Docker: ~200MB
- FreeLLMAPI: ~38MB
- OpenCode Proxy: ~30MB
- Nginx: ~10MB
- Haus API: ~50MB
- Remaining: OS + Hermes gateway

## Lessons

1. **n8n volume permissions** — must `chown -R 1000:1000` the mount dir before first start, otherwise EACCES crash loop
2. **Nginx static site** — serve landing page directly via Nginx for zero-latency, no need for a backend serving static HTML
3. **Docker group** — `usermod -aG docker ubuntu` requires new login session; use `sudo docker` in the interim
4. **Service manager pattern** — wrapping 5+ heterogeneous supervisors (systemd/pm2/docker/pid/port) in one CLI is essential for operational sanity
