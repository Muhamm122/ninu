"""
browser_engine.py — stealth-first Playwright engine for an AI agent.

Core stance:
    The base launcher is CloakBrowser — a Chromium with fingerprint patches
    compiled into the binary at C++ source level (canvas, WebGL, audio, fonts,
    GPU, screen, WebRTC, automation signals). It passes bot detection
    (reCAPTCHA v3, Cloudflare Turnstile, FingerprintJS) while exposing the
    standard Playwright API. Set ``BrowserConfig.cloaking=False`` to fall back to
    plain upstream Chromium (e.g. when you want to respect a site that blocks
    automation, or for offline/no-binary environments).

    Stealth is for legitimate automation on sites that block headless traffic.
    It does NOT authorize abuse — credential stuffing, mass account creation, or
    automating systems without permission are out of bounds (CloakBrowser
    BINARY-LICENSE). No CAPTCHA solver is wired in. The governor + confirm gate
    apply to every side-effectful action exactly as before.

Mature extension control (both launchers):
    - Load extensions from a FOLDER, a .crx FILE, or the CHROME WEB STORE
      (by id or URL) — resolved to unpacked folders by scripts/extensions.py.
    - Discover loaded extensions + read their manifest (id / name / version).
    - Wait for a named extension to come up after launch.
    - Open popup / options / any internal chrome-extension:// page and drive it.
    - Low-level: evaluate JS inside the extension background (SW / page) and
      read chrome.storage.

Honest limits (Chromium, documented — not faked):
    - Extensions need a PERSISTENT context and do NOT run in classic headless;
      the engine auto-injects ``--headless=new`` when you ask for headless WITH
      extensions (both launchers).
    - You choose WHICH extensions load; you cannot toggle an installed extension
      on/off at runtime (chrome://extensions is a privileged WebUI).
    - In stealth mode CloakBrowser ships its own binary, so ``channel`` is
      ignored.

Install:
    pip install cloakbrowser                      # stealth core (auto-downloads binary)
    pip install playwright && playwright install chromium   # for cloaking=False fallback
"""

from __future__ import annotations

import asyncio
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

# Re-export the source resolver so callers can `from browser_engine import ExtensionSpec`.
from extensions import ExtensionResolver, ExtensionSpec, ResolvedExtension  # noqa: F401

try:
    from playwright.async_api import (  # used for type checks + the fallback path
        async_playwright,
        BrowserContext,
        Page,
        Worker,
        TimeoutError as PWTimeout,
    )

    _PLAYWRIGHT_OK = True
except ImportError:
    async_playwright = None  # type: ignore
    BrowserContext = Page = Worker = Any  # type: ignore
    PWTimeout = Exception  # type: ignore
    _PLAYWRIGHT_OK = False


# ───────────────────────── config ─────────────────────────


@dataclass
class StealthConfig:
    """
    Knobs for the CloakBrowser core (mirrors launch_persistent_context_async).

      - proxy: "http://user:pass@host:port" / "socks5://...". Site galak
        (Cloudflare/DataDome) WAJIB residential — datacenter IP keblok reputasi.
      - geoip: cocokin timezone+locale ke exit IP proxy. Butuh cloakbrowser[geoip].
      - humanize: mouse Bézier, typing per-karakter, scroll natural ("default"|"careful").
      - fingerprint_seed: pin identitas (returning visitor) untuk skoring v3.
      - timezone: override IANA tz (mis. "Asia/Jakarta"); menang atas geoip.
      - stealth_args: default fingerprint patches nyala.
      - auto_update: default False → CLOAKBROWSER_AUTO_UPDATE=false (binary closed
        gak update diam-diam di VPS). Update manual: python -m cloakbrowser update.
      - extra_args: raw flag CloakBrowser, mis. ["--fingerprint-noise=false"].
    """

    proxy: Optional[str] = None
    geoip: bool = False
    humanize: bool = False
    human_preset: str = "default"  # "default" | "careful"
    human_config: Optional[dict] = None
    fingerprint_seed: Optional[int] = None
    timezone: Optional[str] = None
    stealth_args: bool = True
    auto_update: bool = False
    extra_args: list[str] = field(default_factory=list)


