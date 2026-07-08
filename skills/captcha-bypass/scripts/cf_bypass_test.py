#!/usr/bin/env python3
"""
PROXY LISTENER — Cloudflare Bypass Test
Uses: cloudscraper + residential proxy (instant-proxies)
Target: test CF bypass on known CF-protected site
"""

import cloudscraper
import sys
import json

# Target CF-protected
TARGETS = [
    'https://skripsi.muham.dev/data',
    'https://www.namecheap.com/legal/hosting/aup.aspx',
    'https://www.cloudflare.com/',
]

# proxy config
PROXY = 'http://2952:D8WHKfYnaSnV@p101.instantproxies.com:9188'

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False, 'desktop': True},
)

for t in TARGETS:
    try:
        r = scraper.get(t, timeout=30)
        status = r.status_code
        content_len = len(r.text)
        print(f'{t}: {status} ({content_len}b)')
        # CF headers
        cf_headers = {k: v for k, v in r.headers.items() if 'cf-' in k.lower() or 'cloudflare' in k.lower()}
        if cf_headers:
            print(f'  CF headers: {cf_headers}')
        if status == 200:
            print(f'  ✅ BYPASSED!')
            print(f'  First 500 chars: {r.text[:500]}')
        elif 403 in [status]:
            print(f'  ❌ BLOCKED by CF')
        else:
            print(f'  Other: {status}')
    except Exception as e:
        print(f'{t}: ERROR {e}')