#!/usr/bin/env python3
"""
Deep Parlay Analyzer — combined A-G + H-X pipeline.
Merges parlay-analysis v2 and v3 into readable dashboard + deep report.
Usage:
  python3 deep_parlay_analyzer.py --file matches.json --bankroll 1000
  python3 deep_parlay_analyzer.py --file matches.json --bankroll 1000 --json
"""
from __future__ import annotations
import argparse, importlib.util, json, math
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PARLAY_SCRIPTS = SKILL_DIR.parent / "parlay-analysis" / "scripts"

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

v2 = load_module("parlay_v2", PARLAY_SCRIPTS / "match_analyzer_v2.py")
v3 = load_module("parlay_v3", PARLAY_SCRIPTS / "match_analyzer_v3.py")

def american_to_decimal(am):
    return (am/100.0)+1.0 if am > 0 else 100.0/abs(am)+1.0

def decimal_to_american(dec):
    return int(round((dec-1.0)*100)) if dec >= 2 else int(round(-100.0/(dec-1.0)))

def fmt_pct(x):
    return f"{x:.1f}%"

def fmt_ev(x):
    return f"{x:+.1f}%"

def fmt_odds(x):
    return f"{x:.2f}"

def normalize_match(m):
    m = dict(m)
    if "home_team" not in m:
        m["home_team"] = m.get("home") or m.get("home_name") or "Unknown Home"
    if "away_team" not in m:
        m["away_team"] = m.get("away") or m.get("away_name") or "Unknown Away"
    if "league" not in m:
        group = m.get("group")
        m["league"] = f"World Cup 2026 Group {group}" if group else m.get("competition") or m.get("league") or "Unknown"
    if "kickoff" not in m:
        if m.get("date") and m.get("time"):
            m["kickoff"] = f"{m['date']} {m['time']}"
        else:
            m["kickoff"] = m.get("kickoff") or "TBD"
    if "current_odds" not in m and "odds_home" in m:
        m["current_odds"] = decimal_to_american(float(m["odds_home"]))
    if "opening_odds" not in m:
        m["opening_odds"] = m.get("current_odds", -110)
    if "public_pct_home" not in m:
        m["public_pct_home"] = 50
    return m

def get_odds(m, ctx):
    books = ctx.get("odds_by_bookmaker") or {}
    pin = books.get("Pinnacle") or books.get("pinnacle") or {}
    return {
        "home": float(m.get("odds_home") or ctx.get("odds_home") or pin.get("home") or 1.85),
        "draw": float(m.get("odds_draw") or ctx.get("odds_draw") or pin.get("draw") or 3.40),
        "away": float(m.get("odds_away") or ctx.get("odds_away") or pin.get("away") or 4.50),
    }

def rank_to_elo(rank):
    try: r = int(rank)
    except: return 1500.0
    return 1500.0 + max(0, 22-r)*20.0

def derive_elo(m, ctx):
    ratings = dict(ctx.get("elo_ratings") or {})
    for key, team_key in [("home_fifa_rank","home_team"),("away_fifa_rank","away_team")]:
        if m.get(team_key) and m[team_key] not in ratings and key in m:
            ratings[m[team_key]] = rank_to_elo(m[key])
    return ratings

def build_context(m, ctx, v2a):
    ctx = dict(ctx or {})
    mc = v2a["monte_carlo"]
    odds = get_odds(m, ctx)
    ctx.setdefault("home_lambda", mc["home_lambda"])
    ctx.setdefault("away_lambda", mc["away_lambda"])
    ctx.setdefault("odds_home", odds["home"])
    ctx.setdefault("odds_draw", odds["draw"])
    ctx.setdefault("odds_away", odds["away"])
    ctx.setdefault("odds_home_current", odds["home"])
    ctx.setdefault("odds_home_opening", odds["home"])
    ctx.setdefault("public_pct_home", m.get("public_pct_home", 50))
    ctx.setdefault("weather", {"temp_c":20,"humidity":50,"wind_kmh":10,"condition":"normal"})
    ctx.setdefault("ref_stats", {"matches":30,"yellow_avg":3.8,"red_avg":0.10,"penalty_per_game":0.12,"home_win_pct":0.48})
    ctx.setdefault("h2h_history", [])
    ctx.setdefault("recent_results", ["W","D","L","W","D","L","W","D","W","L"])
    ctx.setdefault("goal_timing", {"first_half_goals_pct":0.45,"late_goals_tendency":"medium","early_goals_tendency":"medium"})
    ctx.setdefault("stake", 50)
    ctx.setdefault("bankroll", 1000)
    ctx.setdefault("elo_ratings", derive_elo(m, ctx))
    return ctx

