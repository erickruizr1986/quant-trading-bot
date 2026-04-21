import os
import threading
import time
import requests
from flask import Flask

import engine
from risk import position_size
from db import init_db
from ml import train_model, predict

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_KEY = os.environ.get("API_KEY")

engine.API_KEY = API_KEY

app = Flask(__name__)

last_signal = {}


def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


@app.route("/")
def home():
    return "BOT ACTIVO"


def loop():

    send("🚀 BOT CUANT ACTIVO")

    model = train_model()

    while True:
        try:
            for sym in ["SPY", "QQQ"]:

                sig = engine.signal(sym)

                if not sig:
                    continue

                key = f"{sym}_{sig['direction']}"

                if last_signal.get(sym) == key:
                    continue

                prob = predict(model, sig["score"])

                if prob < 0.55:
                    continue

                contracts = position_size(sig["premium"], prob)

                tp = engine.dynamic_tp(sig["score"], prob)

                msg = (
                    f"🔥 {sig['direction']} {sym}\n"
                    f"Precio: {sig['price']}\n"
                    f"Score: {sig['score']}\n"
                    f"Prob: {round(prob*100,1)}%\n\n"
                    f"Strike: {sig['strike']}\n"
                    f"Exp: {sig['expiry']}\n\n"
                    f"Contratos: {contracts}\n"
                    f"SL: -30% | TP: +{tp}%"
                )

                send(msg)

                last_signal[sym] = key

            time.sleep(300)

        except Exception as e:
            print(e)
            time.sleep(60)


if __name__ == "__main__":

    init_db()

    threading.Thread(target=loop).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
