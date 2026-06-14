# VPS Decommission / Clean Removal

Companion to `vps-add-provisioning.md`. When user says "hapus VPS X dari sistem" or "buang VPS X", the goal is to make the VPS completely invisible to all automation — without losing the artifacts that might be useful later (configs, scripts, last-known IP/creds for forensics).

## When To Use

- User says "hapus VPS X dari sistem", "buang VPS X", "remove VPS X", "matikan VPS X", "jangan pake VPS X lagi"
- VPS is permanently DOWN and user wants to cut all ties
- Switching to a replacement VPS (e.g., vps-mining → vps-mining2) and old one should be archived

## Decommission Workflow (5-step, idempotent)

### Step 1 — SSH known_hosts cleanup

```bash
# Remove the old host key so any future SSH attempt triggers fresh prompt
# (or fails safely if VPS is truly gone)
ssh-keygen -f ~/.ssh/known_hosts -R "<IP>" 2>&1
ssh-keygen -f ~/.ssh/known_hosts -R "<hostname-if-any>" 2>&1
```

**Why not just `rm` the file**: known_hosts may contain entries for other still-active hosts. Only remove the entry for the dead VPS.

### Step 2 — Disable (don't delete) monitor scripts

```bash
# Backup the script before disabling (so you can reference it later)
cp ~/.hermes/scripts/<vps>_monitor.py /tmp/<vps>_monitor.py.bak
cp ~/.hermes/scripts/<vps>_watchdog.py /tmp/<vps>_watchdog.py.bak

# Rename to .disabled so it's no longer picked up by tab-completion or scripts
mv ~/.hermes/scripts/<vps>_monitor.py ~/.hermes/scripts/<vps>_monitor.py.disabled
mv ~/.hermes/scripts/<vps>_watchdog.py ~/.hermes/scripts/<vps>_watchdog.py.disabled
```

**Why rename not delete**: The script may contain useful patterns (paramiko, RPC calls, Telegram alerts) that the next VPS deployment can copy from. Keep the source, just don't execute it.

### Step 3 — Remove cron entries

```bash
# Backup current crontab first
crontab -l > /tmp/cron_backup_<date>.txt

# Remove only the entries for the dead VPS
crontab -l | grep -v "<vps-name>\|<old-ip>\|<old-script-name>" | crontab -

# Verify
crontab -l
```

**Pitfall**: `crontab -r` removes ALL entries. Always pipe through `grep -v` to keep the rest.

### Step 4 — Update inventory (or remove from it)

```bash
# For a single permanent removal (VPS truly gone):
python3 -c "
import json, os
inv_path = os.path.expanduser('~/.hermes/credentials/vps_inventory.json')
with open(inv_path) as f:
    inv = json.load(f)
if '<old-alias>' in inv:
    del inv['<old-alias>']
with open(inv_path, 'w') as f:
    json.dump(inv, f, indent=2)
"

# For a replacement (vps-mining → vps-mining2):
# Keep the old entry but mark status: "DOWN" + note replacement
# Add new entry for the replacement (see vps-add-provisioning.md)
```

### Step 5 — Mark the password as do-not-use in memory

Add to `MEMORY.md`:

```
<VPS>: REMOVED <date>. SSH known_hosts cleaned, scripts .disabled, cron removed.
Password <password> MUST NOT be reused.
```

**Why not just delete the password from inventory**: The password might have been used in other places (env files, log entries, conversation history). Marking it as "do not reuse" in memory makes the constraint survive even if other copies exist.

## What NOT To Do

- **Don't `rm` monitor scripts** — patterns are reusable
- **Don't `crontab -r`** — nukes all other jobs
- **Don't edit `~/.ssh/known_hosts` by hand** — `ssh-keygen -R` is the only safe way
- **Don't `systemctl stop` anything on the dead VPS** — you can't reach it anyway, and the local systemd is for the AGENT not the target
- **Don't delete the inventory entry without backup** — the `host`, `os`, `role` fields are useful for "what VPS did we have?" queries

## Idempotency

Each step is safe to run twice. If user asks again later, you can re-run the full workflow without breaking anything (renaming `.disabled` to `.disabled.disabled` is fine; the second `ssh-keygen -R` is a no-op).

## Forensic Trail

After running the workflow, these artifacts remain for forensics:
- `/tmp/<vps>_monitor.py.bak` — last working version of the monitoring script
- `/tmp/cron_backup_<date>.txt` — crontab as it was just before removal
- Memory entry with date + password marking
- `~/.hermes/credentials/vps_inventory.json` (if "keep but mark DOWN" path was used)

## Real Example (CUPANG session 2026-06-13)

User said: *"Vps 104.207.74.67 lu hapus aja dari sistem"*

Actions taken:
1. `ssh-keygen -f ~/.ssh/known_hosts -R "104.207.74.67"` — removed host key
2. `mv juno_pool_monitor.py → .disabled` and `mv juno_wallet_monitor.py → .disabled` (backups at `/tmp/juno_*.bak`)
3. `crontab -l | grep -v "juno_wallet_monitor" | crontab -` — removed the 30-min monitoring cron
4. Inventory was on the other agent-side machine — no edit needed there
5. Memory updated: "VPS 104.207.74.67 DIHAPUS dari sistem. Password 8c36ppRnL2OAqd9B5M tidak boleh dipakai lagi."

The replacements (vps-mining2 at 104.207.75.223) were tracked separately — see `references/multi-vps-inventory.md`.

## Quick Reference (copy-paste runbook)

```bash
# Inputs: VPS_IP, VPS_ALIAS, PASSWORD
VPS_IP="104.207.74.67"
VPS_ALIAS="vps-mining"

# 1. SSH key
ssh-keygen -f ~/.ssh/known_hosts -R "$VPS_IP" 2>&1

# 2. Disable monitor scripts (keep backups)
for s in ~/.hermes/scripts/${VPS_ALIAS}*.py; do
    [ -f "$s" ] || continue
    cp "$s" /tmp/$(basename $s).bak
    mv "$s" "$s.disabled"
done

# 3. Remove cron entries
crontab -l > /tmp/cron_backup_$(date +%Y%m%d).txt
crontab -l | grep -v "$VPS_ALIAS\|$VPS_IP" | crontab -

# 4. Memory update (manual — needs date + password note)
echo "REMINDER: Update MEMORY.md with VPS=$VPS_IP removal and password do-not-reuse"
```
