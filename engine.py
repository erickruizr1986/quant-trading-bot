import requests
import pandas as pd
import math
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

API_KEY = None


# -----------------------------
# DATA
# -----------------------------
def get_data(symbol, tf):

    timespan = "hour" if tf == "hour" else "day"

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/2025-01-01/2026-12-31?adjusted=true&sort=desc&limit=100&apiKey={API_KEY}"

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
    df["ema100"] = EMAIndicator(df["close"], 100).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()
    return df


# -----------------------------
# OPTIONS CHAIN
# -----------------------------
def get_option_chain(symbol):

    url = f"https://api.polygon.io/v2/snapshot/options/{symbol}?apiKey={API_KEY}"
    r = requests.get(url).json()

    if "results" not in r:
        return None

    return r["results"]


# -----------------------------
# SELECCIÓN DE OPCIÓN
# -----------------------------
def pick_best_option(chain, price, direction):

    best = None
    best_score = 0

    for opt in chain:
        try:
            strike = opt["details"]["strike_price"]
            delta = opt["greeks"]["delta"]
            premium = opt["last_trade"]["price"]
            volume = opt["day"]["volume"]

            if premium < 0.3 or volume < 50:
                continue

            score = 0

            if direction == "CALL":
                if 0.3 < delta < 0.6:
                    score += 2
                if strike <= price:
                    score += 1

            if direction == "PUT":
                if -0.6 < delta < -0.3:
                    score += 2
                if strike >= price:
                    score += 1

            if score > best_score:
                best_score = score
                best = opt

        except:
            continue

    return best


# -----------------------------
# NORMAL CDF
# -----------------------------
def norm_cdf(x):
    return (1 + math.erf(x / math.sqrt(2))) / 2


# -----------------------------
# BLACK-SCHOLES
# -----------------------------
def black_scholes(S, K, T, r, sigma, call=True):

    if T <= 0:
        return 0

    d1 = (math.log(S / K) + (r + sigma**2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if call:
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


# -----------------------------
# ESTIMACIÓN
# -----------------------------
def estimate(price, option, direction):

    strike = option["details"]["strike_price"]
    premium = option["last_trade"]["price"]
    delta = abs(option["greeks"]["delta"])

    expected_move = price * 0.003  # 0.3%

    future_price = price + expected_move if direction == "CALL" else price - expected_move

    sigma = 0.2
    T = 2 / 365
    r = 0.01

    theoretical = black_scholes(
        future_price,
        strike,
        T,
        r,
        sigma,
        call=(direction == "CALL")
    )

    roi = (theoretical - premium) / premium

    return {
        "premium": round(premium, 2),
        "theoretical": round(theoretical, 2),
        "roi": round(roi * 100, 2),
        "delta": round(delta, 2),
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

    # breakout
    high = h1["close"].iloc[-15:].max()
    low = h1["close"].iloc[-15:].min()

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

    direction = "CALL" if score > 0 else "PUT"

    if abs(score) >= 3:

        chain = get_option_chain(symbol)
        if not chain:
            return None

        option = pick_best_option(chain, last["close"], direction)
        if not option:
            return None

        est = estimate(last["close"], option, direction)

        return {
            "symbol": symbol,
            "direction": direction,
            "price": round(last["close"], 2),
            "score": score,
            "strike": option["details"]["strike_price"],
            "premium": est["premium"],
            "roi": est["roi"],
            "delta": est["delta"],
        }

    return None
