import sqlite3

def init_db():
    conn = sqlite3.connect("trades.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        direction TEXT,
        price REAL,
        score REAL
    )
    """)

    conn.commit()
    conn.close()


def log_trade(symbol, direction, price, score):

    conn = sqlite3.connect("trades.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO trades (symbol, direction, price, score)
    VALUES (?, ?, ?, ?)
    """, (symbol, direction, price, score))

    conn.commit()
    conn.close()
