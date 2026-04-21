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
# DATA ROBUSTA
# -----------------------------
def get_data(symbol, interval, period):

    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            threads=False
        )

        if df is None or len(df) < 30:
            return None

        df = df.reset_index()

        df["close"] = df["Close"]
        df["high"] = df["High"]
        df["low"] = df["Low"]
        df["volume"] = df["Volume"]

        return df

    except Exception as e:
        log(f"❌ ERROR DATA: {e}")
        return None

# -----------------------------
# VWAP
# -----------------------------
def add_vwap(df):
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    return df

# -----------------------------
# SAFE
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
# SIGNAL FINAL ROBUSTO
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        return None

    # -----------------------------
    # 🔥 INTENTO DAILY
    # -----------------------------
    d1 = get_data(symbol, "1d", "2mo")

    bias = None

    if d1 is not None:

        try:
            last_close = safe(d1.iloc[-1]["close"])
            avg_close = safe(d1["close"].tail(20).mean())

            if last_close and avg_close:
                if last_close > avg_close:
                    bias = "CALL"
                    log("📈 BIAS DAILY")
                else:
                    bias = "PUT"
                    log("📉 BIAS DAILY")
        except:
            pass

    # -----------------------------
    # 🔥 FALLBACK INTRADÍA
    # -----------------------------
    if bias is None:
        log("⚠️ FALLBACK A INTRADÍA")

        h1_temp = get_data(symbol, "1h", "5d")

        if h1_temp is None:
            log("❌ SIN DATA TOTAL")
            return None

        try:
            last = safe(h1_temp.iloc[-2]["close"])
            avg = safe(h1_temp["close"].tail(20).mean())

            if last > avg:
                bias = "CALL"
            else:
                bias = "PUT"

        except:
            return None

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
    direction = bias

    # EMA20
    if direction == "CALL" and close > ema20:
        score += 1
    elif direction == "PUT" and close < ema20:
        score -= 1
    else:
        return None

    # Momentum
    if direction == "CALL" and close > prev_close:
        score += 1
    elif direction == "PUT" and close < prev_close:
        score -= 1
    else:
        return None

    # VWAP
    if direction == "CALL" and close > vwap:
        score += 1
    elif direction == "PUT" and close < vwap:
        score -= 1

    # Volumen
    if volume > vol_avg * 0.8:
        score += 1 if direction == "CALL" else -1
    else:
        return None

    # RSI
    if direction == "CALL" and rsi > 50:
        score += 1
    elif direction == "PUT" and rsi < 50:
        score -= 1

    log(f"🎯 SCORE: {score}")

    if abs(score) < 2:
        return None

    strength = "FUERTE" if abs(score) >= 3 else "MEDIA"

    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(close, 2),
        "score": score,
        "strength": strength,
        "strike": round(close),
        "expiry": "0DTE",
        "premium": 1.2
    }
