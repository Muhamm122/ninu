

# ===== YesCaptcha Integration =====
YESCAPTCHA_KEY = "73c9036daae215bfc577b17c009a283d2f928b92125845"
YESCAPTCHA_URL = "https://api.yescaptcha.com"

def yes_solve(task_type, website_url, website_key, timeout=120, **kwargs):
    """Solve CAPTCHA via YesCaptcha API.
    
    Supported types:
      - NoCaptchaTaskProxyless (ReCaptcha v2)
      - RecaptchaV3TaskProxyless (ReCaptcha v3)
      - HCaptchaTaskProxyless (hCaptcha)
      - TurnstileTaskProxyless (Cloudflare Turnstile)
      - ImageToTextTask (Image captcha)
      - FunCaptchaTaskProxyless (Arkose/FunCaptcha)
    
    Returns: dict with 'solution' or 'error'
    """
    import requests, time
    
    task = {'type': task_type, 'websiteURL': website_url, 'websiteKey': website_key}
    task.update(kwargs)
    
    r = requests.post(f'{YESCAPTCHA_URL}/createTask', json={
        'clientKey': YESCAPTCHA_KEY, 'task': task
    }, timeout=30)
    d = r.json()
    
    if d.get('errorId') != 0:
        return {'error': d.get('errorCode'), 'desc': d.get('errorDescription')}
    
    task_id = d['taskId']
    
    for _ in range(timeout // 3):
        time.sleep(3)
        r = requests.post(f'{YESCAPTCHA_URL}/getTaskResult', json={
            'clientKey': YESCAPTCHA_KEY, 'taskId': task_id
        }, timeout=15)
        d = r.json()
        
        if d.get('status') == 'ready':
            return {'solution': d.get('solution', {}), 'task_id': task_id}
        
        if d.get('errorId', 0) != 0:
            return {'error': d.get('errorCode'), 'desc': d.get('errorDescription')}
    
    return {'error': 'TIMEOUT', 'desc': f'Not solved after {timeout}s'}


def yes_balance():
    """Get YesCaptcha balance in USD."""
    import requests
    r = requests.post(f'{YESCAPTCHA_URL}/getBalance', json={'clientKey': YESCAPTCHA_KEY}, timeout=10)
    d = r.json()
    return d.get('balance', 0) / 100 if d.get('errorId') == 0 else None
