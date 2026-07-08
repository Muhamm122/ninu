# hCaptcha Practice Harness + Residential Proxy Pattern

## Context
This session built a reusable Playwright harness for practicing hCaptcha solving on https://7y7j.github.io/ (4 difficulty modes with different sitekeys).

## Key Pattern: Residential Proxy for Reachability
When `page.goto()` times out even at 60s on GitHub Pages / similar sites from VPS/datacenter IPs:

1. Check active residential proxies first:
   ```bash
   ~/bin/proxy list
   ~/bin/proxy get <provider-id>
   ```

2. Launch Playwright with proxy:
   ```python
   browser = await p.chromium.launch(
       proxy={
           "server": "http://p101.instantproxies.com:9188",
           "username": "2952",
           "password": "D8WHKfYnaSnV"
       }
   )
   ```

3. Combine with defensive navigation:
   - `timeout=60000`
   - 3x retry loop on `goto`
   - `page.set_default_navigation_timeout(60000)`

## hCaptcha Sitekeys from the Practice Site
| Mode | Sitekey | Notes |
|------|---------|-------|
| 友好模式 | 345e6d03-eb0c-4911-a63c-05a819bfdc09 | Public test key (always passes) |
| 还可以模式 | a9b82eff-27fe-496c-9238-177b19aaaa7f | Real challenge |
| 困难模式 | 190f1408-3335-43eb-81dd-94f786285b63 | Hardest real challenge |
| Auto | 50f7b453-1b72-42f1-9e8e-ca778728ca6a | Browser auto mode |

## Lesson
Residential proxies are not only for anti-bot evasion — they are also required for basic reachability when the target (GitHub Pages, certain CDNs) has poor connectivity from datacenter ranges. Always test proxy before declaring "site unreachable".