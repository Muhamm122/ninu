# Multi-Repo Batch Deploy via PM2 (Hermes VPS)

Pattern for deploying N GitHub repos as PM2 services on a single Hermes VPS. Validated deploying 6 waguriagentic repos in one session (3 skipped for missing runtime deps, 3 went live).

## The 5-Step Workflow

```bash
# 1. Inventory first — NEVER cd into a path you haven't confirmed exists
ls -d /tmp/<repo-folder> 2>/dev/null   # confirm path BEFORE cd

# 2. Detect the runtime per repo (Node, Python, or both)
cat <repo>/package.json 2>/dev/null | grep -E "(engines|dependencies)"
cat <repo>/pyproject.toml 2>/dev/null | grep -E "(requires-python|dependencies)"
cat <repo>/requirements.txt 2>/dev/null | head -5

# 3. Check port conflicts BEFORE pm2 start — orphan node/python processes from
#    previous sessions often occupy the default port (e.g. 8750)
ss -tlnp 2>/dev/null | grep -E ":(<port>|<port2>)\b"
# OR if ss is not detailed enough:
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:<port>  # 200 = someone is there

# 4. Install deps fresh in each repo
cd <repo> && npm install --silent 2>&1 | tail -3
# OR for Python (in hermes-agent venv, NOT user-site):
/home/ubuntu/.hermes/hermes-agent/venv/bin/pip install -e .

# 5. pm2 start with --cwd and a unique name
/home/ubuntu/.hermes/node/bin/pm2 start server.js --name waguri-<repo> --cwd <repo-path>
# For Python (uvicorn):
/home/ubuntu/.hermes/node/bin/pm2 start "/home/ubuntu/.hermes/hermes-agent/venv/bin/uvicorn app:app --host 0.0.0.0 --port <p>" --name waguri-<repo> --cwd <repo-path>
```

## ⚠️ Pitfall 1 — PM2 Binary Lives in node/bin, NOT venv

`/home/ubuntu/.hermes/hermes-agent/venv/bin/pm2` does **not exist**. The Node.js pm2 binary lives at:

```bash
/home/ubuntu/.hermes/node/bin/pm2
```

Symptom of wrong path: `bash: /home/ubuntu/.hermes/hermes-agent/venv/bin/pm2: No such file or directory`.

The Python venv has `uvicorn` (and other Python tools), but **NOT pm2**. pm2 is a Node.js tool that wraps Node processes — it can also wrap `python -u script.py` via `--interpreter none`.

## ⚠️ Pitfall 2 — Orphan Process Already on the Port

**Symptom**: `pm2 start` says "online" but then dies with `EADDRINUSE: address already in use 0.0.0.0:<port>` in stderr.

**Cause**: A previous session started the same Node app directly (`node server.js &` or as a backgrounded shell job) without going through PM2. PM2 doesn't know about it → tries to bind the same port → crash loop.

**Fix**:
```bash
# 1. Find the PID bound to the port
ss -tlnp 2>/dev/null | grep <port>
# user=((<command>,pid=<PID>,fd=<n>))

# 2. Inspect cwd to confirm it's actually your orphan (not a critical service)
ls -la /proc/<PID>/cwd

# 3. Kill it
kill <PID>
sleep 2
ss -tlnp 2>/dev/null | grep <port>  # should be empty now

# 4. Restart via pm2
/home/ubuntu/.hermes/node/bin/pm2 start server.js --name <unique-name> --cwd <path>
```

**Never blindly `kill -9` an unknown PID** — verify with `ls /proc/<PID>/cwd` first. The orphan process may be serving a different app on a non-obvious port.

## ⚠️ Pitfall 3 — pip `--user` Flag Fails Inside a venv

**Symptom**: `pip install --user -e .` returns:
```
ERROR: Can not perform a '--user' install. User site-packages are not visible in this virtualenv.
```

**Cause**: Python venvs intentionally disable `--user` to keep all deps inside the venv.

**Fix**: Just run `pip install -e .` without `--user` while the venv is active (or use the venv's `pip` binary directly):
```bash
/home/ubuntu/.hermes/hermes-agent/venv/bin/pip install -e .
```

**Also**: dependency conflicts are normal when adding new packages to a shared venv. Hermes Agent may show warnings like `hermes-agent 0.15.1 requires prompt_toolkit==3.0.52, but you have prompt-toolkit 3.0.43` — these are usually non-fatal. Verify the new package imports work:
```bash
/home/ubuntu/.hermes/hermes-agent/venv/bin/python -c "import <pkg>; print('<pkg> OK', <pkg>.__version__)"
```

## ⚠️ Pitfall 4 — Vite/React Frontend Returns 404 Because `dist/` Wasn't Built

**Symptom**: Backend `app.get('/api/health')` returns 200, but `app.get('/')` returns 404. Log shows:
```
Error: ENOENT: no such file or directory, stat '<repo>/dist/index.html'
```

**Cause**: The repo is split into `server/` (Express backend) + `src/` (Vite/React frontend). `server/index.js` does `app.use(express.static(path.join(__dirname, '..', 'dist')))` — but `dist/` only exists after `npm run build` in the repo root.

**Fix**:
```bash
cd <repo-root>   # NOT server/ or src/
npm run build    # runs tsc -b && vite build → produces dist/
# Now backend serves the SPA from dist/
```

For dev hot-reload, use `npm run dev` (Vite) + `npm start` (backend) — but those are dev workflows, not PM2 services.

## ⚠️ Pitfall 5 — "Empty" GitHub Pages Repo (Only CNAME, No `index.html`)

**Symptom**: Cloned repo has only:
```
.git/
CNAME          # contains custom domain like "example.me"
README.md      # single line like "# example"
```

**Cause**: The repo is a **GitHub Pages config stub** — no actual site content. The `CNAME` just tells GitHub Pages what custom domain to bind. The actual HTML lives in a different branch or hasn't been written yet.

**Decision**:
- Don't deploy as a static site (`python -m http.server` would serve an empty directory)
- Don't try to "fix" by adding an `index.html` (user hasn't asked for that)
- Mention it in the deploy report so user knows the repo is a config stub, not a deployable site

