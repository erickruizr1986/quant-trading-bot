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


def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


@app.route("/")
def home():
    return "BOT PROFESIONAL ACTIVO 🚀"


def loop():

    send("🔥 BOT CON GESTION PROFESIONAL ACTIVO")

    active_trades = 0
    max_trades = 3

    while True:
        try:
            for sym in ["SPY", "QQQ"]:

                if active_trades >= max_trades:
                    continue

                sig = engine.signal(sym)

                if sig:

                    contracts = position_size(sig["premium"])

                    msg = (
                        f"🔥 {sig['direction']} {sym}\n"
                        f"Tipo: {sig['type']}\n"
                        f"Precio: {sig['price']}\n\n"
                        f"Strike: {sig['strike']}\n"
                        f"Prima: {sig['premium']}\n"
                        f"Contratos: {contracts}\n\n"
                        f"SL: -30%\n"
                        f"TP: +50%\n\n"
                        f"Score: {sig['score']}\n"
                        f"VIX: {sig['vix']}"
                    )

                    send(msg)

                    log_trade(
                        sig["symbol"],
                        sig["direction"],
                        sig["price"],
                        sig["strike"],
                        sig["premium"],
                        sig["score"]
                    )

                    active_trades += 1

            time.sleep(300)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(60)


if __name__ == "__main__":

    init_db()

    threading.Thread(target=loop).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
