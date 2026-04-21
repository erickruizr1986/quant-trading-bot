import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import pytz
import math

# 🔥 IB DESACTIVADO (evita errores en cloud)
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
# DATA ROBUSTA
# -----------------------------
def get_data(symbol, interval, period):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)

        if df is None or df.empty:
            return None

        # 🔥 FIX columnas tuple (yfinance bug)
        if hasattr(df.columns, "levels"):
            df.columns = [c[0] for c in df.columns]

        df = df.reset_index()

        cols = {c.lower(): c for c in df.columns}

        if "close" in cols:
            df["close"] = df[cols["close"]]
        elif "adj close" in cols:
            df["close"] = df[cols["adj close"]]
        else:
            return None

        if "open" in cols:
            df["open"] = df[cols["open"]]
        if "high" in cols:
            df["high"] = df[cols["high"]]
        if "low" in cols:
            df["low"] = df[cols["low"]]
        if "volume" in cols:
            df["volume"] = df[cols["volume"]]

        df = df.dropna(subset=["close"])

        if len(df) < 3:
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

    return (now.hour == 9 and now.minute >= 30) or (10 <= now.hour < 16)

# -----------------------------
# TAKE PROFIT DINÁMICO (FIX)
# -----------------------------
def dynamic_tp(score, price=None):

    # ignoramos price si lo envían
    if abs(score) >= 2:
        return "40%-80%"
    elif abs(score) == 1:
        return "20%-40%"
    else:
        return "10%-20%"

# -----------------------------
# SIGNAL
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        return None

    # =============================
    # BIAS SIMPLE (estable)
    # =============================
    bias = "CALL"

    d = get_data(symbol, "1d", "2mo")

    if d is not None:
        last = safe(d.iloc[-1]["close"])
        avg = safe(d["close"].tail(20).mean())

        if last is not None and avg is not None:
            bias = "CALL" if last > avg else "PUT"

    log(f"📊 BIAS: {bias}")

    # =============================
    # INTRADÍA
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

    if close is None or prev_close is None:
        return None

    # =============================
    # SCORE SIMPLE Y ESTABLE
    # =============================
    score = 1 if close > prev_close else -1

    direction = "CALL" if score > 0 else "PUT"

    # =============================
    # CONTRATO (SIN IB)
    # =============================
    strike = round(close)
    expiry = "N/A"

    # =============================
    # PREMIUM (FIX ERROR)
    # =============================
    premium = round(close * 0.02, 2)

    tp = dynamic_tp(score)

    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(close, 2),
        "strike": strike,
        "expiry": expiry,
        "premium": premium,
        "score": score,
        "tp": tp
    }
