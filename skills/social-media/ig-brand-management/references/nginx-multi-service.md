# Nginx Multi-Service Reverse Proxy for IG Brand

## Upstream Services

| Service | Port | Route |
|---------|------|-------|
| Landing Page | 80 (static) | `/` (Nginx serves directly) |
| Webhook API | 8000 | `/api/`, `/webhook/` |
| n8n Workflows | 5678 | `/workflow/` |
| FreeLLMAPI | 3001 | `/llm/` (restricted) |

## Rate Limit Zones

```nginx
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
```

## Key Config Patterns

### Static Landing Page (fastest — served by Nginx)
```nginx
location / {
    limit_req zone=general burst=20 nodelay;
    root /var/www/<brand>;
    index index.html;
    try_files $uri $uri/ =404;
    # Cache static assets 30 days
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Reverse Proxy to API
```nginx
location /api/ {
    limit_req zone=api burst=50 nodelay;
    proxy_pass http://upstream_name/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### WebSocket Support (n8n)
```nginx
location /workflow/ {
    proxy_pass http://n8n/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Security (block attack paths)
```nginx
location ~ /\.git { return 404; }
location ~ /\.env { return 404; }
location ~ /wp-admin { return 404; }
```

## Gzip
```nginx
gzip on;
gzip_types text/plain text/css text/xml text/javascript
           application/json application/javascript application/xml;
gzip_min_length 256;
```

## Deploying
```bash
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo cp site.conf /etc/nginx/sites-available/<brand>
sudo ln -sf /etc/nginx/sites-available/<brand> /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## SSL (requires domain pointing to server)
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
