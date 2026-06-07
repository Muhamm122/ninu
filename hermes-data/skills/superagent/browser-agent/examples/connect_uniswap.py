"""
connect_uniswap.py — end-to-end scenario.

Flow:
  1. Install MetaMask from the Chrome Web Store (cached after the first run).
  2. Import a seed phrase ONCE (the persistent profile keeps the wallet after).
  3. Connect to Uniswap behind Cloudflare using the stealth core.

The scenario STOPS at "connected". It never signs or sends anything — real
transactions must go through `governed_sign` + the confirm gate.

──────────────────────────────────────────────────────────────────────────────
SECRETS / SAFETY  (read this)
  • The seed is read from env `MM_SEED` (12/24 words) or a file `MM_SEED_FILE`.
    NEVER hardcode it in the script.
  • The unlock password is read from env `MM_PASSWORD`. If unset, a default dev
    password is used and a loud warning is printed — set your own for anything
    real.
  • The persistent profile dir ($AGENT_BROWSER_PROFILE) stores the *unlocked*
    wallet on disk. Treat that dir as a secret. Use a wallet you control —
    ideally a dedicated burner for automation.
  • Aggressive Cloudflare often needs a RESIDENTIAL proxy — set `MM_PROXY`.
──────────────────────────────────────────────────────────────────────────────

MetaMask's onboarding DOM drifts between versions. Selectors below use MetaMask's
`data-testid`s with text fallbacks, and every step is tolerant (skips if a screen
isn't shown). If a step misbehaves on your MetaMask build, adjust the selector
lists in `_MM` — the engine primitives (`open_popup`, `approve_in_popup`) stay
the same.

Run:
    export MM_SEED="word1 word2 ... word12"
    export MM_PASSWORD="a-strong-password"
    export AGENT_BROWSER_PROFILE=~/.agent/uniswap-profile
    # optional but recommended for Cloudflare:
    export MM_PROXY="http://user:pass@residential-host:port"
    python examples/connect_uniswap.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# make scripts/ importable no matter the CWD
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from browser_engine import BrowserAgent, BrowserConfig, StealthConfig, ExtensionSpec  # noqa: E402

METAMASK_ID = "nkbihfbeogaeaoehlefnkodbefgpgknn"
DEFAULT_DEV_PASSWORD = "Automation-Dev-Pw-Change-Me-1!"

# MetaMask selectors (data-testid first, text fallback). Tolerant by design.
_MM = {
    "terms_checkbox": ['[data-testid="onboarding-terms-checkbox"]'],
    "import_wallet": [
        '[data-testid="onboarding-import-wallet"]',
        'text=Import an existing wallet',
        'text=I have an existing wallet',
    ],
    "metrics_dismiss": [
        '[data-testid="metametrics-no-thanks"]',
        '[data-testid="metametrics-i-agree"]',
        'text=No thanks',
        'text=I agree',
    ],
    "srp_word": '[data-testid="import-srp__srp-word-{i}"]',  # per-word inputs
    "srp_paste": ['[data-testid="import-srp__srp-note"]', 'textarea'],
    "srp_confirm": [
        '[data-testid="import-srp-confirm"]',
        'button:has-text("Confirm Secret Recovery Phrase")',
        'button:has-text("Import")',
    ],
    "pw_new": ['[data-testid="create-password-new"]', 'input[autocomplete="new-password"]'],
    "pw_confirm": ['[data-testid="create-password-confirm"]'],
    "pw_terms": ['[data-testid="create-password-terms"]'],
    "pw_import": [
        '[data-testid="create-password-import"]',
        'button:has-text("Import my wallet")',
        'button:has-text("Create")',
    ],
    "done": [
        '[data-testid="onboarding-complete-done"]',
        'button:has-text("Done")',
        'button:has-text("Got it")',
    ],
    "pin_next": ['[data-testid="pin-extension-next"]', 'button:has-text("Next")'],
    "pin_done": ['[data-testid="pin-extension-done"]', 'button:has-text("Done")'],
    "unlock_pw": ['[data-testid="unlock-password"]', 'input[type="password"]'],
    "unlock_submit": ['[data-testid="unlock-submit"]', 'button:has-text("Unlock")'],
    "already_in": ['[data-testid="account-menu-icon"]', '[data-testid="app-header-logo"]'],
}


# ───────────────────────── tolerant DOM helpers ─────────────────────────


async def _click_first(page, selectors, timeout_ms=4000) -> bool:
    """Click the first selector that appears within the budget. False if none."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout_ms)
            await loc.click()
            return True
        except Exception:
            continue
    return False


