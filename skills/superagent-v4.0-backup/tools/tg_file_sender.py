#!/usr/bin/env python3
"""
CUPANG Telegram File Sender
Based on: https://github.com/dexter7wolf/telegram-file-sender

Sends local files to Telegram reliably by:
1. Copying file to Hermes authorized cache directory
2. Normalizing filename
3. Sending via Telegram Bot API (sendDocument/sendPhoto)

Usage:
  python3 tg_file_sender.py /path/to/file.pdf
  python3 tg_file_sender.py /path/to/file.pdf --caption "Laporan bulanan"
  python3 tg_file_sender.py /path/to/image.png
  python3 tg_file_sender.py /path/to/file.zip --no-cache-cleanup
  python3 tg_file_sender.py /path/to/file.pdf --chat-id 123456
"""

import os
import sys
import re
import json
import shutil
import argparse
import subprocess
from pathlib import Path

CONFIG_DIR = Path.home() / '.hermes'
CACHE_DIR = CONFIG_DIR / 'cache' / 'documents' / 'telegram-sender'
ENV_FILE = CONFIG_DIR / '.env'

# File type classification
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
AUDIO_EXTS = {'.mp3', '.ogg', '.wav', '.m4a', '.flac'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

def get_bot_token():
    """Read TELEGRAM_BOT_TOKEN from Hermes .env"""
    if not ENV_FILE.exists():
        print("❌ ~/.hermes/.env not found")
        sys.exit(1)
    
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                token = line.split('=', 1)[1].strip().strip('"').strip("'")
                if token and not token.startswith('TELEGR'):
                    return token
    
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)

def normalize_filename(filepath):
    """Normalize filename: no spaces, no special chars, max 50 chars"""
    p = Path(filepath)
    stem = p.stem
    ext = p.suffix.lower()
    
    # Replace spaces and special chars
    stem = re.sub(r'[\s]+', '-', stem)
    stem = re.sub(r'[^a-zA-Z0-9\-_.]', '', stem)
    
    # Truncate to 50 chars (including extension)
    max_stem = 50 - len(ext)
    if len(stem) > max_stem:
        stem = stem[:max_stem]
    
    return f"{stem}{ext}"

def copy_to_cache(filepath):
    """Copy file to Hermes authorized cache directory"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    src = Path(filepath).resolve()
    if not src.exists():
        print(f"❌ File not found: {src}")
        sys.exit(1)
    
    # Normalize and copy
    clean_name = normalize_filename(src.name)
    dst = CACHE_DIR / clean_name
    
    shutil.copy2(str(src), str(dst))
    print(f"📋 Copied: {src.name} → {clean_name} ({dst.stat().st_size / 1024:.1f} KB)")
    
    return dst

def send_to_telegram(filepath, chat_id, caption=None, bot_token=None):
    """Send file via Telegram Bot API"""
    if not bot_token:
        bot_token = get_bot_token()
    
    filepath = Path(filepath)
    ext = filepath.suffix.lower()
    filename = filepath.name
    if not caption:
        caption = filename
    
    api_base = f"https://api.telegram.org/bot{bot_token}"
    
    # Choose API method based on file type
    if ext in IMAGE_EXTS:
        method = "sendPhoto"
        file_field = "photo"
    elif ext in AUDIO_EXTS:
        method = "sendAudio"  
        file_field = "audio"
    elif ext in VIDEO_EXTS:
        method = "sendVideo"
        file_field = "video"
    else:
        method = "sendDocument"
        file_field = "document"
    
    url = f"{api_base}/{method}"
    
    # Build curl command
    cmd = [
        'curl', '-s', url,
        '-F', f'{file_field}=@{filepath}',
        '-F', f'chat_id={chat_id}',
        '-F', f'caption={caption[:200]}'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        resp = json.loads(result.stdout)
        if resp.get('ok'):
            msg = resp['result']
            msg_id = msg.get('message_id')
            file_info = ''
            if method == 'sendDocument' and 'document' in msg:
                file_info = f" (file_id: {msg['document']['file_id'][:20]}...)"
            elif method == 'sendPhoto' and 'photo' in msg:
                file_info = f" (photo, sizes: {len(msg['photo'])})"
            print(f"✅ Sent via {method}! msg_id: {msg_id}{file_info}")
            return True
        else:
            err = resp.get('description', 'unknown error')
            print(f"❌ Telegram error: {err}")
            return False
    except json.JSONDecodeError:
        print(f"❌ API error: {result.stdout[:200]}")
        return False

def main():
    parser = argparse.ArgumentParser(description='CUPANG Telegram File Sender')
    parser.add_argument('file', help='Path to file to send')
    parser.add_argument('--caption', '-c', help='Caption for the file')
    parser.add_argument('--chat-id', type=int, default=439901712, 
                        help='Telegram chat ID (default: your DM)')
    parser.add_argument('--no-cache-cleanup', action='store_true',
                        help='Keep file in cache after sending')
    parser.add_argument('--cache-only', action='store_true',
                        help='Only copy to cache, dont send')
    parser.add_argument('--list-cache', action='store_true',
                        help='List files in cache')
    args = parser.parse_args()
    
    # List cache
    if args.list_cache:
        if CACHE_DIR.exists():
            files = list(CACHE_DIR.iterdir())
            if files:
                print(f"📁 Cache ({len(files)} files):")
                for f in sorted(files):
                    size = f.stat().st_size / 1024
                    print(f"  {f.name} ({size:.1f} KB)")
            else:
                print("📁 Cache empty")
        else:
            print("📁 Cache directory not found")
        return
    
    # Copy to cache
    cached_path = copy_to_cache(args.file)
    
    if args.cache_only:
        print(f"📋 File cached at: {cached_path}")
        return
    
    # Send to Telegram
    ok = send_to_telegram(cached_path, args.chat_id, args.caption)
    
    # Cleanup cache
    if ok and not args.no_cache_cleanup:
        cached_path.unlink()
        print("🧹 Cache cleaned")
    elif not ok:
        print(f"⚠️ File kept in cache: {cached_path}")

if __name__ == '__main__':
    main()
