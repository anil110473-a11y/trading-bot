from flask import Flask, request, redirect, session
from db import get_trades
import os, json

app = Flask(__name__)

# 🔐 Secret key (session के लिए जरूरी)
app.secret_key = os.getenv("SECRET_KEY", "supersecret123")

USERNAME = os.getenv("DASH_USER", "admin")
PASSWORD = os.getenv("DASH_PASS", "1234")

# ===== LOGIN =====
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")

        if user == USERNAME and pwd == PASSWORD:
            session["logged_in"] = True
            return redirect("/dashboard")
        else:
            return "<h2>❌ Wrong Username or Password</h2><a href='/'>Try Again</a>"

    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:100px;">
    <h2>🔐 AI BOT LOGIN</h2>
    <form method="post">
        <input name="username" placeholder="Username"><br><br>
        <input type="password" name="password" placeholder="Password"><br><br>
        <button>Login</button>
    </form>
    </body>
    </html>
    """

# ===== DASHBOARD =====
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/")

    trades = get_trades()

    total = len(trades)
    wins = len([t for t in trades if t[3] > 0])
    pnl = sum([t[3] for t in trades])
    winrate = (wins / total * 100) if total > 0 else 0

    # cumulative pnl
    cum = []
    c = 0
    for t in trades:
        c += t[3]
        cum.append(c)

    pnl_json = json.dumps(cum)

    return f"""
    <html>
    <head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
    body {{ font-family: Arial; background:#0f172a; color:white; margin:0; }}
    .container {{ padding:20px; }}
    .card {{ background:#1e293b; padding:15px; border-radius:10px; margin:10px; }}
    .grid {{ display:flex; flex-wrap:wrap; }}
    .kpi {{ flex:1; min-width:150px; text-align:center; }}
    .logout {{ float:right; color:red; text-decoration:none; }}
    table {{ width:100%; margin-top:20px; border-collapse:collapse; }}
    th, td {{ padding:10px; border-bottom:1px solid #334155; }}
    </style>
    </head>

    <body>
    <div class="container">

    <a href="/logout" class="logout">🔓 Logout</a>

    <h1>📊 AI PRO DASHBOARD</h1>

    <div class="grid">
        <div class="card kpi">💰 PnL<br>₹{round(pnl,2)}</div>
        <div class="card kpi">📈 Win Rate<br>{round(winrate,1)}%</div>
        <div class="card kpi">📊 Trades<br>{total}</div>
    </div>

    <div class="card">
        <h3>📈 PnL Chart</h3>
        <canvas id="pnlChart"></canvas>
    </div>

    <div class="card">
        <h3>📋 Trade History</h3>
        <table>
        <tr><th>Stock</th><th>Entry</th><th>Exit</th><th>PnL</th></tr>
        """ + "".join(
            [f"<tr><td>{t[0]}</td><td>{t[1]}</td><td>{t[2]}</td><td>{round(t[3],2)}</td></tr>" for t in trades]
        ) + """
        </table>
    </div>

    </div>

    <script>
    const pnlData = """ + pnl_json + """;

    new Chart(document.getElementById('pnlChart'), {{
        type: 'line',
        data: {{
            labels: pnlData.map((_,i)=>i+1),
            datasets: [{{
                label: 'PnL',
                data: pnlData,
                borderWidth: 2
            }}]
        }}
    }});
    </script>

    </body>
    </html>
    """

# ===== LOGOUT =====
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
