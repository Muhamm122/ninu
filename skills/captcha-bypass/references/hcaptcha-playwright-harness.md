# hCaptcha Practice Harness with Playwright (from 7y7j.github.io session)

## Context
Practice site: https://7y7j.github.io/
Contains 4 hCaptcha widgets with increasing difficulty using these sitekeys:
- Mode 1 (友好): 345e6d03-eb0c-4911-a63c-05a819bfdc09 (public test key — always passes)
- Mode 2 (还可以): a9b82eff-27fe-496c-9238-177b19aaaa7f
- Mode 3 (困难): 190f1408-3335-43eb-81dd-94f786285b63
- Mode 4 (Auto): 50f7b453-1b72-42f1-9e8e-ca778728ca6a

## Key Technique: Reliable Navigation on Slow GitHub Pages

### Problem
`page.goto(url, wait_until="domcontentloaded")` frequently times out (30s default) when running from VPS against GitHub Pages.

### Solution (verified working)
```python
# 1. Set page-level defaults early
await page.set_default_navigation_timeout(60000)
await page.set_default_timeout(30000)

# 2. Use explicit timeout + retry loop in navigation
for attempt in range(3):
    try:
        await page.goto(SITE, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)
        break
    except Exception as e:
        if attempt == 2:
            raise
        await page.wait_for_timeout(3000)
```

### Why it works
- GitHub Pages can be slow from certain VPS regions
- hCaptcha widget loading adds extra latency
- The combination of higher timeout + retry prevents flakiness without making the whole run hang forever

## Widget Interaction Pattern
- Each `div.h-captcha[data-sitekey="..."]` renders its own iframe
- Iframes appear in document order matching the modes (0-indexed)
- Checkbox click target inside iframe: `#checkbox`
- After clicking, check for `challenge` frame to detect image challenge vs immediate token

## When to Use This Harness
- Learning hCaptcha solving flow
- Testing vision-based solvers
- Building local practice before moving to real targets
- Debugging timeout/retry issues in browser automation against slow hosts

## Related Files
- `scripts/practice.py` — the runnable harness (contains the timeout + retry pattern above)