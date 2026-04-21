import sqlite3

DB = "trades.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        score REAL,
        direction TEXT,
        entry REAL,
        strike REAL,
        expiry TEXT,
        result TEXT,
        roi REAL
    )
    """)

    conn.commit()
    conn.close()


def log_trade(symbol, score, direction, entry, strike, expiry):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT INTO trades (symbol, score, direction, entry, strike, expiry, result, roi)
    VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
    """, (symbol, score, direction, entry, strike, expiry))

    trade_id = c.lastrowid

    conn.commit()
    conn.close()

    return trade_id


def update_trade(trade_id, result, roi):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    UPDATE trades
    SET result=?, roi=?
    WHERE id=?
    """, (result, roi, trade_id))

    conn.commit()
    conn.close()
