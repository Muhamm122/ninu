#!/usr/bin/env python3
"""
Advanced Match Analyzer v2 — Football/Soccer Edition
CUPANG AI AGENT — Sports Betting Analysis

Full 7-module analysis pipeline:
A. Statistical Analysis (L5/L10, H/A, xG, H2H, injuries)
B. Odds Market Analysis (movement, sharp money, RLM, margin)
C. Tactical Analysis (formation, style, pressing, set pieces)
D. Motivation Analysis (must-win, derby, rotation, congestion)
E. Monte Carlo Simulation (attack/defense strength, scorelines)
F. Value Bet Detection (EV, implied prob, value classification)
G. Correlation Analysis for Parlay construction

Usage:
  python3 match_analyzer_v2.py --file matches.json --bankroll 500
  python3 match_analyzer_v2.py --file matches.json --bankroll 500 --json
  python3 match_analyzer_v2.py --examples  # print example input format
"""

import json
import math
import random
import argparse
from typing import List, Dict, Tuple, Optional
from collections import Counter


# ═══════════════════════════════════════════════════════════════════
# A. STATISTICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_form(last5: Dict, last10: Dict) -> Dict:
    """
    Analyze team form from last 5 and last 10 matches.
    
    Input format:
      {"home": {"w": 3, "d": 1, "l": 1, "gf": 8, "ga": 4},
       "away": {"w": 4, "d": 0, "l": 1, "gf": 10, "ga": 3},
       "h2h": [{"home": 2, "away": 1}, {"home": 1, "away": 1}, ...]}
    """
    def form_score(w, d, l, gf, ga):
        total = w + d + l
        if total == 0:
            return 50
        pts = (w * 3) + d
        max_pts = total * 3
        ppg = pts / max_pts if max_pts > 0 else 0
        gd = gf - ga if (gf + ga) > 0 else 0
        gd_normalized = max(-1, min(1, gd / (total * 2)))  # -1 to 1
        return min(100, max(0, (ppg * 80) + (gd_normalized * 20) + 10))
    
    l5_home = form_score(**last5.get("home", {"w": 2, "d": 2, "l": 1, "gf": 5, "ga": 4}))
    l5_away = form_score(**last5.get("away", {"w": 2, "d": 2, "l": 1, "gf": 5, "ga": 4}))
    l10_home = form_score(**last10.get("home", {"w": 5, "d": 3, "l": 2, "gf": 12, "ga": 8}))
    l10_away = form_score(**last10.get("away", {"w": 5, "d": 3, "l": 2, "gf": 12, "ga": 8}))
    
    h2h = last10.get("h2h", [])
    h2h_home_wins = sum(1 for h in h2h if h.get("home", 0) > h.get("away", 0))
    h2h_away_wins = sum(1 for h in h2h if h.get("away", 0) > h.get("home", 0))
    h2h_draws = sum(1 for h in h2h if h.get("home", 0) == h.get("away", 0))
    h2h_total = len(h2h)
    
    h2h_edge = "Neutral"
    if h2h_total >= 2:
        if h2h_home_wins > h2h_away_wins + 1:
            h2h_edge = "Home"
        elif h2h_away_wins > h2h_home_wins + 1:
            h2h_edge = "Away"
    
    return {
        "last5_home": round(l5_home, 1),
        "last5_away": round(l5_away, 1),
        "last10_home": round(l10_home, 1),
        "last10_away": round(l10_away, 1),
        "h2h_home_wins": h2h_home_wins,
        "h2h_away_wins": h2h_away_wins,
        "h2h_draws": h2h_draws,
        "h2h_total": h2h_total,
        "h2h_edge": h2h_edge,
    }


def analyze_player_impact(injuries: List[Dict], suspensions: List[Dict]) -> Dict:
    """
    Rate injury/suspension impact.
    
    Input: [{"name": "Mbappe", "position": "FW", "impact": 5, "replacement_level": 3}, ...]
        impact: 1-5 (star player = 5)
        replacement_level: 1-5 (how good is the backup)
    """
    base_score = 100
    details = []
    
    for p in injuries + suspensions:
        impact = p.get("impact", 2)
        replacement = p.get("replacement_level", 3)
        severity = (impact - replacement) / 4  # 0 to 1
        penalty = severity * 12
        base_score -= penalty
        
        if impact >= 4:
            details.append(f"⚠️ {p['name']} ({p.get('position', 'OUT')}) — impact {impact}/5, no adequate replacement")
        elif impact >= 3:
            pos = p.get('position', 'OUT')
            details.append(f"• {p['name']} ({pos}) — impact {impact}/5")
    
    return {
        "player_score": max(0, round(base_score, 1)),
        "key_absences": [p["name"] for p in injuries + suspensions if p.get("impact", 0) >= 3],
        "details": details,
        "severity": "High" if base_score < 70 else "Medium" if base_score < 85 else "Low",
    }


