#!/usr/bin/env python3
"""
X Browser — Playwright + WARP SOCKS5 + Cookie Injection
Opens X/Twitter in a real browser with credentials and proxy.

Usage:
  python3 x_browser.py              # Open X home feed
  python3 x_browser.py --url URL    # Open specific URL on X
  python3 x_browser.py --headless   # Run headless (no display)
  python3 x_browser.py --screenshot # Take screenshot and exit
"""

import asyncio
import json
import os
import sys
import argparse
from pathlib import Path

CONFIG_DIR = Path.home() / '.hermes'
COOKIES_FILE = CONFIG_DIR / 'x-cookies.json'
PROXY = os.environ.get('X_PROXY', 'socks5://127.0.0.1:40000')  # WARP SOCKS5

async def launch_x(url='https://x.com/home', headless=True, screenshot=False):
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # Create context with WARP proxy
        context = await browser.new_context(
            proxy={"server": PROXY},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='Asia/Singapore',
        )
        
        # Inject X cookies (httpOnly supported via add_cookies)
        if COOKIES_FILE.exists():
            with open(COOKIES_FILE) as f:
                cookies_data = json.load(f)
            
            browser_cookies = []
            for c in cookies_data:
                browser_cookies.append({
                    "name": c["name"],
                    "value": c["value"],
                    "domain": ".x.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                })
            
            await context.add_cookies(browser_cookies)
            print(f"✅ Injected {len(browser_cookies)} X cookies")
        else:
            print("⚠️ No cookies file found")
        
        page = await context.new_page()
        
        # Anti-detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
        """)
        
        print(f"🌐 Navigating to {url} via WARP proxy...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
        except Exception as e:
            print(f"⚠️ Navigation issue: {e}")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        await asyncio.sleep(3)
        
        # Check login status
        content = await page.content()
        logged_in = 'Happening now' not in content and 'Log in' not in content[:5000]
        
        title = await page.title()
        print(f"📄 Title: {title}")
        print(f"🔐 Logged in: {'✅ Yes' if logged_in else '❌ No'}")
        print(f"🌐 URL: {page.url}")
        
        if screenshot:
            ss_path = CONFIG_DIR / 'x-screenshot.png'
            await page.screenshot(path=str(ss_path), full_page=False)
            print(f"📸 Screenshot saved: {ss_path}")
        else:
            # Keep browser open for interaction
            print("\n✅ Browser ready. Press Ctrl+C to close.")
            try:
                # Wait indefinitely until interrupted
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
        
        await browser.close()

def main():
    parser = argparse.ArgumentParser(description='X Browser with WARP proxy')
    parser.add_argument('--url', default='https://x.com/home', help='URL to open')
    parser.add_argument('--headless', action='store_true', default=True)
    parser.add_argument('--no-headless', dest='headless', action='store_false')
    parser.add_argument('--screenshot', action='store_true', help='Take screenshot and exit')
    args = parser.parse_args()
    
    asyncio.run(launch_x(url=args.url, headless=args.headless, screenshot=args.screenshot))

if __name__ == '__main__':
    main()
