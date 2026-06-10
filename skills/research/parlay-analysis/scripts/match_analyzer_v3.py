#!/usr/bin/env python3
"""
Match Analyzer v3 — Deep Football Analysis
CUPANG AI AGENT — Elite Sports Betting Intelligence

NEW FEATURES in v3 (beyond v2):
─────────────────────────────────
H. POISSON DISTRIBUTION MODEL — Exact scoreline probabilities
I. ELO RATING SYSTEM — Dynamic team strength tracking
J. MARKET EFFICIENCY TEST — Is the market pricing correctly?
K. SENTIMENT ANALYSIS — Crowd vs sharp divergence detector
L. WEATHER IMPACT MODEL — Rain/wind/heat effect on scoring
M. REFEREE ANALYSIS — Card/adjustment tendencies
N. IN-PLAY MOMENTUM MODEL — Live match state evaluation
O. CROSS-LEAGUE H2H DATABASE — Historical matchup patterns
P. BETTING MARKET DEPTH — Multi-bookmaker odds comparison
Q. RISK-ADJUSTED RETURNS — Sharpe/Sortino for betting portfolios
R. PORTFOLIO OPTIMIZER — Kelly across multiple concurrent bets
S. STREAK ANALYSIS — Win/loss/draw streak patterns & regression
T. GOAL TIMING MODEL — When goals are most likely (1H/2H)
U. ALTERNATIVE LINE FINDER — Best spreads/totals for each match
V. CONTRARIAN SIGNAL GENERATOR — Fade the public alerts

Usage:
  python3 match_analyzer_v3.py --file matches.json --bankroll 1000
  python3 match_analyzer_v3.py --file matches.json --bankroll 1000 --deep
  python3 match_analyzer_v3.py --file matches.json --advanced-only
"""

import json
import math
import random
import argparse
from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# H. POISSON DISTRIBUTION MODEL
# ═══════════════════════════════════════════════════════════════════

def poisson_pmf(lam: int, k: int) -> float:
    """P(X=k) for Poisson distribution."""
    if k < 0:
        return 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def poisson_cdf(lam: float, k: int) -> float:
    """P(X<=k) for Poisson distribution."""
    return sum(poisson_pmf(lam, i) for i in range(k + 1))


def poisson_sf(lam: float, k: int) -> float:
    """P(X>k) = 1 - P(X<=k)."""
    return 1 - poisson_cdf(lam, k)


def poisson_scoreline_matrix(home_lam: float, away_lam: float, max_goals: int = 7) -> Dict:
    """
    Generate exact probability for every scoreline using Poisson model.
    
    Returns:
        {
            "matrix": [[P(0,0), P(0,1), ...], [P(1,0), P(1,1), ...]],
            "home_win_prob": float,
            "draw_prob": float, 
            "away_win_prob": float,
            "over_1_5": float,
            "over_2_5": float,
            "over_3_5": float,
            "btts_yes": float,
            "btts_no": float,
            "exact_score_probs": {"2-1": 0.085, "1-0": 0.103, ...},
            "most_likely_scorelines": [...]
        }
    """
    matrix = []
    exact_scores = {}
    
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over_1_5 = 0.0
    over_2_5 = 0.0
    over_3_5 = 0.0
    btts_yes = 0.0
    
    for hg in range(max_goals + 1):
        row = []
        for ag in range(max_goals + 1):
            p = poisson_pmf(home_lam, hg) * poisson_pmf(away_lam, ag)
            row.append(p)
            key = f"{hg}-{ag}"
            exact_scores[key] = round(p * 100, 2)
            
            if hg > ag:
                home_win += p
            elif hg == ag:
                draw += p
            else:
                away_win += p
            
            total = hg + ag
            if total >= 2:
                over_1_5 += p
            if total >= 3:
                over_2_5 += p
            if total >= 4:
                over_3_5 += p
            if hg > 0 and ag > 0:
                btts_yes += p
        
        matrix.append(row)
    
    btts_no = 1 - btts_yes
    
    # Sort scorelines by probability
    sorted_scores = sorted(exact_scores.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "matrix": [[round(p * 100, 2) for p in row] for row in matrix],
        "home_win_prob": round(home_win * 100, 2),
        "draw_prob": round(draw * 100, 2),
        "away_win_prob": round(away_win * 100, 2),
        "over_1_5": round(over_1_5 * 100, 2),
        "over_2_5": round(over_2_5 * 100, 2),
        "over_3_5": round(over_3_5 * 100, 2),
        "over_4_5": round(sum(poisson_pmf(home_lam, hg) * poisson_pmf(away_lam, ag) 
                            for hg in range(max_goals + 1) for ag in range(max_goals + 1) 
                            if hg + ag >= 5) * 100, 2),
        "btts_yes": round(btts_yes * 100, 2),
        "btts_no": round(btts_no * 100, 2),
        "exact_scores": dict(sorted_scores[:10]),
        "most_likely_scorelines": [{"score": s, "prob": p} for s, p in sorted_scores[:5]],
    }


# ═══════════════════════════════════════════════════════════════════
# I. ELO RATING SYSTEM
# ═══════════════════════════════════════════════════════════════════

class EloRating:
    """
    Chess-style ELO rating adapted for football.
    - K-factor: 32 (higher = more volatile)
    - Home advantage: +100 ELO points
    - Goal difference modifier
    """
    
    K_FACTOR = 32
    HOME_ADVANTAGE = 100
    
    def __init__(self, ratings: Dict[str, float] = None, base_rating: float = 1500):
        self.ratings = ratings or {}
        self.base_rating = base_rating
    
    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.base_rating)
    
    def expected_score(self, team_a: str, team_b: str, home_a: bool = True) -> float:
        """Expected score (0-1) for team_a vs team_b."""
        ra = self.get_rating(team_a) + (self.HOME_ADVANTAGE if home_a else 0)
        rb = self.get_rating(team_b)
        return 1 / (1 + 10 ** ((rb - ra) / 400))
    
    def update(self, team_a: str, team_b: str, score_a: float, score_b: float, home_a: bool = True):
        """
        Update ratings after a match.
        score_a, score_b: actual goals scored
        """
        outcome_a = self._outcome(score_a, score_b)
        expected_a = self.expected_score(team_a, team_b, home_a)
        expected_b = 1 - expected_a
        
        # Goal difference modifier
        gd = abs(score_a - score_b)
        gd_mod = 1 + (math.log(gd + 1) / 3) if gd > 0 else 1
        
        # Margin of victory modifier
        mov = max(1, min(8, score_a + score_b + 1))  # total goals affects reliability
        mov_mod = math.log(gd * mov + 1)
        
        k = self.K_FACTOR * gd_mod * min(2, mov_mod)
        
        self.ratings[team_a] = self.get_rating(team_a) + k * (outcome_a - expected_a)
        self.ratings[team_b] = self.get_rating(team_b) + k * ((1 - outcome_a) - expected_b)
    
    def _outcome(self, score_a: float, score_b: float) -> float:
        if score_a > score_b:
            return 1.0
        elif score_a < score_b:
            return 0.0
        return 0.5
    
    def match_prediction(self, home: str, away: str) -> Dict:
        """Get ELO-based match prediction."""
        e_home = self.expected_score(home, away, True)
        e_away = 1 - self.expected_score(away, home, False)
        
        # Normalize
        total = e_home + e_away
        p_home = e_home / total
        p_away = e_away / total
        
        # Draw probability: inversely proportional to rating difference
        rating_diff = abs(self.get_rating(home) - self.get_rating(away))
        draw_factor = max(0.15, 0.30 - (rating_diff / 2000))
        p_draw = draw_factor
        p_home_adj = p_home * (1 - p_draw)
        p_away_adj = p_away * (1 - p_draw)
        
        return {
            "elo_home": round(self.get_rating(home), 1),
            "elo_away": round(self.get_rating(away), 1),
            "elo_diff": round(self.get_rating(home) - self.get_rating(away), 1),
            "home_win_prob": round(p_home_adj * 100, 1),
            "draw_prob": round(p_draw * 100, 1),
            "away_win_prob": round(p_away_adj * 100, 1),
        }


# ═══════════════════════════════════════════════════════════════════
# J. MARKET EFFICIENCY TEST
# ═══════════════════════════════════════════════════════════════════

def market_efficiency_test(ai_probs: Dict, market_odds: Dict, 
                           confidence_threshold: float = 0.05) -> Dict:
    """
    Test if market is pricing correctly vs AI model.
    
    Args:
        ai_probs: {"home": 0.55, "draw": 0.25, "away": 0.20}
        market_odds: {"home": 1.80, "draw": 3.50, "away": 5.00}
        confidence_threshold: minimum edge to flag as significant
    
    Returns:
        Market efficiency analysis with value flags
    """
    def odds_to_prob(o):
        return 1 / o
    
    results = {}
    differentials = []
    
    for outcome in ["home", "draw", "away"]:
        ai_p = ai_probs.get(outcome, 0)
        mkt_p = odds_to_prob(market_odds.get(outcome, 2.0))
        diff = ai_p - mkt_p
        differentials.append(abs(diff))
        
        ev = (ai_p * market_odds.get(outcome, 2.0)) - 1
        
        if diff > confidence_threshold:
            flag = "UNDERPRICED — Value opportunity"
            signal = "STRONG"
        elif diff > 0.02:
            flag = "Slightly underpriced"
            signal = "MEDIUM"
        elif diff < -confidence_threshold:
            flag = "OVERPRICED — Avoid"
            signal = "DON'T BET"
        elif diff < -0.02:
            flag = "Slightly overpriced"
            signal = "WEAK"
        else:
            flag = "Fairly priced"
            signal = "NEUTRAL"
        
        results[outcome] = {
            "ai_prob": round(ai_p * 100, 1),
            "market_prob": round(mkt_p * 100, 1),
            "differential": round(diff * 100, 2),
            "ev": round(ev * 100, 2),
            "signal": signal,
            "flag": flag,
        }
    
    avg_differential = sum(differentials) / len(differentials)
    
    if avg_differential > 0.05:
        efficiency = "Market INEFFICIENT — significant opportunities exist"
    elif avg_differential > 0.03:
        efficiency = "Market moderately inefficient — some value available"
    else:
        efficiency = "Market EFFICIENT — limited edge opportunities"
    
    # Best value pick
    best = max(results.items(), key=lambda x: x[1]["ev"])
    
    return {
        "outcomes": results,
        "avg_differential": round(avg_differential * 100, 2),
        "market_efficiency": efficiency,
        "best_value_pick": best[0],
        "best_value_ev": best[1]["ev"],
    }


