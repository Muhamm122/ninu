# Extension Control — deep dive

How the engine loads and controls browser extensions, what works, and what
genuinely doesn't (documented, not faked). Loading/installing sources (folder /
.crx / Web Store) are covered in `webstore.md`; this file is about driving them
once they're live.

## How loading works

Chromium loads extensions only when **all** hold:
1. It's Chromium (CloakBrowser core or plain Chromium — both qualify).
2. A **persistent context** is used (the engine always does this).
3. The extension is **unpacked** (a folder with `manifest.json`). The resolver
   guarantees this for every source kind.
4. It's **not classic headless**. The engine auto-injects `--headless=new` when
   `headless=True` *and* extensions are present (both launchers).

Loading flags are built for you: in plain mode the engine sets
`--disable-extensions-except` + `--load-extension`; in stealth mode CloakBrowser
sets the same from `extension_paths`. You never assemble them by hand.

```python
BrowserConfig(extensions=[
    ExtensionSpec.from_folder("~/.wallets/metamask-unpacked", "MetaMask"),
    ExtensionSpec.from_crx("~/ext/helper.crx"),
    ExtensionSpec.from_webstore("<id-or-url>"),
])
```

After launch, `b.loaded` lists what was installed (`ResolvedExtension`:
path / name / version / source_kind / source).

## Discovery (no path guessing)

`discover_extensions()` finds every loaded extension by inspecting the context's
**service workers** (MV3) and **background pages** (MV2). The id is parsed from
the `chrome-extension://<id>/...` URL; the manifest (name/version) is read by
evaluating `chrome.runtime.getManifest()` **inside the extension's own
background** — reliable, no dependence on `web_accessible_resources` or guessed
paths.

```python
exts = await b.discover_extensions()        # list[ExtensionInfo]
mm   = await b.find_extension("MetaMask")    # by name substring or exact id
mm   = await b.wait_for_extension("MetaMask")# poll until it's up (post-launch / post-install)
```

`wait_for_extension` matters when a service worker takes a beat to spin up, or
right after a fresh Web Store install.

## Driving the UI

Popup/options pages live at `chrome-extension://<id>/<file>` and are ordinary DOM
pages. The engine opens them as tabs and you drive them with normal locators:

```python
page = await b.open_popup(mm)                 # resolves manifest action.default_popup
await page.get_by_role("button", name="Next").click()

opts = await b.open_options(mm)               # options_ui.page or options_page
await b.approve_in_popup(mm, "Connect")       # popup + click in one shot ("Confirm"/"Approve"/"Sign")
```

Opening the popup as a tab is **not** clicking the toolbar icon (Playwright can't
touch browser chrome). The DOM is identical, so connect/approve/confirm flows
work. A few extensions gate on `window` size or the popup port; if one misbehaves,
drive its options page or the dApp-side prompt instead.

## Low-level: talk to the background

```python
data = await b.eval_in_extension(mm, "() => chrome.storage.local.get(null)")
await b.eval_in_extension(mm, "() => chrome.runtime.reload()")
store = await b.extension_storage(mm, area="local")   # convenience for the above
```

## What you CANNOT do (be honest with the user)

- **Toggle an installed extension on/off at runtime.** `chrome://extensions` is a
  privileged WebUI with a closed shadow DOM Playwright can't drive. Your control
  is *which* extensions load — set `BrowserConfig.extensions`.
- **Load a `.crx` directly.** It's unpacked first (handled for you).
- **Click the real toolbar icon / see native popup chrome.** Use the popup URL.
- **Auto-update a Web Store install.** It's loaded as unpacked source — re-resolve
  (bust the cache) to upgrade.

## MetaMask-style flow (end to end)

```python
cfg = BrowserConfig(
    headless=False,
    extensions=[ExtensionSpec.from_webstore("nkbihfbeogaeaoehlefnkodbefgpgknn", "MetaMask")],
    stealth=StealthConfig(humanize=True, fingerprint_seed=42069),
)
async with BrowserAgent(cfg) as b:
    mm = await b.wait_for_extension("MetaMask")
    # first run: complete onboarding/import once → persistent profile keeps it
    await b.goto("https://app.uniswap.org")
    await b.click_text("Connect")             # dApp side
    await b.approve_in_popup(mm, "Connect")    # wallet side
    # tx requested by dApp → route through governed_sign, NEVER auto-approve
```

## Boundary

This adds *control* of legitimate extensions (wallets, helpers). It does not add
an anti-detection "stealth extension" payload — stealth lives in the browser
binary (see `stealth.md`), and what you load is the operator's call and
responsibility.
