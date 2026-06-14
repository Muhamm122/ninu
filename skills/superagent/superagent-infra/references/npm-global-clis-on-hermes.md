# npm Global CLI Tools on Hermes-Managed Boxes

When you `npm install -g <package>` on a Hermes VPS, the binary does NOT land in `/usr/local/bin/`. Hermes owns its own Node.js runtime under `~/.hermes/node/`, and the global `node_modules/` is there too.

## Where Things Actually Go

```bash
# Check the npm prefix
npm config get prefix
# Ubuntu (non-root user):  /home/ubuntu/.hermes/node
# Ubuntu (root user):     /root/.hermes/node
# AlmaLinux (root user):  /root/.hermes/node

# Binaries are at
ls /home/ubuntu/.hermes/node/bin/   # ubuntu
ls /root/.hermes/node/bin/          # root

# Examples
ls /root/.hermes/node/bin/kapso
ls /root/.hermes/node/bin/9router
```

## Fix After Every `npm install -g`

```bash
# Add to PATH for current shell
export PATH="$(npm config get prefix)/bin:$PATH"

# Persist for future shells
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.bashrc
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.bash_profile
# Reload
source ~/.bashrc

# Verify
which kapso  # should now resolve
```

## Affected CLIs Encountered So Far

| Package        | Use case                              | First install path                          |
|----------------|---------------------------------------|---------------------------------------------|
| `@kapso/cli`   | WhatsApp Business API automation      | `/root/.hermes/node/bin/kapso`              |
| `pm2`          | Node process manager                  | Same prefix — install before using in systemd|
| `9router`      | LLM proxy aggregator (TUI)            | Same prefix                                 |
| `yarn`         | Node package manager                  | Same prefix                                 |

## @kapso/cli — Auth Pitfalls

**Login is interactive only** — `kapso login` opens a browser for OAuth. No `--email`/`--password` flags, no `--token` option in v0.16.0.

**For non-interactive use (cron, scripts, agents):**
```bash
# Set API key from Kapso dashboard (https://app.kapso.ai/settings/api-keys)
export KAPSO_API_KEY=*** "export KAPSO_API_KEY=*** >> ~/.bashrc

# Verify auth
kapso status  # should show authenticated + plan info
```

**Setup subcommand** (`kapso setup install`) needs:
- `--area-code` — WhatsApp number area code
- `--country` — ISO country code
- `--project` — project name
- Generally requires interactive confirmation; not scriptable end-to-end

**Pro tip**: Run `kapso login` once on the operator's machine (with browser), then export `KAPSO_API_KEY` from the dashboard to deploy on the VPS without interactive flow.

## Pitfall — Running Script from Wrong Dir

```bash
# ❌ Module not found
cd /tmp && node /tmp/gen-wallet.js
# Error: Cannot find module 'tweetnacl'

# ✅ Either cd to dir with node_modules, or copy script in
cd /home/ubuntu/.hermes/skills/owntown-farming/scripts && node /tmp/gen-wallet.js
# Or: cp /tmp/gen-wallet.js scripts/ && node scripts/gen-wallet.js
```

Node.js resolves `require()` relative to the script's location, not the cwd. Running a script that imports a global `node_modules/` only works if the script lives in a dir that can find those modules.

## Pitfall — `require('bs58')` API Change (bs58 v5+)

```js
// ❌ Old snippet from tutorials — works in bs58 v4, FAILS in v5+
const bs58 = require('bs58').default;
bs58.encode(...)  // TypeError: Cannot read properties of undefined

// ✅ Correct for v5+ (no .default export)
const bs58 = require('bs58');
bs58.encode(...)
```

Same applies to several packages that dropped CJS default exports during ESM migration. Check the package's `package.json` `main`/`exports` field before importing.

## Cleanup if Mistakenly Installed to /usr/local/bin

```bash
# Check what's there
ls /usr/local/bin/ | grep -E "node|npm|kapso"

# If a global install polluted /usr/local/bin, remove it
npm uninstall -g <pkg>

# Verify clean state
npm config get prefix
ls $(npm config get prefix)/bin/
```
