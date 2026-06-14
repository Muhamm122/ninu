# Juno Cash Mining — Setup & Pitfalls

## Algorithm

Juno Cash uses **custom RandomX variant** (NOT standard `rx/0`). Standard XMRig produces invalid hashes.

## ⚠️ XMRig is INCOMPATIBLE with Juno Cash

**All XMRig versions (6.22.3–6.26.0) produce 100% rejected shares ("Invalid hash").**

Root cause: Juno Cash uses a custom RandomX variant. XMRig computes standard `rx/0` hashes that pools reject.

| Miner | Result | Why |
|-------|--------|-----|
| **XMRig** | ❌ All shares rejected | Custom RandomX variant mismatch |
| **SRBMiner** | ❌ SIGSEGV crash | Anti-VM detection on QEMU |
| **junocashd solo** | ✅ Works | Official daemon, correct algo |

**Only junocashd (official daemon) can mine Juno Cash correctly.**

## Node Config Quirks

| Quirk | Detail |
|-------|--------|
| **Config filename** | Must be `junocashd.conf` (NOT `junocash.conf`) |
| **Mainnet mining** | Use `-gen` flag (NOT `generate` RPC — regtest-only) |
| **Thread control** | `-genproclimit=N` in CLI flag |
| **Mining address** | `t_getminingaddress` RPC |
| **getnewaddress** | Deprecated — use `t_getminingaddress` |
| **localhashps: 0** | Normal during sync/reindex |
| **getbalance error -28** | Normal during reindex |
| **RPC client** | `junocash-cli` utility (NOT `junocashd`) |

## Config File Conflict — CRITICAL PITFALL

**Symptom:** junocashd exit code 1, systemd restart loop.

**Cause:** Two configs — `junocashd.conf` (correct, port 8232) and `junocash.conf` (wrong, port 26788).

**Fix:** Ensure systemd uses `junocashd.conf`.

## Lock File Pitfall

**Symptom:** "Cannot obtain a lock on data directory."

**Fix:** `killall junocashd; rm -f /root/.junocash/.lock`

## SSH File Writing — Critical Pitfall

**NEVER use sshpass + heredoc for multi-line files.** Use write locally → SCP → execute pattern instead.

## Install Path (Ubuntu + AlmaLinux/RHEL)

junocashd v0.9.12 ships as a self-contained linux64 tarball (no compile needed). Install in 4 steps on either OS family:

```bash
# Detect OS first
cat /etc/os-release | grep ^ID=   # ubuntu | almalinux | debian | rhel | rocky | fedora

# Ubuntu/Debian
apt-get install -y wget tar libssl-dev libcurl4-openssl-dev

# AlmaLinux/RHEL/Rocky/Fedora
dnf install -y openssl-devel libcurl-devel boost-devel wget tar

# Download + verify + install (same on all distros)
cd /tmp
wget -q https://github.com/juno-cash/junocash/releases/download/v0.9.12/junocash-0.9.12-linux64.tar.gz
wget -q https://github.com/juno-cash/junocash/releases/download/v0.9.12/SHA256SUMS
sha256sum -c --ignore-missing SHA256SUMS          # must report OK
tar -xzf junocash-0.9.12-linux64.tar.gz           # extracts to junocash-0.9.12/ (not junocash-0.9.12-linux64/)
install -m 755 junocash-0.9.12/bin/junocashd /usr/local/bin/junocashd
install -m 755 junocash-0.9.12/bin/junocash-cli /usr/local/bin/junocash-cli
```

Re-runnable install script: `scripts/install_junocashd_remote.py` — handles OS detect, deps, config, systemd, and paramiko-safe daemon start in one shot.

**Templates** (drop-in, no edits): `templates/junocashd.service` (systemd unit) and `templates/junocashd.conf` (mainnet config with seed nodes baked in).

## ⚠️ Slow Sync / Stuck at <2 Peers

**Symptom:** Node starts, connects to 0-1 peer, downloads ~150 blocks in 10 min, then stalls. Headers crawl. `getconnectioncount` stays at 1.

**Cause:** Juno Cash network is small and peer discovery via DNS seeds is unreliable.

**Fix — hardcode seed nodes in `junocashd.conf`:**
```
addnode=dnsseed.junocash.com
addnode=seed.junocash.com
addnode=mainnet.junocash.tools
```
Restart daemon: `junocash-cli stop && rm -f .lock && junocashd -daemon`. Peers should jump to 3-8 within a minute.

## ⚠️ `junocashd -daemon` Hangs Paramiko — CRITICAL

**Symptom:** Calling `junocashd -daemon` via `paramiko.SSHClient.exec_command()` blocks for the full timeout (30-60s) and raises `PipeTimeout`/`socket.timeout`, even though the daemon started fine.

**Cause:** `-daemon` mode forks and the daemonized child inherits + keeps open the stdout/stderr file descriptors from the SSH channel. Paramiko's exec_command waits for those FDs to close. They never do.

**Fix — launch via nohup with full FD redirection, return immediately, verify separately:**
```python
ssh.exec_command(
    "pkill -f junocashd 2>/dev/null; sleep 2; rm -f /root/.junocash/.lock; "
    "nohup /usr/local/bin/junocashd -datadir=/root/.junocash "
    "-conf=/root/.junocash/junocashd.conf -daemon "
    "> /var/log/junocashd-startup.log 2>&1 < /dev/null & disown",
    timeout=5  # returns immediately
)
time.sleep(10)  # let daemon bind ports
# Then verify with separate calls
ssh.exec_command("ps aux | grep junocashd | grep -v grep")
ssh.exec_command("ss -tlnp | grep 8234")
```

**Alternative** (if -daemon must be called directly): use `get_pty=False` and accept the timeout, then check `ps` separately — but the daemon DOES start, you just can't read the response.

Encoded in `scripts/install_junocashd_remote.py`.

## Sync Progress Check

**Quick script** (recommended for Telegram/chat replies): `scripts/check_juno_sync.py <host> <user> <key>` — one-line concise status.

**Manual:**
```bash
junocash-cli -datadir=/root/.junocash -conf=/root/.junocash/junocashd.conf getblockchaininfo | python3 -c "import json,sys; d=json.load(sys.stdin); print('Blocks:', d['blocks']); print('Progress: {:.2f}%'.format(d['verificationprogress']*100))"
```

(Write as local script, SCP upload, then execute to avoid SSH quoting issues.)

## Quick-Reference Templates & Scripts

| File | Purpose |
|---|---|
| `templates/junocashd.service` | Systemd unit (Type=forking, PIDFile, no CPUQuota) |
| `templates/junocashd.conf` | Mainnet config (RPC, P2P, seed nodes, mining commented) |
| `scripts/install_junocashd_remote.py` | Full paramiko install: detect OS → install → config → systemd → start |
| `scripts/check_juno_sync.py` | One-shot sync/peer/mining/balance status report |
