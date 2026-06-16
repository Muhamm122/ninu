# VPS Security Hardening — Full Playbook

Comprehensive, production-grade hardening for a fresh Ubuntu 24.04 VPS. Goes beyond the
bootstrap checklist (UFW + fail2ban + SSH) — adds auditd, sysctl kernel hardening, rkhunter,
security cron jobs, and UFW logging.

**Trigger when**: user says "aktifkan fail2ban", "hardening VPS", "secure my VPS", "aktifkan
pengamanan", "secure this VPS", "set up security", or after a fresh VPS is provisioned.

**Verified 2026-06-17** on Ubuntu 24.04.2 LTS (cupang VPS).

---

## 1. Inventory Current State (5 sec)

```bash
echo "=== fail2ban ==="; systemctl is-active fail2ban 2>/dev/null || echo "NOT INSTALLED"
echo "=== UFW ==="; ufw status 2>/dev/null | head -3
echo "=== SSH config ==="; grep -E "^(PermitRoot|PasswordAuth|MaxAuthTries)" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null
echo "=== unattended-upgrades ==="; systemctl is-active unattended-upgrades
echo "=== Listening ==="; ss -tlnp 2>/dev/null | head -10
```

## 2. Install + Configure fail2ban

```bash
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban whois
```

**`/etc/fail2ban/jail.local`** (comprehensive — SSH + web + repeat offenders):

```ini
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16

[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = %(sshd_log)s
maxretry = 5

[sshd-ddos]
enabled = true
port    = ssh
filter  = sshd-ddos
logpath = %(sshd_log)s
maxretry = 10

[nginx-http-auth]
enabled = true
filter  = nginx-http-auth
port    = http,https
logpath = /var/log/nginx/error.log

[nginx-botsearch]
enabled = true
filter  = nginx-botsearch
port    = http,https
logpath = /var/log/nginx/access.log

[recidive]
enabled  = true
filter   = recidive
logpath  = /var/log/fail2ban.log
bantime  = 1w
findtime = 1d
maxretry = 5
```

```bash
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
sudo fail2ban-client status  # verify jails loaded
```

**Jails loaded**: sshd, sshd-ddos, nginx-http-auth, nginx-botsearch, recidive.

**Recidive** = repeat offenders get **1 WEEK** ban (escalation from 1h).

## 3. SSH Hardening (`/etc/ssh/sshd_config.d/99-hermes-hardening.conf`)

```bash
sudo tee /etc/ssh/sshd_config.d/99-hermes-hardening.conf > /dev/null << 'EOF'
PermitRootLogin no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitEmptyPasswords no
UseDNS no
Protocol 2
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
EOF
sudo sshd -t  # test config
sudo systemctl reload sshd
```

**Verify**:
```bash
sudo sshd -T | grep -E "^(permitrootlogin|maxauthtries|logingrace|clientalive|x11forwarding|allowtcp|usedns|ciphers|macs|kexalgorithms)"
```

**Note**: `sshd -T` may fail in containers (`sshd.service not found`). Config is still active for next SSH start.

## 4. Kernel Sysctl Hardening (`/etc/sysctl.d/99-hermes-hardening.conf`)

```bash
sudo tee /etc/sysctl.d/99-hermes-hardening.conf > /dev/null << 'EOF'
# IP forwarding (off for server)
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# SYN flood + spoofing protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_rfc1337 = 1

# IPv6 hardening
net.ipv6.conf.all.accept_ra = 0
net.ipv6.conf.default.accept_ra = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Kernel hardening
kernel.randomize_va_space = 2
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.yama.ptrace_scope = 3
kernel.sysrq = 0
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
EOF

sudo sysctl -p /etc/sysctl.d/99-hermes-hardening.conf
```

**What this does**:
- IP spoofing = blocked (rp_filter, no source route)
- SYN flood = mitigated (syncookies)
- ASLR = full (randomize_va_space=2)
- Kernel pointer leak = blocked (kptr_restrict=2)
- dmesg leak = blocked (dmesg_restrict=1)
- ptrace = blocked (yama.ptrace_scope=3)
- Symlink/hardlink races = protected

## 5. Auditd (`/etc/audit/rules.d/99-hermes.rules`)

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y auditd audispd-plugins
sudo systemctl enable --now auditd
```

**Rules** — watch identity, SSH, cron, systemd, network, fail2ban, binary changes:

```bash
sudo tee /etc/audit/rules.d/99-hermes.rules > /dev/null << 'EOF'
# Identity
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/gshadow -p wa -k identity
-w /etc/sudoers -p wa -k sudoers
-w /etc/sudoers.d/ -p wa -k sudoers

