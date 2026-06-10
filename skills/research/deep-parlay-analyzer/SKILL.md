---
name: deep-parlay-analyzer
description: "Combined deep parlay analysis — merges parlay-analysis v2 A-G and v3 H-X into one readable dashboard plus portfolio/parlay recommendations."
tags: [parlay, sports-betting, football, odds, ev, kelly, monte-carlo, portfolio]
version: 1.0
---

# Deep Parlay Analyzer Skill

Use this skill when the operator wants a **single, deeper parlay analysis** that combines all modules from `parlay-analysis`:

- v2 modules A-G:
  - A. Statistics
  - B. Market odds
  - C. Tactical matchup
  - D. Motivation
  - E. Monte Carlo
  - F. Value bet detection
  - G. Correlation/parlay construction
- v3 modules H-X:
  - H. Poisson exact scorelines
  - I. ELO ratings
  - J. Market efficiency
  - K. Sentiment/sharp-vs-public
  - L. Weather impact
  - M. Referee analysis
  - N. In-play momentum, if live state is provided
  - O. H2H/cross-league patterns
  - P. Market depth/line shopping
  - Q. Risk-adjusted returns
  - R. Portfolio optimizer/Kelly
  - S. Streak analysis
  - T. Goal timing
  - U. Alternative lines
  - V. Contrarian signals
  - W. Under/Over deep
  - X. BTTS deep

## Core Workflow

1. Load or normalize match data.
2. Prefer real/live odds if provided.
3. Run v2-style match analysis for A-G.
4. Run v3-style deep analysis for H-X.
5. Normalize v3 outputs where the legacy script has known issues:
   - Flashscore data may use `home`/`away`; normalize to `home_team`/`away_team`.
   - v3 `alternative_lines` expects probabilities, not percentages.
6. Produce two outputs:
   - **Operator dashboard:** short, readable, actionable.
   - **Deep module view:** full module breakdown for review.
7. End with:
   - Best single bets
   - Parlay recommendation
   - Avoid list
   - Kelly/portfolio sizing
   - Required live-odds check if odds are estimated

## Recommended CLI

```bash
DPA=~/.hermes/skills/research/deep-parlay-analyzer/scripts/deep_parlay_analyzer.py

# Full dashboard + deep report
python3 $DPA --file matches.json --bankroll 1000

# JSON output for automation
python3 $DPA --file matches.json --bankroll 1000 --json

# Use existing parlay-analysis JSON directly
python3 $DPA --file /tmp/wc_first2_analyzer.json --bankroll 100
```

## Polymarket Odds Integration

To use live Polymarket odds instead of estimated odds:

1. Search markets: `python3 ~/.hermes/skills/research/polymarket/scripts/polymarket.py search "Team A Team B"`
2. Get each outcome's market: `python3 polymarket.py market <slug>`
3. Convert Polymarket price to decimal odds: `decimal_odds = 1 / price` (e.g., 0.545 → 1.83)
4. Add to input JSON as `odds_by_bookmaker.Pinnacle` or replace main odds fields
5. Run analyzer — the EV calculation will use the real market odds

**Why this matters**: Estimated odds from Flashscore can diverge significantly from real market odds. Polymarket prices are live and reflect actual money flow. Using real odds improves EV accuracy.

## Known Pitfalls

1. **Estimated odds are not live odds**. Always recalculate when operator provides real book odds.
2. **Same-game parlays are correlated**; do not multiply probabilities blindly.
3. **Draw/Under angles often appear in World Cup opening matches** due tournament variance.
4. **v3 legacy `alternative_lines`** can receive percentages instead of probabilities; normalize before using.
5. **Do not paste large raw JSON to operator unless requested**.
6. **Friendly/qualification matches** (e.g., Indonesia vs Mozambique) have lower liquidity — model confidence should be adjusted down.
7. **FIFA ranking mismatch**: In friendlies, home advantage and squad selection matter more than FIFA rankings. A lower-ranked home team can be correctly favored.

## Input JSON

Supported formats:

```json
{
  "matches": [
    {
      "home_team": "Meksiko",
      "away_team": "Afrika Selatan",
      "league": "World Cup 2026 Group A",
      "kickoff": "11.06.2026 19:00",
      "odds_home": 1.85,
      "odds_draw": 3.40,
      "odds_away": 4.50,
      "home_fifa_rank": 7,
      "away_fifa_rank": 20
    }
  ],
  "contexts": [
    {
      "home_lambda": 0.84,
      "away_lambda": 0.348,
      "public_pct_home": 50,
      "weather": {"temp_c": 22, "humidity": 45, "wind_kmh": 10, "condition": "sunny"},
      "ref_stats": {"matches": 30, "yellow_avg": 3.8, "red_avg": 0.10, "penalty_per_game": 0.12, "home_win_pct": 0.48},
      "recent_results": ["W","W","D","W","W","D","L","W","W","D"],
      "odds_by_bookmaker": {
        "Pinnacle": {"home": 1.85, "draw": 3.40, "away": 4.50}
      }
    }
  ]
}
```

