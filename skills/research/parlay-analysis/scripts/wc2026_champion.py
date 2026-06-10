#!/usr/bin/env python3
"""Analisis Peluang Juara Piala Dunia 2026"""
import math

TEAMS = [
    {"name": "Argentina", "fifa_rank": 2, "conf": "CONMEBOL", "last_wc": "Juara", "form": 90, "attack": 92, "defense": 85, "experience": 93},
    {"name": "Prancis", "fifa_rank": 3, "conf": "UEFA", "last_wc": "Runner-up", "form": 91, "attack": 94, "defense": 87, "experience": 94},
    {"name": "Brazil", "fifa_rank": 1, "conf": "CONMEBOL", "last_wc": "Perempat final", "form": 92, "attack": 95, "defense": 88, "experience": 95},
    {"name": "Spanyol", "fifa_rank": 4, "conf": "UEFA", "last_wc": "Perempat final", "form": 89, "attack": 90, "defense": 86, "experience": 88},
    {"name": "Inggris", "fifa_rank": 5, "conf": "UEFA", "last_wc": "Perempat final", "form": 88, "attack": 91, "defense": 85, "experience": 90},
    {"name": "Jerman", "fifa_rank": 6, "conf": "UEFA", "last_wc": "Grup", "form": 85, "attack": 88, "defense": 84, "experience": 95},
    {"name": "Belanda", "fifa_rank": 7, "conf": "UEFA", "last_wc": "Perempat final", "form": 87, "attack": 89, "defense": 86, "experience": 90},
    {"name": "Portugal", "fifa_rank": 8, "conf": "UEFA", "last_wc": "Perempat final", "form": 86, "attack": 90, "defense": 83, "experience": 88},
    {"name": "Maroko", "fifa_rank": 17, "conf": "CAF", "last_wc": "Semi final", "form": 85, "attack": 84, "defense": 86, "experience": 70},
    {"name": "Amerika Serikat", "fifa_rank": 13, "conf": "CONCACAF", "last_wc": "Perempat final", "form": 80, "attack": 82, "defense": 78, "experience": 75, "host": True},
]

def calc(team):
    rank_s = max(0, 100 - (team["fifa_rank"] - 1) * 2.1)
    lw = {"Juara": 100, "Runner-up": 85, "Semi final": 70, "Perempat final": 55, "Grup": 35, "Tidak lolos": 20}
    lw_s = lw.get(team.get("last_wc", "Grup"), 35)
    hb = 10 if team.get("host") else 0
    raw = rank_s*0.20 + team["form"]*0.20 + team["attack"]*0.15 + team["defense"]*0.15 + team["experience"]*0.10 + lw_s*0.10 + hb
    return {**team, "raw": round(raw,1), "rank_s": round(rank_s,1), "lw_s": lw_s, "host_b": hb}

def softmax(d):
    mx = max(t["raw"] for t in d)
    ex = [math.e**(t["raw"]-mx) for t in d]
    s = sum(ex)
    for i,t in enumerate(d):
        t["prob"] = round(ex[i]/s*100, 2)
        t["odds"] = round(100/t["prob"],1) if t["prob"]>0 else 999
    return sorted(d, key=lambda x: x["prob"], reverse=True)