# ═══════════════════════════════════════════════════════════════════
# K. SENTIMENT ANALYSIS (Crowd vs Sharp Divergence)
# ═══════════════════════════════════════════════════════════════════

def sentiment_analysis(home_odds_current: float, home_odds_opening: float,
                      public_pct_home: float, volume_indicator: str = "medium") -> Dict:
    """
    Detect crowd vs sharp divergence.
    
    Key signals:
    - Steam move: odds move fast = sharp action
    - Reverse line: line moves against public = sharp against public
    - Odds lengthening on favorite = money flowing to underdog
    - High volume + line steam = confirmation
    """
    def implied(o):
        return (100 / (o + 100)) if o > 0 else (abs(o) / (abs(o) + 100))
    
    current_implied = implied(home_odds_current)
    opening_implied = implied(home_odds_opening)
    
    # Line movement direction
    if home_odds_current > home_odds_opening:
        direction = "Lengthening (odds up)"
        pct_move = ((home_odds_current - home_odds_opening) / abs(home_odds_opening)) * 100
    elif home_odds_current < home_odds_opening:
        direction = "Shortening (odds down)"
        pct_move = ((home_odds_opening - home_odds_current) / abs(home_odds_opening)) * 100
    else:
        direction = "No movement"
        pct_move = 0
    
    # Steam detection (significant line move)
    is_steam = pct_move > 10
    steam_category = "STEAM" if pct_move > 15 else "Moderate move" if pct_move > 10 else "Normal"
    
    # Reverse Line Movement
    rlm = False
    rlm_type = "None"
    
    if public_pct_home > 65 and home_odds_current > home_odds_opening:
        # Public on home, but odds lengthening = sharp money on AWAY
        rlm = True
        rlm_type = "RLM: Sharp money on AWAY despite public bias on HOME"
    elif public_pct_home < 35 and home_odds_current < home_odds_opening:
        # Public on away, but odds shortening = sharp money on HOME
        rlm = True
        rlm_type = "RLM: Sharp money on HOME despite public bias on AWAY"
    
    # Crowd bias
    if public_pct_home > 70:
        crowd = "Heavy public favorite"
        fade_suggestion = "Consider fading the public (go AWAY)"
    elif public_pct_home > 60:
        crowd = "Public leans home"
        fade_suggestion = "Mild fade consideration"
    elif public_pct_home < 30:
        crowd = "Sharp/reverse public on home"
        fade_suggestion = "Look for home value"
    elif public_pct_home < 40:
        crowd = "Public leans away"
        fade_suggestion = "Public on away = potential home value"
    else:
        crowd = "Balanced public action"
        fade_suggestion = "No clear fade signal"
    
    # Sharp score (0-100, 50 = neutral)
    sharp_score = 50
    if rlm:
        sharp_score += 25
    if is_steam:
        sharp_score += 15
    if public_pct_home > 70:
        sharp_score -= 20  # fade heavy favorites
    elif public_pct_home < 30:
        sharp_score += 15  # sharp on underdog side
    
    return {
        "line_direction": direction,
        "move_pct": round(pct_move, 1),
        "is_steam_move": is_steam,
        "steam_category": steam_category,
        "rlm_detected": rlm,
        "rlm_type": rlm_type,
        "public_sentiment": crowd,
        "fade_suggestion": fade_suggestion,
        "sharp_score": min(100, max(0, sharp_score)),
        "implied_prob_change": round((opening_implied - current_implied) * 100, 2),
        "volume_context": volume_indicator,
    }


# ═══════════════════════════════════════════════════════════════════
# L. WEATHER IMPACT MODEL
# ═══════════════════════════════════════════════════════════════════

def weather_impact(weather: Dict) -> Dict:
    """
    Model weather effects on match outcome and totals.
    
    Input:
        {
            "temp_c": 32,           # temperature
            "humidity": 80,         # percentage
            "wind_kmh": 25,         # wind speed
            "condition": "rain",     # rain/snow/sunny/cloudy/normal
            "precipitation_mm": 5,   # expected rain
        }
    """
    temp = weather.get("temp_c", 20)
    humidity = weather.get("humidity", 50)
    wind = weather.get("wind_kmh", 10)
    condition = weather.get("condition", "normal")
    precip = weather.get("precipitation_mm", 0)
    
    # Temperature impact
    if temp > 35:
        temp_effect = "Extreme heat — fatigue likely, lower scoring"
        gf_modifier = -0.2
    elif temp > 28:
        temp_effect = "Hot — slight fatigue, pace slows"
        gf_modifier = -0.1
    elif temp < 0:
        temp_effect = "Freezing — ball behaves differently"
        gf_modifier = -0.15
    elif temp < 10:
        temp_effect = "Cold — slight impact on play"
        gf_modifier = -0.05
    else:
        temp_effect = "Optimal temperature"
        gf_modifier = 0.0
    
    # Wind impact on long balls / set pieces
    if wind > 40:
        wind_effect = "Very windy — disrupts passing, advantages long-ball teams"
        wind_impact = "high"
        gf_modifier -= 0.15
    elif wind > 25:
        wind_effect = "Moderate wind — slight disruption to passing game"
        wind_impact = "medium"
        gf_modifier -= 0.08
    elif wind > 15:
        wind_effect = "Light breeze — minimal impact"
        wind_impact = "low"
        gf_modifier -= 0.02
    else:
        wind_effect = "Calm — no wind impact"
        wind_impact = "none"
        gf_modifier += 0.0
    
    # Rain impact
    rain_modifier = 0
    if condition == "rain":
        if precip > 10:
            rain_effect = "Heavy rain — pitch condition deteriorates, lower scoring, more errors"
            rain_modifier = -0.25
            fav_defense = True
        elif precip > 5:
            rain_effect = "Moderate rain — slight scoring reduction, wet pitch"
            rain_modifier = -0.15
            fav_defense = True
        else:
            rain_effect = "Light rain — minor impact"
            rain_modifier = -0.05
            fav_defense = False
    elif condition == "snow":
        rain_effect = "Snow — significant disruption, very low scoring likely"
        rain_modifier = -0.35
        fav_defense = True
    else:
        rain_effect = "Dry conditions — no precipitation impact"
        fav_defense = False
    
    # Humidity impact
    if humidity > 85:
        hum_effect = "Very humid — stamina drain, especially for visitors"
        gf_modifier -= 0.08
    elif humidity > 70:
        hum_effect = "Humid — slight stamina effect"
        gf_modifier -= 0.03
    else:
        hum_effect = "Comfortable humidity"
    
    total_gf_modifier = round(gf_modifier + rain_modifier, 2)
    
    # Tactical implications
    tactics = []
    if rain_modifier < -0.1:
        tactics.append("Wet pitch favors defensive teams and long-ball tactics")
        tactics.append("Set pieces become more important")
    if wind_impact in ("high", "medium"):
        tactics.append("Wind disrupts high-pressing and possession play")
    if temp > 30:
        tactics.append("Heat favors rotation-heavy squads and tactical fouling")
    
    # Under/Over lean
    if total_gf_modifier < -0.2:
        total_lean = "Strong lean UNDER"
    elif total_gf_modifier < -0.1:
        total_lean = "Lean UNDER"
    elif total_gf_modifier > 0.1:
        total_lean = "LEAN OVER"
    else:
        total_lean = "Neutral on totals"
    
    return {
        "temp_effect": temp_effect,
        "wind_effect": wind_effect,
        "rain_effect": rain_effect if condition in ("rain", "snow") else "No precipitation",
        "humidity_effect": hum_effect if humidity > 70 else "Comfortable humidity",
        "modifier": total_gf_modifier,
        "defense_favored": fav_defense,
        "total_lean": total_lean,
        "tactical_implications": tactics,
    }


# ═══════════════════════════════════════════════════════════════════
# M. REFEREE ANALYSIS
# ═══════════════════════════════════════════════════════════════════

REFEREE_DB = {
    # name: {"cards_avg": 4.2, "penalty_rate": 0.15, "home_bias": 0.05, "style": "strict/lenient/neutral"}
    "default": {"cards_avg": 3.8, "penalty_rate": 0.12, "home_bias": 0.03, "style": "neutral"},
}

