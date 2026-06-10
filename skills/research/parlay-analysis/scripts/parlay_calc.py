#!/usr/bin/env python3
"""
Sports Parlay Calculator
CUPANG AI AGENT — Parlay Analysis Toolkit

Usage:
  # Interactive mode
  python3 parlay_calc.py

  # Quick single-leg conversion
  python3 parlay_calc.py --odds +150

  # Quick parlay calc (decimal odds, comma-separated)
  python3 parlay_calc.py --parlay 2.10,1.85,1.95 --stake 50

  # Full analysis with JSON input
  python3 parlay_calc.py --file parlay_input.json
"""

import sys
import json
import argparse
from typing import List, Dict, Optional


# ─── ODDS CONVERSION ───────────────────────────────────────────────

def american_to_decimal(american: float) -> float:
    if american > 0:
        return (american / 100) + 1
    else:
        return (100 / abs(american)) + 1


def decimal_to_american(decimal: float) -> float:
    if decimal >= 2.0:
        return (decimal - 1) * 100
    else:
        return -100 / (decimal - 1)


def american_to_implied_prob(american: float) -> float:
    if american > 0:
        return 100 / (american + 100)
    else:
        return abs(american) / (abs(american) + 100)


def decimal_to_implied_prob(decimal: float) -> float:
    return 1 / decimal


def remove_vig_implied(probs: List[float]) -> List[float]:
    """Remove vig via multiplicative normalization."""
    total = sum(probs)
    return [p / total for p in probs]


# ─── PARLAY CALCULATION ────────────────────────────────────────────

def parlay_decimal_odds(legs: List[float]) -> float:
    """Calculate combined parlay decimal odds from list of leg decimals."""
    result = 1.0
    for d in legs:
        result *= d
    return result


def parlay_american_odds(legs_american: List[float]) -> float:
    """Calculate combined parlay American odds from list of leg American odds."""
    decimals = [american_to_decimal(a) for a in legs_american]
    return decimal_to_american(parlay_decimal_odds(decimals))


def parlay_payout(stake: float, decimal_odds: float) -> Dict:
    payout = stake * decimal_odds
    profit = payout - stake
    return {
        "stake": round(stake, 2),
        "decimal_odds": round(decimal_odds, 4),
        "american_odds": round(decimal_to_american(decimal_odds), 0),
        "payout": round(payout, 2),
        "profit": round(profit, 2),
    }


# ─── EXPECTED VALUE ────────────────────────────────────────────────

def ev_single(stake: float, decimal_odds: float, true_prob: float) -> Dict:
    """EV for a single bet."""
    profit_if_win = stake * (decimal_odds - 1)
    ev = (true_prob * profit_if_win) - ((1 - true_prob) * stake)
    ev_pct = (true_prob * decimal_odds) - 1
    return {
        "stake": round(stake, 2),
        "decimal_odds": round(decimal_odds, 4),
        "true_prob": round(true_prob, 4),
        "ev_dollar": round(ev, 2),
        "ev_percent": round(ev_pct * 100, 2),
    }


def ev_parlay(stake: float, leg_decimals: List[float], leg_true_probs: List[float]) -> Dict:
    """EV for a multi-leg parlay."""
    parlay_dec = parlay_decimal_odds(leg_decimals)
    combined_true_prob = 1.0
    for p in leg_true_probs:
        combined_true_prob *= p

    profit_if_win = stake * (parlay_dec - 1)
    ev = (combined_true_prob * profit_if_win) - ((1 - combined_true_prob) * stake)
    ev_pct = (combined_true_prob * parlay_dec) - 1

    return {
        "parlay_decimal_odds": round(parlay_dec, 4),
        "parlay_american_odds": round(decimal_to_american(parlay_dec), 0),
        "combined_true_prob": round(combined_true_prob, 4),
        "stake": round(stake, 2),
        "potential_profit": round(profit_if_win, 2),
        "ev_dollar": round(ev, 2),
        "ev_percent": round(ev_pct * 100, 2),
    }


# ─── KELLY CRITERION ───────────────────────────────────────────────

def kelly_fraction(decimal_odds: float, true_prob: float) -> float:
    """Full Kelly fraction. Negative = don't bet."""
    b = decimal_odds - 1
    p = true_prob
    q = 1 - p
    return (b * p - q) / b


def kelly_sizing(bankroll: float, decimal_odds: float, true_prob: float,
                 kelly_mult: float = 0.25) -> Dict:
    """Fractional Kelly recommended sizing."""
    full_kelly = kelly_fraction(decimal_odds, true_prob)
    if full_kelly < 0:
        return {
            "full_kelly": round(full_kelly, 4),
            "adjusted_kelly": 0,
            "recommended_bet": 0,
            "edge": "NEGATIVE — do not bet",
        }

    adjusted = full_kelly * kelly_mult
    bet = bankroll * adjusted
    return {
        "full_kelly": round(full_kelly, 4),
        "adjusted_kelly": round(adjusted, 4),
        "kelly_multiplier": kelly_mult,
        "bankroll": round(bankroll, 2),
        "recommended_bet": round(bet, 2),
        "edge": "POSITIVE",
    }


