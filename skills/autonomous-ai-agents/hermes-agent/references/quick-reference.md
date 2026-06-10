# Hermes Agent — Quick Reference

## Provider Config Quick Reference

| Provider | base_url | default_model | Key env var |
|----------|----------|---------------|-------------|
| MiMo | `https://token-plan-sgp.xiaomimimo.com/v1` | `mimo-v2.5-pro` | config.yaml or `XIAOMI_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `openrouter/owl-alpha` | `OPENROUTER_API_KEY` |
| 9Router (local) | `http://localhost:20128/v1` | `freellmapi/qwen3-coder-480b` | — |
| NVIDIA | `https://integrate.api.nvidia.com/v1` | `qwen/qwen3-coder-480b-a35b-instruct` | config.yaml or `NVIDIA_API_KEY` |

## API Key Management

```bash
# Set key (auto-routes to .env)
hermes config set OPENROUTER_API_KEY sk-or-...
hermes config set XIAOMI_API_KEY tp-...

# View current config
hermes config

# Check .env path
hermes config env-path
```

**Rule**: Secrets → `.env`, everything else → `config.yaml`. `hermes config set` auto-routes.

## Gateway Commands

```bash
# From VPS shell (NOT from inside the agent):
hermes gateway restart      # restart after config change
hermes gateway status       # check status

# If running as systemd:
systemctl --user restart hermes-gateway
```

**CRITICAL**: `hermes gateway restart` from inside the agent ALWAYS fails — the agent IS the gateway process. Tell the user to run from VPS shell.

## Config Hot-Reload

Hot-reload on next message (no restart):
- `model.*` (context_length, default, provider)
- `compression.*` (threshold, target_ratio)
- `display.*` (tool_progress, show_reasoning)

Require restart:
- API keys in `.env`
- Tool/skill config
- `terminal.*` backend changes

## Docs URLs

- Configuration: https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- Providers: https://hermes-agent.nousresearch.com/docs/integrations/providers
- CLI Reference: https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- Slash Commands: https://hermes-agent.nousresearch.com/docs/reference/slash-commands
- Full docs index: https://hermes-agent.nousresearch.com/docs/

## Deep Research Pattern (Browser Docs Extraction)

1. Navigate: `browser_navigate(url="https://hermes-agent.nousresearch.com/docs/...")`
2. Extract full article: `browser_console(expression="document.querySelector('article').innerText")`
3. If page times out: `browser_snapshot(full=true)` instead
4. GitHub raw: `browser_navigate(url="https://raw.githubusercontent.com/nousresearch/hermes-agent/main/README.md")`
5. GitHub API search requires auth — skip if no token configured

## Skill File Writing — Large Content

For large files (>50KB), use `write_file` tool directly instead of `skill_manage(action='write_file')`:

```python
# Preferred for large files
write_file(path="/home/ubuntu/.hermes/scripts/my_script.py", content="...")

# skill_manage write_file works for smaller files under skill directories
skill_manage(action='write_file', name='my-skill', file_path='scripts/helper.py', content="...")
```

## MiMo Connectivity Test

```python
import urllib.request, json
req = urllib.request.Request(
    "https://token-plan-sgp.xiaomimimo.com/v1/chat/completions",
    headers={"Content-Type": "application/json", "Authorization": "Bearer tp-..."},
    method="POST",
    data=json.dumps({"model": "mimo-v2.5-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}).encode()
)
resp = urllib.request.urlopen(req, timeout=15)
print(resp.status, json.loads(resp.read())["choices"][0]["message"]["content"])
```

**NOT** `api.mimo.ai` — DNS doesn't resolve. Use `token-plan-sgp.xiaomimimo.com`.
