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

        if df is None or len(df) < 5:
            log(f"❌ DATA INSUFICIENTE ({symbol} {interval})")
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
    o = safe(c["open"])
    c_ = safe(c["close"])
    h = safe(c["high"])
    l = safe(c["low"])

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

    # 1️⃣ DAILY
    d = get_data(symbol, "1d", "2mo")

    if d is not None and len(d) >= 20:
        last = safe(d.iloc[-1]["close"])
        avg = safe(d["close"].tail(20).mean())

        if last is not None and avg is not None:
            bias = "CALL" if last > avg else "PUT"
            log(f"📊 BIAS DAILY: {bias}")

    # 2️⃣ 1H
    if bias is None:
        log("⚠️ FALLBACK 1H")

        h1 = get_data(symbol, "1h", "5d")

        if h1 is not None and len(h1) >= 3:
            last = safe(h1.iloc[-1]["close"])
            prev = safe(h1.iloc[-2]["close"])

            if last is not None and prev is not None:
                bias = "CALL" if last > prev else "PUT"
                log(f"📊 BIAS 1H: {bias}")

    # 3️⃣ 5M
    if bias is None:
        log("⚠️ FALLBACK 5M")

        m5 = get_data(symbol, "5m", "1d")

        if m5 is not None and len(m5) >= 3:
            last = safe(m5.iloc[-1]["close"])
            prev = safe(m5.iloc[-2]["close"])

            if last is not None and prev is not None:
                bias = "CALL" if last > prev else "PUT"
                log(f"📊 BIAS 5M: {bias}")

    # 4️⃣ FORZADO
    if bias is None:
        log("⚠️ BIAS FORZADO")

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")

            if hist is not None and not hist.empty:
                bias = "CALL"
                log("📊 BIAS DEFAULT: CALL")
        except:
            pass

    if bias is None:
        log("❌ SIN BIAS FINAL")
        return None

    # =============================
    # 🔥 INTRADÍA
    # =============================
    df = get_data(symbol, "1h", "10d")

    if df is None or len(df) < 3:
        log("❌ DATA INTRADIA INSUFICIENTE")
        return None

    df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = safe(last["close"])
    ema20 = safe(last["ema20"])
    prev_close = safe(prev["close"])
    volume = safe(last["volume"])
    vol_avg = safe(df["volume"].rolling(20).mean().iloc[-1])
    rsi = safe(last["rsi"])

    if None in [close, ema20, prev_close, volume, vol_avg, rsi]:
        log("❌ DATA INVALIDA")
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
    if bias == "CALL" and close > ema20:
        score += 1
    elif bias == "PUT" and close < ema20:
        score -= 1

    # volumen flexible
    if volume > vol_avg * 0.5:
        score += 1 if bias == "CALL" else -1
    else:
        log("⚠️ VOLUMEN BAJO PERMITIDO")

    # RSI
    if bias == "CALL" and rsi > 50:
        score += 1
    elif bias == "PUT" and rsi < 50:
        score -= 1

    log(f"🎯 SCORE: {score}")

    if score == 0:
        log("⚠️ SEÑAL DEBIL PERMITIDA")

    # =============================
    # CLASIFICACIÓN
    # =============================
    if abs(score) >= 3:
        strength = "FUERTE"
    elif abs(score) == 2:
        strength = "MEDIA"
    else:
        strength = "DEBIL"

    direction = "CALL" if score > 0 else "PUT"

    # =============================
    # OPTIONS
    # =============================
    if IB_AVAILABLE:
        strike, expiry = get_best_option_ib(symbol, close, direction)
    else:
        log("⚠️ IB NO DISPONIBLE")
        strike = round(close)
        expiry = "N/A"

    if strike is None:
        strike = round(close)
        expiry = "N/A"

    # =============================
    # CAPITAL
    # =============================
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