def referee_analysis(referee: str = None, ref_stats: Dict = None) -> Dict:
    """
    Analyze referee tendencies and impact on match.
    
    Args:
        referee: referee name
        ref_stats: {"matches": 50, "yellow_avg": 3.2, "red_avg": 0.15, 
                    "penalty_per_game": 0.12, "home_win_pct": 0.52}
    """
    if ref_stats:
        cards_avg = ref_stats.get("yellow_avg", 3.5) + ref_stats.get("red_avg", 0.1) * 3
        pen_rate = ref_stats.get("penalty_per_game", 0.1)
        home_bias = ref_stats.get("home_win_pct", 0.5) - 0.43  # vs average
        matches = ref_stats.get("matches", 30)
    else:
        ref = REFEREE_DB.get(referee, REFEREE_DB.get("default"))
        cards_avg = ref["cards_avg"]
        pen_rate = ref["penalty_rate"]
        home_bias = ref["home_bias"]
        matches = 0
    
    # Card market implications
    if cards_avg > 5.0:
        card_signal = "High-card referee — lean OVER cards"
        card_risk = "High"
    elif cards_avg > 4.0:
        card_signal = "Above-average card issuer"
        card_risk = "Medium"
    elif cards_avg < 3.0:
        card_signal = "Lenient referee — lean UNDER cards"
        card_risk = "Low"
    else:
        card_signal = "Normal card rate"
        card_risk = "Medium"
    
    # Over/Under implications from aggressive refereeing
    if pen_rate > 0.2:
        penalty_signal = "High penalty rate — slight boost to totals"
    elif pen_rate < 0.08:
        penalty_signal = "Low penalty rate — slight totals reduction"
    else:
        penalty_signal = "Normal penalty rate"
    
    # Home bias impact
    if home_bias > 0.08:
        bias_signal = "Strong home bias referee"
    elif home_bias > 0.04:
        bias_signal = "Moderate home bias"
    elif home_bias < -0.04:
        bias_signal = "Visitor-friendly referee"
    else:
        bias_signal = "Neutral referee — no bias detected"
    
    return {
        "cards_avg": round(cards_avg, 1),
        "penalty_rate": round(pen_rate, 3),
        "home_bias": round(home_bias * 100, 1),
        "card_signal": card_signal,
        "penalty_signal": penalty_signal,
        "bias_signal": bias_signal,
        "card_risk": card_risk,
        "reliability": "High" if matches > 40 else "Medium" if matches > 20 else "Low",
    }


# ═══════════════════════════════════════════════════════════════════
# N. IN-PLAY MOMENTUM MODEL
# ═══════════════════════════════════════════════════════════════════

def in_play_momentum(match_state: Dict) -> Dict:
    """
    Analyze in-play momentum and live betting opportunities.
    
    Input:
        {
            "minute": 65,
            "home_goals": 1, "away_goals": 0,
            "home_possession": 58, "away_possession": 42,
            "home_shots": 12, "away_shots": 5,
            "home_corners": 6, "away_corners": 2,
            "home_cards": 1, "away_cards": 2,
            "momentum_events": ["goal", "red_card", "substitution"],
            "home_pressure": 75,    # 0-100 attacking pressure index
            "away_pressure": 30,
        }
    """
    minute = match_state.get("minute", 0)
    hg = match_state.get("home_goals", 0)
    ag = match_state.get("away_goals", 0)
    h_poss = match_state.get("home_possession", 50)
    h_shots = match_state.get("home_shots", 0)
    a_shots = match_state.get("away_shots", 0)
    h_press = match_state.get("home_pressure", 50)
    a_press = match_state.get("away_pressure", 50)
    h_cards = match_state.get("home_cards", 0)
    a_cards = match_state.get("away_cards", 0)
    
    # Momentum score (-100 to +100, positive = home momentum)
    gd = hg - ag
    possession_diff = h_poss - 50
    shot_diff = h_shots - a_shots
    pressure_diff = h_press - a_press
    card_advantage = (a_cards - h_cards) * 5  # red/yellow advantage
    
    # Time decay: momentum matters more late in game
    time_weight = 1 + (minute / 90) * 0.5
    
    momentum = (
        gd * 25 +
        possession_diff * 0.3 +
        shot_diff * 3 +
        pressure_diff * 0.2 +
        card_advantage
    ) * time_weight
    
    momentum = max(-100, min(100, momentum))
    
    # Momentum classification
    if momentum > 40:
        classification = "Strong home momentum"
    elif momentum > 20:
        classification = "Moderate home momentum"
    elif momentum > -20:
        classification = "Even contest"
    elif momentum > -40:
        classification = "Moderate away momentum"
    else:
        classification = "Strong away momentum"
    
    # Key moments detected
    key_moments = []
    red_cards = match_state.get("red_cards", 0)
    pens = match_state.get("penalties", 0)
    
    if minute > 75 and abs(gd) == 1:
        key_moments.append(f"Late {minute}' — game state likely to hold or see late goal")
    if minute > 60 and momentum > 30 and gd == 0:
        key_moments.append("Home pressing hard — breakthrough possible")
    if red_cards > 0 and minute < 45:
        key_moments.append("Early red card — significant tactical shift")
    if a_cards - h_cards >= 2:
        key_moments.append("Away team card trouble — exploitation opportunity")
    if h_shots > 10 and h_shots > a_shots * 2 and minute > 50:
        key_moments.append("Home dominating shots — goal expected")
    
    # Second half adjustment prediction
    if minute < 20:
        trend = "Too early to call"
    elif momentum > 30:
        trend = "Home likely to extend or maintain advantage"
    elif momentum < -30:
        trend = "Away likely to threaten or extend"
    else:
        trend = "Game still in balance — next goal crucial"
    
    return {
        "momentum_score": round(momentum, 0),
        "classification": classification,
        "goal_differential": gd,
        "dominance_index": round((h_poss + h_press) / 2 - (match_state.get("away_possession", 50) + a_press) / 2, 1),
        "key_moments": key_moments,
        "second_half_trend": trend,
        "next_goal": "Home" if momentum > 20 else "Away" if momentum < -20 else "Uncertain",
    }


# ═══════════════════════════════════════════════════════════════════
# O. CROSS-LEAGUE H2H DATABASE
# ═══════════════════════════════════════════════════════════════════

def cross_league_h2h(team_a: str, team_b: str, 
                     h2h_history: List[Dict] = None,
                     league_context: str = None) -> Dict:
    """
    Analyze head-to-head patterns including cross-league matchups.
    
    For WC2026, this uses:
    - Competitive H2H (WC qualifiers, friendlies)
    - Style-based analysis when direct H2H is unavailable
    - Regional matchup patterns (CONCACAF vs UEFA, etc.)
    
    h2h_history: [{"date": "...", "competition": "...", "home": team_a, "away": team_b, "score": "2-1"}, ...]
    """
    if not h2h_history:
        return {
            "h2h_available": False,
            "note": "No direct H2H — using style-based projection",
            "style_projection": "Analyze playing styles for matchup edge",
        }
    
    total = len(h2h_history)
    a_wins = 0
    b_wins = 0
    draws = 0
    goals_a = 0
    goals_b = 0
    results_by_comp = Counter()
    
    for h in h2h_history:
        if h.get("home") == team_a:
            ga, gb = h.get("home_goals", 0), h.get("away_goals", 0)
        else:
            ga, gb = h.get("away_goals", 0), h.get("home_goals", 0)
        
        goals_a += ga
        goals_b += gb
        
        if ga > gb:
            a_wins += 1
        elif ga < gb:
            b_wins += 1
        else:
            draws += 1
        
        results_by_comp[h.get("competition", "Unknown")] += 1
    
    # Recent form weighting (recent matches count more)
    recent_5 = h2h_history[-5:] if len(h2h_history) >= 5 else h2h_history
    recent_a_wins = sum(1 for h in recent_5 
                        if (h.get("home") == team_a and h.get("home_goals", 0) > h.get("away_goals", 0)) or
                           (h.get("away") == team_a and h.get("away_goals", 0) > h.get("home_goals", 0)))
    
    avg_gf_a = goals_a / total if total > 0 else 0
    avg_gf_b = goals_b / total if total > 0 else 0
    
    if a_wins > b_wins + 2:
        h2h_edge = f"{team_a} dominates H2H"
    elif b_wins > a_wins + 2:
        h2h_edge = f"{team_b} dominates H2H"
    else:
        h2h_edge = "H2H relatively balanced"
    
    return {
        "h2h_available": True,
        "total_matches": total,
        f"{team_a}_wins": a_wins,
        f"{team_b}_wins": b_wins,
        "draws": draws,
        f"{team_a}_avg_gf": round(avg_gf_a, 2),
        f"{team_b}_avg_gf": round(avg_gf_b, 2),
        "recent_5_a_wins": recent_a_wins,
        "h2h_edge": h2h_edge,
        "by_competition": dict(results_by_comp),
        "confidence": "High" if total >= 5 else "Medium" if total >= 3 else "Low",
    }


# ═══════════════════════════════════════════════════════════════════
# P. BETTING MARKET DEPTH — Multi-Bookmaker Comparison
# ═══════════════════════════════════════════════════════════════════

