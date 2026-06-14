# Paramiko Remote Ops — Password SSH from Python Agent

When the agent needs to SSH to a remote VPS **with a password** (not key-based), `sshpass` + `heredoc` is unreliable for multi-line content. Use Python `paramiko` instead.

This pattern was battle-tested while setting up VPS 104.207.74.67 (Ubuntu 24.04, password auth) for JUNO Cash mining — `sshpass` + `expect` were unavailable, and `sshpass + ssh + heredoc` corrupted multi-line Python scripts. Paramiko SFTP gave reliable file transfer.

---

## When to use paramiko vs sshpass

| Scenario | Use |
|---|---|
| Quick one-liner with no special chars | `sshpass ssh host 'cmd'` |
| Multi-line file write, JSON, Python, configs | **paramiko SFTP** |
| Long-lived daemon (junocashd, xmrig) | `nohup ... & disown` via paramiko exec_command |
| File transfer (download/upload) | paramiko SFTP `put()` / `get()` |
| Reconnect loops, polling | paramiko transport with keepalive |

---

## Working pattern: connect + exec + SFTP

```python
import paramiko, time

host = '104.207.74.67'
port = 22
user = 'root'
passwd = 'USER_PROVIDED_PASSWORD'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # accept new host key silently
client.connect(host, port=port, username=user, password=passwd, timeout=15, look_for_keys=False, allow_agent=False)

def run(cmd, timeout=60):
    """Run a command. Returns (rc, stdout, stderr)."""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    rc = stdout.channel.recv_exit_status()
    return rc, out, err

# Run command
rc, out, err = run('uptime')
print(f'rc={rc} out={out} err={err}')

# Upload file via SFTP
sftp = client.open_sftp()
sftp.put('/local/file.py', '/remote/file.py')
sftp.chmod('/remote/file.py', 0o755)
sftp.close()

# Download file via SFTP
sftp = client.open_sftp()
sftp.get('/remote/path/file', '/local/file')
sftp.close()

client.close()
```

---

## ⚠️ Critical pitfall: `daemon` flag HANGS paramiko

**Symptom**: `client.exec_command('junocashd -daemon')` hangs forever or until timeout, even though `junocashd` is correctly running in the background on the remote.

**Cause**: The `-daemon` flag tells the program to fork itself, but the **file descriptors (stdin/stdout/stderr) stay connected** to the paramiko channel. paramiko waits for the FDs to close — they never do — so exec_command blocks.

**Fix**: Use the `nohup ... > log 2>&1 < /dev/null & disown` pattern to fully detach:

```python
# WRONG — hangs paramiko
run('junocashd -daemon')

# WRONG — still has FDs connected
run('nohup junocashd -daemon &')

# RIGHT — fully detaches, paramiko returns immediately
run('nohup junocashd -datadir=/root/.junocash -conf=/root/.junocash/junocashd.conf '
    '> /root/.junocash/debug.log 2>&1 < /dev/null & disown')
```

The `disown` removes the process from the shell's job table so the shell can exit cleanly. `< /dev/null` and `> log 2>&1` close stdio. Without **all three** (`nohup` + `&` + `disown` + redirected stdio), paramiko will hang.

**Prefer systemd for long-running daemons.** The nohup pattern is for quick starts before the systemd service is configured. Once the service file is in place, use `systemctl start` instead.

---

## Pattern: write file locally, SCP, run

Most reliable way to deploy a multi-line file (Python script, systemd service, config) to a remote VPS:

```python
import paramiko, tempfile, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=22, username='root', password=passwd, timeout=15, look_for_keys=False, allow_agent=False)

# 1. Write content to local tmp file
content = """#!/bin/bash
echo "multi-line script with $vars and 'quotes' and special chars"
"""
with open('/tmp/deploy_script.sh', 'w') as f:
    f.write(content)

# 2. SCP to remote
sftp = client.open_sftp()
sftp.put('/tmp/deploy_script.sh', '/root/deploy_script.sh')
sftp.chmod('/root/deploy_script.sh', 0o755)
sftp.close()

# 3. Execute
stdin, stdout, stderr = client.exec_command('bash /root/deploy_script.sh')
print(stdout.read().decode())
```

