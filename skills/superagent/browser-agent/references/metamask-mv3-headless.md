# MetaMask MV3 Headless Automation — Detailed Notes

## Problem Statement
Automating MetaMask MV3 wallet setup (import/create) in headless CloakBrowser fails because:
1. MetaMask's SPA doesn't render in headless mode (loading spinner forever)
2. LavaMoat scuttling mode blocks property access on globalThis
3. Popup pages crash with TargetClosedError
4. DOM queries return 0 results (buttons, inputs all empty)

## Confirmed Working (2026-06-08)

### Service Worker Access
```python
from cloakbrowser import launch_persistent_context_async

ctx = await launch_persistent_context_async(
    user_data_dir="~/.cloakbrowser/mm_profile",
    headless=True,
    extension_paths=["~/.wallets/metamask-unpacked"],
    viewport={"width": 1280, "height": 900},
    args=["--headless=new"],
)
await asyncio.sleep(5)

workers = ctx.service_workers
w = workers[0]

kc = await w.evaluate("chrome.storage.local.get('KeyringController')")
# Returns: {"KeyringController": {}} on fresh profile
```

### Storage Structure
Key controllers:
- `KeyringController`: `{vault, keyrings[], isUnlocked}` — empty on fresh profile
- `OnboardingController`: `{completedOnboarding, firstTimeFlowType, seedPhraseBackedUp}`
- `PreferencesController`: `{forgottenPassword, currentLocale, ...}`

### Marking Onboarding Complete
```python
await w.evaluate("""
(async () => {
    const oc = await chrome.storage.local.get('OnboardingController');
    const o = oc.OnboardingController || {};
    o.completedOnboarding = true;
    o.firstTimeFlowType = 'import';
    o.seedPhraseBackedUp = true;
    await chrome.storage.local.set({OnboardingController: o});
})()
""")
```

## Confirmed NOT Working

| Approach | Error |
|----------|-------|
| `page.goto("chrome-extension://<id>/popup.html")` | TargetClosedError |
| `page.query_selector_all("button")` on MM page | Returns [] |
| `page.evaluate("document.body.innerText")` | Returns "" |
| `page.screenshot()` after MM page loads | TargetClosedError |
| Finding webpack require in SW | Not found |
| Creating valid vault from Python | Format unknown |

## Extension Details

| Field | Value |
|-------|-------|
| Web Store ID | `nkbihfbeogaeaoehlefnkodbefgpgknn` |
| Extension ID | `lcpmajdcaiedieelpghcmgnoonbeokgg` |
| Version | 13.34.0.0 |
| Manifest | MV3 (service worker) |

## Recommended Approaches

1. **Non-headless with Xvfb** (most reliable): `xvfb-run python3 mm_import.py`
2. **Manual user onboarding**: User completes onboarding, profile persists
3. **Pre-computed vault injection** (experimental): Risk of format mismatch

## Files
- Extension: `~/.wallets/metamask-unpacked/`
- Trading profile: `~/.cloakbrowser/mm_trading/`
- Solana wallets (NOT MetaMask): `~/.hermes/sol-wallets.json`
- EVM vault (password lost): `~/.hermes/wallets.enc`
