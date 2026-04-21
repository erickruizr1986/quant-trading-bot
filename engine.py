import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz
import math

DEBUG = True

def log(msg):
    if DEBUG:
        print(msg)

# -----------------------------
# DATA
# -----------------------------
def get_data(symbol, interval, period):

    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False
        )

        if df is None or len(df) < 50:
            return None

        df = df.reset_index()

        df["close"] = df["Close"]
        df["high"] = df["High"]
        df["low"] = df["Low"]
        df["volume"] = df["Volume"]

        return df

    except:
        return None

# -----------------------------
# VWAP
# -----------------------------
def add_vwap(df):
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    return df

# -----------------------------
# SAFE FLOAT
# -----------------------------
def safe(x):
    try:
        v = float(x)
        if math.isnan(v):
            return None
        return v
    except:
        return None

# -----------------------------
# HORARIO
# -----------------------------
def valid_session():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 30)) and now.hour < 16

# -----------------------------
# SIGNAL PRO
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        return None

    # -----------------------------
    # DAILY CONTEXTO
    # -----------------------------
    d1 = get_data(symbol, "1d", "3mo")

    if d1 is None:
        log("❌ SIN DATA DAILY")
        return None

    d1["ema200"] = EMAIndicator(d1["close"], 200).ema_indicator()

    daily_close = safe(d1.iloc[-1]["close"])
    daily_ema = safe(d1.iloc[-1]["ema200"])

    if None in [daily_close, daily_ema]:
        return None

    if daily_close > daily_ema:
        bias = "CALL"
        log("📈 BIAS ALCISTA")
    else:
        bias = "PUT"
        log("📉 BIAS BAJISTA")

    # -----------------------------
    # INTRADÍA
    # -----------------------------
    h1 = get_data(symbol, "1h", "10d")

    if h1 is None:
        log("❌ SIN DATA INTRADIA")
        return None

    h1["ema20"] = EMAIndicator(h1["close"], 20).ema_indicator()
    h1["rsi"] = RSIIndicator(h1["close"], 14).rsi()
    h1 = add_vwap(h1)

    try:
        last = h1.iloc[-2]
        prev = h1.iloc[-3]
    except:
        return None

    close = safe(last["close"])
    ema20 = safe(last["ema20"])
    prev_close = safe(prev["close"])
    vwap = safe(last["vwap"])
    volume = safe(last["volume"])
    vol_avg = safe(h1["volume"].rolling(20).mean().iloc[-1])
    rsi = safe(last["rsi"])

    if None in [close, ema20, prev_close, vwap, volume, vol_avg, rsi]:
        log("❌ DATA INVALIDA")
        return None

    score = 0

    # -----------------------------
    # FILTRO DIRECCIÓN
    # -----------------------------
    direction = bias

    # -----------------------------
    # EMA20 (timing)
    # -----------------------------
    if direction == "CALL" and close > ema20:
        score += 1
    elif direction == "PUT" and close < ema20:
        score -= 1
    else:
        return None

    # -----------------------------
    # MOMENTUM
    # -----------------------------
    if direction == "CALL" and close > prev_close:
        score += 1
    elif direction == "PUT" and close < prev_close:
        score -= 1
    else:
        return None

    # -----------------------------
    # VWAP (institucional)
    # -----------------------------
    if direction == "CALL" and close > vwap:
        score += 1
    elif direction == "PUT" and close < vwap:
        score -= 1

    # -----------------------------
    # VOLUMEN
    # -----------------------------
    if volume > vol_avg * 0.8:
        score += 1 if direction == "CALL" else -1
    else:
        return None

    # -----------------------------
    # RSI
    # -----------------------------
    if direction == "CALL" and rsi > 50:
        score += 1
    elif direction == "PUT" and rsi < 50:
        score -= 1

    log(f"🎯 SCORE: {score}")

    if abs(score) < 2:
        return None

    log("🚀 SIGNAL PRO OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(close, 2),
        "score": score,
        "strike": round(close),
        "expiry": "0DTE",
        "premium": 1.2
    }
