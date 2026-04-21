import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
import pytz

API_KEY = None

# -----------------------------
# DEBUG
# -----------------------------
DEBUG = True

def log(msg):
    if DEBUG:
        print(msg)

# -----------------------------
# DATA CON FALLBACK
# -----------------------------
def get_data(symbol):

    try:
        end = datetime.now()
        start = end - timedelta(days=5)

        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        # -----------------------------
        # INTENTO INTRADÍA
        # -----------------------------
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/hour/{start_str}/{end_str}?adjusted=true&sort=asc&limit=500&apiKey={API_KEY}"

        r = requests.get(url).json()

        if "results" in r and len(r["results"]) > 20:
            log(f"✅ DATA INTRADÍA ({symbol})")

            df = pd.DataFrame(r["results"])

            df["close"] = df["c"]
            df["high"] = df["h"]
            df["low"] = df["l"]
            df["volume"] = df["v"]

            return df

        # -----------------------------
        # FALLBACK A DIARIO
        # -----------------------------
        log(f"⚠️ FALLBACK DIARIO ({symbol})")

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_str}/{end_str}?adjusted=true&sort=asc&limit=200&apiKey={API_KEY}"

        r = requests.get(url).json()

        if "results" not in r or len(r["results"]) < 20:
            log(f"❌ SIN DATA ({symbol})")
            return None

        df = pd.DataFrame(r["results"])

        df["close"] = df["c"]
        df["high"] = df["h"]
        df["low"] = df["l"]
        df["volume"] = df["v"]

        return df

    except:
        log("❌ ERROR API")
        return None

# -----------------------------
# INDICADORES
# -----------------------------
def add_ind(df):
    df["ema200"] = EMAIndicator(df["close"], 200).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()
    return df

# -----------------------------
# HORARIO
# -----------------------------
def valid_session():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16

# -----------------------------
# OPCIONES
# -----------------------------
def get_options_chain(symbol):

    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={symbol}&limit=50&apiKey={API_KEY}"

    try:
        r = requests.get(url).json()
    except:
        log("❌ ERROR OPTIONS API")
        return []

    return r.get("results", [])

def select_contract(chain, price, direction):

    best = None
    diff_min = 999

    for c in chain:
        try:
            strike = float(c["strike_price"])

            if direction == "CALL" and c["contract_type"] != "call":
                continue
            if direction == "PUT" and c["contract_type"] != "put":
                continue

            diff = abs(strike - price)

            if diff < diff_min:
                diff_min = diff
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

    return int(max(0.25, min(tp, 1.0)) * 100)

# -----------------------------
# SIGNAL FINAL
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        log("❌ FUERA DE HORARIO")
        return None

    df = get_data(symbol)

    if df is None or len(df) < 30:
        log("❌ SIN DATA")
        return None

    df = add_ind(df)

    try:
        last = df.iloc[-2]
        prev = df.iloc[-3]
    except:
        log("❌ ERROR INDEX")
        return None

    score = 0

    # -----------------------------
    # TENDENCIA
    # -----------------------------
    if last["close"] > last["ema200"]:
        direction = "CALL"
        score += 2
        log("✅ EMA200 CALL")
    else:
        direction = "PUT"
        score -= 2
        log("✅ EMA200 PUT")

    # -----------------------------
    # MOMENTUM
    # -----------------------------
    if direction == "CALL" and last["close"] > prev["close"]:
        score += 1
        log("⚠️ MOMENTUM CALL")

    elif direction == "PUT" and last["close"] < prev["close"]:
        score -= 1
        log("⚠️ MOMENTUM PUT")

    else:
        log("❌ SIN MOMENTUM")
        return None

    # -----------------------------
    # VOLUMEN
    # -----------------------------
    if last["volume"] > df["volume"].rolling(20).mean().iloc[-1]:
        log("✅ VOLUMEN OK")
    else:
        log("❌ VOLUMEN BAJO")
        return None

    # -----------------------------
    # RSI
    # -----------------------------
    if direction == "CALL" and 50 <= last["rsi"] <= 70:
        score += 1
    elif direction == "PUT" and 30 <= last["rsi"] <= 50:
        score -= 1

    log(f"🎯 SCORE FINAL: {score}")

    if abs(score) < 3:
        log("❌ SCORE BAJO")
        return None

    # -----------------------------
    # OPCIONES
    # -----------------------------
    chain = get_options_chain(symbol)
    contract = select_contract(chain, last["close"], direction)

    if not contract:
        log("❌ SIN OPCIÓN")
        return None

    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(last["close"], 2),
        "score": score,
        "strike": contract["strike"],
        "expiry": contract["expiry"],
        "premium": 1.2
    }