def analyze_stats(raw: Dict) -> Dict:
    """
    Deep statistical analysis.
    
    Input:
      {
        "home": {
          "gf_avg": 1.8, "ga_avg": 0.9, "xg": 1.7, "xga": 0.8,
          "possession": 54, "sot_avg": 5.2, "cs_pct": 0.4,
          "home_gf_avg": 2.1, "home_ga_avg": 0.7, "home_possession": 58
        },
        "away": { ... similar ... }
      }
    """
    home = raw.get("home", {})
    away = raw.get("away", {})
    
    def team_stats(gf, ga, xg, xga, poss, sot, cs_pct, home_away_modifier=0):
        gd = gf - ga
        xg_diff = xg - xga
        
        # Normalize each metric to 0-100
        attack = min(100, max(0, (gf / 2.5) * 100))  # 2.5 goals/game = elite
        defense = min(100, max(0, ((2.5 - ga) / 2.5) * 100))  # 0 GA = perfect
        xg_quality = min(100, max(0, 50 + (xg_diff * 20)))
        poss_score = min(100, max(0, poss * 1.5))
        shot_quality = min(100, max(0, sot * 15))
        cs_score = min(100, max(0, cs_pct * 200))
        
        overall = (attack * 0.25 + defense * 0.25 + xg_quality * 0.20 +
                   poss_score * 0.10 + shot_quality * 0.05 + cs_score * 0.15)
        
        return {
            "attack": round(attack, 1),
            "defense": round(defense, 1),
            "xg_quality": round(xg_quality, 1),
            "possession": round(poss_score, 1),
            "shot_quality": round(shot_quality, 1),
            "clean_sheet": round(cs_score, 1),
            "overall": round(min(100, overall + home_away_modifier), 1),
            "avg_gf": gf,
            "avg_ga": ga,
            "xg": xg,
            "xga": xga,
            "xg_diff": round(xg_diff, 2),
        }
    
    home_stats = team_stats(
        home.get("gf_avg", 1.5), home.get("ga_avg", 1.0),
        home.get("xg", 1.4), home.get("xga", 1.0),
        home.get("possession", 52), home.get("sot_avg", 4.5),
        home.get("cs_pct", 0.3), home_away_modifier=5
    )
    
    away_stats = team_stats(
        away.get("gf_avg", 1.3), away.get("ga_avg", 1.2),
        away.get("xg", 1.2), away.get("xga", 1.1),
        away.get("possession", 48), away.get("sot_avg", 4.0),
        away.get("cs_pct", 0.25), home_away_modifier=-3
    )
    
    edge = "Neutral"
    if home_stats["overall"] - away_stats["overall"] > 10:
        edge = "Home"
    elif away_stats["overall"] - home_stats["overall"] > 10:
        edge = "Away"
    
    return {
        "home": home_stats,
        "away": away_stats,
        "statistical_advantage": edge,
        "confidence": round(min(100, abs(home_stats["overall"] - away_stats["overall"]) * 2 + 50), 1),
    }


# ═══════════════════════════════════════════════════════════════════
# B. ODDS MARKET ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_market(match: Dict) -> Dict:
    """
    Analyze odds movement and market signals.
    
    Input market fields:
      opening_odds, current_odds (American format)
      public_pct_home, public_pct_away, public_pct_draw
      book_names: ["Pinnacle", "Bet365", "DraftKings"]
      pinnacle_closing: float (American odds from Pinnacle)
    """
    opening = match.get("current_odds", -110)
    current = match.get("current_odds", -110)
    
    # Use opening_odds if available
    opening = match.get("opening_odds", current)
    
    # American to implied probability
    def implied_prob(american):
        if american > 0:
            return 100 / (american + 100)
        return abs(american) / (abs(american) + 100)
    
    implied = implied_prob(current)
    
    # Line movement
    if current > opening:
        movement = "↑"  # odds got longer (worse)
        move_pct = ((current - opening) / abs(opening)) * 100
    elif current < opening:
        movement = "↓"  # odds got shorter (better)
        move_pct = ((opening - current) / abs(opening)) * 100
    else:
        movement = "→"
        move_pct = 0
    
    # Reverse Line Movement (RLM) detection
    public_home = match.get("public_pct_home", 50)
    public_away = match.get("public_pct_away", 30)
    
    rlm_signal = "None"
    if current > opening and public_home > 65:
        # Line moved against public = sharp money against public
        rlm_signal = "RLM detected — sharp money against home"
    elif current < opening and public_home > 65:
        rlm_signal = "Public + line aligned — no RLM"
    elif abs(current - opening) > 15 and public_home < 40:
        rlm_signal = "RLM detected — sharp money on home despite low public %"
    
    # Bookmaker margin
    odds_fields = ["home_odds", "draw_odds", "away_odds"]
    odds_vals = [match.get(f) for f in odds_fields if match.get(f)]
    if len(odds_vals) >= 2:
        margins = [implied_prob(o) for o in odds_vals]
        total_implied = sum(margins) * 100
        margin_pct = round(total_implied - 100, 2)
    else:
        margin_pct = 0
    
    # Pinnacle comparison
    pinnacle = match.get("pinnacle_closing")
    pinnacle_edge = None
    if pinnacle:
        pinnacle_implied = implied_prob(pinnacle)
        pinnacle_edge = round((implied - pinnacle_implied) * 100, 2)
    
    # Market signal strength
    signal = "Weak"
    if abs(move_pct) > 10 and rlm_signal != "None":
        signal = "Strong"
    elif abs(move_pct) > 5 or rlm_signal != "None":
        signal = "Medium"
    
    # Trap line detection
    is_trap = False
    if public_home > 75 and current < opening:
        # Heavy public, line moved toward them — potential trap
        is_trap = True
    
    risk = "Low"
    if is_trap:
        risk = "High"
    elif signal == "Strong":
        risk = "Medium"
    
    return {
        "opening_odds": opening,
        "current_odds": current,
        "movement": movement,
        "move_pct": round(move_pct, 1),
        "implied_prob": round(implied * 100, 1),
        "margin_pct": margin_pct,
        "public_home": public_home,
        "public_away": public_away,
        "rlm_signal": rlm_signal,
        "pinnacle_edge": pinnacle_edge,
        "market_signal": signal,
        "is_trap_line": is_trap,
        "risk_level": risk,
        "public_pct_home": public_home,
        "public_pct_away": public_away,
        "pinnacle_closing": pinnacle,
    }


# ═══════════════════════════════════════════════════════════════════
# C. TACTICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════

TACTICAL_STYLES = {
    "possession": {"beats_high_press": 1, "loses_to_counter": -1, "set_piece": 0},
    "counter": {"beats_high_press": 1, "loses_to_possession": -1, "set_piece": 0},
    "high_press": {"beats_possession": -1, "loses_to_counter": -1, "set_piece": 0},
    "defensive": {"beats_counter": 1, "loses_to_possession": -1, "set_piece": 0},
    "direct": {"beats_defensive": 1, "loses_to_possession": -1, "set_piece": 0},
}


