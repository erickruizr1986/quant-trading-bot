import os, threading, time, requests
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
    log_trade("SPY", "CALL", 500, 9)

@app.route("/metrics")
def metrics():
    df = fetch_trades()
    return jsonify(compute_metrics(df))

@app.route("/trades")
def trades():
    df = fetch_trades()
    if df is None: return jsonify([])
    return df.tail(100).to_json(orient="records")

def loop():
    send("📊 QUANT SYSTEM + DASHBOARD ONLINE")

    print("LOOP CORRIENDO")

    while True:
        try:
            for sym in ["SPY","QQQ"]:
                print("Evaluando:", sym)
    
                sig = engine.signal(sym)
                
                if sig:
                    msg = (f"🎯 {sig['direction']} {sym}\n"
                           f"Precio: {sig['price']}\n"
                           f"Score: {sig['score']}/10\n"
                           f"Exp: 1–3 DTE")
                    send(msg)
                    log_trade("SPY", "CALL", 500, 8)
                    log_trade(sig['symbol'], sig['direction'], sig['price'], sig['score'])
            time.sleep(300)  # cada 5 min
        except Exception as e:
            print(e)
            time.sleep(60)

if __name__ == "__main__":
    init_db()

    # 🔥 PRUEBA FORZADA
    log_trade("TEST", "CALL", 999, 10)

    threading.Thread(target=loop).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
