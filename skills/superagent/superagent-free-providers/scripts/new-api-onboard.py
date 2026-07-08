#!/usr/bin/env python3
"""
Reusable onboarding recipe for new-api / one-api based LLM gateways.

These platforms (IAMHC, etc.) deliberately mask API keys in `/api/token` and
require the undocumented `/api/token/batch/keys` endpoint to reveal them.
They also use `PUT /api/token/` (trailing slash, id in body) for updates —
`PUT /api/token/<id>` returns 404.

Works against any deployment of:
  - https://github.com/songquanpeng/one-api  (one-api)
  - https://github.com/Calcium-Ion/new-api-secret (new-api, fork)

Usage:
  python3 new-api-onboard.py <base_url> <username> <password>

Outputs:
  - All tokens with their UNMASKED keys
  - Hermes-ready config snippet
"""
import sys
import json
import time
import urllib3
import requests

urllib3.disable_warnings()


def retry(fn, attempts=4, delay=10):
    """Site is flaky — SSL handshake timeouts common. Retry loop."""
    for i in range(attempts):
        try:
            return fn()
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:
            if i == attempts - 1:
                raise
            print(f"  retry {i+1}/{attempts} after {delay}s: {e}")
            time.sleep(delay)


def onboard(base_url, username, password):
    s = requests.Session()
    s.verify = False
    base = base_url.rstrip('/')

    # 1. Login
    print(f"[*] Login as {username}")
    r = retry(lambda: s.post(
        f"{base}/api/user/login",
        json={"username": username, "password": password},
        timeout=30,
    ))
    if not r.json().get("success"):
        print(f"[!] Login failed: {r.text[:200]}")
        return
    uid = r.json()["data"]["id"]
    print(f"[+] uid={uid}")

    headers = {"New-Api-User": str(uid)}

    # 2. List tokens (masked)
    r = retry(lambda: s.get(f"{base}/api/token", headers=headers, timeout=30))
    items = r.json()["data"]["items"]
    print(f"[+] Found {len(items)} tokens (keys masked)")
    for t in items:
        print(f"    - id={t['id']} name={t['name']} group={t.get('group','')!r} "
              f"key={t['key']}")

    # 3. Reveal unmasked keys via /api/token/batch/keys
    ids = [t["id"] for t in items]
    r = retry(lambda: s.post(
        f"{base}/api/token/batch/keys",
        json={"ids": ids},
        headers=headers,
        timeout=30,
    ))
    if not r.json().get("success"):
        print(f"[!] batch/keys failed: {r.text[:200]}")
        return
    keys = r.json()["data"]["keys"]
    print(f"[+] Unmasked keys:")
    for tid, key in keys.items():
        print(f"    {tid}: {key}")

    # 4. Probe /v1/models with each key — find which models work
    print(f"\n[*] Probing models with each key...")
    working_models = {}
    for name, key in zip([t["name"] for t in items], keys.values()):
        # Refresh models list once
        try:
            r = retry(lambda: s.get(f"{base}/v1/models", timeout=30))
            models = [m["id"] for m in r.json().get("data", [])]
        except Exception as e:
            print(f"  Could not list models: {e}")
            models = ["gpt-4o-mini", "Kimi-K2.6"]

        # Try a few candidate models
        for model in ["Kimi-K2.6", "gpt-4o-mini", "gpt-3.5-turbo"]:
            if model not in models:
                continue
            try:
                rr = retry(lambda m=model, k=key: s.post(
                    f"{base}/v1/chat/completions",
                    json={"model": m, "messages": [{"role": "user", "content": "hi"}],
                          "max_tokens": 5},
                    headers={"Authorization": f"Bearer {k}"},
                    timeout=30,
                ))
                if rr.status_code == 200:
                    working_models[name] = model
                    print(f"  [+] {name} / {model}: 200 OK")
                    break
                elif rr.status_code == 503:
                    print(f"  [-] {name} / {model}: 503 no channel")
                else:
                    print(f"  [-] {name} / {model}: {rr.status_code}")
            except Exception as e:
                print(f"  [-] {name} / {model}: {str(e)[:60]}")

    # 5. Set group=default on first token (via PUT /api/token/ with id in body)
    if items:
        first = items[0]
        print(f"\n[*] Setting group=default on token id={first['id']}")
        payload = {**first, "group": "default"}
        # The masked "key" must NOT be sent back — server expects it empty or absent
        payload["key"] = ""
        r = retry(lambda: s.put(
            f"{base}/api/token/",
            json=payload,
            headers=headers,
            timeout=30,
        ))
        print(f"  PUT /api/token/: {r.status_code} {r.json().get('data',{}).get('group')!r}")

    # 6. Emit Hermes config snippet
    if keys:
        first_key = next(iter(keys.values()))
        print(f"\n=== HERMES CONFIG SNIPPET ===")
        print(f"hermes config set providers.<alias>.api_key '{first_key}'")
        print(f"hermes config set providers.<alias>.base_url '{base}/v1'")
        if working_models:
            model = next(iter(working_models.values()))
            print(f"hermes config set providers.<alias>.default_model '{model}'")
            print(f"hermes config set providers.<alias>.name '{username}'")
        print(f"hermes config set fallback_providers '[\"...\",\"<alias>\"]'")
        print(f"\nDirect test:")
        print(f"  curl {base}/v1/chat/completions \\")
        print(f"    -H 'Authorization: Bearer {first_key}' \\")
        print(f"    -H 'Content-Type: application/json' \\")
        print(f"    -d '{{\"model\":\"{next(iter(working_models.values()), 'Kimi-K2.6')}\",\"messages\":[{{\"role\":\"user\",\"content\":\"hi\"}}]}}'")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    onboard(sys.argv[1], sys.argv[2], sys.argv[3])
