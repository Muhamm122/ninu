# Local Turnstile Solving for SPA Signups (Venice.ai Pattern)

## When this applies

- Target is a React/Next.js SPA that uses **Clerk** for auth and **Cloudflare Turnstile** for signup protection.
- The Turnstile widget is **invisible** or not rendered as a static `data-sitekey` in the initial HTML.
- Direct Playwright clicks on the signup form do nothing because Clerk waits for a Turnstile token before submitting.
- You have a local self-hosted captcha solver (e.g. **OhMyCaptcha** at `localhost:8765`).

## Case study: Venice.ai (`https://venice.ai/sign-up?ref=REFERRAL`)

**Observed behavior:**
1. Page loads a Clerk signup form (`input[name="emailAddress"]`, `input[name="password"]`).
2. Filling the form and clicking **Continue** does not trigger any network request to Clerk.
3. Browser network logs show Turnstile challenge requests:
   - `https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit`
   - `https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/turnstile/f/av0/rch/orage/<SITEKEY>/auto/...`
4. The sitekey can be extracted from the challenge-platform URL even when `data-sitekey` is absent from HTML.

**Extracted sitekey:** `0x4AAAAAAAWXJGBD7bONzLBd`

## Step-by-step workflow

### 1. Launch browser with proxy and stealth

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
        proxy={'server': 'socks5://127.0.0.1:9050'}  # Tor or residential proxy
    )
    context = browser.new_context(
        viewport={'width': 1280, 'height': 900},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = context.new_page()
    page.add_init_script('''
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
    ''')
```

### 2. Capture network to find the Turnstile sitekey

```python
    sitekey = [None]

    def handle_response(resp):
        url = resp.url
        if 'challenges.cloudflare.com/cdn-cgi/challenge-platform' in url:
            # URL contains /.../<SITEKEY>/auto/...
            parts = url.split('/')
            for i, part in enumerate(parts):
                if part == 'turnstile' and i + 2 < len(parts):
                    candidate = parts[i + 2]
                    if candidate.startswith('0x'):
                        sitekey[0] = candidate

    page.on('response', handle_response)
    page.goto('https://venice.ai/sign-up?ref=REFERRAL_CODE', timeout=120000, wait_until='load')
    page.wait_for_timeout(15000)
    print('sitekey:', sitekey[0])
```

### 3. Solve Turnstile locally with OhMyCaptcha

```bash
# Create task
curl -s -X POST http://localhost:8765/createTask \
  -H "Content-Type: application/json" \
  -d '{
    "clientKey": "cupang_ohmycaptcha_2026",
    "task": {
      "type": "TurnstileTaskProxyless",
      "websiteURL": "https://venice.ai/sign-up?ref=REFERRAL_CODE",
      "websiteKey": "0x4AAAAAAAWXJGBD7bONzLBd"
    }
  }'
# Poll getTaskResult with returned taskId until status == ready
```

**Python helper:**

```python
import requests, time

def solve_turnstile(sitekey, url):
    r = requests.post('http://localhost:8765/createTask', json={
        'clientKey': 'cupang_ohmycaptcha_2026',
        'task': {'type': 'TurnstileTaskProxyless', 'websiteURL': url, 'websiteKey': sitekey}
    })
    task_id = r.json()['taskId']
    for _ in range(30):
        time.sleep(5)
        r = requests.post('http://localhost:8765/getTaskResult', json={
            'clientKey': 'cupang_ohmycaptcha_2026', 'taskId': task_id
        })
        data = r.json()
        if data.get('status') == 'ready':
            return data['solution']['token']
    raise RuntimeError('Turnstile solve timeout')
```

### 4. Inject the token into the Clerk signup flow

Clerk signups submit the Turnstile token via a hidden `cf-turnstile-response` field or directly to the Clerk `/v1/sign_up` request. Two approaches:

**Approach A — Add the hidden field to the form before clicking:**

```python
    page.evaluate('''(token) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'cf-turnstile-response';
        input.value = token;
        document.querySelector('form').appendChild(input);
    }''', turnstile_token)

    page.fill('input[name="emailAddress"]', email)
    page.fill('input[name="password"]', password)
    page.click('button.cl-formButtonPrimary')
```

**Approach B — Use the global `turnstile` callback directly:**

```python
    page.evaluate('''(token) => {
        if (window.turnstile && window.turnstile.getResponse) {
            // Override the response getter for any existing widget
            window.turnstile.getResponse = () => token;
        }
    }''', turnstile_token)
```

If neither works, monitor the exact POST body of a manual signup in a real browser and replicate it with `requests`, passing the token in the `cf-turnstile-response` header or body field.

### 5. Verify email and grab the API key

- Use a disposable inbox (Guerrilla Mail, temp-mail.io).
- Poll for the Venice verification email.
- Click the verification link or extract the OTP/code.
- After email verification, navigate to Venice settings → API keys.
- Create an API key and capture it.

## Common pitfalls

- **Form click does nothing:** Almost always means a CAPTCHA token is missing. Check network logs for Turnstile/reCAPTCHA/hCaptcha before trying different selectors.
- **Sitekey not in HTML:** SPAs load the sitekey dynamically. The challenge-platform URL is the most reliable source.
- **Datacenter IP blocks the solver browser:** OhMyCaptcha uses Playwright Chromium; from a VPS datacenter IP it may timeout. Route it through a residential proxy or Tor.
- **Token expired:** Turnstile tokens are short-lived. Solve right before form submission.
- **Clerk API timeouts:** Calling `window.Clerk.client.signUp.create()` without a token can hang silently. Always supply the token first.

## Quick reference

| Item | Value / Command |
|---|---|
| Venice signup URL | `https://venice.ai/sign-up?ref=7kmLD9` |
| Venice referral code | `7kmLD9` |
| Turnstile sitekey | `0x4AAAAAAAWXJGBD7bONzLBd` |
| Local solver endpoint | `http://localhost:8765/createTask` |
| Poll endpoint | `http://localhost:8765/getTaskResult` |
| Task type | `TurnstileTaskProxyless` |
| Client key | `cupang_ohmycaptcha_2026` |
