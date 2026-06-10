#!/usr/bin/env python3
"""
Match Analyzer & Parlay Recommendation Engine
CUPANG AI AGENT — Sports Betting Analysis

Gathers match data, calculates confidence scores, and generates
parlay recommendations in SAFE / MEDIUM / AGGRESSIVE tiers.

Usage:
  # Analyze specific matches
  python3 match_analyzer.py --matches "Lakers vs Celtics, Warriors vs Nuggets" --bankroll 500

  # Analyze from JSON input
  python3 match_analyzer.py --file matches.json --bankroll 500

  # Generate recommendations only (from pre-analyzed data)
  python3 match_analyzer.py --recommend --file analyzed_legs.json --bankroll 500
"""

import json
import math
import argparse
import sys
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# CONFIDENCE SCORE ENGINE
# ═══════════════════════════════════════════════════════════════════

# Weights for each analysis layer
WEIGHTS = {
    "form": 0.25,
    "players": 0.20,
    "stats": 0.25,
    "market": 0.20,
    "context": 0.10,
}


def calculate_confidence(scores: Dict[str, float]) -> Tuple[float, str]:
    """
    Calculate weighted confidence score from analysis layers.
    
    Args:
        scores: {"form": 80, "players": 70, "stats": 75, "market": 65, "context": 60}
    
    Returns:
        (score, tier_label)
    """
    total = 0
    for layer, weight in WEIGHTS.items():
        layer_score = scores.get(layer, 50)  # default 50 if missing
        total += layer_score * weight
    
    score = round(min(100, max(0, total)), 1)
    
    if score >= 80:
        tier = "🔒 LOCK"
    elif score >= 65:
        tier = "💪 STRONG"
    elif score >= 50:
        tier = "⚡ MODERATE"
    elif score >= 35:
        tier = "⚠️ RISKY"
    else:
        tier = "🎲 LONGSHOT"
    
    return score, tier


def score_form(last10_wins: int, last10_draws: int, last10_losses: int,
               home_away_modifier: float = 0) -> float:
    """Score team form from last 10 results."""
    points = (last10_wins * 3) + last10_draws
    max_points = 30
    base_score = (points / max_points) * 100
    
    # Apply home/away modifier (-10 to +10)
    return min(100, max(0, base_score + home_away_modifier))


def score_players(injuries: List[Dict], suspensions: List[Dict]) -> float:
    """
    Score player availability.
    
    Args:
        injuries: [{"name": "Player", "position": "ST", "impact": 4}, ...]
                  impact: 1=bench, 2=rotation, 3=starter, 4=key, 5=star
        suspensions: same format
    """
    if not injuries and not suspensions:
        return 100
    
    total_impact = 0
    for p in injuries:
        total_impact += p.get("impact", 2)
    for p in suspensions:
        total_impact += p.get("impact", 2)
    
    # Each impact point reduces score by ~8 points
    penalty = total_impact * 8
    return max(0, 100 - penalty)


def score_stats(xg_for: float, xg_against: float, 
                possession: float = 50, sot_ratio: float = 0.4,
                clean_sheet_pct: float = 0.3) -> float:
    """
    Score statistical profile.
    
    Args:
        xg_for: expected goals scored per game
        xg_against: expected goals conceded per game
        possession: average possession %
        sot_ratio: shots on target / total shots
        clean_sheet_pct: % of clean sheets
    """
    # xG differential (normalized: 0-2 range → 0-40 points)
    xg_diff = xg_for - xg_against
    xg_score = min(40, max(0, (xg_diff + 1) * 20))
    
    # Possession (40-60% is normal, bonus for extremes with context)
    poss_score = min(20, max(0, possession * 0.4))
    
    # Shot accuracy (0.3-0.5 is normal range)
    sot_score = min(20, max(0, sot_ratio * 40))
    
    # Clean sheets (0-50% range)
    cs_score = min(20, max(0, clean_sheet_pct * 40))
    
    return xg_score + poss_score + sot_score + cs_score


