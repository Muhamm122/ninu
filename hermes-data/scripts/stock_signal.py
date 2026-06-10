"""
IDX Stock Signal Detector v2 — with Support/Resistance Model
Usage: python3 stock_signal.py TICKER.JK
"""
import sys
import yfinance as yf
import pandas as pd
import numpy as np

def find_swing_points(series, window=5):
    """Find swing highs and lows in a price series"""
    swing_highs = []
    swing_lows = []
    for i in range(window, len(series) - window):
        if series.iloc[i] == series.iloc[i-window:i+window+1].max():
            swing_highs.append((series.index[i], series.iloc[i]))
        if series.iloc[i] == series.iloc[i-window:i+window+1].min():
            swing_lows.append((series.index[i], series.iloc[i]))
    return swing_highs, swing_lows

def compute_fibonacci(high, low):
    """Compute Fibonacci retracement levels"""
    rng = high - low
    return {
        '0% (Swing High)': high,
        '23.6%': high - rng * 0.236,
        '38.2%': high - rng * 0.382,
        '50.0%': high - rng * 0.500,
        '61.8%': high - rng * 0.618,
        '78.6%': high - rng * 0.786,
        '100% (Swing Low)': low,
    }

def compute_volume_profile(df, bins=20):
    """Compute simplified volume profile"""
    price_min = df['Close'].min()
    price_max = df['Close'].max()
    bin_edges = np.linspace(price_min, price_max, bins + 1)
    volume_by_bin = np.zeros(bins)
    
    for _, row in df.iterrows():
        price = row['Close']
        vol = row['Volume']
        bin_idx = min(int((price - price_min) / (price_max - price_min) * bins), bins - 1)
        volume_by_bin[bin_idx] += vol
    
    # Find high/low volume nodes
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    sorted_indices = np.argsort(volume_by_bin)
    
    lvn = [(bin_centers[i], volume_by_bin[i]) for i in sorted_indices[:3]]
    hvn = [(bin_centers[i], volume_by_bin[i]) for i in sorted_indices[-3:]]
    poc_idx = sorted_indices[-1]
    
    return {
        'poc': bin_centers[poc_idx],
        'hvn': hvn,
        'lvn': lvn,
        'bin_centers': bin_centers,
        'volume_by_bin': volume_by_bin,
    }

