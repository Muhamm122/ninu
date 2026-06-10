---
name: parlay-analysis
description: "Sports parlay analysis — odds conversion, EV calculation, Kelly criterion sizing, correlation detection, hedge calculator, line shopping, and multi-leg parlay optimization. Covers American/Decimal/Fractional odds formats."
tags: [parlay, sports-betting, odds, ev, kelly, hedge, correlation, gambling]
version: 1.0
---

# Parlay Analysis Skill

Analyze sports betting parlays: convert odds, calculate parlay payouts, compute expected value, size bets via Kelly criterion, detect correlated legs, and find optimal combinations.

## Core Concepts

### Odds Formats
- **American (Moneyline)**: +150 / -200. Positive = underdog payout on $100. Negative = amount to bet to win $100.
- **Decimal**: 2.50. Total return per $1 wagered (stake + profit).
- **Fractional**: 3/2. Profit per unit staked.

### Key Formulas

#### Odds Conversion
```
American → Decimal:
  if american > 0: decimal = (american / 100) + 1
  else: decimal = (100 / abs(american)) + 1

Decimal → American:
  if decimal >= 2: american = (decimal - 1) * 100
  else: american = -100 / (decimal - 1)

American → Implied Probability:
  if american > 0: prob = 100 / (american + 100)
  else: prob = abs(american) / (abs(american) + 100)
```

#### Parlay Payout
```
parlay_decimal_odds = leg1_decimal × leg2_decimal × ... × legN_decimal
parlay_payout = stake × parlay_decimal_odds
parlay_profit = stake × (parlay_decimal_odds - 1)
```

#### True Probability (removing vig)
```
# Method: multiplicative normalization
raw_prob_sum = sum(implied_probs)
true_prob_i = implied_prob_i / raw_prob_sum
```

#### Expected Value (EV)
```
EV = (true_prob × profit_if_win) - ((1 - true_prob) × stake)
EV% = (true_prob × decimal_odds) - 1
```

#### Kelly Criterion
```
# Fractional Kelly (recommended: 0.25 to 0.5 Kelly)
f* = (bp - q) / b
  where b = decimal_odds - 1 (net odds)
        p = true probability of winning
        q = 1 - p (probability of losing)
  f* = fraction of bankroll to bet (if negative → don't bet)
```

#### Correlation Detection
```
# Two legs are correlated if:
# 1. Same game (e.g., team A spread + over total)
# 2. Same sport/team streak dependencies
# 3. Weather/injury factors affect multiple props
#
# Correlation factor: -1.0 to +1.0
# Positive correlation → parlay odds OVERSTATE true combined probability
# Negative correlation → hedging opportunity
#
# Adjusted combined probability:
# P(A and B) = P(A) × P(B) × (1 + ρ)
# where ρ = correlation coefficient
```

#### Hedge Calculator
```
# Given current parlay position and last leg remaining:
hedge_stake = (parlay_potential_profit + parlay_stake) / (hedge_decimal_odds + 1)
guaranteed_profit = parlay_potential_profit - hedge_stake
```

## Workflow: Analyze a Parlay

### Step 1: Input legs
Collect each leg: sport, event, market (ML/spread/total/prop), line, odds, and your estimated true probability.

### Step 2: Convert all odds to decimal
Normalize to decimal for calculation.

### Step 3: Calculate parlay odds and payout
Multiply decimal odds across all legs.

### Step 4: Assess true probabilities
Remove vig from market odds. Compare with your estimated edge.

### Step 5: Calculate EV per leg and combined
Positive EV legs = edge. Negative EV legs = bleed.

### Step 6: Check correlations
Flag legs from same game, same team, or correlated outcomes.

### Step 7: Size via Kelly
Use fractional Kelly (0.25×) for bankroll management.

### Step 8: Report
Output: parlay odds, payout, combined EV, per-leg breakdown, correlation warnings, recommended sizing.

## Python Scripts

### Base Calculator — `scripts/parlay_calc.py`
Odds conversion, parlay payout, EV, Kelly sizing, hedge, correlation.
```bash
python3 ~/.hermes/skills/research/parlay-analysis/scripts/parlay_calc.py --odds +150
python3 ~/.hermes/skills/research/parlay-analysis/scripts/parlay_calc.py --parlay 2.10,1.85,1.95 --stake 50
python3 ~/.hermes/skills/research/parlay-analysis/scripts/parlay_calc.py --file parlay.json
python3 ~/.hermes/skills/research/parlay-analysis/scripts/parlay_calc.py --interactive
```

