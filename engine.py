import yfinance as yf
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
import pytz
import math

DEBUG = True

def log(msg):
    if DEBUG:
        print(msg)

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
        df = yf.download(symbol, period=period, interval=interval, progress=False)

        if df is None or df.empty:
            return None

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

        df = df.dropna(subset=["close"])
        return df

    except:
        return None

# -----------------------------
# SESSION
# -----------------------------
def valid_session():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    return (9 <= now.hour < 11) or (14 <= now.hour < 16)

# -----------------------------
# EXPIRATION
# -----------------------------
def get_expiration():
    ny = pytz.timezone("America/New_York")
    today = datetime.now(ny)

    if today.weekday() == 4:
        return today.strftime("%Y-%m-%d")

    return (today + timedelta(days=1)).strftime("%Y-%m-%d")

# -----------------------------
# SCORE PROFESIONAL
# -----------------------------
def compute_score(df):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = safe(last["close"])
    prev_close = safe(prev["close"])

    ema20 = safe(last["ema20"])
    rsi = safe(last["rsi"])

    if close is None or prev_close is None:
        return None

    score = 0

    # momentum
    if close > prev_close:
        score += 1
    else:
        score -= 1

    # tendencia EMA
    if ema20:
        if close > ema20:
            score += 1
        else:
            score -= 1

    # RSI
    if rsi:
        if rsi > 60:
            score += 1
        elif rsi < 40:
            score -= 1

    # vela fuerte
    move = abs(close - prev_close) / close
    if move > 0.002:
        score += 1 if close > prev_close else -1

    return score

# -----------------------------
# PROBABILIDAD REALISTA
# -----------------------------
def probability(score):
    if abs(score) >= 4:
        return 0.80
    elif abs(score) == 3:
        return 0.75
    else:
        return 0.60

# -----------------------------
# TP AGRESIVO
# -----------------------------
def dynamic_tp(score, price=None):
    if abs(score) >= 4:
        return "70%-150%"
    elif abs(score) == 3:
        return "60%-100%"
    else:
        return "40%-70%"

# -----------------------------
# SIGNAL
# -----------------------------
def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        return None

    # -----------------------------
    # DAILY TREND (FILTRO MACRO)
    # -----------------------------
    d = get_data(symbol, "1d", "2mo")

    if d is None:
        return None

    d["ema50"] = EMAIndicator(d["close"], 50).ema_indicator()

    last_d = d.iloc[-1]
    trend_up = safe(last_d["close"]) > safe(last_d["ema50"])

    # -----------------------------
    # INTRADÍA
    # -----------------------------
    df = get_data(symbol, "1h", "10d")

    if df is None or len(df) < 3:
        return None

    df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()

    score = compute_score(df)

    if score is None:
        return None

    log(f"🎯 SCORE: {score}")

    # -----------------------------
    # FILTRO PRO
    # -----------------------------
    if abs(score) < 3:
        log("❌ SIN CONFLUENCIA")
        return None

    direction = "CALL" if score > 0 else "PUT"

    # filtro con tendencia diaria
    if direction == "CALL" and not trend_up:
        log("❌ CONTRA TENDENCIA")
        return None

    if direction == "PUT" and trend_up:
        log("❌ CONTRA TENDENCIA")
        return None

    prob = probability(score)

    if prob < 0.75:
        return None

    # -----------------------------
    # CONTRATO INTELIGENTE
    # -----------------------------
    price = safe(df.iloc[-1]["close"])
    strike = round(price)

    expiry = get_expiration()

    premium = round(price * 0.015, 2)

    tp = dynamic_tp(score)

    log("🚀 SIGNAL PRO")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(price, 2),
        "strike": strike,
        "expiry": expiry,
        "premium": premium,
        "probability": prob,
        "score": score,
        "tp": tp
    }
