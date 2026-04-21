import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz
import math

# IB opcional
try:
    from ib_options import get_best_option_ib
    IB_AVAILABLE = True
except:
    IB_AVAILABLE = False

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
# DATA (ROBUSTA)
# -----------------------------
def get_data(symbol, interval, period):
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            threads=False,
            group_by='column'
        )

        if df is None or df.empty:
            log(f"❌ DATA VACÍA ({symbol} {interval})")
            return None

        # 🔥 FIX CRÍTICO: APLANAR COLUMNAS
        if isinstance(df.columns, tuple) or hasattr(df.columns, 'levels'):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

        df = df.reset_index()

        # 🔥 NORMALIZACIÓN SEGURA
        columns = {c.lower(): c for c in df.columns}

        if "close" in columns:
            df["close"] = df[columns["close"]]
        elif "adj close" in columns:
            df["close"] = df[columns["adj close"]]
        else:
            log("❌ NO EXISTE CLOSE")
            return None

        if "open" in columns:
            df["open"] = df[columns["open"]]

        if "high" in columns:
            df["high"] = df[columns["high"]]

        if "low" in columns:
            df["low"] = df[columns["low"]]

        if "volume" in columns:
            df["volume"] = df[columns["volume"]]

        # limpieza
        df = df.dropna(subset=["close"])

        if len(df) < 3:
            log(f"❌ DATA INSUFICIENTE ({symbol})")
            return None

        return df

    except Exception as e:
        log(f"❌ ERROR DATA: {e}")
        return None
# -----------------------------
# HORARIO
# -----------------------------
def valid_session():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)

    h = now.hour
    m = now.minute

    if (h == 9 and m >= 30) or h == 10:
        return True

    if 14 <= h < 16:
        return True

    return False

# -----------------------------
# VELA
# -----------------------------
def candle_strength(c):
    o = safe(c.get("open"))
    c_ = safe(c.get("close"))
    h = safe(c.get("high"))
    l = safe(c.get("low"))

    if None in [o, c_, h, l]:
        return None

    body = abs(c_ - o)
    rng = h - l

    if rng == 0:
        return None

    strength = body / rng
    return strength, c_ > o

# -----------------------------
# CAPITAL
# -----------------------------
def position_size(strength, capital=1000):
    if strength == "FUERTE":
        return round(capital * 0.12, 2)
    elif strength == "MEDIA":
        return round(capital * 0.07, 2)
    else:
        return round(capital * 0.03, 2)

def take_profit(score):
    if abs(score) >= 3:
        return "40%-80%"
    elif abs(score) == 2:
        return "25%-50%"
    else:
        return "15%-30%"

# -----------------------------
# SIGNAL
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        log("⏰ FUERA DE HORARIO")
        return None

    # =============================
    # 🔥 BIAS MULTI-NIVEL
    # =============================
    bias = None

    d = get_data(symbol, "1d", "2mo")

    if d is not None and len(d) >= 20:
        last = safe(d.iloc[-1]["close"])
        avg = safe(d["close"].tail(20).mean())

        if last is not None and avg is not None:
            bias = "CALL" if last > avg else "PUT"
            log(f"📊 BIAS DAILY: {bias}")

    if bias is None:
        log("⚠️ FALLBACK 1H")
        h1 = get_data(symbol, "1h", "5d")

        if h1 is not None and len(h1) >= 3:
            last = safe(h1.iloc[-1]["close"])
            prev = safe(h1.iloc[-2]["close"])
            if last is not None and prev is not None:
                bias = "CALL" if last > prev else "PUT"
                log(f"📊 BIAS 1H: {bias}")

    if bias is None:
        log("⚠️ FALLBACK 5M")
        m5 = get_data(symbol, "5m", "1d")

        if m5 is not None and len(m5) >= 3:
            last = safe(m5.iloc[-1]["close"])
            prev = safe(m5.iloc[-2]["close"])
            if last is not None and prev is not None:
                bias = "CALL" if last > prev else "PUT"
                log(f"📊 BIAS 5M: {bias}")

    if bias is None:
        log("⚠️ BIAS FORZADO")
        bias = "CALL"
        log("📊 BIAS DEFAULT: CALL")

    # =============================
    # 🔥 INTRADÍA
    # =============================
    df = get_data(symbol, "1h", "10d")

    if df is None:
        return None

    df["ema20"] = EMAIndicator(df["close"].ffill(), 20).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"].ffill(), 14).rsi()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = safe(last["close"])
    prev_close = safe(prev["close"])
    ema20 = safe(last["ema20"])
    volume = safe(last.get("volume"))
    vol_avg = safe(df["volume"].rolling(20).mean().iloc[-1]) if "volume" in df else None
    rsi = safe(last["rsi"])

    if close is None or prev_close is None:
        log("❌ DATA CRÍTICA INVALIDA")
        return None

    score = 0

    # vela
    cs = candle_strength(last)
    if cs:
        strength_candle, bullish = cs
        score += 1 if bullish else -1

        if strength_candle > 0.6:
            score += 1 if bullish else -1

    # momentum
    score += 1 if close > prev_close else -1

    # EMA
    if ema20 is not None:
        if bias == "CALL" and close > ema20:
            score += 1
        elif bias == "PUT" and close < ema20:
            score -= 1

    # volumen
    if volume is not None and vol_avg is not None:
        if volume > vol_avg * 0.5:
            score += 1 if bias == "CALL" else -1

    # RSI
    if rsi is not None:
        if bias == "CALL" and rsi > 50:
            score += 1
        elif bias == "PUT" and rsi < 50:
            score -= 1

    log(f"🎯 SCORE: {score}")

    if score == 0:
        log("⚠️ SEÑAL DEBIL PERMITIDA")

    # clasificación
    if abs(score) >= 3:
        strength = "FUERTE"
    elif abs(score) == 2:
        strength = "MEDIA"
    else:
        strength = "DEBIL"

    direction = "CALL" if score > 0 else "PUT"

    # opciones
    if IB_AVAILABLE:
        strike, expiry = get_best_option_ib(symbol, close, direction)
    else:
        strike = round(close)
        expiry = "N/A"

    if strike is None:
        strike = round(close)
        expiry = "N/A"

    size = position_size(strength)
    tp = take_profit(score)

    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(close, 2),
        "score": score,
        "strength": strength,
        "strike": strike,
        "expiry": expiry,
        "size": size,
        "tp": tp,
        "sl": "-25%"
    }
