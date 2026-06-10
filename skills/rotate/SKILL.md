---
name: rotate
description: "API key rotation — auto-rotate to next key in pool on command or error trigger"
trigger:
  keywords: ["rotate", "ganti key", "key rotation", "rate limit", "error key"]
  auto_execute: true
  no_confirm: true
---

# Rotate — API Key Rotation

## Trigger
User says "rotate" (or variants) → execute immediately, no confirmation.

## Command
```bash
~/bin/rotate now [error_type]
```

## Pool Config
- Pool: `primary`
- Strategy: `round_robin`
- Keys: mimo-1, mimo-2, openrouter-1

## Execution
1. Run `~/bin/rotate now`
2. Parse output for new active key
3. Report: `✅ Rotated to [key_id] ([provider]) | Model: [model]`
4. Note: Hermes hot-reloads on next request (no restart needed)

## On Error/Rotate Trigger
When user reports error/rate limit:
1. Auto-detect error type (rate_limit / exhausted / invalid)
2. Run `~/bin/rotate now <error_type>`
3. Report result

## Output Format
```
🔄 Rotating...
✅ Active: [key_id] ([provider]) | Model: [model]
⏭️ Next: [next_key_id]
```