def score_market(opening_odds: float, current_odds: float,
                 public_pct: float = 50, sharp_side: str = None) -> float:
    """
    Score market signals.
    
    Args:
        opening_odds: opening American odds
        current_odds: current American odds
        public_pct: % of public bets on this side (0-100)
        sharp_side: "this" if sharp money on this side, "opposite" if against
    """
    score = 50  # baseline
    
    # Line movement (favorable = odds got better for us)
    if current_odds > opening_odds:
        score += 15  # line moved in our favor
    elif current_odds < opening_odds:
        score -= 10  # line moved against us
    
    # Sharp money indicator
    if sharp_side == "this":
        score += 20
    elif sharp_side == "opposite":
        score -= 15
    
    # Fade the public on lopsided action
    if public_pct > 70:
        score -= 10  # heavy public = usually wrong
    elif public_pct < 30:
        score += 10  # contrarian value
    
    return min(100, max(0, score))


def score_context(factors: Dict) -> float:
    """
    Score contextual factors.
    
    Args:
        factors: {
            "is_home": True,
            "is_derby": False,
            "motivation": "high",  # high/medium/low/none
            "schedule_congestion": 0,  # games in last 7 days
            "weather_impact": "none",  # none/low/medium/high
            "travel_fatigue": 0,  # timezone changes
        }
    """
    score = 50
    
    if factors.get("is_home"):
        score += 10
    
    if factors.get("is_derby"):
        score -= 5  # more unpredictable
    
    motivation = factors.get("motivation", "medium")
    mot_map = {"high": 15, "medium": 5, "low": -10, "none": -20}
    score += mot_map.get(motivation, 0)
    
    congestion = factors.get("schedule_congestion", 0)
    if congestion >= 3:
        score -= 15
    elif congestion >= 2:
        score -= 8
    
    weather = factors.get("weather_impact", "none")
    w_map = {"none": 0, "low": -3, "medium": -8, "high": -15}
    score += w_map.get(weather, 0)
    
    travel = factors.get("travel_fatigue", 0)
    score -= travel * 3
    
    return min(100, max(0, score))


# ═══════════════════════════════════════════════════════════════════
# MATCH ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_match(match: Dict) -> Dict:
    """
    Full match analysis.
    
    Args:
        match: {
            "home_team": "Lakers",
            "away_team": "Celtics",
            "competition": "NBA",
            "kickoff": "2025-01-15 19:30",
            "prediction": "Lakers ML",
            "odds_american": -120,
            "your_prob": 0.58,
            
            "home_form": {"wins": 7, "draws": 0, "losses": 3},
            "away_form": {"wins": 6, "draws": 0, "losses": 4},
            
            "home_injuries": [{"name": "AD", "impact": 5}],
            "away_injuries": [{"name": "Tatum", "impact": 4}],
            
            "home_xg": 115.2, "home_xga": 108.5,
            "away_xg": 112.8, "away_xga": 110.1,
            "home_possession": 52.3, "away_possession": 47.7,
            
            "opening_odds": -110, "current_odds": -120,
            "public_pct": 65, "sharp_side": "this",
            
            "context": {"is_home": True, "motivation": "high"}
        }
    """
    # Score each layer for the predicted outcome
    home_form = match.get("home_form", {})
    away_form = match.get("away_form", {})
    
    is_home_pick = match.get("prediction", "").lower().find("home") >= 0 or \
                   match.get("prediction", "").lower().find(match.get("home_team", "").lower()) >= 0
    
    if is_home_pick:
        form = score_form(
            home_form.get("wins", 5), home_form.get("draws", 2), home_form.get("losses", 3),
            home_away_modifier=5  # home advantage
        )
        injuries = match.get("home_injuries", [])
        suspensions = match.get("home_suspensions", [])
        xg_for = match.get("home_xg", 1.5)
        xg_against = match.get("home_xga", 1.2)
        possession = match.get("home_possession", 50)
    else:
        form = score_form(
            away_form.get("wins", 5), away_form.get("draws", 2), away_form.get("losses", 3),
            home_away_modifier=-3
        )
        injuries = match.get("away_injuries", [])
        suspensions = match.get("away_suspensions", [])
        xg_for = match.get("away_xg", 1.3)
        xg_against = match.get("away_xga", 1.4)
        possession = match.get("away_possession", 50)
    
    players = score_players(injuries, suspensions)
    stats = score_stats(xg_for, xg_against, possession,
                        match.get("sot_ratio", 0.4),
                        match.get("clean_sheet_pct", 0.3))
    market = score_market(
        match.get("opening_odds", match.get("odds_american", -110)),
        match.get("current_odds", match.get("odds_american", -110)),
        match.get("public_pct", 50),
        match.get("sharp_side")
    )
    context = score_context(match.get("context", {}))
    
    layer_scores = {
        "form": form,
        "players": players,
        "stats": stats,
        "market": market,
        "context": context,
    }
    
    confidence, tier = calculate_confidence(layer_scores)
    
    # Market probability
    odds = match.get("odds_american", -110)
    if odds > 0:
        market_prob = 100 / (odds + 100)
    else:
        market_prob = abs(odds) / (abs(odds) + 100)
    
    your_prob = match.get("your_prob", confidence / 100)
    edge = your_prob - market_prob
    
    return {
        "match": f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}",
        "competition": match.get("competition", "Unknown"),
        "kickoff": match.get("kickoff", "TBD"),
        "prediction": match.get("prediction", "TBD"),
        "odds_american": odds,
        "odds_decimal": round(american_to_decimal(odds), 4),
        "market_prob": round(market_prob * 100, 1),
        "your_prob": round(your_prob * 100, 1),
        "edge_pct": round(edge * 100, 1),
        "confidence": confidence,
        "tier": tier,
        "layer_scores": layer_scores,
        "reasoning": generate_reasoning(match, layer_scores, edge),
    }