def recompute_alt_lines(p, odds):
    matrix = [[x/100.0 for x in row] for row in p["matrix"]]
    alt = {}
    home_win = draw = away_win = 0.0
    total_le_1 = total_le_2 = total_le_3 = 0.0
    for hg, row in enumerate(matrix):
        for ag, prob in enumerate(row):
            total = hg+ag
            if hg > ag: home_win += prob
            elif hg == ag: draw += prob
            else: away_win += prob
            if total <= 1: total_le_1 += prob
            if total <= 2: total_le_2 += prob
            if total <= 3: total_le_3 += prob
    alt.update({
        "home_0_5": home_win, "away_0_5": away_win,
        "home_1_5": sum(prob for hg,row in enumerate(matrix) for ag,prob in enumerate(row) if hg-ag >= 2),
        "home_2_5": sum(prob for hg,row in enumerate(matrix) for ag,prob in enumerate(row) if hg-ag >= 3),
        "over_2_5": p["over_2_5"]/100.0, "under_2_5": 1.0-p["over_2_5"]/100.0,
        "over_3_5": p["over_3_5"]/100.0, "under_3_5": 1.0-p["over_3_5"]/100.0,
    })
    return v3.alternative_lines(alt, odds)

def market_scan(v2a, v3a, odds, ctx):
    p = v3a["poisson_model"]
    probs = {"Home":p["home_win_prob"]/100.0,"Draw":p["draw_prob"]/100.0,"Away":p["away_win_prob"]/100.0}
    decs = {"Home":odds["home"],"Draw":odds["draw"],"Away":odds["away"]}
    rows = []
    for name, prob in probs.items():
        dec = decs[name]
        rows.append({"market":name,"prob":prob,"odds":dec,
                      "fair_odds":1.0/prob if prob>0 else None,
                      "edge":prob-1.0/dec,"ev":prob*dec-1.0})
    rows.sort(key=lambda x: x["ev"], reverse=True)

    totals = []
    mkt_totals = ctx.get("market_totals") or {}
    for line, prob in [("O2.5",p["over_2_5"]/100.0),("U2.5",1.0-p["over_2_5"]/100.0),
                       ("O3.5",p["over_3_5"]/100.0),("U3.5",1.0-p["over_3_5"]/100.0)]:
        item = {"market":line,"prob":prob,"fair_odds":1.0/prob if prob>0 else None}
        if line in mkt_totals:
            dec = float(mkt_totals[line])
            item.update({"odds":dec,"edge":prob-1.0/dec,"ev":prob*dec-1.0})
        totals.append(item)

    btts = []
    mkt_btts = ctx.get("market_btts") or {}
    for outcome, prob in [("BTTS Yes",p["btts_yes"]/100.0),("BTTS No",1.0-p["btts_yes"]/100.0)]:
        item = {"market":outcome,"prob":prob,"fair_odds":1.0/prob if prob>0 else None}
        key = "yes" if "Yes" in outcome else "no"
        if key in mkt_btts:
            dec = float(mkt_btts[key])
            item.update({"odds":dec,"edge":prob-1.0/dec,"ev":prob*dec-1.0})
        btts.append(item)

    candidates = [r for r in rows if r["ev"] >= 0.02 and r["prob"] >= 0.15]
    if all(r["ev"] < 0 for r in rows):
        verdict = "SKIP"
    elif candidates and max(c["ev"] for c in candidates) >= 0.05:
        verdict = "BET"
    elif candidates:
        verdict = "SMALL"
    else:
        verdict = "SKIP"

    return {"outcomes":rows,"totals":totals,"btts":btts,
            "best_1x2":rows[0],"positive_candidates":candidates,"verdict":verdict}

