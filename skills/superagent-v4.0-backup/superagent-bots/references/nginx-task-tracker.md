# Nginx Reverse Proxy — Task Tracker API

## Adding /task/ location to existing Haus Living nginx config

When adding a new API route to an existing FastAPI service behind nginx:

```nginx
# In /etc/nginx/sites-enabled/haus-living
# Add BEFORE the /webhook/ location block

# Task Tracker API
location /task/ {
    limit_req zone=api burst=30 nodelay;
    proxy_pass http://haus_api/task/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Full Haus Living nginx location blocks (reference)

```
/           → static landing page (/var/www/haus-living)
/api/       → proxy to haus_api (FastAPI on :8000)
/webhook/   → proxy to haus_api/webhook/
/task/      → proxy to haus_api/task/ (task tracker)
/workflow/  → proxy to n8n (:5678)
/llm/       → proxy to freellmapi (:3001)
/health     → nginx-level health check (no upstream)
```

## Upstream definitions

```nginx
upstream haus_api { server 127.0.0.1:8000; }
```

## Testing

```bash
# Test nginx config
sudo nginx -t

# Reload
sudo nginx -s reload

# Test endpoint
curl -H "X-API-Key: haus_living_task_key_2026" http://18.143.107.30/task/stats
```