@dataclass
class BrowserConfig:
    headless: bool = False
    user_data_dir: str = field(
        default_factory=lambda: os.environ.get(
            "AGENT_BROWSER_PROFILE", str(Path.home() / ".agent" / "browser-profile")
        )
    )
    extensions: list[ExtensionSpec] = field(default_factory=list)
    viewport: tuple[int, int] = (1280, 800)
    locale: str = "en-US"
    channel: Optional[str] = None  # ignored when cloaking=True
    slow_mo_ms: int = 0
    extra_args: list[str] = field(default_factory=list)
    default_timeout_ms: int = 30_000
    # stealth core ON by default; flip to False for plain Playwright fallback.
    cloaking: bool = True
    stealth: StealthConfig = field(default_factory=StealthConfig)
    # where downloaded/unpacked extensions are cached
    extension_cache_dir: Optional[str] = None
    offline_extensions: bool = False  # forbid Web Store download; require cache


@dataclass
class ExtensionInfo:
    """A loaded, running extension (discovered from the live context)."""

    id: str
    name: str
    version: str
    kind: str  # "service_worker" (MV3) | "background_page" (MV2)
    _target: Union[Worker, Page]  # internal: where background JS is evaluated

    def origin(self) -> str:
        return f"chrome-extension://{self.id}"


# ───────────────────────── engine ─────────────────────────