def generate_reasoning(match: Dict, scores: Dict, edge: float) -> str:
    """Generate 2-3 sentence reasoning for the pick."""
    parts = []
    
    # Form
    if scores["form"] >= 70:
        parts.append("Strong recent form")
    elif scores["form"] >= 50:
        parts.append("Decent form")
    else:
        parts.append("Poor recent form is a concern")
    
    # Players
    if scores["players"] >= 80:
        parts.append("full squad available")
    elif scores["players"] >= 60:
        parts.append("some absences but manageable")
    else:
        parts.append("significant injury concerns")
    
    # Market
    if edge > 0.05:
        parts.append(f"model shows {edge*100:.1f}% edge over market")
    elif edge > 0:
        parts.append("slight edge detected")
    else:
        parts.append("no clear market edge — proceed with caution")
    
    return ". ".join(parts) + "."


# ═══════════════════════════════════════════════════════════════════
# PARLAY RECOMMENDATION ENGINE
# ═══════════════════════════════════════════════════════════════════

def generate_recommendations(analyzed_legs: List[Dict], bankroll: float = 1000,
                             kelly_mult: float = 0.25) -> Dict:
    """
    Generate SAFE / MEDIUM / AGGRESSIVE parlay recommendations.
    
    Args:
        analyzed_legs: output from analyze_match() for each leg
        bankroll: total bankroll
        kelly_mult: base Kelly multiplier
    """
    # Sort by confidence
    legs = sorted(analyzed_legs, key=lambda x: x["confidence"], reverse=True)
    
    # Filter viable legs (confidence >= 35, positive edge preferred)
    viable = [l for l in legs if l["confidence"] >= 35]
    
    if len(viable) < 2:
        return {"error": "Not enough viable legs (need ≥2 with confidence ≥35)"}
    
    # ── SAFE PARLAY: top 3 by confidence, all ≥ 65 ──
    safe_pool = [l for l in viable if l["confidence"] >= 65]
    safe_legs = safe_pool[:3] if len(safe_pool) >= 3 else safe_pool[:3]
    
    # ── MEDIUM PARLAY: top 4 by confidence, all ≥ 50 ──
    medium_pool = [l for l in viable if l["confidence"] >= 50]
    medium_legs = medium_pool[:4] if len(medium_pool) >= 4 else medium_pool[:4]
    
    # ── AGGRESSIVE PARLAY: top 5-6, all ≥ 35, include longshots ──
    agg_pool = viable
    # Add diversity: include at least 1 longshot if available
    longshots = [l for l in legs if l["confidence"] < 50 and l["confidence"] >= 35]
    agg_legs = agg_pool[:5]
    if longshots and len(agg_legs) < 6:
        agg_legs.append(longshots[0])
    
    def build_parlay(leg_list, tier_name, kelly_factor):
        if len(leg_list) < 2:
            return None
        
        parlay_dec = 1.0
        combined_prob = 1.0
        for l in leg_list:
            parlay_dec *= l["odds_decimal"]
            combined_prob *= (l["your_prob"] / 100)
        
        ev = (combined_prob * (parlay_dec - 1)) - (1 - combined_prob)
        
        # Kelly sizing
        kelly_full = kelly_fraction(parlay_dec, combined_prob)
        kelly_adj = max(0, kelly_full * kelly_factor)
        stake = round(bankroll * kelly_adj, 2)
        stake = max(stake, 0)
        
        potential_profit = round(stake * (parlay_dec - 1), 2) if stake > 0 else 0
        
        return {
            "tier": tier_name,
            "num_legs": len(leg_list),
            "legs": [{
                "match": l["match"],
                "prediction": l["prediction"],
                "odds": l["odds_american"],
                "confidence": l["confidence"],
                "tier": l["tier"],
            } for l in leg_list],
            "combined_decimal": round(parlay_dec, 4),
            "combined_american": round(decimal_to_american(parlay_dec), 0),
            "combined_prob": round(combined_prob * 100, 1),
            "ev_pct": round(ev * 100, 1),
            "kelly_full": round(kelly_full * 100, 2),
            "kelly_adjusted": round(kelly_adj * 100, 2),
            "stake": stake,
            "potential_profit": potential_profit,
            "risk_label": tier_risk(tier_name),
        }
    
    safe = build_parlay(safe_legs, "🟢 SAFE", kelly_mult * 2)
    medium = build_parlay(medium_legs, "🟡 MEDIUM", kelly_mult)
    aggressive = build_parlay(agg_legs, "🔴 AGGRESSIVE", kelly_mult * 0.5)
    
    # Bankroll summary
    total_risk = sum(p["stake"] for p in [safe, medium, aggressive] if p)
    max_potential = max((p["potential_profit"] for p in [safe, medium, aggressive] if p), default=0)
    
    return {
        "bankroll": bankroll,
        "total_legs_analyzed": len(analyzed_legs),
        "viable_legs": len(viable),
        "recommendations": {
            "safe": safe,
            "medium": medium,
            "aggressive": aggressive,
        },
        "bankroll_management": {
            "bankroll": bankroll,
            "total_risk": round(total_risk, 2),
            "risk_pct": round((total_risk / bankroll) * 100, 1),
            "max_potential_profit": round(max_potential, 2),
            "safe_stake": safe["stake"] if safe else 0,
            "medium_stake": medium["stake"] if medium else 0,
            "aggressive_stake": aggressive["stake"] if aggressive else 0,
        },
    }


