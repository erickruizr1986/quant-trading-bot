import sqlite3

def init_db():
    conn = sqlite3.connect("trades.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        score REAL,
        result TEXT
    )
    """)

    conn.commit()
    conn.close()
