import os
import threading
import time
import requests
from flask import Flask

import engine
from risk import position_size
from db import init_db, log_trade
from ml import train_model, predict

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_KEY = os.environ.get("API_KEY")

engine.API_KEY = API_KEY

app = Flask(__name__)

last_signal = {}


def send(msg):
    print("ENVIANDO TELEGRAM...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})


@app.route("/")
def home():
    return "BOT ACTIVO"


def loop():

    print("🚀 LOOP INICIADO")

    send("🚀 BOT ACTIVO")

    model = train_model()

    while True:
        try:
            print("🔄 LOOP CORRIENDO")

            for sym in ["SPY", "QQQ"]:

                print(f"Evaluando: {sym}")

                sig = engine.signal(sym)

                if not sig:
                    print(f"{sym} ❌ SIN SEÑAL\n")
                    continue

                key = f"{sym}_{sig['direction']}"

                if last_signal.get(sym) == key:
                    print(f"{sym} ⚠️ DUPLICADO\n")
                    continue

                prob = predict(model, sig["score"])

                print(f"{sym} Prob ML: {prob}")

                if prob < 0.55:
                    print(f"{sym} ❌ PROB BAJA\n")
                    continue

                contracts = position_size(sig["premium"], prob)

                tp = engine.dynamic_tp(sig["score"], prob)

                trade_id = log_trade(
                    sig["symbol"],
                    sig["score"],
                    sig["direction"],
                    sig["price"],
                    sig["strike"],
                    sig["expiry"]
                )

                msg = (
                    f"🔥 {sig['direction']} {sym}\n"
                    f"Precio: {sig['price']}\n"
                    f"Score: {sig['score']}\n"
                    f"Prob: {round(prob*100,1)}%\n\n"
                    f"Strike: {sig['strike']}\n"
                    f"Exp: {sig['expiry']}\n\n"
                    f"Contratos: {contracts}\n"
                    f"SL: -30% | TP: +{tp}%\n\n"
                    f"ID: {trade_id}"
                )

                send(msg)

                last_signal[sym] = key

                print(f"{sym} ✅ SEÑAL ENVIADA\n")

            time.sleep(60)

        except Exception as e:
            print("ERROR LOOP:", e)
            time.sleep(10)


if __name__ == "__main__":

    init_db()

    t = threading.Thread(target=loop)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