def tier_risk(tier_name: str) -> str:
    if "SAFE" in tier_name:
        return "Low risk — consistent edge plays"
    elif "MEDIUM" in tier_name:
        return "Moderate risk — solid picks with variance"
    else:
        return "High risk — big payout potential, lower hit rate"


# ═══════════════════════════════════════════════════════════════════
# DISPLAY FORMATTER
# ═══════════════════════════════════════════════════════════════════

def format_match_analysis(analysis: Dict) -> str:
    """Format single match analysis for display."""
    lines = []
    lines.append("═" * 50)
    lines.append(f"  🏟️ {analysis['match']}")
    lines.append("═" * 50)
    lines.append(f"  Competition: {analysis['competition']}")
    lines.append(f"  Kickoff: {analysis['kickoff']}")
    lines.append("")
    lines.append(f"  📊 Prediction: {analysis['prediction']}")
    lines.append(f"  💰 Odds: {analysis['odds_american']:+.0f} (decimal: {analysis['odds_decimal']:.2f})")
    lines.append(f"  📈 Market prob: {analysis['market_prob']}%  |  Your prob: {analysis['your_prob']}%")
    lines.append(f"  🎯 Edge: {analysis['edge_pct']:+.1f}%")
    lines.append(f"  ⭐ Confidence: {analysis['confidence']}/100 {analysis['tier']}")
    lines.append("")
    lines.append(f"  📝 {analysis['reasoning']}")
    lines.append("")
    lines.append("  Layer scores:")
    for layer, score in analysis["layer_scores"].items():
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        lines.append(f"    {layer:10s} [{bar}] {score:.0f}")
    lines.append("═" * 50)
    return "\n".join(lines)


