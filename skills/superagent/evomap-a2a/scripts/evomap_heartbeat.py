#!/usr/bin/env python3
"""
EvoMap A2A heartbeat loop — keeps node online between sessions.
Run as background process or cron job.

Usage:
  python3 evomap_heartbeat.py              # Single heartbeat
  python3 evomap_heartbeat.py --loop       # Continuous loop (5 min interval)
  python3 evomap_heartbeat.py --count 12   # 12 heartbeats then exit
"""
import json, subprocess, os, time, argparse

SECRET_PATH = os.path.expanduser("~/.evomap/node_secret")
NODE_ID_PATH = os.path.expanduser("~/.evomap/node_id")

def load_creds():
    secret = open(SECRET_PATH).read().strip()
    node_id = open(NODE_ID_PATH).read().strip()
    return node_id, secret

def heartbeat(node_id, secret):
    """Send single heartbeat, return parsed response."""
    result = subprocess.run(
        ["torsocks", "curl", "-s", "-m", "15", "-X", "POST",
         "https://evomap.ai/a2a/heartbeat",
         "-H", "Authorization: Bearer *** + secret,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"node_id": node_id})],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except:
            return {"error": "parse_error"}
    return {"error": "request_failed"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Continuous loop")
    parser.add_argument("--count", type=int, default=1, help="Number of heartbeats")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between beats")
    args = parser.parse_args()

    node_id, secret = load_creds()
    
    for i in range(args.count):
        r = heartbeat(node_id, secret)
        ts = time.strftime("%H:%M:%S")
        status = r.get("node_status", r.get("status", "?"))
        claimed = r.get("claimed", "?")
        credits = r.get("credit_balance", "?")
        events = len(r.get("pending_events", []))
        work = len(r.get("available_work", []))
        
        print(f"[{ts}] status={status} claimed={claimed} credits={credits} events={events} work={work}")
        
        if r.get("claim_url"):
            print(f"  claim_url: {r['claim_url']}")
        
        if not args.loop and i >= args.count - 1:
            break
            
        if args.loop or i < args.count - 1:
            interval = r.get("next_heartbeat_ms", args.interval * 1000) / 1000
            time.sleep(interval)
