#!/usr/bin/env python3
"""
Advanced Parlay Analysis Toolkit
CUPANG AI AGENT — Extended calculators

Modules:
  - Line Shopping: compare odds across books
  - Arbitrage Detector: find sure-bet opportunities
  - Round Robin: generate all parlay combinations
  - Teaser Calculator: adjusted spreads with fixed odds
  - Middle Calculator: find middling opportunities
  - Monte Carlo Simulation: simulate parlay variance
  - Bankroll Manager: unit system, drawdown, risk of ruin
  - SGP Correlation Matrix: same-game parlay adjustments
  - Break-even Calculator: required win rate
  - CLV Tracker: closing line value analysis
  - Parlay Optimizer: find best leg combinations
  - No-Vig Fair Odds: market baseline extraction
"""

import math
import random
import itertools
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# 1. LINE SHOPPING — Compare odds across multiple sportsbooks
# ═══════════════════════════════════════════════════════════════════

def line_shop(books: Dict[str, float], market_type: str = "american") -> Dict:
    """
    Compare odds across sportsbooks.
    
    Args:
        books: {"DraftKings": -110, "FanDuel": -105, "Pinnacle": -108, ...}
        market_type: "american" or "decimal"
    
    Returns:
        Best odds, worst odds, spread, % edge from shopping
    """
    if not books:
        return {}
    
    if market_type == "american":
        decimals = {k: american_to_decimal(v) for k, v in books.items()}
    else:
        decimals = books
    
    best_book = max(decimals, key=decimals.get)
    worst_book = min(decimals, key=decimals.get)
    best_dec = decimals[best_book]
    worst_dec = decimals[worst_book]
    
    # Edge from shopping best vs worst
    edge_pct = ((best_dec / worst_dec) - 1) * 100
    
    # Edge vs market average
    avg_dec = sum(decimals.values()) / len(decimals)
    edge_vs_avg = ((best_dec / avg_dec) - 1) * 100
    
    # Pinnacle as baseline (if present)
    pinnacle_edge = None
    if "Pinnacle" in decimals:
        pinnacle_edge = ((best_dec / decimals["Pinnacle"]) - 1) * 100
    
    return {
        "best_book": best_book,
        "best_decimal": round(best_dec, 4),
        "best_american": round(decimal_to_american(best_dec), 0),
        "worst_book": worst_book,
        "worst_decimal": round(worst_dec, 4),
        "spread_bps": round(edge_pct * 100, 1),
        "edge_vs_worst_pct": round(edge_pct, 2),
        "edge_vs_avg_pct": round(edge_vs_avg, 2),
        "pinnacle_edge_pct": round(pinnacle_edge, 2) if pinnacle_edge else None,
        "all_books": {k: {"decimal": round(v, 4), "american": round(decimal_to_american(v), 0)}
                      for k, v in decimals.items()},
    }


# ═══════════════════════════════════════════════════════════════════
# 2. ARBITRAGE DETECTOR — Find sure-bet opportunities
# ═══════════════════════════════════════════════════════════════════

def detect_arbitrage(best_odds_per_outcome: List[Tuple[str, float]], 
                     total_stake: float = 1000) -> Dict:
    """
    Detect arbitrage across 2+ outcomes.
    
    Args:
        best_odds_per_outcome: [("Book A", 2.10), ("Book B", 1.95)] for 2-way market
        total_stake: total amount to distribute
    
    Returns:
        Is arb? Stakes per outcome, guaranteed profit
    """
    # Calculate implied probabilities
    implied = [1 / odds for _, odds in best_odds_per_outcome]
    total_implied = sum(implied)
    
    is_arb = total_implied < 1.0
    
    if not is_arb:
        return {
            "is_arbitrage": False,
            "total_implied_prob": round(total_implied, 4),
            "vig_pct": round((total_implied - 1) * 100, 2),
            "message": "No arbitrage — market has vig",
        }
    
    # Calculate stakes
    stakes = []
    for i, (book, odds) in enumerate(best_odds_per_outcome):
        stake = (total_stake * implied[i]) / total_implied
        stakes.append({
            "book": book,
            "odds_decimal": round(odds, 4),
            "odds_american": round(decimal_to_american(odds), 0),
            "stake": round(stake, 2),
            "payout": round(stake * odds, 2),
        })
    
    guaranteed_payout = stakes[0]["payout"]  # same for all in arb
    guaranteed_profit = guaranteed_payout - total_stake
    roi_pct = (guaranteed_profit / total_stake) * 100
    
    return {
        "is_arbitrage": True,
        "total_implied_prob": round(total_implied, 4),
        "arb_margin_pct": round((1 - total_implied) * 100, 2),
        "total_stake": total_stake,
        "guaranteed_profit": round(guaranteed_profit, 2),
        "roi_pct": round(roi_pct, 2),
        "stakes": stakes,
    }