def pick_confidence_bucket(conf):
    if conf >= 70: return "STRONG"
    if conf >= 55: return "MODERATE"
    if conf >= 40: return "RISKY"
    return "LONGSHOT"

def format_dashboard(item):
    m = item["match"]; v2a = item["v2"]; v3a = item["v3"]
    scan = item["market_scan"]; p = v3a["poisson_model"]
    odds = item["odds"]; best = scan["best_1x2"]
    v = scan["verdict"]; tier = pick_confidence_bucket(v2a["confidence"])
    lines = [
        f"🏟️  {v2a['match']}",
        f"    Kickoff: {v2a['kickoff']}",
        f"    ─────────────────────────────────────",
        f"    Verdict: {v}  |  Tier: {tier}",
        f"    Model pick: {v2a['prediction']}",
        f"    Confidence: {v2a['confidence']:.0f}/100  |  Risk: {v2a['risk_level']}",
        f"    ─────────────────────────────────────",
        f"    Market odds:  Home {odds['home']:.2f}  Draw {odds['draw']:.2f}  Away {odds['away']:.2f}",
        f"    Fair odds:    Home {best['fair_odds']:.2f}  Draw {fmt_odds(100/p['draw_prob']) if p['draw_prob']>0 else 'N/A'}  Away {fmt_odds(100/p['away_win_prob']) if p['away_win_prob']>0 else 'N/A'}",
        f"    ─────────────────────────────────────",
        f"    Win prob:  Home {fmt_pct(p['home_win_prob'])}  Draw {fmt_pct(p['draw_prob'])}  Away {fmt_pct(p['away_win_prob'])}",
        f"    Totals:    O2.5 {fmt_pct(p['over_2_5'])}  U2.5 {fmt_pct(100-p['over_2_5'])}",
        f"    BTTS:      Yes {fmt_pct(p['btts_yes'])}  No {fmt_pct(p['btts_no'])}",
        f"    Scorelines: " + ", ".join(f"{s['score']} ({fmt_pct(s['prob'])})" for s in p['most_likely_scorelines'][:3]),
        f"    ─────────────────────────────────────",
        f"    Best 1X2 EV: {best['market']} @ {best['odds']:.2f} -> EV {fmt_ev(best['ev']*100)}",
    ]
    if scan["positive_candidates"]:
        for c in scan["positive_candidates"]:
            lines.append(f"    ✅ {c['market']} @ {c['odds']:.2f}  EV {fmt_ev(c['ev']*100)}")
    else:
        lines.append(f"    ❌ No positive-EV singles")
    lines.append(f"    Parlay: {'SKIP' if not item.get('portfolio',{}).get('allocations') else 'CHECK BELOW'}")
    return "\n".join(lines)