Legacy Flashscore-style keys are accepted:

```json
{"home": "Meksiko", "away": "Afrika Selatan", "date": "11.06.2026", "time": "19:00"}
```

The analyzer normalizes them internally.

## Output Style

Use a readable dashboard, not raw dump. **CRITICAL: Every analysis MUST include reasoning/paragraphs explaining WHY each verdict was given — not just tables and numbers.** The operator explicitly requested: "SAAT LU ANALISIS LU SEKALIAN KASIH ALESAN ATAU PERNYATAAN YA. BIAR ENAK DI BACA."

Format each match analysis with:
1. **VERDICT header** with emoji + one-line summary
2. **Module breakdown** — each module gets a 1-2 sentence explanation in Indonesian/English explaining what it means and why it matters
3. **Recommendation table** with reasoning column
4. **Avoid list** with specific reasons
5. **Parlay construction** with correlation explanation

Write for readability. Short paragraphs > dense bullet lists. The operator is a builder who wants to understand the logic, not just see output.

```text
🏟️ MATCH: Meksiko vs Afrika Selatan
Verdict: SKIP / SMALL / BET
Pick model: Home Win
Confidence: 47/100
Risk: High
Win prob: Home 45.5% | Draw 39.8% | Away 14.7%
Fair odds: Home 2.20 | Draw 2.51 | Away 6.80
Best EV: Draw @3.40, EV +35.3%
Totals: O2.5 11.9% | U2.5 88.1%
BTTS: Yes 16.5% | No 83.5%
Scorelines: 0-0 30.4%, 1-0 25.7%, 0-1 10.9%
Parlay: SKIP
```

## Decision Rules

- **BET single:** EV >= +5%, probability >= 25%, confidence >= 55.
- **SMALL single:** EV +2% to +5% or tactical angle strong but confidence 45-55.
- **SKIP:** EV < 0 or confidence < 45.
- **Parlay:** only combine 2+ positive-EV legs with low correlation.
- **Kelly:** use half-Kelly or 0.25 Kelly max for sportsbook parlays.
- **Avoid:** negative EV, low-confidence ML favorite, correlated same-game legs without adjustment.

## Known Pitfalls

1. **v2 analyzer defaults**: When real match data is missing (no H2H, no xG, no form data), `match_analyzer_v2.py` uses hardcoded default values (form 62/100, xG 1.4/1.2, etc.). This means multiple matches analyzed without real data will get IDENTICAL module A-F outputs. Always supplement with v3 deep modules and manual context.
2. **Estimated odds are not live odds**. Always recalculate when operator provides real book odds.
3. **Same-game parlays are correlated**; do not multiply probabilities blindly.
4. **Draw/Under angles often appear in World Cup opening matches** due tournament variance.
5. **v3 legacy `alternative_lines` can receive percentages instead of probabilities**; normalize before using.
6. **Do not paste large raw JSON to operator unless requested**.
7. **Polymarket integration**: Polymarket skill is read-only. For auto-bet, need EVM wallet with USDC on Polygon + EIP-712 signing. See `polymarket` skill limitations.
8. **Polymarket O/U gap**: Polymarket doesn't always have Over/Under markets — often only 1X2. When O/U markets are missing, compute from Poisson model (Module W) using `match_analyzer_v3.py` and present as AI-derived estimate, not market odds.
9. **Flashscore live score extraction**: Clicking match links on Flashscore via `browser_click` often fails to navigate (page stays on listing). Instead, use `browser_console` with JS: `document.querySelectorAll('.event__match')` and filter by team name. Scores appear inline in the listing (e.g., "Indonesia Mozambik 1 0" at half-time). Scroll down to find the match section if not visible in viewport. See `references/flashscore-scraping.md` for full JS selectors and extraction patterns.
10. **Live HT analysis adjustment**: When analyzing at half-time with a score (e.g., 1-0), adjust Poisson lambda for 2H: reduce home lambda by ~30% (fatigue/defensive play), keep away lambda similar. The pre-match full-game lambda overestimates 2H scoring.
