"""
extensions.py — mature extension source resolver for browser_engine.

Chromium can only ``--load-extension`` an UNPACKED folder (a dir containing
``manifest.json``). This module turns any of three sources into such a folder:

  • folder    — an already-unpacked extension dir (used as-is, no copy)
  • .crx      — a packed extension (CRX2 or CRX3); unpacked into the cache
  • webstore  — a Chrome Web Store id or detail URL; the .crx is downloaded from
                Google's public on-demand update endpoint, then unpacked

Resolved extensions are cached under ``cache_dir`` keyed by a stable hash of the
source, so repeat runs don't re-download / re-unpack. Each resolve reads
``manifest.json`` (localizing ``__MSG_*__`` names via ``_locales``) and returns
name + version + the folder path the engine can hand to Chromium.

No third-party deps — ``urllib`` + ``zipfile`` only.

Accountability: this installs/loads *legitimate* extensions (wallets, helpers)
on behalf of the operator. Programmatic Web Store download uses Google's public
``installsource=ondemand`` CRX endpoint; respect the Web Store Terms and each
extension's license. It is not a store-policy bypass and adds no DRM removal or
anti-detection payload.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Chrome extension ids are 32 chars drawn from a–p (mpdecimal of the key hash).
_EXT_ID_RE = re.compile(r"[a-p]{32}")
_FALLBACK_PRODVERSION = "146.0.0.0"

# Google's on-demand CRX endpoint. 302-redirects to the real .crx blob.
_WEBSTORE_CRX_URL = (
    "https://clients2.google.com/service/update2/crx"
    "?response=redirect&acceptformat=crx2,crx3&prodversion={pv}"
    "&x=id%3D{eid}%26installsource%3Dondemand%26uc"
)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)


def _default_cache_dir() -> Path:
    return Path(
        os.environ.get("AGENT_EXT_CACHE", str(Path.home() / ".agent" / "ext-cache"))
    ).expanduser()


def _default_prodversion() -> str:
    """Major.x version string for the Web Store endpoint, from CloakBrowser if present."""
    try:
        from cloakbrowser import CHROMIUM_VERSION  # type: ignore

        major = CHROMIUM_VERSION.split(".")[0]
        return f"{major}.0.0.0"
    except Exception:
        return _FALLBACK_PRODVERSION


# ───────────────────────── source spec ─────────────────────────


@dataclass
class ExtensionSpec:
    """
    One extension source. ``source`` may be a folder path, a ``.crx`` file path,
    or a Web Store id / detail URL. ``kind`` is auto-detected unless forced.

    Back-compat: the old ``ExtensionSpec(path=..., name=...)`` (folder only)
    still works — ``path`` is treated as ``source``.
    """

    source: str = ""
    name: str = ""
    kind: str = "auto"  # auto | folder | crx | webstore
    path: str = ""  # deprecated alias for source (folder)

    def __post_init__(self) -> None:
        if not self.source and self.path:
            self.source = self.path
        if not self.source:
            raise ValueError(
                "ExtensionSpec butuh source: folder, file .crx, atau Web Store id/URL"
            )

    # explicit constructors (clearer than relying on auto-detect)
    @classmethod
    def from_folder(cls, path: str, name: str = "") -> "ExtensionSpec":
        return cls(source=path, name=name, kind="folder")

    @classmethod
    def from_crx(cls, path: str, name: str = "") -> "ExtensionSpec":
        return cls(source=path, name=name, kind="crx")

    @classmethod
    def from_webstore(cls, id_or_url: str, name: str = "") -> "ExtensionSpec":
        return cls(source=id_or_url, name=name, kind="webstore")

    def detect_kind(self) -> str:
        if self.kind != "auto":
            return self.kind
        s = self.source.strip()
        if s.lower().endswith(".crx"):
            return "crx"
        p = Path(s).expanduser()
        if p.is_dir():
            return "folder"
        if _looks_like_webstore(s):
            return "webstore"
        if p.is_file():
            return "crx"  # a packed file without the .crx suffix
        # last resort: assume a folder path that doesn't exist yet → loud error later
        return "folder"


@dataclass
class ResolvedExtension:
    """An extension turned into a loadable unpacked folder + its metadata."""

    path: str  # absolute folder path, ready for --load-extension
    name: str
    version: str
    source_kind: str  # folder | crx | webstore
    source: str  # original source (or resolved Web Store id)


# ───────────────────────── helpers ─────────────────────────


def _looks_like_webstore(value: str) -> bool:
    try:
        extract_webstore_id(value)
        return True
    except ValueError:
        return False


def extract_webstore_id(value: str) -> str:
    """Accept a bare 32-char id or any Web Store detail URL → return the id."""
    v = value.strip()
    if _EXT_ID_RE.fullmatch(v):
        return v
    if "://" in v or v.startswith(("chrome.google", "chromewebstore")):
        url = v if "://" in v else "https://" + v
        for seg in reversed(urlparse(url).path.split("/")):
            if _EXT_ID_RE.fullmatch(seg):
                return seg
    raise ValueError(f"bukan Web Store id/URL valid: {value!r}")


def _read_manifest(folder: Path) -> dict:
    mf = folder / "manifest.json"
    if not mf.exists():
        raise FileNotFoundError(f"manifest.json gak ada di: {folder}")
    m = json.loads(mf.read_text(encoding="utf-8"))
    for key in ("name", "short_name", "description"):
        v = m.get(key, "")
        if isinstance(v, str) and v.startswith("__MSG_") and v.endswith("__"):
            loc = _localize(folder, m, v)
            if loc:
                m[key] = loc
    return m


def _localize(folder: Path, manifest: dict, token: str) -> Optional[str]:
    msg_key = token[len("__MSG_") : -len("__")]
    candidates = [manifest.get("default_locale", "en"), "en", "en_US"]
    for loc in candidates:
        f = folder / "_locales" / loc / "messages.json"
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            entry = data.get(msg_key) or data.get(msg_key.lower())
            if isinstance(entry, dict) and "message" in entry:
                return entry["message"]
    return None


def unpack_crx(crx_path: str | os.PathLike, dest_dir: str | os.PathLike) -> Path:
    """
    Unpack a CRX2 or CRX3 file into ``dest_dir``. A .crx is a small header
    followed by an ordinary ZIP; we locate the ZIP offset by version and extract.
    """
    raw = Path(crx_path).read_bytes()
    if raw[:4] != b"Cr24":
        raise ValueError(f"bukan file CRX (magic 'Cr24' gak ada): {crx_path}")
    version = int.from_bytes(raw[4:8], "little")
    if version == 2:
        pub_len = int.from_bytes(raw[8:12], "little")
        sig_len = int.from_bytes(raw[12:16], "little")
        zip_off = 16 + pub_len + sig_len
    elif version == 3:
        hdr_len = int.from_bytes(raw[8:12], "little")
        zip_off = 12 + hdr_len
    else:
        raise ValueError(f"versi CRX gak didukung: {version}")

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw[zip_off:])) as z:
        # guard against zip-slip
        for info in z.infolist():
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise RuntimeError(f"entri zip keluar dari dest (zip-slip): {info.filename}")
        z.extractall(dest)
    if not (dest / "manifest.json").exists():
        raise RuntimeError(f"unpack CRX gagal: manifest.json gak ada di {dest}")
    return dest


def download_webstore_crx(
    ext_id: str,
    dest_path: str | os.PathLike,
    prodversion: Optional[str] = None,
    timeout: int = 60,
) -> Path:
    """Download an extension's .crx from the Web Store on-demand endpoint."""
    ext_id = extract_webstore_id(ext_id)
    pv = prodversion or _default_prodversion()
    url = _WEBSTORE_CRX_URL.format(pv=pv, eid=ext_id)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # follows 302
        data = resp.read()
    if data[:4] != b"Cr24":
        raise RuntimeError(
            "respons Web Store bukan CRX — kemungkinan id salah, ekstensi ditarik, "
            "atau jaringan diblok (coba via proxy / VPS)."
        )
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


