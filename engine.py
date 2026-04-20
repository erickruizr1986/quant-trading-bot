import requests, pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

API_KEY = None  # se setea desde main

def get_data(symbol, tf):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{tf}/2023-01-01/2026-01-01?apiKey={API_KEY}"
    r = requests.get(url).json()
    if 'results' not in r: return None
    df = pd.DataFrame(r['results'])
    df['close'] = df['c']; df['volume'] = df['v']
    return df

def add_ind(df):
    df['ema20'] = EMAIndicator(df['close'], 20).ema_indicator()
    df['ema40'] = EMAIndicator(df['close'], 40).ema_indicator()
    df['ema100'] = EMAIndicator(df['close'], 100).ema_indicator()
    df['ema200'] = EMAIndicator(df['close'], 200).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], 14).rsi()
    return df

def vix_trend():
    v = get_data("VIX", "day")
    if v is None or len(v) < 6: return 0
    return v['close'].iloc[-1] - v['close'].iloc[-5]

def signal(symbol):
    h1 = get_data(symbol, "hour")
    d1 = get_data(symbol, "day")
    if h1 is None or d1 is None: return None

    h1 = add_ind(h1); d1 = add_ind(d1)
    last, prev = h1.iloc[-1], h1.iloc[-2]

    # bias diario
    daily_up = d1['ema20'].iloc[-1] > d1['ema40'].iloc[-1] > d1['ema100'].iloc[-1]

    # breakout 20 velas + volumen
    high = h1['close'].iloc[-20:].max()
    low  = h1['close'].iloc[-20:].min()
    vol_ok = last['volume'] > h1['volume'].rolling(20).mean().iloc[-1]

    vix = vix_trend()

    score = 0; direction = None

    # CALL
    if last['close'] > high and vol_ok and daily_up and vix <= 0:
        score += 6
        if 50 <= last['rsi'] <= 65: score += 1
        if last['ema20'] > last['ema40']: score += 1
        direction = "CALL"

    # PUT
    if last['close'] < low and vol_ok and (not daily_up) and vix >= 0:
        score += 6
        if 35 <= last['rsi'] <= 50: score += 1
        if last['ema20'] < last['ema40']: score += 1
        direction = "PUT"

    if direction and score >= 6:
        return {
            "symbol": symbol,
            "direction": direction,
            "price": float(round(last['close'], 2)),
            "score": float(score)
        }
    return None
