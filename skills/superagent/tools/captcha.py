#!/usr/bin/env python3
"""
CUPANG CAPTCHA Solver — YesCaptcha + SCTG
==========================================
Solve CAPTCHAs via paid API services.

Usage:
  captcha.py balance              — Show balance for all providers
  captcha.py recaptcha-v2 URL KEY — Solve ReCaptcha v2
  captcha.py recaptcha-v3 URL KEY — Solve ReCaptcha v3 (score 0.3-0.9)
  captcha.py hcaptcha URL KEY     — Solve hCaptcha
  captcha.py turnstile URL KEY    — Solve Cloudflare Turnstile
  captcha.py image BASE64         — Solve image captcha (base64)
  captcha.py funcaptcha URL KEY   — Solve FunCaptcha/Arkose

Providers (priority order):
  1. YesCaptcha ($15.00) — ReCaptcha, hCaptcha, Turnstile, Image, FunCaptcha
  2. SCTG (balance: check) — ReCaptcha, hCaptcha, GeeTest, Yandex, Protonmail

Environment:
  YESCAPTCHA_KEY — YesCaptcha API key
  SCTG_KEY       — SCTG API key (optional)
"""

import os, sys, json, time, requests

YES_KEY = os.environ.get('YESCAPTCHA_KEY', '73c9036daae215bfc577b17c009a283d2f928b92125845')
SCTG_KEY = os.environ.get('SCTG_KEY', '')
YES_URL = 'https://api.yescaptcha.com'
SCTG_URL = 'https://api.sctg.xyz'


def yes_balance():
    try:
        r = requests.post(f'{YES_URL}/getBalance', json={'clientKey': YES_KEY}, timeout=10)
        d = r.json()
        if d.get('errorId') == 0:
            return d.get('balance', 0) / 100  # cents to dollars
        return None
    except: return None


def sctg_balance():
    if not SCTG_KEY: return None
    try:
        r = requests.get(f'{SCTG_URL}/res.php?key={SCTG_KEY}&action=getbalance', timeout=10)
        return float(r.text) if r.text and not r.text.startswith('ERROR') else None
    except: return None


def cmd_balance():
    yb = yes_balance()
    sb = sctg_balance()
    print("🔍 CAPTCHA Solver Balances:")
    print()
    print(f"  🟢 YesCaptcha:  ${yb:.2f}" if yb is not None else "  ⚪ YesCaptcha:  unavailable")
    print(f"  🟡 SCTG:        ${sb:.4f}" if sb is not None else "  ⚪ SCTG:        not configured")
    print()
    total = (yb or 0) + (sb or 0)
    print(f"  💰 Total: ~${total:.2f}")


def solve_yescaptcha(task_type, website_url, website_key, **kwargs):
    """Create and poll YesCaptcha task."""
    task = {
        'type': task_type,
        'websiteURL': website_url,
        'websiteKey': website_key,
    }
    task.update(kwargs)
    
    # Create task
    r = requests.post(f'{YES_URL}/createTask', json={
        'clientKey': YES_KEY,
        'task': task
    }, timeout=30)
    
    d = r.json()
    if d.get('errorId') != 0:
        return {'error': d.get('errorCode', 'unknown'), 'desc': d.get('errorDescription', '')}
    
    task_id = d['taskId']
    
    # Poll for result (max 120 seconds)
    for _ in range(40):
        time.sleep(3)
        r = requests.post(f'{YES_URL}/getTaskResult', json={
            'clientKey': YES_KEY,
            'taskId': task_id
        }, timeout=15)
        d = r.json()
        
        if d.get('status') == 'ready':
            return {'solution': d.get('solution', {}), 'task_id': task_id}
        
        if d.get('errorId', 0) != 0:
            return {'error': d.get('errorCode', 'unknown'), 'desc': d.get('errorDescription', '')}
    
    return {'error': 'TIMEOUT', 'desc': 'Solution not ready after 120s'}


def cmd_recaptcha_v2(url, key):
    print(f"🔄 Solving ReCaptcha v2...")
    print(f"   URL: {url}")
    print(f"   Key: {key}")
    
    result = solve_yescaptcha('NoCaptchaTaskProxyless', url, key)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']} — {result.get('desc', '')}")
    else:
        token = result['solution'].get('gRecaptchaResponse', '')
        print(f"✅ Solved! (task: {result['task_id']})")
        print(f"   Token: {token[:80]}...")
        print(f"\n📋 Full token:\n{token}")


