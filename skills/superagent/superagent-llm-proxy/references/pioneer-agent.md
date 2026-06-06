# Pioneer AI Agent Onboarding

## Overview

`pioneer_agent.py` automates the full Pioneer AI onboarding flow:
- Phase A: Google OAuth login (browser-automated)
- Phase B: Add credit card via Stripe
- Phase C: Run first inference + advance onboarding
- Phase D: Create API key (intercepted from network)
- Phase E: Verify key with real `/v1/chat/completions` call

## Location

`~/.hermes/skills/superagent/tools/pioneer_agent.py`

## Prerequisites

```bash
pip install cloakbrowser httpx
playwright install chromium
playwright install-deps chromium  # Linux only
```

## Required CONFIG

- `email` + `password` — Google account
- `card_number` + `exp_mm` + `exp_yy` + `cvc` + `zip` — Valid credit card (Stripe will reject test/dummy CCs)
- `proxy` — Optional residential proxy (recommended: Google flags AWS/datacenter IPs)

## Known Issues

| Issue | Solution |
|-------|----------|
| Google speedbump / unusual activity | Use residential proxy US. AWS IP almost always flagged. |
| Card declined | Try different CC. Stripe validates against BIN database. |
| API key not captured | UI may have changed. Check `/tmp/pioneer_*.png` screenshots. |
| OAuth challenge (2FA, captcha) | Cannot automate — user must intervene manually. |

## Output

- `~/pioneer_result.json` — API key + verified status
- `~/pioneer_run.log` — step-by-step log
- `~/.pioneer-profile/` — browser session (cached for re-runs)

## Security Notes

- **Never share Google credentials via chat** — too sensitive
- Run on local machine (home IP) for best OAuth success rate
- Script stores browser profile locally — re-runs skip Phase A if cookies valid


# Dummy CC Generator

## Overview

`cc_gen.py` generates Luhn-valid dummy credit card numbers from a BIN prefix.

## Location

`~/.hermes/skills/superagent/tools/cc_gen.py`

## Usage

```bash
python3 ~/.hermes/skills/superagent/tools/cc_gen.py <BIN> [count]
python3 ~/.hermes/skills/superagent/tools/cc_gen.py 6233586370 5
```

## Limitations

- Dummy CCs pass Luhn check but **will be rejected by Stripe/real payment processors**
- For testing payment forms only — not for actual transactions