async def _fill_first(page, selectors, value, timeout_ms=4000) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=timeout_ms)
            await loc.fill(value)
            return True
        except Exception:
            continue
    return False


async def _present(page, selectors, timeout_ms=2500) -> bool:
    for sel in selectors:
        try:
            await page.locator(sel).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


# ───────────────────────── MetaMask onboarding ─────────────────────────


def _load_seed() -> list[str]:
    seed = os.environ.get("MM_SEED", "").strip()
    if not seed and os.environ.get("MM_SEED_FILE"):
        seed = Path(os.environ["MM_SEED_FILE"]).expanduser().read_text().strip()
    if not seed:
        raise SystemExit(
            "MM_SEED (atau MM_SEED_FILE) belum di-set. Pakai wallet yang LO kontrol "
            "(idealnya burner). Seed jangan pernah di-hardcode."
        )
    words = seed.split()
    if len(words) not in (12, 24):
        raise SystemExit(f"seed harus 12/24 kata, dapet {len(words)}.")
    return words


def _password() -> str:
    pw = os.environ.get("MM_PASSWORD")
    if not pw:
        print("⚠️  MM_PASSWORD belum di-set — pakai default dev. Set sendiri buat yang serius.")
        return DEFAULT_DEV_PASSWORD
    return pw


async def _open_mm_home(b: BrowserAgent, mm) -> "object":
    """Open MetaMask's home/onboarding page as a tab."""
    # try the onboarding route first, fall back to home.html
    for rel in ("home.html#onboarding/welcome", "home.html"):
        try:
            return await b.open_extension_page(mm, rel)
        except Exception:
            continue
    return await b.open_popup(mm)


async def ensure_metamask_ready(b: BrowserAgent, mm) -> None:
    """
    Idempotent: import on first run, unlock on later runs, no-op if already open.
    """
    page = await _open_mm_home(b, mm)
    await asyncio.sleep(2)  # native sleep — wait_for_timeout sends CDP signals

    if await _present(page, _MM["already_in"], timeout_ms=2000):
        print("   MetaMask sudah ke-unlock / siap.")
        await page.close()
        return

    if await _present(page, _MM["unlock_pw"], timeout_ms=2000):
        print("   MetaMask ke-lock → unlock dengan MM_PASSWORD.")
        await _fill_first(page, _MM["unlock_pw"], _password())
        await _click_first(page, _MM["unlock_submit"])
        await asyncio.sleep(2)
        await page.close()
        return

    print("   First run → import seed (sekali aja, profil persisten nyimpen).")
    await _import_seed_flow(page)
    await page.close()


