# Service Manager Script Template

Standalone Python CLI for managing all brand infrastructure services.
Copy to `~/.hermes/<brand>/services.py` and customize the SERVICES list.

## Usage
```bash
python3 services.py status   # Show all service status + health
python3 services.py health   # HTTP health check all endpoints
python3 services.py start    # Start all services
python3 services.py stop     # Stop all services
python3 services.py logs     # Tail recent logs
```

## Service Types Supported
- `systemd` — check via `systemctl is-active`
- `pm2` — check via `pm2 jlist` JSON
- `docker` — check via `docker inspect -f '{{.State.Status}}'`
- `port` — check via `ss -tlnp`
- `pid` — check via `pgrep -f`

## Color Output
- Green = active/online/running/listening
- Red = inactive/stopped/not found
- Yellow = other states

## Key Pattern
Each service is a tuple: `(name, type, identifier, port, health_url)`
Health check via `curl -s -o /dev/null -w '%{http_code}'` against health_url.
