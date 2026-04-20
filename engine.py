import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

API_KEY = None  # se setea desde main.py


# -----------------------------
# DATA
# -----------------------------
def get_data(symbol, tf):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{tf}/2023-01-01/2026-01-01?apiKey={API_KEY}"
    r = requests.get(url).json()

    if 'results' not in r:
        return None

    df = pd.DataFrame(r['results'])
    df['close'] = df['c']
    df['volume'] = df['v']

    return df


# -----------------------------
# INDICADORES
# -----------------------------
def add_ind(df):
    df['ema20'] = EMAIndicator(df['close'], 20).ema_indicator()
    df['ema40'] = EMAIndicator(df['close'], 40).ema_indicator()
    df['ema100'] = EMAIndicator(df['close'], 100).ema_indicator()
    df['ema200'] = EMAIndicator(df['close'], 200).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], 14).rsi()

    return df


# -----------------------------
# VIX
# -----------------------------
def vix_trend():
    v = get_data("VIX", "day")

    if v is None or len(v) < 6:
        return 0

    return v['close'].iloc[-1] - v['close'].iloc[-5]


# -----------------------------
# MOTOR DE SEÑALES
# -----------------------------
def signal(symbol):

    h1 = get_data(symbol, "hour")
    d1 = get_data(symbol, "day")

    if h1 is None or d1 is None:
        return None

    h1 = add_ind(h1)
    d1 = add_ind(d1)

    last = h1.iloc[-1]
    prev = h1.iloc[-2]

    score = 0

    # -----------------------------
    # TENDENCIA DIARIA
    # -----------------------------
    daily_up = (
        d1['ema20'].iloc[-1] > d1['ema40'].iloc[-1] >
        d1['ema100'].iloc[-1]
    )

    if daily_up:
        score += 2
    else:
        score -= 2

    # -----------------------------
    # BREAKOUT
    # -----------------------------
    high = h1['close'].iloc[-15:].max()
    low = h1['close'].iloc[-15:].min()

    if last['close'] > high:
        score += 2

    if last['close'] < low:
        score -= 2

    # -----------------------------
    # VOLUMEN
    # -----------------------------
    vol_mean = h1['volume'].rolling(20).mean().iloc[-1]

    if last['volume'] > vol_mean:
        score += 1

    # -----------------------------
    # RSI (momentum)
    # -----------------------------
    if 50 <= last['rsi'] <= 70:
        score += 1

    if 30 <= last['rsi'] <= 50:
        score -= 1

    # -----------------------------
    # VIX
    # -----------------------------
    vix = vix_trend()

    if vix < 1:
        score += 1
    if vix > 1:
        score -= 1

    # -----------------------------
    # DEBUG (VER EN LOGS)
    # -----------------------------
    print(f"{symbol} | score: {score} | price: {round(last['close'],2)}")

    # -----------------------------
    # DIRECCIÓN
    # -----------------------------
    direction = "CALL" if score > 0 else "PUT"

    # -----------------------------
    # FILTRO FINAL
    # -----------------------------
    if abs(score) >= 4:
        return {
            "symbol": symbol,
            "direction": direction,
            "price": float(round(last['close'], 2)),
            "score": float(score)
        }

    return None
