# Browser Engine — usage

`scripts/browser_engine.py`. Stealth-first persistent context (CloakBrowser by
default; plain Playwright when `cloaking=False`).

## Config

```python
BrowserConfig(
    headless=False,                 # ext + new-headless handled automatically
    user_data_dir=...,              # default: $AGENT_BROWSER_PROFILE or ~/.agent/browser-profile
    extensions=[ExtensionSpec(...)],# folder / .crx / webstore (see extensions.md)
    viewport=(1280, 800),
    locale="en-US",
    channel="chrome",               # ignored when cloaking=True
    slow_mo_ms=0,
    default_timeout_ms=30000,
    cloaking=True,                  # True = CloakBrowser core; False = plain Playwright
    stealth=StealthConfig(...),     # see stealth.md (used only when cloaking=True)
    extension_cache_dir=None,       # default: $AGENT_EXT_CACHE or ~/.agent/ext-cache
    offline_extensions=False,       # True = never download from Web Store; require cache
)
```

The persistent `user_data_dir` keeps logins / wallet onboarding / sessions
across runs — treat it like sensitive data (cookies + localStorage on disk).

`cloaking` is the launcher switch. `True` (default) uses CloakBrowser's patched
binary; `False` uses upstream Chromium via Playwright (respects a site that
blocks automation, works with no binary download). Every method below is
identical across both.

## API surface

| Method | What it does |
|---|---|
| `start()` / `close()` | lifecycle (or use `async with`) |
| `.loaded` | list of `ResolvedExtension` installed this launch (path/name/version/source_kind) |
| `goto(url, wait=...)` | navigate |
| `read_text()` | visible body text — feed to agent reasoning |
| `snapshot()` | accessibility snapshot (role-based, less brittle) |
| `click_text(text, exact=)` | click element by text |
| `fill(selector, value)` | fill input |
| `screenshot(path, full_page=)` | capture |
| `discover_extensions(timeout_ms=)` | list loaded extensions |
| `find_extension(query)` | find by id or name substring |
| `wait_for_extension(query, timeout_ms=)` | poll until a named extension is up |
| `open_extension_page(ext, rel)` | open any `chrome-extension://` page |
| `open_popup(ext)` | open the extension's default popup |
| `open_options(ext)` | open the extension's options page |
| `approve_in_popup(ext, button_text)` | open popup + click a button |
| `eval_in_extension(ext, expr)` | run JS in the extension background |
| `extension_storage(ext, area="local")` | read chrome.storage.local/sync/session |
| `capture_walletconnect_uri(timeout_ms=)` | grab `wc:...` URI from the page |

## WalletConnect

`capture_walletconnect_uri()` scrapes the `wc:` URI from the dApp (href / input
value / page text). You pair it on **your own** WC signer (via `web3_connect.py`)
— not a third-party service. Signing always goes through the governor.

## Governed signing

`governed_sign(SignRequest, confirm_cb)` enforces, in order: `screen_tx` (decode
to human-readable) → `governor.authorize` (caps / slippage / kill-switch) →
operator confirm → sign. The dApp can *request* a tx; the agent *decides*. A page
can never force a signature by telling the agent to sign. `governed_sign` imports
`web3_connect.py` + `governor.py` (present in openclaw); standalone it raises a
clear error naming those modules.

## Run

```bash
pip install cloakbrowser
python -c "import asyncio, browser_engine as b; asyncio.run(b._example_webstore_extension())"
```