def format_recommendations(recs: Dict) -> str:
    """Format full parlay recommendations for display."""
    lines = []
    lines.append("\n" + "═" * 50)
    lines.append("  🎰 PARLAY RECOMMENDATIONS")
    lines.append("═" * 50)
    
    for tier_key, tier_name in [("safe", "🟢 SAFE PARLAY"), 
                                 ("medium", "🟡 MEDIUM PARLAY"),
                                 ("aggressive", "🔴 AGGRESSIVE PARLAY")]:
        parlay = recs["recommendations"][tier_key]
        if not parlay:
            continue
        
        lines.append(f"\n  {tier_name} ({parlay['num_legs']} legs)")
        lines.append("  " + "─" * 45)
        
        for i, leg in enumerate(parlay["legs"], 1):
            lines.append(f"    {i}. {leg['match']}")
            lines.append(f"       → {leg['prediction']} @ {leg['odds']:+.0f}")
            lines.append(f"       Confidence: {leg['confidence']}/100 {leg['tier']}")
        
        lines.append(f"\n    Combined: {parlay['combined_american']:+.0f} (decimal: {parlay['combined_decimal']:.2f})")
        lines.append(f"    Combined prob: {parlay['combined_prob']}%  |  EV: {parlay['ev_pct']:+.1f}%")
        lines.append(f"    Kelly: {parlay['kelly_full']:.2f}% (adj: {parlay['kelly_adjusted']:.2f}%)")
        lines.append(f"    Stake: ${parlay['stake']:.2f}  |  Potential: ${parlay['potential_profit']:.2f}")
        lines.append(f"    Risk: {parlay['risk_label']}")
    
    bm = recs["bankroll_management"]
    lines.append(f"\n  💰 BANKROLL MANAGEMENT")
    lines.append("  " + "─" * 45)
    lines.append(f"    Bankroll: ${bm['bankroll']:.2f}")
    lines.append(f"    Total risk: ${bm['total_risk']:.2f} ({bm['risk_pct']:.1f}%)")
    lines.append(f"    Max potential: ${bm['max_potential_profit']:.2f}")
    lines.append(f"    Safe: ${bm['safe_stake']:.2f}  |  Med: ${bm['medium_stake']:.2f}  |  Agg: ${bm['aggressive_stake']:.2f}")
    lines.append("\n" + "═" * 50)
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
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
    return max(0, (b * p - q) / b)


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Match Analyzer & Parlay Engine")
    parser.add_argument("--file", help="JSON file with match data")
    parser.add_argument("--bankroll", type=float, default=1000, help="Bankroll")
    parser.add_argument("--kelly", type=float, default=0.25, help="Kelly multiplier")
    parser.add_argument("--recommend-only", action="store_true", help="Skip analysis, generate recs from pre-analyzed legs")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.file:
        parser.print_help()
        print("\n📝 Example JSON input format:")
        print(json.dumps({
            "matches": [{
                "home_team": "Lakers",
                "away_team": "Celtics",
                "competition": "NBA",
                "kickoff": "2025-01-15 19:30",
                "prediction": "Lakers ML",
                "odds_american": -120,
                "your_prob": 0.58,
                "home_form": {"wins": 7, "draws": 0, "losses": 3},
                "away_form": {"wins": 6, "draws": 0, "losses": 4},
                "home_injuries": [{"name": "AD", "impact": 5}],
                "away_injuries": [{"name": "Tatum", "impact": 4}],
                "home_xg": 115.2, "home_xga": 108.5,
                "away_xg": 112.8, "away_xga": 110.1,
                "home_possession": 52.3,
                "opening_odds": -110, "current_odds": -120,
                "public_pct": 65, "sharp_side": "this",
                "context": {"is_home": True, "motivation": "high"}
            }]
        }, indent=2))
        return
    
    with open(args.file) as f:
        data = json.load(f)
    
    matches = data.get("matches", data if isinstance(data, list) else [data])
    
    # Analyze each match
    analyzed = []
    for match in matches:
        result = analyze_match(match)
        analyzed.append(result)
        if not args.json:
            print(format_match_analysis(result))
    
    # Generate recommendations
    recs = generate_recommendations(analyzed, args.bankroll, args.kelly)
    
    if args.json:
        output = {
            "analyzed_matches": analyzed,
            "recommendations": recs,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_recommendations(recs))


if __name__ == "__main__":
    main()