def analyze_tactical(match: Dict) -> Dict:
    """
    Tactical matchup analysis.
    
    Input:
      {
        "home_formation": "4-3-3",
        "away_formation": "4-2-3-1",
        "home_style": "possession",     # possession/counter/high_press/defensive/direct
        "away_style": "counter",
        "home_pressing": 72,            # pressing intensity PPDA (lower = more press)
        "away_pressing": 80,
        "home_set_pieces": "strong",    # strong/medium/weak
        "away_set_pieces": "medium",
        "home_key_player": "Salah",
        "away_key_player": "Son",
        "home_key_vs_away": "Salah vs Walker — pace mismatch",
      }
    """
    home_style = match.get("home_style", "balanced")
    away_style = match.get("away_style", "balanced")
    
    # Style matchup
    style_matchup = "Even"
    if home_style in TACTICAL_STYLES and away_style in TACTICAL_STYLES:
        home_advantage = 0
        if away_style in TACTICAL_STYLES.get(home_style, {}):
            home_advantage += TACTICAL_STYLES[home_style].get(f"beats_{away_style}", 0)
        if home_style in TACTICAL_STYLES.get(away_style, {}):
            home_advantage -= TACTICAL_STYLES[away_style].get(f"beats_{home_style}", 0)
        
        if home_advantage > 0:
            style_matchup = f"Home advantage ({home_style} vs {away_style})"
        elif home_advantage < 0:
            style_matchup = f"Away advantage ({away_style} vs {home_style})"
    
    # Formation matchup
    home_form = match.get("home_formation", "4-4-2")
    away_form = match.get("away_formation", "4-4-2")
    
    # Midfield battle (count midfielders)
    def count_midfield(formation):
        parts = formation.split("-")
        if len(parts) >= 3:
            return int(parts[1])
        return 3
    
    home_mid = count_midfield(home_form)
    away_mid = count_midfield(away_form)
    midfield = "Home" if home_mid > away_mid else "Away" if away_mid > home_mid else "Even"
    
    # Pressing intensity comparison
    home_press = match.get("home_pressing", 75)  # PPDA
    away_press = match.get("away_pressing", 80)
    pressing = "Home" if home_press < 72 else "Away" if away_press < 72 else "Even"
    
    # Set pieces
    sp_map = {"strong": 2, "medium": 1, "weak": 0}
    home_sp = sp_map.get(match.get("home_set_pieces", "medium"), 1)
    away_sp = sp_map.get(match.get("away_set_pieces", "medium"), 1)
    set_pieces = "Home" if home_sp > away_sp else "Away" if away_sp > home_sp else "Even"
    
    # Counter-attack threat
    ca_threat = "Medium"
    if away_style == "counter":
        ca_threat = "High"  # away team counters well
    if home_style == "high_press":
        ca_threat = "High"  # high press leaves space
    
    # Key player matchup
    key_matchup = match.get("home_key_vs_away", "")
    
    # Determine tactical edge
    edge_score = 50
    if style_matchup.startswith("Home"):
        edge_score += 10
    elif style_matchup.startswith("Away"):
        edge_score -= 10
    if midfield == "Home":
        edge_score += 5
    elif midfield == "Away":
        edge_score -= 5
    if pressing == "Home":
        edge_score += 5
    elif pressing == "Away":
        edge_score -= 5
    if set_pieces == "Home":
        edge_score += 3
    elif set_pieces == "Away":
        edge_score -= 3
    
    if edge_score > 60:
        tactical_edge = "Home"
    elif edge_score < 40:
        tactical_edge = "Away"
    else:
        tactical_edge = "Draw risk"
    
    return {
        "style_matchup": style_matchup,
        "formation_home": home_form,
        "formation_away": away_form,
        "midfield_control": midfield,
        "pressing_intensity": pressing,
        "set_piece_advantage": set_pieces,
        "counter_attack_threat": ca_threat,
        "key_player_matchup": key_matchup,
        "tactical_edge": tactical_edge,
        "tactical_score": round(min(100, max(0, edge_score)), 1),
    }


# ═══════════════════════════════════════════════════════════════════
# D. MOTIVATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_motivation(match: Dict) -> Dict:
    """
    Motivation and situational analysis.
    
    Input:
      {
        "home_motivation": "must_win",    # must_win/high/medium/low/irrelevant
        "away_motivation": "medium",
        "context": {
          "is_derby": false,
          "is_cup": false,
          "title_race": false,
          "relegation_battle": false,
          "qualification": false,
          "upcoming_important": false,
          "rotation_risk": false,
          "days_rest": 4,
          "travel_distance_km": 200,
          "internal_issues": false
        }
      }
    """
    mot_map = {
        "must_win": 25, "high": 15, "medium": 5, "low": -10, "irrelevant": -20
    }
    
    home_mot = mot_map.get(match.get("home_motivation", "medium"), 5)
    away_mot = mot_map.get(match.get("away_motivation", "medium"), 5)
    
    context = match.get("context", {})
    context_score = 0
    context_notes = []
    
    if context.get("is_derby"):
        context_score += 5
        context_notes.append("Derby — elevated motivation for both")
    
    if context.get("title_race"):
        context_score += 8
        context_notes.append("Title race pressure")
    
    if context.get("relegation_battle"):
        context_score += 10
        context_notes.append("Relegation battle — desperation factor")
    
    if context.get("qualification"):
        context_score += 7
        context_notes.append("Champions League/Europa qualification at stake")
    
    if context.get("upcoming_important"):
        context_score -= 5
        context_notes.append("Risk of rotation for upcoming big match")
    
    if context.get("rotation_risk"):
        context_score -= 10
        context_notes.append("Expected rotation — weakened lineup likely")
    
    rest_days = context.get("days_rest", 4)
    if rest_days < 3:
        context_score -= 8
        context_notes.append(f"Fatigue — only {rest_days} days rest")
    elif rest_days > 5:
        context_score += 3
        context_notes.append("Well rested")
    
    travel = context.get("travel_distance_km", 0)
    if travel > 800:
        context_score -= 5
        context_notes.append(f"Long travel {travel}km")
    
    if context.get("internal_issues"):
        context_score -= 15
        context_notes.append("Internal club issues reported")
    
    if context.get("is_cup"):
        context_notes.append("Cup match — different mentality")
    
    total_mot = (home_mot - away_mot) + context_score + 50  # base 50
    
    return {
        "home_motivation_score": max(-25, min(25, home_mot)),
        "away_motivation_score": max(-25, min(25, away_mot)),
        "context_notes": context_notes,
        "motivation_score": round(min(100, max(0, total_mot)), 1),
        "motivation_edge": "Home" if total_mot > 55 else "Away" if total_mot < 45 else "Neutral",
    }


