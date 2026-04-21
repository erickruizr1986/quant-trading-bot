import yfinance as yf
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
        df = yf.download(symbol, period=period, interval=interval, progress=False)

        if df is None or len(df) < 30:
            return None

        df = df.reset_index()

        df["close"] = df["Close"]
        df["open"] = df["Open"]
        df["high"] = df["High"]
        df["low"] = df["Low"]
        df["volume"] = df["Volume"]

        return df

    except:
        return None

# -----------------------------
# OPTIONS CHAIN REAL
# -----------------------------
def get_best_contract(symbol, price, direction):

    try:
        ticker = yf.Ticker(symbol)

        expirations = ticker.options

        if not expirations:
            return round(price), "N/A"

        exp = expirations[0]  # nearest expiry

        chain = ticker.option_chain(exp)

        if direction == "CALL":
            df = chain.calls
        else:
            df = chain.puts

        # filtro liquidez
        df = df[df["volume"] > 10]
        df = df[df["openInterest"] > 50]

        if df.empty:
            return round(price), exp

        # strike más cercano al precio
        df["diff"] = abs(df["strike"] - price)
        best = df.sort_values("diff").iloc[0]

        return best["strike"], exp

    except Exception as e:
        log(f"ERROR OPTIONS: {e}")
        return round(price), "N/A"

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

    if h >= 14 and h < 16:
        return True

    return False

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

    log(f"\nANALIZANDO {symbol}")

    if not valid_session():
        return None

    # -----------------------------
    # BIAS
    # -----------------------------
    d = get_data(symbol, "1d", "2mo")

    bias = None

    if d is not None:
        last = safe(d.iloc[-1]["close"])
        avg = safe(d["close"].tail(20).mean())

        if last and avg:
            bias = "CALL" if last > avg else "PUT"

    if bias is None:
        return None

    # -----------------------------
    # INTRADIA
    # -----------------------------
    df = get_data(symbol, "1h", "10d")

    if df is None:
        return None

    df["ema20"] = EMAIndicator(df["close"], 20).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()

    last = df.iloc[-2]
    prev = df.iloc[-3]

    close = safe(last["close"])
    ema20 = safe(last["ema20"])
    prev_close = safe(prev["close"])
    volume = safe(last["volume"])
    vol_avg = safe(df["volume"].rolling(20).mean().iloc[-1])
    rsi = safe(last["rsi"])

    if None in [close, ema20, prev_close, volume, vol_avg, rsi]:
        return None

    score = 0

    if close > prev_close:
        score += 1
    else:
        score -= 1

    if bias == "CALL" and close > ema20:
        score += 1
    elif bias == "PUT" and close < ema20:
        score -= 1

    if volume > vol_avg * 0.6:
        score += 1 if bias == "CALL" else -1

    if bias == "CALL" and rsi > 50:
        score += 1
    elif bias == "PUT" and rsi < 50:
        score -= 1

    if abs(score) < 1:
        return None

    if abs(score) >= 3:
        strength = "FUERTE"
    elif abs(score) == 2:
        strength = "MEDIA"
    else:
        strength = "DEBIL"

    direction = "CALL" if score > 0 else "PUT"

    # 🔥 AQUÍ ESTÁ LA MAGIA REAL
    strike, expiry = get_best_contract(symbol, close, direction)

    size = position_size(strength)
    tp = take_profit(score)

    log("SIGNAL OK")

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
