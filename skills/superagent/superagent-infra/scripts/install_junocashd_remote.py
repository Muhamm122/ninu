#!/usr/bin/env python3
"""
Install junocashd v0.9.12 on a remote Linux VPS (Ubuntu or AlmaLinux/RHEL).

Usage:
    python3 install_junocashd_remote.py <host> <user> <password> [--port 22]
    VPS_PASS=<password> python3 install_junocashd_remote.py <host> <user>

Behavior:
    1. Detect OS family (apt vs dnf) and install build deps
    2. Download junocash-0.9.12-linux64.tar.gz from official GitHub release
    3. Verify SHA256 against published sums
    4. Install binaries to /usr/local/bin
    5. Create /root/.junocash/ with config (no mining yet — sync first)
    6. Upload systemd unit + enable
    7. Start daemon (paramiko-safe pattern — see notes)
    8. Report sync status

Re-runnable: safe to re-invoke; stops existing daemon and restarts.

Pitfall encoded: paramiko's exec_command waits for stdout/stderr FDs to
close. `junocashd -daemon` forks and the child keeps the FDs open → call
hangs for the full timeout. Solution: wrap launch in `nohup ... & disown`
with explicit FD redirection, return immediately, verify with separate
`ps`/`ss` calls.
"""
import argparse
import json
import os
import secrets
import sys
import time

import paramiko

JUNO_VERSION = "0.9.12"
RELEASE_URL = (
    f"https://github.com/juno-cash/junocash/releases/download/"
    f"v{JUNO_VERSION}/junocash-{JUNO_VERSION}-linux64.tar.gz"
)
SHA_URL = (
    f"https://github.com/juno-cash/junocash/releases/download/"
    f"v{JUNO_VERSION}/SHA256SUMS"
)

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_FILE = os.path.join(SKILL_DIR, "..", "templates", "junocashd.service")
CONFIG_TEMPLATE = os.path.join(SKILL_DIR, "..", "templates", "junocashd.conf")


