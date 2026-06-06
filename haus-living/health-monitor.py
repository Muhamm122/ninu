#!/usr/bin/env python3
"""
Haus Living — Server Health Monitor
Checks all services, disk, RAM, CPU, and reports status.
Run standalone or via cron for automated alerts.
"""

import subprocess
import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))

# Service definitions
SERVICES = {
    "nginx": {"type": "systemd", "check_cmd": "systemctl is-active nginx", "health_url": "http://localhost/health"},
    "freellmapi": {"type": "systemd", "check_cmd": "systemctl is-active freellmapi", "health_url": "http://localhost:3001/v1/models"},
    "opencode-proxy": {"type": "pm2", "pm2_name": "opencode-free-proxy", "health_url": "http://localhost:19912/health"},
    "haus-api": {"type": "pm2", "pm2_name": "haus-api", "health_url": "http://localhost:8000/webhook/health"},
    "n8n": {"type": "docker", "container": "n8n", "health_url": "http://localhost:5678/healthz"},
}

# Thresholds
WARN_DISK_PCT = 80
CRIT_DISK_PCT = 90
WARN_RAM_PCT = 80
CRIT_RAM_PCT = 90
WARN_LOAD = 2.0
CRIT_LOAD = 4.0


def run(cmd):
    """Run shell command and return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def check_service(name, cfg):
    """Check a single service health."""
    result = {"name": name, "status": "unknown", "health": None, "type": cfg["type"]}

    # Process check
    if cfg["type"] == "systemd":
        out, rc = run(cfg["check_cmd"])
        result["status"] = "running" if out == "active" else "stopped"
    elif cfg["type"] == "pm2":
        out, rc = run(f"pm2 show {cfg.get('pm2_name', name)} 2>/dev/null | grep status")
        result["status"] = "running" if "online" in out else "stopped"
    elif cfg["type"] == "docker":
        out, rc = run(f"sudo docker inspect -f '{{{{.State.Status}}}}' {cfg.get('container', name)} 2>/dev/null")
        result["status"] = "running" if out == "running" else "stopped"

    # Health check (HTTP)
    if result["status"] == "running" and "health_url" in cfg:
        try:
            out, rc = run(f"curl -sf -m 5 -o /dev/null -w '%{{http_code}}' {cfg['health_url']}")
            result["health"] = "ok" if out == "200" else f"http_{out}"
        except:
            result["health"] = "error"

    return result


def get_system_stats():
    """Get disk, RAM, CPU stats."""
    stats = {}

    # Disk
    out, _ = run("df -h / | tail -1 | awk '{print $2,$3,$4,$5}'")
    parts = out.split()
    if len(parts) >= 4:
        stats["disk"] = {
            "total": parts[0], "used": parts[1], "avail": parts[2],
            "pct": int(parts[3].replace('%', ''))
        }

    # RAM
    out, _ = run("free -m | grep Mem | awk '{print $2,$3,$4,$5}'")
    parts = out.split()
    if len(parts) >= 4:
        total, used = int(parts[0]), int(parts[1])
        pct = round(used / total * 100) if total > 0 else 0
        stats["ram"] = {
            "total_mb": total, "used_mb": used, "free_mb": int(parts[2]),
            "pct": pct
        }

    # Load
    out, _ = run("cat /proc/loadavg | awk '{print $1,$2,$3}'")
    parts = out.split()
    if len(parts) >= 3:
        stats["load"] = {
            "1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])
        }

    # Uptime
    out, _ = run("uptime -p 2>/dev/null || uptime | sed 's/.*up //' | sed 's/,.*//'")
    stats["uptime"] = out

    # Swap
    out, _ = run("free -m | grep Swap | awk '{print $2,$3}'")
    parts = out.split()
    if len(parts) >= 2:
        stats["swap"] = {"total_mb": int(parts[0]), "used_mb": int(parts[1])}

    return stats


def get_docker_stats():
    """Get Docker container stats."""
    out, _ = run("sudo docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null")
    containers = []
    for line in out.strip().split('\n'):
        if line:
            parts = line.split('\t')
            containers.append({
                "name": parts[0] if len(parts) > 0 else "",
                "status": parts[1] if len(parts) > 1 else "",
                "ports": parts[2] if len(parts) > 2 else ""
            })
    return containers


def assess_alerts(services, stats):
    """Check for alerts."""
    alerts = []

    # Service alerts
    for svc in services:
        if svc["status"] != "running":
            alerts.append(("CRIT", f"Service DOWN: {svc['name']} ({svc['type']})"))
        elif svc.get("health") and svc["health"] != "ok":
            alerts.append(("WARN", f"Service UNHEALTHY: {svc['name']} (health={svc['health']})"))

    # Disk alerts
    if "disk" in stats:
        pct = stats["disk"]["pct"]
        if pct >= CRIT_DISK_PCT:
            alerts.append(("CRIT", f"Disk CRITICAL: {pct}% used"))
        elif pct >= WARN_DISK_PCT:
            alerts.append(("WARN", f"Disk warning: {pct}% used"))

    # RAM alerts
    if "ram" in stats:
        pct = stats["ram"]["pct"]
        if pct >= CRIT_RAM_PCT:
            alerts.append(("CRIT", f"RAM CRITICAL: {pct}% used"))
        elif pct >= WARN_RAM_PCT:
            alerts.append(("WARN", f"RAM warning: {pct}% used"))

    # Load alerts
    if "load" in stats:
        load1 = stats["load"]["1m"]
        if load1 >= CRIT_LOAD:
            alerts.append(("CRIT", f"Load CRITICAL: {load1:.2f}"))
        elif load1 >= WARN_LOAD:
            alerts.append(("WARN", f"Load warning: {load1:.2f}"))

    return alerts


def print_report(services, stats, docker, alerts, format="text"):
    """Print health report."""
    now = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")

    if format == "json":
        report = {
            "timestamp": now,
            "services": services,
            "system": stats,
            "docker": docker,
            "alerts": alerts,
            "summary": {
                "total_services": len(services),
                "healthy": sum(1 for s in services if s["status"] == "running" and s.get("health") == "ok"),
                "alerts_count": len(alerts)
            }
        }
        print(json.dumps(report, indent=2))
        return

    # Text format
    print(f"🏠 Haus Living — Server Health Report")
    print(f"📅 {now}")
    print("=" * 50)

    # Services
    print(f"\n📡 SERVICES")
    for svc in services:
        icon = "✅" if svc["status"] == "running" and svc.get("health") == "ok" else "❌" if svc["status"] != "running" else "⚠️"
        health_str = f" (health: {svc['health']})" if svc.get("health") else ""
        print(f"  {icon} {svc['name']:<20} {svc['status']:<10}{health_str}")

    # System
    print(f"\n💻 SYSTEM")
    if "disk" in stats:
        d = stats["disk"]
        icon = "🔴" if d["pct"] >= CRIT_DISK_PCT else "🟡" if d["pct"] >= WARN_DISK_PCT else "🟢"
        print(f"  {icon} Disk: {d['used']}/{d['total']} ({d['pct']}%) — avail: {d['avail']}")
    if "ram" in stats:
        r = stats["ram"]
        icon = "🔴" if r["pct"] >= CRIT_RAM_PCT else "🟡" if r["pct"] >= WARN_RAM_PCT else "🟢"
        print(f"  {icon} RAM:  {r['used_mb']}MB/{r['total_mb']}MB ({r['pct']}%)")
    if "swap" in stats:
        s = stats["swap"]
        print(f"  💾 Swap: {s['used_mb']}MB/{s['total_mb']}MB")
    if "load" in stats:
        l = stats["load"]
        icon = "🔴" if l["1m"] >= CRIT_LOAD else "🟡" if l["1m"] >= WARN_LOAD else "🟢"
        print(f"  {icon} Load: {l['1m']:.2f} / {l['5m']:.2f} / {l['15m']:.2f}")
    if "uptime" in stats:
        print(f"  ⏰ Uptime: {stats['uptime']}")

    # Docker
    if docker:
        print(f"\n🐳 DOCKER")
        for c in docker:
            print(f"  📦 {c['name']:<15} {c['status']}")

    # Alerts
    if alerts:
        print(f"\n🚨 ALERTS ({len(alerts)})")
        for level, msg in alerts:
            icon = "🔴" if level == "CRIT" else "🟡"
            print(f"  {icon} [{level}] {msg}")
    else:
        print(f"\n✅ No alerts — all systems healthy!")

    print(f"\n{'=' * 50}")


def main():
    fmt = "json" if "--json" in sys.argv else "text"
    quiet = "--quiet" in sys.argv

    # Collect data
    services = []
    for name, cfg in SERVICES.items():
        services.append(check_service(name, cfg))

    stats = get_system_stats()
    docker = get_docker_stats()
    alerts = assess_alerts(services, stats)

    # Output
    print_report(services, stats, docker, alerts, format=fmt)

    # Exit code for cron alerting
    crits = [a for a in alerts if a[0] == "CRIT"]
    if crits and not quiet:
        sys.exit(1)


if __name__ == "__main__":
    main()
