# Free & Open-Source Captcha Solvers — Research Notes

> Source: GitHub deep research 2026-06-12. Verified repos, READMEs, and issue trackers.
> Covers: free tiers, open-source self-hosted, and "freemium" alternatives to paid 2captcha/AntiCaptcha.

---

## Quick Comparison

| Solver | Cost | Method | Support | Success | Stars | Language |
|--------|------|--------|---------|---------|-------|----------|
| **noCaptchaAi** | FREE 6000 solves/mo | AI vision API | qCaptcha, image | ~95% | 7 | API (any) |
| **puppeteer-recatcha** | FREE unlimited | wit.ai audio-to-text | reCAPTCHA v2 | 70-80% | 4 | Node.js |
| **FastSolverCaptcha** | FREE unlimited | Tesseract.js OCR | Image/text captcha | ~60-70% | 1 | Node.js |
| **CaptchaFree** | FREE unlimited | OpenAI Whisper local | reCAPTCHA v2 (audio) | 70-80% | 9 | Python |
| **librecaptcha** | FREE/libre | Framework for solving | reCAPTCHA | Varies | 48 | Python |
| **CapSolver trial** | FREE $0.50 trial | Paid API (trial) | reCAPTCHA v2/v3, hCaptcha, GeeTest, AWS | ~99% | N/A | Extension |

---

## 1. noCaptchaAi.com — 6000 Free Solves/Month ⭐ BEST FREE API

- **Repo**: `nocaptchaai-com/qCaptcha-Solver` (official: `noCaptchaAi/qCaptchaSolverApi`)
- **URL**: https://nocaptchaAi.com
- **Free tier**: 6000 solves/month
- **Speed**: 0.02s ~ 0.5s per solve
- **API**: REST API, compatible with 2captcha format
- **Libraries available**: Puppeteer, Selenium, Userscript
- **Status**: Actively developing TikTok, Instagram, Stripe solvers
- **Signup**: https://nocaptchaAi.com (crypto payment supported)

### Integration (Python, 2captcha-compatible format)
```python
import requests, time

API_KEY = "your_key_here"

# Create task
resp = requests.post("https://api.nocaptchaai.com/createTask", json={
    "clientKey": API_KEY,
    "task": {
        "type": "ReCaptchaV2TaskProxyless",
        "websiteURL": "https://target.com",
        "websiteKEY": "site_key_here"
    }
})
task_id = resp.json()["taskId"]

# Poll for result
while True:
    result = requests.post("https://api.nocaptchaai.com/getTaskResult", json={
        "clientKey": API_KEY, "taskId": task_id
    }).json()
    if result["status"] == "ready":
        token = result["solution"]["gRecaptchaResponse"]
        break
    time.sleep(3)
```

---

## 2. puppeteer-recatcha — Free via wit.ai (Unlimited)