def market_depth_analysis(odds_by_bookmaker: Dict[str, Dict]) -> Dict:
    """
    Compare odds across multiple bookmakers for best value + detect steam.
    
    Input:
        {
            "Pinnacle": {"home": 1.85, "draw": 3.40, "away": 4.50},
            "Bet365": {"home": 1.80, "draw": 3.50, "away": 4.40},
            "DraftKings": {"home": 1.83, "draw": 3.45, "away": 4.60},
            "FanDuel": {"home": 1.82, "draw": 3.55, "away": 4.30},
            "local_book": {"home": 1.75, "draw": 3.30, "away": 5.00},
        }
    """
    outcomes = ["home", "draw", "away"]
    
    best_odds = {}
    worst_odds = {}
    all_implied = []
    
    for outcome in outcomes:
        odds_list = [(book, o[outcome]) for book, o in odds_by_bookmaker.items() if outcome in o]
        if odds_list:
            best_book, best_o = max(odds_list, key=lambda x: x[1])
            worst_book, worst_o = min(odds_list, key=lambda x: x[1])
            avg_o = sum(o for _, o in odds_list) / len(odds_list)
            
            best_odds[outcome] = {"book": best_book, "odds": round(best_o, 2)}
            worst_odds[outcome] = {"book": worst_book, "odds": round(worst_o, 2)}
            
            implied = 1 / avg_o
            all_implied.append(implied)
    
    # Market consensus vig
    total_implied = sum(all_implied)
    vig_pct = round((total_implied - 1) * 100, 2)
    
    # Fair odds (no vig)
    fair_probs = [p / total_implied for p in all_implied]
    fair_odds = {o: round(1 / p, 2) for o, p in zip(outcomes, fair_probs)}
    
    # Arbitrage check
    min_arb_cost = sum(1 / best_odds[o]["odds"] for o in outcomes if o in best_odds)
    arb_possible = min_arb_cost < 1.0
    
    # Outlier detection (books with significantly different odds)
    outliers = []
    for outcome in outcomes:
        odds_list = [o[outcome] for o in odds_by_bookmaker.values() if outcome in o]
        if len(odds_list) >= 3:
            avg = sum(odds_list) / len(odds_list)
            for book, o in odds_by_bookmaker.items():
                if outcome in o and abs(o[outcome] - avg) / avg > 0.05:
                    direction = "high" if o[outcome] > avg else "low"
                    outliers.append(f"{book}: {o[outcome]} ({direction} vs avg {avg:.2f})")
    
    # Shopping value (best vs worst)
    shopping_value = {}
    for outcome in outcomes:
        if outcome in best_odds and outcome in worst_odds:
            bv = ((best_odds[outcome]["odds"] / worst_odds[outcome]["odds"]) - 1) * 100
            shopping_value[outcome] = round(bv, 2)
    
    return {
        "best_odds": best_odds,
        "worst_odds": worst_odds,
        "fair_odds": fair_odds,
        "market_vig_pct": vig_pct,
        "arbitrage_possible": arb_possible,
        "arbitrage_margin_pct": round((1 - min_arb_cost) * 100, 2) if arb_possible else 0,
        "outliers": outliers,
        "line_shopping_value": shopping_value,
        "consensus_recommendation": {
            "home": f"Best at {best_odds.get('home', {}).get('book', 'N/A')} @ {best_odds.get('home', {}).get('odds', 'N/A')}",
            "draw": f"Best at {best_odds.get('draw', {}).get('book', 'N/A')} @ {best_odds.get('draw', {}).get('odds', 'N/A')}",
            "away": f"Best at {best_odds.get('away', {}).get('book', 'N/A')} @ {best_odds.get('away', {}).get('odds', 'N/A')}",
        }
    }


# ═══════════════════════════════════════════════════════════════════
# Q. RISK-ADJUSTED RETURNS — Sharpe/Sortino for Betting
# ═══════════════════════════════════════════════════════════════════

