#!/usr/bin/env python3
"""
BBRI Alert System
Monitors BBRI price and sends alerts when hitting target levels.
Run via cron or systemd timer.

Alert Levels:
  🟢 BUY:     Rp 2,730 - Rp 2,780 (near 52W low / oversold)
  🎯 TP1:     Rp 2,950 (+7.7%)
  🎯 TP2:     Rp 3,054 (+11.5%, MA20)
  🎯 TP3:     Rp 3,220 (10-day resistance)
  🛑 STOP:    Rp 2,593 (-5.4%, below support)
  ⚠️  BREAKOUT: Rp 3,300 (above resistance)
"""

import json
import urllib.request
import sys
from datetime import datetime

TICKER = "BBRI.JK"
ALERT_FILE = "/home/ubuntu/.hermes/haus-living/bbrr-alerts.json"

# Alert levels
LEVELS = {
    "STOP_LOSS":    {"price": 2593, "type": "stop_loss",   "priority": "CRIT"},
    "STRONG_BUY":   {"price": 2730, "type": "buy_zone",    "priority": "HIGH"},
    "BUY_ZONE_MAX": {"price": 2780, "type": "buy_zone",    "priority": "HIGH"},
    "TP1":          {"price": 2950, "type": "take_profit", "priority": "MED"},
    "TP2":          {"price": 3054, "type": "take_profit", "priority": "MED"},
    "TP3":          {"price": 3220, "type": "take_profit", "priority": "LOW"},
    "BREAKOUT":     {"price": 3300, "type": "breakout",    "priority": "HIGH"},
}


def get_price():
    """Fetch current BBRI price from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}?interval=1d&range=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data["chart"]["result"][0]
            meta = result["meta"]
            return {
                "price": meta.get("regularMarketPrice", 0),
                "prev_close": meta.get("previousClose", 0),
                "52w_high": meta.get("fiftyTwoWeekHigh", 0),
                "52w_low": meta.get("fiftyTwoWeekLow", 0),
                "50d_ma": meta.get("fiftyDayAverage", 0),
                "200d_ma": meta.get("twoHundredDayAverage", 0),
                "volume": meta.get("regularMarketVolume", 0),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S WIB"),
            }
    except Exception as e:
        return {"error": str(e)}


def check_alerts(price_data):
    """Check if price hit any alert levels."""
    if "error" in price_data:
        return [f"❌ Error fetching price: {price_data['error']}"]

    price = price_data["price"]
    alerts = []
    messages = []

    # RSI-based conditions (estimated)
    # RSI < 30 = oversold
    # RSI > 70 = overbought

    # Check each level
    for name, level in LEVELS.items():
        target = level["price"]
        diff_pct = ((price - target) / target) * 100

        # For BUY zones: alert when price drops to or below
        if level["type"] == "buy_zone":
            if price <= target:
                alerts.append(
                    f"🟢 [{level['priority']}] {name}: Rp {price:,} <= Rp {target:,} (BUY ZONE!)"
                )
        # For TP/Stop: alert when price crosses
        elif level["type"] == "take_profit":
            if price >= target:
                alerts.append(
                    f"🎯 [{level['priority']}] {name}: Rp {price:,} >= Rp {target:,} (TAKE PROFIT!)"
                )
        elif level["type"] == "stop_loss":
            if price <= target:
                alerts.append(
                    f"🛑 [{level['priority']}] {name}: Rp {price:,} <= Rp {target:,} (STOP LOSS!)"
                )
        elif level["type"] == "breakout":
            if price >= target:
                alerts.append(
                    f"🚀 [{level['priority']}] {name}: Rp {price:,} >= Rp {target:,} (BREAKOUT!)"
                )

    return alerts


def format_report(price_data, alerts):
    """Format full alert report."""
    if "error" in price_data:
        return f"❌ BBRI Alert Error: {price_data['error']}"

    price = price_data["price"]
    prev = price_data.get("prev_close", 0)
    change = price - prev
    change_pct = ((price - prev) * 100 / prev) if prev else 0
    vol = price_data.get("volume", 0) or 0

    # 52W position
    low_52w = price_data.get("52w_low", 0) or 0
    high_52w = price_data.get("52w_high", 0) or 0
    range_52 = high_52w - low_52w
    pos = ((price - low_52w) / range_52 * 100) if range_52 else 0

    icon = "🔴" if change < 0 else "🟢" if change > 0 else "⚪"

    report = f"""
📊 BBRI — Price Alert Report
{'='*40}
💰 Price:    Rp {price:,}
{icon} Change:   {change:+,.0f} ({change_pct:+.2f}%)
📈 Volume:   {vol/1e6:.1f}M shares
📅 Time:     {price_data.get('timestamp', 'N/A')}

── 52W POSITION ──
📉 Low:  Rp {low_52w:,}
📍 Now:  Rp {price:,} ({pos:.1f}% dari range)
📈 High: Rp {high_52w:,}

── ALERT LEVELS ──
🛑 STOP:       Rp 2,593  |  Gap: {((2593-price)/price*100):+.1f}%
🟢 BUY ZONE:   Rp 2,730 - Rp 2,780
🎯 TP1:        Rp 2,950  |  Gap: {((2950-price)/price*100):+.1f}%
🎯 TP2:        Rp 3,054  |  Gap: {((3054-price)/price*100):+.1f}%
🎯 TP3:        Rp 3,220  |  Gap: {((3220-price)/price*100):+.1f}%
🚀 BREAKOUT:   Rp 3,300  |  Gap: {((3300-price)/price*100):+.1f}%
"""

    if alerts:
        report += "\n🚨 ACTIVE ALERTS:\n"
        for a in alerts:
            report += f"  {a}\n"
    else:
        report += "\n✅ No alerts triggered. Price in neutral zone.\n"

    report += f"\n{'='*40}\n⚠️  NOT FINANCIAL ADVICE — DYOR!\n"
    return report


def main():
    """Main function."""
    price_data = get_price()
    alerts = check_alerts(price_data)
    report = format_report(price_data, alerts)
    print(report)

    # Save state
    state = {
        "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price": price_data.get("price"),
        "alerts": alerts,
    }
    try:
        with open(ALERT_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except:
        pass

    # Return exit code for cron (1 = alerts triggered)
    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
