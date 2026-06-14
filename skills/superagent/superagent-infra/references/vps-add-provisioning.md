---
name: vps-add-provisioning
description: "Recipe for adding a brand new VPS to the existing fleet — health check, key-based auth, password disable, inventory tracking, SSH config shortcut, DOWN detection."
---

# Add New VPS to Fleet

When user says "tambahkan VPS ini" with IP/port/user/password, follow this recipe. Works for any Linux VPS (Ubuntu, AlmaLinux, Rocky, Debian) — **check OS family first** before running package commands.

## Step 0 — Health Check FIRST

Before doing anything, confirm the VPS is actually reachable. If `ping -c 3 -W 5 IP` shows 100% packet loss → mark as **DOWN** and stop.

```bash
ping -c 3 -W 5 <IP> 2>&1
# → If "100% packet loss" → STOP, report DOWN status, ask user
# → If replies → continue
```

Why first: wasting 30s on SSH that will timeout is silly. And user often asks "cek sync" expecting confirmation the host is alive.

## Step 1 — Detect OS Family

```bash
# Paramiko script or sshpass
ssh root@<IP> "cat /etc/os-release | grep -E '^(ID|NAME|VERSION_ID)='"
```

Map:
- `ID="ubuntu"` / `ID="debian"` → `apt` package manager
- `ID="almalinux"` / `ID="rhel"` / `ID="centos"` / `ID="rocky"` → `dnf` package manager
- `ID="fedora"` → `dnf`

Different package names too: `apt install -y python3-venv` vs `dnf install -y python3-virtualenv`.

## Step 2 — Test Connection with Password

Use **paramiko** (Python), not sshpass CLI. Cleaner error handling and no nested-quote issues. See `scripts/vps_add.py` template below.

## Step 3 — Push SSH Key, Disable Password

```python
# Paramiko — push local pubkey, disable PasswordAuthentication
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(IP, port=22, username='root', password=PASSWORD, timeout=20)

PUBKEY = open(os.path.expanduser('~/.ssh/<alias>')).read().strip()
cmd = f'''mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
echo "{PUBKEY}" >> ~/.ssh/authorized_keys && \
chmod 600 ~/.ssh/authorized_keys && \
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys && \
sed -i 's/^#\\?PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && \
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config.d/*.conf 2>/dev/null; \
echo OK'''

stdin, stdout, stderr = ssh.exec_command(cmd)
ssh.close()  # closes old connection
```

**Why disable password**: key-based auth is mandatory for production. Leaving password auth open = brute force surface. The user can always re-enable via VNC console if locked out.

