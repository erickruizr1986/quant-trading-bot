import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

API_KEY = None

# -----------------------------
# PARÁMETROS (OPTIMIZABLES)
# -----------------------------
BREAKOUT_WINDOW = 15
THRESHOLD = 3
VOL_MULT = 1.5


# -----------------------------
# DATA
# -----------------------------
def get_data(symbol, tf):

    timespan = "hour" if tf == "hour" else "day"

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/2025-01-01/2026-12-31?adjusted=true&sort=desc&limit=200&apiKey={API_KEY}"

    r = requests.get(url).json()

    if "results" not in r:
        return None

    df = pd.DataFrame(r["results"]).sort_values("t")

    df["close"] = df["c"]
    df["volume"] = df["v"]

    return df


# -----------------------------
# INDICADORES
# -----------------------------
def add_ind(df):
    df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
    df["ema40"] = EMAIndicator(df["close"], 40).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()
    return df


# -----------------------------
# VOLATILIDAD
# -----------------------------
def calc_volatility(df):
    return df["close"].pct_change().rolling(20).std().iloc[-1]


# -----------------------------
# OPCIÓN SIMULADA PRO
# -----------------------------
def simulate_option(price, direction, vol):

    strike = round(price)

    if direction == "CALL":
        strike -= 1
        moneyness = (price - strike) / price
    else:
        strike += 1
        moneyness = (strike - price) / price

    delta = 0.3 + (moneyness * 5)
    delta = max(0.3, min(delta, 0.6))

    premium = max(0.8, price * vol * VOL_MULT)

    expected_move = price * (vol * 1.5)

    gain = expected_move * delta

    future_price = premium + gain

    roi = (future_price - premium) / premium * 100

    return {
        "strike": strike,
        "premium": round(premium, 2),
        "delta": round(delta, 2),
        "roi": round(roi, 2)
    }


# -----------------------------
# SIGNAL
# -----------------------------
def signal(symbol):

    h1 = get_data(symbol, "hour")
    d1 = get_data(symbol, "day")

    if h1 is None or d1 is None:
        return None

    h1 = add_ind(h1)
    d1 = add_ind(d1)

    last = h1.iloc[-2]

    score = 0

    # tendencia
    if d1["ema20"].iloc[-1] > d1["ema40"].iloc[-1]:
        score += 2
    else:
        score -= 2

    # breakout dinámico
    high = h1["close"].iloc[-BREAKOUT_WINDOW:].max()
    low = h1["close"].iloc[-BREAKOUT_WINDOW:].min()

    if last["close"] > high:
        score += 2
    if last["close"] < low:
        score -= 2

    # RSI
    if 50 <= last["rsi"] <= 70:
        score += 1
    if 30 <= last["rsi"] <= 50:
        score -= 1

    print(f"{symbol} SCORE: {score}")

    if abs(score) < THRESHOLD:
        return None

    direction = "CALL" if score > 0 else "PUT"

    vol = calc_volatility(h1)

    option = simulate_option(last["close"], direction, vol)

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(last["close"], 2),
        "score": score,
        "strike": option["strike"],
        "premium": option["premium"],
        "roi": option["roi"],
        "delta": option["delta"],
    }
