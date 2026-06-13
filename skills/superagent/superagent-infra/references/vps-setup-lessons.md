# VPS Setup — Lessons Learned (2026-06-13/14)

## SSH Access Patterns

### Password Auth Disabled (Common on Modern VPS)
Most modern VPS providers disable password auth via SSH. Use Python paramiko from agent VPS:
```python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=22, username='root', password='PASS', timeout=15)
```

### Key-Based Auth (Preferred for production)
```bash
ssh-keygen -t ed25519 -C "hermes-agent" -f ~/.ssh/id_ed25519 -N ""
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@TARGET_IP
```

## Ubuntu 24.04 Specifics

### PEP 668 — Pip Blocked Globally
Use venv method for Hermes:
```bash
python3 -m venv /opt/hermes-venv
/opt/hermes-venv/bin/pip install hermes-agent
ln -sf /opt/hermes-venv/bin/hermes /usr/local/bin/hermes
```

### Node.js 20 + Docker
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs
curl -fsSL https://get.docker.com | sh && systemctl enable --now docker
```

## API Key Error Patterns

| Error | Meaning | Action |
|-------|---------|--------|
| 403 error 1010 (CastAI) | IP block, keys valid | Keep keys, note IP status |
| 401 (any provider) | Key dead/invalid | Remove from pool immediately |
| 429 | Rate limit | Wait and retry |
| 401 "User not found" (OpenRouter) | Key expired | Get new key |

CastAI blocks most VPS IPs. Keys may work from residential IPs.

## File Migration (VPS to VPS)
```bash
# Source VPS
tar -czf /tmp/migrate.tar.gz -C /home/user .hermes/ bin/
# Target VPS (via paramiko SCP)
scp.put('/tmp/migrate.tar.gz', '/tmp/migrate.tar.gz')
# Extract: tar -xzf /tmp/migrate.tar.gz -C /root/
```

## Junocash Mining Quick Reference
- Binary: `/usr/local/bin/junocashd` (v0.9.12)
- Config: `/root/.junocash/junocash.conf`
- Systemd: `systemctl start junocash-miner`
- Status: `junocash-cli getmininginfo`
- Mining only effective after 100% blockchain sync

## User Preference
User wants DIRECT EXECUTION. Use paramiko to SSH and run commands programmatically. Do NOT ask user to copy-paste scripts unless SSH is impossible.
