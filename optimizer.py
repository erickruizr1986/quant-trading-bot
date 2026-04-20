import itertools
from engine import get_data, add_ind, simulate_option, calc_volatility

SYMBOL = "SPY"


def run_test(df, bw, th, vol_mult):

    results = []

    for i in range(50, len(df)-5):

        row = df.iloc[i]

        score = 0

        if df["ema20"].iloc[i] > df["ema40"].iloc[i]:
            score += 2
        else:
            score -= 2

        high = df["close"].iloc[i-bw:i].max()
        low = df["close"].iloc[i-bw:i].min()

        if row["close"] > high:
            score += 2
        if row["close"] < low:
            score -= 2

        if abs(score) < th:
            continue

        direction = "CALL" if score > 0 else "PUT"

        entry = row["close"]
        exit_price = df["close"].iloc[i+3]

        vol = calc_volatility(df.iloc[:i]) * vol_mult

        option = simulate_option(entry, direction, vol)

        move = exit_price - entry
        if direction == "PUT":
            move = -move

        pnl = move * option["delta"]
        roi = (pnl / option["premium"]) * 100

        results.append(roi)

    if len(results) < 30:
        return None

    return sum(results)


def optimize():

    df = get_data(SYMBOL, "hour")
    df = add_ind(df)

    best = None
    best_score = -999

    for bw, th, vm in itertools.product(
        [10,15,20],
        [2,3,4],
        [1.0,1.5,2.0]
    ):

        score = run_test(df, bw, th, vm)

        if not score:
            continue

        print(f"BW:{bw} TH:{th} VM:{vm} → {round(score,2)}")

        if score > best_score:
            best_score = score
            best = (bw, th, vm)

    print("\n🏆 MEJOR:", best)


if __name__ == "__main__":
    optimize()
