import sqlite3
import pandas as pd

DB_NAME = "trades.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        direction TEXT,
        price REAL,
        strike REAL,
        premium REAL,
        score REAL
    )
    """)

    conn.commit()
    conn.close()


def log_trade(symbol, direction, price, strike, premium, score):

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    INSERT INTO trades (symbol, direction, price, strike, premium, score)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (symbol, direction, price, strike, premium, score))

    conn.commit()
    conn.close()


def get_trades():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM trades", conn)
    conn.close()
    return df
