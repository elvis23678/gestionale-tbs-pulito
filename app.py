import os
import sqlite3
from functools import wraps

from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiare-questa-chiave")
DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/gestionale_tbs.db")

CSS = '''
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f5f5f7;color:#171717}
header{background:#111827;color:white;padding:14px;display:flex;gap:15px;flex-wrap:wrap}
header strong{margin-right:auto}
header a{color:white;text-decoration:none}
main{max-width:1050px;margin:20px auto;padding:0 14px}
.card{background:white;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.metric{font-size:28px;font-weight:bold}
.muted{color:#6b7280}
table{width:100%;border-collapse:collapse}
th,td{padding:9px;border-bottom:1px solid #e5e7eb;text-align:left}
input,button{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:8px}
button{background:#111827;color:white;font-weight:bold}
.inline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.login{max-width:420px;margin:70px auto}
.flash{padding:10px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;margin-bottom:12px}
'''

BASE = '''
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title>
<style>{{ css }}</style>
</head>
<body>
{% if session.get("user") %}
<header>
<strong>Gestionale TBS</strong>
<a href="{{ url_for("dashboard") }}">Dashboard</a>
<a href="{{ url_for("products") }}">Prodotti</a>
<a href="{{ url_for("logout") }}">Esci</a>
</header>
{% endif %}
<main>
{% with messages=get_flashed_messages() %}
{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}
{% endwith %}
{{ body|safe }}
</main>
</body>
</html>
'''

INITIAL_PRODUCTS = [
    ("TX51210G", "CHM-001", 1, 24.90),
    ("TX51210W", "CHM-002", 1, 24.90),
    ("TXV50314G-PPPK", "CHM-003", 1, 34.90),
    ("TXV50314-PPPK", "CHM-004", 1, 34.90),
    ("TJV5016-1608", "CUR-001", 1, 34.90),
    ("TL62-AQ1608", "TOP-001", 1, 19.90),
    ("TCS30505-AQ1416", "EAR-001", 1, 24.90),
    ("TA40701-1608LD", "CLK-001", 1, 99.90),
    ("TA40701-1610LD", "CLK-002", 1, 109.90),
    ("TA40701G-1610LD", "CLK-003", 1, 114.90),
    ("HTL00-16104", "LAB-001", 10, 14.90),
    ("HTM00-16083", "LAB-002", 3, 9.90),
    ("TD08-140858", "BEL-001", 5, 19.90),
    ("TD08-141058", "BEL-002", 5, 19.90),
    ("TE01-162.5", "TOP-003", 10, 9.90),
    ("TL08-16083", "LAB-003", 10, 19.90),
]

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.executescript(
            '''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY,
                supplier_code TEXT UNIQUE NOT NULL,
                brand_code TEXT UNIQUE NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                price REAL NOT NULL DEFAULT 0
            );
            '''
        )
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "cambia-subito")
        db.execute(
            "INSERT OR IGNORE INTO users(username,password_hash) VALUES(?,?)",
            (username, generate_password_hash(password)),
        )
        if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO products(supplier_code,brand_code,quantity,price) VALUES(?,?,?,?)",
                INITIAL_PRODUCTS,
            )
        db.commit()

def page(title, body, **context):
    inner = render_template_string(body, **context)
    return render_template_string(BASE, title=title, css=CSS, body=inner)

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper

@app.get("/health")
def health():
    return {"status": "ok"}

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with connect() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username=?",
                (request.form["username"].strip(),),
            ).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Credenziali non corrette.")

    return page(
        "Login",
        '''
        <div class="login card">
        <h1>Gestionale TBS</h1>
        <p class="muted">Accesso riservato</p>
        <form method="post">
        <p><input name="username" placeholder="Utente" required></p>
        <p><input name="password" type="password" placeholder="Password" required></p>
        <button>Accedi</button>
        </form>
        </div>
        ''',
    )

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/")
@login_required
def dashboard():
    with connect() as db:
        references = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        pieces = db.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]
        low_stock = db.execute("SELECT COUNT(*) FROM products WHERE quantity<=1").fetchone()[0]
    return page(
        "Dashboard",
        '''
        <h1>Dashboard</h1>
        <div class="grid">
        <div class="card"><div class="muted">Referenze</div><div class="metric">{{ references }}</div></div>
        <div class="card"><div class="muted">Pezzi disponibili</div><div class="metric">{{ pieces }}</div></div>
        <div class="card"><div class="muted">Scorte ≤ 1</div><div class="metric">{{ low_stock }}</div></div>
        </div>
        ''',
        references=references,
        pieces=pieces,
        low_stock=low_stock,
    )

@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        try:
            with connect() as db:
                db.execute(
                    "INSERT INTO products(supplier_code,brand_code,quantity,price) VALUES(?,?,?,?)",
                    (
                        request.form["supplier_code"].strip(),
                        request.form["brand_code"].strip(),
                        int(request.form["quantity"]),
                        float(request.form["price"].replace(",", ".")),
                    ),
                )
                db.commit()
            flash("Prodotto aggiunto.")
        except Exception as error:
            flash(f"Errore: {error}")

    query = request.args.get("q", "").strip()
    with connect() as db:
        rows = db.execute(
            '''
            SELECT * FROM products
            WHERE supplier_code LIKE ? OR brand_code LIKE ?
            ORDER BY brand_code
            ''',
            (f"%{query}%", f"%{query}%"),
        ).fetchall()

    return page(
        "Prodotti",
        '''
        <h1>Prodotti</h1>
        <div class="card">
        <form class="inline" method="get">
        <input name="q" value="{{ query }}" placeholder="Cerca codice">
        <button>Cerca</button>
        </form>
        </div>
        <div class="card">
        <form class="inline" method="post">
        <input name="supplier_code" placeholder="Codice fornitore" required>
        <input name="brand_code" placeholder="Codice brand" required>
        <input name="quantity" type="number" min="0" value="1" required>
        <input name="price" placeholder="Prezzo" required>
        <button>Aggiungi</button>
        </form>
        </div>
        <div class="card">
        <table>
        <tr><th>Fornitore</th><th>Brand</th><th>Quantità</th><th>Prezzo</th></tr>
        {% for row in rows %}
        <tr>
        <td>{{ row.supplier_code }}</td>
        <td><b>{{ row.brand_code }}</b></td>
        <td>{{ row.quantity }}</td>
        <td>€ {{ "%.2f"|format(row.price) }}</td>
        </tr>
        {% endfor %}
        </table>
        </div>
        ''',
        rows=rows,
        query=query,
    )

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