# ═══════════════════════════════════════════════════════════════════
# 3. ROUND ROBIN — Generate all parlay combinations
# ═══════════════════════════════════════════════════════════════════

def round_robin(legs: List[Dict], parlay_sizes: List[int] = None,
                stake_per_parlay: float = 10) -> Dict:
    """
    Generate all round-robin parlay combinations.
    
    Args:
        legs: [{"name": "...", "decimal_odds": 2.10, "true_prob": 0.50}, ...]
        parlay_sizes: [2, 3] = all 2-leg and 3-leg combos. Default: all sizes.
        stake_per_parlay: stake per individual parlay
    """
    n = len(legs)
    if parlay_sizes is None:
        parlay_sizes = list(range(2, n + 1))
    
    combos = []
    total_cost = 0
    
    for size in parlay_sizes:
        for combo_indices in itertools.combinations(range(n), size):
            combo_legs = [legs[i] for i in combo_indices]
            dec_odds = [l["decimal_odds"] for l in combo_legs]
            true_probs = [l.get("true_prob", 0) for l in combo_legs]
            
            parlay_dec = 1.0
            combined_prob = 1.0
            for d, p in zip(dec_odds, true_probs):
                parlay_dec *= d
                combined_prob *= p
            
            profit_if_win = stake_per_parlay * (parlay_dec - 1)
            ev = (combined_prob * profit_if_win) - ((1 - combined_prob) * stake_per_parlay)
            
            combo_names = [legs[i]["name"] for i in combo_indices]
            
            combos.append({
                "legs": combo_names,
                "size": size,
                "decimal_odds": round(parlay_dec, 4),
                "american_odds": round(decimal_to_american(parlay_dec), 0),
                "combined_prob": round(combined_prob, 4),
                "stake": stake_per_parlay,
                "potential_profit": round(profit_if_win, 2),
                "ev": round(ev, 2),
            })
            total_cost += stake_per_parlay
    
    # Summary
    total_ev = sum(c["ev"] for c in combos)
    positive_ev = [c for c in combos if c["ev"] > 0]
    
    return {
        "total_combos": len(combos),
        "total_cost": round(total_cost, 2),
        "total_ev": round(total_ev, 2),
        "positive_ev_count": len(positive_ev),
        "best_combo": max(combos, key=lambda x: x["ev"]),
        "combos": combos,
    }


# ═══════════════════════════════════════════════════════════════════
# 4. TEASER CALCULATOR — Adjusted spreads with fixed odds
# ═══════════════════════════════════════════════════════════════════

def teaser_calc(legs: List[Dict], teaser_points: float = 6.0,
                teaser_odds: float = -110) -> Dict:
    """
    Calculate teaser with points added to spread/total.
    
    Args:
        legs: [{"name": "...", "original_line": -7.0, "side": "favorite"}, ...]
              side: "favorite" (add points), "underdog" (subtract), 
                    "over" (subtract total), "under" (add total)
        teaser_points: points to add (e.g., 6 for NFL 6-point teaser)
        teaser_odds: standard teaser pricing
    """
    adjusted = []
    for leg in legs:
        orig = leg["original_line"]
        side = leg.get("side", "favorite")
        
        if side in ("favorite", "over"):
            new_line = orig + teaser_points
        else:  # underdog, under
            new_line = orig - teaser_points
        
        adjusted.append({
            "name": leg["name"],
            "original_line": orig,
            "side": side,
            "teaser_line": new_line,
            "points_added": teaser_points,
        })
    
    dec_odds = american_to_decimal(teaser_odds)
    n_legs = len(legs)
    # Standard teaser pricing (varies by book)
    teaser_multipliers = {
        2: {6: -110, 6.5: -120, 7: -130},
        3: {6: +180, 6.5: +150, 7: +120},
        4: {6: +300, 6.5: +250, 7: +200},
        5: {6: +500, 6.5: +400, 7: +300},
        6: {6: +800, 6.5: +600, 7: +450},
    }
    
    if n_legs in teaser_multipliers:
        points_int = int(teaser_points) if teaser_points == int(teaser_points) else teaser_points
        if points_int in teaser_multipliers[n_legs]:
            suggested_odds = teaser_multipliers[n_legs][points_int]
            dec_odds = american_to_decimal(suggested_odds)
    
    payout_on_100 = 100 * dec_odds
    
    return {
        "teaser_points": teaser_points,
        "num_legs": n_legs,
        "teaser_odds_american": round(decimal_to_american(dec_odds), 0),
        "teaser_odds_decimal": round(dec_odds, 4),
        "payout_per_100": round(payout_on_100, 2),
        "legs": adjusted,
    }


