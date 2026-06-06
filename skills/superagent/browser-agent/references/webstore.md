# Web Store & .crx install — deep dive

`scripts/extensions.py` turns any extension source into an unpacked folder that
Chromium can `--load-extension`. Three source kinds; all funnel to a folder.

## Source kinds

```python
ExtensionSpec.from_folder("~/ext/unpacked")                # used as-is, no copy
ExtensionSpec.from_crx("~/ext/wallet.crx")                 # CRX2/CRX3 → unpacked
ExtensionSpec.from_webstore("nkbihfbeogaeaoehlefnkodbefgpgknn")   # by id
ExtensionSpec.from_webstore("https://chromewebstore.google.com/detail/metamask/<id>")  # by URL
ExtensionSpec("~/path-or-id")                              # kind="auto" (detected)
```

Auto-detect order: `.crx` suffix → crx; existing dir → folder; 32-char `[a-p]`
id or Web Store URL → webstore; existing file → crx.

## How each kind resolves

- **folder** — read `manifest.json` for name/version, return the path. Fails
  loudly if the folder or manifest is missing.
- **.crx** — a `.crx` is a small header + an ordinary ZIP. The unpacker reads the
  `Cr24` magic and version (CRX2: skip pubkey+sig; CRX3: skip protobuf header),
  then extracts the ZIP (with zip-slip guard) into the cache. Re-packing the
  source busts the cache (keyed by path + mtime).
- **webstore** — the id is extracted from a bare id or any detail URL, then the
  `.crx` is fetched from Google's public on-demand endpoint
  (`clients2.google.com/service/update2/crx`, `installsource=ondemand`), unpacked,
  and cached keyed by id.

`__MSG_*__` manifest names are localized via `_locales/<default_locale>/messages.json`
so discovered names read like "MetaMask", not "__MSG_appName__".

## Caching

Resolved extensions live under `extension_cache_dir` (default `$AGENT_EXT_CACHE`
or `~/.agent/ext-cache`), in `crx-<hash>/` and `webstore-<hash>/` slots. Repeat
runs reuse the cache — no re-download, no re-unpack. Delete a slot to force a
refresh.

## Offline / air-gapped

`BrowserConfig(offline_extensions=True)` forbids Web Store downloads — a
webstore spec that isn't already cached raises instead of hitting the network.
Pre-seed the cache on a connected machine, or use `.crx`/folder sources.

## Network notes

- The Web Store endpoint needs outbound HTTPS to `clients2.google.com`. On a
  locked-down VPS, allow it or route through a proxy.
- `prodversion` in the request defaults to CloakBrowser's Chromium major if
  installed, else a sane fallback. Pass `prodversion=` to `download_webstore_crx`
  or `ExtensionResolver(prodversion=...)` to pin it.
- A non-`Cr24` response means a wrong id, a pulled extension, or a blocked
  network — the downloader raises with that hint rather than writing garbage.

## Direct helpers (without the engine)

```python
from extensions import ExtensionResolver, unpack_crx, download_webstore_crx, extract_webstore_id

unpack_crx("wallet.crx", "/tmp/wallet")                    # → folder Path
download_webstore_crx("<id>", "/tmp/x.crx")                # → .crx Path
extract_webstore_id("https://.../detail/metamask/<id>")    # → "<id>"

res = ExtensionResolver(cache_dir="~/.agent/ext-cache")
r = res.resolve(ExtensionSpec.from_webstore("<id>"))       # → ResolvedExtension
```

## Honest limits

- Chromium loads only **unpacked** extensions — that's why everything resolves to
  a folder. A `.crx` is never loaded directly.
- A Web Store install via this path is the unpacked source, not a managed install;
  it won't auto-update. Re-resolve (bust the cache) to get a newer version.
- Some extensions ship platform-specific binaries or expect a signed install;
  most wallet/helper extensions load fine unpacked, a few may warn.
