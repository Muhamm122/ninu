#!/usr/bin/env python3
"""
Check junocashd sync status on a remote VPS.

Usage:
    python3 check_juno_sync.py <host> <user> [key_path] [--port 22]

Examples:
    python3 check_juno_sync.py 104.207.75.223 root ~/.ssh/vps_mining2
    python3 check_juno_sync.py vps-mining2 root  # uses default key

Returns a concise status report suitable for Telegram/chat.
"""
import argparse
import json
import os
import sys

import paramiko

DEFAULT_KEY = os.path.expanduser("~/.ssh/vps_mining2")
DEFAULT_USER = "root"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("host")
    p.add_argument("user", default=DEFAULT_USER, nargs="?")
    p.add_argument("key", default=DEFAULT_KEY, nargs="?")
    p.add_argument("--port", type=int, default=22)
    args = p.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, port=args.port, username=args.user,
                key_filename=args.key, timeout=20)

    # Blockchain
    stdin, stdout, _ = ssh.exec_command(
        "junocash-cli -datadir=/root/.junocash "
        "-conf=/root/.junocash/junocashd.conf getblockchaininfo 2>&1"
    )
    out = stdout.read().decode()
    try:
        info = json.loads(out)
        blocks = info["blocks"]
        headers = info["headers"]
        progress = info["verificationprogress"] * 100
        ibd = info["initial_block_download_complete"]
        best = info["bestblockhash"][:24]
        size = info["size_on_disk"]
        diff = info["difficulty"]
    except Exception as e:
        print(f"Blockchain info parse failed: {e}\n{out}")
        ssh.close()
        sys.exit(1)

    # Peers
    stdin, stdout, _ = ssh.exec_command(
        "junocash-cli -datadir=/root/.junocash "
        "-conf=/root/.junocash/junocashd.conf getconnectioncount 2>&1"
    )
    peers = stdout.read().decode().strip()

    # Mining (check process args for -gen flag)
    stdin, stdout, _ = ssh.exec_command(
        "ps aux | grep junocashd | grep -v grep | head -1"
    )
    ps_line = stdout.read().decode().strip()
    has_gen = " -gen" in ps_line or "gen=1" in ps_line

    # Network hashrate
    stdin, stdout, _ = ssh.exec_command(
        "junocash-cli -datadir=/root/.junocash "
        "-conf=/root/.junocash/junocashd.conf getnetworkhashps 2>&1"
    )
    net_hash = stdout.read().decode().strip()

    # Datadir size
    stdin, stdout, _ = ssh.exec_command(
        "du -sh /root/.junocash 2>&1 | awk '{print $1}'"
    )
    datadir_size = stdout.read().decode().strip()

    # Balance
    stdin, stdout, _ = ssh.exec_command(
        "junocash-cli -datadir=/root/.junocash "
        "-conf=/root/.junocash/junocashd.conf getbalance 2>&1"
    )
    bal = stdout.read().decode().strip()

    print(f"=== {args.user}@{args.host} ===")
    print(f"  Sync:        {blocks:,} / {headers:,} blocks "
          f"({progress:.4f}%)  IBD={ibd}")
    print(f"  Best block:  {best}...")
    print(f"  Peers:       {peers}")
    print(f"  Datadir:     {datadir_size} (chain: {size:,} bytes)")
    print(f"  Difficulty:  {diff}")
    print(f"  Mining:      {'ON' if has_gen else 'OFF'}  "
          f"(network: {net_hash} H/s)")
    print(f"  Balance:     {bal} JOC")
    ssh.close()


if __name__ == "__main__":
    main()