def main():
    print("\n" + "🏆"*25)
    print("  ANALISIS PELUANG JUARA PIALA DUNIA 2026")
    print("🏆"*25)
    data = softmax([calc(t) for t in TEAMS])

    print(f"\n{'═'*60}")
    print("  🏆 TOP 10 FAVORIT JUARA")
    print(f"{'═'*60}")
    print(f"  {'#':<4}{'Tim':<18}{'FIFA':>4}{'Skor':>5}{'Peluang':>8}{'Fair Odds':>10}")
    print(f"  {'─'*50}")
    for i,t in enumerate(data[:10],1):
        h=" 🏠" if t.get("host") else ""
        print(f"  {i:<4}{t['name']:<18}{t['fifa_rank']:>4}{t['raw']:>5.1f}{t['prob']:>7.2f}%{t['odds']:>9.1f}{h}")

    print(f"\n{'═'*60}")
    print("  🌍 PER KONFEDERASI")
    print(f"{'═'*60}")
    confs={}
    for t in data:
        c=t["conf"]
        confs.setdefault(c,{"total":0,"top":"","top_p":0})
        confs[c]["total"]+=t["prob"]
        if t["prob"]>confs[c]["top_p"]:
            confs[c]["top"]=t["name"]; confs[c]["top_p"]=t["prob"]
    nm={"UEFA":"Eropa","CONMEBOL":"Amerika Selatan","CONCACAF":"Amerika Utara","AFC":"Asia","CAF":"Afrika"}
    for c,d in sorted(confs.items(),key=lambda x:x[1]["total"],reverse=True):
        print(f"  {nm.get(c,c):<18}: {d['total']:.1f}% | Favorit: {d['top']} ({d['top_p']:.2f}%)")

    print(f"\n{'═'*60}")
    print("  🔬 DETAIL TOP 5")
    print(f"{'═'*60}")
    medals=["🥇","🥈","🥉","4️⃣","5️⃣"]
    for i,t in enumerate(data[:5]):
        print(f"\n  {medals[i]} {t['name'].upper()} (FIFA #{t['fifa_rank']})")
        print(f"     Peluang: {t['prob']:.2f}% | Fair odds: {t['odds']:.1f} | Skor: {t['raw']:.1f}/100")
        print(f"     Ranking:{t['rank_s']:.0f} | Form:{t['form']:.0f} | Serangan:{t['attack']:.0f} | Pertahanan:{t['defense']:.0f}")
        print(f"     Pengalaman:{t['experience']:.0f} | Pildun 2022: {t['last_wc']} ({t['lw_s']:.0f})", end="")
        if t.get("host"): print(f" | Bonus tuan rumah: +{t['host_b']}")
        else: print()
        s,w=[],[]
        if t["attack"]>=90: s.append("Serangan elit")
        if t["defense"]>=85: s.append("Pertahanan solid")
        if t["form"]>=88: s.append("Form sangat baik")
        if t["last_wc"] in ("Grup","Tidak lolos"): w.append("Pildun 2022 buruk")
        if t["defense"]<80: w.append("Pertahanan kurang")
        if s: print(f"     ✅ {' | '.join(s)}")
        if w: print(f"     ⚠️  {' | '.join(w)}")

    t3=data[:3]
    print(f"\n{'═'*60}")
    print("  📋 KESIMPULAN")
    print(f"{'═'*60}")
    print(f"""
  🥇 FAVORIT: {t3[0]['name']} ({t3[0]['prob']:.2f}%)
     Fair odds: {t3[0]['odds']:.1f}
     Alasan: Juara bertahan, form terbaik, seimbang

  🥈 CHALLENGER: {t3[1]['name']} ({t3[1]['prob']:.2f}%)
     Fair odds: {t3[1]['odds']:.1f}
     Alasan: Kualitas individu tinggi, runner-up 2022

  🥉 OUTSIDER: {t3[2]['name']} ({t3[2]['prob']:.2f}%)
     Fair odds: {t3[2]['odds']:.1f}
     Alasan: Ranking #1, serangan terbaik, tapi 2022 mengecewakan

  💰 REKOMENDASI:
     Safe:   {t3[0]['name']} @ {t3[0]['odds']:.1f}
     Value:  {t3[2]['name']} @ {t3[2]['odds']:.1f}
     Long:   Maroko @ ~50.0 (dark horse)
""")
    print(f"{'═'*60}")
    print("  ⚠️  DISCLAIMER: Data historis + proyeksi. Pildun penuh kejutan!")
    print(f"{'═'*60}")

if __name__=="__main__":
    main()