def format_deep(item):
    v2a = item["v2"]; v3a = item["v3"]; scan = item["market_scan"]
    lines = [f"\n  🔬 {v2a['match']} — Deep Modules"]
    lines.append(f"    A. Stats:       Form H{v2a['statistics']['form']['last10_home']:.0f} A{v2a['statistics']['form']['last10_away']:.0f} | xG H{v2a['statistics']['deep_stats']['home']['xg']} A{v2a['statistics']['deep_stats']['away']['xg']} | Edge {v2a['statistics']['deep_stats']['statistical_advantage']}")
    lines.append(f"    B. Market:      Implied {v2a['market']['implied_prob']}% | Signal {v2a['market']['market_signal']} | RLM {v2a['market']['rlm_signal']}")
    lines.append(f"    C. Tactical:    {v2a['tactical']['style_matchup']} | Mid {v2a['tactical']['midfield_control']} | Press {v2a['tactical']['pressing_intensity']} | Edge {v2a['tactical']['tactical_edge']}")
    lines.append(f"    D. Motivation:  Score {v2a['motivation']['motivation_score']:.0f} | Edge {v2a['motivation']['motivation_edge']}")
    mc = v2a['monte_carlo']
    lines.append(f"    E. Monte Carlo: H{mc['home_win_prob']}% D{mc['draw_prob']}% A{mc['away_win_prob']}% | O2.5 {mc['over_2_5_prob']}% | BTTS {mc['btts_prob']}%")
    lines.append(f"    F. Value:       ML EV {v2a['value_bet']['ev_score']:+.1f}% | Status {v2a['value_bet']['value_status']}")
    lines.append(f"    G. Correlation: parlay rec computed below")
    lines.append(f"    ─────────────────────────────────────")
    lines.append(f"    H. Poisson:     exact scores computed")
    ep = v3a['elo_prediction']
    lines.append(f"    I. ELO:         {ep['elo_home']:.0f} vs {ep['elo_away']:.0f} (diff {ep['elo_diff']:+.0f}) | H{ep['home_win_prob']}% D{ep['draw_prob']}% A{ep['away_win_prob']}%")
    me = v3a['market_efficiency']
    lines.append(f"    J. Eff/Mkt:     {me['market_efficiency']}")
    for k2,v2 in me['outcomes'].items():
        lines.append(f"       {k2}: AI {v2['ai_prob']}% Mkt {v2['market_prob']}% Edge {v2['differential']:+.1f}% EV {v2['ev']:+.1f}% {v2['signal']}")
    lines.append(f"    K. Sentiment:   {v3a['sentiment_analysis']['public_sentiment']} | Sharp {v3a['sentiment_analysis']['sharp_score']}/100 | {v3a['sentiment_analysis']['fade_suggestion']}")
    lines.append(f"    L. Weather:     {v3a['weather_impact']['total_lean']} | mod {v3a['weather_impact']['modifier']:+.2f} goals")
    lines.append(f"    M. Referee:     Cards {v3a['referee_analysis']['cards_avg']} | Pen {v3a['referee_analysis']['penalty_rate']} | {v3a['referee_analysis']['card_signal']}")
    h2h = v3a['h2h_analysis']
    lines.append(f"    N/O. H2H:       {h2h.get('note','n/a')}")
    if 'current_streak' in v3a['streak_analysis']:
        sa = v3a['streak_analysis']
        lines.append(f"    S. Streak:      {sa['current_streak']} | WR {sa['overall_win_rate']}% | Mom {sa['momentum_score']}")
    gt = v3a['goal_timing']
    lines.append(f"    T. Timing:      1H {gt['first_half_pct']}% 2H {gt['second_half_pct']}% | {gt['timing_profile']}")
    alt = v3a['alternative_lines']
    if alt.get('best_totals'):
        lines.append(f"    U. Alt totals:  " + " | ".join(f"{x['line']} {fmt_pct(x['ai_prob'])} fair {x['fair_odds']:.2f}" for x in alt['best_totals'][:3]))
    cs = v3a['contrarian_signals']
    lines.append(f"    V. Contrarian:  Score {cs['contrarian_score']}/100 | {cs['verdict']}")
    if 'projected' in v3a['risk_adjusted_returns']:
        ra = v3a['risk_adjusted_returns']['projected']
        lines.append(f"    Q. Risk/ROI:    {ra['expected_roi']:+.1f}% | Sharpe {ra['portfolio_sharpe']} | Loss prob {ra['total_loss_probability']:.1f}%")
    return "\n".join(lines)