### Advanced Toolkit — `scripts/parlay_advanced.py`
12 advanced modules via subcommands:
```bash
ADV=~/.hermes/skills/research/parlay-analysis/scripts/parlay_advanced.py

# Line Shopping — compare odds across books
python3 $ADV line-shop --odds '{"DraftKings": -110, "FanDuel": -105, "Pinnacle": -108}'

# Arbitrage — detect sure-bet
python3 $ADV arb --odds '[["Book A", 2.15], ["Book B", 1.95]]' --stake 1000

# Round Robin — all combinations
python3 $ADV round-robin --file legs.json --stake 10

# Teaser — adjusted spreads
python3 $ADV teaser --file legs.json --points 6

# Middle — find middling opportunities
python3 $ADV middle --bet-a '{"side":"Over 220.5","odds":-110,"line":220.5}' --bet-b '{"side":"Under 225.5","odds":-110,"line":225.5}' --stake 100

# Monte Carlo — simulate variance
python3 $ADV monte-carlo --file legs.json --stake 50 --bankroll 1000 --sims 100000

# Bankroll Manager — unit sizing, risk of ruin
python3 $ADV bankroll --bankroll 1000 --bets 100 --odds -110 --win-rate 0.525 --unit-pct 0.02

# SGP Correlation — same-game parlay adjustments
python3 $ADV sgp --file sgp_legs.json

# Break-even — required win rate
python3 $ADV break-even --odds -110
python3 $ADV break-even --parlay 2.10,1.85,1.95

# CLV — closing line value tracker
python3 $ADV clv --bet -110 --close -120

# Fair Odds — remove vig
python3 $ADV fair-odds --odds "-110,-110"

# Optimize — find best parlay combos
python3 $ADV optimize --file all_legs.json --max-legs 4 --min-edge 2
```

### JSON Input Format
```json
{
  "stake": 50,
  "bankroll": 1000,
  "kelly_mult": 0.25,
  "correlation": 0.0,
  "legs": [
    {"name": "Lakers ML", "american_odds": 130, "decimal_odds": 2.30, "true_prob": 0.48, "market_type": "team_ml"},
    {"name": "Over 220.5", "american_odds": -110, "decimal_odds": 1.909, "true_prob": 0.55, "market_type": "game_total"}
  ]
}
```

## SGP Correlation Matrix (Built-in)

| Market A | Market B | ρ |
|---|---|---|
| team_spread | team_ml | 0.85 |
| team_spread | team_total | 0.70 |
| first_half_spread | game_spread | 0.60 |
| team_td_first (NFL) | team_ml | 0.65 |
| first_half_total | game_total | 0.55 |
| player_points | game_total | 0.30 |
| anytime_td (NFL) | team_ml | 0.35 |
| player_3pm (NBA) | game_total | 0.25 |
| player_points | team_ml | 0.20 |
| pitcher_ks (MLB) | game_total | -0.20 |

## Standard Teaser Pricing (NFL)

| Legs | 6pt | 6.5pt | 7pt |
|---|---|---|---|
| 2 | -110 | -120 | -130 |
| 3 | +180 | +150 | +120 |
| 4 | +300 | +250 | +200 |
| 5 | +500 | +400 | +300 |
| 6 | +800 | +600 | +450 |

## Pitfalls

1. **Vig inflation**: Market odds include bookmaker margin (~3-8%). Always remove vig before comparing to your model.
2. **Correlation blindness**: 3-leg parlay from same game is NOT independent. Adjust probabilities.
3. **Kelly over-betting**: Full Kelly is aggressive. Use 0.25× Kelly max for survival.
4. **Parlay tax**: Books profit more from parlays than singles. 4+ legs typically have negative EV even with slight edge per leg.
5. **Line movement**: Odds at bet time ≠ odds at analysis time. Record the actual odds used.
6. **Parlay cards/specials**: Promotional parlays often have worse pricing hidden in the structure.
7. **Polymarket odds ≠ bookmaker odds**: Polymarket prices are probabilities (0-1 scale), not decimal odds. Convert: `decimal_odds = 1 / price`. Polymarket also has lower liquidity on niche markets — spreads can be wide.
8. **Friendly match bias**: In friendlies/WC prep matches, market odds may overvalue home team due to public bias. Model should weight home advantage lower for friendlies vs competitive matches.