class BrowserAgent:
    """Async context manager. `async with BrowserAgent(cfg) as b: ...`"""

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.cfg = config or BrowserConfig()
        self._pw = None
        self.ctx: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.loaded: list[ResolvedExtension] = []  # what we installed this launch

    # -- lifecycle --------------------------------------------------------

    async def __aenter__(self) -> "BrowserAgent":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def start(self) -> "BrowserAgent":
        cfg = self.cfg

        # 1) resolve every extension source → unpacked folder path
        resolver = ExtensionResolver(
            cache_dir=cfg.extension_cache_dir, offline=cfg.offline_extensions
        )
        self.loaded = resolver.resolve_all(cfg.extensions)
        ext_paths = [r.path for r in self.loaded]

        # 2) launch
        Path(cfg.user_data_dir).mkdir(parents=True, exist_ok=True)
        if cfg.cloaking:
            await self._start_stealth(cfg, ext_paths)
        else:
            await self._start_plain(cfg, ext_paths)

        self.ctx.set_default_timeout(cfg.default_timeout_ms)
        self.page = self.ctx.pages[0] if self.ctx.pages else await self.ctx.new_page()
        return self

    async def _start_stealth(self, cfg: BrowserConfig, ext_paths: list[str]) -> None:
        try:
            from cloakbrowser import launch_persistent_context_async  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "stealth core butuh CloakBrowser. Jalankan: pip install cloakbrowser "
                f"(atau set BrowserConfig.cloaking=False untuk Playwright biasa). Detail: {e}"
            )
        s = cfg.stealth
        if cfg.channel:
            warnings.warn(
                "BrowserConfig.channel diabaikan saat cloaking=True "
                "(CloakBrowser pakai patched binary-nya sendiri).",
                stacklevel=2,
            )
        if not s.auto_update:
            os.environ.setdefault("CLOAKBROWSER_AUTO_UPDATE", "false")

        args = list(s.extra_args)
        if s.fingerprint_seed is not None:
            args.append(f"--fingerprint={s.fingerprint_seed}")
        headless = cfg.headless
        if ext_paths and cfg.headless:
            args.append("--headless=new")  # ekstensi mati di headless klasik
            headless = False

        self.ctx = await launch_persistent_context_async(
            user_data_dir=cfg.user_data_dir,
            headless=headless,
            proxy=s.proxy,
            geoip=s.geoip,
            humanize=s.humanize,
            human_preset=s.human_preset,
            human_config=s.human_config,
            timezone=s.timezone,
            locale=cfg.locale,
            stealth_args=s.stealth_args,
            extension_paths=ext_paths or None,
            viewport={"width": cfg.viewport[0], "height": cfg.viewport[1]},
            args=args,
            slow_mo=cfg.slow_mo_ms,  # forwarded to playwright via **kwargs
        )
        # CloakBrowser patches ctx.close() to stop its own Playwright instance.

    async def _start_plain(self, cfg: BrowserConfig, ext_paths: list[str]) -> None:
        if not _PLAYWRIGHT_OK:
            raise RuntimeError(
                "cloaking=False butuh Playwright: pip install playwright && playwright install chromium"
            )
        args = list(cfg.extra_args)
        use_headless = cfg.headless
        if ext_paths:
            joined = ",".join(ext_paths)
            args += [f"--disable-extensions-except={joined}", f"--load-extension={joined}"]
            if cfg.headless:
                args.append("--headless=new")
                use_headless = False
        self._pw = await async_playwright().start()
        self.ctx = await self._pw.chromium.launch_persistent_context(
            user_data_dir=cfg.user_data_dir,
            headless=use_headless,
            args=args,
            viewport={"width": cfg.viewport[0], "height": cfg.viewport[1]},
            locale=cfg.locale,
            channel=cfg.channel,
            slow_mo=cfg.slow_mo_ms,
        )

    async def close(self) -> None:
        if self.ctx:
            await self.ctx.close()  # stealth: also stops CloakBrowser's playwright
            self.ctx = None
        if self._pw:
            await self._pw.stop()
            self._pw = None

    # -- navigation / reading --------------------------------------------

    async def goto(self, url: str, wait: str = "domcontentloaded") -> None:
        await self._page().goto(url, wait_until=wait)

    async def read_text(self) -> str:
        return await self._page().inner_text("body")

    async def snapshot(self) -> Any:
        return await self._page().accessibility.snapshot() or {}

    async def click_text(self, text: str, exact: bool = False) -> None:
        await self._page().get_by_text(text, exact=exact).first.click()

    async def fill(self, selector: str, value: str) -> None:
        await self._page().fill(selector, value)

    async def screenshot(self, path: str, full_page: bool = True) -> str:
        await self._page().screenshot(path=path, full_page=full_page)
        return path

    # -- extension control -----------------------------------------------

    async def discover_extensions(self, timeout_ms: int = 10_000) -> list[ExtensionInfo]:
        """List loaded extensions via service workers (MV3) + background pages (MV2)."""
        ctx = self._context()
        deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
        seen: dict[str, Union[Worker, Page]] = {}

        while asyncio.get_event_loop().time() < deadline:
            for w in ctx.service_workers:
                eid = self._ext_id(w.url)
                if eid:
                    seen.setdefault(eid, w)
            for bp in getattr(ctx, "background_pages", []) or []:
                eid = self._ext_id(bp.url)
                if eid:
                    seen.setdefault(eid, bp)
            if seen:
                break
            try:
                await ctx.wait_for_event("serviceworker", timeout=1000)
            except PWTimeout:
                pass

        out: list[ExtensionInfo] = []
        for eid, target in seen.items():
            try:
                m = await target.evaluate("() => chrome.runtime.getManifest()")
            except Exception:
                m = {}
            kind = "service_worker" if isinstance(target, Worker) else "background_page"
            out.append(
                ExtensionInfo(
                    id=eid,
                    name=str(m.get("name", "")),
                    version=str(m.get("version", "")),
                    kind=kind,
                    _target=target,
                )
            )
        return out

    async def find_extension(self, query: str, timeout_ms: int = 10_000) -> ExtensionInfo:
        """Find by exact id or by name substring (case-insensitive)."""
        exts = await self.discover_extensions(timeout_ms)
        for e in exts:
            if e.id == query:
                return e
        q = query.lower()
        for e in exts:
            if q in e.name.lower():
                return e
        loaded = ", ".join(f"{e.name}({e.id[:8]})" for e in exts) or "(kosong)"
        raise LookupError(f"extension '{query}' gak ketemu. Yang ke-load: {loaded}")

    async def wait_for_extension(self, query: str, timeout_ms: int = 20_000) -> ExtensionInfo:
        """
        Poll until an extension matching `query` is up. Useful right after launch
        (service workers can take a beat) or after installing from the Web Store.
        """
        deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
        last: Optional[Exception] = None
        while asyncio.get_event_loop().time() < deadline:
            try:
                return await self.find_extension(query, timeout_ms=1500)
            except LookupError as e:
                last = e
                await asyncio.sleep(0.5)
        raise LookupError(f"extension '{query}' gak muncul dalam {timeout_ms}ms ({last})")

    async def open_extension_page(self, ext: Union[str, ExtensionInfo], rel: str = "") -> Page:
        info = ext if isinstance(ext, ExtensionInfo) else await self.find_extension(ext)
        page = await self._context().new_page()
        await page.goto(f"{info.origin()}/{rel.lstrip('/')}")
        return page

    async def open_popup(self, ext: Union[str, ExtensionInfo]) -> Page:
        """Open the extension's default popup (rendered as a tab — DOM is identical)."""
        info = ext if isinstance(ext, ExtensionInfo) else await self.find_extension(ext)
        m = await info._target.evaluate("() => chrome.runtime.getManifest()")
        popup = (m.get("action") or {}).get("default_popup") or (
            m.get("browser_action") or {}
        ).get("default_popup")
        if not popup:
            raise LookupError(f"{info.name}: gak ada default_popup di manifest")
        return await self.open_extension_page(info, popup)

    async def open_options(self, ext: Union[str, ExtensionInfo]) -> Page:
        """Open the extension's options page (options_ui.page or options_page)."""
        info = ext if isinstance(ext, ExtensionInfo) else await self.find_extension(ext)
        m = await info._target.evaluate("() => chrome.runtime.getManifest()")
        opts = (m.get("options_ui") or {}).get("page") or m.get("options_page")
        if not opts:
            raise LookupError(f"{info.name}: gak ada options page di manifest")
        return await self.open_extension_page(info, opts)

    async def approve_in_popup(
        self, ext: Union[str, ExtensionInfo], button_text: str, exact: bool = False
    ) -> Page:
        """Open popup → click a button (Connect / Confirm / Approve / Sign / Next)."""
        page = await self.open_popup(ext)
        await page.get_by_role("button", name=button_text, exact=exact).first.click()
        return page

    async def eval_in_extension(self, ext: Union[str, ExtensionInfo], expression: str) -> Any:
        """Run JS in the extension background (chrome.* available)."""
        info = ext if isinstance(ext, ExtensionInfo) else await self.find_extension(ext)
        return await info._target.evaluate(expression)

    async def extension_storage(
        self, ext: Union[str, ExtensionInfo], area: str = "local"
    ) -> Any:
        """Read chrome.storage.<area> (local|sync|session) for an extension."""
        return await self.eval_in_extension(
            ext, f"() => chrome.storage.{area}.get(null)"
        )

    # -- WalletConnect (carried over) ------------------------------------

    async def capture_walletconnect_uri(self, timeout_ms: int = 15_000) -> Optional[str]:
        """
        Grab a `wc:...` URI from the page (href / input value / text). Pair it on
        YOUR own WC signer (web3_connect.py), not a third party. Signing stays
        with you + the governor.
        """
        js = """
        () => {
          const grab = (s) => (s && s.match(/wc:[^"'\\s]+/)) ? s.match(/wc:[^"'\\s]+/)[0] : null;
          for (const a of document.querySelectorAll('a[href^="wc:"]')) { const u = grab(a.href); if (u) return u; }
          for (const i of document.querySelectorAll('input')) { const u = grab(i.value); if (u) return u; }
          return grab(document.body ? document.body.innerText : "");
        }
        """
        deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
        while asyncio.get_event_loop().time() < deadline:
            uri = await self._page().evaluate(js)
            if uri:
                return uri
            await asyncio.sleep(0.5)
        return None

    # -- internals --------------------------------------------------------

    def _page(self) -> Page:
        if not self.page:
            raise RuntimeError("browser belum start(). Pakai `async with BrowserAgent(...)`.")
        return self.page

    def _context(self) -> BrowserContext:
        if not self.ctx:
            raise RuntimeError("browser belum start().")
        return self.ctx

    @staticmethod
    def _ext_id(url: str) -> Optional[str]:
        if url and url.startswith("chrome-extension://"):
            return url.split("/")[2]
        return None