# ═══════════════════════════════════════════════════════════════════
# 5. MIDDLE CALCULATOR — Find middling opportunities
# ═══════════════════════════════════════════════════════════════════

def middle_calc(bet_a: Dict, bet_b: Dict, stake: float = 100) -> Dict:
    """
    Calculate middle opportunity between two opposing bets.
    
    Args:
        bet_a: {"side": "Over 220.5", "odds": -110, "line": 220.5}
        bet_b: {"side": "Under 225.5", "odds": -110, "line": 225.5}
        stake: stake per side
    """
    dec_a = american_to_decimal(bet_a["odds"])
    dec_b = american_to_decimal(bet_b["odds"])
    
    line_a = bet_a["line"]
    line_b = bet_b["line"]
    
    # Check if middle exists
    has_middle = (line_a < line_b) if "Over" in bet_a.get("side", "") or "under" in bet_a.get("side", "").lower() else (line_a > line_b)
    
    # Outcomes
    # 1. Only A wins
    only_a = stake * (dec_a - 1) - stake
    # 2. Only B wins
    only_b = stake * (dec_b - 1) - stake
    # 3. Both win (middle hits)
    both_win = stake * (dec_a - 1) + stake * (dec_b - 1)
    # 4. Push on one side
    push_profit = stake * (dec_a - 1) if "push" in str(bet_a) else 0
    
    # Middle probability estimate (depends on the gap)
    # Wider gap = lower probability but higher reward
    gap = abs(line_b - line_a)
    
    return {
        "bet_a": bet_a,
        "bet_b": bet_b,
        "gap": gap,
        "has_middle": has_middle,
        "if_only_a_wins": round(only_a, 2),
        "if_only_b_wins": round(only_b, 2),
        "if_both_win_middle": round(both_win, 2),
        "worst_case_loss": round(-stake, 2),
        "total_at_risk": round(stake * 2, 2),
        "max_profit": round(both_win, 2),
        "max_loss": round(-stake * 2 + stake * min(dec_a, dec_b), 2),
        "message": f"Middle: {bet_a['side']} @ {line_a} / {bet_b['side']} @ {line_b} — gap {gap} pts" if has_middle else "No middle exists",
    }


# ═══════════════════════════════════════════════════════════════════
# 6. MONTE CARLO SIMULATION — Simulate parlay outcomes
# ═══════════════════════════════════════════════════════════════════

