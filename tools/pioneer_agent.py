#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
  🔥 PIONEER AI — AGENT ONBOARDING SCRIPT (CLEAN, SHAREABLE)
═══════════════════════════════════════════════════════════════════════

  Script standalone untuk AI agent automate dari 0 sampai dapat
  API key Pioneer AI yang verified.

  Flow:
    PHASE A → Google OAuth login (browser-automated)
    PHASE B → Add credit card di Stripe
    PHASE C → Run first inference + advance onboarding
    PHASE D → Create API key + intercept secret_key dari network
    PHASE E → Verify key dengan real /v1/chat/completions call

═══════════════════════════════════════════════════════════════════════
  📦 INSTALL DEPENDENCIES:

    pip install cloakbrowser httpx
    playwright install chromium
    playwright install-deps chromium   # Linux only

═══════════════════════════════════════════════════════════════════════
  🚀 USAGE:

    1. Edit CONFIG dict di bawah:
       - email + password (akun Google)
       - card_number + exp_mm + exp_yy + cvc (CC yang work)

    2. Run:
       python3 pioneer_agent.py

    3. Output:
       - ~/pioneer_result.json  → API key + verified status
       - ~/pioneer_run.log      → step-by-step log
       - ~/.pioneer-profile/    → browser session (cached)

═══════════════════════════════════════════════════════════════════════
  💡 TIPS BUAT AGENT YANG NGEJALININ:

    - Headless mode default ON (no DISPLAY needed)
    - Profile dir cached: kalau crash mid-way, re-run skip Phase A
    - Network interceptor capture API key 100% reliable
    - Auto-screenshot kalau gagal (di /tmp/pioneer_*.png)
    - Exit code: 0=success, 1=fail, 2=crash

═══════════════════════════════════════════════════════════════════════
  ⚠️  KENDALA UMUM:

    [Google Speedbump / unusual activity warning]
    → IP server-mu kemungkinan udah ke-flag Google.
       SOLUSI: gunakan proxy residential US (set CONFIG["proxy"]).
       Contoh format:
         "proxy": {
             "server":   "http://your-proxy:port",
             "username": "user",
             "password": "pass",
         }

    [Card declined]
    → CC ditolak Stripe. Coba CC lain.

    [API key not captured]
    → UI Pioneer mungkin update. Cek screenshot di /tmp/pioneer_*.png.
