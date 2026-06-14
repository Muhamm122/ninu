# Ubuntu 24.04 Fresh VPS — Setup Pitfalls

Ubuntu 24.04 LTS ("Noble Numbat") is the default for many new VPS images. It introduced several changes that bite scripts written for 20.04/22.04. Documented here so the next VPS setup doesn't waste hours rediscovering them.

---

## 1. PEP 668 — `externally-managed-environment`

**Symptom**:
```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
    
note: If you believe this is a mistake, please contact your
Python installation's maintainer with information about the
```

**Cause**: Ubuntu 24.04 marks the system Python as "externally managed" (PEP 668). `pip install <pkg>` is blocked to prevent breaking system tools (apt-managed packages).

**Fix** (pick one):

1. **Recommended — use a venv**:
   ```bash
   python3 -m venv /opt/myapp-venv
   /opt/myapp-venv/bin/pip install <pkg>
   /opt/myapp-venv/bin/python -c "import <pkg>"
   ```

2. **Override with `--break-system-packages`** (use only for system services where venv is overkill):
   ```bash
   pip install --break-system-packages <pkg>
   ```

3. **Use `pipx`** for CLI tools (creates isolated env automatically):
   ```bash
   apt install -y pipx
   pipx install <cli-tool>
   pipx ensurepath
   ```

**For Hermes Agent on Ubuntu 24.04** — the official install script handles this:
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```
It uses a venv at `~/.hermes/hermes-agent/venv/`. Don't try to `pip install` Hermes globally on 24.04.

**For ad-hoc Python packages** (paramiko, requests, etc.) used in agent scripts — `--break-system-packages` is the pragmatic choice. venv is correct for production services.

---

## 2. Python 3.12 default (3.11 not preinstalled)

**Symptom**: A script requiring Python 3.11 fails because system has 3.12.

**Fix** (if you really need 3.11):
```bash
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev
```

But for most agent scripts, **just use 3.12** — it's the new default and works fine. The "must use 3.11" requirement is mostly vestigial (3.10+ has all the features Hermes needs).

**Hermes install** expects Python 3.10+. On AlmaLinux 9 (which has 3.9) you need to install 3.11+ explicitly. On Ubuntu 24.04, 3.12 is fine out of the box.

---

## 3. `apt upgrade` hangs on `daemon-reload` (interactive prompt)

**Symptom**: `apt upgrade -y` hangs at "Daemons using outdated libraries" prompt waiting for confirmation.

**Fix**:
```bash
DEBIAN_FRONTEND=noninteractive apt upgrade -y
```

This is **critical** for unattended paramiko-driven installs. Without `DEBIAN_FRONTEND=noninteractive`, the apt upgrade will wait for stdin and paramiko will timeout.

---

## 4. `iptables` vs `nftables` / `ufw`

Ubuntu 24.04 uses `nftables` as the backend. `ufw` still works (it generates nftables rules). `iptables` is a legacy compatibility shim.

For agent scripts, **use `ufw`** — it's the same API as 22.04:
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw --force enable
```

Don't try to call `iptables` directly on 24.04 unless you know what you're doing.

---

## 5. systemd-resolved controls `/etc/resolv.conf`

**Symptom**: DNS works initially but breaks after reboot, OR `/etc/resolv.conf` shows `127.0.0.53` instead of real nameservers.

**Cause**: Ubuntu 24.04 uses `systemd-resolved` as a local DNS stub. `/etc/resolv.conf` is a symlink to `/run/systemd/resolve/stub-resolv.conf` which points to 127.0.0.53.

**If you need custom DNS** (e.g., to bypass a blocked CDN), edit `/etc/systemd/resolved.conf`:
```ini
[Resolve]
DNS=1.1.1.1 8.8.8.8
```
Then:
```bash
systemctl restart systemd-resolved
```

**Don't** edit `/etc/resolv.conf` directly — it's a symlink and will be overwritten.

**For AlmaLinux 9 (different issue)**: `/etc/resolv.conf` is empty by default and not symlinked. Just write to it directly.

---

## 6. Node.js — `which node` returns nothing right after `npm install -g`

**Symptom**: `npm install -g hermes-agent` succeeds, but `which hermes` returns nothing, and `hermes` command not found.

