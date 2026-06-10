---
name: telegram-file-sender
description: Send local files to Telegram reliably by copying to Hermes authorized cache first, then sending via Bot API. Use when you need to send PDF, DOCX, XLSX, ZIP, images, or any local file that is not in Hermes cache directories. Avoids silent gateway drops.
version: 1.1.0
author: Andrea Armeni (original), CUPANG AI AGENT (enhanced)
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [telegram, file-sending, media-delivery, workaround]
triggers:
  - kirim file ke telegram
  - send file telegram
  - telegram document
  - telegram pdf
  - MEDIA: silent drop
---

# Telegram File Sender

## Contesto
Hermes media delivery funziona SOLO per file in cartelle consentite:
- `~/.hermes/cache/images/`
- `~/.hermes/cache/documents/`
- `~/.hermes/cache/screenshots/`
- `~/.hermes/image_cache/`
- `~/.hermes/document_cache/`

File in altre cartelle (es. `_inbox/raw`, progetti, download) vengono **scartati silenziosamente** dal gateway.

## Procedura

### 1. Copiare i file nella cache documenti (nomi puliti)
```bash
mkdir -p ~/.hermes/cache/documents/telegram-sender
cp /path/to/file.pdf ~/.hermes/cache/documents/telegram-sender/
```

**Regole nomi file:**
- Niente spazi (sostituisci con `-`)
- Niente caratteri speciali
- Massimo 50 caratteri
- Estensione originale conservata

### 2. Inviare documenti/PDF/ZIP/XLSX con Telegram API (curl)
```bash
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
CHAT_ID=<TELEGRAM_CHAT_ID>

curl -F "document=@/percorso/file.pdf" \
  "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
  -F "chat_id=${CHAT_ID}" \
  -F "caption=nomefile.pdf"
```

**Limite:** 1 file per chiamata curl (Telegram API).

### 3. Inviare immagini con MEDIA: (funziona)
```
MEDIA:${HOME}/.hermes/cache/documents/telegram-sender/foto.png
```

### 4. Pulizia (opzionale)
```bash
rm -rf ~/.hermes/cache/documents/telegram-sender/*
```

## Output atteso
- Messaggio Telegram con allegati nativi (PDF, documenti, immagini)
- Nessun errore silenzioso
- File consegnati come attachment, non come link

## Enhanced Tool: `tg_file_sender.py`

Bukan cuma manual copy+curl — ada Python tool yang otomatis:

```bash
# Kirim file (auto-detect type: photo/document/audio/video)
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py /path/to/file.pdf

# Dengan caption
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py file.zip --caption "Laporan Q2"

# Ke chat lain (group/channel)
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py file.pdf --chat-id -1001234567890

# Lihat cache
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py --list-cache

# Hanya copy ke cache tanpa kirim
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py file.pdf --cache-only

# Keep file di cache setelah kirim
python3 ~/.hermes/skills/superagent/tools/tg_file_sender.py file.pdf --no-cache-cleanup
```

The tool auto-selects Telegram API method by file extension:
- `.png/.jpg/.jpeg/.gif/.webp` → `sendPhoto`
- `.mp3/.ogg/.wav/.m4a` → `sendAudio`
- `.mp4/.mov/.webm` → `sendVideo`
- All others → `sendDocument`

## Errori comuni
- "File non inviato" → il file non era nella cache consentita
- "Silent drop" → il gateway ha scartato il file senza avvisare
- Soluzione: verificare che il path sia sotto `~/.hermes/cache/`

## Pitfalls
- **Bot token must be in `~/.hermes/.env`** as `TELEGRAM_BOT_TOKEN=xxx` — tool reads from there
- **User must have started a conversation with the bot** before bot can send DMs (Telegram API rule). If `getUpdates` returns 0 chats, user needs to send `/start` or any message to the bot first.
- **1 file per API call** — for bulk sending, loop with delay between calls
- **Caption max 200 chars** — Telegram API limit
- **Token line in .env may have leading whitespace** — tool strips it, but manual curl may fail if not trimmed
- **Chat ID for DM ≈ user ID** but group/channel IDs are negative (e.g., `-1001234567890`)
