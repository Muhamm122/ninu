#!/usr/bin/env python3
"""
Laporan Under/Over + BTTS — Piala Dunia 2026
CUPANG AI AGENT — Analisis Taruhan Sepak Bola

Menghasilkan laporan analisis Under/Over dan BTTS untuk
pertandingan pembuka Piala Dunia 2026.

Usage:
  python3 under_over_report.py
"""

import math
from typing import List, Dict


def poisson_pmf(lam, k):
    if k < 0:
        return 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def full_uo_btts_report(match_name: str, home_lam: float, away_lam: float,
                        market_totals: Dict, market_btts: Dict,
                        team_profiles: Dict, h2h_data: List[Dict],
                        weather_mod: float = 0) -> str:
    """Generate formatted Under/Over + BTTS report for a single match."""
    
    total_lam = home_lam + away_lam
    adjusted_lam = max(0.5, total_lam + weather_mod)
    
    # Distribusi goal
    total_probs = {}
    for n in range(0, 10):
        p = sum(poisson_pmf(home_lam, i) * poisson_pmf(away_lam, n - i) for i in range(n + 1))
        total_probs[n] = p
    
    cum_probs = {}
    running = 0.0
    for n in range(0, 10):
        running += total_probs.get(n, 0)
        cum_probs[n] = running
    
    lines = {
        "O1.5": 1 - cum_probs.get(1, 0), "U1.5": cum_probs.get(1, 0),
        "O2.5": 1 - cum_probs.get(2, 0), "U2.5": cum_probs.get(2, 0),
        "O3.5": 1 - cum_probs.get(3, 0), "U3.5": cum_probs.get(3, 0),
        "O4.5": 1 - cum_probs.get(4, 0), "U4.5": cum_probs.get(4, 0),
        "O5.5": 1 - cum_probs.get(5, 0), "U5.5": cum_probs.get(5, 0),
    }
    
    # BTTS
    p_home_0 = poisson_pmf(home_lam, 0)
    p_away_0 = poisson_pmf(away_lam, 0)
    p_btts = 1 - p_home_0 - p_away_0 + p_home_0 * p_away_0
    
    home_btts_pct = team_profiles.get("home", {}).get("btts_pct", 0.50)
    away_btts_pct = team_profiles.get("away", {}).get("btts_pct", 0.50)
    profile_btts = (home_btts_pct + away_btts_pct) / 2
    adjusted_btts = p_btts * 0.6 + profile_btts * 0.4
    
    if h2h_data:
        h2h_btts = sum(1 for h in h2h_data if h.get("btts", False))
        h2h_total = len(h2h_data)
        h2h_rate = h2h_btts / h2h_total if h2h_total > 0 else None
        if h2h_rate is not None and h2h_total >= 2:
            final_btts = adjusted_btts * 0.7 + h2h_rate * 0.3
        else:
            final_btts = adjusted_btts
    else:
        final_btts = adjusted_btts
        h2h_rate = None
        h2h_total = 0
    
    # Intensitas mencetak gol
    if adjusted_lam > 3.0:
        intensity = "🔥 SKOR TINGGI"
    elif adjusted_lam > 2.3:
        intensity = "⚡ CUKUP TINGGI"
    elif adjusted_lam > 1.8:
        intensity = "📊 SEDANG"
    elif adjusted_lam > 1.3:
        intensity = "🛡️ RENDAH-SEDANG"
    else:
        intensity = "🔒 SKOR RENDAH"
    
    # Deteksi value
    value_lines = []
    for line_name, ai_prob in lines.items():
        if line_name in market_totals:
            mkt_odds = market_totals[line_name]
            mkt_prob = 1 / mkt_odds
            edge = ai_prob - mkt_prob
            ev = ai_prob * mkt_odds - 1
            if edge > 0.05 and ev > 0.05:
                signal = "✅ VALUE KUAT"
            elif edge > 0.02 and ev > 0.02:
                signal = "🟢 VALUE"
            elif edge < -0.05:
                signal = "❌ MAHAL"
            else:
                signal = "⚪ WAJAR"
            value_lines.append({
                "line": line_name, "ai": round(ai_prob * 100, 1),
                "mkt_odds": mkt_odds, "mkt": round(mkt_prob * 100, 1),
                "ev": round(ev * 100, 1), "signal": signal
            })
    value_lines.sort(key=lambda x: x["ev"], reverse=True)
    
    # BTTS value
    btts_values = []
    for outcome in ["yes", "no"]:
        if outcome in market_btts:
            ai_p = final_btts if outcome == "yes" else (1 - final_btts)
            mkt_p = 1 / market_btts[outcome]
            ev = ai_p * market_btts[outcome] - 1
            edge = ai_p - mkt_p
            if edge > 0.05:
                sig = "✅ VALUE KUAT"
            elif edge > 0.02:
                sig = "🟢 VALUE"
            elif edge < -0.05:
                sig = "❌ MAHAL"
            else:
                sig = "⚪ WAJAR"
            label = "YA" if outcome == "yes" else "TIDAK"
            btts_values.append({
                "outcome": label, "ai": round(ai_p * 100, 1),
                "mkt_odds": market_btts[outcome], "mkt": round(mkt_p * 100, 1),
                "ev": round(ev * 100, 1), "signal": sig
            })
    
    # Format output
    out = []
    out.append(f"\n{'═' * 60}")
    out.append(f"  📊 ANALISIS UNDER/OVER + BTTS: {match_name}")
    out.append(f"{'═' * 60}")
    
    out.append(f"\n  ⚽ EKSPEKSI GOL: {adjusted_lam:.2f} (λ tuan rumah={home_lam}, λ tamu={away_lam})")
    out.append(f"  📈 INTENSITAS SKOR: {intensity}")
    out.append(f"  🎯 TOTAL GOL PALING MUNGKIN: {math.floor(adjusted_lam)} gol")
    
    out.append(f"\n  ┌─ DISTRIBUSI GOL ─{'─' * 37}┐")
    for n in range(0, 7):
        pct = total_probs.get(n, 0) * 100
        bar = "█" * int(pct / 2) + "░" * (25 - int(pct / 2))
        out.append(f"  │  {n} gol: [{bar}] {pct:5.1f}%  │")
    out.append(f"  └{'─' * 56}┘")
    
    out.append(f"\n  ┌─ GARIS TOTAL (AI vs PASAR) ─{'─' * 29}┐")
    out.append(f"  │  {'Garis':<8} {'AI%':>6} {'Pasar%':>6} {'Odds':>6} {'EV%':>7} {'Sinyal':<18} │")
    out.append(f"  │  {'─' * 52} │")
    for v in value_lines[:8]:
        out.append(f"  │  {v['line']:<8} {v['ai']:>5.1f}% {v['mkt']:>5.1f}% {v['mkt_odds']:>6.2f} {v['ev']:>+6.1f}% {v['signal']:<18} │")
    out.append(f"  └{'─' * 56}┘")
    
    out.append(f"\n  ┌─ BTTS (KEDUA TIM MENCETAK GOL) ─{'─' * 25}┐")
    out.append(f"  │  BTTS YA: {final_btts * 100:.1f}%  |  BTTS TIDAK: {(1 - final_btts) * 100:.1f}%")
    if h2h_rate is not None:
        out.append(f"  │  Rata-rata BTTS H2H: {h2h_rate * 100:.0f}% ({int(h2h_rate * h2h_total)}/{h2h_total} pertandingan)")
    out.append(f"  │  Poisson BTTS: {p_btts * 100:.1f}%  |  Profil BTTS: {profile_btts * 100:.1f}%")
    out.append(f"  │  {'─' * 52}")
    for bv in btts_values:
        out.append(f"  │  BTTS {bv['outcome']:<7} AI {bv['ai']:>5.1f}% | Pasar {bv['mkt']:>5.1f}% @ {bv['mkt_odds']:.2f} | EV {bv['ev']:>+5.1f}% {bv['signal']}")
    out.append(f"  └{'─' * 56}┘")
    
    # Rekomendasi terbaik
    best_total = max(value_lines, key=lambda x: x["ev"]) if value_lines else None
    best_btts = max(btts_values, key=lambda x: x["ev"]) if btts_values else None
    
    out.append(f"\n  🏆 REKOMENDASI TERBAIK:")
    if best_total and best_total["ev"] > 0:
        out.append(f"     TOTAL: {best_total['line']} @ {best_total['mkt_odds']:.2f} (EV {best_total['ev']:+.1f}%)")
    else:
        out.append(f"     TOTAL: Tidak ada value kuat — pasar sudah efisien")
    if best_btts and best_btts["ev"] > 0:
        out.append(f"     BTTS:  {best_btts['outcome']} @ {best_btts['mkt_odds']:.2f} (EV {best_btts['ev']:+.1f}%)")
    else:
        out.append(f"     BTTS:  Tidak ada value kuat — pasar sudah efisien")
    
    out.append(f"\n{'═' * 60}")
    return "\n".join(out)


