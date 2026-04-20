import os
import threading
import time
import requests
from flask import Flask, jsonify

import engine
from db import init_db, log_trade, fetch_trades
from metrics import compute_metrics

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
    return "QUANT DASHBOARD LIVE 📊"


@app.route("/metrics")
def metrics():
    df = fetch_trades()
    return jsonify(compute_metrics(df))


@app.route("/trades")
def trades():
    df = fetch_trades()
    if df is None:
        return jsonify([])
    return df.tail(100).to_json(orient="records")


def loop():

    send("🚀 BOT QUANT OPCIONES ACTIVADO")

    while True:
        try:
            for sym in ["SPY", "QQQ"]:

                sig = engine.signal(sym)

                print("SIG:", sig)

                if sig:

                    msg = (
                        f"🎯 {sig['direction']} {sym}\n"
                        f"Precio: {sig['price']}\n\n"
                        f"📊 OPCIÓN:\n"
                        f"Strike: {sig['strike']}\n"
                        f"Prima: {sig['premium']}\n"
                        f"Delta: {sig['delta']}\n\n"
                        f"📈 Proyección:\n"
                        f"ROI estimado: {sig['roi']}%\n"
                        f"Score: {sig['score']}"
                    )

                    send(msg)

                    log_trade(
                        sig['symbol'],
                        sig['direction'],
                        sig['price'],
                        sig['score']
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
