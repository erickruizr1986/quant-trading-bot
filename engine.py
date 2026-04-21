from datetime import datetime, timedelta

def get_data(symbol, tf):

    try:
        end = datetime.now()
        start = end - timedelta(days=5)

        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        timespan = "hour" if tf == "hour" else "day"

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/{start_str}/{end_str}?adjusted=true&sort=asc&limit=500&apiKey={API_KEY}"

        r = requests.get(url).json()

    except:
        log("❌ ERROR API")
        return None

    if "results" not in r or len(r["results"]) < 20:
        log(f"❌ DATA INSUFICIENTE API ({symbol})")
        return None

    df = pd.DataFrame(r["results"])

    df["close"] = df["c"]
    df["high"] = df["h"]
    df["low"] = df["l"]
    df["volume"] = df["v"]

    return df
