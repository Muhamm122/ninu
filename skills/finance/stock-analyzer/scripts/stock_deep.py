"""
IDX Stock Deep Analysis v4 — Enhanced with Yahoo Finance browser data
Includes: S/R multi-method, holders, analyst consensus, earnings estimates, financials
Usage: python3 stock_deep.py TICKER.JK [--period 6mo] [--source yf|browser|both]
"""
import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def find_swing_points(series, window=5):
    swing_highs, swing_lows = [], []
    for i in range(window, len(series) - window):
        if series.iloc[i] == series.iloc[i-window:i+window+1].max():
            swing_highs.append((series.index[i], series.iloc[i]))
        if series.iloc[i] == series.iloc[i-window:i+window+1].min():
            swing_lows.append((series.index[i], series.iloc[i]))
    return swing_highs, swing_lows

def compute_fibonacci(high, low):
    rng = high - low
    return {
        '0%': high, '23.6%': high - rng*0.236, '38.2%': high - rng*0.382,
        '50.0%': high - rng*0.500, '61.8%': high - rng*0.618, '78.6%': high - rng*0.786, '100%': low,
    }

def compute_volume_profile(df, bins=20):
    pmin, pmax = df['Close'].min(), df['Close'].max()
    edges = np.linspace(pmin, pmax, bins + 1)
    vol = np.zeros(bins)
    for _, row in df.iterrows():
        idx = min(int((row['Close'] - pmin) / (pmax - pmin) * bins), bins - 1)
        vol[idx] += row['Volume']
    centers = (edges[:-1] + edges[1:]) / 2
    si = np.argsort(vol)
    return {
        'poc': centers[si[-1]],
        'hvn': [(centers[i], vol[i]) for i in si[-3:]],
        'lvn': [(centers[i], vol[i]) for i in si[:3]],
    }

def cluster_levels(levels, tol=0.015):
    levels = sorted(set(levels))
    if not levels:
        return []
    clusters, cur = [], [levels[0]]
    for i in range(1, len(levels)):
        avg = sum(cur) / len(cur)
        if abs(levels[i] - avg) / avg <= tol:
            cur.append(levels[i])
        else:
            clusters.append(cur)
            cur = [levels[i]]
    clusters.append(cur)
    return [(sum(c)/len(c), len(c)) for c in clusters]