# ───────────── governed signing (integration point) ─────────────
# screen_tx → governor.authorize → confirm → sign. Imports guarded so this file
# compiles standalone; in openclaw, web3_connect.py + governor.py already exist.


@dataclass
class SignRequest:
    w3: Any
    account: Any
    tx: dict
    dapp_name: str
    chain_id: Optional[int] = None
    usd_value: Optional[float] = None
    simulated_ok: bool = False


@dataclass
class SignResult:
    status: str  # "signed" | "rejected" | "blocked"
    summary: str
    signed_raw: Optional[str] = None
    human_readable: Optional[dict] = None


async def governed_sign(req: SignRequest, confirm_cb=None) -> SignResult:
    """
    Order (cannot be skipped): screen_tx → governor.authorize (caps/slippage/
    kill-switch) → operator confirm → sign. A dApp can *request* a tx; the agent
    *decides*. A page can never force a signature by telling the agent to sign.
    """
    try:
        from .web3_connect import screen_tx  # type: ignore
        from .governor import SpendGovernor, TxIntent  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "governed_sign butuh web3_connect.py + governor.py (ada di project openclaw). "
            f"Detail: {e}"
        )

    chain_id = req.chain_id or req.w3.eth.chain_id
    screen = await screen_tx(req.w3, req.tx, req.dapp_name)
    human = screen.__dict__ if hasattr(screen, "__dict__") else {"summary": str(screen)}

    gov = SpendGovernor()
    intent = TxIntent(
        wallet=req.account.address,
        chain_id=chain_id,
        action=f"dapp:{req.dapp_name}",
        usd_value=req.usd_value,
        simulated_ok=req.simulated_ok,
        gas_price_wei=req.tx.get("gasPrice") or req.tx.get("maxFeePerGas"),
        recipient=req.tx.get("to"),
    )
    decision = gov.authorize(intent)
    if not decision.allowed:
        return SignResult("blocked", decision.summary(), human_readable=human)

    if confirm_cb is not None:
        ok = await confirm_cb({"dapp": req.dapp_name, "screen": human, "decision": decision.summary()})
        if not ok:
            return SignResult("rejected", "operator menolak di konfirmasi", human_readable=human)

    signed = req.account.sign_transaction(req.tx)
    raw = "0x" + signed.raw_transaction.hex()
    return SignResult("signed", "lolos governor + konfirmasi", signed_raw=raw, human_readable=human)


# ───────────── examples (pseudo; need cloakbrowser/playwright + env) ─────────────


async def _example_webstore_extension():
    # Install MetaMask straight from the Web Store, stealth core, then drive it.
    cfg = BrowserConfig(
        headless=False,
        extensions=[ExtensionSpec.from_webstore(
            "nkbihfbeogaeaoehlefnkodbefgpgknn", name="MetaMask"
        )],
        stealth=StealthConfig(humanize=True, fingerprint_seed=42069),
    )
    async with BrowserAgent(cfg) as b:
        for r in b.loaded:
            print(f"installed: {r.name} v{r.version} [{r.source_kind}] -> {r.path}")
        mm = await b.wait_for_extension("MetaMask")
        await b.goto("https://app.uniswap.org")
        await b.approve_in_popup(mm, "Connect")
        print("storage keys:", list((await b.extension_storage(mm)).keys()))


if __name__ == "__main__":
    print(
        "browser_engine: stealth core (CloakBrowser) + extension control "
        "(folder/.crx/webstore). cloaking=False → Playwright biasa. "
        "Install: pip install cloakbrowser  [+ playwright untuk fallback]"
    )