def risk_adjusted_returns(bet_history: List[Dict] = None,
                          projected_bets: List[Dict] = None,
                          risk_free_rate: float = 0.0) -> Dict:
    """
    Calculate Sharpe ratio, Sortino ratio for betting portfolio.
    
    bet_history: [{"stake": 50, "odds": 2.10, "won": True}, ...]
    projected_bets: [{"stake": 50, "odds": 1.85, "prob": 0.55, "ev": 2.5}, ...]
    """
    results = {}
    
    # Historical analysis
    if bet_history:
        returns = []
        for bet in bet_history:
            if bet.get("won"):
                ret = bet["stake"] * (bet["odds"] - 1) / bet["stake"]
            else:
                ret = -1.0
            returns.append(ret)
        
        n = len(returns)
        if n >= 5:
            avg_ret = sum(returns) / n
            variance = sum((r - avg_ret) ** 2 for r in returns) / n
            std_dev = math.sqrt(variance) if variance > 0 else 0.001
            
            # Downside deviation (for Sortino)
            downside = [min(0, r) for r in returns]
            downside_var = sum(d ** 2 for d in downside) / n
            downside_dev = math.sqrt(downside_var) if downside_var > 0 else 0.001
            
            sharpe = (avg_ret - risk_free_rate) / std_dev if std_dev > 0 else 0
            sortino = (avg_ret - risk_free_rate) / downside_dev if downside_dev > 0 else 0
            
            results["historical"] = {
                "n_bets": n,
                "avg_return": round(avg_ret * 100, 2),
                "std_dev": round(std_dev * 100, 2),
                "downside_dev": round(downside_dev * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "sortino_ratio": round(sortino, 3),
                "max_return": round(max(returns) * 100, 1),
                "min_return": round(min(returns) * 100, 1),
                "win_rate": round(sum(1 for r in returns if r > 0) / n * 100, 1),
            }
    
    # Projected portfolio analysis
    if projected_bets:
        total_stake = sum(b["stake"] for b in projected_bets)
        expected_return = sum(
            b["stake"] * (b.get("prob", 0.5) * b["odds"] - 1) for b in projected_bets
        )
        
        # Portfolio variance (assuming independent bets)
        portfolio_var = sum(
            b["stake"] ** 2 * b.get("prob", 0.5) * (1 - b.get("prob", 0.5))
            for b in projected_bets
        )
        portfolio_std = math.sqrt(portfolio_var) if portfolio_var > 0 else 0.001
        
        port_sharpe = (expected_return / total_stake) / (portfolio_std / total_stake) if portfolio_std > 0 else 0
        
        # Probability of losing entire stake
        loss_prob = 1.0
        for b in projected_bets:
            loss_prob *= (1 - b.get("prob", 0.5))
        
        results["projected"] = {
            "total_stake": round(total_stake, 2),
            "expected_return": round(expected_return, 2),
            "expected_roi": round((expected_return / total_stake) * 100, 2) if total_stake > 0 else 0,
            "portfolio_sharpe": round(port_sharpe, 3),
            "portfolio_risk": round((portfolio_std / total_stake) * 100, 2),
            "total_loss_probability": round(loss_prob * 100, 2),
        }
    
    return results


# ═══════════════════════════════════════════════════════════════════
# R. PORTFOLIO OPTIMIZER — Kelly Across Multiple Bets
# ═══════════════════════════════════════════════════════════════════

def portfolio_optimizer(bets: List[Dict], bankroll: float, 
                        max_correlation: float = 0.3,
                        max_exposure: float = 0.10) -> Dict:
    """
    Optimize bet sizing across multiple concurrent bets using Kelly + correlation.
    
    bets: [{"match": "...", "prob": 0.55, "odds": 1.85, "correlation_group": "group_a"}, ...]
    """
    n = len(bets)
    if n == 0:
        return {"error": "No bets provided"}
    
    # Individual Kelly fractions
    kelly_fractions = []
    for bet in bets:
        p = bet["prob"]
        b = bet["odds"] - 1
        q = 1 - p
        k = max(0, (b * p - q) / b) if b > 0 else 0
        kelly_fractions.append(k)
    
    # Correlation adjustment
    groups = {}
    for i, bet in enumerate(bets):
        grp = bet.get("correlation_group", f"group_{i}")
        groups.setdefault(grp, []).append(i)
    
    # Reduce Kelly for correlated bets
    adjusted_kelly = kelly_fractions.copy()
    for grp, indices in groups.items():
        if len(indices) > 1:
            # Reduce by factor based on group size
            reduction = max(0.5, 1 - (len(indices) - 1) * 0.15)
            for idx in indices:
                adjusted_kelly[idx] *= reduction
    
    # Half-Kelly safety
    half_kelly = [k * 0.5 for k in adjusted_kelly]
    
    # Total allocation check
    total_alloc = sum(half_kelly)
    
    # Scale down if over max exposure
    if total_alloc > max_exposure:
        scale = max_exposure / total_alloc
        half_kelly = [k * scale for k in half_kelly]
    
    # Calculate stakes
    total_stake = 0
    bet_allocations = []
    for i, bet in enumerate(bets):
        stake = round(bankroll * half_kelly[i], 2)
        potential = round(stake * bet["odds"], 2) if stake > 0 else 0
        total_stake += stake
        
        bet_allocations.append({
            "match": bet.get("match", f"Bet {i+1}"),
            "prob": round(bet["prob"] * 100, 1),
            "odds": bet["odds"],
            "full_kelly": round(kelly_fractions[i] * 100, 2),
            "adjusted_kelly": round(adjusted_kelly[i] * 100, 2),
            "half_kelly": round(half_kelly[i] * 100, 2),
            "stake": stake,
            "potential_payout": potential,
            "group": bet.get("correlation_group", "none"),
        })
    
    # Portfolio metrics
    total_ev = sum(
        alloc["stake"] * (bets[i]["prob"] * bets[i]["odds"] - 1) / bankroll * 100
        for i, alloc in enumerate(bet_allocations)
    )
    
    return {
        "bankroll": bankroll,
        "num_bets": n,
        "total_stake": round(total_stake, 2),
        "total_exposure_pct": round((total_stake / bankroll) * 100, 2),
        "total_ev_pct": round(total_ev, 2),
        "allocations": bet_allocations,
        "diversification_score": round(max(0, 100 - total_alloc * 200), 1),
    }


# ═══════════════════════════════════════════════════════════════════
# S. STREAK ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def streak_analysis(results: List[str], market_odds: List[float] = None) -> Dict:
    """
    Analyze win/loss/draw streaks and regression to mean.
    
    results: ["W", "W", "D", "L", "W", "W", "W", "D", "L", "L"]
    market_odds: [1.80, 2.10, 3.20, ...] — odds at time of each result
    """
    n = len(results)
    if n < 3:
        return {"error": "Need at least 3 results for streak analysis"}
    
    # Current streak
    current = results[-1]
    current_streak = 0
    for r in reversed(results):
        if r == current:
            current_streak += 1
        else:
            break
    
    # Longest streaks
    longest = {"W": 0, "D": 0, "L": 0}
    running = {"W": 0, "D": 0, "L": 0}
    for r in results:
        for k in running:
            if k == r:
                running[k] += 1
                longest[k] = max(longest[k], running[k])
            else:
                running[k] = 0
    
    # Streak frequency
    streaks = []
    s_type = results[0]
    s_len = 1
    for r in results[1:]:
        if r == s_type:
            s_len += 1
        else:
            streaks.append((s_type, s_len))
            s_type = r
            s_len = 1
    streaks.append((s_type, s_len))
    
    avg_streak_len = sum(s for _, s in streaks) / len(streaks)
    
    # Regression to mean signal
    if current_streak >= 4:
        regression = f"⚠️ {current_streak}-game {current} streak — regression likely"
        regression_signal = "STRONG"
    elif current_streak >= 3:
        regression = f"• {current_streak}-game {current} streak — watch for regression"
        regression_signal = "MODERATE"
    else:
        regression = f"Current {current} streak: {current_streak} — within normal range"
        regression_signal = "NONE"
    
    # Win rate during streaks vs non-streaks
    win_rate = results.count("W") / n * 100
    
    # Momentum score (recent weighted)
    weights = [0.5 ** (n - 1 - i) for i in range(n)]
    w_score = sum(w for r, w in zip(results, weights) if r == "W")
    l_score = sum(w for r, w in zip(results, weights) if r == "L")
    momentum = (w_score - l_score) / (w_score + l_score) * 100 if (w_score + l_score) > 0 else 0
    
    return {
        "current_streak": f"{current_streak} {current}",
        "longest_streaks": longest,
        "total_streaks": len(streaks),
        "avg_streak_length": round(avg_streak_len, 1),
        "overall_win_rate": round(win_rate, 1),
        "regression_signal": regression_signal,
        "regression_warning": regression,
        "momentum_score": round(momentum, 1),
        "streak_history": [{"type": t, "length": l} for t, l in streaks[-5:]],
    }


# ═══════════════════════════════════════════════════════════════════
# T. GOAL TIMING MODEL
# ═══════════════════════════════════════════════════════════════════

def goal_timing_model(team_profile: Dict) -> Dict:
    """
    Analyze when goals are most likely (1H vs 2H, specific minute ranges).
    
    Input:
        {
            "first_half_goals_pct": 0.42,  # % of goals scored in 1H
            "goals_by_period": {
                "0-15": 0.12, "15-30": 0.18, "30-45": 0.15,
                "45-60": 0.15, "60-75": 0.18, "75-90": 0.22
            },
            "late_goals_tendency": "high",  # high/medium/low
            "early_goals_tendency": "low",
        }
    """
    fh_pct = team_profile.get("first_half_goals_pct", 0.45)
    periods = team_profile.get("goals_by_period", {})
    
    # 1H vs 2H split
    sh_pct = 1 - fh_pct
    
    if fh_pct > 0.55:
        timing = "First-half heavy scorer"
        live_betting = "Consider live over bets in 1H"
    elif fh_pct < 0.35:
        timing = "Second-half heavy scorer"
        live_betting = "Consider live over bets in 2H, especially 75-90"
    else:
        timing = "Evenly distributed scoring"
        live_betting = "No strong timing edge"
    
    # Peak scoring periods
    if periods:
        peak = max(periods.items(), key=lambda x: x[1])
        low = min(periods.items(), key=lambda x: x[1])
    else:
        peak = ("unknown", 0)
        low = ("unknown", 0)
    
    # Late goal tendency
    late = team_profile.get("late_goals_tendency", "medium")
    early = team_profile.get("early_goals_tendency", "medium")
    
    # BTTS timing
    if fh_pct > 0.5 and late == "high":
        btts_timing = "BTTS likely — both teams score early, late goals add"
    elif fh_pct < 0.4 and late == "high":
        btts_timing = "BTTS in 2H likely — slow start, open finish"
    else:
        btts_timing = "BTTS timing neutral"
    
    return {
        "first_half_pct": round(fh_pct * 100, 1),
        "second_half_pct": round(sh_pct * 100, 1),
        "timing_profile": timing,
        "peak_period": f"{peak[0]} min ({peak[1]*100:.0f}% of goals)",
        "lowest_period": f"{low[0]} min ({low[1]*100:.0f}% of goals)",
        "late_goal_tendency": late,
        "early_goal_tendency": early,
        "live_betting_tip": live_betting,
        "btts_timing": btts_timing,
    }


# ═══════════════════════════════════════════════════════════════════
# U. ALTERNATIVE LINE FINDER
# ═══════════════════════════════════════════════════════════════════

def alternative_lines(ai_probs: Dict, base_odds: Dict) -> Dict:
    """
    Find best alternative spreads and totals for a match.
    
    Args:
        ai_probs: {"home_2_5": 0.05, "home_2": 0.08, "home_1_5": 0.12, ...}
                  (from Poisson model)
        base_odds: {"home": 1.85, "draw": 3.40, "away": 4.50}
    """
    alternatives = {}
    
    # Alternative spreads
    spreads = [
        ("AH -2.5", ai_probs.get("home_2_5", 0)),
        ("AH -2", ai_probs.get("home_2", 0)),
        ("AH -1.5", ai_probs.get("home_1_5", 0)),
        ("AH -1", ai_probs.get("home_1", 0)),
        ("AH -0.5", ai_probs.get("home_0_5", 0)),
        ("AH +0.5", ai_probs.get("away_0_5", 0)),
        ("AH +1", ai_probs.get("away_1", 0)),
        ("AH +1.5", ai_probs.get("away_1_5", 0)),
    ]
    
    # Alternative totals
    totals = [
        ("O 1.5", ai_probs.get("over_1_5", 0)),
        ("O 2", ai_probs.get("over_2", 0)),
        ("O 2.5", ai_probs.get("over_2_5", 0)),
        ("O 3", ai_probs.get("over_3", 0)),
        ("O 3.5", ai_probs.get("over_3_5", 0)),
        ("U 2.5", ai_probs.get("under_2_5", 0)),
        ("U 3.5", ai_probs.get("under_3_5", 0)),
    ]
    
    # Find best value alternatives (highest probability above threshold)
    best_spreads = []
    for name, prob in spreads:
        if prob > 0.15:  # minimum 15% probability
            # Estimate fair odds
            fair_odds = 1 / prob if prob > 0 else 999
            best_spreads.append({
                "line": name,
                "ai_prob": round(prob * 100, 1),
                "fair_odds": round(fair_odds, 2),
                "value": "Good" if prob > 0.25 else "Decent" if prob > 0.15 else "Marginal",
            })
    
    best_totals = []
    for name, prob in totals:
        if prob > 0.20:
            fair_odds = 1 / prob if prob > 0 else 999
            best_totals.append({
                "line": name,
                "ai_prob": round(prob * 100, 1),
                "fair_odds": round(fair_odds, 2),
                "value": "Good" if prob > 0.55 else "Decent" if prob > 0.40 else "Marginal",
            })
    
    # Sort by probability
    best_spreads.sort(key=lambda x: x["ai_prob"], reverse=True)
    best_totals.sort(key=lambda x: x["ai_prob"], reverse=True)
    
    return {
        "best_spreads": best_spreads[:5],
        "best_totals": best_totals[:5],
        "recommendation": f"Best spread: {best_spreads[0]['line']}" if best_spreads else "No strong spread value",
        "total_recommendation": f"Best total: {best_totals[0]['line']}" if best_totals else "No strong total value",
    }


# ═══════════════════════════════════════════════════════════════════
# V. CONTRARIAN SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════════

def contrarian_signals(match: Dict, market: Dict, public_data: Dict) -> Dict:
    """
    Generate contrarian betting signals — fade the public opportunities.
    
    Combines multiple signals to identify when the crowd is wrong.
    """
    signals = []
    contrarian_score = 50  # 0 = follow public, 100 = strong contrarian
    
    # Signal 1: Heavy public on favorite + line moving away
    public_home = public_data.get("pct_home", 50)
    if public_home > 75 and market.get("home_odds_current", 0) > market.get("home_odds_opening", 0):
        signals.append("🔴 Heavy public on home + odds lengthening = SHARP MONEY ON AWAY")
        contrarian_score += 25
    
    # Signal 2: Lopsided public but odds not moving
    if public_home > 80 and abs(market.get("home_odds_current", 0) - market.get("home_odds_opening", 0)) < 5:
        signals.append("🟡 Lopsided public but line steady = bookmakers not concerned")
        contrarian_score += 10
    
    # Signal 3: Underdog value
    if public_home > 70:
        away_pct = 100 - public_home
        if away_pct < 20:
            signals.append("🟡 Heavy public favorite — underdog may be value")
            contrarian_score += 15
    
    # Signal 4: Market efficiency gap
    ai_home = match.get("ai_home_prob", 0.5)
    market_home = 1 / market.get("home_odds_current", 2.0)
    if ai_home < market_home - 0.1:
        signals.append("🔴 AI model significantly lower on home than market")
        contrarian_score += 20
    elif ai_home > market_home + 0.1:
        signals.append("🟢 AI model higher on home than market — follow model")
        contrarian_score -= 15
    
    # Signal 5: Historical fade patterns
    if public_data.get("historical_fade_success", 0) > 0.6:
        signals.append("🟢 Historical fade pattern successful in this matchup type")
        contrarian_score += 15
    
    # Signal 6: Tournament context
    tournament = match.get("tournament", "")
    if "World Cup" in tournament and public_home > 70:
        signals.append("🟡 WC matches have more variance — favorites underperform")
        contrarian_score += 10
    
    # Final verdict
    if contrarian_score > 75:
        verdict = "STRONG CONTRARIAN — Fade the public aggressively"
        action = "Bet against the public favorite"
    elif contrarian_score > 60:
        verdict = "MODERATE CONTRARIAN — Consider fading"
        action = "Look for value on the underdog side"
    elif contrarian_score > 40:
        verdict = "NEUTRAL — No strong contrarian signal"
        action = "Follow your model, no public fade needed"
    else:
        verdict = "FOLLOW PUBLIC — Crowd may be right"
        action = "Public aligned with model — consider following"
    
    return {
        "contrarian_score": min(100, max(0, contrarian_score)),
        "signals": signals,
        "verdict": verdict,
        "recommended_action": action,
        "fade_direction": "Away" if contrarian_score > 60 else "Home" if contrarian_score < 40 else "None",
    }


# ═══════════════════════════════════════════════════════════════════
# MASTER ANALYSIS — Combine all modules
# ═══════════════════════════════════════════════════════════════════

def deep_analysis(match: Dict, context: Dict = None) -> Dict:
    """
    Run all advanced analysis modules and combine into comprehensive report.
    
    Returns full analysis with all modules H-V.
    """
    if context is None:
        context = {}
    
    # Get base probabilities from Poisson model
    home_lam = context.get("home_lambda", 1.5)
    away_lam = context.get("away_lambda", 1.2)
    
    poisson = poisson_scoreline_matrix(home_lam, away_lam)
    
    # ELO ratings
    elo = EloRating(context.get("elo_ratings", {}))
    elo_pred = elo.match_prediction(match.get("home_team", ""), match.get("away_team", ""))
    
    # Market efficiency
    ai_probs = {
        "home": poisson["home_win_prob"] / 100,
        "draw": poisson["draw_prob"] / 100,
        "away": poisson["away_win_prob"] / 100,
    }
    market_odds = {
        "home": context.get("odds_home", 1.85),
        "draw": context.get("odds_draw", 3.40),
        "away": context.get("odds_away", 4.50),
    }
    efficiency = market_efficiency_test(ai_probs, market_odds)
    
    # Sentiment
    sentiment = sentiment_analysis(
        context.get("odds_home_current", 1.85),
        context.get("odds_home_opening", 1.80),
        context.get("public_pct_home", 50),
    )
    
    # Weather
    weather = weather_impact(context.get("weather", {}))
    
    # Referee
    referee = referee_analysis(
        context.get("referee"),
        context.get("ref_stats"),
    )
    
    # H2H
    h2h = cross_league_h2h(
        match.get("home_team", ""),
        match.get("away_team", ""),
        context.get("h2h_history"),
    )
    
    # Market depth
    if context.get("odds_by_bookmaker"):
        depth = market_depth_analysis(context["odds_by_bookmaker"])
    else:
        depth = {"note": "No multi-bookmaker data provided"}
    
    # Streak analysis
    if context.get("recent_results"):
        streaks = streak_analysis(context["recent_results"])
    else:
        streaks = {"note": "No recent results provided"}
    
    # Goal timing
    timing = goal_timing_model(context.get("goal_timing", {}))
    
    # Alternative lines
    alt_probs = {
        "home_2_5": poisson["exact_scores"].get("3-0", 0) + poisson["exact_scores"].get("4-0", 0) + poisson["exact_scores"].get("3-1", 0) + poisson["exact_scores"].get("4-1", 0) + poisson["exact_scores"].get("5-0", 0),
        "home_1_5": poisson["exact_scores"].get("2-0", 0) + poisson["exact_scores"].get("2-1", 0),
        "over_2_5": poisson["over_2_5"],
        "over_3_5": poisson["over_3_5"],
        "under_2_5": 100 - poisson["over_2_5"],
        "under_3_5": 100 - poisson["over_3_5"],
    }
    alternatives = alternative_lines(alt_probs, market_odds)
    
    # Contrarian signals
    contrarian = contrarian_signals(
        match,
        {"home_odds_current": market_odds["home"], "home_odds_opening": context.get("odds_home_opening", market_odds["home"])},
        {"pct_home": context.get("public_pct_home", 50)},
    )
    
    # Risk-adjusted returns
    risk_adj = risk_adjusted_returns(
        projected_bets=[{
            "stake": context.get("stake", 50),
            "odds": market_odds["home"],
            "prob": ai_probs["home"],
            "ev": efficiency["outcomes"]["home"]["ev"],
        }]
    )
    
    # Portfolio optimizer
    if context.get("portfolio_bets"):
        portfolio = portfolio_optimizer(context["portfolio_bets"], context.get("bankroll", 1000))
    else:
        portfolio = {"note": "No portfolio bets provided"}
    
    return {
        "match": f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}",
        "poisson_model": poisson,
        "elo_prediction": elo_pred,
        "market_efficiency": efficiency,
        "sentiment_analysis": sentiment,
        "weather_impact": weather,
        "referee_analysis": referee,
        "h2h_analysis": h2h,
        "market_depth": depth,
        "streak_analysis": streaks,
        "goal_timing": timing,
        "alternative_lines": alternatives,
        "contrarian_signals": contrarian,
        "risk_adjusted_returns": risk_adj,
        "portfolio_optimizer": portfolio,
    }


