import psycopg2
import os

def connect():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_db():
    conn = connect()
    cur = conn.cursor()

    # ===== TRADES TABLE =====
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        stock TEXT,
        entry REAL,
        exit REAL,
        pnl REAL
    )
    """)

    # ===== POSITIONS TABLE =====
    cur.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        stock TEXT PRIMARY KEY,
        entry REAL
    )
    """)

    # ===== AI WEIGHTS TABLE (NEW) =====
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_weights (
        name TEXT PRIMARY KEY,
        value REAL
    )
    """)

    conn.commit()
    conn.close()

    # 🔥 Default weights insert (IMPORTANT)
    init_weights()


# ===== DEFAULT AI WEIGHTS =====
def init_weights():
    conn = connect()
    cur = conn.cursor()

    defaults = {
        "EMA": 25,
        "RSI": 15,
        "VWAP": 20,
        "MACD": 25
    }

    for k, v in defaults.items():
        cur.execute("""
        INSERT INTO ai_weights (name, value)
        VALUES (%s,%s)
        ON CONFLICT (name) DO NOTHING
        """, (k, v))

    conn.commit()
    conn.close()


# ===== LOAD WEIGHTS =====
def load_weights():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT name, value FROM ai_weights")
    rows = cur.fetchall()

    conn.close()

    return {r[0]: r[1] for r in rows}


# ===== UPDATE WEIGHTS (SELF LEARNING) =====
def update_weights(weights, pnl):
    conn = connect()
    cur = conn.cursor()

    step = 1  # 🔥 safe learning speed

    for key in weights:
        if pnl > 0:
            weights[key] += step
        else:
            weights[key] -= step

        # 🔒 limit (important)
        weights[key] = max(5, min(weights[key], 50))

        cur.execute("""
        UPDATE ai_weights SET value=%s WHERE name=%s
        """, (weights[key], key))

    conn.commit()
    conn.close()


# ===== OLD FUNCTIONS (UNCHANGED) =====

def save_trade(stock, entry, exit, pnl):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO trades (stock, entry, exit, pnl) VALUES (%s,%s,%s,%s)",
        (stock, entry, exit, pnl)
    )

    conn.commit()
    conn.close()


def get_trades():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT stock, entry, exit, pnl FROM trades ORDER BY id DESC")
    data = cur.fetchall()

    conn.close()
    return data


def save_position(stock, entry):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO positions (stock, entry) VALUES (%s,%s) ON CONFLICT (stock) DO NOTHING",
        (stock, entry)
    )

    conn.commit()
    conn.close()


def delete_position(stock):
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM positions WHERE stock=%s", (stock,))

    conn.commit()
    conn.close()


def load_positions():
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT stock, entry FROM positions")
    rows = cur.fetchall()

    conn.close()

    return {r[0]: {"entry": r[1]} for r in rows}