**Why not `cat > remote << EOF` via sshpass?** Nested quoting across 3 layers (local shell → ssh → remote shell) ALWAYS breaks for content with quotes, `$vars`, backticks, or special chars. Local write + SCP avoids the issue entirely.

---

## Pattern: connection health check

```python
import paramiko

def is_reachable(host, port=22, timeout=5):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, username='root', password=passwd,
                       timeout=timeout, look_for_keys=False, allow_agent=False,
                       banner_timeout=timeout, auth_timeout=timeout)
        client.close()
        return True
    except Exception as e:
        return False
```

For batch health checks across multiple VPS, use the **TCP port check** approach first (faster), then paramiko if the port is open:

```python
import socket
def port_open(host, port=22, timeout=3):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False
```

---

## Pattern: install paramiko locally

```bash
pip install paramiko        # if PEP 668 OK
pip install --break-system-packages paramiko  # Ubuntu 24.04+
# or in a venv
python3 -m venv .venv && source .venv/bin/activate && pip install paramiko pexpect
```

---

## Connection security notes

- `look_for_keys=False, allow_agent=False` — disable SSH key/agent auth, force password
- `set_missing_host_key_policy(AutoAddPolicy())` — auto-accept host key (avoids interactive prompt; safe for first connect to a known VPS)
- Store password in **memory only** (not in scripts or shell history). Use a separate secrets file referenced by path
- Always close the client: `client.close()` (or use `with` statement)

---

## VPS setup walkthrough (real example)

Setup of VPS 104.207.74.67 (Ubuntu 24.04) for JUNO mining via paramiko:

```python
import paramiko, time

host = '104.207.74.67'
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, port=22, username='root', password=PASS, timeout=15,
               look_for_keys=False, allow_agent=False)

def run(cmd, t=120):
    si, so, se = client.exec_command(cmd, timeout=t)
    return so.channel.recv_exit_status(), so.read().decode(), se.read().decode()

# 1. Update + install base packages
run('apt update && DEBIAN_FRONTEND=noninteractive apt upgrade -y', t=300)
run('apt install -y python3 python3-pip python3-venv curl wget git unzip nano htop ufw fail2ban build-essential')

# 2. Create non-root user
run('adduser --disabled-password --gecos "" cupang')
run('echo "cupang:cupang2026" | chpasswd')
run('usermod -aG sudo cupang')

# 3. Enable firewall
run('ufw default deny incoming && ufw default allow outgoing')
run('ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp')
run('ufw --force enable')
run('systemctl enable --now fail2ban')

# 4. Install Node.js 20
run('curl -fsSL https://deb.nodesource.com/setup_20.x | bash -')
run('apt install -y nodejs')

# 5. Install Docker
run('curl -fsSL https://get.docker.com | sh')
run('systemctl enable --now docker')

# 6. Install Hermes Agent (Ubuntu 24.04 PEP 668 issue!)
#    PEP 668 requires --break-system-packages OR venv
run('python3 -m venv /opt/hermes-venv')
run('/opt/hermes-venv/bin/pip install --quiet hermes-agent')
# (binary ends up in /opt/hermes-venv/bin/hermes — symlink to /usr/local/bin/hermes if desired)

# 7. Verify
rc, out, _ = run('node --version && npm --version && python3 --version && which hermes')
print(out)

client.close()
```

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `paramiko.ssh_exception.NoValidConnectionsError` | Port closed or filtered | Check `ufw status` / VPS firewall / `nc -zv host 22` |
| `paramiko.ssh_exception.AuthenticationException` | Wrong password or `PermitRootLogin no` | Use non-root user OR enable root login in `/etc/ssh/sshd_config` |
| `Bad host key` | Host key changed | `ssh-keygen -R <host>` then reconnect (paramiko will re-add via AutoAddPolicy) |
| `SSH session not active` after `client.close()` | Reused client after close | Re-create client or use try/finally |
| Hangs after `nohup daemon &` | Daemon process holds FDs | Add `> log 2>&1 < /dev/null & disown` |
| `pip install paramiko` fails on Ubuntu 24.04 | PEP 668 externally-managed | Use `pip install --break-system-packages` or venv |
