#!/usr/bin/env python3
"""
Multi-service VPS Health Monitor.
Checks systemd, PM2, and Docker services + system resources.
Usage: python3 health-monitor.py [--json] [--quiet]
"""

import subprocess, json, sys
from datetime import datetime, timezone, timedelta

WIB = timezone(timedelta(hours=7))

SERVICES = {
    "nginx":         {"type": "systemd", "check_cmd": "systemctl is-active nginx", "health_url": "http://localhost/health"},
    "freellmapi":    {"type": "systemd", "check_cmd": "systemctl is-active freellmapi", "health_url": "http://localhost:3001/v1/models"},
    "opencode-proxy":{"type": "pm2", "pm2_name": "opencode-free-proxy", "health_url": "http://localhost:19912/health"},
    "haus-api":      {"type": "pm2", "pm2_name": "haus-api", "health_url": "http://localhost:8000/webhook/health"},
    "n8n":           {"type": "docker", "container": "n8n", "health_url": "http://localhost:5678/healthz"},
}

WARN_DISK_PCT, CRIT_DISK_PCT = 80, 90
WARN_RAM_PCT, CRIT_RAM_PCT = 80, 90
WARN_LOAD, CRIT_LOAD = 2.0, 4.0

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1

def check_service(name, cfg):
    result = {"name": name, "status": "unknown", "health": None, "type": cfg["type"]}
    if cfg["type"] == "systemd":
        out, _ = run(cfg["check_cmd"])
        result["status"] = "running" if out == "active" else "stopped"
    elif cfg["type"] == "pm2":
        out, _ = run(f"pm2 show {cfg.get('pm2_name', name)} 2>/dev/null | grep status")
        result["status"] = "running" if "online" in out else "stopped"
    elif cfg["type"] == "docker":
        out, _ = run(f"sudo docker inspect -f '{{{{.State.Status}}}}' {cfg.get('container', name)} 2>/dev/null")
        result["status"] = "running" if out == "running" else "stopped"
    if result["status"] == "running" and "health_url" in cfg:
        out, _ = run(f"curl -sf -m 5 -o /dev/null -w '%{{http_code}}' {cfg['health_url']}")
        result["health"] = "ok" if out == "200" else f"http_{out}"
    return result

def get_stats():
    stats = {}
    out, _ = run("df -h / | tail -1 | awk '{print $2,$3,$4,$5}'")
    parts = out.split()
    if len(parts) >= 4:
        stats["disk"] = {"total": parts[0], "used": parts[1], "avail": parts[2], "pct": int(parts[3].replace('%',''))}
    out, _ = run("free -m | grep Mem | awk '{print $2,$3,$4}'")
    parts = out.split()
    if len(parts) >= 3:
        t, u = int(parts[0]), int(parts[1])
        stats["ram"] = {"total_mb": t, "used_mb": u, "free_mb": int(parts[2]), "pct": round(u/t*100) if t else 0}
    out, _ = run("cat /proc/loadavg | awk '{print $1,$2,$3}'")
    parts = out.split()
    if len(parts) >= 3:
        stats["load"] = {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])}
    out, _ = run("uptime -p 2>/dev/null || uptime | sed 's/.*up //' | sed 's/,.*//'")
    stats["uptime"] = out
    return stats

def assess_alerts(services, stats):
    alerts = []
    for svc in services:
        if svc["status"] != "running":
            alerts.append(("CRIT", f"Service DOWN: {svc['name']}"))
        elif svc.get("health") and svc["health"] != "ok":
            alerts.append(("WARN", f"Unhealthy: {svc['name']} ({svc['health']})"))
    if "disk" in stats and stats["disk"]["pct"] >= CRIT_DISK_PCT:
        alerts.append(("CRIT", f"Disk {stats['disk']['pct']}%"))
    elif "disk" in stats and stats["disk"]["pct"] >= WARN_DISK_PCT:
        alerts.append(("WARN", f"Disk {stats['disk']['pct']}%"))
    if "ram" in stats and stats["ram"]["pct"] >= CRIT_RAM_PCT:
        alerts.append(("CRIT", f"RAM {stats['ram']['pct']}%"))
    elif "ram" in stats and stats["ram"]["pct"] >= WARN_RAM_PCT:
        alerts.append(("WARN", f"RAM {stats['ram']['pct']}%"))
    if "load" in stats and stats["load"]["1m"] >= CRIT_LOAD:
        alerts.append(("CRIT", f"Load {stats['load']['1m']:.2f}"))
    elif "load" in stats and stats["load"]["1m"] >= WARN_LOAD:
        alerts.append(("WARN", f"Load {stats['load']['1m']:.2f}"))
    return alerts

def main():
    fmt = "json" if "--json" in sys.argv else "text"
    services = [check_service(n, c) for n, c in SERVICES.items()]
    stats = get_stats()
    alerts = assess_alerts(services, stats)
    now = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")

    if fmt == "json":
        print(json.dumps({"timestamp": now, "services": services, "system": stats, "alerts": alerts}, indent=2))
    else:
        print(f"🏠 Health Report | {now}")
        for svc in services:
            icon = "✅" if svc["status"]=="running" and svc.get("health")=="ok" else "❌" if svc["status"]!="running" else "⚠️"
            print(f"  {icon} {svc['name']:<20} {svc['status']}")
        if "disk" in stats: print(f"  🟢 Disk: {stats['disk']['pct']}%")
        if "ram" in stats: print(f"  🟢 RAM:  {stats['ram']['pct']}%")
        if "load" in stats: print(f"  🟢 Load: {stats['load']['1m']:.2f}")
        if alerts:
            for lvl, msg in alerts: print(f"  {'🔴' if lvl=='CRIT' else '🟡'} [{lvl}] {msg}")
        else:
            print("  ✅ All healthy")
    sys.exit(1 if any(a[0]=="CRIT" for a in alerts) else 0)

if __name__ == "__main__":
    main()