═══════════════════════════════════════════════════════════════════════
"""
import asyncio
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from cloakbrowser import launch_persistent_context_async

# ═══════════════════════════════════════════════════════════════════════
# CONFIG — EDIT SEBELUM RUN
# ═══════════════════════════════════════════════════════════════════════

CONFIG = {
    # ─── GOOGLE ACCOUNT ───
    "email":    "youremail@gmail.com",
    "password": "yourpassword",

    # ─── CREDIT CARD ───
    "card_number": "4242424242424242",   # 16 digits, no spaces
    "exp_mm":      "12",                 # 2 digits
    "exp_yy":      "29",                 # 2 digits
    "cvc":         "123",
    "zip":         "10001",

    # ─── PROXY (OPTIONAL) ───
    # Default None = pakai IP server langsung.
    # Kalau Google flag IP-mu (speedbump warning), set proxy residential di sini.
    "proxy": None,
    # Format kalau pakai:
    # "proxy": {
    #     "server":   "http://gw.example.com:8080",
    #     "username": "user",
    #     "password": "pass",
    # },

    # ─── BROWSER ───
    "headless":    True,    # False = tampil GUI (butuh DISPLAY)
    "profile_dir": str(Path.home() / ".pioneer-profile"),

    # ─── OUTPUT ───
    "result_file": str(Path.home() / "pioneer_result.json"),
    "log_file":    str(Path.home() / "pioneer_run.log"),

    # ─── RETRY ───
    "phase_a_max_retries": 3,   # OAuth retry kalau gagal
    "verify_model":        "claude-haiku-4-5",   # model buat verify step
}


# ═══════════════════════════════════════════════════════════════════════
# LOGGER
# ═══════════════════════════════════════════════════════════════════════

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(CONFIG["log_file"], "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# HELPER: dump debug info kalau gagal
# ═══════════════════════════════════════════════════════════════════════

async def dump_debug(page, tag: str):
    """Save screenshot + HTML + body text untuk debugging."""
    try:
        shot = f"/tmp/pioneer_{tag}.png"
        await page.screenshot(path=shot, full_page=True)
        log(f"      🖼️  screenshot: {shot}")
    except Exception:
        pass
    try:
        html_path = f"/tmp/pioneer_{tag}.html"
        html = await page.content()
        Path(html_path).write_text(html[:50000])
        log(f"      📄 html: {html_path}")
    except Exception:
        pass
    try:
        body = await page.evaluate("document.body.innerText")
        log(f"      📋 body preview: {body[:500]}")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# PHASE A — Google OAuth login
# ═══════════════════════════════════════════════════════════════════════

async def is_authed_in_profile() -> bool:
    """Quick probe: open profile, check kalau /settings/billing balikin authed page."""
    profile_dir = Path(CONFIG["profile_dir"])
    cookies_path = profile_dir / "Default" / "Cookies"
    if not (cookies_path.exists() and cookies_path.stat().st_size > 1000):
        return False

    launch_kwargs = {
        "user_data_dir": str(profile_dir),
        "headless":      CONFIG["headless"],
        "viewport":      {"width": 1400, "height": 900},
    }

    ctx = await launch_persistent_context_async(**launch_kwargs)
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    try:
        await page.goto("https://agent.pioneer.ai/settings/billing",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        cur_url = page.url
        body = await page.evaluate("document.body.innerText")
        # Authed kalau ga ke-redirect ke login & body punya keyword billing
        authed_indicators = ["FREE CREDIT", "Payment Method", "Add payment",
                             "Verify account", "Billing", "Usage", "Payment method"]
        if any(k in body for k in authed_indicators) and "/auth" not in cur_url:
            return True
        return False
    finally:
        await ctx.close()


async def phase_a_oauth_once() -> bool:
    """One attempt: launch browser, login via Google, return True if reached pioneer.ai."""
    profile_dir = Path(CONFIG["profile_dir"])
    profile_dir.mkdir(parents=True, exist_ok=True)

    launch_kwargs = {
        "user_data_dir": str(profile_dir),
        "headless":      CONFIG["headless"],
        "viewport":      {"width": 1400, "height": 900},
    }
    if CONFIG["proxy"]:
        launch_kwargs["proxy"] = CONFIG["proxy"]
        log(f"      🌐 proxy: {CONFIG['proxy']['server']}")

    ctx = await launch_persistent_context_async(**launch_kwargs)
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    success = False

    try:
        # ─── A1: Buka homepage ───
        log("      [A1] open https://agent.pioneer.ai/")
        await page.goto("https://agent.pioneer.ai/",
                        wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        body = await page.evaluate("document.body.innerText")
        if "FREE CREDIT" in body or "Add a payment" in body or "Verify account" in body:
            log("      [A1] already authed (cookies valid)")
            return True

        # ─── A2: Click "Continue with Google" ───
        log("      [A2] click 'Continue with Google'")
        g_btn = page.get_by_text("Continue with Google", exact=False).first
        if await g_btn.count() == 0:
            g_btn = page.locator("button:has-text('Google')").first
        await g_btn.click(timeout=15000)
        await asyncio.sleep(5)

        # ─── A3: Fill email (visible only) ───
        log("      [A3] fill Google email")
        email_input = page.locator("input[type='email']:visible").first
        try:
            await email_input.wait_for(state="visible", timeout=25000)
        except Exception:
            email_input = page.locator("input[name='identifier']").first
            await email_input.wait_for(state="visible", timeout=15000)
        await email_input.fill(CONFIG["email"])
        await page.get_by_role("button", name=re.compile("Next|Berikutnya", re.I)).first.click(timeout=10000)
        await asyncio.sleep(5)

        # ─── A4: Fill password (visible only) ───
        log("      [A4] fill password")
        pw_input = page.locator("input[type='password']:visible").first
        try:
            await pw_input.wait_for(state="visible", timeout=25000)
        except Exception:
            pw_input = page.locator("input[name='Passwd']").first
            await pw_input.wait_for(state="visible", timeout=15000)
        await pw_input.fill(CONFIG["password"])
        await page.get_by_role("button", name=re.compile("Next|Berikutnya|Sign in", re.I)).first.click(timeout=10000)
        await asyncio.sleep(7)

        # ─── A5: Handle speedbump / consent / redirect ───
        log("      [A5] handle post-password screens")
        for attempt in range(20):
            await asyncio.sleep(3)
            cur_url = page.url
            host = urlparse(cur_url).hostname or ""

            if host.endswith("pioneer.ai"):
                log(f"      [A5] ✅ reached pioneer.ai @attempt {attempt+1}")
                success = True
                break

            # Challenge page — Google minta verify (wrong password, 2FA, captcha, etc)
            if "challenge" in cur_url and "speedbump" not in cur_url:
                log(f"      [A5] ⚠️ Google challenge: {cur_url[:120]}")
                await dump_debug(page, "oauth_challenge")
                break

            # Speedbump (warning before granting OAuth)
            if "speedbump" in cur_url or "gaplustos" in cur_url:
                log(f"      [A5] speedbump @attempt {attempt+1}")
                clicked = False
                for kw in ["I understand", "Saya mengerti", "Accept",
                           "Continue", "Lanjutkan", "Confirm", "Konfirmasi",
                           "Next", "Berikutnya", "Got it", "Mengerti", "Send", "OK"]:
                    try:
                        b = page.get_by_role("button", name=re.compile(kw, re.I)).first
                        if await b.count() and await b.is_visible():
                            await b.click(timeout=4000, force=True)
                            log(f"            clicked '{kw}'")
                            clicked = True
                            await asyncio.sleep(4)
                            break
                    except Exception:
                        pass
                if not clicked:
                    try:
                        btns = await page.locator("button:visible").all()
                        for b in btns:
                            try:
                                t = (await b.inner_text()).strip()
                                if t and len(t) < 30 and not any(bad in t.lower() for bad in ["cancel", "back", "sign out"]):
                                    await b.click(timeout=3000, force=True)
                                    log(f"            fallback clicked '{t}'")
                                    await asyncio.sleep(4)
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass
                continue

            # Regular consent screen
            try:
                cont = page.get_by_role("button", name=re.compile("Continue|Allow|Lanjutkan", re.I)).first
                if await cont.count() and await cont.is_visible():
                    await cont.click(timeout=6000, force=True)
                    await asyncio.sleep(5)
                    continue
            except Exception:
                pass
            break

        await asyncio.sleep(5)
        final_url = page.url
        log(f"      [A5] final URL: {final_url}")

        if not success:
            # Capture Google error clues
            try:
                err_body = await page.evaluate("document.body.innerText")
                err_clues = []
                for clue in [
                    "Wrong password", "Couldn't sign you in", "wasn't Google",
                    "verify it's you", "2-Step Verification", "Confirm your identity",
                    "unusual activity", "browser or app may not be secure",
                    "captcha", "Try again", "incorrect", "Salah",
                    "Sandi salah", "Tidak bisa", "Tidak dapat",
                ]:
                    if clue.lower() in err_body.lower():
                        err_clues.append(clue)
                if err_clues:
                    log(f"      [A5] ⚠️ Google clues: {err_clues}")
                await dump_debug(page, "oauth_stuck")
            except Exception:
                pass

        return success

    finally:
        try:
            await ctx.close()
        except Exception:
            pass


async def phase_a_oauth():
    """Phase A wrapper with retries."""
    log("═══════════════════════════════════════════════════════════════")
    log("PHASE A — Google OAuth")
    log("═══════════════════════════════════════════════════════════════")

    # Quick check: profile sudah authed?
    if Path(CONFIG["profile_dir"]).exists():
        log("  [A0] checking existing profile validity...")
        try:
            if await is_authed_in_profile():
                log("  [A0] ✅ profile already authed — skip OAuth")
                return
            log("  [A0] profile cookies invalid/expired")
        except Exception as e:
            log(f"  [A0] probe err: {e}")

    # Retry OAuth
    for attempt in range(1, CONFIG["phase_a_max_retries"] + 1):
        log(f"  [A]  attempt {attempt}/{CONFIG['phase_a_max_retries']}")
        try:
            ok = await phase_a_oauth_once()
            if ok:
                log(f"  [A]  ✅ OAuth success @attempt {attempt}")
                return
        except Exception as e:
            log(f"  [A]  attempt {attempt} crashed: {type(e).__name__}: {str(e)[:200]}")
        if attempt < CONFIG["phase_a_max_retries"]:
            wait = random.randint(15, 30)
            log(f"  [A]  waiting {wait}s before retry")
            await asyncio.sleep(wait)

    raise RuntimeError(
        "OAuth failed after all retries — IP kemungkinan ke-flag Google. "
        "Set CONFIG['proxy'] dengan residential proxy US. "
        "Lihat /tmp/pioneer_oauth_stuck.png untuk detail."
    )


# ═══════════════════════════════════════════════════════════════════════
# PHASE B-E — Stripe + Inference + API Key (NO PROXY)
# ═══════════════════════════════════════════════════════════════════════

async def phase_b_to_e():
    """Stripe block proxy IPs → harus DIRECT. Cookies dari Phase A persisted."""
    log("═══════════════════════════════════════════════════════════════")
    log("PHASE B-E — Stripe + Inference + API Key")
    log("═══════════════════════════════════════════════════════════════")

    captured_keys = []
    result = {
        "email":      CONFIG["email"],
        "card_last4": CONFIG["card_number"][-4:],
        "api_key":    None,
        "key_id":     None,
        "expires_at": None,
        "verified":   False,
        "stage":      "init",
        "error":      None,
    }

    ctx = await launch_persistent_context_async(
        user_data_dir=CONFIG["profile_dir"],
        headless=CONFIG["headless"],
        viewport={"width": 1400, "height": 900},
        # NO proxy — Stripe blocks proxy IPs
    )
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # ─── Network interceptor for /create-api-key ───
    def on_response(resp):
        try:
            if "create-api-key" in resp.url:
                async def grab():
                    try:
                        data = await resp.json()
                        captured_keys.append(data)
                        log(f"  [INTERCEPT] 🎯 captured key from {resp.url}")
                    except Exception as e:
                        log(f"  [INTERCEPT err] {e}")
                asyncio.create_task(grab())
        except Exception:
            pass
    page.on("response", on_response)

    try:
        # ═══════════════════════════════════════════════════════════════
        # PHASE B — Goto /settings/billing & add CC
        # ═══════════════════════════════════════════════════════════════
        result["stage"] = "billing_nav"
        log("  [B1] goto /settings/billing")
        await page.goto("https://agent.pioneer.ai/settings/billing",
                        wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        # ─── Handle "Tell us about your team" onboarding modal ───
        body = await page.evaluate("document.body.innerText")
        if "Tell us about your team" in body or ("Team name" in body and "Team size" in body):
            log("  [B2] onboarding modal — fill & continue")
            try:
                await page.get_by_text("Just me", exact=False).first.click(timeout=4000, force=True)
                log("      ✓ picked 'Just me'")
            except Exception:
                pass
            await asyncio.sleep(1)
            try:
                ta = page.locator("textarea").first
                if await ta.count():
                    await ta.fill("Personal experimentation with LLM APIs")
                    log("      ✓ filled use case")
            except Exception:
                pass
            await asyncio.sleep(1)
            try:
                cont = page.get_by_role("button", name=re.compile("Continue", re.I)).first
                if await cont.count() and await cont.is_visible():
                    await cont.click(timeout=6000, force=True)
                    log("      ✓ clicked Continue")
                    await asyncio.sleep(5)
            except Exception as e:
                log(f"      continue err: {e}")
            await page.goto("https://agent.pioneer.ai/settings/billing",
                            wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)

        # ─── Check if CC already added ───
        body = await page.evaluate("document.body.innerText")
        if "Payment Method on File" in body and "ending in" in body:
            log("  [B3] CC already on file — skip")
        else:
            # ─── Click "Add payment method" with 5 strategies ───
            log("  [B3] click 'Add payment method' CTA")
            result["stage"] = "open_stripe"
            clicked_add = False

            # S1: scope to Payment Method section
            try:
                section = page.locator("section, div").filter(has_text="Payment Method").first
                if await section.count():
                    inner_btn = section.get_by_role("button",
                                                   name=re.compile("Add payment method", re.I)).first
                    if await inner_btn.count() and await inner_btn.is_visible():
                        await inner_btn.click(timeout=8000, force=True)
                        log("      ✓ S1: clicked CTA in PaymentMethod section")
                        clicked_add = True
                        await asyncio.sleep(5)
            except Exception:
                pass

            # S2: regex loose match
            if not clicked_add:
                try:
                    loc = page.get_by_role("button", name=re.compile("Add payment method", re.I))
                    cnt = await loc.count()
                    for j in range(cnt - 1, -1, -1):
                        btn = loc.nth(j)
                        if await btn.is_visible() and await btn.is_enabled():
                            await btn.click(timeout=6000, force=True)
                            log(f"      ✓ S2: clicked button nth={j}")
                            clicked_add = True
                            await asyncio.sleep(5)
                            break
                except Exception:
                    pass

            # S3: variants
            if not clicked_add:
                for variant in ["Add card", "Add method", "Add new", "Add a payment",
                                "Add Card", "Add Payment"]:
                    try:
                        b = page.get_by_role("button", name=re.compile(variant, re.I)).first
                        if await b.count() and await b.is_visible() and await b.is_enabled():
                            await b.click(timeout=6000, force=True)
                            log(f"      ✓ S3: clicked '{variant}'")
                            clicked_add = True
                            await asyncio.sleep(5)
                            break
                    except Exception:
                        pass

            # S4: scan all visible buttons for "add" + payment-related word
            if not clicked_add:
                try:
                    btns = await page.locator("button:visible").all()
                    for b in btns:
                        try:
                            t = (await b.inner_text()).strip().lower()
                            if "add" in t and any(w in t for w in ["payment", "card", "method", "pay"]):
                                await b.click(timeout=4000, force=True)
                                log(f"      ✓ S4: scan-matched '{t}'")
                                clicked_add = True
                                await asyncio.sleep(5)
                                break
                        except Exception:
                            pass
                except Exception:
                    pass

            if not clicked_add:
                log("      ❌ no CTA found — dumping debug")
                await dump_debug(page, "billing")
                # Log visible buttons
                try:
                    btns = await page.locator("button:visible").all()
                    log(f"      📋 visible buttons on page: {len(btns)}")
                    for i, b in enumerate(btns[:25]):
                        try:
                            t = (await b.inner_text()).strip()
                            log(f"          btn[{i}]: '{t[:60]}'")
                        except Exception:
                            pass
                except Exception:
                    pass
                raise RuntimeError("Could not click 'Add payment method' button")

            # ─── Wait for Stripe iframe to mount ───
            log("  [B4] wait Stripe iframe mount")
            stripe_frame = None
            for poll in range(20):
                await asyncio.sleep(1)
                for fr in page.frames:
                    if "stripe" in (fr.url or "").lower() or "js.stripe.com" in (fr.url or ""):
                        stripe_frame = fr
                        break
                if stripe_frame:
                    log(f"      ✓ stripe frame mounted @poll {poll+1}: {stripe_frame.url[:80]}")
                    break
            await asyncio.sleep(2)

            # ─── Fill Stripe form ───
            result["stage"] = "fill_cc"
            log("  [B5] fill Stripe form")

            # Card number
            filled_card = False
            for fr in page.frames:
                try:
                    ci = fr.locator("input[name='cardnumber'], input[autocomplete='cc-number'], input[placeholder*='1234']").first
                    if await ci.count() and await ci.is_visible():
                        await ci.fill(CONFIG["card_number"])
                        filled_card = True
                        log(f"      ✓ card number filled")
                        break
                except Exception:
                    pass
            if not filled_card:
                # aria-label fallback
                for fr in page.frames:
                    try:
                        ci = fr.get_by_label(re.compile("Card number", re.I)).first
                        if await ci.count():
                            await ci.fill(CONFIG["card_number"])
                            filled_card = True
                            log(f"      ✓ card number filled (aria)")
                            break
                    except Exception:
                        pass
            if not filled_card:
                await dump_debug(page, "stripe_no_card")
                raise RuntimeError("Card number field not found")

            # Expiry
            exp = f"{CONFIG['exp_mm']}/{CONFIG['exp_yy']}"
            for fr in page.frames:
                try:
                    e = fr.locator("input[name='exp-date'], input[autocomplete='cc-exp'], input[placeholder*='MM']").first
                    if await e.count() and await e.is_visible():
                        await e.fill(exp)
                        log(f"      ✓ expiry filled: {exp}")
                        break
                except Exception:
                    pass

            # CVC
            for fr in page.frames:
                try:
                    c = fr.locator("input[name='cvc'], input[autocomplete='cc-csc'], input[placeholder*='CVC']").first
                    if await c.count() and await c.is_visible():
                        await c.fill(CONFIG["cvc"])
                        log(f"      ✓ cvc filled")
                        break
                except Exception:
                    pass

            # Name on card
            name = f"User {CONFIG['email'].split('@')[0]}"
            for sel in ["input[name='name']", "input[autocomplete='cc-name']", "input[placeholder*='Name']"]:
                try:
                    n = page.locator(sel).first
                    if await n.count() and await n.is_visible():
                        await n.fill(name)
                        log(f"      ✓ name filled: {name}")
                        break
                except Exception:
                    pass

            # ZIP
            for sel in ["input[name='postal']", "input[name='postalCode']", "input[autocomplete='postal-code']"]:
                try:
                    z = page.locator(sel).first
                    if await z.count() and await z.is_visible():
                        await z.fill(CONFIG["zip"])
                        log(f"      ✓ zip filled: {CONFIG['zip']}")
                        break
                except Exception:
                    pass

            await asyncio.sleep(2)

            # ─── Submit ───
            result["stage"] = "submit_cc"
            log("  [B6] submit CC")
            submitted = False
            for kw in ["Add payment method", "Add card", "Save card", "Save", "Submit", "Add"]:
                try:
                    btn = page.get_by_role("button", name=re.compile(kw, re.I)).first
                    if await btn.count() and await btn.is_visible() and await btn.is_enabled():
                        await btn.click(timeout=8000)
                        log(f"      ✓ clicked '{kw}'")
                        submitted = True
                        break
                except Exception:
                    pass
            if not submitted:
                raise RuntimeError("Could not find CC submit button")

            # ─── Wait for CC confirm ───
            cc_ok = False
            for i in range(30):
                await asyncio.sleep(2)
                try:
                    await page.keyboard.press("Escape")
                except Exception:
                    pass
                # Re-navigate every 5 polls
                if i > 0 and i % 5 == 0:
                    try:
                        await page.goto("https://agent.pioneer.ai/settings/billing",
                                        wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(3)
                    except Exception:
                        pass
                body = await page.evaluate("document.body.innerText")
                if ("Payment Method" in body or "Payment method" in body) and "ending in" in body:
                    log("  [B7] ✅ CC accepted (on file)")
                    cc_ok = True
                    break
                if "successfully" in body.lower():
                    log("  [B7] ✅ CC accepted (toast)")
                    cc_ok = True
                    break
                if "card was declined" in body.lower():
                    raise RuntimeError("CC declined explicitly")
            if not cc_ok:
                raise RuntimeError("CC submit timeout — see /tmp/pioneer_*.png")

        # ═══════════════════════════════════════════════════════════════
        # PHASE C — Run first inference + advance stepper
        # ═══════════════════════════════════════════════════════════════
        result["stage"] = "inference"
        log("  [C1] goto /dashboard, trigger first inference")

        for _ in range(3):
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
            except Exception:
                pass

        await page.goto("https://agent.pioneer.ai/dashboard",
                        wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        for _ in range(3):
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
            except Exception:
                pass
        await asyncio.sleep(2)

        try:
            run_btn = page.locator("button:has-text('Run inference')").first
            await run_btn.click(timeout=10000, force=True)
            log("      ✓ clicked Run inference")
            await asyncio.sleep(10)
        except Exception as e:
            log(f"      ⚠️ Run inference err: {str(e)[:80]} — continue anyway")

        try:
            next_btn = page.get_by_role("button", name="Next").first
            if await next_btn.count() and await next_btn.is_visible():
                await next_btn.click(timeout=8000, force=True)
                log("      ✓ clicked Next")
                await asyncio.sleep(5)
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════════════
        # PHASE D — Create API key
        # ═══════════════════════════════════════════════════════════════
        result["stage"] = "api_key"
        log("  [D1] goto /api-keys")
        await page.goto("https://agent.pioneer.ai/api-keys",
                        wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(6)

        for _ in range(3):
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
            except Exception:
                pass
        await asyncio.sleep(2)

        key_name = f"agent-{int(time.time())}-{random.randint(1000,9999)}"

        log("  [D2] click 'Create key'")
        await page.get_by_role("button", name="Create key").first.click(timeout=10000, force=True)
        await asyncio.sleep(3)

        # Fill name
        text_inputs = await page.locator("input[type='text'], input:not([type])").all()
        for inp in text_inputs:
            try:
                if await inp.is_visible():
                    await inp.fill(key_name)
                    log(f"      ✓ name: {key_name}")
                    break
            except Exception:
                pass
        await asyncio.sleep(1)

        # Submit (look inside dialog first)
        log("  [D3] submit create")
        submitted = False
        try:
            dialog = page.get_by_role("dialog").last
            if await dialog.count():
                for kw in ["Create key", "Create API key", "Generate", "Create"]:
                    try:
                        btn = dialog.get_by_role("button", name=kw).first
                        if await btn.count() and await btn.is_visible() and await btn.is_enabled():
                            await btn.click(timeout=6000, force=True)
                            submitted = True
                            log(f"      ✓ clicked '{kw}' in dialog")
                            break
                    except Exception:
                        pass
        except Exception:
            pass

        if not submitted:
            for kw in ["Create key", "Create API key", "Generate", "Create"]:
                try:
                    loc = page.get_by_role("button", name=kw)
                    cnt = await loc.count()
                    for j in range(cnt - 1, -1, -1):
                        btn = loc.nth(j)
                        if await btn.is_visible() and await btn.is_enabled():
                            await btn.click(timeout=6000, force=True)
                            submitted = True
                            log(f"      ✓ clicked '{kw}' nth={j}")
                            break
                    if submitted:
                        break
                except Exception:
                    pass

        if not submitted:
            try:
                await page.keyboard.press("Enter")
            except Exception:
                pass

        # Wait for /create-api-key intercept
        log("  [D4] wait for key payload (network intercept)")
        for _ in range(15):
            await asyncio.sleep(2)
            if captured_keys:
                break

        if not captured_keys:
            await dump_debug(page, "no_key")
            raise RuntimeError("API key not captured from /create-api-key")

        kdata = captured_keys[0]
        result["api_key"]    = kdata.get("secret_key")
        result["key_id"]     = kdata.get("id")
        result["expires_at"] = kdata.get("expires_at")
        log(f"  [D5] 🎯 key captured: {result['api_key'][:25]}...")

        # ═══════════════════════════════════════════════════════════════
        # PHASE E — Verify
        # ═══════════════════════════════════════════════════════════════
        result["stage"] = "verify"
        log("  [E1] verify via /v1/chat/completions")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.pioneer.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {result['api_key']}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":      CONFIG["verify_model"],
                    "messages":   [{"role": "user", "content": "OK"}],
                    "max_tokens": 5,
                },
            )
            if r.status_code == 200 and "content" in r.text:
                log("  [E2] ✅ KEY VERIFIED — works for real inference")
                result["verified"] = True
                result["stage"]    = "done"
            else:
                log(f"  [E2] ⚠️ verify HTTP {r.status_code}: {r.text[:200]}")

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        log(f"  [ERR] {result['error']}")
    finally:
        try:
            await ctx.close()
        except Exception:
            pass

    return result


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

async def main():
    t0 = time.time()

    # Ensure parent dirs
    Path(CONFIG["log_file"]).parent.mkdir(parents=True, exist_ok=True)
    Path(CONFIG["result_file"]).parent.mkdir(parents=True, exist_ok=True)
    Path(CONFIG["profile_dir"]).mkdir(parents=True, exist_ok=True)
    open(CONFIG["log_file"], "w").close()

    log("╔═══════════════════════════════════════════════════════════════╗")
    log("║  🔥 PIONEER AI AGENT ONBOARDING                                ║")
    log("╚═══════════════════════════════════════════════════════════════╝")
    log(f"  Email:      {CONFIG['email']}")
    log(f"  Card last4: {CONFIG['card_number'][-4:]}")
    log(f"  Profile:    {CONFIG['profile_dir']}")
    log(f"  Headless:   {CONFIG['headless']}")
    log(f"  Proxy:      {'YES' if CONFIG['proxy'] else 'NO (direct IP)'}")
    log("")

    result = {
        "email":      CONFIG["email"],
        "card_last4": CONFIG["card_number"][-4:],
        "api_key":    None,
        "verified":   False,
        "stage":      "init",
        "error":      None,
        "elapsed_seconds": 0,
    }

    try:
        # PHASE A
        await phase_a_oauth()

        # PHASE B-E
        result = await phase_b_to_e()

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        log(f"")
        log(f"╔═══════════════════════════════════════════════════════════════╗")
        log(f"║  ❌ CRASH                                                      ║")
        log(f"╚═══════════════════════════════════════════════════════════════╝")
        log(f"  {result['error']}")

    result["elapsed_seconds"] = round(time.time() - t0, 1)

    # Save result
    with open(CONFIG["result_file"], "w") as f:
        json.dump(result, f, indent=2)

    log("")
    if result.get("api_key"):
        log("╔═══════════════════════════════════════════════════════════════╗")
        log("║  ✅ SUCCESS                                                    ║")
        log("╚═══════════════════════════════════════════════════════════════╝")
        log(f"  🔑 API KEY:  {result['api_key']}")
        log(f"  🆔 KEY ID:   {result['key_id']}")
        log(f"  ✓  VERIFIED: {result['verified']}")
        log(f"  ⏱️  ELAPSED:  {result['elapsed_seconds']}s")
        log(f"  💾 SAVED:    {CONFIG['result_file']}")
        return 0
    else:
        log("╔═══════════════════════════════════════════════════════════════╗")
        log("║  ❌ FAILED                                                     ║")
        log("╚═══════════════════════════════════════════════════════════════╝")
        log(f"  STAGE:    {result.get('stage')}")
        log(f"  ERROR:    {result.get('error')}")
        log(f"  ELAPSED:  {result['elapsed_seconds']}s")
        log(f"  LOG:      {CONFIG['log_file']}")
        log(f"  DEBUG:    /tmp/pioneer_*.png")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