# ═══════════════════════════════════════════════════════════════════
# W. UNDER/OVER DEEP ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def under_over_analysis(home_lam: float, away_lam: float, 
                        market_totals: Dict = None,
                        team_profiles: Dict = None,
                        context: Dict = None) -> Dict:
    """
    Deep Under/Over analysis with multiple models and market comparison.
    
    Args:
        home_lam: Poisson lambda for home team goals
        away_lam: Poisson lambda for away team goals
        market_totals: {"O2.5": 1.90, "U2.5": 1.95, "O3.5": 2.50, "U3.5": 1.55, ...}
        team_profiles: {
            "home": {"avg_gf": 1.8, "avg_ga": 1.0, "over_pct": 0.55, "high_scoring": True},
            "away": {"avg_gf": 1.3, "avg_ga": 1.2, "over_pct": 0.48, "high_scoring": False}
        }
        context: {"weather_modifier": -0.1, "ref_penalty_rate": 0.12, "is_knockout": False}
    """
    if market_totals is None:
        market_totals = {}
    if team_profiles is None:
        team_profiles = {}
    if context is None:
        context = {}
    
    total_lam = home_lam + away_lam
    weather_mod = context.get("weather_modifier", 0)
    adjusted_lam = max(0.5, total_lam + weather_mod)
    
    # ── Poisson-based total goals probabilities ──
    total_probs = {}
    for n in range(0, 10):
        # P(exactly n goals) = sum over all (i, j) where i+j=n
        p = 0.0
        for i in range(n + 1):
            j = n - i
            p += poisson_pmf(home_lam, i) * poisson_pmf(away_lam, j)
        total_probs[n] = p
    
    # Cumulative probabilities
    cum_probs = {}
    running = 0.0
    for n in range(0, 10):
        running += total_probs.get(n, 0)
        cum_probs[n] = running
    
    # ── Standard line probabilities ──
    lines = {
        "O1.5": 1 - cum_probs.get(1, 0),
        "U1.5": cum_probs.get(1, 0),
        "O2.0": 1 - cum_probs.get(1, 0),
        "U2.0": cum_probs.get(1, 0),
        "O2.5": 1 - cum_probs.get(2, 0),
        "U2.5": cum_probs.get(2, 0),
        "O3.0": 1 - cum_probs.get(2, 0),
        "U3.0": cum_probs.get(2, 0),
        "O3.5": 1 - cum_probs.get(3, 0),
        "U3.5": cum_probs.get(3, 0),
        "O4.0": 1 - cum_probs.get(3, 0),
        "U4.0": cum_probs.get(3, 0),
        "O4.5": 1 - cum_probs.get(4, 0),
        "U4.5": cum_probs.get(4, 0),
        "O5.5": 1 - cum_probs.get(5, 0),
        "U5.5": cum_probs.get(5, 0),
    }
    
    # ── Expected total goals ──
    expected_goals = adjusted_lam
    variance = adjusted_lam  # Poisson variance = lambda
    std_dev = math.sqrt(variance)
    
    # ── Most likely total ──
    mode_goals = math.floor(adjusted_lam)
    
    # ── Team profile adjustments ──
    home_profile = team_profiles.get("home", {})
    away_profile = team_profiles.get("away", {})
    
    home_over_pct = home_profile.get("over_pct", 0.50)
    away_over_pct = away_profile.get("over_pct", 0.50)
    home_high_scoring = home_profile.get("high_scoring", False)
    away_high_scoring = away_profile.get("high_scoring", False)
    
    # Combined over tendency
    combined_over_pct = (home_over_pct + away_over_pct) / 2
    
    # ── Market comparison & value detection ──
    value_lines = []
    for line_name, ai_prob in lines.items():
        if line_name in market_totals:
            market_odds = market_totals[line_name]
            market_prob = 1 / market_odds
            edge = ai_prob - market_prob
            ev = (ai_prob * market_odds) - 1
            
            if edge > 0.05 and ev > 0.05:
                signal = "STRONG VALUE"
                recommendation = f"Bet {line_name} — market underpricing"
            elif edge > 0.02 and ev > 0.02:
                signal = "VALUE"
                recommendation = f"Consider {line_name} — slight edge"
            elif edge < -0.05:
                signal = "OVERPRICED"
                recommendation = f"Avoid {line_name} — market overpricing"
            else:
                signal = "FAIR"
                recommendation = f"{line_name} fairly priced"
            
            value_lines.append({
                "line": line_name,
                "ai_prob": round(ai_prob * 100, 1),
                "market_odds": market_odds,
                "market_prob": round(market_prob * 100, 1),
                "edge": round(edge * 100, 2),
                "ev": round(ev * 100, 2),
                "signal": signal,
                "recommendation": recommendation,
            })
    
    # Sort by EV
    value_lines.sort(key=lambda x: x["ev"], reverse=True)
    
    # ── Goal distribution analysis ──
    goal_dist = {}
    for n in range(0, 8):
        goal_dist[f"{n} goals"] = round(total_probs.get(n, 0) * 100, 1)
    
    # ── Scoring intensity classification ──
    if adjusted_lam > 3.0:
        intensity = "HIGH SCORING EXPECTED"
        intensity_emoji = "🔥"
    elif adjusted_lam > 2.3:
        intensity = "MODERATE-HIGH SCORING"
        intensity_emoji = "⚡"
    elif adjusted_lam > 1.8:
        intensity = "MODERATE SCORING"
        intensity_emoji = "📊"
    elif adjusted_lam > 1.3:
        intensity = "LOW-MODERATE SCORING"
        intensity_emoji = "🛡️"
    else:
        intensity = "LOW SCORING EXPECTED"
        intensity_emoji = "🔒"
    
    # ── Best line recommendation ──
    o25_prob = lines.get("O2.5", 0.5)
    u25_prob = lines.get("U2.5", 0.5)
    
    if o25_prob > 0.60:
        best_total = "O2.5 — Strong over"
    elif o25_prob > 0.55:
        best_total = "O2.5 — Lean over"
    elif u25_prob > 0.60:
        best_total = "U2.5 — Strong under"
    elif u25_prob > 0.55:
        best_total = "U2.5 — Lean under"
    elif o25_prob > 0.50:
        best_total = "O2.5 — Slight lean over"
    elif u25_prob > 0.50:
        best_total = "U2.5 — Slight lean under"
    else:
        best_total = "No strong total signal"
    
    # ── Alternative total lines ──
    alt_totals = []
    for line_name in ["O1.5", "U1.5", "O2.5", "U2.5", "O3.5", "U3.5", "O4.5", "U4.5"]:
        prob = lines.get(line_name, 0)
        if prob > 0.20:
            fair_odds = 1 / prob if prob > 0 else 999
            alt_totals.append({
                "line": line_name,
                "ai_prob": round(prob * 100, 1),
                "fair_odds": round(fair_odds, 2),
            })
    
    alt_totals.sort(key=lambda x: x["ai_prob"], reverse=True)
    
    # ── Contextual factors ──
    factors = []
    if weather_mod < -0.1:
        factors.append(f"Weather reducing scoring ({weather_mod:+.1f} goals)")
    if home_high_scoring and away_high_scoring:
        factors.append("Both teams high-scoring — over favored")
    if not home_high_scoring and not away_high_scoring:
        factors.append("Both teams low-scoring — under favored")
    if context.get("is_knockout"):
        factors.append("Knockout match — caution may reduce scoring")
    if context.get("ref_penalty_rate", 0) > 0.15:
        factors.append("High penalty referee — slight over boost")
    
    return {
        "expected_goals": round(expected_goals, 2),
        "variance": round(variance, 2),
        "std_dev": round(std_dev, 2),
        "mode_goals": mode_goals,
        "scoring_intensity": f"{intensity_emoji} {intensity}",
        "goal_distribution": goal_dist,
        "line_probabilities": {k: round(v * 100, 1) for k, v in lines.items()},
        "best_total_line": best_total,
        "value_lines": value_lines[:6],
        "alternative_totals": alt_totals[:6],
        "combined_over_pct": round(combined_over_pct * 100, 1),
        "contextual_factors": factors,
        "home_lambda": round(home_lam, 2),
        "away_lambda": round(away_lam, 2),
        "adjusted_lambda": round(adjusted_lam, 2),
    }


