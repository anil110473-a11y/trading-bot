from db import init_db, save_trade, save_position, delete_position, load_positions
from db import load_weights, update_weights   # 🔥 NEW
import yfinance as yf
import pandas as pd
import time, os, requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

positions = {}
last_trade_time = {}
highest_price = {}

# 🔥 AI weights (global)
weights = {}

STOCKS = [
"HDFCBANK.NS","ICICIBANK.NS","SBIN.NS",
"TCS.NS","INFY.NS","WIPRO.NS",
"RELIANCE.NS","TATASTEEL.NS","HINDZINC.NS",
"HINDCOPPER.NS","SUNPHARMA.NS","DRREDDY.NS",
"CIPLA.NS","COFORGE.NS","TRENT.NS"
]

# ===== TELEGRAM =====
def send(msg):
    try:
        if TOKEN:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg}
            )
        print(msg)
    except:
        print("Telegram error")

# ===== SAFE VALUE =====
def safe(x):
    try:
        if hasattr(x, "values"):
            return float(x.values[0])
        return float(x)
    except:
        return 0.0

# ===== DATA =====
def get_df(stock, interval="5m"):
    for _ in range(3):
        try:
            df = yf.download(stock, period="2d", interval=interval, progress=False)
            if df is None or df.empty or len(df) < 50:
                return None
            return df
        except:
            time.sleep(2)
    return None

# ===== INDICATORS =====
def indicators(df):
    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["EMA5"] = df["Close"].ewm(span=5).mean()
    df["EMA15"] = df["Close"].ewm(span=15).mean()

    df["RET"] = df["Close"].pct_change()
    df["RSI"] = df["RET"].rolling(14).mean() * 100

    df["VWAP"] = (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()

    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    # MACD
    df["EMA12"] = df["Close"].ewm(span=12).mean()
    df["EMA26"] = df["Close"].ewm(span=26).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9).mean()

    return df.dropna()

# ===== AI SCORE (🔥 WEIGHT BASED) =====
def ai_score(row):
    score = 0

    score += weights.get("EMA", 25) if safe(row["EMA5"]) > safe(row["EMA15"]) else -weights.get("EMA", 25)
    score += weights.get("RSI", 15) if safe(row["RSI"]) > 0 else -weights.get("RSI", 15)
    score += weights.get("VWAP", 20) if safe(row["Close"]) > safe(row["VWAP"]) else -weights.get("VWAP", 20)
    score += weights.get("MACD", 25) if safe(row["MACD"]) > safe(row["MACD_SIGNAL"]) else -weights.get("MACD", 25)

    return score

# ===== BOT =====
def run():
    global positions, highest_price, weights

    send("🚀 V9 AI POWER BOT STARTED")
    init_db()

    # 🔥 load AI weights
    weights = load_weights()
    send(f"🧠 AI Weights Loaded: {weights}")

    positions = load_positions()

    for s in positions:
        highest_price[s] = positions[s]["entry"]

    if positions:
        send(f"♻️ Restored Positions: {positions}")

    last_heartbeat = time.time()

    while True:
        try:
            # ===== NIFTY TREND =====
            nifty_df = get_df("^NSEI")
            nifty_trend = True

            if nifty_df is not None:
                nifty_df = indicators(nifty_df)
                if not nifty_df.empty:
                    last_nifty = nifty_df.iloc[-1]
                    nifty_trend = safe(last_nifty["EMA5"]) > safe(last_nifty["EMA15"])

            for s in STOCKS:
                try:
                    df5 = get_df(s, "5m")
                    df15 = get_df(s, "15m")

                    if df5 is None or df15 is None:
                        continue

                    df5 = indicators(df5)
                    df15 = indicators(df15)

                    if df5.empty or df15.empty:
                        continue

                    last5 = df5.iloc[-1]
                    last15 = df15.iloc[-1]

                    score = ai_score(last5)
                    price = safe(last5["Close"])
                    volume = safe(last5["Volume"])
                    vol_avg = safe(last5["VOL_AVG"])

                    pos = positions.get(s)

                    # ===== FILTERS =====
                    trend_ok = safe(last5["EMA5"]) > safe(last5["EMA15"])
                    volume_ok = volume > vol_avg
                    mtf_ok = safe(last15["EMA5"]) > safe(last15["EMA15"])

                    now = time.time()
                    last_time = last_trade_time.get(s, 0)
                    cooldown = 300

                    # ===== ENTRY =====
                    if score >= 60 and not pos and trend_ok and volume_ok and mtf_ok and nifty_trend and (now - last_time > cooldown):
                        positions[s] = {"entry": price}
                        save_position(s, price)
                        highest_price[s] = price
                        last_trade_time[s] = now

                        send(f"🟢 BUY {s} @ {price} | Score {score}")

                    # ===== TRAILING SL =====
                    if pos:
                        highest_price[s] = max(highest_price.get(s, price), price)
                        trail_sl = highest_price[s] * 0.98

                        if price < trail_sl:
                            pnl = price - pos["entry"]

                            save_trade(s, pos["entry"], price, pnl)
                            delete_position(s)

                            # 🔥 AI LEARNING
                            update_weights(weights, pnl)

                            send(f"🔒 TRAIL EXIT {s} ₹{round(pnl,2)}")

                            del positions[s]
                            del highest_price[s]
                            continue

                    # ===== NORMAL EXIT =====
                    elif pos and score <= -60:
                        pnl = price - pos["entry"]

                        save_trade(s, pos["entry"], price, pnl)
                        delete_position(s)

                        # 🔥 AI LEARNING
                        update_weights(weights, pnl)

                        send(f"🔁 EXIT {s} ₹{round(pnl,2)}")

                        del positions[s]
                        if s in highest_price:
                            del highest_price[s]

                except Exception as stock_error:
                    print("STOCK ERROR:", s, stock_error)

            # ===== HEARTBEAT =====
            if time.time() - last_heartbeat > 1800:
                send("🤖 BOT RUNNING OK")
                last_heartbeat = time.time()

            time.sleep(90)

        except Exception as e:
            print("LOOP ERROR:", e)
            send(f"⚠️ LOOP ERROR: {e}")
            time.sleep(5)

# ===== MASTER LOOP =====
def start():
    while True:
        try:
            run()
        except Exception as e:
            print("CRASH:", e)
            send(f"🚨 BOT CRASHED: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start()