## Verification

After analysis, sanity-check:
- Parlay decimal odds should equal product of all leg decimals
- EV should be calculated with TRUE probability, not implied
- Kelly fraction should never be negative (skip those legs)
- Correlation adjustment should reduce combined probability for positively correlated legs

---

## Match Analysis Framework

### Analysis Pipeline (5 Layers)

#### Layer 1: Team Form (weight: 25%)
- Last 10 matches (W/D/L streak)
- Home vs Away split (separate records)
- Goal difference trend (improving/declining)
- Form rating: calculate points-per-game (PPG) last 10

#### Layer 2: Player Analysis (weight: 20%)
- Key player injuries (top scorer, playmaker, first-choice GK)
- Suspensions (yellow card accumulation, red card)
- Expected lineup changes (rotation risk mid-week)
- Impact score: rate each absence 1-5 on team performance

#### Layer 3: Statistical Analysis (weight: 25%)
- xG (expected goals) — for AND against
- xG differential = xG - xGA (positive = dominant)
- Possession % (contextual — counter-attack teams have low)
- Shots on target ratio (SoT / total shots)
- Clean sheet % (last 10 matches)
- Set piece efficiency (goals from corners/free kicks)

#### Layer 4: Market Analysis (weight: 20%)
- Odds movement: opening → current (steam moves = sharp action)
- Sharp money indicator: reverse line movement (line moves AGAINST public %)
- Public betting %: fade the public on lopsided action (>70% one side)
- Pinnacle as market baseline ( sharpest book)
- Line value: compare your model odds vs market odds

#### Layer 5: Contextual Factors (weight: 10%)
- Derby/rivalry factor (form goes out the window)
- Weather (rain/wind affects totals)
- Travel fatigue (distance, timezone)
- Motivation (relegation battle, title race, nothing to play for)
- Schedule congestion (3 games in 7 days)

### Confidence Score Calculation

```
raw_score = (
    form_score × 0.25 +
    player_score × 0.20 +
    stats_score × 0.25 +
    market_score × 0.20 +
    context_score × 0.10
)

confidence = clamp(raw_score, 0, 100)
```

Confidence tiers:
- 80-100: 🔒 LOCK — highest conviction
- 65-79: 💪 STRONG — solid edge
- 50-64: ⚡ MODERATE — decent probability
- 35-49: ⚠️ RISKY — proceed with caution
- 0-34: 🎲 LONGSHOT — lottery ticket only

---

## Parlay Recommendation Engine

### Output Format

```
🏟️ MATCH ANALYSIS
═══════════════════════════════════════
Match: [Team A] vs [Team B]
Competition: [League/Cup]
Kickoff: [Date/Time]

📊 FORM (L10): Team A [W-D-L] | Team B [W-D-L]
🏥 INJURIES: [Key absences]
📈 xG: Team A [xG] vs Team B [xG]
💰 LINE: [Odds] → movement [↑/↓/→]
🎯 MODEL PROB: [Your %] vs Market [%]

Prediction: [Outcome]
Confidence: [Score]/100 [Tier emoji]
Edge: [Your prob - market prob]%
Reasoning: [2-3 sentence summary]
═══════════════════════════════════════

🎰 PARLAY RECOMMENDATIONS
───────────────────────────────────────

🟢 SAFE PARLAY (3 legs, ~60% combined win rate)
  1. [Pick] @ [Odds] (confidence: XX)
  2. [Pick] @ [Odds] (confidence: XX)
  3. [Pick] @ [Odds] (confidence: XX)
  Combined: [Decimal odds] ([American])
  Stake: $XX | Potential: $XX

🟡 MEDIUM PARLAY (4 legs, ~35% combined win rate)
  1. [Pick] @ [Odds] (confidence: XX)
  2. [Pick] @ [Odds] (confidence: XX)
  3. [Pick] @ [Odds] (confidence: XX)
  4. [Pick] @ [Odds] (confidence: XX)
  Combined: [Decimal odds] ([American])
  Stake: $XX | Potential: $XX

🔴 AGGRESSIVE PARLAY (5 legs, ~15% combined win rate)
  1. [Pick] @ [Odds] (confidence: XX)
  2. [Pick] @ [Odds] (confidence: XX)
  3. [Pick] @ [Odds] (confidence: XX)
  4. [Pick] @ [Odds] (confidence: XX)
  5. [Pick] @ [Odds] (confidence: XX)
  Combined: [Decimal odds] ([American])
  Stake: $XX | Potential: $XX

💰 BANKROLL MANAGEMENT
───────────────────────────────────────
  Bankroll: $XXX
  Safe stake: $XX (2% Kelly)
  Medium stake: $XX (1% Kelly)
  Aggressive stake: $XX (0.5% Kelly)
  Max risk this card: $XX
  Expected return: $XX
```