**Test key-based auth immediately** (don't trust the push succeeded):

```python
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect(IP, port=22, username='root', key_filename=KEY_PATH, timeout=15)
stdin, stdout, stderr = ssh2.exec_command('hostname && whoami && echo KEY_AUTH_OK')
assert b'KEY_AUTH_OK' in stdout.read()
```

If key-based auth fails, **revert the PasswordAuthentication change** before closing. Otherwise user is locked out (only VNC console can recover).

## Step 4 — SSH Config Shortcut

Append to `~/.ssh/config`:

```
Host <alias>
    HostName <IP>
    Port 22
    User <user>
    IdentityFile ~/.ssh/<key-name>
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
```

After: `ssh <alias>` works without password. Test with `ssh <alias> 'hostname'`.

**`StrictHostKeyChecking no` + `UserKnownHostsFile /dev/null`**: Accepts the host key on first connect, never persists it. Safe for short-lived fleet entries; if you want strict key pinning, comment these out and manually add the key.

## Step 5 — Inventory File

Maintain a single JSON inventory at `~/.hermes/credentials/vps_inventory.json` so future sessions can find all VPS without grep:

```json
{
  "vps_utama": {
    "alias": "vps-utama",
    "host": "18.143.107.30",
    "port": 22,
    "user": "ubuntu",
    "os": "Ubuntu 24.04",
    "role": "primary",
    "status": "UP",
    "ssh_alias": "vps-utama"
  },
  "vps_mining2": {
    "alias": "vps-mining2",
    "host": "104.207.75.223",
    "port": 22,
    "user": "root",
    "os": "AlmaLinux 9.8",
    "role": "mining-juno",
    "status": "UP",
    "specs": {"cpu": 12, "ram_gb": 23, "disk_gb": 465},
    "ssh_alias": "vps-mining2"
  }
}
```

`chmod 600` the file. **NEVER include the actual password** in this file — only credentials reference env file.

## Step 6 — Credentials Reference (env file)

```bash
# ~/.hermes/credentials/<vps-alias>.sh
export VPS_<ALIAS>_HOST="1.2.3.4"
export VPS_<ALIAS>_PORT="22"
export VPS_<ALIAS>_USER="root"
export VPS_<ALIAS>_PASS="<password>"  # source this to get the var
export VPS_<ALIAS>_KEY="$HOME/.ssh/<key-name>"
```

`chmod 600`. **Never echo the password in chat output** — reference the file path only.

## DOWN Detection Protocol

When user says "cek sync" or "cek status" and the target is a remote VPS:

1. `ping -c 3 -W 5 <IP>` — first signal
2. If ping OK but service down → service-level issue, not VPS issue
3. If ping fails → mark VPS as DOWN in inventory, ask user (provider console? billing? transient?)
4. Don't waste time sshpass-retrying a DOWN host — user knows better

Update inventory `status` field: `"UP"` / `"DOWN"` / `"DEGRADED"` (ping OK but service down).

## Common OS-Specific Gotchas

| Issue | Ubuntu | AlmaLinux/RHEL |
|---|---|---|
| Firewall | `ufw` | `firewalld` (`firewall-cmd --permanent --add-port=22/tcp && firewall-cmd --reload`) |
| Python venv | `apt install python3.11-venv` | `dnf install python3-virtualenv` |
| Repo add | `add-apt-repository` | `dnf config-manager --set-enabled <repo>` |
| Service enable | `systemctl enable` | same |
| Default SSH | Password or key | Usually key-only (AWS, Azure) |
| Package cache | `apt update` | `dnf makecache` |

## When to Reject

If user gives credentials for a host you can't reach (DOWN), don't try to "force" it. Report status, ask user to verify with provider, then continue.

If user gives credentials for a host in a different region/VPS provider without context, ask which alias to use. Don't auto-name — collisions break SSH config.

## Full Python Template — `scripts/vps_add.py`

```python
#!/usr/bin/env python3
"""Add a new VPS to the fleet: test, push SSH key, disable password, add to inventory."""
import paramiko
import json
import os
import sys

IP = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 22
USER = sys.argv[3] if len(sys.argv) > 3 else "root"
PASSWORD = os.environ.get("VPS_NEW_PASS") or sys.argv[4]  # prefer env var
ALIAS = sys.argv[5] if len(sys.argv) > 5 else f"vps-{IP.replace('.', '-')}"
KEY_PATH = os.path.expanduser(f"~/.ssh/{ALIAS}")
INVENTORY = os.path.expanduser("~/.hermes/credentials/vps_inventory.json")

# 0. Health check
r = subprocess.run(["ping", "-c", "3", "-W", "5", IP], capture_output=True, text=True)
if "100% packet loss" in r.stdout:
    print(f"DOWN {IP} UNREACHABLE. Stopping.")
    sys.exit(1)
print(f"OK {IP} ping OK")

# 1. Generate local key if not exists
if not os.path.exists(KEY_PATH):
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", KEY_PATH, "-N", "", "-C", f"{ALIAS}-2026", "-q"], check=True)
    print(f"OK Key generated: {KEY_PATH}")

with open(KEY_PATH + ".pub") as f:
    pubkey = f.read().strip()

# 2. Push pubkey + disable password
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(IP, port=PORT, username=USER, password=PASSWORD, timeout=20)

stdin, stdout, _ = ssh.exec_command("cat /etc/os-release | grep -E '^(ID|NAME|VERSION_ID)=' | tr '\\n' ' '")
os_info = stdout.read().decode().strip()
print(f"OS: {os_info}")

cmd = f'''mkdir -p ~/.ssh && chmod 700 ~/.ssh && \\
echo "{pubkey}" >> ~/.ssh/authorized_keys && \\
chmod 600 ~/.ssh/authorized_keys && \\
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys && \\
sed -i 's/^#\\\\?PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && \\
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config.d/*.conf 2>/dev/null; \\
echo PUSHED_OK'''
stdin, stdout, stderr = ssh.exec_command(cmd)
out = stdout.read().decode()
print(f"Push: {out.strip()}")
ssh.close()

# 3. Test key-based auth
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh2.connect(IP, port=PORT, username=USER, key_filename=KEY_PATH, timeout=15)
    stdin, stdout, _ = ssh2.exec_command("hostname && uptime && nproc && free -h | head -2")
    info = stdout.read().decode()
    print(f"OK Key-based auth OK\n{info}")
    ssh2.close()
except Exception as e:
    print(f"FAIL Key-based auth FAILED: {e}")
    print("WARNING: Re-enable password auth via VNC console.")
    sys.exit(1)

# 4. SSH config shortcut
config_line = f"""
Host {ALIAS}
    HostName {IP}
    Port {PORT}
    User {USER}
    IdentityFile {KEY_PATH}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
"""
with open(os.path.expanduser("~/.ssh/config"), "a") as f:
    f.write(config_line)
os.chmod(os.path.expanduser("~/.ssh/config"), 0o600)
print(f"OK SSH config: ssh {ALIAS}")

# 5. Update inventory
inv = {}
if os.path.exists(INVENTORY):
    with open(INVENTORY) as f:
        inv = json.load(f)
inv[ALIAS] = {
    "alias": ALIAS,
    "host": IP,
    "port": PORT,
    "user": USER,
    "os": os_info,
    "role": "unspecified",
    "status": "UP",
    "ssh_alias": ALIAS,
}
with open(INVENTORY, "w") as f:
    json.dump(inv, f, indent=2)
os.chmod(INVENTORY, 0o600)
print(f"OK Inventory updated: {INVENTORY}")
print(f"\nUse: ssh {ALIAS}  (no password needed)")
```

## Pitfalls

1. **Don't use `sshpass + ssh` for multi-line commands** — nested quoting always breaks. Use paramiko.
2. **Don't echo the password in chat** — Hermes auto-masks but the user's view of the chat is the source. Reference file path.
3. **Don't disable password before testing key auth** — if key push fails, user is locked out (only VNC recovers).
4. **Don't blindly run `apt` commands on AlmaLinux** — they're `dnf`. Detect first.
5. **Don't add a "DOWN" VPS to active service routing** — mark it DOWN in inventory and exclude.
6. **`StrictHostKeyChecking no` is fine for fleet** — fleet entries rotate often, strict pinning creates more toil than security.
7. **Inventory file MUST be `chmod 600`** — contains hostnames, users, OS info (low-sensitivity but still).
8. **Don't store password in inventory JSON** — only in the env-file (chmod 600) referenced by path.
9. **Service-level "DOWN" != VPS-level "DOWN"** — `ping` works but `systemctl` shows failed = service issue, not host issue.
10. **Same IP across providers** — VPS-mining and VPS-mining2 had different providers (server1.muham.dev, server2.muham.id.my) — don't assume same provider from IP alone.