# ═══════════════════════════════════════════════════════════════════
# E. MONTE CARLO SIMULATION
# ═══════════════════════════════════════════════════════════════════

def monte_carlo_sim(match: Dict, stats: Dict, injuries: Dict, 
                    motivation: Dict, n_sims: int = 50000) -> Dict:
    """
    Monte Carlo simulation using attack/defense strength + adjustments.
    
    Returns probabilities for 1X2, O/U 2.5, BTTS, and most likely scorelines.
    """
    random.seed(42)
    
    def lambda_from_xg(xg):
        """Convert xG to Poisson lambda with variance."""
        return max(0.1, xg)
    
    # Get attack/defense strengths from stats analysis
    home_atk = stats.get("home", {}).get("avg_gf", 1.5)
    home_def = stats.get("home", {}).get("avg_ga", 1.0)
    away_atk = stats.get("away", {}).get("avg_gf", 1.2)
    away_def = stats.get("away", {}).get("avg_ga", 1.1)
    home_xg = stats.get("home", {}).get("xg", 1.4)
    home_xga = stats.get("home", {}).get("xga", 1.1)
    away_xg = stats.get("away", {}).get("xg", 1.2)
    away_xga = stats.get("away", {}).get("xga", 1.0)
    
    # Blend xG model with actual goals
    home_attack_strength = (home_atk + home_xg) / 2
    home_defense_strength = (home_def + home_xga) / 2
    away_attack_strength = (away_atk + away_xg) / 2
    away_defense_strength = (away_def + away_xga) / 2
    
    # Adjustments
    # Injury adjustment (reduce attack if key players out)
    injury_mod = 1.0
    if injuries.get("severity") == "High":
        injury_mod = 0.85
    elif injuries.get("severity") == "Medium":
        injury_mod = 0.92
    
    # Motivation adjustment
    mot_mod = 1.0
    mot_score = motivation.get("motivation_score", 50)
    if mot_score > 70:
        mot_mod = 1.1
    elif mot_score < 30:
        mot_mod = 0.85
    
    # Home advantage factor
    home_advantage = 1.15  # ~15% boost
    
    # Lambda (expected goals per team)
    home_lambda = home_attack_strength / (away_defense_strength + 0.5) * home_advantage * injury_mod * mot_mod
    away_lambda = away_attack_strength / (home_defense_strength + 0.5) * (2.0 - home_advantage) * injury_mod * mot_mod
    
    home_lambda = max(0.2, home_lambda)
    away_lambda = max(0.2, away_lambda)
    
    # Run simulations
    home_wins = 0
    draws = 0
    away_wins = 0
    over_1_5 = 0
    over_2_5 = 0
    btts_yes = 0
    
    scorelines = Counter()
    
    for _ in range(n_sims):
        hg = sum(1 for _ in range(n_sims // n_sims + 1) if random.random() < home_lambda / n_sims * 100) if False else \
             _poisson_sample(home_lambda)
        ag = _poisson_sample(away_lambda)
        
        # Cap at 7 goals for realism
        hg = min(hg, 7)
        ag = min(ag, 7)
        
        if hg > ag:
            home_wins += 1
        elif hg == ag:
            draws += 1
        else:
            away_wins += 1
        
        total = hg + ag
        if total >= 2:
            over_1_5 += 1
        if total >= 3:
            over_2_5 += 1
        if hg > 0 and ag > 0:
            btts_yes += 1
        
        scorelines[f"{hg}-{ag}"] += 1
    
    # Most likely scoreline
    most_likely = scorelines.most_common(3)
    
    return {
        "home_lambda": round(home_lambda, 3),
        "away_lambda": round(away_lambda, 3),
        "home_win_prob": round(home_wins / n_sims * 100, 1),
        "draw_prob": round(draws / n_sims * 100, 1),
        "away_win_prob": round(away_wins / n_sims * 100, 1),
        "over_1_5_prob": round(over_1_5 / n_sims * 100, 1),
        "over_2_5_prob": round(over_2_5 / n_sims * 100, 1),
        "btts_prob": round(btts_yes / n_sims * 100, 1),
        "most_likely_scorelines": [
            {"score": s, "prob": round(c / n_sims * 100, 1)} for s, c in most_likely
        ],
        "simulations": n_sims,
    }


def _poisson_sample(lam: float) -> int:
    """Generate Poisson-distributed random variable."""
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


# ═══════════════════════════════════════════════════════════════════
# F. VALUE BET DETECTION
# ═══════════════════════════════════════════════════════════════════

def detect_value(match: Dict, mc_result: Dict) -> Dict:
    """
    Detect value bets by comparing AI probability vs market implied probability.
    
    EV = (AI Probability × Decimal Odds) - 1
    """
    market = match.get("market", {})
    current = market.get("current_odds", match.get("current_odds", -110))
    
    def american_to_decimal(am):
        if am > 0:
            return (am / 100) + 1
        return (100 / abs(am)) + 1
    
    dec = american_to_decimal(current)
    implied_prob = 1 / dec
    
    # AI probability from Monte Carlo
    ai_prob = mc_result.get("home_win_prob", 50) / 100
    
    # EV calculation
    ev = (ai_prob * dec) - 1
    ev_pct = ev * 100
    
    # Value classification
    if ev_pct > 5 and ai_prob > implied_prob + 0.05:
        value_status = "Positive"
        recommendation = "STRONG VALUE — consider play"
    elif ev_pct > 2 and ai_prob > implied_prob:
        value_status = "Positive"
        recommendation = "Good value — solid pick"
    elif ev_pct > 0:
        value_status = "Neutral"
        recommendation = "Marginal — small edge only"
    else:
        value_status = "Negative"
        recommendation = "No value — avoid"
    
    edge = (ai_prob - implied_prob) * 100
    
    return {
        "odds_american": current,
        "odds_decimal": round(dec, 3),
        "ai_probability": round(ai_prob * 100, 1),
        "implied_probability": round(implied_prob * 100, 1),
        "edge_pct": round(edge, 2),
        "ev_score": round(ev_pct, 2),
        "value_status": value_status,
        "recommendation": recommendation,
    }


# ═══════════════════════════════════════════════════════════════════
# G. CORRELATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════

CORRELATION_MATRIX = {
    # Same match combinations
    ("1X2_home", "O2.5"): 0.25,
    ("1X2_home", "BTTS_yes"): 0.35,
    ("1X2_home", "O1.5"): 0.50,
    ("1X2_away", "O2.5"): 0.15,
    ("1X2_away", "BTTS_yes"): 0.30,
    ("O2.5", "BTTS_yes"): 0.45,
    ("O1.5", "O2.5"): 0.65,
    ("1X2_home", "AH_-1.5"): 0.50,
    ("1X2_draw", "U2.5"): 0.40,
}


def analyze_correlation(selected_picks: List[Dict]) -> Dict:
    """
    Analyze correlation risk for a set of parlay legs.
    
    Args:
        selected_picks: [{"match": "A vs B", "market": "1X2_home", "odds": -120}, ...]
    """
    if len(selected_picks) < 2:
        return {"risk": "Low", "correlation_score": 0, "warnings": []}
    
    warnings = []
    total_corr = 0
    pairs = 0
    
    for i in range(len(selected_picks)):
        for j in range(i + 1, len(selected_picks)):
            p1, p2 = selected_picks[i], selected_picks[j]
            
            # Same match check
            same_match = p1["match"] == p2["match"]
            
            # Correlation lookup
            mkt1, mkt2 = p1["market"], p2["market"]
            corr = CORRELATION_MATRIX.get(
                (mkt1, mkt2),
                CORRELATION_MATRIX.get((mkt2, mkt1), 0)
            )
            
            if same_match:
                corr = max(corr, 0.4)  # minimum 0.4 for same match
                warnings.append(f"⚠️ Same match: {p1['match']} — {mkt1} & {mkt2} (ρ ≥ 0.4)")
            
            if corr > 0.4:
                warnings.append(f"⚠️ High correlation: {p1['match']} {mkt1} ↔ {p2['match']} {mkt2} (ρ={corr})")
            elif corr > 0.2:
                warnings.append(f"• Medium correlation: {mkt1} ↔ {mkt2} (ρ={corr})")
            
            total_corr += corr
            pairs += 1
    
    avg_corr = total_corr / pairs if pairs > 0 else 0
    
    if avg_corr > 0.4:
        risk = "High"
    elif avg_corr > 0.2:
        risk = "Medium"
    else:
        risk = "Low"
    
    # Check league concentration
    leagues = Counter()
    for p in selected_picks:
        league = p.get("league", "Unknown")
        leagues[league] += 1
    
    top_league, top_count = leagues.most_common(1)[0] if leagues else ("None", 0)
    if top_count > len(selected_picks) * 0.6:
        warnings.append(f"⚠️ Overexposure to {top_league} ({top_count}/{len(selected_picks)} legs)")
    
    return {
        "correlation_risk": risk,
        "avg_correlation": round(avg_corr, 3),
        "num_pairs": pairs,
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════════════════════════
# FULL MATCH ANALYSIS PIPELINE
# ═══════════════════════════════════════════════════════════════════

def full_analysis(match: Dict) -> Dict:
    """Run all 7 analysis modules on a single match."""
    
    # A. Statistics
    form = analyze_form(
        match.get("last5", {}),
        match.get("last10", {})
    )
    
    injuries = analyze_player_impact(
        match.get("home_injuries", []),
        match.get("home_suspensions", [])
    )
    
    raw_stats = {
        "home": {
            "gf_avg": match.get("home_gf_avg", 1.5),
            "ga_avg": match.get("home_ga_avg", 1.0),
            "xg": match.get("home_xg", 1.4),
            "xga": match.get("home_xga", 1.1),
            "possession": match.get("home_possession", 52),
            "sot_avg": match.get("home_sot", 4.5),
            "cs_pct": match.get("home_cs_pct", 0.3),
        },
        "away": {
            "gf_avg": match.get("away_gf_avg", 1.2),
            "ga_avg": match.get("away_ga_avg", 1.1),
            "xg": match.get("away_xg", 1.2),
            "xga": match.get("away_xga", 1.0),
            "possession": match.get("away_possession", 48),
            "sot_avg": match.get("away_sot", 4.0),
            "cs_pct": match.get("away_cs_pct", 0.25),
        }
    }
    stats = analyze_stats(raw_stats)
    
    # B. Market
    market = analyze_market(match)
    
    # C. Tactical
    tactical = analyze_tactical(match)
    
    # D. Motivation
    motivation = analyze_motivation(match)
    
    # E. Monte Carlo
    mc = monte_carlo_sim(match, stats, injuries, motivation)
    
    # F. Value Bet
    value = detect_value(match, mc)
    
    # Overall confidence (weighted combination)
    confidence = (
        stats["confidence"] * 0.20 +
        (market["market_signal"] == "Strong") * 15 +
        (market["market_signal"] == "Medium") * 8 +
        tactical["tactical_score"] * 0.15 +
        motivation["motivation_score"] * 0.15 +
        (value["ev_score"] > 5) * 20 +
        (value["ev_score"] > 2) * 10 +
        form["last10_home"] * 0.10 +
        injuries["player_score"] * 0.05
    )
    confidence = min(100, max(0, confidence))
    
    # Determine prediction
    prediction = mc.get("home_win_prob", 40) > mc.get("away_win_prob", 30) and "Home Win" or "Away Win"
    if mc["draw_prob"] > max(mc["home_win_prob"], mc["away_win_prob"]) + 5:
        prediction = "Draw"
    
    # Risk level
    risk = "Low"
    if market["risk_level"] == "High" or value["value_status"] == "Negative":
        risk = "High"
    elif market["risk_level"] == "Medium" or confidence < 60:
        risk = "Medium"
    
    return {
        "match": f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}",
        "league": match.get("league", "Unknown"),
        "kickoff": match.get("kickoff", "TBD"),
        "prediction": prediction,
        "confidence": round(confidence, 1),
        "risk_level": risk,
        "odds": value["odds_american"],
        "statistics": {
            "form": form,
            "injuries": injuries,
            "deep_stats": stats,
        },
        "market": market,
        "tactical": tactical,
        "motivation": motivation,
        "monte_carlo": mc,
        "value_bet": value,
    }


# ═══════════════════════════════════════════════════════════════════
# PARLAY CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════

def build_parlays(analyses: List[Dict], bankroll: float, 
                  kelly_mult: float = 0.25) -> Dict:
    """Build SAFE/MEDIUM/AGGRESSIVE parlay recommendations."""
    
    def a2d(am):
        return (am / 100) + 1 if am > 0 else (100 / abs(am)) + 1
    
    def d2a(d):
        return (d - 1) * 100 if d >= 2 else -100 / (d - 1)
    
    # Filter viable (positive value, decent confidence)
    viable = [a for a in analyses if a["value_bet"]["value_status"] != "Negative" and a["confidence"] >= 45]
    viable.sort(key=lambda x: x["confidence"], reverse=True)
    
    def make_parlay(pool, min_conf, max_legs, kelly_factor, name, risk_desc):
        legs = [l for l in pool if l["confidence"] >= min_conf][:max_legs]
        if len(legs) < 2:
            return None
        
        dec_odds = 1.0
        combined_prob = 1.0
        picks = []
        for l in legs:
            dec = a2d(l["odds"])
            dec_odds *= dec
            prob = l["monte_carlo"]["home_win_prob"] / 100
            combined_prob *= prob
            picks.append({
                "match": l["match"],
                "prediction": l["prediction"],
                "odds": l["odds"],
                "confidence": l["confidence"],
                "ev": l["value_bet"]["ev_score"],
            })
        
        ev = (combined_prob * (dec_odds - 1)) - (1 - combined_prob)
        
        b = dec_odds - 1
        p = combined_prob
        kelly_f = max(0, (b * p - (1 - p)) / b) if b > 0 else 0
        kelly_bet = bankroll * kelly_f * kelly_factor
        
        # Flat stake minimum
        stake = round(max(kelly_bet, bankroll * kelly_factor * 0.01), 2)
        
        # Correlation check
        corr_check = analyze_correlation([
            {"match": p["match"], "market": "1X2_home" if "Home" in p["prediction"] else "1X2_away"}
            for p in picks
        ])
        
        return {
            "tier": name,
            "legs": picks,
            "total_odds_decimal": round(dec_odds, 3),
            "total_odds_american": round(d2a(dec_odds), 0),
            "estimated_prob": round(combined_prob * 100, 1),
            "ev_pct": round(ev * 100, 1),
            "risk": risk_desc,
            "correlation": corr_check,
            "recommended_stake": stake,
            "potential_payout": round(stake * dec_odds, 2),
            "potential_profit": round(stake * (dec_odds - 1), 2),
        }
    
    safe = make_parlay(viable, 70, 3, 1.0, "🟢 SAFE PARLAY (2-3 legs)", "Low")
    medium = make_parlay(viable, 62, 5, 0.5, "🟡 MEDIUM PARLAY (3-5 legs)", "Medium")
    aggressive = make_parlay(viable, 50, 8, 0.25, "🔴 AGGRESSIVE PARLAY (5-8 legs)", "High")
    
    recs = {"safe": safe, "medium": medium, "aggressive": aggressive}
    
    total_risk = sum(r["recommended_stake"] for r in recs.values() if r)
    
    # Best picks
    best_pick = max(analyses, key=lambda x: x["confidence"])
    best_value = max(analyses, key=lambda x: x["value_bet"]["ev_score"])
    avoid = min(analyses, key=lambda x: x["value_bet"]["ev_score"])
    
    # Main risks
    risks = []
    neg_ev = [a for a in analyses if a["value_bet"]["value_status"] == "Negative"]
    if neg_ev:
        risks.append(f"{len(neg_ev)} picks have negative EV")
    trap = [a for a in analyses if a["market"].get("is_trap_line")]
    if trap:
        risks.append(f"{len(trap)} potential trap line(s)")
    high_corr = [a for a in analyses if a["confidence"] < 50]
    if high_corr:
        risks.append(f"{len(high_corr)} low-confidence picks on card")
    
    return {
        "bankroll": bankroll,
        "total_matches": len(analyses),
        "viable_picks": len(viable),
        "recommendations": recs,
        "total_risk": round(total_risk, 2),
        "risk_pct": round((total_risk / bankroll) * 100, 1),
        "final_judgment": {
            "best_pick": best_pick["match"],
            "best_pick_confidence": best_pick["confidence"],
            "best_value_bet": best_value["match"],
            "best_value_ev": best_value["value_bet"]["ev_score"],
            "pick_to_avoid": avoid["match"],
            "avoid_reason": f"EV {avoid['value_bet']['ev_score']:.1f}%",
            "main_risks": risks if risks else ["None significant"],
            "overall_confidence": round(sum(a["confidence"] for a in analyses) / len(analyses), 1) if analyses else 0,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# DISPLAY FORMATTER
# ═══════════════════════════════════════════════════════════════════

def format_full_analysis(a: Dict) -> str:
    """Format complete match analysis per the required output schema."""
    lines = []
    
    # Header
    lines.append("╔" + "═" * 58 + "╗")
    lines.append(f"║  🏟️  {a['match']:<52} ║")
    lines.append(f"║  📅 {a['league']}  |  {a['kickoff']:<40} ║")
    lines.append("╚" + "═" * 58 + "╝")
    
    lines.append(f"\n  📊 PREDICTION: {a['prediction']}")
    lines.append(f"  💰 Market Odds: {a['odds']:+.0f}")
    lines.append(f"  ⭐ Confidence: {a['confidence']:.0f}/100")
    lines.append(f"  ⚠️  Risk Level: {a['risk_level']}")
    
    # A. Statistics Summary
    lines.append(f"\n  ┌─ A. STATISTICS SUMMARY ─{'─' * 32}┐")
    f = a["statistics"]["form"]
    lines.append(f"  │  Form L10: Home {f['last10_home']:.0f}/100 | Away {f['last10_away']:.0f}/100")
    lines.append(f"  │  H2H: {f['h2h_home_wins']}-{f['h2h_draws']}-{f['h2h_away_wins']} (edge: {f['h2h_edge']})")
    i = a["statistics"]["injuries"]
    lines.append(f"  │  Key Absences: {i['severity']} | Score: {i['player_score']:.0f}/100")
    if i["key_absences"]:
        lines.append(f"  │  Players out: {', '.join(i['key_absences'])}")
    s = a["statistics"]["deep_stats"]
    lines.append(f"  │  Home xG: {s['home']['xg']} | xGA: {s['home']['xga']} | Net: {s['home']['xg_diff']:+.2f}")
    lines.append(f"  │  Away xG: {s['away']['xg']} | xGA: {s['away']['xga']} | Net: {s['away']['xg_diff']:+.2f}")
    lines.append(f"  │  Stat Advantage: {s['statistical_advantage']} (conf: {s['confidence']:.0f})")
    lines.append(f"  └{'─' * 56}┘")
    
    # B. Market Summary
    m = a["market"]
    lines.append(f"\n  ┌─ B. MARKET ODDS SUMMARY ─{'─' * 31}┐")
    lines.append(f"  │  Opening: {m['opening_odds']:+.0f} → Current: {m['current_odds']:+.0f} ({m['movement']} {m['move_pct']:.1f}%)")
    lines.append(f"  │  Implied Prob: {m['implied_prob']}% | Margin: {m['margin_pct']}%")
    lines.append(f"  │  Public: {m['public_pct_home']}% home | Signal: {m['market_signal']}")
    lines.append(f"  │  RLM: {m['rlm_signal']}")
    if m.get("is_trap_line"):
        lines.append(f"  │  ⚠️ TRAP LINE POSSIBLE")
    lines.append(f"  │  Risk: {m['risk_level']}")
    lines.append(f"  └{'─' * 56}┘")
    
    # C. Tactical Summary
    t = a["tactical"]
    lines.append(f"\n  ┌─ C. TACTICAL SUMMARY ───{'─' * 32}┐")
    lines.append(f"  │  Formation: {t['formation_home']} vs {t['formation_away']}")
    lines.append(f"  │  Style: {t['style_matchup']}")
    lines.append(f"  │  Midfield: {t['midfield_control']} | Pressing: {t['pressing_intensity']}")
    lines.append(f"  │  Set Pieces: {t['set_piece_advantage']} | Counter Threat: {t['counter_attack_threat']}")
    if t["key_player_matchup"]:
        lines.append(f"  │  Key Matchup: {t['key_player_matchup']}")
    lines.append(f"  │  Tactical Edge: {t['tactical_edge']} (score: {t['tactical_score']:.0f})")
    lines.append(f"  └{'─' * 56}┘")
    
    # D. Motivation Summary
    mot = a["motivation"]
    lines.append(f"\n  ┌─ D. MOTIVATION SUMMARY ─{'─' * 31}┐")
    lines.append(f"  │  Score: {mot['motivation_score']:.0f}/100 | Edge: {mot['motivation_edge']}")
    for note in mot["context_notes"][:4]:
        lines.append(f"  │  • {note}")
    lines.append(f"  └{'─' * 56}┘")
    
    # E. Monte Carlo
    mc = a["monte_carlo"]
    lines.append(f"\n  ┌─ E. MONTE CARLO RESULT ({mc['simulations']:,} sims) ─{'─' * 18}┐")
    lines.append(f"  │  1X2: Home {mc['home_win_prob']}% | Draw {mc['draw_prob']}% | Away {mc['away_win_prob']}%")
    lines.append(f"  │  O1.5: {mc['over_1_5_prob']}% | O2.5: {mc['over_2_5_prob']}% | BTTS: {mc['btts_prob']}%")
    scorelines = [f"{s['score']} ({s['prob']}%)" for s in mc['most_likely_scorelines']]
    lines.append(f"  │  Most likely: {', '.join(scorelines)}")
    lines.append(f"  │  λ: Home {mc['home_lambda']} | Away {mc['away_lambda']}")
    lines.append(f"  └{'─' * 56}┘")
    
    # F. Value Bet
    v = a["value_bet"]
    lines.append(f"\n  ┌─ F. VALUE BET RESULT ───{'─' * 32}┐")
    lines.append(f"  │  Odds: {v['odds_american']:+.0f} (dec: {v['odds_decimal']})")
    lines.append(f"  │  AI Prob: {v['ai_probability']}% | Implied: {v['implied_probability']}%")
    lines.append(f"  │  Edge: {v['edge_pct']:+.2f}% | EV: {v['ev_score']:+.2f}%")
    lines.append(f"  │  Status: {v['value_status']} — {v['recommendation']}")
    lines.append(f"  └{'─' * 56}┘")
    
    return "\n".join(lines)


def format_parlays(recs: Dict) -> str:
    """Format parlay recommendations."""
    lines = []
    lines.append("\n" + "╔" + "═" * 58 + "╗")
    lines.append("║" + "  🎰 PARLAY RECOMMENDATIONS".center(58) + "║")
    lines.append("╚" + "═" * 58 + "╝")
    
    for key, label in [("safe", "🟢 SAFE"), ("medium", "🟡 MEDIUM"), ("aggressive", "🔴 AGGRESSIVE")]:
        p = recs["recommendations"][key]
        if not p:
            continue
        
        lines.append(f"\n  {label} PARLAY ({len(p['legs'])} legs)")
        lines.append(f"  {'─' * 54}")
        
        for i, leg in enumerate(p["legs"], 1):
            lines.append(f"    {i}. {leg['match']}")
            lines.append(f"       → {leg['prediction']} @ {leg['odds']:+.0f} (conf: {leg['confidence']:.0f}, EV: {leg['ev']:+.1f}%)")
        
        lines.append(f"\n    Total Odds: {p['total_odds_american']:+.0f} (dec: {p['total_odds_decimal']})")
        lines.append(f"    Est. Probability: {p['estimated_prob']}%")
        lines.append(f"    EV: {p['ev_pct']:+.1f}%")
        lines.append(f"    Risk: {p['risk']}")
        lines.append(f"    Correlation: {p['correlation']['correlation_risk']} (ρ={p['correlation']['avg_correlation']})")
        if p['correlation']['warnings']:
            for w in p['correlation']['warnings'][:3]:
                lines.append(f"      {w}")
        lines.append(f"    Recommended Stake: ${p['recommended_stake']:.2f}")
        lines.append(f"    Potential Payout: ${p['potential_payout']:.2f}")
        lines.append(f"    Potential Profit: ${p['potential_profit']:.2f}")
    
    # Bankroll
    lines.append(f"\n  💰 BANKROLL MANAGEMENT")
    lines.append(f"  {'─' * 54}")
    lines.append(f"    Bankroll: ${recs['bankroll']:.2f}")
    lines.append(f"    Total Risk: ${recs['total_risk']:.2f} ({recs['risk_pct']:.1f}%)")
    
    # Final Judgment
    j = recs["final_judgment"]
    lines.append(f"\n  📋 FINAL JUDGMENT")
    lines.append(f"  {'─' * 54}")
    lines.append(f"    Best Pick: {j['best_pick']} (conf: {j['best_pick_confidence']:.0f})")
    lines.append(f"    Best Value Bet: {j['best_value_bet']} (EV: {j['best_value_ev']:+.1f}%)")
    lines.append(f"    Pick to Avoid: {j['pick_to_avoid']} ({j['avoid_reason']})")
    lines.append(f"    Main Risks: {', '.join(j['main_risks'])}")
    lines.append(f"    Overall Confidence: {j['overall_confidence']:.0f}/100")
    
    # Betting advice
    if j["overall_confidence"] >= 70:
        advice = "Strong card — consider full parlay allocation"
    elif j["overall_confidence"] >= 55:
        advice = "Decent card — stick to Safe + Medium parlays"
    elif j["overall_confidence"] >= 40:
        advice = "Weak card — reduce stakes or skip"
    else:
        advice = "Poor card — avoid betting today"
    lines.append(f"    Betting Advice: {advice}")
    
    lines.append("\n" + "═" * 60)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Advanced Match Analyzer v2")
    parser.add_argument("--file", help="JSON file with match data")
    parser.add_argument("--bankroll", type=float, default=1000)
    parser.add_argument("--kelly", type=float, default=0.25)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--examples", action="store_true", help="Print example input format")
    
    args = parser.parse_args()
    
    if args.examples or not args.file:
        print(json.dumps({
            "matches": [{
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "league": "Premier League",
                "kickoff": "2025-01-15 20:00",
                "current_odds": -140,
                "opening_odds": -130,
                "public_pct_home": 65,
                "public_pct_away": 25,
                "pinnacle_closing": -135,
                "last5": {
                    "home": {"w": 4, "d": 0, "l": 1, "gf": 9, "ga": 3},
                    "away": {"w": 3, "d": 1, "l": 1, "gf": 7, "ga": 4}
                },
                "last10": {
                    "home": {"w": 7, "d": 2, "l": 1, "gf": 18, "ga": 7},
                    "away": {"w": 5, "d": 3, "l": 2, "gf": 14, "ga": 9},
                    "h2h": [{"home": 2, "away": 1}, {"home": 1, "away": 1}, {"home": 3, "away": 0}]
                },
                "home_injuries": [],
                "home_suspensions": [],
                "home_gf_avg": 1.8, "home_ga_avg": 0.7,
                "home_xg": 1.7, "home_xga": 0.8,
                "home_possession": 55, "home_sot": 5.2, "home_cs_pct": 0.4,
                "away_gf_avg": 1.4, "away_ga_avg": 0.9,
                "away_xg": 1.3, "away_xga": 0.9,
                "away_possession": 48, "away_sot": 4.1, "away_cs_pct": 0.35,
                "home_formation": "4-3-3",
                "away_formation": "4-2-3-1",
                "home_style": "possession",
                "away_style": "counter",
                "home_pressing": 68,
                "away_pressing": 78,
                "home_set_pieces": "strong",
                "away_set_pieces": "medium",
                "home_key_vs_away": "Salah vs James — pace mismatch",
                "home_motivation": "high",
                "away_motivation": "medium",
                "context": {
                    "is_derby": true,
                    "title_race": true,
                    "days_rest": 4,
                    "travel_distance_km": 50
                }
            }]
        }, indent=2))
        if not args.file:
            return
    
    with open(args.file) as f:
        data = json.load(f)
    
    matches = data.get("matches", data if isinstance(data, list) else [data])
    
    # Analyze each match
    analyses = []
    for match in matches:
        result = full_analysis(match)
        analyses.append(result)
        if not args.json:
            print(format_full_analysis(result))
    
    # Build parlays
    recs = build_parlays(analyses, args.bankroll, args.kelly)
    
    if args.json:
        print(json.dumps({"analyses": analyses, "recommendations": recs}, indent=2))
    else:
        print(format_parlays(recs))


if __name__ == "__main__":
    main()