### Parlay Construction Rules

**SAFE (3 legs):**
- All legs confidence ≥ 70
- No correlated legs from same game
- Mix markets (ML + Total + Spread)
- Combined true prob target: >55%
- Kelly: 2% of bankroll

**MEDIUM (4 legs):**
- All legs confidence ≥ 55
- Max 2 legs from same game (with correlation check)
- At least 1 underdog (odds > 2.00)
- Combined true prob target: >30%
- Kelly: 1% of bankroll

**AGGRESSIVE (5+ legs):**
- All legs confidence ≥ 40
- Can include longshots (odds > 3.00)
- Max 2 correlated legs
- Combined true prob target: >12%
- Kelly: 0.5% of bankroll

### Leg Selection Priority

1. **Highest edge** (your prob - market prob)
2. **Highest confidence** score
3. **Lowest correlation** with other selected legs
4. **Best line value** (beat Pinnacle closing)
5. **Diversify sports/markets** (don't stack same league)

---

### Flashscore Scraper — `scripts/flashscore_scraper.py`
Scrapes World Cup 2026 match data from Flashscore.co.id and exports in analyzer format.
```bash
FS=~/.hermes/skills/research/parlay-analysis/scripts/flashscore_scraper.py

# Print match summary with estimated odds
python3 $FS --summary

# Export for match_analyzer_v2.py
python3 $FS --export-analyzer --output wc2026.json

# Filter by date
python3 $FS --date 11.06.2026 --export-analyzer --output day1.json
```

### Browser Scraping (Live Data)
For live odds scraping from Flashscore:
1. Navigate to `https://www.flashscore.co.id/`
2. Click "PIALA DUNIA" → "JADWAL PERTANDINGAN" for match schedule
3. Click "PELUANG" for odds (requires JS render)
4. Use `browser_console` with JS selectors to extract data
5. Match detail pages have H2H, form, and lineup data

### Data Sources (for match analysis)

Use these to gather real data for analysis:

### Free APIs / Scrapers
- **Football-data.org**: EPL, La Liga, Serie A, Bundesliga, Ligue 1 results + fixtures
- **API-Football** (free tier): xG, lineups, injuries, standings
- **Odds API** (free tier): live odds from multiple books
- **Understat**: xG data for top 5 leagues
- **FBref**: advanced stats (possession, SoT, clean sheets)
- **Flashscore**: live scores, H2H, form (scrape via browser)
- **Covers.com**: public betting %

### Web Scraping Targets
- Odds movement: scrape Pinnacle/DK/FD for line history
- Injury news: scrape team Twitter/official sites
- Sharp money: compare line movement vs public %

### Data Collection Script
Use `scripts/match_analyzer.py` for automated data gathering + analysis.

### Match Analyzer & Recommendation Engine — `scripts/match_analyzer.py`
Full 5-layer analysis + parlay recommendation engine.
```bash
MA=~/.hermes/skills/research/parlay-analysis/scripts/match_analyzer.py

# Analyze matches + generate parlay recommendations
python3 $MA --file matches.json --bankroll 500 --kelly 0.25

# JSON output (for piping to other tools)
python3 $MA --file matches.json --bankroll 500 --json

# See example input format
python3 $MA
```

### Match Analysis JSON Input Format
```json
{
  "matches": [
    {
      "home_team": "Arsenal",
      "away_team": "Chelsea",
      "competition": "Premier League",
      "kickoff": "2025-01-15 20:00",
      "prediction": "Arsenal ML",
      "odds_american": -140,
      "your_prob": 0.62,
      "home_form": {"wins": 8, "draws": 1, "losses": 1},
      "away_form": {"wins": 5, "draws": 2, "losses": 3},
      "home_injuries": [],
      "away_injuries": [{"name": "Reece James", "impact": 3}],
      "home_xg": 2.1, "home_xga": 0.8,
      "away_xg": 1.6, "away_xga": 1.3,
      "home_possession": 55.2,
      "opening_odds": -130, "current_odds": -140,
      "public_pct": 72, "sharp_side": "opposite",
      "context": {"is_home": true, "motivation": "high", "is_derby": true}
    }
  ]
}
```

### Confidence Score Tiers
| Score | Tier | Description |
|---|---|---|
| 80-100 | 🔒 LOCK | Highest conviction |
| 65-79 | 💪 STRONG | Solid edge |
| 50-64 | ⚡ MODERATE | Decent probability |
| 35-49 | ⚠️ RISKY | Proceed with caution |
| 0-34 | 🎲 LONGSHOT | Lottery ticket only |

### Analysis Layer Weights
| Layer | Weight | What it measures |
|---|---|---|
| Team Form | 25% | Last 10 results, home/away split, goal diff trend |
| Player Analysis | 20% | Injuries, suspensions, lineup changes |
| Statistical | 25% | xG, possession, SoT ratio, clean sheets |
| Market | 20% | Odds movement, sharp money, public % |
| Context | 10% | Derby, weather, travel, motivation, congestion |

---

## Advanced Match Analyzer v2 — `scripts/match_analyzer_v2.py`

Full 7-module football analysis pipeline per the Elite Sports Betting Analyst framework.

### 7 Analysis Modules

**A. Statistical Analysis**
- Last 5 & Last 10 form (W/D/L, GF, GA)
- Home/Away performance split
- xG and xGA differential
- Shots on target, possession, clean sheet %
- Head-to-head record
- Injury/suspension impact scoring (1-5 scale)

**B. Odds Market Analysis**
- Opening → Current odds movement
- Implied probability extraction
- Bookmaker margin calculation
- Reverse Line Movement (RLM) detection
- Sharp money indicators
- Public betting bias (fade the public)
- Pinnacle closing line comparison
- Trap line detection

**C. Tactical Analysis**
- Formation matchup (midfield battle)
- Playing style clash (possession vs counter vs high press vs defensive)
- Pressing intensity comparison (PPDA)
- Set piece advantage
- Counter-attack threat assessment
- Key player matchup notes

**D. Motivation Analysis**
- Must-win / title race / relegation battle / qualification
- Derby/rivalry factor
- Rotation risk (upcoming important match)
- Schedule congestion (days rest)
- Travel distance fatigue
- Internal club issues

**E. Monte Carlo Simulation (50,000 sims)**
- Poisson-based goal simulation
- Attack/defense strength from xG + actual goals
- Injury and motivation adjustments
- Home advantage factor (1.15x)
- Output: 1X2 probs, O1.5/O2.5/BTTS probs, most likely scorelines, λ values

**F. Value Bet Detection**
- EV = (AI Probability × Decimal Odds) - 1
- AI prob from Monte Carlo vs market implied prob
- Edge calculation
- Classification: Positive / Neutral / Negative

**G. Correlation Analysis for Parlay**
- Pre-built correlation matrix for market combinations
- Same-match detection (minimum ρ=0.4)
- League concentration warnings
- Per-pair correlation breakdown

### Parlay Construction Rules

| Tier | Legs | Min Conf | Kelly | Risk |
|---|---|---|---|---|
| 🟢 SAFE | 2-3 | 70% | 2% bankroll | Low |
| 🟡 MEDIUM | 3-5 | 62% | 1% bankroll | Medium |
| 🔴 AGGRESSIVE | 5-8 | 50% | 0.5% bankroll | High |
### Output Format

Each match analysis includes all 7 modules with formatted output.
Parlay recommendations include correlation risk, recommended stake, potential payout.
Final judgment: best pick, best value bet, pick to avoid, main risks, betting advice.

**CRITICAL: Include reasoning paragraphs, not just numbers.** For each module and each verdict, write 1-2 sentences explaining WHY. The operator wants readable analysis with alasan/pernyataan, not raw data dumps. Match the operator's energy: direct, tactical, no fluff.

### CLI Usage
```bash
MA=~/.hermes/skills/research/parlay-analysis/scripts/match_analyzer_v2.py

# Full analysis + parlay recommendations
python3 $MA --file matches.json --bankroll 500 --kelly 0.25

# JSON output
python3 $MA --file matches.json --bankroll 500 --json

# Print example input format
python3 $MA --examples
```

---

## Deep Analysis v3 — `scripts/match_analyzer_v3.py`

13 advanced analysis modules (H-V) for elite-level betting intelligence:

| Module | Description |
|---|---|
| **H. Poisson Model** | Exact scoreline probabilities via Poisson distribution. Full matrix P(home_goals, away_goals) for all combinations. |
| **I. ELO Rating** | Chess-style ELO with home advantage (+100), goal difference modifier, K-factor 32. Dynamic team strength tracking. |
| **J. Market Efficiency** | Compares AI probability vs market implied probability per outcome. Flags underpriced/overpriced odds. |
| **K. Sentiment Analysis** | Crowd vs sharp divergence detection. Steam moves, reverse line movement, public bias, sharp score 0-100. |
| **L. Weather Impact** | Temperature, humidity, wind, rain/snow effects on scoring. Tactical implications (wet pitch → defense favored). |
| **M. Referee Analysis** | Card rate, penalty rate, home bias. Impacts card markets and match flow. |
| **N. In-Play Momentum** | Live match state evaluation. Momentum score, key moments, second-half trend prediction. |
| **O. Cross-League H2H** | Historical matchup patterns with competition weighting. Style-based projection when no direct H2H. |
| **P. Market Depth** | Multi-bookmaker odds comparison. Best/worst odds, fair odds (no vig), arbitrage detection, outlier identification. |
| **Q. Risk-Adjusted Returns** | Sharpe ratio, Sortino ratio for betting portfolios. Portfolio variance and total loss probability. |
| **R. Portfolio Optimizer** | Kelly sizing across multiple concurrent bets with correlation adjustment. Diversification scoring. |
| **S. Streak Analysis** | Win/loss/draw streak patterns, regression to mean signals, momentum scoring, streak frequency. |
| **T. Goal Timing** | 1H vs 2H scoring distribution, peak scoring periods, live betting timing tips, BTTS timing. |
| **U. Alternative Lines** | Best spreads and totals for each match based on Poisson model. Fair odds for each alternative line. |
| **V. Contrarian Signals** | Fade the public alerts. Combines 6 signal types into contrarian score 0-100 with actionable verdict. |
| **W. Under/Over Deep** | Full Poisson goal distribution, 15+ total lines, market value detection, scoring intensity classification |
| **X. BTTS Deep** | Poisson + profile + H2H blended BTTS probability, market value, clean sheet analysis |

### Under/Over Analysis (Module W) Features:
- **Poisson goal distribution** — P(exactly 0, 1, 2, 3... goals)
- **15+ total lines** — O/U 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.5
- **Expected goals** with variance and standard deviation
- **Scoring intensity** — 🔥 High / ⚡ Mod-High / 📊 Moderate / 🛡️ Low-Mod / 🔒 Low
- **Market value detection** — AI prob vs market odds per line
- **Contextual adjustments** — weather, referee, knockout
- **Alternative totals** — ranked by probability with fair odds

### BTTS Analysis (Module X) Features:
- **Poisson BTTS** — P(both score) from goal lambdas
- **Profile blend** — team BTTS% and clean sheet% history
- **H2H adjustment** — historical BTTS rate
- **Market value** — BTTS Yes/No vs market odds
- **Key factors** — clean sheet rates, attacking strength

### v3 CLI Usage
```bash
V3=~/.hermes/skills/research/parlay-analysis/scripts/match_analyzer_v3.py

# Deep analysis with all modules
python3 $V3 --file deep_matches.json

# JSON output
python3 $V3 --file deep_matches.json --json

# Print example input format
python3 $V3 --examples
```

### v3 JSON Input Format
```json
{
  "matches": [{"home_team": "Brazil", "away_team": "Morocco"}],
  "contexts": [{
    "home_lambda": 2.2, "away_lambda": 0.8,
    "odds_home": 1.45, "odds_draw": 4.20, "odds_away": 8.00,
    "public_pct_home": 78,
    "weather": {"temp_c": 30, "humidity": 60, "wind_kmh": 10, "condition": "sunny"},
    "ref_stats": {"matches": 50, "yellow_avg": 3.8, "red_avg": 0.10, "penalty_per_game": 0.12, "home_win_pct": 0.52},
    "recent_results": ["W","W","W","D","W","W","W","D","W","W"],
    "odds_by_bookmaker": {"Pinnacle": {"home": 1.45, "draw": 4.20, "away": 8.00}, ...}
  }]
}
```