# SSH
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /etc/ssh/sshd_config.d/ -p wa -k sshd_config
-w /home/*/.ssh/ -p wa -k ssh_keys
-w /root/.ssh/ -p wa -k ssh_keys

# Cron
-w /etc/crontab -p wa -k cron
-w /etc/cron.d/ -p wa -k cron
-w /etc/cron.daily/ -p wa -k cron
-w /etc/cron.hourly/ -p wa -k cron
-w /etc/cron.weekly/ -p wa -k cron
-w /etc/cron.monthly/ -p wa -k cron
-w /var/spool/cron/ -p wa -k cron
-w /var/spool/cron/crontabs/ -p wa -k cron

# Service tampering
-w /etc/systemd/ -p wa -k systemd
-w /etc/init.d/ -p wa -k init
-w /usr/lib/systemd/system/ -p wa -k systemd

# Network
-w /etc/hosts -p wa -k hosts
-w /etc/resolv.conf -p wa -k dns
-w /etc/iptables/ -p wa -k iptables
-w /etc/ufw/ -p wa -k ufw

# fail2ban
-w /etc/fail2ban/ -p wa -k fail2ban

# Binaries
-w /usr/bin/ -p wa -k binaries
-w /usr/sbin/ -p wa -k binaries
-w /usr/local/bin/ -p wa -k binaries
-w /usr/local/sbin/ -p wa -k binaries
EOF

sudo augenrules --load
sudo auditctl -l | head -20  # verify
```

**Query audit log**:
```bash
sudo ausearch -k identity  # who changed /etc/passwd?
sudo ausearch -k sshd_config  # who modified SSH config?
sudo aureport --summary  # daily summary
```

## 6. Rootkit Detection (rkhunter, chkrootkit, debsums)

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y rkhunter chkrootkit debsums
sudo rkhunter --update
sudo rkhunter --propupd  # baseline known-good file hashes
```

## 7. UFW Logging

```bash
sudo ufw logging on
# Verify
sudo ufw status verbose
# Log location: /var/log/ufw.log
```

## 8. Security Cron Jobs (`/etc/cron.d/hermes-security`)

```bash
sudo tee /etc/cron.d/hermes-security > /dev/null << 'EOF'
# Hermes security scans - automated

# Daily rkhunter scan at 3 AM
0 3 * * * root /usr/bin/rkhunter --check --sk --nocolor --quiet --cronjob 2>&1 | mail -s "rkhunter daily scan" root@localhost || true

# Weekly chkrootkit on Sunday 4 AM
0 4 * * 0 root /usr/bin/chkrootkit -q 2>&1 | mail -s "chkrootkit weekly scan" root@localhost || true

# Daily fail2ban status log at 6 AM
0 6 * * * root /usr/bin/fail2ban-client status sshd 2>&1 >> /var/log/fail2ban-status.log

# Weekly audit rules status log
0 5 * * 1 root /sbin/auditctl -l > /var/log/audit-rules-status.log 2>&1
EOF
```

**Note**: For mail to work, install `mailutils` (postfix) — skip if not needed, the `|| true` means cron won't fail.

## 9. Disable Unused Services

```bash
# CUPS printer service (port 631) — not needed on server
sudo systemctl disable --now cups 2>/dev/null
```

Other services to consider disabling (only if NOT used):
- `bluetooth.service` — no BT on server
- `avahi-daemon.service` — mDNS, not needed
- `ModemManager.service` — no modem
- `wpa_supplicant.service` — no WiFi

## 10. Verify Everything

```bash
echo "=== 1. fail2ban ==="
sudo systemctl is-active fail2ban
sudo fail2ban-client status | grep "Jail list"

echo "=== 2. UFW ==="
sudo ufw status | head -3

echo "=== 3. SSH ==="
sudo sshd -T 2>/dev/null | grep -E "^(permitrootlogin|maxauthtries|logingrace|clientalive|x11forwarding|allowtcp|usedns)"

echo "=== 4. Sysctl ==="
sysctl -p /etc/sysctl.d/99-hermes-hardening.conf 2>&1 | tail -3

echo "=== 5. Auditd ==="
sudo systemctl is-active auditd
echo "Active rules: $(sudo auditctl -l 2>/dev/null | grep -c '^-w')"

echo "=== 6. Rootkit detection ==="
which rkhunter chkrootkit debsums

echo "=== 7. Unattended-upgrades ==="
sudo systemctl is-active unattended-upgrades

echo "=== 8. Security cron ==="
ls -la /etc/cron.d/hermes-security

echo "=== Active security services ==="
systemctl list-units --type=service --state=running 2>/dev/null | grep -E "fail2ban|auditd|ufw|unattended|cron|ssh"
```

---

## Optional Add-ons (Not Included Above)

| Add-on | Use case | Install |
|--------|----------|---------|
| **Port knocking** | Hide SSH from port scan | `apt install knockd` |
| **2FA for SSH** | TOTP on SSH login | `apt install libpam-google-authenticator` |
| **CrowdSec** | Shared blocklist + fail2ban alternative | Docker: `caddy/crowdsec` |
| **AIDE** | File integrity monitoring | `apt install aide` + `aide --init` |
| **ClamAV** | Malware scanner | `apt install clamav clamav-daemon` |
| **WireGuard VPN** | Hide SSH from public | `apt install wireguard` |
| **OSSEC/Wazuh** | HIDS | Docker image |
| **rspamd** | Anti-spam if running mail | `apt install rspamd` |

## Pitfalls

- **`fail2ban-client status` returns "0 jails"** → jail.local has syntax error, check `journalctl -u fail2ban`
- **`ufw logging on` floods /var/log/ufw.log** → use `sudo ufw logging low` to reduce verbosity
- **`sysctl -p` returns "permission denied on key"** → running in container without CAP_SYS_ADMIN, persists on host
- **auditd "backlog 2" warning at startup** → normal, backlog limit hit during boot, clears in 10 min
- **rkhunter false positives on QEMU VMs** → some checks look for "VMware/VirtualBox" strings and flag QEMU as suspicious. Suppress with `ALLOWDEVFILE="/dev/shm"` in `/etc/rkhunter.conf`
- **Don't disable root login until you have a non-root user with sudo** — lockout risk
- **Backup /etc/ssh/sshd_config.d/ before changes** — wrong config = SSH lockout (recover via VNC/console)
- **`apt install whois` needed for fail2ban** — without it, whois lookups for ban reasons fail silently

## See Also

- `references/vps-setup-lessons.md` — fresh VPS install pitfalls
- `references/vps-add-provisioning.md` — add VPS to fleet
- `references/paramiko-ssh-pattern.md` — programmatic SSH