def run(ssh, cmd, timeout=120, label=None):
    if label:
        print(f"\n=== {label} ===")
    print(f">>> {cmd[:200]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip():
        print(out)
    if err.strip():
        print("STDERR:", err)
    return out, err


def main():
    p = argparse.ArgumentParser()
    p.add_argument("host")
    p.add_argument("user", default="root", nargs="?")
    p.add_argument("password", nargs="?", default=os.environ.get("VPS_PASS", ""))
    p.add_argument("--port", type=int, default=22)
    p.add_argument("--key", default=None, help="Use key-based auth instead of password")
    args = p.parse_args()

    if not args.password and not args.key:
        print("Need password (argv/VPS_PASS) or --key path")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if args.key:
        ssh.connect(args.host, port=args.port, username=args.user,
                    key_filename=os.path.expanduser(args.key), timeout=20)
    else:
        ssh.connect(args.host, port=args.port, username=args.user,
                    password=args.password, timeout=20)
    print(f"=== CONNECTED to {args.user}@{args.host} ===")

    # Step 1: Detect OS
    stdin, stdout, _ = ssh.exec_command(
        "cat /etc/os-release | grep -E '^(ID|NAME|VERSION_ID)=' | tr '\\n' ' '"
    )
    os_info = stdout.read().decode().strip()
    print(f"OS: {os_info}")
    is_rhel = any(x in os_info.lower()
                  for x in ["almalinux", "rhel", "centos", "rocky", "fedora"])
    pkg_mgr = "dnf" if is_rhel else "apt"
    print(f"Package manager: {pkg_mgr}")

    # Step 2: Install build deps
    if is_rhel:
        run(ssh, "dnf install -y openssl-devel libcurl-devel boost-devel "
                 "wget tar 2>&1 | tail -3",
            timeout=300, label="Install RHEL deps")
    else:
        run(ssh, "apt-get update -qq && apt-get install -y wget tar "
                 "libssl-dev libcurl4-openssl-dev 2>&1 | tail -3",
            timeout=300, label="Install Debian deps")

    # Step 3: Download + verify
    run(ssh, f"cd /tmp && wget -q {RELEASE_URL} && "
             f"ls -la junocash-{JUNO_VERSION}-linux64.tar.gz",
        timeout=180, label="Download tarball")
    run(ssh, f"cd /tmp && wget -q {SHA_URL} && "
             f"sha256sum -c --ignore-missing SHA256SUMS 2>&1 | tail -3",
        timeout=30, label="Verify SHA256")

    # Step 4: Extract + install
    run(ssh, f"cd /tmp && tar -xzf junocash-{JUNO_VERSION}-linux64.tar.gz && "
             f"ls junocash-{JUNO_VERSION}/bin/",
        timeout=30, label="Extract")
    run(ssh,
        f"install -m 755 /tmp/junocash-{JUNO_VERSION}/bin/junocashd "
        f"/usr/local/bin/junocashd && "
        f"install -m 755 /tmp/junocash-{JUNO_VERSION}/bin/junocash-cli "
        f"/usr/local/bin/junocash-cli && "
        f"which junocashd && junocashd --version | head -3",
        timeout=15, label="Install binaries")
    run(ssh, f"rm -rf /tmp/junocash-{JUNO_VERSION}* /tmp/SHA256SUMS")

    # Step 5: Datadir + config
    run(ssh, "mkdir -p /root/.junocash && chmod 700 /root/.junocash",
        label="Create datadir")

    rpc_pass = secrets.token_urlsafe(24)
    if os.path.exists(CONFIG_TEMPLATE):
        with open(CONFIG_TEMPLATE) as f:
            config = f.read()
        config = config.replace("CHANGE_ME_TO_LONG_RANDOM_STRING", rpc_pass)
    else:
        config = f"""rpcuser=junorpc
rpcpassword={rpc_pass}
rpcallowip=127.0.0.1
rpcport=8232
listen=1
server=1
daemon=1
txindex=1
dbcache=512
addnode=dnsseed.junocash.com
addnode=seed.junocash.com
addnode=mainnet.junocash.tools
"""

    sftp = ssh.open_sftp()
    with sftp.open("/root/.junocash/junocashd.conf", "w") as f:
        f.write(config)
    sftp.chmod("/root/.junocash/junocashd.conf", 0o600)
    sftp.close()
    print(f"=== CONFIG WRITTEN === (RPC password prefix: {rpc_pass[:8]}...)")

    # Step 6: Upload systemd service
    if os.path.exists(SERVICE_FILE):
        with open(SERVICE_FILE) as f:
            svc = f.read()
        sftp = ssh.open_sftp()
        with sftp.open("/etc/systemd/system/junocashd.service", "w") as f:
            f.write(svc)
        sftp.chmod("/etc/systemd/system/junocashd.service", 0o644)
        sftp.close()
        print("=== SYSTEMD UNIT UPLOADED ===")
        run(ssh, "systemctl daemon-reload && systemctl enable junocashd.service",
            label="Enable service")

    # Step 7: Start daemon
    # CRITICAL: paramiko exec_command waits for channel close.
    # `junocashd -daemon` forks and the daemonized child keeps FDs open,
    # so a bare exec_command hangs for the full timeout.
    # Workaround: launch via nohup with full FD redirection and disown,
    # then verify with separate ps/ss calls.
    print("\n=== STARTING DAEMON ===")
    ssh.exec_command(
        "pkill -f junocashd 2>/dev/null; sleep 2; rm -f /root/.junocash/.lock; "
        "nohup /usr/local/bin/junocashd -datadir=/root/.junocash "
        "-conf=/root/.junocash/junocashd.conf -daemon "
        "> /var/log/junocashd-startup.log 2>&1 < /dev/null & disown",
        timeout=5
    )
    time.sleep(10)  # let daemon initialize and bind ports

    # Step 8: Verify
    print("\n=== POST-INSTALL VERIFY ===")
    run(ssh, "ps aux | grep junocashd | grep -v grep | "
             "awk '{print $2,$3,$11,$12,$13,$14,$15}'",
        label="Process")
    run(ssh, "ss -tlnp | grep -E ':(8232|8234)'", label="Ports")
    run(ssh, "junocash-cli -datadir=/root/.junocash "
             "-conf=/root/.junocash/junocashd.conf getconnectioncount 2>&1",
        label="Peers")

    stdin, stdout, _ = ssh.exec_command(
        "junocash-cli -datadir=/root/.junocash "
        "-conf=/root/.junocash/junocashd.conf getblockchaininfo 2>/dev/null"
    )
    try:
        info = json.loads(stdout.read().decode())
        print(f"\n=== SYNC STATUS ===")
        print(f"  Blocks:        {info['blocks']:,}")
        print(f"  Headers:       {info['headers']:,}")
        print(f"  Progress:      {info['verificationprogress']*100:.4f}%")
        print(f"  IBD complete:  {info['initial_block_download_complete']}")
    except Exception as e:
        print(f"Status check failed: {e}")
        print("Daemon may still be starting — check again in 30s")

    print("\n=== DONE ===")
    print("Next: wait for IBD complete, then enable mining:")
    print("  junocash-cli -datadir=/root/.junocash t_getminingaddress")
    print("  Edit /root/.junocash/junocashd.conf → uncomment gen=1, genproclimit=12, miningaddr=<addr>")
    print("  systemctl restart junocashd")
    ssh.close()


if __name__ == "__main__":
    main()