def analyze(data, bankroll):
    raw_matches = data.get("matches", data if isinstance(data, list) else [data])
    contexts = data.get("contexts", [{} for _ in raw_matches]) if isinstance(data, dict) else [{}]*len(raw_matches)
    items = []
    for i, raw in enumerate(raw_matches):
        m = normalize_match(raw)
        ctx = contexts[i] if i < len(contexts) else {}
        v2a = v2.full_analysis(m)
        ctx = build_context(m, ctx, v2a)
        v3a = v3.deep_analysis(m, ctx)
        odds = get_odds(m, ctx)
        v3a["alternative_lines"] = recompute_alt_lines(v3a["poisson_model"], odds)
        scan = market_scan(v2a, v3a, odds, ctx)
        candidates = [{"match":v2a["match"],"market":r["market"],"prob":r["prob"],"odds":r["odds"],"ev":r["ev"],"correlation_group":v2a["match"]} for r in scan["positive_candidates"]]
        portfolio = v3.portfolio_optimizer(candidates, bankroll=bankroll) if candidates else {"num_bets":0,"total_stake":0,"allocations":[]}
        items.append({"match":m,"context":ctx,"odds":odds,"v2":v2a,"v3":v3a,"market_scan":scan,"portfolio":portfolio})
    v2_for_parlays = []
    for it in items:
        v2_for_parlays.append(it["v2"])
    parlays = v2.build_parlays(v2_for_parlays, bankroll=bankroll, kelly_mult=0.25)
    return {"items":items,"recommendations":parlays}

def main():
    parser = argparse.ArgumentParser(description="Deep Parlay Analyzer — combined A-G + H-X")
    parser.add_argument("--file", required=True)
    parser.add_argument("--bankroll", type=float, default=1000.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = json.loads(Path(args.file).read_text())
    result = analyze(data, args.bankroll)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("📊 DEEP PARLAY ANALYZER — DASHBOARD")
    print("=" * 60)
    for item in result["items"]:
        print("\n" + format_dashboard(item))
    print("\n" + "=" * 60)
    print("🔬 DEEP MODULE BREAKDOWN (H-X)")
    for item in result["items"]:
        print(format_deep(item))
    print("\n" + "=" * 60)
    print("🎰 PARLAY & PORTFOLIO SUMMARY")
    rec = result["recommendations"]
    if rec:
        fj = rec.get("final_judgment", {})
        print(f"  Bankroll: ${rec.get('bankroll',0):.0f}")
        print(f"  Viable picks: {rec.get('viable_picks',0)}/{rec.get('total_matches',0)}")
        print(f"  Overall confidence: {fj.get('overall_confidence',0):.0f}/100")
        print(f"  Best pick: {fj.get('best_pick','N/A')} (conf {fj.get('best_pick_confidence',0):.0f})")
        print(f"  Best value: {fj.get('best_value_bet','N/A')} (EV {fj.get('best_value_ev',0):+.1f}%)")
        print(f"  Avoid: {fj.get('pick_to_avoid','N/A')}")
        print(f"  Risks: {'; '.join(fj.get('main_risks',['None']))}")
        for key in ["safe","medium","aggressive"]:
            p = rec.get("recommendations",{}).get(key)
            if p:
                print(f"\n  {key.upper()} PARLAY ({len(p['legs'])} legs)")
                for leg in p["legs"]:
                    print(f"    {leg['match']} -> {leg['prediction']} @ {leg['odds']:+.0f} (conf {leg['confidence']:.0f}, EV {leg['ev']:+.1f}%)")
                print(f"    Total odds: {p['total_odds_american']:+.0f} (dec {p['total_odds_decimal']})")
                print(f"    Stake: ${p['recommended_stake']:.2f} -> Payout: ${p['potential_payout']:.2f}")
                print(f"    EV: {p['ev_pct']:+.1f}% | Corr risk: {p['correlation']['correlation_risk']}")

    print("\n" + "=" * 60)
    print("✅ Modules loaded: A-G (v2) + H-X (v3)")
    print("⚠️  If odds are estimates, recalculate with live book odds")

if __name__ == "__main__":
    main()