# ─── CORRELATION ───────────────────────────────────────────────────

def adjusted_combined_prob(leg_probs: List[float], correlation: float = 0.0) -> float:
    """
    Adjust combined probability for correlated legs.
    correlation: -1.0 to +1.0
    Positive = legs tend to hit together (same game, same team)
    Negative = legs are inversely related (hedging)
    """
    base = 1.0
    for p in leg_probs:
        base *= p

    # Apply pairwise correlation adjustment (simplified)
    n = len(leg_probs)
    if n == 2:
        return base * (1 + correlation)
    else:
        # For multi-leg, apply avg pairwise correlation
        return base * (1 + correlation)


# ─── HEDGE CALCULATOR ──────────────────────────────────────────────

def hedge_last_leg(parlay_stake: float, parlay_decimal_odds: float,
                   hedge_decimal_odds: float) -> Dict:
    """Calculate hedge bet for last remaining leg."""
    parlay_payout = parlay_stake * parlay_decimal_odds
    # Hedge covers the parlay stake loss
    hedge_stake = parlay_payout / (hedge_decimal_odds + parlay_decimal_odds)

    # Scenarios
    if_parlay_wins = parlay_payout - parlay_stake - hedge_stake
    if_hedge_wins = (hedge_stake * hedge_decimal_odds) - parlay_stake

    return {
        "parlay_stake": round(parlay_stake, 2),
        "parlay_payout": round(parlay_payout, 2),
        "hedge_stake": round(hedge_stake, 2),
        "hedge_odds_decimal": round(hedge_decimal_odds, 4),
        "if_parlay_wins": round(if_parlay_wins, 2),
        "if_hedge_wins": round(if_hedge_wins, 2),
        "guaranteed_profit": round(min(if_parlay_wins, if_hedge_wins), 2),
    }


# ─── DISPLAY ───────────────────────────────────────────────────────

def format_analysis(legs: List[Dict], stake: float, bankroll: float = 1000,
                    kelly_mult: float = 0.25, correlation: float = 0.0) -> str:
    """Full parlay analysis report."""
    lines = []
    lines.append("=" * 55)
    lines.append("  🎰 PARLAY ANALYSIS REPORT")
    lines.append("=" * 55)

    leg_decimals = []
    leg_true_probs = []

    # Per-leg analysis
    lines.append("\n📋 LEGS:")
    lines.append("-" * 55)
    for i, leg in enumerate(legs, 1):
        name = leg.get("name", f"Leg {i}")
        american = leg.get("american_odds", 0)
        decimal = leg.get("decimal_odds", american_to_decimal(american) if american else 0)
        true_prob = leg.get("true_prob", 0)
        market_prob = decimal_to_implied_prob(decimal)

        leg_decimals.append(decimal)
        leg_true_probs.append(true_prob)

        edge = true_prob - market_prob
        leg_ev = ev_single(stake, decimal, true_prob)

        lines.append(f"  {i}. {name}")
        lines.append(f"     Odds: {american:+.0f} (decimal: {decimal:.4f})")
        lines.append(f"     Market prob: {market_prob*100:.1f}%  |  Your prob: {true_prob*100:.1f}%")
        lines.append(f"     Edge: {edge*100:+.1f}%  |  EV: ${leg_ev['ev_dollar']:+.2f} ({leg_ev['ev_percent']:+.1f}%)")
        lines.append("")

    # Parlay calculation
    parlay_dec = parlay_decimal_odds(leg_decimals)
    parlay_info = parlay_payout(stake, parlay_dec)

    lines.append("🎰 PARLAY:")
    lines.append("-" * 55)
    lines.append(f"  Combined odds: {parlay_info['american_odds']:+.0f} (decimal: {parlay_info['decimal_odds']:.4f})")
    lines.append(f"  Stake: ${parlay_info['stake']:.2f}")
    lines.append(f"  Potential payout: ${parlay_info['payout']:.2f}")
    lines.append(f"  Potential profit: ${parlay_info['profit']:.2f}")

    # EV with correlation
    combined_prob = adjusted_combined_prob(leg_true_probs, correlation)
    parlay_ev = ev_parlay(stake, leg_decimals, leg_true_probs)
    adj_ev = ev_single(stake, parlay_dec, combined_prob)

    lines.append(f"\n  True combined prob (no corr): {parlay_ev['combined_true_prob']*100:.2f}%")
    if correlation != 0:
        lines.append(f"  Adjusted prob (ρ={correlation:+.2f}): {combined_prob*100:.2f}%")
        lines.append(f"  Adjusted EV: ${adj_ev['ev_dollar']:+.2f} ({adj_ev['ev_percent']:+.1f}%)")
    else:
        lines.append(f"  Combined EV: ${parlay_ev['ev_dollar']:+.2f} ({parlay_ev['ev_percent']:+.1f}%)")

    # Kelly sizing
    kelly_info = kelly_sizing(bankroll, parlay_dec, combined_prob, kelly_mult)
    lines.append(f"\n💰 KELLY SIZING ({kelly_mult}× Kelly):")
    lines.append("-" * 55)
    lines.append(f"  Bankroll: ${bankroll:.2f}")
    lines.append(f"  Full Kelly: {kelly_info['full_kelly']*100:.2f}%")
    lines.append(f"  Adjusted Kelly: {kelly_info['adjusted_kelly']*100:.2f}%")
    if kelly_info['recommended_bet'] > 0:
        lines.append(f"  Recommended bet: ${kelly_info['recommended_bet']:.2f}")
    else:
        lines.append(f"  ⚠️  {kelly_info['edge']}")

    # Correlation warning
    if correlation > 0.1:
        lines.append(f"\n⚠️  CORRELATION WARNING: ρ={correlation:+.2f}")
        lines.append("  Legs are positively correlated — true parlay probability")
        lines.append("  is LOWER than independent multiplication suggests.")

    lines.append("\n" + "=" * 55)
    return "\n".join(lines)


