import os
import time
import requests
import cloudscraper
from twocaptcha import TwoCaptcha
from dotenv import load_dotenv

load_dotenv()

API_KEY_2CAPTCHA = os.getenv("TWOCAPTCHA_API_KEY")
SCTG_API_KEY = os.getenv("SCTG_API_KEY")  # SCTG captcha solver (2captcha-compatible)
SCTG_ENDPOINT = os.getenv("SCTG_ENDPOINT", "https://sctg.xyz")
PROXY_URL = os.getenv("PROXY_URL")

# Priority: SCTG > 2captcha
_ACTIVE_SOLVER_KEY = SCTG_API_KEY or API_KEY_2CAPTCHA
_ACTIVE_SOLVER_URL = SCTG_ENDPOINT if SCTG_API_KEY else "https://2captcha.com"

# ── 1. CLOUDFLARE BYPASS ──

def cf_get(url, headers=None, use_proxy=False):
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    proxies = _build_proxies() if use_proxy else None
    resp = scraper.get(url, headers=headers or {}, proxies=proxies, timeout=30)
    resp.raise_for_status()
    return resp

def cf_post(url, data=None, json=None, headers=None, use_proxy=False):
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    proxies = _build_proxies() if use_proxy else None
    resp = scraper.post(url, data=data, json=json, headers=headers or {}, proxies=proxies, timeout=30)
    resp.raise_for_status()
    return resp

# ── 2. 2CAPTCHA SOLVER ──

# Use SCTG endpoint if available, else 2captcha
# SCTG is 2captcha-compatible — just change the server URL
solver = TwoCaptcha(_ACTIVE_SOLVER_KEY, server=_ACTIVE_SOLVER_URL.replace("https://","").rstrip("/")) if _ACTIVE_SOLVER_KEY else None

def solve_recaptcha_v2(site_key, page_url):
    if not solver:
        raise ValueError("TWOCAPTCHA_API_KEY not set")
    result = solver.recaptcha(sitekey=site_key, url=page_url)
    return result["code"]

def solve_recaptcha_v3(site_key, page_url, action="verify", min_score=0.7):
    if not solver:
        raise ValueError("TWOCAPTCHA_API_KEY not set")
    result = solver.recaptcha(sitekey=site_key, url=page_url, version="v3", action=action, score=min_score)
    return result["code"]

def solve_hcaptcha(site_key, page_url):
    if not solver:
        raise ValueError("TWOCAPTCHA_API_KEY not set")
    result = solver.hcaptcha(sitekey=site_key, url=page_url)
    return result["code"]

def solve_turnstile(site_key, page_url):
    if not solver:
        raise ValueError("TWOCAPTCHA_API_KEY not set")
    result = solver.turnstile(sitekey=site_key, url=page_url)
    return result["code"]

def solve_image_captcha(image_path=None, image_url=None):
    if not solver:
        raise ValueError("TWOCAPTCHA_API_KEY not set")
    if image_path:
        result = solver.normal(image_path)
    elif image_url:
        result = solver.normal(image_url)
    else:
        raise ValueError("Need image_path or image_url")
    return result["code"]

# ── 3. PROXY HELPER ──

def _build_proxies():
    if not PROXY_URL:
        raise ValueError("PROXY_URL not set in .env")
    return {"http": PROXY_URL, "https": PROXY_URL}

def requests_with_proxy(method, url, **kwargs):
    kwargs["proxies"] = _build_proxies()
    kwargs.setdefault("timeout", 30)
    func = getattr(requests, method.lower())
    return func(url, **kwargs)

def check_proxy_ip():
    resp = requests_with_proxy("get", "https://api.ipify.org?format=json")
    return resp.json()["ip"]

# ── 4. PLAYWRIGHT STEALTH ──

async def playwright_stealth_get(url, wait_selector=None, use_proxy=False):
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async

    proxy_config = None
    if use_proxy and PROXY_URL:
        proxy_config = {"server": PROXY_URL}
        if "@" in PROXY_URL:
            creds = PROXY_URL.split("@")[0].split("//")[1]
            user, password = creds.split(":")
            host = PROXY_URL.split("@")[1]
            scheme = PROXY_URL.split("://")[0]
            proxy_config = {"server": f"{scheme}://{host}", "username": user, "password": password}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context(
            proxy=proxy_config,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        await stealth_async(page)
        await page.goto(url, wait_until="networkidle", timeout=60000)
        if wait_selector:
            await page.wait_for_selector(wait_selector, timeout=30000)
        content = await page.content()
        await browser.close()
        return content
