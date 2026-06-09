#!/usr/bin/env python3
"""
download_metamask.py — Download MetaMask CRX3 from Chrome Web Store and unpack.

Usage:
    python3 download_metamask.py [DEST]

Default DEST: ~/.wallets/metamask-unpacked
"""

import io
import os
import sys
import zipfile
import urllib.request

WEBSTORE_ID = "nkbihfbeogaeaoehlefnkodbefgpgknn"
CRX_URL = (
    "https://clients2.google.com/service/update2/crx"
    "?response=redirect&acceptformat=crx2,crx3&prodversion=146.0.0"
    f"&x=id%3D{WEBSTORE_ID}%26uc"
)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)


def download_and_unpack(dest: str) -> str:
    dest = os.path.expanduser(dest)
    os.makedirs(dest, exist_ok=True)

    print(f"[1/3] Downloading MetaMask CRX3 from Chrome Web Store...")
    req = urllib.request.Request(CRX_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
    print(f"      Downloaded {len(raw) / 1024 / 1024:.1f} MB")

    if raw[:4] != b"Cr24":
        raise RuntimeError("Response is not a valid CRX file (bad ID or network block)")

    version = int.from_bytes(raw[4:8], "little")
    print(f"[2/3] CRX version: {version}")

    if version == 3:
        hdr_len = int.from_bytes(raw[8:12], "little")
        zip_off = 12 + hdr_len
    elif version == 2:
        pub_len = int.from_bytes(raw[8:12], "little")
        sig_len = int.from_bytes(raw[12:16], "little")
        zip_off = 16 + pub_len + sig_len
    else:
        raise RuntimeError(f"Unsupported CRX version: {version}")

    print(f"[3/3] Unpacking to {dest}...")
    with zipfile.ZipFile(io.BytesIO(raw[zip_off:])) as z:
        names = z.namelist()
        z.extractall(dest)

    manifest = os.path.join(dest, "manifest.json")
    if not os.path.exists(manifest):
        raise RuntimeError("Unpack failed: manifest.json not found")

    import json
    with open(manifest) as f:
        m = json.load(f)
    print(f"      OK {m.get('name', '?')} v{m.get('version', '?')} — {len(names)} files")
    return dest


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else "~/.wallets/metamask-unpacked"
    result = download_and_unpack(dest)
    print(f"\nDone. MetaMask unpacked to: {result}")
    print(f"Load in CloakBrowser: extension_paths=[\"{result}\"]")
