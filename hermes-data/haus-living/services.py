#!/usr/bin/env python3
"""
Haus Living — Service Manager
Start, stop, and monitor all services.

Usage:
  python3 services.py start    — Start all services
  python3 services.py stop     — Stop all services
  python3 services.py status   — Show status of all services
  python3 services.py health   — Health check all endpoints
  python3 services.py logs     — Tail all service logs
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

COLORS = {
    "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
    "blue": "\033[94m", "bold": "\033[1m", "end": "\033[0m",
}

def c(text, color):
    return f"{COLORS.get(color, '')}{text}{COLORS['end']}"

def run(cmd, silent=False):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        if not silent:
            print(f"  ❌ Error: {e}")
        return "", 1

def get_systemd_status(service):
    out, code = run(f"systemctl is-active {service}", silent=True)
    return out if code == 0 else "inactive"

def get_pm2_status(app):
    out, _ = run(f"pm2 jlist", silent=True)
    try:
        procs = json.loads(out)
        for p in procs:
            if p.get("name") == app:
                return "online" if p.get("pm2_env", {}).get("status") == "online" else "stopped"
    except Exception:
        pass
    return "not found"

def get_docker_status(container):
    out, _ = run(f"sudo docker inspect -f '{{{{.State.Status}}}}' {container}", silent=True)
    return out if out else "not found"

def get_port_status(port):
    out, _ = run(f"ss -tlnp 2>/dev/null | grep ':{port}'", silent=True)
    return "listening" if out else "not listening"

def check_url(url):
    out, code = run(f"curl -s -o /dev/null -w '%{{http_code}}' {url}", silent=True)
    try:
        return int(out)
    except Exception:
        return 0


SERVICES = [
    # (name, type, identifier, port, health_url)
    ("Nginx",         "systemd",  "nginx",               80,   "http://localhost/health"),
    ("FreeLLMAPI",    "systemd",  "freellmapi",          3001, "http://localhost:3001/v1/models"),
    ("OpenCode Proxy","pm2",      "opencode-free-proxy", 19912, None),
    ("n8n",           "docker",   "n8n",                 5678, "http://localhost:5678/healthz"),
    ("Haus API",      "port",     "haus-api",            8000, "http://localhost:8000/webhook/health"),
    ("Hermes Gateway","pid",      "hermes",              0,    None),
    ("Telegram Bot",  "env",      "TG_BOT_PID",          0,    None),
    ("Discord Bot",   "env",      "DC_BOT_PID",          0,    None),
]


def cmd_status():
    print(c("\n🏠 Haus Living — Service Status\n", "bold"))
    print(f"{'Service':<20} {'Type':<10} {'Status':<15} {'Port':<8} {'Health'}")
    print("-" * 70)

    for name, stype, sid, port, health in SERVICES:
        if stype == "systemd":
            status = get_systemd_status(sid)
        elif stype == "pm2":
            status = get_pm2_status(sid)
        elif stype == "docker":
            status = get_docker_status(sid)
        elif stype == "port":
            status = get_port_status(port) if port else "unknown"
        elif stype == "pid":
            out, _ = run(f"pgrep -f {sid}", silent=True)
            status = "running" if out else "stopped"
        elif stype == "env":
            status = "not started"
        else:
            status = "unknown"

        # Colorize status
        if status in ("active", "online", "running", "listening"):
            status_str = c(f"● {status}", "green")
        elif status in ("inactive", "stopped", "not found", "not listening", "not started"):
            status_str = c(f"● {status}", "red")
        else:
            status_str = c(f"● {status}", "yellow")

        # Port
        port_str = str(port) if port else "-"

        # Health check
        health_str = ""
        if health:
            code = check_url(health)
            if code == 200:
                health_str = c(f"✅ {code}", "green")
            elif code > 0:
                health_str = c(f"⚠️ {code}", "yellow")
            else:
                health_str = c("❌ down", "red")

        print(f"{name:<20} {stype:<10} {status_str:<25} {port_str:<8} {health_str}")

    print()


def cmd_start():
    print(c("\n🚀 Starting all Haus Living services...\n", "bold"))

    steps = [
        ("Nginx",            "sudo systemctl start nginx"),
        ("FreeLLMAPI",       "sudo systemctl start freellmapi"),
        ("OpenCode Proxy",   "pm2 start opencode-free-proxy 2>/dev/null || pm2 resurrect 2>/dev/null"),
        ("n8n (Docker)",     "sudo docker start n8n 2>/dev/null || echo 'n8n already running or not created'"),
        ("Haus API",         f"cd {os.path.expanduser('~/.hermes/haus-living/api')} && nohup python3 webhook-server.py > /tmp/haus-api.log 2>&1 & echo $!"),
    ]

    for name, cmd in steps:
        print(f"  Starting {name}...", end=" ")
        out, code = run(cmd)
        if code == 0:
            print(c("✅", "green"))
        else:
            print(c(f"❌ ({code})", "red"))

    print(c("\n✅ All services started! Run 'status' to verify.", "green"))


def cmd_stop():
    print(c("\n🛑 Stopping all Haus Living services...\n", "bold"))

    steps = [
        ("Haus API",         "pkill -f 'webhook-server.py' 2>/dev/null; echo done"),
        ("n8n (Docker)",     "sudo docker stop n8n 2>/dev/null || echo 'not running'"),
        ("OpenCode Proxy",   "pm2 stop opencode-free-proxy 2>/dev/null || echo 'not running'"),
        ("FreeLLMAPI",       "sudo systemctl stop freellmapi"),
        ("Nginx",            "sudo systemctl stop nginx"),
    ]

    for name, cmd in steps:
        print(f"  Stopping {name}...", end=" ")
        _, code = run(cmd)
        print(c("✅", "green") if code == 0 else c("⚠️", "yellow"))

    print(c("\n✅ All services stopped.", "green"))


def cmd_health():
    print(c("\n🏥 Haus Living — Health Check\n", "bold"))

    endpoints = [
        ("Nginx",           "http://localhost/"),
        ("Haus API",        "http://localhost:8000/webhook/health"),
        ("FreeLLMAPI",      "http://localhost:3001/v1/models"),
        ("n8n",             "http://localhost:5678/healthz"),
        ("OpenCode Proxy",  "http://localhost:19912/v1/models"),
    ]

    all_healthy = True
    for name, url in endpoints:
        code = check_url(url)
        if code == 200:
            print(f"  {name:<20} {c('✅ HEALTHY', 'green')}  ({code})")
        elif code > 0:
            print(f"  {name:<20} {c('⚠️ DEGRADED', 'yellow')}  ({code})")
            all_healthy = False
        else:
            print(f"  {name:<20} {c('❌ DOWN', 'red')}")
            all_healthy = False

    print()
    if all_healthy:
        print(c("✅ All services healthy!", "green"))
    else:
        print(c("⚠️ Some services need attention", "yellow"))


def cmd_logs():
    print(c("\n📋 Haus Living — Recent Logs\n", "bold"))
    for name, cmd in [
        ("Nginx access", "sudo tail -5 /var/log/nginx/access.log 2>/dev/null"),
        ("Nginx error",  "sudo tail -5 /var/log/nginx/error.log 2>/dev/null"),
        ("n8n",          "sudo docker logs --tail 5 n8n 2>&1"),
        ("Haus API",     "tail -5 /tmp/haus-api.log 2>/dev/null || echo 'no log'"),
    ]:
        print(f"\n  {c(name, 'blue')}:")
        out, _ = run(cmd)
        for line in out.split("\n")[:5]:
            print(f"    {line}")


def main():
    parser = argparse.ArgumentParser(description="Haus Living Service Manager")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start",  help="Start all services")
    sub.add_parser("stop",   help="Stop all services")
    sub.add_parser("status", help="Show service status")
    sub.add_parser("health", help="Health check all endpoints")
    sub.add_parser("logs",   help="Show recent logs")

    args = parser.parse_args()
    cmds = {
        "start": cmd_start, "stop": cmd_stop, "status": cmd_status,
        "health": cmd_health, "logs": cmd_logs,
    }
    if args.command in cmds:
        cmds[args.command]()
    else:
        cmd_status()

if __name__ == "__main__":
    main()
