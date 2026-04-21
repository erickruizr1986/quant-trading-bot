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
# DATA
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
        df["open"] = df["Open"]
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
# HORARIO PRO (ALTO VOLUMEN)
# -----------------------------
def valid_session():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)

    h = now.hour
    m = now.minute

    # apertura
    if (h == 9 and m >= 30) or (h == 10):
        return True

    # power hour
    if h >= 14 and h < 16:
        return True

    return False

# -----------------------------
# ANALISIS DE VELAS
# -----------------------------
def candle_strength(candle):

    o = safe(candle["open"])
    c = safe(candle["close"])
    h = safe(candle["high"])
    l = safe(candle["low"])

    if None in [o, c, h, l]:
        return None

    body = abs(c - o)
    range_total = h - l

    if range_total == 0:
        return 0

    strength = body / range_total

    return strength, c > o  # fuerza + dirección

# -----------------------------
# SIGNAL
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        log("⏰ FUERA DE HORARIO PRO")
        return None

    # -----------------------------
    # BIAS BASE
    # -----------------------------
    d1 = get_data(symbol, "1d", "2mo")
    bias = None

    if d1 is not None:
        last_close = safe(d1.iloc[-1]["close"])
        avg_close = safe(d1["close"].tail(20).mean())

        if last_close and avg_close:
            bias = "CALL" if last_close > avg_close else "PUT"
            log(f"📊 BIAS DAILY: {bias}")

    # fallback
    if bias is None:
        log("⚠️ FALLBACK INTRADÍA")

        temp = get_data(symbol, "1h", "5d")
        if temp is None:
            return None

        last = safe(temp.iloc[-2]["close"])
        prev = safe(temp.iloc[-3]["close"])

        if last and prev:
            bias = "CALL" if last > prev else "PUT"
        else:
            return None

    # -----------------------------
    # INTRADÍA
    # -----------------------------
    df = get_data(symbol, "1h", "10d")

    if df is None:
        return None

    df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()
    df = add_vwap(df)

    last = df.iloc[-2]
    prev = df.iloc[-3]

    close = safe(last["close"])
    ema20 = safe(last["ema20"])
    vwap = safe(last["vwap"])
    volume = safe(last["volume"])
    vol_avg = safe(df["volume"].rolling(20).mean().iloc[-1])
    rsi = safe(last["rsi"])

    if None in [close, ema20, vwap, volume, vol_avg, rsi]:
        return None

    score = 0
    direction = bias

    # -----------------------------
    # 🔥 ANALISIS DE VELA
    # -----------------------------
    strength_data = candle_strength(last)

    if strength_data:
        strength, bullish = strength_data

        if bullish:
            score += 1
            log("🟢 VELA ALCISTA")
        else:
            score -= 1
            log("🔴 VELA BAJISTA")

        if strength > 0.6:
            score += 1 if bullish else -1
            log("🔥 VELA FUERTE")

    # -----------------------------
    # EMA20 (flexible)
    # -----------------------------
    if direction == "CALL":
        if close > ema20:
            score += 1
        else:
            log("⚠️ EMA20 NO IDEAL")
    else:
        if close < ema20:
            score -= 1
        else:
            log("⚠️ EMA20 NO IDEAL")

    # -----------------------------
    # VWAP
    # -----------------------------
    if direction == "CALL" and close > vwap:
        score += 1
    elif direction == "PUT" and close < vwap:
        score -= 1

    # -----------------------------
    # VOLUMEN (más permisivo)
    # -----------------------------
    if volume > vol_avg * 0.6:
        score += 1 if direction == "CALL" else -1
    else:
        log("⚠️ VOLUMEN BAJO")

    # -----------------------------
    # RSI
    # -----------------------------
    if direction == "CALL" and rsi > 50:
        score += 1
    elif direction == "PUT" and rsi < 50:
        score -= 1

    log(f"🎯 SCORE: {score}")

    if abs(score) < 1:
        return None

    if abs(score) >= 3:
        strength_label = "FUERTE"
    elif abs(score) == 2:
        strength_label = "MEDIA"
    else:
        strength_label = "DEBIL"

    # -----------------------------
    # PROYECCION (CLAVE)
    # -----------------------------
    prediction = "CALL" if score > 0 else "PUT"

    # -----------------------------
    # STRIKE + EXPIRY
    # -----------------------------
    strike = round(close)

    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)

    if now.hour < 12:
        expiry = "0DTE"
    elif now.hour < 15:
        expiry = "1DTE"
    else:
        expiry = "1-2DTE"

    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": prediction,
        "price": round(close, 2),
        "score": score,
        "strength": strength_label,
        "strike": strike,
        "expiry": expiry,
        "premium": 1.2
    }
