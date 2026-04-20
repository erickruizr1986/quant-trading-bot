import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz

API_KEY = None


def get_data(symbol, tf):

    timespan = "hour" if tf == "hour" else "day"

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/2025-01-01/2026-12-31?adjusted=true&sort=desc&limit=150&apiKey={API_KEY}"

    r = requests.get(url).json()

    if "results" not in r:
        return None

    df = pd.DataFrame(r["results"]).sort_values("t")

    df["close"] = df["c"]
    df["open"] = df["o"]
    df["high"] = df["h"]
    df["low"] = df["l"]
    df["volume"] = df["v"]

    return df


def add_ind(df):
    df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
    df["ema40"] = EMAIndicator(df["close"], 40).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    return df


def get_vix_trend():

    vix = get_data("VIX", "day")

    if vix is None or len(vix) < 5:
        return 0

    return vix["close"].iloc[-1] - vix["close"].iloc[-5]


def valid_session():

    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)

    hour = now.hour
    minute = now.minute

    if (hour > 9 or (hour == 9 and minute >= 30)) and hour < 16:
        return True

    return False


def simulate_option(price, direction):

    strike = round(price)

    if direction == "CALL":
        strike -= 1
        delta = 0.4
    else:
        strike += 1
        delta = 0.4

    premium = 1.2
    expected_move = price * 0.003

    gain = expected_move * delta
    roi = (gain / premium) * 100

    return strike, premium, delta, round(roi, 2)


def signal(symbol):

    if not valid_session():
        return None

    h1 = get_data(symbol, "hour")
    d1 = get_data(symbol, "day")

    if h1 is None or d1 is None:
        return None

    h1 = add_ind(h1)
    d1 = add_ind(d1)

    last = h1.iloc[-2]

    score = 0

    # tendencia
    ema_slope = d1["ema20"].iloc[-1] - d1["ema20"].iloc[-5]

    if d1["ema20"].iloc[-1] > d1["ema40"].iloc[-1] and ema_slope > 0:
        score += 2
    elif d1["ema20"].iloc[-1] < d1["ema40"].iloc[-1] and ema_slope < 0:
        score -= 2
    else:
        return None

    # breakout
    high = h1["close"].iloc[-15:].max()
    low = h1["close"].iloc[-15:].min()

    if last["close"] > high:
        score += 2
    elif last["close"] < low:
        score -= 2
    else:
        return None

    # volumen
    vol_mean = h1["volume"].rolling(20).mean().iloc[-1]
    if last["volume"] < vol_mean:
        return None

    # RSI
    if 50 <= last["rsi"] <= 70:
        score += 1
    elif 30 <= last["rsi"] <= 50:
        score -= 1

    # VIX
    vix = get_vix_trend()
    if vix < -1:
        score += 1
    elif vix > 1:
        score -= 1

    print(f"{symbol} SCORE: {score}")

    if abs(score) < 3:
        return None

    direction = "CALL" if score > 0 else "PUT"

    strike, premium, delta, roi = simulate_option(last["close"], direction)

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(last["close"], 2),
        "score": score,
        "type": "PRO",
        "strike": strike,
        "premium": premium,
        "delta": delta,
        "roi": roi
    }