def monte_carlo_parlay(legs: List[Dict], stake: float, 
                       simulations: int = 100000,
                       bankroll: float = 1000,
                       sessions: int = 100) -> Dict:
    """
    Monte Carlo simulation of parlay outcomes.
    
    Args:
        legs: [{"name": "...", "decimal_odds": 2.10, "true_prob": 0.50}, ...]
        stake: bet amount per parlay
        simulations: number of MC trials
        bankroll: starting bankroll
        sessions: number of "sessions" to simulate for distribution
    """
    random.seed(42)
    
    parlay_dec = 1.0
    for leg in legs:
        parlay_dec *= leg["decimal_odds"]
    
    combined_prob = 1.0
    for leg in legs:
        combined_prob *= leg["true_prob"]
    
    # Single session simulation
    results = []
    for _ in range(simulations):
        # Each leg independently wins/loses
        won = True
        for leg in legs:
            if random.random() > leg["true_prob"]:
                won = False
                break
        
        if won:
            results.append(stake * (parlay_dec - 1))
        else:
            results.append(-stake)
    
    wins = sum(1 for r in results if r > 0)
    losses = simulations - wins
    avg_return = sum(results) / simulations
    std_dev = (sum((r - avg_return) ** 2 for r in results) / simulations) ** 0.5
    
    # Bankroll simulation over sessions
    bankroll_paths = []
    busts = 0
    for _ in range(1000):
        br = bankroll
        path = [br]
        busted = False
        for _ in range(sessions):
            if br < stake:
                busted = True
                break
            won = random.random() < combined_prob
            if won:
                br += stake * (parlay_dec - 1)
            else:
                br -= stake
            path.append(br)
        bankroll_paths.append(path[-1])
        if busted:
            busts += 1
    
    # Percentiles
    bankroll_paths.sort()
    p5 = bankroll_paths[int(len(bankroll_paths) * 0.05)]
    p25 = bankroll_paths[int(len(bankroll_paths) * 0.25)]
    p50 = bankroll_paths[int(len(bankroll_paths) * 0.50)]
    p75 = bankroll_paths[int(len(bankroll_paths) * 0.75)]
    p95 = bankroll_paths[int(len(bankroll_paths) * 0.95)]
    
    # Max drawdown estimate
    max_dd_pct = ((bankroll - p5) / bankroll) * 100 if p5 < bankroll else 0
    
    return {
        "simulations": simulations,
        "sessions_simulated": sessions,
        "parlay_decimal_odds": round(parlay_dec, 4),
        "combined_true_prob": round(combined_prob, 4),
        "stake": stake,
        "win_rate": round(wins / simulations * 100, 2),
        "avg_return_per_bet": round(avg_return, 2),
        "std_deviation": round(std_dev, 2),
        "sharpe_ratio": round(avg_return / std_dev, 3) if std_dev > 0 else 0,
        "theoretical_ev": round((combined_prob * stake * (parlay_dec - 1)) - ((1 - combined_prob) * stake), 2),
        "bankroll_outcomes": {
            "starting": bankroll,
            "bust_rate_pct": round(busts / 1000 * 100, 1),
            "p5_worst": round(p5, 2),
            "p25": round(p25, 2),
            "median": round(p50, 2),
            "p75": round(p75, 2),
            "p95_best": round(p95, 2),
            "max_drawdown_pct": round(max_dd_pct, 1),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 7. BANKROLL MANAGER — Unit system, risk management
# ═══════════════════════════════════════════════════════════════════

def bankroll_manager(bankroll: float, num_bets: int, 
                     avg_odds_american: float = -110,
                     win_rate: float = 0.525,
                     unit_pct: float = 0.02) -> Dict:
    """
    Bankroll management analysis.
    
    Args:
        bankroll: starting bankroll
        num_bets: planned number of bets
        avg_odds_american: average odds bet
        win_rate: expected win rate
        unit_pct: unit size as % of bankroll
    """
    unit_size = bankroll * unit_pct
    dec_odds = american_to_decimal(avg_odds_american)
    
    # Expected return per bet
    ev_per_bet = (win_rate * unit_size * (dec_odds - 1)) - ((1 - win_rate) * unit_size)
    
    # Risk of Ruin (simplified)
    # Using gambler's ruin formula approximation
    q = 1 - win_rate
    if win_rate > 0.5:
        ror = (q / win_rate) ** (bankroll / unit_size)
    else:
        ror = 1.0  # guaranteed to go bust
    
    # Simulate
    random.seed(42)
    final_bankrolls = []
    max_drawdowns = []
    for _ in range(5000):
        br = bankroll
        peak = br
        max_dd = 0
        for _ in range(num_bets):
            br -= unit_size  # stake
            if random.random() < win_rate:
                br += unit_size * dec_odds  # payout
            peak = max(peak, br)
            dd = (peak - br) / peak
            max_dd = max(max_dd, dd)
        final_bankrolls.append(br)
        max_drawdowns.append(max_dd * 100)
    
    final_bankrolls.sort()
    max_drawdowns.sort()
    
    return {
        "bankroll": bankroll,
        "unit_size": round(unit_size, 2),
        "unit_pct": round(unit_pct * 100, 1),
        "num_bets": num_bets,
        "avg_odds": avg_odds_american,
        "expected_win_rate": round(win_rate * 100, 1),
        "ev_per_bet": round(ev_per_bet, 2),
        "total_ev": round(ev_per_bet * num_bets, 2),
        "risk_of_ruin_pct": round(ror * 100, 2),
        "projected_outcomes": {
            "p5_worst": round(final_bankrolls[int(len(final_bankrolls) * 0.05)], 2),
            "p25": round(final_bankrolls[int(len(final_bankrolls) * 0.25)], 2),
            "median": round(final_bankrolls[int(len(final_bankrolls) * 0.50)], 2),
            "p75": round(final_bankrolls[int(len(final_bankrolls) * 0.75)], 2),
            "p95_best": round(final_bankrolls[int(len(final_bankrolls) * 0.95)], 2),
        },
        "max_drawdown": {
            "median_pct": round(max_drawdowns[len(max_drawdowns) // 2], 1),
            "p95_worst_pct": round(max_drawdowns[int(len(max_drawdowns) * 0.95)], 1),
        },
        "recommendation": _bankroll_recommendation(ror, max_drawdowns[len(max_drawdowns) // 2]),
    }


def _bankroll_recommendation(ror: float, median_dd: float) -> str:
    if ror > 0.3:
        return "HIGH RISK — reduce unit size or improve edge"
    if ror > 0.1:
        return "MODERATE RISK — consider smaller units"
    if median_dd > 30:
        return "VOLATILE — expect 30%+ drawdowns regularly"
    return "MANAGED — unit sizing is appropriate"


# ═══════════════════════════════════════════════════════════════════
# 8. SGP CORRELATION MATRIX — Same-Game Parlay adjustments
# ═══════════════════════════════════════════════════════════════════

# Pre-built correlation coefficients for common SGP combos
SGP_CORRELATIONS = {
    # Format: (market_a, market_b) -> correlation coefficient
    ("team_spread", "team_ml"): 0.85,          # heavily correlated
    ("team_spread", "game_total"): 0.15,       # slight correlation
    ("team_ml", "game_total"): 0.10,
    ("team_spread", "team_total"): 0.70,
    ("player_points", "game_total"): 0.30,
    ("player_points", "team_ml"): 0.20,
    ("player_rebounds", "player_points"): 0.15,
    ("player_assists", "player_points"): 0.10,
    ("first_half_spread", "game_spread"): 0.60,
    ("first_half_total", "game_total"): 0.55,
    ("team_td_first", "team_ml"): 0.65,        # NFL: TD first scorer + ML
    ("pitcher_ks", "game_total"): -0.20,       # MLB: more Ks = less runs
    ("anytime_td_scorer", "team_ml"): 0.35,    # NFL
    ("player_3pm", "game_total"): 0.25,        # NBA
}


def sgp_adjust_prob(legs: List[Dict], custom_correlations: Dict = None) -> Dict:
    """
    Adjust combined probability for same-game parlay legs.
    
    Args:
        legs: [{"name": "...", "market_type": "team_ml", "true_prob": 0.55, "decimal_odds": 1.85}, ...]
        custom_correlations: override built-in correlations
    
    Returns:
        Adjusted combined probability, per-pair correlation breakdown
    """
    corr_table = {**SGP_CORRELATIONS}
    if custom_correlations:
        corr_table.update(custom_correlations)
    
    n = len(legs)
    
    # Independent combined probability
    independent_prob = 1.0
    for leg in legs:
        independent_prob *= leg["true_prob"]
    
    # Find pairwise correlations
    pair_correlations = []
    total_corr_adjustment = 0
    pairs_found = 0
    
    for i in range(n):
        for j in range(i + 1, n):
            mkt_a = legs[i].get("market_type", "unknown")
            mkt_b = legs[j].get("market_type", "unknown")
            
            # Check both orderings
            corr = corr_table.get((mkt_a, mkt_b), corr_table.get((mkt_b, mkt_a), 0))
            
            if corr != 0:
                pair_correlations.append({
                    "leg_a": legs[i]["name"],
                    "leg_b": legs[j]["name"],
                    "market_a": mkt_a,
                    "market_b": mkt_b,
                    "correlation": corr,
                })
                total_corr_adjustment += corr
                pairs_found += 1
    
    # Average correlation across pairs
    avg_corr = total_corr_adjustment / pairs_found if pairs_found > 0 else 0
    
    # Adjusted probability: P(A∩B∩C...) ≈ P_independent × (1 + avg_corr)
    adjusted_prob = independent_prob * (1 + avg_corr)
    adjusted_prob = min(adjusted_prob, 1.0)  # cap at 100%
    
    # EV impact
    parlay_dec = 1.0
    for leg in legs:
        parlay_dec *= leg["decimal_odds"]
    
    ev_independent = (independent_prob * (parlay_dec - 1)) - (1 - independent_prob)
    ev_adjusted = (adjusted_prob * (parlay_dec - 1)) - (1 - adjusted_prob)
    
    return {
        "num_legs": n,
        "independent_prob": round(independent_prob, 4),
        "avg_correlation": round(avg_corr, 3),
        "adjusted_prob": round(adjusted_prob, 4),
        "prob_difference": round(adjusted_prob - independent_prob, 4),
        "ev_impact": round((ev_adjusted - ev_independent) * 100, 2),
        "parlay_decimal_odds": round(parlay_dec, 4),
        "ev_independent_pct": round(ev_independent * 100, 2),
        "ev_adjusted_pct": round(ev_adjusted * 100, 2),
        "pair_correlations": pair_correlations,
        "warning": "⚠️ SGP odds from books already price in correlation — verify your edge against BOOK odds, not fair odds" if avg_corr > 0.2 else None,
    }


# ═══════════════════════════════════════════════════════════════════
# 9. BREAK-EVEN CALCULATOR
# ═══════════════════════════════════════════════════════════════════

def break_even(american_odds: float = None, decimal_odds: float = None,
               parlay_legs: List[float] = None) -> Dict:
    """
    Calculate break-even win rate for a bet or parlay.
    
    Args:
        american_odds: single bet American odds
        decimal_odds: single bet decimal odds
        parlay_legs: list of decimal odds for parlay legs
    """
    if decimal_odds is None and american_odds is not None:
        decimal_odds = american_to_decimal(american_odds)
    
    if parlay_legs:
        # Parlay break-even
        combined = 1.0
        for d in parlay_legs:
            combined *= d
        decimal_odds = combined
    
    if decimal_odds is None:
        return {"error": "Provide odds"}
    
    # Break-even: p × (dec - 1) = (1 - p) × 1
    # p = 1 / dec
    be_prob = 1 / decimal_odds
    be_american = decimal_to_american(decimal_odds)
    
    # Implied prob from odds (with vig)
    implied = 1 / decimal_odds
    
    # Edge needed
    if parlay_legs:
        leg_implied = [1 / d for d in parlay_legs]
        total_implied = sum(leg_implied)
        vig_per_leg = (total_implied / len(parlay_legs) - 1 / len(parlay_legs)) * 100
    
    return {
        "odds_decimal": round(decimal_odds, 4),
        "odds_american": round(be_american, 0),
        "break_even_prob": round(be_prob, 4),
        "break_even_win_rate": round(be_prob * 100, 2),
        "implied_prob": round(implied, 4),
        "message": f"Need {be_prob*100:.1f}% win rate to break even at {be_american:+.0f}",
        "parlay_breakdown": f"{len(parlay_legs)}-leg parlay" if parlay_legs else "Single bet",
    }


# ═══════════════════════════════════════════════════════════════════
# 10. CLV TRACKER — Closing Line Value
# ═══════════════════════════════════════════════════════════════════

def closing_line_value(bet_odds_american: float, closing_odds_american: float) -> Dict:
    """
    Calculate Closing Line Value (CLV).
    
    Positive CLV = you beat the market → long-term profitable signal.
    
    Args:
        bet_odds_american: odds when you placed the bet
        closing_odds_american: final odds at game start
    """
    bet_dec = american_to_decimal(bet_odds_american)
    close_dec = american_to_decimal(closing_odds_american)
    
    bet_prob = 1 / bet_dec
    close_prob = 1 / close_dec
    
    clv = close_prob - bet_prob  # positive = you got better odds
    clv_pct = (clv / close_prob) * 100
    
    # Also calculate in terms of odds improvement
    odds_improvement = ((bet_dec / close_dec) - 1) * 100
    
    return {
        "bet_odds": round(bet_odds_american, 0),
        "closing_odds": round(closing_odds_american, 0),
        "bet_decimal": round(bet_dec, 4),
        "closing_decimal": round(close_dec, 4),
        "bet_implied_prob": round(bet_prob * 100, 2),
        "closing_implied_prob": round(close_prob * 100, 2),
        "clv_pct": round(clv_pct, 2),
        "odds_improvement_pct": round(odds_improvement, 2),
        "verdict": _clv_verdict(clv_pct),
    }


def _clv_verdict(clv_pct: float) -> str:
    if clv_pct > 5:
        return "🟢 EXCELLENT CLV — strong long-term edge"
    if clv_pct > 2:
        return "🟢 GOOD CLV — positive signal"
    if clv_pct > 0:
        return "🟡 MARGINAL CLV — slight edge"
    if clv_pct > -2:
        return "🟡 NEUTRAL — market moved against you slightly"
    return "🔴 NEGATIVE CLV — you bet too early or on the wrong side"


# ═══════════════════════════════════════════════════════════════════
# 11. PARLAY OPTIMIZER — Find best leg combinations
# ═══════════════════════════════════════════════════════════════════

def optimize_parlay(available_legs: List[Dict], max_legs: int = 4,
                    min_edge_pct: float = 0, max_correlation: float = 0.3,
                    stake: float = 50) -> Dict:
    """
    Find optimal parlay combinations from available legs.
    
    Args:
        available_legs: [{"name": "...", "decimal_odds": 2.10, "true_prob": 0.50, "market_type": "..."}]
        max_legs: max parlay size
        min_edge_pct: minimum EV% per leg to include
        max_correlation: max allowed avg correlation between legs
        stake: stake per parlay
    """
    # Filter legs with positive edge
    viable_legs = []
    for leg in available_legs:
        ev_pct = (leg["true_prob"] * leg["decimal_odds"]) - 1
        if ev_pct * 100 >= min_edge_pct:
            leg["ev_pct"] = round(ev_pct * 100, 2)
            viable_legs.append(leg)
    
    if not viable_legs:
        return {"error": "No legs meet minimum edge requirement", "available": len(available_legs)}
    
    # Generate all combinations
    best_combos = []
    for size in range(2, min(max_legs + 1, len(viable_legs) + 1)):
        for combo in itertools.combinations(viable_legs, size):
            combo_list = list(combo)
            
            # Check correlation
            avg_corr = _estimate_avg_correlation(combo_list)
            if avg_corr > max_correlation:
                continue
            
            # Calculate combined
            parlay_dec = 1.0
            combined_prob = 1.0
            for leg in combo_list:
                parlay_dec *= leg["decimal_odds"]
                combined_prob *= leg["true_prob"]
            
            # Adjust for correlation
            adjusted_prob = combined_prob * (1 + avg_corr)
            
            ev = (adjusted_prob * (parlay_dec - 1)) - (1 - adjusted_prob)
            kelly = kelly_fraction(parlay_dec, adjusted_prob)
            
            best_combos.append({
                "legs": [l["name"] for l in combo_list],
                "size": size,
                "parlay_odds": round(parlay_dec, 4),
                "parlay_american": round(decimal_to_american(parlay_dec), 0),
                "combined_prob": round(adjusted_prob, 4),
                "ev_pct": round(ev * 100, 2),
                "kelly_fraction": round(kelly, 4),
                "avg_correlation": round(avg_corr, 3),
                "potential_profit": round(stake * (parlay_dec - 1), 2),
            })
    
    # Sort by EV
    best_combos.sort(key=lambda x: x["ev_pct"], reverse=True)
    
    return {
        "total_legs_evaluated": len(available_legs),
        "viable_legs": len(viable_legs),
        "total_combos": len(best_combos),
        "top_10": best_combos[:10],
        "best_combo": best_combos[0] if best_combos else None,
    }


def _estimate_avg_correlation(legs: List[Dict]) -> float:
    """Estimate average pairwise correlation for a set of legs."""
    n = len(legs)
    if n < 2:
        return 0
    
    total_corr = 0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            mkt_a = legs[i].get("market_type", "unknown")
            mkt_b = legs[j].get("market_type", "unknown")
            corr = SGP_CORRELATIONS.get((mkt_a, mkt_b), 
                   SGP_CORRELATIONS.get((mkt_b, mkt_a), 0))
            total_corr += abs(corr)
            pairs += 1
    
    return total_corr / pairs if pairs > 0 else 0


# ═══════════════════════════════════════════════════════════════════
# 12. NO-VIG FAIR ODDS — Extract market baseline
# ═══════════════════════════════════════════════════════════════════

def fair_odds_from_market(book_odds_american: List[float]) -> List[Dict]:
    """
    Remove vig from a set of market odds to get fair probabilities.
    
    Args:
        book_odds_american: [-110, -110] for 2-way market, [-200, +170, +400] for 3-way, etc.
    
    Returns:
        Fair probabilities and fair odds for each outcome
    """
    decimals = [american_to_decimal(o) for o in book_odds_american]
    implied = [1 / d for d in decimals]
    total_implied = sum(implied)
    
    vig_pct = (total_implied - 1) * 100
    
    results = []
    for i, (am, dec) in enumerate(zip(book_odds_american, decimals)):
        fair_prob = implied[i] / total_implied
        fair_dec = 1 / fair_prob
        fair_am = decimal_to_american(fair_dec)
        
        results.append({
            "outcome": i + 1,
            "book_odds_american": round(am, 0),
            "book_decimal": round(dec, 4),
            "implied_prob": round(implied[i] * 100, 2),
            "fair_prob": round(fair_prob * 100, 2),
            "fair_decimal": round(fair_dec, 4),
            "fair_american": round(fair_am, 0),
        })
    
    return {
        "num_outcomes": len(results),
        "total_implied_prob": round(total_implied * 100, 2),
        "vig_pct": round(vig_pct, 2),
        "outcomes": results,
    }


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (duplicated from base for standalone use)
# ═══════════════════════════════════════════════════════════════════

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


def kelly_fraction(decimal_odds: float, true_prob: float) -> float:
    b = decimal_odds - 1
    p = true_prob
    q = 1 - p
    if b <= 0:
        return -1
    return (b * p - q) / b


# ═══════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Advanced Parlay Analysis Toolkit")
    sub = parser.add_subparsers(dest="command")
    
    # line-shop
    p = sub.add_parser("line-shop", help="Compare odds across books")
    p.add_argument("--odds", required=True, help='JSON: {"Book": odds, ...}')
    
    # arb
    p = sub.add_parser("arb", help="Detect arbitrage")
    p.add_argument("--odds", required=True, help='JSON: [["Book", odds], ...]')
    p.add_argument("--stake", type=float, default=1000)
    
    # round-robin
    p = sub.add_parser("round-robin", help="Round robin combinations")
    p.add_argument("--file", required=True, help="JSON file with legs")
    p.add_argument("--stake", type=float, default=10)
    
    # teaser
    p = sub.add_parser("teaser", help="Teaser calculator")
    p.add_argument("--file", required=True, help="JSON file with legs")
    p.add_argument("--points", type=float, default=6.0)
    
    # middle
    p = sub.add_parser("middle", help="Middle calculator")
    p.add_argument("--bet-a", required=True, help='JSON: {"side": "...", "odds": -110, "line": 220.5}')
    p.add_argument("--bet-b", required=True, help='JSON: {"side": "...", "odds": -110, "line": 225.5}')
    p.add_argument("--stake", type=float, default=100)
    
    # monte-carlo
    p = sub.add_parser("monte-carlo", help="Monte Carlo simulation")
    p.add_argument("--file", required=True, help="JSON file with legs")
    p.add_argument("--stake", type=float, default=50)
    p.add_argument("--bankroll", type=float, default=1000)
    p.add_argument("--sims", type=int, default=100000)
    
    # bankroll
    p = sub.add_parser("bankroll", help="Bankroll management")
    p.add_argument("--bankroll", type=float, required=True)
    p.add_argument("--bets", type=int, default=100)
    p.add_argument("--odds", type=float, default=-110)
    p.add_argument("--win-rate", type=float, default=0.525)
    p.add_argument("--unit-pct", type=float, default=0.02)
    
    # sgp
    p = sub.add_parser("sgp", help="SGP correlation adjustment")
    p.add_argument("--file", required=True, help="JSON file with legs (need market_type)")
    
    # break-even
    p = sub.add_parser("break-even", help="Break-even calculator")
    p.add_argument("--odds", type=float, help="American odds")
    p.add_argument("--parlay", help="Comma-separated decimal odds")
    
    # clv
    p = sub.add_parser("clv", help="Closing Line Value")
    p.add_argument("--bet", type=float, required=True, help="Bet odds (American)")
    p.add_argument("--close", type=float, required=True, help="Closing odds (American)")
    
    # fair-odds
    p = sub.add_parser("fair-odds", help="Remove vig from market")
    p.add_argument("--odds", required=True, help="Comma-separated American odds")
    
    # optimize
    p = sub.add_parser("optimize", help="Optimize parlay combinations")
    p.add_argument("--file", required=True, help="JSON file with available legs")
    p.add_argument("--max-legs", type=int, default=4)
    p.add_argument("--min-edge", type=float, default=0)
    p.add_argument("--stake", type=float, default=50)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    import json as json_mod
    
    if args.command == "line-shop":
        books = json_mod.loads(args.odds)
        result = line_shop(books)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "arb":
        odds = json_mod.loads(args.odds)
        result = detect_arbitrage([(o[0], o[1]) for o in odds], args.stake)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "round-robin":
        with open(args.file) as f:
            data = json_mod.load(f)
        legs = data.get("legs", data) if isinstance(data, dict) else data
        result = round_robin(legs, stake_per_parlay=args.stake)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "teaser":
        with open(args.file) as f:
            data = json_mod.load(f)
        legs = data.get("legs", data) if isinstance(data, dict) else data
        result = teaser_calc(legs, teaser_points=args.points)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "middle":
        bet_a = json_mod.loads(args.bet_a)
        bet_b = json_mod.loads(args.bet_b)
        result = middle_calc(bet_a, bet_b, args.stake)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "monte-carlo":
        with open(args.file) as f:
            data = json_mod.load(f)
        legs = data.get("legs", data) if isinstance(data, dict) else data
        result = monte_carlo_parlay(legs, args.stake, args.sims, args.bankroll)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "bankroll":
        result = bankroll_manager(args.bankroll, args.bets, args.odds, args.win_rate, args.unit_pct)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "sgp":
        with open(args.file) as f:
            data = json_mod.load(f)
        legs = data.get("legs", data) if isinstance(data, dict) else data
        result = sgp_adjust_prob(legs)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "break-even":
        if args.parlay:
            legs = [float(x.strip()) for x in args.parlay.split(",")]
            result = break_even(parlay_legs=legs)
        else:
            result = break_even(american_odds=args.odds)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "clv":
        result = closing_line_value(args.bet, args.close)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "fair-odds":
        odds = [float(x.strip()) for x in args.odds.split(",")]
        result = fair_odds_from_market(odds)
        print(json_mod.dumps(result, indent=2))
    
    elif args.command == "optimize":
        with open(args.file) as f:
            data = json_mod.load(f)
        legs = data.get("legs", data) if isinstance(data, dict) else data
        result = optimize_parlay(legs, args.max_legs, args.min_edge, stake=args.stake)
        print(json_mod.dumps(result, indent=2))


if __name__ == "__main__":
    main()