# ─── INTERACTIVE MODE ──────────────────────────────────────────────

def interactive_mode():
    print("=" * 55)
    print("  🎰 PARLAY CALCULATOR — Interactive Mode")
    print("=" * 55)
    print()

    legs = []
    while True:
        i = len(legs) + 1
        print(f"--- Leg {i} ---")
        name = input("  Name/description: ").strip() or f"Leg {i}"
        american = float(input("  American odds (e.g. +150, -110): "))
        true_prob = float(input("  Your estimated true probability (0-1): "))

        legs.append({
            "name": name,
            "american_odds": american,
            "decimal_odds": american_to_decimal(american),
            "true_prob": true_prob,
        })

        more = input("  Add another leg? (y/n): ").strip().lower()
        if more != 'y':
            break
        print()

    stake = float(input("\nStake ($): "))
    bankroll = float(input("Bankroll ($): ") or "1000")
    kelly_mult = float(input("Kelly multiplier (0.25 default): ") or "0.25")
    corr = float(input("Correlation factor (-1 to 1, 0=independent): ") or "0")

    print()
    print(format_analysis(legs, stake, bankroll, kelly_mult, corr))


# ─── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sports Parlay Calculator")
    parser.add_argument("--odds", type=float, help="Convert single American odds to decimal/prob")
    parser.add_argument("--parlay", type=str, help="Parlay decimal odds (comma-separated)")
    parser.add_argument("--stake", type=float, default=100, help="Stake amount (default: $100)")
    parser.add_argument("--bankroll", type=float, default=1000, help="Bankroll for Kelly (default: $1000)")
    parser.add_argument("--kelly", type=float, default=0.25, help="Kelly multiplier (default: 0.25)")
    parser.add_argument("--corr", type=float, default=0, help="Correlation factor (default: 0)")
    parser.add_argument("--file", type=str, help="JSON file with leg definitions")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    # Single odds conversion
    if args.odds:
        dec = american_to_decimal(args.odds)
        prob = american_to_implied_prob(args.odds)
        print(f"American: {args.odds:+.0f}")
        print(f"Decimal: {dec:.4f}")
        print(f"Implied Probability: {prob*100:.2f}%")
        return

    # Quick parlay calc
    if args.parlay:
        decimals = [float(x.strip()) for x in args.parlay.split(",")]
        result = parlay_payout(args.stake, parlay_decimal_odds(decimals))
        print(f"Legs: {len(decimals)}")
        for i, d in enumerate(decimals, 1):
            print(f"  Leg {i}: {d:.4f} ({decimal_to_american(d):+.0f})")
        print(f"Parlay odds: {result['decimal_odds']:.4f} ({result['american_odds']:+.0f})")
        print(f"Stake: ${result['stake']:.2f}")
        print(f"Payout: ${result['payout']:.2f}")
        print(f"Profit: ${result['profit']:.2f}")
        return

    # JSON file input
    if args.file:
        with open(args.file) as f:
            data = json.load(f)
        legs = data.get("legs", [])
        stake = data.get("stake", args.stake)
        bankroll = data.get("bankroll", args.bankroll)
        kelly_mult = data.get("kelly_mult", args.kelly)
        corr = data.get("correlation", args.corr)
        print(format_analysis(legs, stake, bankroll, kelly_mult, corr))
        return

    # Interactive
    interactive_mode()


if __name__ == "__main__":
    main()
