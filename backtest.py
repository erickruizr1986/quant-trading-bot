import pandas as pd
from engine import get_data, add_ind, simulate_option, calc_volatility, BREAKOUT_WINDOW, THRESHOLD

SYMBOL = "SPY"


def generate_signal(df, i):

    row = df.iloc[i]
    score = 0

    if df["ema20"].iloc[i] > df["ema40"].iloc[i]:
        score += 2
    else:
        score -= 2

    high = df["close"].iloc[i-BREAKOUT_WINDOW:i].max()
    low = df["close"].iloc[i-BREAKOUT_WINDOW:i].min()

    if row["close"] > high:
        score += 2
    if row["close"] < low:
        score -= 2

    if 50 <= row["rsi"] <= 70:
        score += 1
    if 30 <= row["rsi"] <= 50:
        score -= 1

    if abs(score) < THRESHOLD:
        return None

    direction = "CALL" if score > 0 else "PUT"

    return score, direction


def run_backtest():

    df = get_data(SYMBOL, "hour")
    df = add_ind(df)

    results = []

    for i in range(50, len(df)-5):

        sig = generate_signal(df, i)
        if not sig:
            continue

        score, direction = sig

        entry = df["close"].iloc[i]
        exit_price = df["close"].iloc[i+3]

        vol = calc_volatility(df.iloc[:i])

        option = simulate_option(entry, direction, vol)

        move = exit_price - entry
        if direction == "PUT":
            move = -move

        pnl = move * option["delta"]
        roi = (pnl / option["premium"]) * 100

        roi = max(min(roi, 50), -30)

        results.append(roi)

    df_res = pd.Series(results)

    print("\n📊 BACKTEST")
    print("Trades:", len(df_res))
    print("Winrate:", (df_res > 0).mean())
    print("ROI promedio:", df_res.mean())


if __name__ == "__main__":
    run_backtest()
