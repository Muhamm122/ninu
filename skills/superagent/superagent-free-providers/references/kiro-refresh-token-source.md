# KIRO-Refresh-Token Source Analysis

## Repository
- **URL:** `https://github.com/KorekKayu/KIRO-Refresh-Token.git`
- **Purpose:** Auto-register GSuite/Google accounts on kiro.dev via Google SSO, harvest OAuth tokens

## Architecture (index.js)

| Module | Lines | Purpose |
|--------|-------|---------|
| `handleGoogleLogin()` | ~180 | Fills email + password in Google OAuth form (Playwright) |
| `setupTokenInterceptor()` | ~40 | Network-level response interceptor: captures `refreshToken` from gateway API responses |
| `extractTokenFromStorage()` | ~60 | 4-priority token extraction: cookies → localStorage → window → API |
| `processAccount()` | ~140 | Full account lifecycle: signin → Google → consent → token → save |

## Token Capture Points
1. **Cookies** — `page.context().cookies()` → filters for `AccessToken`, `RefreshToken`, `XSRF-TOKEN`
2. **localStorage** — `page.evaluate(() => localStorage)` → parses JSON for `{accessToken, refreshToken}`
3. **window object** — `window.__kiro_token__` or `window.__auth__`
4. **API fetch** — `fetch('/api/auth/session')` with credentials:include

## Output Files
- `results/token_<email>.json` — full token object per account
- `RT.txt` — one refresh token per line (appended)
- `results/summary_*.json` — batch stats

## Google OAuth Flow (what the bot waits for)
```
1. GET https://app.kiro.dev/signin → click "Google" button
2. Redirect to accounts.google.com → fill email
3. Fill password → press Next
4. OAuth consent screen ("Lanjutkan" / "Continue" / "Allow")
5. Redirect back to app.kiro.dev/home
6. Intercept token from network (response body) or storage
```

## Pitfalls
| Error | Cause | Fix |
|-------|-------|-----|
| `Tombol Google SSO tidak ditemukan` | Page layout changed | Increase waitForSelector timeout, check button text |
| `Input email Google tidak ditemukan` | CAPTCHA or slow load | Set HEADLESS=false, reduce concurrency |
| `Gagal redirect ke Kiro setelah login Google` | Google blocked the redirect | Manual solve in browser, increase timeout |
| `Gagal mendapatkan token` | Storage/cookie cleared on redirect | Intercept BEFORE redirect (network listener) |