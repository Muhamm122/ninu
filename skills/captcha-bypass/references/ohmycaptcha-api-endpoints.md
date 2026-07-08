# OhMyCaptcha API Endpoints (Verified 2026-06-25)

> Self-hosted captcha solver at `http://localhost:8765`. Source: https://github.com/shenhao-stu/ohmycaptcha

## Correct API Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/createTask` | POST | Create a captcha solving task |
| `/getTaskResult` | POST | Poll for solution |
| `/getBalance` | POST | Check balance |
| `/api/v1/health` | GET | Health check |

**Note:** `/api/v1/tasks` and `/api/v1/solve` do NOT exist (404). Use `/createTask` and `/getTaskResult`.

## Create Task — Request Body

```json
{
  "clientKey": "cupang_ohmycaptcha_2026",
  "task": {
    "type": "HCaptchaTaskProxyless",
    "websiteURL": "https://target.com/page",
    "websiteKey": "sitekey-here"
  }
}
```

**Field names matter:**
- `websiteURL` (camelCase) — NOT `url` or `website_url`
- `websiteKey` (camelCase) — NOT `siteKey` or `site_key`
- `clientKey` — NOT `client_key`

## Task Types

| Type | String |
|------|--------|
| hCaptcha | `HCaptchaTaskProxyless` |
| reCAPTCHA v2 | `RecaptchaV2TaskProxyless` |
| reCAPTCHA v3 | `RecaptchaV3TaskProxyless` |
| Turnstile | `TurnstileTaskProxyless` |
| Image OCR | `ImageToTextTask` |

## Get Task Result — Request Body

```json
{
  "clientKey": "cupang_ohmycaptcha_2026",
  "taskId": "task-id-from-create"
}
```

## Response Format

**Success:**
```json
{
  "errorId": 0,
  "status": "ready",
  "solution": {
    "token": "<captcha solution token>"
  }
}
```

**Processing:**
```json
{
  "errorId": 0,
  "status": "processing",
  "solution": null
}
```

**Error (unsolvable):**
```json
{
  "errorId": 1,
  "status": null,
  "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
  "errorDescription": "HCaptcha failed after 3 attempts: ..."
}
```

## Known Limitations

- **Datacenter IP = frequent failures**: Browser-based solvers (hCaptcha, reCAPTCHA, Turnstile) use Playwright headless Chromium. From VPS datacenter IP, Cloudflare/Google often block the challenge before Chromium renders it. Expect `ERROR_CAPTCHA_UNSOLVABLE`.
- **ImageToText requires cloud LLM key**: Needs `CLOUD_API_KEY` (MiMo, OpenAI, etc). Without it, image tasks fail with connection error.
- **No fingerprint-bound solving**: Cloud solver cannot solve Discord/Spotify hCaptcha (fingerprint-bound by design).
