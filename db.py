import sqlite3
from datetime import datetime

DB = "trades.db"

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        symbol TEXT,
        direction TEXT,
        price REAL,
        score REAL,
        result REAL,
        pnl REAL
    )
    """)
    con.commit()
    con.close()

def log_trade(symbol, direction, price, score):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    INSERT INTO trades(time, symbol, direction, price, score, result, pnl)
    VALUES(?,?,?,?,?,?,?)
    """, (datetime.utcnow().isoformat(), symbol, direction, price, score, None, None))
    con.commit()
    con.close()

def update_trade(trade_id, result, pnl):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("UPDATE trades SET result=?, pnl=? WHERE id=?", (result, pnl, trade_id))
    con.commit()
    con.close()

def fetch_trades():
    con = sqlite3.connect(DB)
    df = None
    try:
        import pandas as pd
        df = pd.read_sql_query("SELECT * FROM trades", con)
    finally:
        con.close()
    return df
