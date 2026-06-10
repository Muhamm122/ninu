---
name: polymarket
description: "Query Polymarket: markets, prices, orderbooks, history."
version: 1.0.0
author: Hermes Agent + Teknium
tags: [polymarket, prediction-markets, market-data, trading]
platforms: [linux, macos, windows]
---

# Polymarket — Prediction Market Data

Query prediction market data from Polymarket using their public REST APIs.
All endpoints are read-only and require zero authentication.

See `references/api-endpoints.md` for the full endpoint reference with curl examples.

## When to Use

- User asks about prediction markets, betting odds, or event probabilities
- User wants to know "what are the odds of X happening?"
- User asks about Polymarket specifically
- User wants market prices, orderbook data, or price history
- User asks to monitor or track prediction market movements

## Key Concepts

- **Events** contain one or more **Markets** (1:many relationship)
- **Markets** are binary outcomes with Yes/No prices between 0.00 and 1.00
- Prices ARE probabilities: price 0.65 means the market thinks 65% likely
- `outcomePrices` field: JSON-encoded array like `["0.80", "0.20"]`
- `clobTokenIds` field: JSON-encoded array of two token IDs [Yes, No] for price/book queries
- `conditionId` field: hex string used for price history queries
- Volume is in USDC (US dollars)

## Three Public APIs

1. **Gamma API** at `gamma-api.polymarket.com` — Discovery, search, browsing
2. **CLOB API** at `clob.polymarket.com` — Real-time prices, orderbooks, history
3. **Data API** at `data-api.polymarket.com` — Trades, open interest

## Typical Workflow

When a user asks about prediction market odds:

1. **Search** using the Gamma API public-search endpoint with their query
2. **Parse** the response — extract events and their nested markets
3. **Present** market question, current prices as percentages, and volume
4. **Deep dive** if asked — use clobTokenIds for orderbook, conditionId for history

## Presenting Results

Format prices as percentages for readability:
- outcomePrices `["0.652", "0.348"]` becomes "Yes: 65.2%, No: 34.8%"
- Always show the market question and probability
- Include volume when available

Example: `"Will X happen?" — 65.2% Yes ($1.2M volume)`

## Parsing Double-Encoded Fields

The Gamma API returns `outcomePrices`, `outcomes`, and `clobTokenIds` as JSON strings
inside JSON responses (double-encoded). When processing with Python, parse them with
`json.loads(market['outcomePrices'])` to get the actual array.

## Rate Limits

Generous — unlikely to hit for normal usage:
- Gamma: 4,000 requests per 10 seconds (general)
- CLOB: 9,000 requests per 10 seconds (general)
- Data: 1,000 requests per 10 seconds (general)

## Limitations

- This skill is read-only — it does not support placing trades
- Trading requires wallet-based crypto authentication (EIP-712 signatures)
- Some new markets may have empty price history
- Geographic restrictions apply to trading but read-only data is globally accessible
- **Not all matches have Over/Under markets** — Polymarket often only lists 1X2 (Win/Draw/Win) markets. When O/U is missing, compute from Poisson model via `deep-parlay-analyzer` skill.

## Known Pitfalls

1. **Search ambiguity**: Searching "Korea Czech" returns both FIFA World Cup and Winter Olympics markets. Always verify the event slug starts with `fifwc-` for FIFA World Cup matches.
2. **Date mismatch**: Polymarket slugs use the match date (e.g., `2026-06-11`), not the announcement date. Double-check dates when multiple matches between same teams exist.
3. **Draw market cancellation rule**: Draw markets resolve to "Yes" (draw) if the match is canceled entirely. This is different from team win markets which resolve to "No" on cancellation.
4. **Friendly matches**: Polymarket sometimes lists friendly/qualification matches (e.g., Indonesia vs Mozambique). These have lower liquidity and wider spreads — odds may not reflect true probabilities.
5. **O/U market gap**: For many matches (especially friendlies and smaller tournaments), Polymarket only has 1X2 markets — no Over/Under or BTTS. Don't assume O/U exists; check with `search` first. If missing, derive from Poisson model (Module W in v3 analyzer).
6. **Auto-bet blocker**: Polymarket trading requires EVM wallet with USDC on Polygon + EIP-712 signing. The `wallets.enc` vault password is unknown — cannot decrypt existing wallet. Options: (a) user provides correct password, (b) create new wallet, (c) manual bet based on analysis.

## Integration with Parlay Analysis

When the user wants to analyze sports matches with Polymarket odds:

1. **Search** Polymarket for the match: `python3 scripts/polymarket.py search "Team A Team B"`
2. **Get market details**: `python3 scripts/polymarket.py market <slug>` for each outcome
3. **Extract Polymarket implied probabilities** from outcomePrices (e.g., Yes: 54.5% / No: 45.5%)
4. **Feed into deep-parlay-analyzer** as `odds_by_bookmaker.Polymarket` in the input JSON
5. **Compare** Polymarket odds vs model odds to find edge

Example workflow:
```bash
# Step 1: Find the market
python3 polymarket.py search "Canada Bosnia"

# Step 2: Get odds for each outcome
python3 polymarket.py market "fifwc-can-bih-2026-06-12-can"
python3 polymarket.py market "fifwc-can-bih-2026-06-12-bih"
python3 polymarket.py market "fifwc-can-bih-2026-06-12-draw"

# Step 3: Build analyzer input with Polymarket odds
# Step 4: Run deep analysis
python3 ~/.hermes/skills/research/deep-parlay-analyzer/scripts/deep_parlay_analyzer.py \
  --file matches_with_poly_odds.json --bankroll 1000
```

**Key insight**: Polymarket prices ARE probabilities (price 0.545 = 54.5%). Compare directly with model implied probabilities to find value bets. When Polymarket odds diverge significantly from model odds, that's an edge opportunity.
