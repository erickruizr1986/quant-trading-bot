def signal(symbol):

    log(f"\n🔍 ANALIZANDO {symbol}")

    if not valid_session():
        return None

    # -----------------------------
    # BIAS (fallback incluido)
    # -----------------------------
    d1 = get_data(symbol, "1d", "2mo")
    bias = None

    if d1 is not None:
        try:
            last_close = safe(d1.iloc[-1]["close"])
            avg_close = safe(d1["close"].tail(20).mean())

            if last_close and avg_close:
                bias = "CALL" if last_close > avg_close else "PUT"
        except:
            pass

    if bias is None:
        h1_temp = get_data(symbol, "1h", "5d")
        if h1_temp is None:
            return None

        last = safe(h1_temp.iloc[-2]["close"])
        avg = safe(h1_temp["close"].tail(20).mean())

        bias = "CALL" if last > avg else "PUT"

    # -----------------------------
    # INTRADÍA
    # -----------------------------
    h1 = get_data(symbol, "1h", "10d")

    if h1 is None:
        return None

    h1["ema20"] = EMAIndicator(h1["close"], 20).ema_indicator()
    h1["rsi"] = RSIIndicator(h1["close"], 14).rsi()
    h1 = add_vwap(h1)

    last = h1.iloc[-2]
    prev = h1.iloc[-3]

    close = safe(last["close"])
    ema20 = safe(last["ema20"])
    prev_close = safe(prev["close"])
    vwap = safe(last["vwap"])
    volume = safe(last["volume"])
    vol_avg = safe(h1["volume"].rolling(20).mean().iloc[-1])
    rsi = safe(last["rsi"])

    if None in [close, ema20, prev_close, vwap, volume, vol_avg, rsi]:
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

    if abs(score) < 2:
        return None

    strength = "FUERTE" if abs(score) >= 3 else "MEDIA"

    # -----------------------------
    # 🔥 STRIKE PROFESIONAL
    # -----------------------------
    strike = round(close)

    if direction == "CALL":
        strike = strike  # ATM
    else:
        strike = strike  # ATM

    # -----------------------------
    # 🔥 EXPIRACIÓN INTELIGENTE
    # -----------------------------
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)

    if now.hour < 12:
        expiry = "0DTE"
    elif now.hour < 15:
        expiry = "1DTE"
    else:
        expiry = "1-2DTE"

    log(f"🎯 SCORE: {score}")
    log("🚀 SIGNAL OK")

    return {
        "symbol": symbol,
        "direction": direction,
        "price": round(close, 2),
        "score": score,
        "strength": strength,
        "strike": strike,
        "expiry": expiry,
        "premium": 1.2
    }