def cmd_recaptcha_v3(url, key, score=0.3):
    print(f"🔄 Solving ReCaptcha v3 (score: {score})...")
    print(f"   URL: {url}")
    
    result = solve_yescaptcha('RecaptchaV3TaskProxyless', url, key, minScore=score)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']} — {result.get('desc', '')}")
    else:
        token = result['solution'].get('gRecaptchaResponse', '')
        print(f"✅ Solved! (task: {result['task_id']})")
        print(f"   Token: {token[:80]}...")
        print(f"\n📋 Full token:\n{token}")


def cmd_hcaptcha(url, key):
    print(f"🔄 Solving hCaptcha...")
    print(f"   URL: {url}")
    print(f"   Key: {key}")
    
    result = solve_yescaptcha('HCaptchaTaskProxyless', url, key)
    
    if 'error' in result:
        # Try alternate type name
        if 'ERROR_TASK_NOT_SUPPORTED' in result.get('error', ''):
            result = solve_yescaptcha('HCaptchaTurboTask', url, key)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']} — {result.get('desc', '')}")
    else:
        token = result['solution'].get('gRecaptchaResponse', '')
        print(f"✅ Solved! (task: {result['task_id']})")
        print(f"   Token: {token[:80]}...")
        print(f"\n📋 Full token:\n{token}")


def cmd_turnstile(url, key):
    print(f"🔄 Solving Cloudflare Turnstile...")
    print(f"   URL: {url}")
    
    result = solve_yescaptcha('TurnstileTaskProxyless', url, key)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']} — {result.get('desc', '')}")
    else:
        token = result['solution'].get('token', '')
        print(f"✅ Solved! (task: {result['task_id']})")
        print(f"   Token: {token[:80]}...")
        print(f"\n📋 Full token:\n{token}")


def cmd_image(base64_img):
    print(f"🔄 Solving image captcha...")
    
    result = solve_yescaptcha('ImageToTextTask', '', '', body=base64_img)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']} — {result.get('desc', '')}")
    else:
        text = result['solution'].get('text', '')
        print(f"✅ Solved! Text: {text}")


def cmd_funcaptcha(url, key):
    print(f"🔄 Solving FunCaptcha/Arkose...")
    print(f"   URL: {url}")
    
    result = solve_yescaptcha('FunCaptchaTaskProxyless', url, key)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']} — {result.get('desc', '')}")
    else:
        token = result['solution'].get('token', '')
        print(f"✅ Solved! (task: {result['task_id']})")
        print(f"   Token: {token[:80]}...")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == 'balance':
        cmd_balance()
    elif cmd == 'recaptcha-v2':
        if len(sys.argv) < 4:
            print("Usage: captcha.py recaptcha-v2 <URL> <SITE_KEY>")
            sys.exit(1)
        cmd_recaptcha_v2(sys.argv[2], sys.argv[3])
    elif cmd == 'recaptcha-v3':
        if len(sys.argv) < 4:
            print("Usage: captcha.py recaptcha-v3 <URL> <SITE_KEY> [SCORE]")
            sys.exit(1)
        score = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
        cmd_recaptcha_v3(sys.argv[2], sys.argv[3], score)
    elif cmd == 'hcaptcha':
        if len(sys.argv) < 4:
            print("Usage: captcha.py hcaptcha <URL> <SITE_KEY>")
            sys.exit(1)
        cmd_hcaptcha(sys.argv[2], sys.argv[3])
    elif cmd == 'turnstile':
        if len(sys.argv) < 4:
            print("Usage: captcha.py turnstile <URL> <SITE_KEY>")
            sys.exit(1)
        cmd_turnstile(sys.argv[2], sys.argv[3])
    elif cmd == 'image':
        if len(sys.argv) < 3:
            print("Usage: captcha.py image <BASE64>")
            sys.exit(1)
        cmd_image(sys.argv[2])
    elif cmd == 'funcaptcha':
        if len(sys.argv) < 4:
            print("Usage: captcha.py funcaptcha <URL> <PUBLIC_KEY>")
            sys.exit(1)
        cmd_funcaptcha(sys.argv[2], sys.argv[3])
    elif cmd in ('help', '-h', '--help'):
        print(__doc__)
    else:
        print(f"Unknown: {cmd}")