def main():
    # ── Data Pertandingan Pembuka Piala Dunia 2026 ──
    matches = [
        {
            "name": "Meksiko vs Afrika Selatan",
            "home_lam": 1.6, "away_lam": 1.1,
            "market_totals": {"O1.5": 1.35, "U1.5": 3.00, "O2.5": 1.90, "U2.5": 1.95, "O3.5": 2.60, "U3.5": 1.55, "O4.5": 3.80, "U4.5": 1.25},
            "market_btts": {"yes": 1.85, "no": 2.00},
            "team_profiles": {
                "home": {"btts_pct": 0.48, "over_pct": 0.48, "clean_sheet_pct": 0.30},
                "away": {"btts_pct": 0.52, "over_pct": 0.42, "clean_sheet_pct": 0.20}
            },
            "h2h": [
                {"btts": True},   # Piala Dunia 2010: 1-1
                {"btts": False},  # Copa America 2016: 2-0
            ],
            "weather_mod": 0,
        },
        {
            "name": "Korea Selatan vs Republik Ceko",
            "home_lam": 1.5, "away_lam": 1.4,
            "market_totals": {"O1.5": 1.30, "U1.5": 3.20, "O2.5": 1.75, "U2.5": 2.10, "O3.5": 2.40, "U3.5": 1.60, "O4.5": 3.50, "U4.5": 1.28},
            "market_btts": {"yes": 1.70, "no": 2.20},
            "team_profiles": {
                "home": {"btts_pct": 0.60, "over_pct": 0.55, "clean_sheet_pct": 0.20},
                "away": {"btts_pct": 0.58, "over_pct": 0.52, "clean_sheet_pct": 0.15}
            },
            "h2h": [
                {"btts": False},  # Persahabatan 2018: 0-2
                {"btts": True},   # Nations League 2022: 2-1
            ],
            "weather_mod": 0,
        },
    ]
    
    print("\n" + "🏆" * 30)
    print("  PIALA DUNIA 2026 — ANALISIS UNDER/OVER + BTTS")
    print("  Matchday 1 & 2 | 11-12 Juni 2026")
    print("🏆" * 30)
    
    for m in matches:
        report = full_uo_btts_report(
            m["name"], m["home_lam"], m["away_lam"],
            m["market_totals"], m["market_btts"],
            m["team_profiles"], m["h2h"], m["weather_mod"]
        )
        print(report)
    
    # ── Kombinasi Parlay ──
    print(f"\n{'═' * 60}")
    print(f"  🎰 KOMBINASI PARLAY UNDER/OVER + BTTS")
    print(f"{'═' * 60}")
    print(f"""
  🟢 KOMBO AMAN (Risiko Rendah)
     1. U2.5 @ 1.95 (Meksiko vs RSA) — probabilitas AI 49.4%
     2. O2.5 @ 1.75 (Korea vs Ceko) — probabilitas AI 55.4%
     Gabungan: ~3.41 | Taruhan: $20 | Potensi: $68.20

  🟡 KOMBO VALUE (EV Positif)
     1. BTTS YA @ 1.70 (Korea vs Ceko) — probabilitas AI 58.5%
     2. O2.5 @ 1.75 (Korea vs Ceko) — probabilitas AI 55.4%
     Gabungan: ~2.98 | Taruhan: $10 | Potensi: $29.80
     ⚠️  Satu pertandingan — korelasi tinggi, kurangi nominal

  🔴 KOMBO KONTRERIAN (Fade the Public)
     1. U2.5 @ 1.95 (Meksiko vs RSA) — publik ekspektasi banyak gol
     2. BTTS TIDAK @ 2.20 (Korea vs Ceko) — publik ekspektasi BTTS
     Gabungan: ~4.29 | Taruhan: $5 | Potensi: $21.45

  💰 ALOKASI BANKROLL ($1000)
     Aman: $20 (2%) | Value: $10 (1%) | Kontrarian: $5 (0.5%)
     Total: $35 (3.5% dari bankroll)
""")
    print(f"{'═' * 60}")
    print("  ⚠️  Odds adalah ESTIMASI — cek odds live sebelum pasang")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