**Cause**: `npm install -g` installs to a prefix not in the current shell's `$PATH` (e.g., `/usr/local/lib/node_modules` while `$PATH` only has `/usr/bin`).

**Fix**:
```bash
# Find where it actually went
npm root -g
npm bin -g  # deprecated but still works
# Usually: /usr/local/lib/node_modules + /usr/local/bin

# Add to PATH (one-time)
export PATH="$(npm root -g)/../bin:$PATH"

# Make permanent
echo 'export PATH="$(npm root -g)/../bin:$PATH"' >> ~/.bashrc

# OR install with explicit prefix
npm install -g --prefix=/usr/local <pkg>
```

**For systemd services** — always use the absolute path:
```ini
ExecStart=/usr/local/bin/node /opt/myapp/index.js
# NOT
ExecStart=node /opt/myapp/index.js
```

Service starts in a minimal environment where `node` may not be in `$PATH`.

---

## 7. SSH password auth may be disabled

**Symptom**: SSH with password fails with "Permission denied (publickey)" even with the right password.

**Cause**: Many VPS providers (especially AWS, DigitalOcean) ship Ubuntu 24.04 images with `PasswordAuthentication no`.

**Fix** (when you have console access):
1. Open VPS console from provider dashboard
2. Edit `/etc/ssh/sshd_config`:
   ```
   PasswordAuthentication yes
   ```
3. `systemctl restart sshd`

**Alternative — use SSH keys from the start** (preferred):
```bash
# Generate key on agent's machine
ssh-keygen -t ed25519 -f ~/.ssh/vps_key -N ""
# Add public key to ~/.ssh/authorized_keys on VPS (via console or initial setup)
```

**From agent perspective** — if the user can only provide a password (no key), use **paramiko** (see `paramiko-remote-ops.md`):
```python
client.connect(host, port=22, username='root', password=passwd, 
               look_for_keys=False, allow_agent=False,
               allow_missing_host_key=True)
```

---

## 8. `apt update` may need IPv6 disabled in some networks

**Symptom**: `apt update` hangs on `Connecting to archive.ubuntu.com` for several minutes.

**Cause**: IPv6 DNS resolves but IPv6 connectivity is broken on the network.

**Fix**:
```bash
sysctl -w net.ipv6.conf.all.disable_ipv6=1
sysctl -w net.ipv6.conf.default.disable_ipv6=1
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
```

Or in `/etc/apt/apt.conf.d/99force-ipv4`:
```
Acquire::ForceIPv4 "true";
```

---

## 9. fail2ban needs explicit SSH jail config on 24.04

**Symptom**: `apt install fail2ban` succeeds but no jail is active — `fail2ban-client status` returns "0 jail".

**Cause**: Ubuntu 24.04 fail2ban package no longer ships with `jail.conf` enabling sshd by default.

**Fix**:
```bash
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
EOF

systemctl restart fail2ban
fail2ban-client status sshd  # should show "1 jail, 0 banned"
```

---

## Quick install recipe (Ubuntu 24.04, agent-friendly)

```bash
# 1. System refresh (NEVER skip DEBIAN_FRONTEND=noninteractive in agent scripts)
DEBIAN_FRONTEND=noninteractive apt update
DEBIAN_FRONTEND=noninteractive apt upgrade -y

# 2. Base packages
apt install -y python3 python3-pip python3-venv curl wget git unzip nano \
               htop ufw fail2ban build-essential ca-certificates gnupg

# 3. Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw --force enable

# 4. fail2ban
# (see section 9 above for jail.local)

# 5. Timezone
timedatectl set-timezone Asia/Jakarta

# 6. Python packages — pick strategy:
pip install --break-system-packages paramiko requests  # ad-hoc agent scripts
# OR
python3 -m venv /opt/myapp-venv && /opt/myapp-venv/bin/pip install ...  # production
```

---

## Quick health check (post-setup)

```bash
# System
uname -a
cat /etc/os-release | head -3
uptime

# Resources
free -h
df -h
nproc

# Services
systemctl is-active ufw fail2ban ssh

# Network
ss -tlnp
ip addr show

# Python
python3 --version
pip --version
python3 -c "import paramiko; print('paramiko', paramiko.__version__)" 2>/dev/null
```
