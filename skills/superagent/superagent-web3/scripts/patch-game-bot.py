#!/usr/bin/env python3
"""
patch-game-bot.py — Apply standard patches to a github-hosted Node.js game bot
so it can be self-hosted with your own wallet + env.

Run from the bot's scripts/ directory:
    python3 patch-game-bot.py

What it does:
  1. Fix bs58 import (require('bs58').default → require('bs58'))
  2. Add `require('dotenv').config();` as line 1
  3. Replace hardcoded WALLET_ADDR with env-driven
  4. Replace hardcoded WALLET_FILE with env-driven
  5. Make MY_PLAYER_ID a `let` with env fallback
  6. Move TOKEN_PATH from /tmp (PrivateTmp) to persistent data dir
  7. Save a .bak backup as bot.js.bak-pre-patch

Idempotent — safe to re-run. Reports each applied change.
"""
import re
import sys
import os
from pathlib import Path

BOT_JS = "bot.js"

def main():
    if not Path(BOT_JS).exists():
        print(f"ERROR: {BOT_JS} not found. Run from scripts/ dir.", file=sys.stderr)
        sys.exit(1)

    data = open(BOT_JS, "rb").read()
    backup_path = f"{BOT_JS}.bak-pre-patch"
    if not Path(backup_path).exists():
        Path(backup_path).write_bytes(data)
        print(f"backup: {backup_path}")

    changes = []

    # 1. Fix bs58 import
    if b"const bs58 = require('bs58').default;" in data:
        data = data.replace(
            b"const bs58 = require('bs58').default;",
            b"const bs58 = require('bs58');",
            1
        )
        changes.append("bs58_import")

    # 2. Add dotenv as line 1
    if not data.startswith(b"require('dotenv').config();") and b"require('dotenv')" not in data[:200]:
        data = b"require('dotenv').config();\n" + data
        changes.append("dotenv")

    # 3. WALLET_ADDR
    m = re.search(rb"const WALLET_ADDR = '([^']+)'", data)
    if m and not m.group(1).startswith(b"process"):
        new = b"const WALLET_ADDR = process.env.WALLET_ADDRESS || 'FALLBACK';"
        data = data.replace(m.group(0), new, 1)
        changes.append("WALLET_ADDR")

    # 4. WALLET_FILE
    m = re.search(rb"const WALLET_FILE = '([^']+)'", data)
    if m and "/root/" in m.group(1) or (m and not m.group(1).startswith(b"process")):
        # Default fallback to ./data/wallet.json
        new = b"const WALLET_FILE = process.env.WALLET_FILE || './data/wallet.json';"
        data = data.replace(m.group(0), new, 1)
        changes.append("WALLET_FILE")

    # 5. MY_PLAYER_ID — convert const → let, env-driven
    m = re.search(rb"const MY_PLAYER_ID = '([^']+)';", data)
    if m:
        new = b"let MY_PLAYER_ID = process.env.MY_PLAYER_ID || '" + m.group(1) + b"';"
        data = data.replace(m.group(0), new, 1)
        changes.append("MY_PLAYER_ID")

    # 6. TOKEN_PATH — move from /tmp/ to ./data/
    # The original may have 4 dots between name and .txt; build safely
    D = bytes([46])  # dot
    four_dots = D * 4
    # Find any /tmp/<filename>....txt pattern in TOKEN_PATH
    m = re.search(rb"const TOKEN_PATH\s*=\s*'/tmp/([a-zA-Z0-9_]+)" + four_dots + rb"([^']*)';", data)
    if not m:
        # Try simple TOKEN_PATH
        m = re.search(rb"const TOKEN_PATH\s*=\s*'([^']+)';", data)
    if m:
        old_path = m.group(0)
        # Build new path: ./data/<botname>-token.txt
        botname_match = re.search(rb"/tmp/([a-zA-Z0-9_]+)", old_path)
        botname = botname_match.group(1).decode() if botname_match else "bot"
        new_path = f"const TOKEN_PATH = './data/{botname}-token.txt';".encode()
        data = data.replace(old_path, new_path, 1)
        changes.append("TOKEN_PATH")

    if changes:
        Path(BOT_JS).write_bytes(data)
        print(f"Applied: {', '.join(changes)}")
    else:
        print("No patches needed (already applied or different structure).")

    # Verify syntax
    print(f"\nRun `node -c {BOT_JS}` to verify syntax.")


if __name__ == "__main__":
    main()
