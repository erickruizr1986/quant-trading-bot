import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz

API_KEY = None


# -----------------------------
# DATA
# -----------------------------
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
    return df


# -----------------------------
# HORARIO NY
# -----------------------------
def valid_session():

    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)

    h = now.hour
    m = now.minute

    return (h > 9 or (h == 9 and m >= 30)) and h < 16


# -----------------------------
# VIX
# -----------------------------
def get_vix():

    vix = get_data("VIX", "day")

    if vix is None or len(vix) < 5:
        return 0

    return round(vix["close"].iloc[-1] - vix["close"].iloc[-5], 2)


# -----------------------------
# OPTIONS
# -----------------------------
def get_options_chain(symbol):

    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={symbol}&limit=50&apiKey={API_KEY}"

    r = requests.get(url).json()

    return r.get("results", [])


def select_contract(chain, price, direction):

    best = None
    min_diff = 999

    for c in chain:
        try:
            strike = float(c["strike_price"])
            typ = c["contract_type"]

            if direction == "CALL" and typ != "call":
                continue
            if direction == "PUT" and typ != "put":
                continue

            diff = abs(strike - price)

            if diff < min_diff:
                min_diff = diff
                best = c

        except:
            continue

    if not best:
        return None

    return {
        "strike": best["strike_price"],
        "expiry": best["expiration_date"]
    }


# -----------------------------
# TAKE PROFIT DINÁMICO
# -----------------------------
def dynamic_tp(score, prob):

    tp = 0.5

    if abs(score) >= 5:
        tp += 0.2
    elif abs(score) == 4:
        tp += 0.1
    else:
        tp -= 0.1

    if prob > 0.7:
        tp += 0.1
    elif prob < 0.6:
        tp -= 0.1

    tp = max(0.25, min(tp, 1.0))

    return int(tp * 100)


# -----------------------------
# SIGNAL
# -----------------------------
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

    if d1["ema20"].iloc[-1] > d1["ema40"].iloc[-1]:
        score += 2
        direction = "CALL"
    elif d1["ema20"].iloc[-1] < d1["ema40"].iloc[-1]:
        score -= 2
        direction = "PUT"
    else:
        return None

    high = h1["close"].iloc[-15:].max()
    low = h1["close"].iloc[-15:].min()

    if last["close"] > high:
        score += 2
    elif last["close"] < low:
        score -= 2
    else:
        return None

    if last["volume"] < h1["volume"].rolling(20).mean().iloc[-1]:
        return None

    if 50 <= last["rsi"] <= 70:
        score += 1
    elif 30 <= last["rsi"] <= 50:
        score -= 1

    if abs(score) < 3:
        return None

    chain = get_options_chain(symbol)
    contract = select_contract(chain, last["close"], direction)

    if not contract:
        return None

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(last["close"], 2),
        "score": score,
        "strike": contract["strike"],
        "expiry": contract["expiry"],
        "premium": 1.2,
        "vix": get_vix()
    }