- **Repo**: `jejolare/puppeteer-recatcha`
- **URL**: https://github.com/jejolare/puppeteer-recatcha
- **Cost**: 100% free (requires wit.ai API key — free signup at https://wit.ai)
- **Method**: Clicks audio captcha → downloads audio → transcribes via wit.ai speech-to-text
- **Success rate**: 70-80%
- **Support**: reCAPTCHA v2 via Puppeteer/headless browser
- **Last updated**: 5 years ago (still functional as of 2026-06)

### Usage
```bash
npm install puppeteer-recatcha
```

```js
import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import solve from 'puppeteer-recaptcha';

puppeteer.use(StealthPlugin());
const API_KEY = "your_wit_ai_key";  // Free from https://wit.ai

(async () => {
    const browser = await puppeteer.launch({
        args: [
            '--disable-web-security',
            '--disable-features=IsolateOrigins',
            '--disable-site-isolation-trials'
        ]
    });
    const page = await browser.newPage();
    await page.goto('https://target.com');
    const result = await solve(page, API_KEY);
    console.log(result);  // { solved: true, error: null }
})();
```

### Pitfalls
- Requires `puppeteer-extra-plugin-stealth` to avoid bot detection
- Audio captcha must be available on the target site (not all sites offer it)
- wit.ai key required — free signup, but requires account

---

## 3. FastSolverCaptcha — Self-Hosted OCR (Unlimited)

- **Repo**: `codedByCan/FastSolverCaptcha`
- **URL**: https://github.com/codedByCan/FastSolverCaptcha
- **Cost**: 100% free, self-hosted
- **Method**: Tesseract.js OCR + Jimp image processing
- **Support**: Image/text captcha ONLY (NOT reCAPTCHA/hCaptcha)
- **Tech stack**: Node.js, tesseract.js, jimp
- **Use case**: Custom captcha images, simple text-on-image challenges

### Limitations
- Only works on simple image captchas (text on background)
- No reCAPTCHA/hCaptcha/CF Turnstile support
- Low success rate on noisy/distorted images

---

## 4. CaptchaFree — Local Whisper (Unlimited, GPU Recommended)

- **Repo**: `theriley106/CaptchaFree`
- **URL**: https://github.com/theriley106/CaptchaFree
- **Cost**: 100% free (no API calls — runs OpenAI Whisper locally)
- **Method**: Downloads audio captcha → transcribes via local Whisper model
- **Support**: reCAPTCHA v2 via Selenium WebDriver wrapper
- **Requirements**: Local Whisper model (needs ~2GB RAM, GPU optional but faster)

### Pitfalls
- Downloads Whisper model on first run (~1-3 GB depending on model size)
- Slower than API-based methods (local inference)
- Quality depends on Whisper model tier (tiny → medium → large)

---

## 5. librecaptcha — Libre Framework (Advanced)

- **Repo**: `taylordotfish/librecaptcha` (archived 2025-05)
- **URL**: https://github.com/taylordotfish/librecaptcha
- **Cost**: Free/libre
- **Approach**: Framework for building custom reCAPTCHA solvers
- **Best for**: Developers who want to build automated solvers
- **Status**: Archived — read-only as of May 2025, but code is still usable

---

## 6. CapSolver — $0.50 Free Trial (Paid API, Best Coverage)

- **URL**: https://capsolver.com
- **Free trial**: $0.50 via livechat (ask for trial)
- **Coverage**: reCAPTCHA v2/v3/enterprise, hCaptcha, GeeTest, AWS, Turnstile, Funcaptcha
- **Success rate**: ~99%
- **Browser extension**: `capsolver/capsolver-browser-extension`
- **Trial**: Register → contact livechat → ask for trial → get $0.50 free

---

## GitHub Research Methodology

When searching for free alternatives on GitHub:

1. **Search repos**: `https://github.com/search?q=<query>&type=repositories&s=stars&o=desc`
2. **Check README**: Fetch via `raw.githubusercontent.com/<user>/<repo>/<branch>/README.md`
3. **Check issues**: `https://api.github.com/repos/<user>/<repo>/issues?state=all&per_page=30`
4. **Check user's other repos**: `https://api.github.com/users/<username>/repos?per_page=100&sort=updated`
5. **File tree**: `https://api.github.com/repos/<user>/<repo>/git/trees/<branch>?recursive=1`

### Common search queries
- "free captcha solver api"
- "2captcha alternative free"
- "recaptcha solver free github"
- "hcaptcha solver free github"
- "captcha solving free service"

---

## What Does NOT Work (Debunked)

- **`recaptchaUser/FREE-CAPTCHA-SOLVER-EXTENSION`**: Just a proxy page pointing to Capsolver API with trial instructions — not an actual free solver
- **2captcha.com free tier**: Does not exist — purely paid ($2.99/1000)
- **AntiCaptcha free trial**: No free trial available (paid only as of 2026-06)
- **`tashfeenahmed/freellmapi`**: LLM API proxy — zero captcha functionality despite URL name similarity. 223 files, 0 captcha references. Do NOT waste time researching this for captcha purposes.
- **`puppeteer-recatcha`**: Already set up at `/tmp/captcha-test/` on this VPS (2026-06-12). Test script ready at `/tmp/captcha-test/test.js`. Just needs `WIT_AI_KEY` env var.

---

## Recommendation Matrix

| Use Case | Best Free Option |
|----------|-----------------|
| High-volume reCAPTCHA solving | noCaptchaAi (6000/mo) + CapSolver trial |
| Unlimited reCAPTCHA v2 via browser | puppeteer-recatcha (wit.ai) |
| Image/text captcha OCR | FastSolverCaptcha (Tesseract.js) |
| No API key, fully offline | CaptchaFree (Whisper local) |
| Maximum coverage | CapSolver trial → paid |
| Building custom solver | librecaptcha framework |
