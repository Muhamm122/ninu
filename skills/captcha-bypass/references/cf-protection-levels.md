# CF Protection Levels & Bypass Strategy (2026-07-08)

Not all CF protections are equal. Classify before choosing a bypass method.

## Levels

| Level | Type | cloudscraper (no proxy) | cloudscraper + proxy | Playwright + session | Example sites |
|-------|------|:---:|:---:|:---:|:---:|
| 🟢 **Light** | Basic CDN, no challenge | ✅ 100% | ✅ 100% | ✅ | `cloudflare.com`, `nousresearch.com`, `blockchain.com` |
| 🟡 **Medium** | JS challenge, no captcha | ✅ 90% | ✅ 90% | ✅ | `tiktok.com`, `discord.com`, `skripsi.muham.dev` |
| 🔴 **Heavy** | JS + Captcha (Turnstile/hCaptcha) | ❌ 30% | ❌ 10% | ✅ w/ 2captcha | `namecheap.com`, `reddit.com` |
| ⚫ **Blocked** | Datacenter IP 403 | ❌ 0% | ❌ 0% | ❌ (need residential) | All from VPS |

## Key Insight (2026-07-08)

- `cloudscraper` **WITHOUT proxy** actually bypasses more CF sites than with proxy — because the proxy IP is often blacklisted.
- Using the **VPS's own IP** (no proxy) → works for Light/Medium levels  
- Using **residential proxy** → works for Heavy level but needs valid cookies/session
- `https://challenges.cloudflare.com` is **NOT a real Turnstile challenge** — it's an info page about Turnstile, not a captcha to solve

## Recommendations

- **Light/Medium**: use `cloudscraper` directly (no proxy) — fast, reliable
- **Heavy**: use `cloudscraper` + `2captcha` or `Playwright` + pre-loaded cookies
- **Blocked**: switch to different VPS IP or use Tor/exit nodes