import os
import threading
import time
import requests
from flask import Flask

import engine
from risk import position_size
from db import init_db, log_trade

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_KEY = os.environ.get("API_KEY")

engine.API_KEY = API_KEY

app = Flask(__name__)

last_signals = {}
last_time = {}


def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


@app.route("/")
def home():
    return "BOT ACTIVO"


def loop():

    send("🚀 BOT PROFESIONAL ACTIVO")

    while True:
        try:
            for sym in ["SPY", "QQQ"]:

                sig = engine.signal(sym)

                if not sig:
                    continue

                key = f"{sym}_{sig['direction']}"

                now = time.time()

                if last_signals.get(sym) == key:
                    continue

                if sym in last_time and now - last_time[sym] < 1800:
                    continue

                last_signals[sym] = key
                last_time[sym] = now

                contracts = position_size(sig["premium"], sig["score"])

                if contracts == 0:
                    continue

                msg = (
                    f"🔥 {sig['direction']} {sym}\n"
                    f"Precio: {sig['price']}\n"
                    f"Score: {sig['score']}\n\n"
                    f"Contratos: {contracts}\n"
                    f"Strike: {sig['strike']}\n"
                    f"Prima: {sig['premium']}\n\n"
                    f"SL: -30% | TP: +50%"
                )

                send(msg)

                log_trade(
                    sig["symbol"],
                    sig["direction"],
                    sig["price"],
                    sig["score"]
                )

            time.sleep(300)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(60)


if __name__ == "__main__":

    init_db()

    threading.Thread(target=loop).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