# ═══════════════════════════════════════════════════════════════════
# X. BTTS (BOTH TEAMS TO SCORE) DEEP ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def btts_analysis(home_lam: float, away_lam: float,
                  market_btts: Dict = None,
                  team_profiles: Dict = None,
                  h2h_data: List[Dict] = None) -> Dict:
    """
    Deep BTTS (Both Teams to Score) analysis.
    
    Args:
        home_lam: Poisson lambda for home team
        away_lam: Poisson lambda for away team
        market_btts: {"yes": 1.80, "no": 2.00}
        team_profiles: {
            "home": {"clean_sheet_pct": 0.3, "btts_pct": 0.55, "strong_attack": True},
            "away": {"clean_sheet_pct": 0.25, "btts_pct": 0.50, "strong_attack": False}
        }
        h2h_data: [{"home_goals": 2, "away_goals": 1, "btts": True}, ...]
    """
    if market_btts is None:
        market_btts = {}
    if team_profiles is None:
        team_profiles = {}
    
    # ── Poisson-based BTTS probability ──
    # P(BTTS) = 1 - P(home=0) - P(away=0) + P(home=0 AND away=0)
    p_home_0 = poisson_pmf(home_lam, 0)
    p_away_0 = poisson_pmf(away_lam, 0)
    p_both_0 = p_home_0 * p_away_0
    
    p_btts = 1 - p_home_0 - p_away_0 + p_both_0
    p_btts_no = 1 - p_btts
    
    # ── Team profile adjustment ──
    home_profile = team_profiles.get("home", {})
    away_profile = team_profiles.get("away", {})
    
    home_cs_pct = home_profile.get("clean_sheet_pct", 0.30)
    away_cs_pct = away_profile.get("clean_sheet_pct", 0.25)
    home_btts_pct = home_profile.get("btts_pct", 0.50)
    away_btts_pct = away_profile.get("btts_pct", 0.50)
    
    # Combined BTTS tendency
    profile_btts = (home_btts_pct + away_btts_pct) / 2
    
    # Adjust Poisson BTTS with profile
    adjusted_btts = (p_btts * 0.6 + profile_btts * 0.4)
    
    # ── H2H BTTS rate ──
    if h2h_data:
        h2h_btts_count = sum(1 for h in h2h_data if h.get("btts", False))
        h2h_total = len(h2h_data)
        h2h_btts_rate = h2h_btts_count / h2h_total if h2h_total > 0 else 0.5
    else:
        h2h_btts_rate = None
        h2h_total = 0
    
    # Final blended probability
    if h2h_btts_rate is not None and h2h_total >= 2:
        final_btts = adjusted_btts * 0.7 + h2h_btts_rate * 0.3
    else:
        final_btts = adjusted_btts
    
    # ── Market comparison ──
    value_signals = []
    for outcome in ["yes", "no"]:
        if outcome in market_btts:
            ai_prob = final_btts if outcome == "yes" else (1 - final_btts)
            mkt_prob = 1 / market_btts[outcome]
            edge = ai_prob - mkt_prob
            ev = (ai_prob * market_btts[outcome]) - 1
            
            if edge > 0.05:
                signal = "STRONG VALUE"
            elif edge > 0.02:
                signal = "VALUE"
            elif edge < -0.05:
                signal = "OVERPRICED"
            else:
                signal = "FAIR"
            
            value_signals.append({
                "outcome": f"BTTS {outcome.upper()}",
                "ai_prob": round(ai_prob * 100, 1),
                "market_odds": market_btts[outcome],
                "market_prob": round(mkt_prob * 100, 1),
                "edge": round(edge * 100, 2),
                "ev": round(ev * 100, 2),
                "signal": signal,
            })
    
    # ── BTTS classification ──
    if final_btts > 0.60:
        classification = "BTTS YES — High confidence"
        lean = "YES"
    elif final_btts > 0.52:
        classification = "BTTS YES — Moderate lean"
        lean = "YES"
    elif final_btts < 0.40:
        classification = "BTTS NO — High confidence"
        lean = "NO"
    elif final_btts < 0.48:
        classification = "BTTS NO — Moderate lean"
        lean = "NO"
    else:
        classification = "BTTS — Too close to call"
        lean = "NEUTRAL"
    
    # ── Key factors ──
    factors = []
    if home_cs_pct < 0.20:
        factors.append(f"{home_profile.get('name', 'Home')} rarely keeps clean sheets ({home_cs_pct*100:.0f}%)")
    if away_cs_pct < 0.20:
        factors.append(f"{away_profile.get('name', 'Away')} rarely keeps clean sheets ({away_cs_pct*100:.0f}%)")
    if home_btts_pct > 0.60:
        factors.append(f"Home team involved in high BTTS matches ({home_btts_pct*100:.0f}%)")
    if away_btts_pct > 0.60:
        factors.append(f"Away team involved in high BTTS matches ({away_btts_pct*100:.0f}%)")
    if h2h_btts_rate is not None:
        factors.append(f"H2H BTTS rate: {h2h_btts_rate*100:.0f}% ({h2h_btts_count}/{h2h_total})")
    
    return {
        "btts_yes_prob": round(final_btts * 100, 1),
        "btts_no_prob": round((1 - final_btts) * 100, 1),
        "poisson_btts": round(p_btts * 100, 1),
        "profile_btts": round(profile_btts * 100, 1),
        "h2h_btts_rate": round(h2h_btts_rate * 100, 1) if h2h_btts_rate else None,
        "classification": classification,
        "lean": lean,
        "value_signals": value_signals,
        "key_factors": factors,
        "home_clean_sheet_pct": round(home_cs_pct * 100, 1),
        "away_clean_sheet_pct": round(away_cs_pct * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════════
# DISPLAY FORMATTER
# ═══════════════════════════════════════════════════════════════════

def format_deep_analysis(analysis: Dict) -> str:
    """Format comprehensive deep analysis report."""
    lines = []
    lines.append("\n" + "╔" + "═" * 62 + "╗")
    lines.append("║" + f"  🔬 DEEP ANALYSIS: {analysis['match']}".ljust(62) + "║")
    lines.append("╚" + "═" * 62 + "╝")
    
    # Poisson Model
    p = analysis["poisson_model"]
    lines.append(f"\n  📊 POISSON MODEL (Exact Scorelines)")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  1X2: Home {p['home_win_prob']}% | Draw {p['draw_prob']}% | Away {p['away_win_prob']}%")
    lines.append(f"  Totals: O1.5 {p['over_1_5']}% | O2.5 {p['over_2_5']}% | O3.5 {p['over_3_5']}% | O4.5 {p['over_4_5']}%")
    lines.append(f"  BTTS: Yes {p['btts_yes']}% | No {p['btts_no']}%")
    top3 = p['most_likely_scorelines'][:3]
    top3_str = ', '.join(f"{s['score']} ({s['prob']}%)" for s in top3)
    lines.append(f"  Top scorelines: {top3_str}")
    
    # ELO
    e = analysis["elo_prediction"]
    lines.append(f"\n  📈 ELO RATINGS")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  Home: {e['elo_home']} | Away: {e['elo_away']} | Diff: {e['elo_diff']:+}")
    lines.append(f"  Prediction: Home {e['home_win_prob']}% | Draw {e['draw_prob']}% | Away {e['away_win_prob']}%")
    
    # Market Efficiency
    me = analysis["market_efficiency"]
    lines.append(f"\n  💰 MARKET EFFICIENCY")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  {me['market_efficiency']}")
    lines.append(f"  Avg differential: {me['avg_differential']}%")
    for outcome, data in me["outcomes"].items():
        lines.append(f"  {outcome.upper():6s}: AI {data['ai_prob']}% vs Mkt {data['market_prob']}% | "
                     f"Edge {data['differential']:+.2f}% | EV {data['ev']:+.1f}% | {data['signal']}")
    
    # Sentiment
    s = analysis["sentiment_analysis"]
    lines.append(f"\n  🎭 SENTIMENT ANALYSIS")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  Line: {s['line_direction']} ({s['move_pct']:.1f}%) | Steam: {s['steam_category']}")
    lines.append(f"  RLM: {s['rlm_type']}")
    lines.append(f"  Public: {s['public_sentiment']}")
    lines.append(f"  Sharp score: {s['sharp_score']}/100")
    lines.append(f"  → {s['fade_suggestion']}")
    
    # Weather
    w = analysis["weather_impact"]
    lines.append(f"\n  🌤️  WEATHER IMPACT")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  {w['temp_effect']} | {w['wind_effect']}")
    lines.append(f"  Modifier: {w['modifier']:+.2f} goals | {w['total_lean']}")
    for t in w["tactical_implications"][:2]:
        lines.append(f"  • {t}")
    
    # Referee
    r = analysis["referee_analysis"]
    lines.append(f"\n  👨‍⚖️ REFEREE ANALYSIS")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  Cards avg: {r['cards_avg']} | Penalty rate: {r['penalty_rate']}")
    lines.append(f"  {r['card_signal']} | {r['bias_signal']}")
    
    # H2H
    h = analysis["h2h_analysis"]
    lines.append(f"\n  🔄 HEAD-TO-HEAD")
    lines.append(f"  {'─' * 58}")
    if h.get("h2h_available"):
        lines.append(f"  {h['total_matches']} matches: {h.get(analysis['match'].split(' vs ')[0] + '_wins', 0)}-{h['draws']}-{h.get(analysis['match'].split(' vs ')[1] + '_wins', 0)}")
        lines.append(f"  {h['h2h_edge']} (conf: {h['confidence']})")
    else:
        lines.append(f"  {h.get('note', 'No H2H data')}")
    
    # Streak
    st = analysis["streak_analysis"]
    lines.append(f"\n  📉 STREAK ANALYSIS")
    lines.append(f"  {'─' * 58}")
    if "current_streak" in st:
        lines.append(f"  Current: {st['current_streak']} | Longest: W{st['longest_streaks']['W']} D{st['longest_streaks']['D']} L{st['longest_streaks']['L']}")
        lines.append(f"  Win rate: {st['overall_win_rate']}% | Momentum: {st['momentum_score']}")
        lines.append(f"  {st['regression_warning']}")
    
    # Goal Timing
    gt = analysis["goal_timing"]
    lines.append(f"\n  ⏱️  GOAL TIMING")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  1H: {gt['first_half_pct']}% | 2H: {gt['second_half_pct']}%")
    lines.append(f"  Peak: {gt['peak_period']} | {gt['timing_profile']}")
    lines.append(f"  → {gt['live_betting_tip']}")
    
    # Alternative Lines
    al = analysis["alternative_lines"]
    lines.append(f"\n  📐 ALTERNATIVE LINES")
    lines.append(f"  {'─' * 58}")
    if al.get("best_spreads"):
        for s in al["best_spreads"][:3]:
            lines.append(f"  {s['line']:12s}: AI {s['ai_prob']}% | Fair {s['fair_odds']} | {s['value']}")
    if al.get("best_totals"):
        for t in al["best_totals"][:3]:
            lines.append(f"  {t['line']:12s}: AI {t['ai_prob']}% | Fair {t['fair_odds']} | {t['value']}")
    
    # Contrarian
    c = analysis["contrarian_signals"]
    lines.append(f"\n  🔄 CONTRARIAN SIGNALS (Score: {c['contrarian_score']}/100)")
    lines.append(f"  {'─' * 58}")
    lines.append(f"  {c['verdict']}")
    lines.append(f"  → {c['recommended_action']}")
    for sig in c["signals"][:3]:
        lines.append(f"  {sig}")
    
    # Risk-Adjusted
    ra = analysis["risk_adjusted_returns"]
    lines.append(f"\n  📊 RISK-ADJUSTED RETURNS")
    lines.append(f"  {'─' * 58}")
    if "projected" in ra:
        p = ra["projected"]
        lines.append(f"  Expected ROI: {p['expected_roi']}% | Sharpe: {p['portfolio_sharpe']}")
        lines.append(f"  Portfolio risk: {p['portfolio_risk']}% | Total loss prob: {p['total_loss_probability']}%")
    
    lines.append("\n" + "═" * 64)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Match Analyzer v3 — Deep Analysis")
    parser.add_argument("--file", help="JSON file with match data")
    parser.add_argument("--bankroll", type=float, default=1000)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--deep", action="store_true", help="Include all advanced modules")
    parser.add_argument("--examples", action="store_true", help="Print example input format")
    
    args = parser.parse_args()
    
    if args.examples or not args.file:
        print(json.dumps({
            "match": {
                "home_team": "Brazil",
                "away_team": "Morocco",
                "league": "World Cup 2026",
            },
            "context": {
                "home_lambda": 1.8,
                "away_lambda": 0.9,
                "odds_home": 1.45,
                "odds_draw": 4.20,
                "odds_away": 8.00,
                "odds_home_current": 1.45,
                "odds_home_opening": 1.50,
                "public_pct_home": 75,
                "weather": {"temp_c": 28, "humidity": 65, "wind_kmh": 12, "condition": "sunny"},
                "ref_stats": {"matches": 45, "yellow_avg": 3.5, "red_avg": 0.12, "penalty_per_game": 0.10, "home_win_pct": 0.48},
                "recent_results": ["W", "W", "D", "W", "W", "W", "L", "W", "D", "W"],
                "goal_timing": {"first_half_goals_pct": 0.42, "late_goals_tendency": "high", "early_goals_tendency": "medium"},
                "h2h_history": [{"competition": "WC 2022", "home": "Brazil", "away": "Morocco", "home_goals": 2, "away_goals": 1}],
                "odds_by_bookmaker": {
                    "Pinnacle": {"home": 1.45, "draw": 4.20, "away": 8.00},
                    "Bet365": {"home": 1.44, "draw": 4.33, "away": 7.50},
                    "DraftKings": {"home": 1.47, "draw": 4.10, "away": 8.50},
                },
                "stake": 50,
                "bankroll": 1000,
            }
        }, indent=2, ensure_ascii=False))
        if not args.file:
            return
    
    with open(args.file) as f:
        data = json.load(f)
    
    matches = data.get("matches", data if isinstance(data, list) else [data])
    contexts = data.get("contexts", [{} for _ in matches])
    
    for i, match in enumerate(matches):
        ctx = contexts[i] if i < len(contexts) else {}
        result = deep_analysis(match, ctx)
        
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(format_deep_analysis(result))


if __name__ == "__main__":
    main()