async def _import_seed_flow(page) -> None:
    words = _load_seed()
    pw = _password()

    # 1) welcome: agree to terms, choose import
    await _click_first(page, _MM["terms_checkbox"], timeout_ms=6000)
    await _click_first(page, _MM["import_wallet"], timeout_ms=6000)
    # 2) metametrics consent screen (either button moves on)
    await _click_first(page, _MM["metrics_dismiss"], timeout_ms=5000)
    await asyncio.sleep(1)

    # 3) SRP entry — try per-word inputs, fall back to a paste field
    filled = False
    try:
        first = page.locator(_MM["srp_word"].format(i=0)).first
        await first.wait_for(state="visible", timeout=5000)
        for i, w in enumerate(words):
            await page.locator(_MM["srp_word"].format(i=i)).first.fill(w)
        filled = True
    except Exception:
        filled = await _fill_first(page, _MM["srp_paste"], " ".join(words), timeout_ms=4000)
    if not filled:
        raise RuntimeError("gak nemu field SRP — cek versi MetaMask, sesuaikan _MM['srp_*'].")
    await _click_first(page, _MM["srp_confirm"], timeout_ms=6000)
    await asyncio.sleep(1)

    # 4) create local password
    await _fill_first(page, _MM["pw_new"], pw, timeout_ms=6000)
    await _fill_first(page, _MM["pw_confirm"], pw)
    await _click_first(page, _MM["pw_terms"], timeout_ms=3000)
    await _click_first(page, _MM["pw_import"], timeout_ms=6000)
    await asyncio.sleep(2)

    # 5) completion / pin screens (all optional)
    await _click_first(page, _MM["done"], timeout_ms=6000)
    await _click_first(page, _MM["pin_next"], timeout_ms=4000)
    await _click_first(page, _MM["pin_done"], timeout_ms=4000)
    print("   ✅ seed imported.")


# ───────────────────────── Uniswap connect ─────────────────────────


async def connect_uniswap(b: BrowserAgent, mm) -> None:
    print("3) Buka Uniswap (lewat stealth core, tembus Cloudflare)...")
    await b.goto("https://app.uniswap.org", wait="domcontentloaded")
    await asyncio.sleep(4)  # let Cloudflare's check settle if shown

    page = b.page
    # open the connect modal
    clicked = await _click_first(
        page,
        ['[data-testid="navbar-connect-wallet"]', 'button:has-text("Connect")',
         'text=Connect wallet'],
        timeout_ms=15000,
    )
    if not clicked:
        print("   ⚠️ tombol Connect gak ketemu — mungkin masih di challenge Cloudflare,"
              " coba MM_PROXY residential + headed.")
        return

    # pick MetaMask in the modal
    await _click_first(
        page,
        ['[data-testid="wallet-option-METAMASK"]',
         '[data-testid="wallet-option-injected"]',
         'text=MetaMask'],
        timeout_ms=8000,
    )
    await asyncio.sleep(2)

    # drive the MetaMask approval popup (Connect → Next → Confirm, whichever shows)
    print("   Approve di MetaMask...")
    approved = False
    for rel in ("notification.html", "home.html"):
        try:
            mm_page = await b.open_extension_page(mm, rel)
        except Exception:
            continue
        await asyncio.sleep(1)
        for label in ("Next", "Connect", "Confirm", "Approve"):
            if await _click_first(mm_page, [f'button:has-text("{label}")'], timeout_ms=2500):
                approved = True
        await mm_page.close()
        if approved:
            break

    if approved:
        print("   ✅ connected (atau request approve terkirim).")
    else:
        print("   ⚠️ gak nemu tombol approve di MetaMask — popup connect mungkin"
              " beda route di versi ini; pakai b.approve_in_popup(mm, 'Connect') manual.")


# ───────────────────────── main ─────────────────────────


async def main() -> None:
    proxy = os.environ.get("MM_PROXY") or None
    cfg = BrowserConfig(
        headless=False,  # headed = best vs Cloudflare; extensions need non-classic-headless anyway
        extensions=[ExtensionSpec.from_webstore(METAMASK_ID, name="MetaMask")],
        stealth=StealthConfig(
            proxy=proxy,
            geoip=bool(proxy),     # match tz/locale to the proxy exit IP
            humanize=True,
            fingerprint_seed=42069,  # consistent identity across runs
        ),
    )

    async with BrowserAgent(cfg) as b:
        print("1) MetaMask terpasang dari Web Store:")
        for r in b.loaded:
            print(f"   {r.name} v{r.version} [{r.source_kind}] -> {r.path}")

        mm = await b.wait_for_extension("MetaMask", timeout_ms=30000)

        print("2) Pastikan wallet siap (import sekali / unlock)...")
        await ensure_metamask_ready(b, mm)

        await connect_uniswap(b, mm)

        print("\nSelesai. Berhenti di 'connected' — tidak ada signing/tx. "
              "Tx asli HARUS lewat governed_sign + confirm gate.")
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
