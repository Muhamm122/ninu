#!/bin/bash
# Haus Living Telegram Bot Launcher
# Reads BOT_TOKEN from secrets file or environment

if [ -z "$BOT_TOKEN" ]; then
    TOKEN_FILE="$HOME/.hermes/haus-living/secrets/tg_bot_token"
    if [ -f "$TOKEN_FILE" ]; then
        export BOT_TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')
    else
        echo "ERROR: BOT_TOKEN not set and no secrets file found"
        echo "Create: echo 'YOUR_TOKEN' > $TOKEN_FILE"
        exit 1
    fi
fi

echo "Starting Haus Living Telegram Bot..."
echo "Token length: ${#BOT_TOKEN}"
exec python3 "$HOME/.hermes/haus-living/bots/telegram-bot.py"
