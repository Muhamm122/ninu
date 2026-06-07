# Playwright Stealth — Correct API Reference

## Correct Usage (async)
```python
from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # Import the CLASS

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox',
                  '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1280, 'height': 720},
        )
        page = await context.new_page()
        
        # Step 1: Create Stealth instance (NO positional args)
        stealth = Stealth()
        
        # Step 2: Apply stealth to page (async method)
        await stealth.apply_stealth_async(page)
        
        # Now navigate
        await page.goto('https://example.com', wait_until='networkidle')
```

## Stealth() Keyword-Only Args (all optional)
- `navigator_webdriver=True` — hide webdriver flag
- `navigator_user_agent=True` — spoof UA
- `navigator_languages=True` — spoof languages
- `navigator_platform=True` — spoof platform
- `webgl_vendor=True` — spoof WebGL
- `chrome_runtime=False` — disable chrome.runtime
- `init_scripts_only=False` — only inject init scripts

## Common Mistakes
| Wrong | Right |
|-------|-------|
| `from playwright_stealth import stealth_async` | `from playwright_stealth import Stealth` |
| `stealth_async(page)` | `Stealth().apply_stealth_async(page)` |
| `Stealth(page)` | `Stealth()` (keyword-only args) |
| `stealth.apply_stealth_sync(page)` in async | `await stealth.apply_stealth_async(page)` |

## Version Info
- `playwright_stealth` 2.0.3 (installed 2026-06-06)
- API may change with updates — test before relying on
