# Stealth core — CloakBrowser

The base launcher is CloakBrowser: a Chromium with fingerprint patches compiled
into the binary at C++ source level (canvas, WebGL, audio, fonts, GPU, screen,
WebRTC, automation signals). It passes bot detection while exposing the standard
Playwright API. Every engine method behaves identically; only the browser
underneath differs. Set `BrowserConfig(cloaking=False)` to use plain upstream
Chromium instead.

## Why it beats playwright-stealth / undetected-chromedriver

Those inject JS or flip flags at runtime — antibot detects the patch itself, and
Chrome updates break them. CloakBrowser modifies the compiled binary, so
detection sees a real browser because it *is* one. Trade-off: the binary is
closed-source and auto-downloaded (~200MB first launch), separate from the
MIT-licensed wrapper.

## `StealthConfig` fields

| Field | Default | What it does |
|---|---|---|
| `proxy` | `None` | `http://user:pass@host:port` or `socks5://...`. Aggressive sites need **residential** — datacenter IPs are blocked by reputation regardless of fingerprint. |
| `geoip` | `False` | Match timezone + locale to the proxy exit IP. Without it, UTC + en-US through a non-US IP is a bot signal. Needs `pip install cloakbrowser[geoip]`. |
| `humanize` | `False` | Human-like mouse (Bézier), per-character typing, natural scroll. Applies to all click/fill/type calls automatically. |
| `human_preset` | `"default"` | `"default"` or `"careful"` (slower, idle micro-movements). |
| `human_config` | `None` | dict overriding individual humanize params, e.g. `{"typing_delay":100,"mistype_chance":0.05}`. |
| `fingerprint_seed` | `None` | Pin a deterministic identity (returning visitor). Same seed = same fingerprint across runs — important for reCAPTCHA v3/Enterprise scoring. |
| `timezone` | `None` | Override IANA tz (e.g. `"Asia/Jakarta"`); wins over `geoip`. |
| `stealth_args` | `True` | Keep default fingerprint patches on. |
| `auto_update` | `False` | When False, sets `CLOAKBROWSER_AUTO_UPDATE=false` so the closed-source binary doesn't update silently — recommended on a prod VPS. Update with `python -m cloakbrowser update`. |
| `extra_args` | `[]` | Raw CloakBrowser flags (below). |

## Anti-block recipe

Most blocks come from one of these, not the fingerprint:

```python
StealthConfig(
    proxy="http://user:pass@residential-proxy:port",  # residential IP
    geoip=True,
    humanize=True,
)
# plus BrowserConfig(headless=False) — some sites detect headless even with C++ patches
```

For the worst sites (DataDome, Kasada), run headed on a virtual display on Linux:

```bash
sudo apt install xvfb fonts-noto-color-emoji fonts-freefont-ttf fonts-unifont \
    fonts-ipafont-gothic fonts-wqy-zenhei fonts-tlwg-loma-otf
Xvfb :99 -screen 0 1920x1080x24 & export DISPLAY=:99
```

(Missing emoji/font packages on minimal Linux make canvas hashes Kasada/Akamai
don't recognize — a common cause of blocks after proxy + geoip are set.)

## Useful raw flags (`extra_args`)

| Flag | Use |
|---|---|
| `--fingerprint-noise=false` | Stops FingerprintJS "browser tampering" ML detection. |
| `--fingerprint-screen-width=1920` / `--fingerprint-screen-height=1080` | Match screen to viewport (prevents "virtual machine" flag). |
| `--fingerprint-gpu-vendor=...` / `--fingerprint-gpu-renderer=...` | Spoof a specific GPU. |
| `--disable-http2` | First-visit HTTP/2 challenge — warm a persistent profile once with this, then drop it. |

## reCAPTCHA v3 tips

- Use Playwright (this engine), not Puppeteer.
- Avoid `page.wait_for_timeout()` (sends CDP commands reCAPTCHA detects); use `asyncio.sleep()`.
- Prefer typing over `fill()` for forms — `humanize=True` handles this.
- Fixed `fingerprint_seed` so you look like a returning device.
- Residential proxy; spend 15+ seconds on the page before the check fires.

## Honest limits / accountability

- Stealth prevents many challenges; it does **not** solve CAPTCHAs, and no solver
  is wired in.
- The binary is closed-source, auto-downloaded from `cloakbrowser.dev`, releases
  SHA-256 + GPG/Sigstore signed. Verify if your threat model needs it; keep
  `auto_update=False` on production. Wrapper source is in the bundle if you prefer
  to build/vendor.
- Legitimate use only — the CloakBrowser BINARY-LICENSE prohibits unauthorized
  automation, credential stuffing, and account-creation abuse. The governor +
  confirm gate on signing are unchanged: a stealthier browser does not loosen them.
