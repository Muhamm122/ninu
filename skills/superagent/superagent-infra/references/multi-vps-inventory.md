# Multi-VPS Inventory Pattern

When operating multiple VPS (primary + mining + backups), track them in a single JSON registry for fast status checks. The pattern below is used for the CUPANG setup with 3+ VPS.

## When to use

- User has >1 VPS (mining box, main, backup, regional, etc.)
- Need quick "cek vps terbaru" / "vps utama masih aman?" / "sync saat ini" type status checks
- Want to know which VPS is currently serving which role
- Need to swap to a replacement VPS seamlessly

## File layout

```
~/.hermes/credentials/
├── vps_inventory.json       # multi-VPS registry
├── vps_mining.sh            # sourceable: VPS_MINING_HOST, _PORT, _USER, _PASS, _KEY
├── vps_mining2.sh           # sourceable: same shape, for replacement VPS
└── (per-VPS script)
```

## vps_inventory.json schema

```json
{
  "vps_utama": {
    "alias": "vps-utama",
    "host": "18.143.107.30",
    "port": 22,
    "user": "ubuntu",
    "os": "Ubuntu 24.04",
    "role": "primary",
    "ssh_alias": "vps-utama"
  },
  "vps_mining": {
    "alias": "vps-mining",
    "host": "104.207.74.67",
    "port": 22,
    "user": "root",
    "os": "Ubuntu 24.04.2",
    "role": "mining-juno",
    "status": "DOWN",
    "note": "100% packet loss, server1.muham.dev",
    "ssh_alias": "vps-mining"
  },
  "vps_mining2": {
    "alias": "vps-mining2",
    "host": "104.207.75.223",
    "port": 22,
    "user": "root",
    "os": "AlmaLinux 9.8",
    "role": "mining-juno (replace vps-mining)",
    "status": "UP",
    "specs": {"cpu": 12, "ram_gb": 23, "disk_gb": 465},
    "ssh_alias": "vps-mining2"
  }
}
```

### Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `alias` | ✅ | Short name used in inventory keys + scripts |
| `host` | ✅ | IP or hostname |
| `port` | ✅ | Usually 22 |
| `user` | ✅ | SSH user (root, ubuntu, etc.) |
| `os` | ✅ | Ubuntu 24.04 / AlmaLinux 9.8 / etc. |
| `role` | ✅ | What this VPS does (primary, mining-juno, backup, etc.) |
| `status` | optional | `UP` / `DOWN` — update after every check |
| `note` | optional | Transient issue notes (CF block, sync in progress, etc.) |
| `specs` | optional | `{cpu, ram_gb, disk_gb}` for capacity planning |
| `ssh_alias` | optional | Match `~/.ssh/config` Host entry |

## Per-VPS credential script (sourceable .sh)

```bash
# ~/.hermes/credentials/vps_mining2.sh
# VPS Mining #2 (AlmaLinux 9.8, server2.muham.id.my)
# Replaces: 104.207.74.67 (DOWN)
export VPS_MINING2_HOST="104.207.75.223"
export VPS_MINING2_PORT="22"
export VPS_MINING2_USER="root"
export VPS_MINING2_PASS="BVap512QN3pH9bC0ro"
export VPS_MINING2_KEY="$HOME/.ssh/vps_mining2"
```

Pattern: `VPS_<UPPER_ALIAS>_HOST/PORT/USER/PASS/KEY` env vars, named by alias in inventory.

## Quick status check pattern

```bash
# Single line, sourceable + sshpass
source ~/.hermes/credentials/vps_mining2.sh
sshpass -p "$VPS_MINING2_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
  $VPS_MINING2_USER@$VPS_MINING2_HOST 'uptime && free -h | head -2 && df -h / | tail -1'
```

For role-specific status (mining sync, hashrate, balance, etc.), extend the inline command:
```bash
sshpass -p "$VPS_MINING2_PASS" ssh ... "$VPS_MINING2_USER@$VPS_MINING2_HOST" '
  echo "=== junocashd SYNC ==="
  /usr/local/bin/junocash-cli getblockchaininfo | head -10
  echo "=== XMRig hashrate ==="
  curl -s http://127.0.0.1:8888/1/summary | python3 -c "import json,sys;d=json.load(sys.stdin);print(d[\"hashrate\"])"
'
```

## "Cek VPS terbaru" workflow

When user says "cek vps terbaru" or similar:

1. **Read** `~/.hermes/credentials/vps_inventory.json`
2. **Pick** the entry with most recent `status: UP` (or whatever user said)
3. **Connect** via sshpass (password) or `ssh <ssh_alias>` (key-based)
4. **Probe** connectivity first (`ping -c 3 -W 5`); if down, mark `status: "DOWN"` in inventory
5. **Report** uptime, load, disk, RAM, active services, role-specific status
6. **Update** `vps_inventory.json` if status changed (UP ↔ DOWN)

## Status field maintenance

- Update `status: "UP" | "DOWN"` after every status check
- Add `note: "..."` for transient issues (CF block, sync in progress, etc.)
- If VPS goes DOWN, create a new entry as `vps_NAME2` with `role: "X (replace vps_NAME)"`
- Keep `ssh_alias` consistent with `~/.ssh/config` so `ssh vps-mining2` works directly

## SSH config integration (for key-based auth)

Add to `~/.ssh/config`:
```
Host vps-mining
  HostName 104.207.74.67
  User root
  IdentityFile ~/.ssh/vps_mining

Host vps-mining2
  HostName 104.207.75.223
  User root
  IdentityFile ~/.ssh/vps_mining2
  PasswordAuthentication no
```

This lets you use `ssh vps-mining2` directly without sshpass when key-based.

## Failure handling

| Symptom | Diagnosis | Action |
|---------|-----------|--------|
| Connection timed out | VPS down OR network block | `ping -c 3` to confirm, then mark DOWN |
| All ports filtered | Datacenter-level block (rare) | Mark DOWN, check provider dashboard |
| DNS NXDOMAIN | Hostname expired/migrated | Use IP directly or update DNS |
| sshpass password rejected | Password changed | Ask user for new password OR switch to key-based auth |
| Permission denied (publickey) | Key not in authorized_keys | Push key manually OR use password fallback |

## Example: full "cek vps" one-liner

```bash
# Status check all VPS in inventory
python3 -c "
import json, subprocess
inv = json.load(open('/home/ubuntu/.hermes/credentials/vps_inventory.json'))
for name, v in inv.items():
    cmd = ['ping', '-c', '1', '-W', '3', v['host']]
    r = subprocess.run(cmd, capture_output=True)
    state = 'UP' if r.returncode == 0 else 'DOWN'
    print(f'  {state:>4}  {name:<14}  {v[\"host\"]:<16}  {v.get(\"role\",\"\")}')
"
```

## Known VPS in current setup (as of 2026-06-13)

| Alias | Host | OS | Role | Status |
|-------|------|-----|------|--------|
| vps-utama | 18.143.107.30 | Ubuntu 24.04 | primary (Hermes + cron) | UP |
| vps-mining | 104.207.74.67 | Ubuntu 24.04.2 | mining-juno (LEGACY) | DOWN |
| vps-mining2 | 104.207.75.223 | AlmaLinux 9.8 | mining-juno (replacement) | UP |
