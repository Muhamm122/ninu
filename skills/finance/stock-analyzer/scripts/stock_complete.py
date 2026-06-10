"""
IDX Stock Complete Analysis Pipeline v5
========================================
Menggabungkan:
1. TEKNIKAL: S/R multi-method, oscillators, MAs, BB, volume profile
2. FUNDAMENTAL: P/E, EPS, ROE, margins, growth, analyst consensus
3. EKONOMI MIKRO: Sektor, industri, competitive position, company-specific risks
4. EKONOMI MAKRO: IHSG, BI rate, GDP, inflation, fiscal policy, global sentiment
5. CHART: Candlestick + S/R lines, RSI, MACD

Usage: python3 stock_complete.py TICKER.JK
"""
import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# SECTION 1: TECHNICAL ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════

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
        '50.0%': high - rng*0.500, '61.8%': high - rng*0.618,
        '78.6%': high - rng*0.786, '100%': low,
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

def compute_indicators(df):
    """Compute all technical indicators"""
    df = df.copy()
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
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).cumsum()
    return df

def compute_support_resistance(df_ind, df_price):
    """Multi-method S/R computation. df_ind has indicators, df_price has OHLCV."""
    latest = df_ind.iloc[-1]
    close = latest['Close']
    
    # Pivot Points (from price data)
    pivot = (latest['High'] + latest['Low'] + latest['Close']) / 3
    r1 = 2 * pivot - latest['Low']; s1 = 2 * pivot - latest['High']
    r2 = pivot + (latest['High'] - latest['Low']); s2 = pivot - (latest['High'] - latest['Low'])
    r3 = latest['High'] + 2 * (pivot - latest['Low']); s3 = latest['Low'] - 2 * (latest['High'] - pivot)
    
    # Fibonacci
    swing_high = df_price['High'].max(); swing_low = df_price['Low'].min()
    fib = compute_fibonacci(swing_high, swing_low)
    
    # Volume Profile
    vp = compute_volume_profile(df_price)
    
    # Swing Points
    swing_highs, swing_lows = find_swing_points(df_price['Close'], window=5)
    recent_sh = sorted(swing_highs, key=lambda x: x[0])[-3:]
    recent_sl = sorted(swing_lows, key=lambda x: x[0])[-3:]
    
    # Round Numbers
    if close > 10000: step = 1000
    elif close > 1000: step = 500
    else: step = 100
    base = round(close / step) * step
    round_nums = [base - step, base, base + step, base + 2*step]
    
    # Confluence
    sma20 = latest['SMA_20']; sma50 = latest['SMA_50']; sma200 = latest['SMA_200']
    bb_u = latest['BB_Upper']; bb_l = latest['BB_Lower']
    
    all_r = [r1, r2, r3, bb_u, sma20, sma50, sma200] + [v for _, v in recent_sh] + round_nums + list(fib.values())
    all_s = [s1, s2, s3, bb_l, sma20, sma50, sma200] + [v for _, v in recent_sl] + round_nums + list(fib.values())
    
    r_clusters = cluster_levels(sorted([l for l in set(all_r) if l > close * 0.95])[:8])
    s_clusters = cluster_levels(sorted([l for l in set(all_s) if l < close * 1.05], reverse=True)[:8])
    
    return {
        'pivot': pivot, 'r1': r1, 'r2': r2, 'r3': r3, 's1': s1, 's2': s2, 's3': s3,
        'fib': fib, 'vp': vp, 'recent_sh': recent_sh, 'recent_sl': recent_sl,
        'r_clusters': r_clusters[:4], 's_clusters': s_clusters[:4],
        'swing_high': swing_high, 'swing_low': swing_low,
    }

