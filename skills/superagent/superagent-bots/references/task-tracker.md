# Task Tracker — FastAPI + SQLite + Telethon Bot

## Architecture

Telegram User ──#task add──▶ Telethon Bot ──POST──▶ FastAPI (:8000) ──▶ SQLite

FastAPI at 127.0.0.1:8000 — Haus Living webhook server + task tracker
SQLite at ~/.hermes/haus-living/tasks.db
Nginx at port 80 — /task/ → haus_api/task/
Telethon at /home/ubuntu/adib_session.session

## Telethon Bot Commands

#task help                    — Show all commands
#task stats                   — Statistics
#task list [N]                — List N latest (default 10)
#task add <title> | <cat> | <note>  — Add task
#task done <id>               — Mark done
#task del <id>                — Delete
#task update <id> | <title> | <cat> | <note>  — Edit

## Files

API server: /home/ubuntu/.hermes/haus-living/api/webhook-server.py
Bot: /home/ubuntu/task_bot.py
DB: ~/.hermes/haus-living/tasks.db
Nginx: /etc/nginx/sites-enabled/haus-living

## Current Limitation

Telethon session /home/ubuntu/adib_session.session exists but is_user_authorized()=False
with the known API_ID 28683464. Session was created with a different API_ID.