## Port Allocation Strategy

For multi-service deploys on a single VPS:

| Port Range | Convention |
|---|---|
| 80, 443 | Nginx reverse proxy only |
| 3000-3999 | Standalone Node.js apps (Next.js, Vite preview) |
| 5000-5999 | Flask / Python web apps (dev defaults) |
| 8000-8999 | FastAPI / uvicorn defaults |
| 9000-9999 | Custom internal services (cf-proxy, autoteam) |
| 10000+ | Long-running tools (crawler, scraper) |

Reserve a **dedicated high-numbered port range per project family** to make collisions easy to spot:
- `87xx` for Cloudflare proxies (cf-proxy = 8750)
- `91xx` for Hermes-managed services (cf-tempemail 9124, hermes-miniapp 9122, autoteam 9126)
- `34xx` for LLM gateways (9router 3457)

Check before each deploy:
```bash
ss -tlnp 2>/dev/null | sort -t: -k2 -n | tail -20
# See the actual layout — don't assume ports are free
```

## Skipping Repos That Can't Run On This VPS

Common reasons to skip a GitHub repo even when user says "deploy all":

| Skip reason | Example |
|---|---|
| GPU-required | hash256-cli-with-gpu, comfyui workflows |
| External service dependency | Kiro-Auto-Pro needs GSuite list, malware scanner needs C2 server |
| Bot/script (not service) | 9router-auto-login-antigravity = `python3 bot.py` one-shot |
| Browser-only (no headless support) | aws-builder-id needs undetected-chromedriver, OOMs on 2GB VPS |
| Resource-heavy | LLM training repos, browser-automation servers |

Always present skip reasons in the deploy report — never silently omit.

## Final Health Check After Batch Deploy

```bash
# 1. PM2 status — all "online", none crashing
/home/ubuntu/.hermes/node/bin/pm2 list

# 2. Port reachability per service
for p in 8750 9122 9126; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:$p 2>/dev/null)
  echo "port $p → $code"
done

# 3. Memory headroom
free -h | head -2   # if available < 200MB, abort next deploy

# 4. PM2 memory per process (catches silent leaks)
/home/ubuntu/.hermes/node/bin/pm2 jlist | \
  python3 -c "import json,sys; ps=json.load(sys.stdin); [print(f\"  {p['name']:<22} mem={p.get('memory',0)//1024//1024}MB status={p['pm2_env']['status']}\") for p in ps]"
```

## Worked Example — Deploying 6 waguriagentic Repos

| Repo | Stack | Port | Skip? |
|---|---|---|---|
| 9router | Node + Electron tray | 3457 | already running, skip |
| cf-proxy | Node + Express | 8750 | deploy (orphan was already running, adopted) |
| cloudflare_temp_email | Python + SQLite | 9124 | already running, skip |
| hermes-miniapp-template | Node + Express + Vite | 9122 | deploy (server OK, frontend `dist/` not built — 404 on `/`) |
| AutoTeam | Python + FastAPI + uvicorn | 9126 | deploy (after `pip install -e .` in hermes-agent venv) |
| Kiro-Auto-Pro | Node + Camoufox | n/a | skip — needs GSuite list + VCC pool |
| kiro-register-en | Python + Tkinter GUI | n/a | skip — needs GSuite list + email provider |
| aws-builder-id | Python + undetected-chromedriver | n/a | skip — VPS 2GB no Chrome GUI |
| 9router-auto-login-antigravity | Python bot script | n/a | skip — bot, not service |
| waguriagentic.github.io | Empty repo (CNAME only) | n/a | skip — no `index.html` |
| equium-miner / h98-miner / hash256-cli / hash256-cli-with-gpu / slc-miner | mining | n/a | skip per user "kecuali miner" |

Final PM2 list after deploy:
```
5  waguri-cf-proxy       port 8750   200 OK
6  waguri-hermes-miniapp port 9122   /api/health 200, / 404 (frontend dist not built)
7  waguri-autoteam       port 9126   /docs 200
```

Resource: 1.4Gi used / 1.9Gi total → ~494MB headroom. Safe to deploy more.