def detect_signals(latest, prev, close, avg_vol, hi52, lo52, s_clusters, r_clusters):
    """Signal detection engine"""
    signals = []; score = 0
    rsi = latest['RSI']; macd = latest['MACD']; macd_sig = latest['MACD_Signal']
    macd_hist = latest['MACD_Hist']; stoch = latest['Stoch_K']
    bb_u = latest['BB_Upper']; bb_l = latest['BB_Lower']
    sma20 = latest['SMA_20']; sma50 = latest['SMA_50']
    vol = latest['Volume']
    
    # RSI
    if rsi < 20: signals.append(("STRONG_BUY", f"RSI extremely oversold ({rsi:.0f})")); score += 3
    elif rsi < 30: signals.append(("STRONG_BUY", f"RSI oversold ({rsi:.0f})")); score += 2
    elif rsi < 40: signals.append(("BUY", f"RSI near oversold ({rsi:.0f})")); score += 1
    elif rsi > 80: signals.append(("STRONG_SELL", f"RSI extremely overbought ({rsi:.0f})")); score -= 3
    elif rsi > 70: signals.append(("STRONG_SELL", f"RSI overbought ({rsi:.0f})")); score -= 2
    elif rsi > 60: signals.append(("SELL", f"RSI near overbought ({rsi:.0f})")); score -= 1
    
    # MACD
    if macd > macd_sig and prev['MACD'] <= prev['MACD_Signal']:
        signals.append(("STRONG_BUY", "MACD bullish crossover")); score += 2
    elif macd < macd_sig and prev['MACD'] >= prev['MACD_Signal']:
        signals.append(("STRONG_SELL", "MACD bearish crossover")); score -= 2
    elif macd > macd_sig and macd_hist > 0:
        signals.append(("BUY", "MACD bullish")); score += 1
    elif macd < macd_sig and macd_hist < 0:
        signals.append(("SELL", "MACD bearish")); score -= 1
    
    # SMA Crossover
    if sma20 > sma50 and prev['SMA_20'] <= prev['SMA_50']:
        signals.append(("STRONG_BUY", "Golden Cross")); score += 3
    elif sma20 < sma50 and prev['SMA_20'] >= prev['SMA_50']:
        signals.append(("STRONG_SELL", "Death Cross")); score -= 3
    elif sma20 > sma50: signals.append(("BUY", "SMA20 > SMA50")); score += 1
    elif sma20 < sma50: signals.append(("SELL", "SMA20 < SMA50")); score -= 1
    
    # Bollinger Bands
    if close < bb_l: signals.append(("STRONG_BUY", "Below BB lower")); score += 2
    elif close > bb_u: signals.append(("STRONG_SELL", "Above BB upper")); score -= 2
    
    # Stochastic
    if stoch < 20: signals.append(("BUY", f"Stoch oversold ({stoch:.0f})")); score += 1
    elif stoch > 80: signals.append(("SELL", f"Stoch overbought ({stoch:.0f})")); score -= 1
    
    # S/R Proximity
    for level, cnt in s_clusters[:2]:
        if abs(close - level) / close < 0.02:
            signals.append(("BUY", f"Near support confluence ({level:.0f}, {cnt} methods)")); score += 1; break
    for level, cnt in r_clusters[:2]:
        if abs(close - level) / close < 0.02:
            signals.append(("SELL", f"Near resistance confluence ({level:.0f}, {cnt} methods)")); score -= 1; break
    
    # Volume
    if avg_vol > 0:
        ratio = vol / avg_vol
        if ratio > 2:
            if close > prev['Close']: signals.append(("STRONG_BUY", f"Vol spike {ratio:.1f}x + price up")); score += 2
            else: signals.append(("STRONG_SELL", f"Vol spike {ratio:.1f}x + price down")); score -= 2
        elif ratio > 1.5:
            if close > prev['Close']: signals.append(("BUY", f"Vol {ratio:.1f}x avg + price up")); score += 1
            else: signals.append(("SELL", f"Vol {ratio:.1f}x avg + price down")); score -= 1
    
    # 52W Position
    pos52 = (close - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else 50
    if pos52 < 10: signals.append(("BUY", f"At {pos52:.0f}% of 52W range")); score += 1
    elif pos52 > 90: signals.append(("SELL", f"At {pos52:.0f}% of 52W range")); score -= 1
    
    if score >= 5: overall = "STRONG_BUY"
    elif score >= 3: overall = "BUY"
    elif score >= 1: overall = "MILD_BUY"
    elif score <= -5: overall = "STRONG_SELL"
    elif score <= -3: overall = "SELL"
    elif score <= -1: overall = "MILD_SELL"
    else: overall = "NEUTRAL"
    
    return signals, score, overall

# ═══════════════════════════════════════════════════════════════
# SECTION 2: FUNDAMENTAL ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════

def analyze_fundamental(ticker, info):
    """Extract and analyze fundamental data"""
    data = {
        'name': info.get('shortName', ''),
        'sector': info.get('sector', 'N/A'),
        'industry': info.get('industry', 'N/A'),
        'market_cap': info.get('marketCap', 0) or 0,
        'pe': info.get('trailingPE', 0) or 0,
        'forward_pe': info.get('forwardPE', 0) or 0,
        'eps': info.get('trailingEps', 0) or 0,
        'forward_eps': info.get('forwardEps', 0) or 0,
        'pb': info.get('priceToBook', 0) or 0,
        'roe': info.get('returnOnEquity', 0) or 0,
        'debt_equity': info.get('debtToEquity', 0) or 0,
        'dy': (info.get('dividendYield', 0) or 0) * 100,
        'beta': info.get('beta', 0) or 0,
        'profit_margin': info.get('profitMargins', 0) or 0,
        'operating_margin': info.get('operatingMargins', 0) or 0,
        'revenue_growth': info.get('revenueGrowth', 0) or 0,
        'earnings_growth': info.get('earningsGrowth', 0) or 0,
        'target_price': info.get('targetMeanPrice', 0) or 0,
        'target_high': info.get('targetHighPrice', 0) or 0,
        'target_low': info.get('targetLowPrice', 0) or 0,
        'num_analysts': info.get('numberOfAnalystOpinions', 0) or 0,
        'recommendation': info.get('recommendationKey', 'N/A'),
        'hi52': info.get('fiftyTwoWeekHigh', 0) or 0,
        'lo52': info.get('fiftyTwoWeekLow', 0) or 0,
        'avg_vol': info.get('averageVolume', 0) or 0,
        'shares_outstanding': info.get('sharesOutstanding', 0) or 0,
        'book_value': info.get('bookValue', 0) or 0,
        'free_cashflow': info.get('freeCashflow', 0) or 0,
        'operating_cashflow': info.get('operatingCashflow', 0) or 0,
    }
    
    # Financials from yfinance
    try:
        fin = ticker.financials
        if fin is not None and not fin.empty:
            col = fin.columns[0]
            data['revenue_annual'] = fin.loc['Total Revenue', col] if 'Total Revenue' in fin.index else None
            data['gross_profit_annual'] = fin.loc['Gross Profit', col] if 'Gross Profit' in fin.index else None
            data['operating_income_annual'] = fin.loc['Operating Income', col] if 'Operating Income' in fin.index else None
            data['net_income_annual'] = fin.loc['Net Income', col] if 'Net Income' in fin.index else None
            data['ebitda_annual'] = fin.loc['EBITDA', col] if 'EBITDA' in fin.index else None
        else:
            data['revenue_annual'] = data['gross_profit_annual'] = data['operating_income_annual'] = data['net_income_annual'] = data['ebitda_annual'] = None
    except:
        data['revenue_annual'] = data['gross_profit_annual'] = data['operating_income_annual'] = data['net_income_annual'] = data['ebitda_annual'] = None
    
    # Balance Sheet
    try:
        bs = ticker.balance_sheet
        if bs is not None and not bs.empty:
            col = bs.columns[0]
            data['total_assets'] = bs.loc['Total Assets', col] if 'Total Assets' in bs.index else None
            data['total_debt'] = bs.loc['Total Debt', col] if 'Total Debt' in bs.index else None
            data['total_equity'] = bs.loc['Stockholders Equity', col] if 'Stockholders Equity' in bs.index else None
            data['cash'] = bs.loc['Cash And Cash Equivalents', col] if 'Cash And Cash Equivalents' in bs.index else None
        else:
            data['total_assets'] = data['total_debt'] = data['total_equity'] = data['cash'] = None
    except:
        data['total_assets'] = data['total_debt'] = data['total_equity'] = data['cash'] = None
    
    # Calculate derived metrics
    if data['revenue_annual'] and data['gross_profit_annual']:
        data['gross_margin'] = (data['gross_profit_annual'] / data['revenue_annual']) * 100
    else:
        data['gross_margin'] = None
    
    if data['revenue_annual'] and data['operating_income_annual']:
        data['operating_margin_calc'] = (data['operating_income_annual'] / data['revenue_annual']) * 100
    else:
        data['operating_margin_calc'] = None
    
    if data['revenue_annual'] and data['net_income_annual']:
        data['net_margin'] = (data['net_income_annual'] / data['revenue_annual']) * 100
    else:
        data['net_margin'] = None
    
    return data

# ═══════════════════════════════════════════════════════════════
# SECTION 3: ECONOMIC ANALYSIS ENGINE (Mikro & Makro)
# ═══════════════════════════════════════════════════════════════

def get_macro_data_from_browser():
    """
    Scrape real-time global macro data from Yahoo Finance.
    Returns dict with macro indicators.
    """
    macro = {}
    
    # IHSG
    try:
        ihsg = yf.Ticker("^JKSE")
        ihsg_info = ihsg.info
        ihsg_df = ihsg.history(period="5d")
        if not ihsg_df.empty:
            macro['ihsg_close'] = ihsg_df['Close'].iloc[-1]
            macro['ihsg_prev'] = ihsg_df['Close'].iloc[-2] if len(ihsg_df) > 1 else ihsg_df['Close'].iloc[-1]
            macro['ihsg_chg'] = ((macro['ihsg_close'] / macro['ihsg_prev']) - 1) * 100
            macro['ihsg_52w_high'] = ihsg_info.get('fiftyTwoWeekHigh', 0)
            macro['ihsg_52w_low'] = ihsg_info.get('fiftyTwoWeekLow', 0)
    except:
        macro['ihsg_close'] = macro['ihsg_chg'] = 0
    
    # S&P 500
    try:
        sp500 = yf.Ticker("^GSPC")
        sp500_df = sp500.history(period="5d")
        if not sp500_df.empty:
            macro['sp500_close'] = sp500_df['Close'].iloc[-1]
            macro['sp500_chg'] = ((sp500_df['Close'].iloc[-1] / sp500_df['Close'].iloc[-2]) - 1) * 100 if len(sp500_df) > 1 else 0
    except:
        macro['sp500_close'] = macro['sp500_chg'] = 0
    
    # Gold
    try:
        gold = yf.Ticker("GC=F")
        gold_df = gold.history(period="5d")
        if not gold_df.empty:
            macro['gold_close'] = gold_df['Close'].iloc[-1]
            macro['gold_chg'] = ((gold_df['Close'].iloc[-1] / gold_df['Close'].iloc[-2]) - 1) * 100 if len(gold_df) > 1 else 0
    except:
        macro['gold_close'] = macro['gold_chg'] = 0
    
    # Brent Oil
    try:
        oil = yf.Ticker("BZ=F")
        oil_df = oil.history(period="5d")
        if not oil_df.empty:
            macro['oil_close'] = oil_df['Close'].iloc[-1]
            macro['oil_chg'] = ((oil_df['Close'].iloc[-1] / oil_df['Close'].iloc[-2]) - 1) * 100 if len(oil_df) > 1 else 0
    except:
        macro['oil_close'] = macro['oil_chg'] = 0
    
    # Bitcoin
    try:
        btc = yf.Ticker("BTC-USD")
        btc_df = btc.history(period="5d")
        if not btc_df.empty:
            macro['btc_close'] = btc_df['Close'].iloc[-1]
            macro['btc_chg'] = ((btc_df['Close'].iloc[-1] / btc_df['Close'].iloc[-2]) - 1) * 100 if len(btc_df) > 1 else 0
    except:
        macro['btc_close'] = macro['btc_chg'] = 0
    
    # USD/IDR
    try:
        usd_idr = yf.Ticker("USDIDR=X")
        usd_idr_df = usd_idr.history(period="5d")
        if not usd_idr_df.empty:
            macro['usd_idr'] = usd_idr_df['Close'].iloc[-1]
            macro['usd_idr_chg'] = ((usd_idr_df['Close'].iloc[-1] / usd_idr_df['Close'].iloc[-2]) - 1) * 100 if len(usd_idr_df) > 1 else 0
    except:
        macro['usd_idr'] = macro['usd_idr_chg'] = 0
    
    # US 10Y Treasury
    try:
        us10y = yf.Ticker("^TNX")
        us10y_df = us10y.history(period="5d")
        if not us10y_df.empty:
            macro['us10y'] = us10y_df['Close'].iloc[-1]
            macro['us10y_chg'] = ((us10y_df['Close'].iloc[-1] / us10y_df['Close'].iloc[-2]) - 1) * 100 if len(us10y_df) > 1 else 0
    except:
        macro['us10y'] = macro['us10y_chg'] = 0
    
    # VIX
    try:
        vix = yf.Ticker("^VIX")
        vix_df = vix.history(period="5d")
        if not vix_df.empty:
            macro['vix'] = vix_df['Close'].iloc[-1]
            macro['vix_chg'] = ((vix_df['Close'].iloc[-1] / vix_df['Close'].iloc[-2]) - 1) * 100 if len(vix_df) > 1 else 0
    except:
        macro['vix'] = macro['vix_chg'] = 0
    
    return macro
    
def analyze_economic_context(sector, industry, close, market_cap, beta, revenue_growth, earnings_growth, pe, pb, roe, debt_equity, profit_margin, operating_margin, dy, avg_vol, vol, hi52, lo52, pos52, macro_data):
    """
    Analyze micro and macro economic context relevant to the stock.
    Uses real-time macro data from Yahoo Finance.
    Returns structured analysis text.
    """
    
    # Sector classification
    sector_outlook = {
        'Financial Services': {
            'cycle': 'Cyclical — tied to economic growth & interest rates',
            'drivers': 'BI rate policy, loan growth, NIM, NPL ratio, CAR',
            'risks': 'Credit risk, interest rate volatility, regulatory changes',
            'tailwinds': 'BI easing cycle (5.75%), digital banking adoption, financial inclusion',
            'headwinds': 'NPL pressure, fintech competition, margin compression',
        },
        'Communication Services': {
            'cycle': 'Defensive — recurring revenue from subscriptions',
            'drivers': 'ARPU, subscriber growth, data usage, 5G rollout',
            'risks': 'Regulatory changes, capex intensity, competition',
            'tailwinds': 'Digital transformation, data center/AI demand, broadband penetration',
            'headwinds': 'Legacy revenue decline, high capex, pricing pressure',
        },
        'Consumer Cyclical': {
            'cycle': 'Cyclical — tied to consumer spending',
            'drivers': 'Consumer confidence, disposable income, retail sales',
            'risks': 'Inflation, currency depreciation, competition',
            'tailwinds': 'MBG program, rising middle class, e-commerce growth',
            'headwinds': 'Input cost pressure, supply chain disruption',
        },
        'Consumer Defensive': {
            'cycle': 'Defensive — stable demand regardless of economic cycle',
            'drivers': 'Market share, pricing power, distribution network',
            'risks': 'Input cost inflation, regulatory changes',
            'tailwinds': 'Population growth, urbanization, brand loyalty',
            'headwinds': 'Commodity price volatility, competition',
        },
        'Energy': {
            'cycle': 'Cyclical — tied to commodity prices',
            'drivers': 'Oil & gas prices, production volume, reserves',
            'risks': 'Commodity price volatility, regulatory changes, ESG',
            'tailwinds': 'High oil prices ($90+), energy security focus',
            'headwinds': 'Energy transition, carbon tax, capex requirements',
        },
        'Basic Materials': {
            'cycle': 'Cyclical — tied to global commodity prices',
            'drivers': 'Commodity prices (coal, nickel, tin), production costs, FX',
            'risks': 'Commodity price volatility, China demand, regulatory changes',
            'tailwinds': 'Global infrastructure spending, EV battery demand (nickel)',
            'headwinds': 'China slowdown, environmental regulations',
        },
        'Healthcare': {
            'cycle': 'Defensive — stable demand regardless of economic cycle',
            'drivers': 'Population aging, healthcare spending, product pipeline',
            'risks': 'Regulatory changes, patent cliffs, competition',
            'tailwinds': 'Healthcare reform, rising awareness, demographic tailwind',
            'headwinds': 'Price controls, regulatory burden',
        },
        'Industrials': {
            'cycle': 'Cyclical — tied to economic growth & infrastructure spending',
            'drivers': 'Infrastructure spending, manufacturing activity, order book',
            'risks': 'Economic slowdown, input cost pressure, competition',
            'tailwinds': 'Government infrastructure program, Danantara SWF',
            'headwinds': 'Global slowdown, supply chain disruption',
        },
        'Technology': {
            'cycle': 'Growth — tied to digital adoption & innovation',
            'drivers': 'User growth, monetization, innovation, market share',
            'risks': 'Regulation, competition, technology disruption',
            'tailwinds': 'Digital transformation, AI adoption, e-commerce growth',
            'headwinds': 'Regulatory scrutiny, profitability challenges',
        },
        'Real Estate': {
            'cycle': 'Cyclical — tied to interest rates & economic growth',
            'drivers': 'Interest rates, property demand, occupancy rates, rental yields',
            'risks': 'Interest rate hikes, oversupply, regulatory changes',
            'tailwinds': 'BI easing cycle, urbanization, infrastructure development',
            'headwinds': 'High interest rates, property tax, oversupply in some segments',
        },
        'Utilities': {
            'cycle': 'Defensive — stable demand, regulated returns',
            'drivers': 'Regulatory framework, demand growth, operational efficiency',
            'risks': 'Regulatory changes, fuel cost, environmental regulations',
            'tailwinds': 'Electrification, renewable energy transition',
            'headwinds': 'Regulatory uncertainty, capex requirements',
        },
    }
    
    sector_info = sector_outlook.get(sector, {
        'cycle': 'Mixed — depends on specific industry dynamics',
        'drivers': 'Company-specific factors, industry trends, competitive position',
        'risks': 'Market competition, regulatory changes, macroeconomic factors',
        'tailwinds': 'Economic growth, digital transformation, government support',
        'headwinds': 'Global uncertainty, input cost pressure, competition',
    })
    
    mikro.append(f"**Business Cycle:** {sector_info['cycle']}")
    mikro.append(f"**Key Drivers:** {sector_info['drivers']}")
    mikro.append(f"**Sector Risks:** {sector_info['risks']}")
    mikro.append(f"**Tailwinds:** {sector_info['tailwinds']}")
    mikro.append(f"**Headwinds:** {sector_info['headwinds']}")
    
    # Company-specific micro analysis
    mikro.append("")
    mikro.append("**Company-Specific Factors:**")
    
    # Valuation assessment
    if pe > 0:
        if pe < 10:
            mikro.append(f"• Valuation: P/E {pe:.1f}x — **CHEAP** vs historical average. Market pricing in pessimism.")
        elif pe < 15:
            mikro.append(f"• Valuation: P/E {pe:.1f}x — **FAIR**. Reasonable for quality.")
        elif pe < 25:
            mikro.append(f"• Valuation: P/E {pe:.1f}x — **PREMIUM**. Market expects high growth.")
        else:
            mikro.append(f"• Valuation: P/E {pe:.1f}x — **EXPENSIVE**. High growth expectations priced in.")
    
    # Growth assessment
    if revenue_growth > 0.15:
        mikro.append(f"• Revenue Growth: {revenue_growth*100:.1f}% — **STRONG**. Above industry average.")
    elif revenue_growth > 0.05:
        mikro.append(f"• Revenue Growth: {revenue_growth*100:.1f}% — **MODERATE**. In-line with industry.")
    elif revenue_growth > 0:
        mikro.append(f"• Revenue Growth: {revenue_growth*100:.1f}% — **SLOW**. Below industry average.")
    elif revenue_growth < 0:
        mikro.append(f"• Revenue Growth: {revenue_growth*100:.1f}% — **DECLINING**. ⚠️ Red flag.")
    
    if earnings_growth > 0.15:
        mikro.append(f"• Earnings Growth: {earnings_growth*100:.1f}% — **STRONG**. Profit expanding.")
    elif earnings_growth > 0:
        mikro.append(f"• Earnings Growth: {earnings_growth*100:.1f}% — **POSITIVE**. Profit growing.")
    elif earnings_growth < -0.1:
        mikro.append(f"• Earnings Growth: {earnings_growth*100:.1f}% — **SHARP DECLINE**. ⚠️ Major concern.")
    elif earnings_growth < 0:
        mikro.append(f"• Earnings Growth: {earnings_growth*100:.1f}% — **DECLINING**. ⚠️ Watch closely.")
    
    # Profitability
    if roe > 0.20:
        mikro.append(f"• ROE: {roe*100:.1f}% — **EXCELLENT**. Top-tier profitability.")
    elif roe > 0.15:
        mikro.append(f"• ROE: {roe*100:.1f}% — **GOOD**. Above cost of equity.")
    elif roe > 0.10:
        mikro.append(f"• ROE: {roe*100:.1f}% — **ADEQUATE**. Acceptable return.")
    elif roe > 0:
        mikro.append(f"• ROE: {roe*100:.1f}% — **LOW**. Below cost of equity.")
    
    if profit_margin > 0.30:
        mikro.append(f"• Profit Margin: {profit_margin*100:.1f}% — **EXCELLENT**. Pricing power & efficiency.")
    elif profit_margin > 0.15:
        mikro.append(f"• Profit Margin: {profit_margin*100:.1f}% — **GOOD**. Healthy margins.")
    elif profit_margin > 0.05:
        mikro.append(f"• Profit Margin: {profit_margin*100:.1f}% — **THIN**. Competitive pressure.")
    elif profit_margin > 0:
        mikro.append(f"• Profit Margin: {profit_margin*100:.1f}% — **VERY THIN**. ⚠️ Vulnerable to cost shocks.")
    
    # Balance Sheet Strength
    if debt_equity == 0:
        mikro.append(f"• Balance Sheet: **ZERO DEBT**. Extremely strong financial position.")
    elif debt_equity < 30:
        mikro.append(f"• Balance Sheet: D/E {debt_equity:.1f} — **CONSERVATIVE**. Low leverage.")
    elif debt_equity < 60:
        mikro.append(f"• Balance Sheet: D/E {debt_equity:.1f} — **MODERATE**. Manageable leverage.")
    elif debt_equity < 100:
        mikro.append(f"• Balance Sheet: D/E {debt_equity:.1f} — **ELEVATED**. Monitor closely.")
    else:
        mikro.append(f"• Balance Sheet: D/E {debt_equity:.1f} — **HIGH LEVERAGE**. ⚠️ Risk in rising rate environment.")
    
    # Dividend
    if dy > 8:
        mikro.append(f"• Dividend Yield: {dy:.2f}% — **VERY HIGH**. Income play, but check sustainability.")
    elif dy > 5:
        mikro.append(f"• Dividend Yield: {dy:.2f}% — **ATTRACTIVE**. Good income component.")
    elif dy > 2:
        mikro.append(f"• Dividend Yield: {dy:.2f}% — **MODERATE**. Balanced growth & income.")
    elif dy > 0:
        mikro.append(f"• Dividend Yield: {dy:.2f}% — **LOW**. Growth-focused company.")
    
    # 52W Position
    if pos52 < 20:
        mikro.append(f"• 52W Position: {pos52:.0f}% — **NEAR BOTTOM**. Potential value opportunity if fundamentals intact.")
    elif pos52 < 40:
        mikro.append(f"• 52W Position: {pos52:.0f}% — **LOWER HALF**. Discounted from highs.")
    elif pos52 < 60:
        mikro.append(f"• 52W Position: {pos52:.0f}% — **MID-RANGE**. Fair value zone.")
    elif pos52 < 80:
        mikro.append(f"• 52W Position: {pos52:.0f}% — **UPPER HALF**. Approaching highs.")
    else:
        mikro.append(f"• 52W Position: {pos52:.0f}% — **NEAR TOP**. Overbought risk.")
    
    # Volume analysis
    if avg_vol > 0:
        vol_ratio = vol / avg_vol
        if vol_ratio > 2:
            mikro.append(f"• Volume: {vol_ratio:.1f}x average — **SPIKE**. Institutional activity detected.")
        elif vol_ratio > 1.5:
            mikro.append(f"• Volume: {vol_ratio:.1f}x average — **ABOVE NORMAL**. Increased interest.")
        elif vol_ratio < 0.5:
            mikro.append(f"• Volume: {vol_ratio:.1f}x average — **LOW**. Lack of interest/liquidity.")
    
    # ═══ MAKRO: Economic Context (Real-time Data) ═══
    makro = []
    
    ihsg = macro_data.get('ihsg_close', 0)
    ihsg_chg = macro_data.get('ihsg_chg', 0)
    sp500_chg = macro_data.get('sp500_chg', 0)
    gold_close = macro_data.get('gold_close', 0)
    gold_chg = macro_data.get('gold_chg', 0)
    oil_close = macro_data.get('oil_close', 0)
    oil_chg = macro_data.get('oil_chg', 0)
    btc_close = macro_data.get('btc_close', 0)
    btc_chg = macro_data.get('btc_chg', 0)
    usd_idr = macro_data.get('usd_idr', 0)
    us10y = macro_data.get('us10y', 0)
    vix = macro_data.get('vix', 0)
    vix_chg = macro_data.get('vix_chg', 0)
    
    makro.append("**Indonesia Macro (Real-time):**")
    if ihsg:
        makro.append(f"• IHSG: {ihsg:,.2f} ({ihsg_chg:+.2f}%)")
    makro.append("• BI Rate: 5.75% (easing cycle from 6.00%)")
    makro.append("• GDP Growth 2026P: ~5.0-5.2%")
    makro.append("• Inflation: ~2.5-3.0% (within BI target 2.5%±1%)")
    makro.append("• Fiscal Deficit: ~2.5% GDP (below 3% legal limit)")
    makro.append("• Government Programs: MBG, Danantara SWF (Rp 1,000T), KUR subsidies")
    if usd_idr:
        makro.append(f"• Rupiah: Rp {usd_idr:,.0f}/USD")
    else:
        makro.append("• Rupiah: ~16,500-17,000 vs USD")
    
    makro.append("")
    makro.append("**Global Macro (Real-time):**")
    if sp500_chg:
        makro.append(f"• S&P 500: {sp500_chg:+.2f}%")
    if vix:
        vix_str = f"VIX: {vix:.2f}"
        if vix_chg:
            vix_str += f" ({vix_chg:+.2f}%)"
        if vix > 25:
            vix_str += " 🔴 HIGH FEAR"
        elif vix > 20:
            vix_str += " 🟡 ELEVATED"
        else:
            vix_str += " 🟢 LOW"
        makro.append(f"• {vix_str}")
    if gold_close:
        gold_str = f"Gold: ${gold_close:,.2f}"
        if gold_chg:
            gold_str += f" ({gold_chg:+.2f}%)"
        makro.append(f"• {gold_str}")
    if oil_close:
        oil_str = f"Brent Oil: ${oil_close:.2f}"
        if oil_chg:
            oil_str += f" ({oil_chg:+.2f}%)"
        makro.append(f"• {oil_str}")
    if btc_close:
        btc_str = f"Bitcoin: ${btc_close:,.2f}"
        if btc_chg:
            btc_str += f" ({btc_chg:+.2f}%)"
        makro.append(f"• {btc_str}")
    if us10y:
        makro.append(f"• US 10Y Treasury: {us10y:.2f}%")
    
    makro.append("")
    makro.append("**Macro Events to Watch:**")
    makro.append("• Fed Policy: Rate cut expectations for H2 2026")
    makro.append("• China Growth: ~4.5-5.0% (moderate slowdown)")
    makro.append("• US-China: Trade tensions, supply chain diversification benefits ASEAN")
    makro.append("• AI/Tech: Global capex boom benefits data center & telecom")
    
    # Macro impact on sector
    makro.append("")
    makro.append(f"**Macro Impact on {sector}:**")
    
    if sector == 'Financial Services':
        makro.append("• BI Rate Cut → NIM pressure but loan growth acceleration")
        makro.append("• Economic recovery → lower NPL, higher credit demand")
        makro.append("• Fiscal expansion → infrastructure lending opportunities")
        makro.append("• Rupiah stability → reduced FX risk for banks")
    elif sector == 'Communication Services':
        makro.append("• Economic growth → higher ARPU & data consumption")
        makro.append("• AI/Data Center boom → new revenue stream for telcos")
        makro.append("• 5G rollout → capex intensity but long-term growth")
        makro.append("• Digital transformation → structural tailwind")
    elif sector in ['Energy', 'Basic Materials']:
        makro.append("• Oil price $90+ → strong earnings for energy/mining")
        makro.append("• China demand → key driver for commodity prices")
        makro.append("• Global infrastructure spending → supports materials demand")
        makro.append("• Energy transition → long-term structural shift")
    elif sector in ['Consumer Cyclical', 'Consumer Defensive']:
        makro.append("• MBG program → boosts consumer spending")
        makro.append("• Inflation control → preserves purchasing power")
        makro.append("• Rupiah stability → reduces input cost pressure")
        makro.append("• Economic growth → higher consumer confidence")
    else:
        makro.append("• Economic growth → supports demand")
        makro.append("• BI easing → lower financing costs")
        makro.append("• Fiscal expansion → infrastructure & consumption boost")
        makro.append("• Global uncertainty → monitor for spillover effects")
    
    return mikro, makro

# ═══════════════════════════════════════════════════════════════
# SECTION 4: MAIN ANALYSIS PIPELINE
# ═══════════════════════════════════════════════════════════════

def run_analysis(ticker_str, period="6mo"):
    """Run complete analysis pipeline"""
    
    print(f"\n{'='*70}")
    print(f"  COMPLETE ANALYSIS: {ticker_str}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # Fetch data
    ticker = yf.Ticker(ticker_str)
    df = ticker.history(period="1y")
    df6 = ticker.history(period=period)
    info = ticker.info
    
    if df.empty:
        print(f"ERROR: No data for {ticker_str}")
        return None
    
    close = df6.iloc[-1]['Close']
    prev_close = df6.iloc[-2]['Close']
    chg_pct = ((close / prev_close) - 1) * 100
    
    # ═══ 1. TECHNICAL ANALYSIS ═══
    df6_ind = compute_indicators(df6)
    latest = df6_ind.iloc[-1]
    prev = df6_ind.iloc[-2]
    
    sr = compute_support_resistance(df6_ind, df6_ind)
    signals, score, overall = detect_signals(
        latest, prev, close, info.get('averageVolume', 0) or 0,
        info.get('fiftyTwoWeekHigh', 0) or df['High'].max(),
        info.get('fiftyTwoWeekLow', 0) or df['Low'].min(),
        sr['s_clusters'], sr['r_clusters']
    )
    
    # ═══ 2. FUNDAMENTAL ANALYSIS ═══
    fund = analyze_fundamental(ticker, info)
    
    # ═══ 3. ECONOMIC ANALYSIS ═══
    macro_data = get_macro_data_from_browser()
    makro_indicators = {k: v for k, v in macro_data.items() if v}
    
    mikro, makro = analyze_economic_context(
        fund['sector'], fund['industry'], close, fund['market_cap'],
        fund['beta'], fund['revenue_growth'], fund['earnings_growth'],
        fund['pe'], fund['pb'], fund['roe'], fund['debt_equity'],
        fund['profit_margin'], fund['operating_margin'], fund['dy'],
        fund['avg_vol'], latest['Volume'], fund['hi52'], fund['lo52'],
        (close - fund['lo52']) / (fund['hi52'] - fund['lo52']) * 100 if fund['hi52'] > fund['lo52'] else 50,
        macro_data
    )
    
    # ═══ 4. PERFORMANCE ═══
    def safe_pct(cur, past):
        return ((cur / past) - 1) * 100 if past else 0
    
    perf = {
        '1w': safe_pct(close, df6['Close'].iloc[-5]) if len(df6) >= 5 else 0,
        '1m': safe_pct(close, df6['Close'].iloc[-21]) if len(df6) >= 21 else 0,
        '3m': safe_pct(close, df6['Close'].iloc[-63]) if len(df6) >= 63 else 0,
        '6m': safe_pct(close, df6['Close'].iloc[0]),
        'ytd': safe_pct(close, df6[df6.index >= f'{datetime.now().year}-01-01']['Close'].iloc[0]) if len(df6[df6.index >= f'{datetime.now().year}-01-01']) > 1 else 0,
        '1y': safe_pct(close, df['Close'].iloc[0]),
    }
    
    # IHSG comparison
    try:
        ihsg = yf.Ticker("^JKSE")
        ihsg_df = ihsg.history(period=period)
        ihsg_perf = safe_pct(ihsg_df['Close'].iloc[-1], ihsg_df['Close'].iloc[0]) if len(ihsg_df) > 1 else 0
        alpha = perf['6m'] - ihsg_perf
    except:
        ihsg_perf = 0; alpha = 0
    
    # ═══ 5. TRADE PLAN ═══
    if score > 0:
        entry_low = max(sr['s1'], latest['BB_Lower'] * 1.01)
        entry_high = min(sr['r1'], sr['pivot'])
    else:
        entry_low = max(sr['s1'], latest['BB_Lower'])
        entry_high = sr['pivot']
    stop_loss = min(sr['s2'], latest['BB_Lower'] * (0.99 if score > 0 else 0.98))
    
    # ═══ OUTPUT ═══
    print(f"\n{'─'*70}")
    print(f"  📊 {ticker_str} — {fund['name']}")
    print(f"  Harga: Rp {close:,.2f} ({chg_pct:+.2f}%) | {fund['sector']} | {fund['industry']}")
    print(f"{'─'*70}")
    
    print(f"\n  ═══ I. FUNDAMENTAL ═══")
    print(f"  Market Cap: Rp {fund['market_cap']/1e12:.2f}T")
    print(f"  P/E: {fund['pe']:.2f}x | Fwd P/E: {fund['forward_pe']:.2f}x")
    print(f"  EPS: Rp {fund['eps']:.2f} | Fwd EPS: Rp {fund['forward_eps']:.2f}")
    print(f"  P/B: {fund['pb']:.2f}x | ROE: {fund['roe']*100:.1f}% | D/E: {fund['debt_equity']:.1f}")
    print(f"  Div Yield: {fund['dy']:.2f}% | Beta: {fund['beta']:.2f}")
    print(f"  Profit Margin: {fund['profit_margin']*100:.1f}% | Op Margin: {fund['operating_margin']*100:.1f}%")
    print(f"  Revenue Growth: {fund['revenue_growth']*100:.1f}% | Earnings Growth: {fund['earnings_growth']*100:.1f}%")
    if fund['target_price']:
        print(f"  Analyst Target: Rp {fund['target_price']:,.0f} (Low: {fund['target_low']:,.0f}, High: {fund['target_high']:,.0f})")
        print(f"  # Analysts: {fund['num_analysts']} | Consensus: {fund['recommendation']}")
    if fund['revenue_annual']:
        print(f"  Revenue (Annual): Rp {fund['revenue_annual']/1e12:.2f}T")
    if fund['net_income_annual']:
        print(f"  Net Income (Annual): Rp {fund['net_income_annual']/1e12:.2f}T")
    if fund.get('gross_margin'):
        print(f"  Gross Margin: {fund['gross_margin']:.1f}%")
    if fund.get('net_margin'):
        print(f"  Net Margin: {fund['net_margin']:.1f}%")
    
    print(f"\n  ═══ II. PERFORMANCE ═══")
    print(f"  1W: {perf['1w']:+.1f}% | 1M: {perf['1m']:+.1f}% | 3M: {perf['3m']:+.1f}%")
    print(f"  6M: {perf['6m']:+.1f}% | YTD: {perf['ytd']:+.1f}% | 1Y: {perf['1y']:+.1f}%")
    print(f"  IHSG 6M: {ihsg_perf:+.1f}% | Alpha vs IHSG: {alpha:+.1f}%")
    print(f"  52W: {fund['lo52']:,.0f} — {fund['hi52']:,.0f} (posisi: {(close-fund['lo52'])/(fund['hi52']-fund['lo52'])*100:.0f}%)")
    
    print(f"\n  ═══ III. TECHNICAL ═══")
    print(f"  RSI: {latest['RSI']:.0f} | MACD: {latest['MACD']:.1f} (Sig: {latest['MACD_Signal']:.1f})")
    print(f"  SMA20: {latest['SMA_20']:,.0f} | SMA50: {latest['SMA_50']:,.0f} | SMA200: {latest['SMA_200']:,.0f}")
    print(f"  BB: U={latest['BB_Upper']:,.0f} M={latest['BB_Mid']:,.0f} L={latest['BB_Lower']:,.0f}")
    print(f"  Stoch: {latest['Stoch_K']:.0f} | ATR: {latest['ATR']:,.0f}")
    
    print(f"\n  ═══ IV. SUPPORT & RESISTANCE ═══")
    print(f"  Pivot: R3={sr['r3']:,.0f} R2={sr['r2']:,.0f} R1={sr['r1']:,.0f} P={sr['pivot']:,.0f} S1={sr['s1']:,.0f} S2={sr['s2']:,.0f} S3={sr['s3']:,.0f}")
    fib_str = ' | '.join([f'{k}={v:,.0f}' for k, v in sr['fib'].items()])
    print(f"  Fib: {fib_str}")
    print(f"  POC: {sr['vp']['poc']:,.0f} | HVN: {', '.join([f'{p:,.0f}' for p,_ in sr['vp']['hvn']])}")
    sh_str = ', '.join([f'{p:,.0f}' for _,p in sr['recent_sh']])
    sl_str = ', '.join([f'{p:,.0f}' for _,p in sr['recent_sl']])
    print(f"  Swing Highs: {sh_str} | Swing Lows: {sl_str}")
    if sr['r_clusters']:
        print(f"  Res Confluence: {', '.join([f'{l:,.0f}({c}x)' for l,c in sr['r_clusters']])}")
    if sr['s_clusters']:
        print(f"  Sup Confluence: {', '.join([f'{l:,.0f}({c}x)' for l,c in sr['s_clusters']])}")
    
    print(f"\n  ═══ V. SIGNALS (Score: {score}) ═══")
    print(f"  OVERALL: {overall}")
    for sig, reason in signals:
        print(f"    [{sig}] {reason}")
    
    print(f"\n  ═══ VI. TRADE PLAN ═══")
    sl_pct = ((stop_loss/close)-1)*100
    print(f"  Entry: {entry_low:,.0f} — {entry_high:,.0f}")
    print(f"  Stop Loss: {stop_loss:,.0f} ({sl_pct:.1f}%)")
    print(f"  Target 1: {sr['r1']:,.0f} (+{((sr['r1']/close)-1)*100:.1f}%)")
    print(f"  Target 2: {sr['r2']:,.0f} (+{((sr['r2']/close)-1)*100:.1f}%)")
    print(f"  Target 3: {fund['hi52']:,.0f} (+{((fund['hi52']/close)-1)*100:.1f}%)")
    if fund['target_price']:
        print(f"  Analyst Target: {fund['target_price']:,.0f} (+{((fund['target_price']/close)-1)*100:.1f}%)")
    
    print(f"\n  ═══ VII. EKONOMI MIKRO ═══")
    for line in mikro:
        print(f"  {line}")
    
    print(f"\n  ═══ VIII. EKONOMI MAKRO (Real-time) ═══")
    for line in makro:
        print(f"  {line}")
    
    # Print real-time macro summary
    if macro_data.get('ihsg_close'):
        print(f"\n  📊 Macro Snapshot:")
        if macro_data.get('ihsg_chg'):
            print(f"    IHSG: {macro_data['ihsg_close']:,.2f} ({macro_data['ihsg_chg']:+.2f}%)")
        if macro_data.get('sp500_chg'):
            print(f"    S&P 500: {macro_data['sp500_chg']:+.2f}%")
        if macro_data.get('vix'):
            print(f"    VIX: {macro_data['vix']:.2f} ({macro_data.get('vix_chg', 0):+.2f}%)")
        if macro_data.get('gold_close'):
            print(f"    Gold: ${macro_data['gold_close']:,.2f} ({macro_data.get('gold_chg', 0):+.2f}%)")
        if macro_data.get('oil_close'):
            print(f"    Brent: ${macro_data['oil_close']:.2f} ({macro_data.get('oil_chg', 0):+.2f}%)")
        if macro_data.get('btc_close'):
            print(f"    BTC: ${macro_data['btc_close']:,.2f} ({macro_data.get('btc_chg', 0):+.2f}%)")
        if macro_data.get('usd_idr'):
            print(f"    USD/IDR: Rp {macro_data['usd_idr']:,.0f}")
        if macro_data.get('us10y'):
            print(f"    US 10Y: {macro_data['us10y']:.2f}%")
    
    print(f"\n{'='*70}")
    print(f"  DONE: {ticker_str}")
    print(f"{'='*70}\n")
    
    return {
        'ticker': ticker_str, 'name': fund['name'], 'close': close, 'chg_pct': chg_pct,
        'fundamental': fund, 'technical': latest.to_dict(), 'sr': sr,
        'signals': signals, 'score': score, 'overall': overall,
        'perf': perf, 'ihsg_perf': ihsg_perf, 'alpha': alpha,
        'mikro': mikro, 'makro': makro,
        'trade': {
            'entry_low': entry_low, 'entry_high': entry_high,
            'stop_loss': stop_loss, 'target_1': sr['r1'], 'target_2': sr['r2'], 'target_3': fund['hi52'],
        }
    }

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BBRI.JK"
    period = sys.argv[2] if len(sys.argv) > 2 else "6mo"
    result = run_analysis(ticker, period)
    if not result:
        print(f"ERROR: {ticker}"); sys.exit(1)
