# Troubleshooting — Extended Pitfalls

## Python/Pillow Opacity Computation

**Pitfall**: `intensity()` is not a built-in Python function.

```python
# WRONG — causes NameError
fill=(*color, intensity(255 * 0.55))

# CORRECT
fill=(*color, int(255 * 0.55))
```

This typically appears when computing Pillow RGBA opacity values. The correct built-in is `int()`.

## Shell Quoting with Special Characters

**Pitfall**: Inline `curl` or `python3 -c` with quotes, `$`, `!`, or backslashes fail repeatedly.

```bash
# WRONG — breaks on special characters
curl -X POST http://api/endpoint -d '{"key": "value with $pecial chars"}'

# CORRECT — write to file first
echo '{"key": "value with $pecial chars"}' > /tmp/payload.json
curl -X POST http://api/endpoint -d @/tmp/payload.json
```

## Nginx sites-enabled/ Symlink Check

**Pitfall**: `sites-enabled/` may be a directory with separate file copies, not symlinks.

```bash
# Check
ls -la /etc/nginx/sites-enabled/site-name
# If regular file (not "-> ../sites-available/site-name"), it's a copy

# Must edit BOTH files independently
sudo sed -i '/pattern/,/^}/d' /etc/nginx/sites-available/site-name
sudo sed -i '/pattern/,/^}/d' /etc/nginx/sites-enabled/site-name
```

## Docker sudo Requirement

**Pitfall**: `ubuntu` user not in `docker` group → all docker commands need `sudo`.

Affects: health monitors, service managers, backup scripts.

**Fix**: Either add user to docker group or prefix all docker commands with `sudo` in scripts.

## Pillow getdata() Deprecation

**Pitfall**: `Image.Image.getdata()` is deprecated in Pillow 11+, removed in Pillow 14 (2027-10).

```python
# DEPRECATED
pixels = list(img.getdata())

# Use numpy instead
import numpy as np
pixels = np.array(img)
```

## 9Router FreeLLMAPI Key Rejection (401)

**Pitfall**: When FreeLLMAPI is added as an OpenAI-compatible provider in 9Router, requests routed through 9Router return 401 "Incorrect API key provided" even when the same `freellmapi-...` key works with direct `curl http://localhost:3001/v1/chat/completions`.

**Root cause**: FreeLLMAPI validates its own key format on the Authorization header. 9Router forwards the key, but FreeLLMAPI may receive it in a modified context (header format, model routing) that triggers its OpenAI-format validation check, which rejects the `freellmapi-` prefix.

**Workaround**: Use FreeLLMAPI as a **direct Hermes custom provider** (not through 9Router). Use 9Router for other providers (NVIDIA NIM, OpenRouter, etc.) that accept standard API keys.

**Symptom in 9Router logs**: `[node-id/model-id] [401]: {"error":{"message":"Incorrect API key provided: freellma***********************************************fde0"}}` — note the key is partially visible (masked by 9Router), confirming it IS being forwarded but rejected by FreeLLMAPI.

## Node.js CLI Tools on Headless VPS — Auto-Exit

**Pitfall**: Node.js CLI tools with interactive TUI menus (9router, etc.) auto-select "exit" after a timeout when stdin is not a TTY. The process starts (shows "Ready in 0ms"), then immediately prints "Exiting..." and exits cleanly (code 0).

**Fix**: Use headless/background flags in systemd ExecStart:
- 9Router: `--tray --no-browser --skip-update --log`
- Generic: check for `--daemon`, `--headless`, `--no-tty`, `--background` flags

**Diagnostic**: `journalctl -u <service> --no-pager -n 10` — look for "Exiting..." without any preceding error.

## 9Router SQLite Direct Injection — Stop Service First

**Pitfall**: Writing to `/home/ubuntu/.9router/db/data.sqlite` while 9Router is running causes lock conflicts or data loss.

**Fix**: Always `sudo systemctl stop 9router` before modifying the DB, then `sudo systemctl start 9router` after commit.
