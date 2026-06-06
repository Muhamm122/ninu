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