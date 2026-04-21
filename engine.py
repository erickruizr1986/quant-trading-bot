import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz
import requests

API_KEY = None  # opcional para options

# -----------------------------
# DEBUG
# -----------------------------
DEBUG = True

def log(msg):
    if DEBUG:
        print(msg)

# -----------------------------
# DATA (YAHOO)
# -----------------------------
def get_data(symbol):

    try:
        df = yf.download(
            symbol,
            period="5d",
            interval="1h",
            progress=False
        )

        if df is None or len(df) < 30:
            log(f"❌ DATA INSUFICIENTE YF ({symbol})")
            return None

        df = df.reset_index()

        df["close"] = df["Close"]
        df["high"] = df["High"]
        df["low"] = df["Low"]
        df["volume"] = df["Volume"]

        log(f"✅ DATA YAHOO OK ({symbol})")

        return df

    except Exception as e:
        log(f"❌ ERROR YFINANCE: {e}")
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
# OPCIONES (OPCIONAL)
# -----------------------------
def get_options_chain(symbol):

    if not API_KEY:
        return []

    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={symbol}&limit=50&apiKey={API_KEY}"

    try:
        r = requests.get(url).json()
    except:
        log("❌ ERROR OPTIONS API")
        return []

    return r.get("results", [])

def select_contract(chain, price, direction):

    if not chain:
        return {"strike": round(price), "expiry": "N/A"}

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
        return {"strike": round(price), "expiry": "N/A"}

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
# SIGNAL (FIX COMPLETO)
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        log("❌ FUERA DE HORARIO")
        return None

    df = get_data(symbol)

    if df is None:
        log("❌ SIN DATA")
        return None

    df = add_ind(df)

    try:
        last = df.iloc[-2]
        prev = df.iloc[-3]
    except:
        log("❌ ERROR INDEX")
        return None

    # 🔥 FIX CRÍTICO: convertir a float
    try:
        close = float(last["close"])
        ema200 = float(last["ema200"])
        prev_close = float(prev["close"])
        volume = float(last["volume"])
        vol_avg = float(df["volume"].rolling(20).mean().iloc[-1])
        rsi = float(last["rsi"])
    except:
        log("❌ ERROR CONVERSION FLOAT")
        return None

    score = 0

    # -----------------------------
    # TENDENCIA
    # -----------------------------
    if close > ema200:
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
    if direction == "CALL" and close > prev_close:
        score += 1
        log("⚠️ MOMENTUM CALL")

    elif direction == "PUT" and close < prev_close:
        score -= 1
        log("⚠️ MOMENTUM PUT")

    else:
        log("❌ SIN MOMENTUM")
        return None

    # -----------------------------
    # VOLUMEN
    # -----------------------------
    if volume > vol_avg:
        log("✅ VOLUMEN OK")
    else:
        log("❌ VOLUMEN BAJO")
        return None

    # -----------------------------
    # RSI
    # -----------------------------
    if direction == "CALL" and 50 <= rsi <= 70:
        score += 1
    elif direction == "PUT" and 30 <= rsi <= 50:
        score -= 1

    log(f"🎯 SCORE FINAL: {score}")

    if abs(score) < 3:
        log("❌ SCORE BAJO")
        return None

    # -----------------------------
    # OPCIONES
    # -----------------------------
    chain = get_options_chain(symbol)
    contract = select_contract(chain, close, direction)

    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(close, 2),
        "score": score,
        "strike": contract["strike"],
        "expiry": contract["expiry"],
        "premium": 1.2
    }