def cluster_levels(levels, tolerance=0.015):
    """Cluster nearby price levels (within tolerance %) into confluence zones"""
    levels = sorted(levels)
    clusters = []
    current_cluster = [levels[0]]
    
    for i in range(1, len(levels)):
        avg = sum(current_cluster) / len(current_cluster)
        if abs(levels[i] - avg) / avg <= tolerance:
            current_cluster.append(levels[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [levels[i]]
    clusters.append(current_cluster)
    
    return [(sum(c) / len(c), len(c)) for c in clusters]

def analyze_signals(ticker_str):
    ticker = yf.Ticker(ticker_str)
    df = ticker.history(period="6mo")
    if df.empty:
        return None
    
    info = ticker.info
    name = info.get('shortName', ticker_str)
    market_cap = info.get('marketCap', 0)
    pe = info.get('trailingPE', 0)
    eps = info.get('trailingEps', 0)
    dy = (info.get('dividendYield', 0) or 0) * 100
    beta = info.get('beta', 0)
    hi52 = info.get('fiftyTwoWeekHigh', 0) or df['High'].max()
    lo52 = info.get('fiftyTwoWeekLow', 0) or df['Low'].min()
    avg_vol = info.get('averageVolume', 0)
    
    # === INDICATORS ===
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
    df['SMA_200'] = df['Close'].rolling(min(200, len(df))).mean()
    df['EMA_12'] = df['Close'].ewm(span=12).mean()
    df['EMA_26'] = df['Close'].ewm(span=26).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    
    df['BB_Mid'] = df['Close'].rolling(20).mean()
    df['BB_Std'] = df['Close'].rolling(20).std()
    df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
    df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
    df['Stoch_K'] = ((df['Close'] - df['Low'].rolling(14).min()) /
                     (df['High'].rolling(14).max() - df['Low'].rolling(14).min())) * 100
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    close = latest['Close']
    sma20 = latest['SMA_20']; sma50 = latest['SMA_50']; sma200 = latest['SMA_200']
    rsi = latest['RSI']; macd = latest['MACD']; macd_sig = latest['MACD_Signal']
    macd_hist = latest['MACD_Hist']; stoch = latest['Stoch_K']
    bb_u = latest['BB_Upper']; bb_l = latest['BB_Lower']; bb_mid = latest['BB_Mid']
    vol = latest['Volume']
    
    # === SUPPORT & RESISTANCE ===
    # Method 1: Pivot Points (daily)
    last = df.iloc[-1]
    pivot = (last['High'] + last['Low'] + last['Close']) / 3
    r1 = 2 * pivot - last['Low']; s1 = 2 * pivot - last['High']
    r2 = pivot + (last['High'] - last['Low']); s2 = pivot - (last['High'] - last['Low'])
    r3 = last['High'] + 2 * (pivot - last['Low']); s3 = last['Low'] - 2 * (last['High'] - pivot)
    
    # Method 2: Fibonacci (6-month swing)
    swing_high = df['High'].max()
    swing_low = df['Low'].min()
    fib = compute_fibonacci(swing_high, swing_low)
    
    # Method 3: Volume Profile
    vp = compute_volume_profile(df)
    
    # Method 4: Swing points
    swing_highs, swing_lows = find_swing_points(df['Close'], window=5)
    recent_sh = sorted(swing_highs, key=lambda x: x[0])[-3:]
    recent_sl = sorted(swing_lows, key=lambda x: x[0])[-3:]
    
    # Method 5: Round numbers
    def round_levels(price, step):
        base = round(price / step) * step
        return [base - step, base, base + step, base + 2 * step]
    
    if close > 10000:
        step = 1000
    elif close > 1000:
        step = 500
    else:
        step = 100
    round_nums = round_levels(close, step)
    
    # Confluence detection
    all_resistance = [r1, r2, r3, bb_u, sma20, sma50, sma200] + [v for _, v in recent_sh] + round_nums
    all_support = [s1, s2, s3, bb_l, sma20, sma50, sma200] + [v for _, v in recent_sl] + round_nums
    fib_levels = list(fib.values())
    all_resistance += fib_levels
    all_support += fib_levels
    
    # Filter to relevant levels (near current price)
    r_levels = sorted([l for l in all_resistance if l > close * 0.95])
    s_levels = sorted([l for l in all_support if l < close * 1.05], reverse=True)
    
    r_clusters = cluster_levels(r_levels[:8])
    s_clusters = cluster_levels(s_levels[:8])
    
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
    
    # S/R proximity signals
    for level, count in s_clusters[:2]:
        if abs(close - level) / close < 0.02:
            signals.append(("BUY", f"Price near support confluence ({level:.0f}, {count} methods)"))
            score += 1
            break
    
    for level, count in r_clusters[:2]:
        if abs(close - level) / close < 0.02:
            signals.append(("SELL", f"Price near resistance confluence ({level:.0f}, {count} methods)"))
            score -= 1
            break
    
    if avg_vol > 0:
        ratio = vol / avg_vol
        if ratio > 2:
            if close > prev['Close']: signals.append(("STRONG_BUY", f"Vol spike {ratio:.1f}x + price up")); score += 2
            else: signals.append(("STRONG_SELL", f"Vol spike {ratio:.1f}x + price down")); score -= 2
        elif ratio > 1.5:
            if close > prev['Close']: signals.append(("BUY", f"Vol {ratio:.1f}x avg + price up")); score += 1
            else: signals.append(("SELL", f"Vol {ratio:.1f}x avg + price down")); score -= 1
    
    if hi52 > 0 and lo52 > 0:
        pos52 = (close - lo52) / (hi52 - lo52) * 100
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
    print(f"\n=== SIGNAL: {ticker_str} — {name} ===")
    print(f"Price: {close:.2f} ({((close/prev['Close'])-1)*100:+.2f}%)")
    print(f"P/E: {pe:.2f} | EPS: {eps:.2f} | DY: {dy:.2f}% | Beta: {beta:.2f}")
    print(f"RSI: {rsi:.0f} | MACD: {macd:.1f} | Stoch: {stoch:.0f}")
    print(f"SMA20: {sma20:.0f} | SMA50: {sma50:.0f} | SMA200: {sma200:.0f}")
    print(f"Score: {score} | OVERALL: {overall}")
    
    for sig, reason in signals:
        print(f"  [{sig}] {reason}")
    
    print(f"\n--- SUPPORT & RESISTANCE ---")
    print(f"Pivot Levels:")
    print(f"  R3: {r3:.0f} | R2: {r2:.0f} | R1: {r1:.0f} | Pivot: {pivot:.0f} | S1: {s1:.0f} | S2: {s2:.0f} | S3: {s3:.0f}")
    print(f"Fib ({swing_high:.0f} → {swing_low:.0f}):")
    for label, val in fib.items():
        print(f"  {label}: {val:.0f}")
    print(f"Volume Profile: POC={vp['poc']:.0f}")
    print(f"  HVN: {', '.join([f'{p:.0f}' for p, _ in vp['hvn']])}")
    print(f"  LVN: {', '.join([f'{p:.0f}' for p, _ in vp['lvn']])}")
    print(f"Swing Highs: {', '.join([f'{p:.0f}' for _, p in recent_sh])}")
    print(f"Swing Lows: {', '.join([f'{p:.0f}' for _, p in recent_sl])}")
    print(f"BB: U={bb_u:.0f} M={bb_mid:.0f} L={bb_l:.0f}")
    
    if r_clusters:
        print(f"Resistance Confluence: {', '.join([f'{l:.0f}({c}x)' for l, c in r_clusters[:4]])}")
    if s_clusters:
        print(f"Support Confluence: {', '.join([f'{l:.0f}({c}x)' for l, c in s_clusters[:4]])}")
    
    print(f"\nENTRY: {entry_low:.0f}-{entry_high:.0f} | SL: {stop_loss:.0f} | T1: {r1:.0f} | T2: {r2:.0f} | T3: {hi52:.0f}")
    
    return {
        'ticker': ticker_str, 'name': name, 'close': close,
        'change_pct': ((close / prev['Close']) - 1) * 100,
        'market_cap': market_cap, 'pe': pe, 'eps': eps,
        'dividend_yield': dy, 'beta': beta,
        'hi52': hi52, 'lo52': lo52, 'pos52': pos52 if hi52 > 0 and lo52 > 0 else 50,
        'rsi': rsi, 'macd': macd, 'macd_signal': macd_sig,
        'sma20': sma20, 'sma50': sma50, 'sma200': sma200,
        'bb_upper': bb_u, 'bb_lower': bb_l, 'bb_mid': bb_mid,
        'stoch_k': stoch, 'volume': vol, 'avg_volume': avg_vol,
        'score': score, 'overall': overall, 'signals': signals,
        'pivot': pivot, 'r1': r1, 'r2': r2, 'r3': r3,
        's1': s1, 's2': s2, 's3': s3,
        'fib': fib,
        'volume_profile': vp,
        'swing_highs': recent_sh, 'swing_lows': recent_sl,
        'resistance_clusters': r_clusters[:4],
        'support_clusters': s_clusters[:4],
        'entry_low': entry_low, 'entry_high': entry_high,
        'stop_loss': stop_loss, 'target_1': r1, 'target_2': r2, 'target_3': hi52,
    }

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBRI.JK"
    result = analyze_signals(ticker)
    if not result:
        print(f"ERROR: {ticker}")
        sys.exit(1)
    print(f"DONE: {ticker}")