def analyze(ticker_str, period="6mo"):
    ticker = yf.Ticker(ticker_str)
    df = ticker.history(period="1y")
    if df.empty:
        return None

    info = ticker.info
    name = info.get('shortName', ticker_str)
    sector = info.get('sector', 'N/A')
    industry = info.get('industry', 'N/A')
    market_cap = info.get('marketCap', 0) or 0
    pe = info.get('trailingPE', 0) or 0
    forward_pe = info.get('forwardPE', 0) or 0
    eps = info.get('trailingEps', 0) or 0
    forward_eps = info.get('forwardEps', 0) or 0
    dy = (info.get('dividendYield', 0) or 0) * 100
    beta = info.get('beta', 0) or 0
    hi52 = info.get('fiftyTwoWeekHigh', 0) or df['High'].max()
    lo52 = info.get('fiftyTwoWeekLow', 0) or df['Low'].min()
    avg_vol = info.get('averageVolume', 0) or 0
    target_price = info.get('targetMeanPrice', 0) or 0
    target_high = info.get('targetHighPrice', 0) or 0
    target_low = info.get('targetLowPrice', 0) or 0
    num_analysts = info.get('numberOfAnalystOpinions', 0) or 0
    recommendation = info.get('recommendationKey', 'N/A')
    revenue_growth = info.get('revenueGrowth', 0) or 0
    earnings_growth = info.get('earningsGrowth', 0) or 0
    roe = info.get('returnOnEquity', 0) or 0
    debt_to_equity = info.get('debtToEquity', 0) or 0
    book_value = info.get('bookValue', 0) or 0
    price_to_book = info.get('priceToBook', 0) or 0
    profit_margins = info.get('profitMargins', 0) or 0
    operating_margins = info.get('operatingMargins', 0) or 0

    # === YAHOO FINANCE BROWSER DATA (via yfinance) ===
    # Holders data
    try:
        inst_holders = ticker.institutional_holders
        major_holders = ticker.major_holders
        insider_pct = None
        inst_pct = None
        float_inst_pct = None
        num_inst = None
        if major_holders is not None and len(major_holders) > 0:
            for _, row in major_holders.iterrows():
                val = row.iloc[0] if hasattr(row, 'iloc') else row[0]
                if 'Insider' in str(row.get('', '')) or 'insider' in str(val).lower():
                    insider_pct = float(val) if isinstance(val, (int, float)) else None
                elif 'Institutions' in str(row.get('', '')) and 'Float' not in str(row.get('', '')):
                    inst_pct = float(val) if isinstance(val, (int, float)) else None
                elif 'Float' in str(row.get('', '')):
                    float_inst_pct = float(val) if isinstance(val, (int, float)) else None
        if inst_holders is not None:
            num_inst = len(inst_holders)
    except:
        insider_pct = inst_pct = float_inst_pct = num_inst = None

    # Financials (annual)
    try:
        fin = ticker.financials
        if fin is not None and not fin.empty:
            latest_col = fin.columns[0]
            revenue_annual = fin.loc['Total Revenue', latest_col] if 'Total Revenue' in fin.index else None
            gross_profit_annual = fin.loc['Gross Profit', latest_col] if 'Gross Profit' in fin.index else None
            operating_income_annual = fin.loc['Operating Income', latest_col] if 'Operating Income' in fin.index else None
            net_income_annual = fin.loc['Net Income', latest_col] if 'Net Income' in fin.index else None
        else:
            revenue_annual = gross_profit_annual = operating_income_annual = net_income_annual = None
    except:
        revenue_annual = gross_profit_annual = operating_income_annual = net_income_annual = None

    # Quarterly earnings
    try:
        q_earnings = ticker.quarterly_earnings
        if q_earnings is not None and not q_earnings.empty:
            latest_q = q_earnings.iloc[-1]
            q_revenue = latest_q.get('revenue', None)
            q_earnings_val = latest_q.get('earnings', None)
        else:
            q_revenue = q_earnings_val = None
    except:
        q_revenue = q_earnings_val = None

    # === INDICATORS ===
    df6 = ticker.history(period=period)
    df6['SMA_20'] = df6['Close'].rolling(20).mean()
    df6['SMA_50'] = df6['Close'].rolling(50).mean()
    df6['SMA_200'] = df6['Close'].rolling(min(200, len(df6))).mean()
    df6['EMA_12'] = df6['Close'].ewm(span=12).mean()
    df6['EMA_26'] = df6['Close'].ewm(span=26).mean()
    df6['MACD'] = df6['EMA_12'] - df6['EMA_26']
    df6['MACD_Signal'] = df6['MACD'].ewm(span=9).mean()
    df6['MACD_Hist'] = df6['MACD'] - df6['MACD_Signal']
    delta = df6['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df6['RSI'] = 100 - (100 / (1 + gain / loss))
    df6['BB_Mid'] = df6['Close'].rolling(20).mean()
    df6['BB_Std'] = df6['Close'].rolling(20).std()
    df6['BB_Upper'] = df6['BB_Mid'] + 2 * df6['BB_Std']
    df6['BB_Lower'] = df6['BB_Mid'] - 2 * df6['BB_Std']
    df6['Stoch_K'] = ((df6['Close'] - df6['Low'].rolling(14).min()) /
                       (df6['High'].rolling(14).max() - df6['Low'].rolling(14).min())) * 100

    latest = df6.iloc[-1]
    prev = df6.iloc[-2]
    close = latest['Close']
    sma20 = latest['SMA_20']; sma50 = latest['SMA_50']; sma200 = latest['SMA_200']
    rsi = latest['RSI']; macd = latest['MACD']; macd_sig = latest['MACD_Signal']
    macd_hist = latest['MACD_Hist']; stoch = latest['Stoch_K']
    bb_u = latest['BB_Upper']; bb_l = latest['BB_Lower']; bb_mid = latest['BB_Mid']
    vol = latest['Volume']

    # === SUPPORT & RESISTANCE ===
    pivot = (latest['High'] + latest['Low'] + latest['Close']) / 3
    r1 = 2 * pivot - latest['Low']; s1 = 2 * pivot - latest['High']
    r2 = pivot + (latest['High'] - latest['Low']); s2 = pivot - (latest['High'] - latest['Low'])
    r3 = latest['High'] + 2 * (pivot - latest['Low']); s3 = latest['Low'] - 2 * (latest['High'] - pivot)

    swing_high = df6['High'].max(); swing_low = df6['Low'].min()
    fib = compute_fibonacci(swing_high, swing_low)
    vp = compute_volume_profile(df6)
    swing_highs, swing_lows = find_swing_points(df6['Close'], window=5)
    recent_sh = sorted(swing_highs, key=lambda x: x[0])[-3:]
    recent_sl = sorted(swing_lows, key=lambda x: x[0])[-3:]

    if close > 10000: step = 1000
    elif close > 1000: step = 500
    else: step = 100
    base = round(close / step) * step
    round_nums = [base - step, base, base + step, base + 2*step]

    all_r = [r1, r2, r3, bb_u, sma20, sma50, sma200] + [v for _, v in recent_sh] + round_nums + list(fib.values())
    all_s = [s1, s2, s3, bb_l, sma20, sma50, sma200] + [v for _, v in recent_sl] + round_nums + list(fib.values())
    r_clusters = cluster_levels(sorted([l for l in set(all_r) if l > close * 0.95])[:8])
    s_clusters = cluster_levels(sorted([l for l in set(all_s) if l < close * 1.05], reverse=True)[:8])

    # === PERFORMANCE ===
    def safe_pct(current, past):
        return ((current / past) - 1) * 100 if past else 0
    perf_1w = safe_pct(close, df6['Close'].iloc[-5]) if len(df6) >= 5 else 0
    perf_1m = safe_pct(close, df6['Close'].iloc[-21]) if len(df6) >= 21 else 0
    perf_3m = safe_pct(close, df6['Close'].iloc[-63]) if len(df6) >= 63 else 0
    perf_6m = safe_pct(close, df6['Close'].iloc[0])
    ytd_data = df6[df6.index >= f'{datetime.now().year}-01-01']
    perf_ytd = safe_pct(close, ytd_data['Close'].iloc[0]) if len(ytd_data) > 1 else 0
    perf_1y = safe_pct(close, df['Close'].iloc[0])
    pos52 = (close - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else 50

    # IHSG comparison
    try:
        ihsg = yf.Ticker("^JKSE")
        ihsg_df = ihsg.history(period=period)
        ihsg_perf = safe_pct(ihsg_df['Close'].iloc[-1], ihsg_df['Close'].iloc[0]) if len(ihsg_df) > 1 else 0
        alpha = perf_6m - ihsg_perf
    except:
        ihsg_perf = 0; alpha = 0

    # === SIGNAL DETECTION ===
    signals = []; score = 0

    if rsi < 20: signals.append(("STRONG_BUY", f"RSI extremely oversold ({rsi:.0f})")); score += 3
    elif rsi < 30: signals.append(("STRONG_BUY", f"RSI oversold ({rsi:.0f})")); score += 2
    elif rsi < 40: signals.append(("BUY", f"RSI near oversold ({rsi:.0f})")); score += 1
    elif rsi > 80: signals.append(("STRONG_SELL", f"RSI extremely overbought ({rsi:.0f})")); score -= 3
    elif rsi > 70: signals.append(("STRONG_SELL", f"RSI overbought ({rsi:.0f})")); score -= 2
    elif rsi > 60: signals.append(("SELL", f"RSI near overbought ({rsi:.0f})")); score -= 1

    if macd > macd_sig and prev['MACD'] <= prev['MACD_Signal']:
        signals.append(("STRONG_BUY", "MACD bullish crossover")); score += 2
    elif macd < macd_sig and prev['MACD'] >= prev['MACD_Signal']:
        signals.append(("STRONG_SELL", "MACD bearish crossover")); score -= 2
    elif macd > macd_sig and macd_hist > 0:
        signals.append(("BUY", "MACD bullish")); score += 1
    elif macd < macd_sig and macd_hist < 0:
        signals.append(("SELL", "MACD bearish")); score -= 1

    if sma20 > sma50 and prev['SMA_20'] <= prev['SMA_50']:
        signals.append(("STRONG_BUY", "Golden Cross")); score += 3
    elif sma20 < sma50 and prev['SMA_20'] >= prev['SMA_50']:
        signals.append(("STRONG_SELL", "Death Cross")); score -= 3
    elif sma20 > sma50: signals.append(("BUY", "SMA20 > SMA50")); score += 1
    elif sma20 < sma50: signals.append(("SELL", "SMA20 < SMA50")); score -= 1

    if close < bb_l: signals.append(("STRONG_BUY", "Below BB lower")); score += 2
    elif close > bb_u: signals.append(("STRONG_SELL", "Above BB upper")); score -= 2
    if stoch < 20: signals.append(("BUY", f"Stoch oversold ({stoch:.0f})")); score += 1
    elif stoch > 80: signals.append(("SELL", f"Stoch overbought ({stoch:.0f})")); score -= 1

    for level, cnt in s_clusters[:2]:
        if abs(close - level) / close < 0.02:
            signals.append(("BUY", f"Near support confluence ({level:.0f}, {cnt} methods)")); score += 1; break
    for level, cnt in r_clusters[:2]:
        if abs(close - level) / close < 0.02:
            signals.append(("SELL", f"Near resistance confluence ({level:.0f}, {cnt} methods)")); score -= 1; break

    if avg_vol > 0:
        ratio = vol / avg_vol
        if ratio > 2:
            if close > prev['Close']: signals.append(("STRONG_BUY", f"Vol spike {ratio:.1f}x + price up")); score += 2
            else: signals.append(("STRONG_SELL", f"Vol spike {ratio:.1f}x + price down")); score -= 2
        elif ratio > 1.5:
            if close > prev['Close']: signals.append(("BUY", f"Vol {ratio:.1f}x avg + price up")); score += 1
            else: signals.append(("SELL", f"Vol {ratio:.1f}x avg + price down")); score -= 1

    if pos52 < 10: signals.append(("BUY", f"At {pos52:.0f}% of 52W range")); score += 1
    elif pos52 > 90: signals.append(("SELL", f"At {pos52:.0f}% of 52W range")); score -= 1

    if score >= 5: overall = "STRONG_BUY"
    elif score >= 3: overall = "BUY"
    elif score >= 1: overall = "MILD_BUY"
    elif score <= -5: overall = "STRONG_SELL"
    elif score <= -3: overall = "SELL"
    elif score <= -1: overall = "MILD_SELL"
    else: overall = "NEUTRAL"

    if score > 0:
        entry_low = max(s1, bb_l * 1.01); entry_high = min(r1, pivot)
    else:
        entry_low = max(s1, bb_l); entry_high = pivot
    stop_loss = min(s2, bb_l * (0.99 if score > 0 else 0.98))

    # === OUTPUT ===
    chg = ((close/prev['Close'])-1)*100
    print(f"\n{'='*60}")
    print(f"  DEEP ANALYSIS: {ticker_str} — {name}")
    print(f"{'='*60}")
    print(f"  Price: {close:.2f} ({chg:+.2f}%)")
    print(f"  Sector: {sector} | Industry: {industry}")
    print(f"  Market Cap: {market_cap/1e12:.2f}T IDR")
    print(f"  P/E: {pe:.2f} | Fwd P/E: {forward_pe:.2f} | EPS: {eps:.2f} | Fwd EPS: {forward_eps:.2f}")
    print(f"  P/B: {price_to_book:.2f} | ROE: {roe*100:.1f}% | D/E: {debt_to_equity:.1f}")
    print(f"  Div Yield: {dy:.2f}% | Beta: {beta:.2f}")
    print(f"  Revenue Growth: {revenue_growth*100:.1f}% | Earnings Growth: {earnings_growth*100:.1f}%")
    print(f"  Profit Margin: {profit_margins*100:.1f}% | Op Margin: {operating_margins*100:.1f}%")
    if target_price:
        print(f"  Analyst Target: {target_price:.0f} (Low: {target_low:.0f}, High: {target_high:.0f})")
        print(f"  # Analysts: {num_analysts} | Consensus: {recommendation}")
    print(f"  52W: {lo52:.0f} — {hi52:.0f} ( posisi: {pos52:.0f}% )")

    # Holders
    print(f"\n  OWNERSHIP:")
    if insider_pct: print(f"    Insider: {insider_pct:.2f}%")
    if inst_pct: print(f"    Institutions: {inst_pct:.2f}%")
    if float_inst_pct: print(f"    Float Held by Inst: {float_inst_pct:.2f}%")
    if num_inst: print(f"    # Institutions: {num_inst}")

    # Financials
    if revenue_annual:
        print(f"\n  FINANCIALS (Annual):")
        print(f"    Revenue: {revenue_annual/1e12:.2f}T")
        if gross_profit_annual: print(f"    Gross Profit: {gross_profit_annual/1e12:.2f}T")
        if operating_income_annual: print(f"    Operating Income: {operating_income_annual/1e12:.2f}T")
        if net_income_annual: print(f"    Net Income: {net_income_annual/1e12:.2f}T")

    print(f"\n  PERFORMANCE:")
    print(f"  1W: {perf_1w:+.1f}% | 1M: {perf_1m:+.1f}% | 3M: {perf_3m:+.1f}%")
    print(f"  6M: {perf_6m:+.1f}% | YTD: {perf_ytd:+.1f}% | 1Y: {perf_1y:+.1f}%")
    print(f"  IHSG 6M: {ihsg_perf:+.1f}% | Alpha vs IHSG: {alpha:+.1f}%")

    print(f"\n  TECHNICAL:")
    print(f"  RSI: {rsi:.0f} | MACD: {macd:.1f} (Sig: {macd_sig:.1f}) | Stoch: {stoch:.0f}")
    print(f"  SMA20: {sma20:.0f} | SMA50: {sma50:.0f} | SMA200: {sma200:.0f}")
    print(f"  BB: U={bb_u:.0f} M={bb_mid:.0f} L={bb_l:.0f}")

    print(f"\n  SUPPORT & RESISTANCE:")
    print(f"  Pivot: R3={r3:.0f} R2={r2:.0f} R1={r1:.0f} P={pivot:.0f} S1={s1:.0f} S2={s2:.0f} S3={s3:.0f}")
    fib_str = ' | '.join([f'{k}={v:.0f}' for k, v in fib.items()])
    print(f"  Fib: {fib_str}")
    print(f"  POC: {vp['poc']:.0f} | HVN: {', '.join([f'{p:.0f}' for p,_ in vp['hvn']])} | LVN: {', '.join([f'{p:.0f}' for p,_ in vp['lvn']])}")
    sh_str = ', '.join([f'{p:.0f}' for _,p in recent_sh])
    sl_str = ', '.join([f'{p:.0f}' for _,p in recent_sl])
    print(f"  Swing Highs: {sh_str} | Swing Lows: {sl_str}")
    if r_clusters:
        print(f"  Res Confluence: {', '.join([f'{l:.0f}({c}x)' for l,c in r_clusters[:4]])}")
    if s_clusters:
        print(f"  Sup Confluence: {', '.join([f'{l:.0f}({c}x)' for l,c in s_clusters[:4]])}")

    print(f"\n  SIGNALS (Score: {score}):")
    print(f"  OVERALL: {overall}")
    for sig, reason in signals:
        print(f"    [{sig}] {reason}")

    sl_pct = ((stop_loss/close)-1)*100
    t1_pct = ((r1/close)-1)*100; t2_pct = ((r2/close)-1)*100; t3_pct = ((hi52/close)-1)*100
    print(f"\n  TRADE PLAN:")
    print(f"  Entry: {entry_low:.0f} — {entry_high:.0f}")
    print(f"  Stop Loss: {stop_loss:.0f} ({sl_pct:.1f}%)")
    print(f"  Target 1: {r1:.0f} ({t1_pct:+.1f}%)")
    print(f"  Target 2: {r2:.0f} ({t2_pct:+.1f}%)")
    print(f"  Target 3: {hi52:.0f} ({t3_pct:+.1f}%)")
    if target_price:
        tp_pct = ((target_price/close)-1)*100
        print(f"  Analyst Target: {target_price:.0f} ({tp_pct:+.1f}%)")
    print(f"{'='*60}\n")

    return {
        'ticker': ticker_str, 'name': name, 'sector': sector, 'industry': industry,
        'close': close, 'change_pct': chg,
        'market_cap': market_cap, 'pe': pe, 'forward_pe': forward_pe,
        'eps': eps, 'forward_eps': forward_eps,
        'dividend_yield': dy, 'beta': beta,
        'price_to_book': price_to_book, 'roe': roe, 'debt_to_equity': debt_to_equity,
        'revenue_growth': revenue_growth, 'earnings_growth': earnings_growth,
        'profit_margins': profit_margins, 'operating_margins': operating_margins,
        'target_price': target_price, 'target_high': target_high, 'target_low': target_low,
        'num_analysts': num_analysts, 'recommendation': recommendation,
        'insider_pct': insider_pct, 'inst_pct': inst_pct,
        'float_inst_pct': float_inst_pct, 'num_inst': num_inst,
        'revenue_annual': revenue_annual, 'gross_profit_annual': gross_profit_annual,
        'operating_income_annual': operating_income_annual, 'net_income_annual': net_income_annual,
        'hi52': hi52, 'lo52': lo52, 'pos52': pos52,
        'perf_1w': perf_1w, 'perf_1m': perf_1m, 'perf_3m': perf_3m,
        'perf_6m': perf_6m, 'perf_ytd': perf_ytd, 'perf_1y': perf_1y,
        'ihsg_6m': ihsg_perf, 'alpha': alpha,
        'rsi': rsi, 'macd': macd, 'macd_signal': macd_sig,
        'sma20': sma20, 'sma50': sma50, 'sma200': sma200,
        'bb_upper': bb_u, 'bb_lower': bb_l, 'bb_mid': bb_mid,
        'stoch_k': stoch, 'volume': vol, 'avg_volume': avg_vol,
        'score': score, 'overall': overall, 'signals': signals,
        'pivot': pivot, 'r1': r1, 'r2': r2, 'r3': r3, 's1': s1, 's2': s2, 's3': s3,
        'fib': fib, 'volume_profile': vp,
        'swing_highs': recent_sh, 'swing_lows': recent_sl,
        'resistance_clusters': r_clusters[:4], 'support_clusters': s_clusters[:4],
        'entry_low': entry_low, 'entry_high': entry_high,
        'stop_loss': stop_loss, 'target_1': r1, 'target_2': r2, 'target_3': hi52,
    }

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBRI.JK"
    period = sys.argv[2] if len(sys.argv) > 2 else "6mo"
    result = analyze(ticker, period)
    if not result:
        print(f"ERROR: {ticker}"); sys.exit(1)
    print(f"DONE: {ticker}")
