# SCTG CAPTCHA Solver (sctg.xyz)

2captcha-compatible API endpoint. Drop-in replacement for 2captcha.com — just change the server URL.

## Endpoints

| URL | Region |
|-----|--------|
| `https://sctg.xyz` | Primary |
| `https://ru.sctg.xyz` | Russia |
| `https://api.sctg.xyz` | API-only |

Server IPs: 157.180.15.203, 109.248.207.94 (ports 80/443)

## API Format

Identical to 2captcha (`in.php` / `res.php`):

```
Submit: POST https://sctg.xyz/in.php  key=API_KEY&method=userrecaptcha&googlekey=SITEKEY&pageurl=URL
Response: OK|{REQUEST_ID}

Poll:   GET  https://sctg.xyz/res.php?key=API_KEY&action=get&id={REQUEST_ID}
Response: CAPCHA_NOT_READY (retry after 3-5s) or OK|{TOKEN}

Balance: GET https://sctg.xyz/res.php?key=API_KEY&action=getbalance
```

## Environment

```env
SCTG_API_KEY=your_key_here
SCTG_ENDPOINT=https://sctg.xyz
```

## Integration with Python (2captcha SDK)

```python
from twocaptcha import TwoCaptcha
# Just change the server parameter:
solver = TwoCaptcha(API_KEY, server="sctg.xyz")
result = solver.recaptcha(sitekey=SITE_KEY, url=PAGE_URL)
```

## Supported Types & Pricing

| Service | Price/1K (USD) |
|---------|----------------|
| ReCaptcha v2 | 0.07 |
| ReCaptcha v3 | 0.40 |
| ReCaptcha MB | 0.10 |
| hCaptcha | 0.015 |
| Turnstile (Cloudflare) | 0.22 |
| Yandex SmartCaptcha | 0.05 |
| GeeTest Ico | 0.015 |
| GeeTest Images | 0.015 |
| Slider #1 / #2 | 0.015 |
| FunCaptcha (Tcaptcha) | 0.10 |
| AuthKong | 0.10 |
| Image / Text on Image | 0.015 |
| ReCaptcha IMG | 0.02 |
| ReCaptcha v3 high score | 0.40 |
| LLM AI | 0.10 |
| Protonmail | 0.015 |
| hCaptcha images | 0.015 |
| FriendlyCaptcha | 0.015 |
| Yandex SC IMG | 0.015 |
| Basilisk / Puzzle Ico | 0.015 |
| Cwallet | 0.015 |
| WorkCash | 0.03 |
| PoW sha256 | 0.015 |
| JS Challenge (Cloudflare) | 0.22 |

## CLI Tool

Located at: `~/.hermes/skills/superagent/tools/sctg_solver.py`

```bash
# Check balance
python3 sctg_solver.py --balance

# Solve ReCaptcha v2
python3 sctg_solver.py --type recaptcha_v2 --sitekey 6Le... --url https://example.com/page

# Solve Turnstile
python3 sctg_solver.py --type turnstile --sitekey 0x4A... --url https://example.com/page

# Solve image CAPTCHA
python3 sctg_solver.py --type image --file /tmp/captcha.png
```

## Balance Notes

- Check balance before starting a solve batch: `ERROR_ZERO_BALANCE` means no funds
- Negative balance possible (overdraft) — still returns `ERROR_ZERO_BALANCE` for new requests
- Top up via the SCTG Telegram bot or their support
