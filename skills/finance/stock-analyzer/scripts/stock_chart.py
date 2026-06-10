"""
IDX Stock Chart Generator v2 — with S/R levels overlaid on chart
Usage: python3 stock_chart.py TICKER.JK [period]
"""
import sys
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
matplotlib.use('Agg')

def find_swing_points(series, window=5):
    swing_highs = []
    swing_lows = []
    for i in range(window, len(series) - window):
        if series.iloc[i] == series.iloc[i-window:i+window+1].max():
            swing_highs.append((series.index[i], series.iloc[i]))
        if series.iloc[i] == series.iloc[i-window:i+window+1].min():
            swing_lows.append((series.index[i], series.iloc[i]))
    return swing_highs, swing_lows

def generate_charts(ticker_str, period="6mo", outdir="/tmp"):
    ticker = yf.Ticker(ticker_str)
    df = ticker.history(period=period)
    if df.empty:
        print(f"ERROR: No data for {ticker_str}")
        return None
    
    # Indicators
    df['SMA_20'] = df['Close'].rolling(20).mean()
    df['SMA_50'] = df['Close'].rolling(50).mean()
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
    
    df_plot = df.dropna().copy()
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    close = latest['Close']
    
    sma20 = df['SMA_20'].iloc[-1]
    sma50 = df['SMA_50'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    macd_sig = df['MACD_Signal'].iloc[-1]
    bb_upper = df['BB_Upper'].iloc[-1]
    bb_mid = df['BB_Mid'].iloc[-1]
    bb_lower = df['BB_Lower'].iloc[-1]
    
    # S/R Levels
    last = df.iloc[-1]
    pivot = (last['High'] + last['Low'] + last['Close']) / 3
    r1 = 2 * pivot - last['Low']; s1 = 2 * pivot - last['High']
    r2 = pivot + (last['High'] - last['Low']); s2 = pivot - (last['High'] - last['Low'])
    r3 = last['High'] + 2 * (pivot - last['Low']); s3 = last['Low'] - 2 * (last['High'] - pivot)
    
    swing_high = df['High'].max(); swing_low = df['Low'].min()
    rng = swing_high - swing_low
    fib_382 = swing_high - rng * 0.382
    fib_500 = swing_high - rng * 0.500
    fib_618 = swing_high - rng * 0.618
    
    swing_highs, swing_lows = find_swing_points(df['Close'], window=5)
    recent_sh = sorted(swing_highs, key=lambda x: x[0])[-3:]
    recent_sl = sorted(swing_lows, key=lambda x: x[0])[-3:]
    
    # Signals
    signals = []
    if rsi < 30: signals.append(("STRONG_BUY", "RSI oversold"))
    elif rsi < 40: signals.append(("BUY", "RSI near oversold"))
    elif rsi > 70: signals.append(("STRONG_SELL", "RSI overbought"))
    if macd > macd_sig and df['MACD_Hist'].iloc[-1] > 0: signals.append(("BUY", "MACD bullish"))
    elif macd < macd_sig and df['MACD_Hist'].iloc[-1] < 0: signals.append(("SELL", "MACD bearish"))
    if close < bb_lower: signals.append(("BUY", "Below BB lower"))
    elif close > bb_upper: signals.append(("SELL", "Above BB upper"))
    if sma20 > sma50 and df['SMA_20'].iloc[-2] <= df['SMA_50'].iloc[-2]: signals.append(("STRONG_BUY", "Golden Cross"))
    elif sma20 < sma50 and df['SMA_20'].iloc[-2] >= df['SMA_50'].iloc[-2]: signals.append(("STRONG_SELL", "Death Cross"))
    
    for sig, reason in signals:
        print(f"  [{sig}] {reason}")
    
    entry_low = max(s1, bb_lower * 1.01); entry_high = min(r1, pivot)
    stop_loss = min(s2, bb_lower * 0.99)
    
    print(f"\n=== TECHNICAL: {ticker_str} ===")
    print(f"Close: {close:.2f} | Chg: {((close/prev['Close'])-1)*100:+.2f}%")
    print(f"SMA20: {sma20:.2f} | SMA50: {sma50:.2f}")
    print(f"RSI: {rsi:.1f} | MACD: {macd:.2f} | Signal: {macd_sig:.2f}")
    print(f"BB: U={bb_upper:.2f} M={bb_mid:.2f} L={bb_lower:.2f}")
    print(f"Pivot: R3={r3:.0f} R2={r2:.0f} R1={r1:.0f} P={pivot:.0f} S1={s1:.0f} S2={s2:.0f} S3={s3:.0f}")
    print(f"Fib: 38.2%={fib_382:.0f} 50%={fib_500:.0f} 61.8%={fib_618:.0f}")
    print(f"ENTRY: {entry_low:.0f}-{entry_high:.0f} | SL: {stop_loss:.0f} | T1: {r1:.0f} | T2: {r2:.0f} | T3: {swing_high:.0f}")
    
    # === CHART STYLE ===
    style = mpf.make_mpf_style(
        base_mpf_style='nightclouds',
        marketcolors=mpf.make_marketcolors(up='lime', down='red', edge='inherit', wick='inherit', volume='in'),
        figcolor='#1a1a2f', gridcolor='#2a2a4a', facecolor='#1a1a2f'
    )
    
    # S/R horizontal lines as addplot (constant values)
    sr_length = len(df_plot)
    r1_line = pd.Series([r1] * sr_length, index=df_plot.index)
    r2_line = pd.Series([r2] * sr_length, index=df_plot.index)
    s1_line = pd.Series([s1] * sr_length, index=df_plot.index)
    s2_line = pd.Series([s2] * sr_length, index=df_plot.index)
    pivot_line = pd.Series([pivot] * sr_length, index=df_plot.index)
    fib50_line = pd.Series([fib_500] * sr_length, index=df_plot.index)
    fib618_line = pd.Series([fib_618] * sr_length, index=df_plot.index)
    
    apd = [
        mpf.make_addplot(df_plot['SMA_20'], color='orange', width=1.2, label='SMA20'),
        mpf.make_addplot(df_plot['SMA_50'], color='blue', width=1.2, label='SMA50'),
        mpf.make_addplot(df_plot['BB_Upper'], color='gray', linestyle='--', width=0.7, label='BB Upper'),
        mpf.make_addplot(df_plot['BB_Lower'], color='gray', linestyle='--', width=0.7, label='BB Lower'),
        mpf.make_addplot(r1_line, color='red', linestyle=':', width=0.8, label=f'R1 {r1:.0f}'),
        mpf.make_addplot(r2_line, color='red', linestyle=':', width=0.8, label=f'R2 {r2:.0f}'),
        mpf.make_addplot(s1_line, color='lime', linestyle=':', width=0.8, label=f'S1 {s1:.0f}'),
        mpf.make_addplot(s2_line, color='lime', linestyle=':', width=0.8, label=f'S2 {s2:.0f}'),
        mpf.make_addplot(pivot_line, color='yellow', linestyle='-.', width=0.8, label=f'Pivot {pivot:.0f}'),
        mpf.make_addplot(fib50_line, color='cyan', linestyle=':', width=0.6, label=f'Fib50% {fib_500:.0f}'),
        mpf.make_addplot(fib618_line, color='cyan', linestyle=':', width=0.6, label=f'Fib61.8% {fib_618:.0f}'),
    ]
    
    clean = ticker_str.replace('.', '_').replace('-', '_')
    chart_p = f"{outdir}/{clean}_chart.png"
    rsi_p = f"{outdir}/{clean}_rsi.png"
    macd_p = f"{outdir}/{clean}_macd.png"
    
    # Main chart with S/R lines
    fig, axes = mpf.plot(
        df_plot, type='candle', style=style,
        title=f'\n{ticker_str} — {period} (S/R lines: R1/R2/S1/S2/Pivot/Fib)',
        ylabel='Price (IDR)', volume=True,
        addplot=apd, figsize=(18, 11),
        returnfig=True, tight_layout=True
    )
    
    # Mark swing points on chart
    ax_main = axes[0]
    for date, price in recent_sh:
        if date in df_plot.index:
            ax_main.scatter(date, price, marker='v', color='red', s=80, zorder=5)
    for date, price in recent_sl:
        if date in df_plot.index:
            ax_main.scatter(date, price, marker='^', color='lime', s=80, zorder=5)
    
    fig.savefig(chart_p, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"OK Chart: {chart_p}")
    
    # RSI
    fig2, ax2 = plt.subplots(figsize=(18, 4), facecolor='#1a1a2f')
    ax2.plot(df_plot.index, df_plot['RSI'], color='cyan', linewidth=1.2)
    ax2.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
    ax2.axhline(y=30, color='lime', linestyle='--', alpha=0.7, label='Oversold (30)')
    ax2.axhline(y=50, color='gray', linestyle=':', alpha=0.5)
    ax2.fill_between(df_plot.index, df_plot['RSI'], 70, where=(df_plot['RSI'] >= 70), color='red', alpha=0.3)
    ax2.fill_between(df_plot.index, df_plot['RSI'], 30, where=(df_plot['RSI'] <= 30), color='lime', alpha=0.3)
    ax2.set_facecolor('#1a1a2f'); ax2.tick_params(colors='white')
    for s in ax2.spines.values(): s.set_color('white')
    ax2.set_ylabel('RSI', color='white'); ax2.set_title('RSI (14)', color='white')
    ax2.legend(loc='upper left', fontsize=9)
    fig2.savefig(rsi_p, dpi=150, bbox_inches='tight', facecolor=fig2.get_facecolor())
    print(f"OK RSI: {rsi_p}")
    
    # MACD
    fig3, ax3 = plt.subplots(figsize=(18, 4), facecolor='#1a1a2f')
    ax3.plot(df_plot.index, df_plot['MACD'], color='cyan', linewidth=1.2, label='MACD')
    ax3.plot(df_plot.index, df_plot['MACD_Signal'], color='orange', linewidth=1.0, label='Signal')
    colors_bar = ['lime' if v >= 0 else 'red' for v in df_plot['MACD_Hist']]
    ax3.bar(df_plot.index, df_plot['MACD_Hist'], color=colors_bar, alpha=0.5, width=1.5)
    ax3.axhline(y=0, color='white', linewidth=0.5)
    ax3.set_facecolor('#1a1a2f'); ax3.tick_params(colors='white')
    for s in ax3.spines.values(): s.set_color('white')
    ax3.set_title('MACD (12,26,9)', color='white'); ax3.legend(loc='upper left', fontsize=9)
    fig3.savefig(macd_p, dpi=150, bbox_inches='tight', facecolor=fig3.get_facecolor())
    print(f"OK MACD: {macd_p}")
    
    return {
        'chart': chart_p, 'rsi': rsi_p, 'macd': macd_p,
        'close': close, 'sma20': sma20, 'sma50': sma50, 'rsi': rsi,
        'macd': macd, 'signals': signals,
        'pivot': pivot, 'r1': r1, 'r2': r2, 'r3': r3,
        's1': s1, 's2': s2, 's3': s3,
        'fib_382': fib_382, 'fib_500': fib_500, 'fib_618': fib_618,
        'swing_highs': recent_sh, 'swing_lows': recent_sl,
        'levels': {'entry_low': entry_low, 'entry_high': entry_high,
                   'stop_loss': stop_loss, 'target_1': r1, 'target_2': r2, 'target_3': swing_high}
    }

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBRI.JK"
    period = sys.argv[2] if len(sys.argv) > 2 else "6mo"
    result = generate_charts(ticker, period)
    print(f"DONE: {ticker}" if result else f"FAIL: {ticker}")