# ───────────────────────── resolver ─────────────────────────


class ExtensionResolver:
    """Turns ExtensionSpec sources into loadable unpacked folders, with caching."""

    def __init__(
        self,
        cache_dir: Optional[str | os.PathLike] = None,
        prodversion: Optional[str] = None,
        offline: bool = False,
    ):
        self.cache_dir = Path(cache_dir or _default_cache_dir()).expanduser()
        self.prodversion = prodversion
        self.offline = offline
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _slot(self, kind: str, key: str) -> Path:
        h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{kind}-{h}"

    def resolve(self, spec: ExtensionSpec) -> ResolvedExtension:
        kind = spec.detect_kind()

        if kind == "folder":
            folder = Path(spec.source).expanduser().resolve()
            if not folder.is_dir():
                raise FileNotFoundError(f"folder ekstensi gak ada: {folder}")
            m = _read_manifest(folder)
            return ResolvedExtension(
                str(folder), spec.name or m.get("name", ""), m.get("version", ""),
                "folder", spec.source,
            )

        if kind == "crx":
            crx = Path(spec.source).expanduser().resolve()
            if not crx.is_file():
                raise FileNotFoundError(f"file .crx gak ada: {crx}")
            # cache keyed by path + mtime so re-packing busts the cache
            slot = self._slot("crx", f"{crx}:{crx.stat().st_mtime_ns}")
            if not (slot / "manifest.json").exists():
                unpack_crx(crx, slot)
            m = _read_manifest(slot)
            return ResolvedExtension(
                str(slot), spec.name or m.get("name", ""), m.get("version", ""),
                "crx", spec.source,
            )

        if kind == "webstore":
            eid = extract_webstore_id(spec.source)
            slot = self._slot("webstore", eid)
            if not (slot / "manifest.json").exists():
                if self.offline:
                    raise RuntimeError(
                        f"offline=True tapi ekstensi Web Store {eid} belum ke-cache"
                    )
                crx_tmp = slot.parent / f"{eid}.crx"
                download_webstore_crx(eid, crx_tmp, self.prodversion)
                unpack_crx(crx_tmp, slot)
            m = _read_manifest(slot)
            return ResolvedExtension(
                str(slot), spec.name or m.get("name", ""), m.get("version", ""),
                "webstore", eid,
            )

        raise ValueError(f"kind ekstensi gak dikenal: {kind}")

    def resolve_all(self, specs: list[ExtensionSpec]) -> list[ResolvedExtension]:
        return [self.resolve(s) for s in specs]


if __name__ == "__main__":
    print(
        "extensions.py — resolver folder/.crx/webstore → unpacked folder. "
        "Folder dipakai apa adanya; .crx & webstore di-unpack+cache ke ~/.agent/ext-cache."
    )
