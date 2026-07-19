
import base64
import os
import sqlite3
from functools import wraps

from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiare-questa-chiave")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/gestionale_tbs.db")

CATEGORIES = [
    "Ombelico", "Labret", "Clicker", "Top", "Charm",
    "Capezzolo", "Orecchio", "Curved barbell", "Accessori", "Altro"
]

CSS = '''
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#f5f5f7;color:#171717}
header{background:#111827;color:white;padding:14px;display:flex;gap:15px;flex-wrap:wrap;align-items:center}
header strong{margin-right:auto} header a{color:white;text-decoration:none}
main{max-width:1120px;margin:20px auto;padding:0 14px}
.card{background:white;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.metric{font-size:28px;font-weight:bold}.muted{color:#6b7280}
table{width:100%;border-collapse:collapse} th,td{padding:9px;border-bottom:1px solid #e5e7eb;text-align:left;vertical-align:middle}
input,select,button{width:100%;padding:10px;border:1px solid #d1d5db;border-radius:8px}
button{background:#111827;color:white;font-weight:bold;cursor:pointer}
.inline{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;align-items:end}
.login{max-width:420px;margin:70px auto}.flash{padding:10px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;margin-bottom:12px}
.thumb{width:64px;height:64px;border-radius:8px;object-fit:cover;border:1px solid #e5e7eb;background:#f3f4f6}
.photo-placeholder{width:64px;height:64px;border-radius:8px;background:#f3f4f6;display:flex;align-items:center;justify-content:center;color:#9ca3af}
.actions{display:flex;gap:6px;flex-wrap:wrap}.actions form{margin:0}.actions button,.actions a{width:auto;padding:7px 10px;border-radius:7px;text-decoration:none;display:inline-block;color:white}
.low{background:#fff1f2}.danger{background:#b91c1c}.secondary{background:#4b5563}.success{background:#047857}
.product-cards{display:none}.product-card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:12px}
.product-head{display:flex;gap:12px}.product-info{flex:1}.price{font-size:20px;font-weight:bold}
@media(max-width:760px){
  table.desktop{display:none}.product-cards{display:block}
  header{font-size:14px}.actions button,.actions a{padding:8px 10px}
}
'''

BASE = '''
<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }}</title><style>{{ css }}</style></head><body>
{% if session.get("user") %}
<header><strong>Gestionale TBS</strong>
<a href="{{ url_for("dashboard") }}">Dashboard</a>
<a href="{{ url_for("products") }}">Prodotti</a>
<a href="{{ url_for("logout") }}">Esci</a></header>
{% endif %}
<main>
{% with messages=get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}
{{ body|safe }}
</main></body></html>
'''

def infer_category(brand_code):
    prefix = (brand_code or "").upper().split("-")[0]
    return {
        "BEL": "Ombelico", "LAB": "Labret", "CLK": "Clicker",
        "TOP": "Top", "CHM": "Charm", "NIP": "Capezzolo",
        "EAR": "Orecchio", "CUR": "Curved barbell", "TOOL": "Accessori"
    }.get(prefix, "Altro")

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def ensure_column(db, table, column, definition):
    existing = [r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products(
          id INTEGER PRIMARY KEY, supplier_code TEXT UNIQUE NOT NULL,
          brand_code TEXT UNIQUE NOT NULL, quantity INTEGER NOT NULL DEFAULT 0,
          price REAL NOT NULL DEFAULT 0);
        ''')
        ensure_column(db, "products", "category", "TEXT DEFAULT 'Altro'")
        ensure_column(db, "products", "photo_data", "TEXT")
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "cambia-subito")
        db.execute("INSERT OR IGNORE INTO users(username,password_hash) VALUES(?,?)",
                   (username, generate_password_hash(password)))
        rows = db.execute("SELECT id,brand_code,category FROM products").fetchall()
        for row in rows:
            if not row["category"] or row["category"] == "Altro":
                db.execute("UPDATE products SET category=? WHERE id=?",
                           (infer_category(row["brand_code"]), row["id"]))
        db.commit()

def page(title, body, **context):
    inner = render_template_string(body, **context)
    return render_template_string(BASE, title=title, css=CSS, body=inner)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def image_to_data_url(upload):
    if not upload or not upload.filename:
        return None
    raw = upload.read()
    if not raw:
        return None
    mime = upload.mimetype or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        with connect() as db:
            user = db.execute("SELECT * FROM users WHERE username=?",
                              (request.form["username"].strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Credenziali non corrette.")
    return page("Login", '''
    <div class="login card"><h1>Gestionale TBS</h1><p class="muted">Accesso riservato</p>
    <form method="post"><p><input name="username" placeholder="Utente" required></p>
    <p><input name="password" type="password" placeholder="Password" required></p>
    <button>Accedi</button></form></div>''')

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
        with_photo = db.execute("SELECT COUNT(*) FROM products WHERE photo_data IS NOT NULL AND photo_data<>''").fetchone()[0]
    return page("Dashboard", '''
    <h1>Dashboard</h1><div class="grid">
    <div class="card"><div class="muted">Referenze</div><div class="metric">{{ references }}</div></div>
    <div class="card"><div class="muted">Pezzi disponibili</div><div class="metric">{{ pieces }}</div></div>
    <div class="card"><div class="muted">Scorte ≤ 1</div><div class="metric">{{ low_stock }}</div></div>
    <div class="card"><div class="muted">Prodotti con foto</div><div class="metric">{{ with_photo }}</div></div>
    </div>''', references=references, pieces=pieces, low_stock=low_stock, with_photo=with_photo)

@app.route("/products", methods=["GET","POST"])
@login_required
def products():
    if request.method == "POST":
        try:
            brand_code = request.form["brand_code"].strip().upper()
            category = request.form.get("category") or infer_category(brand_code)
            photo_data = image_to_data_url(request.files.get("photo"))
            with connect() as db:
                db.execute('''INSERT INTO products
                  (supplier_code,brand_code,quantity,price,category,photo_data)
                  VALUES(?,?,?,?,?,?)''',
                  (request.form["supplier_code"].strip().upper(), brand_code,
                   int(request.form["quantity"]),
                   float(request.form["price"].replace(",",".")),
                   category, photo_data))
                db.commit()
            flash("Prodotto aggiunto.")
        except Exception as error:
            flash(f"Errore: {error}")

    query = request.args.get("q","").strip()
    category = request.args.get("category","").strip()
    availability = request.args.get("availability","").strip()

    sql = "SELECT * FROM products WHERE (supplier_code LIKE ? OR brand_code LIKE ?)"
    params = [f"%{query}%", f"%{query}%"]
    if category:
        sql += " AND category=?"
        params.append(category)
    if availability == "available":
        sql += " AND quantity>0"
    elif availability == "low":
        sql += " AND quantity<=1"
    sql += " ORDER BY category,brand_code"

    with connect() as db:
        rows = db.execute(sql, params).fetchall()

    return page("Prodotti", '''
    <h1>Prodotti</h1>
    <div class="card"><h3>Filtri</h3><form class="inline" method="get">
    <input name="q" value="{{ query }}" placeholder="Codice fornitore o brand">
    <select name="category"><option value="">Tutte le categorie</option>
    {% for item in categories %}<option value="{{ item }}" {% if item==selected_category %}selected{% endif %}>{{ item }}</option>{% endfor %}</select>
    <select name="availability"><option value="">Qualsiasi disponibilità</option>
    <option value="available" {% if availability=="available" %}selected{% endif %}>Disponibili</option>
    <option value="low" {% if availability=="low" %}selected{% endif %}>Scorte basse</option></select>
    <button>Filtra</button></form></div>

    <div class="card"><h3>Aggiungi prodotto</h3>
    <form class="inline" method="post" enctype="multipart/form-data">
    <input name="supplier_code" placeholder="Codice fornitore" required>
    <input name="brand_code" placeholder="Codice brand" required>
    <select name="category"><option value="">Categoria automatica</option>
    {% for item in categories %}<option>{{ item }}</option>{% endfor %}</select>
    <input name="quantity" type="number" min="0" value="1" required>
    <input name="price" inputmode="decimal" placeholder="Prezzo" required>
    <input name="photo" type="file" accept="image/*" capture="environment">
    <button>Aggiungi</button></form></div>

    <div class="card">
    <table class="desktop"><tr><th>Foto</th><th>Categoria</th><th>Fornitore</th><th>Brand</th><th>Q.tà</th><th>Prezzo</th><th>Azioni</th></tr>
    {% for row in rows %}<tr class="{% if row.quantity<=1 %}low{% endif %}">
    <td>{% if row.photo_data %}<img class="thumb" src="{{ row.photo_data }}">{% else %}<div class="photo-placeholder">Foto</div>{% endif %}</td>
    <td>{{ row.category }}</td><td>{{ row.supplier_code }}</td><td><b>{{ row.brand_code }}</b></td>
    <td>{{ row.quantity }}</td><td>€ {{ "%.2f"|format(row.price) }}</td>
    <td><div class="actions">
      <form method="post" action="{{ url_for('change_stock', product_id=row.id) }}"><input type="hidden" name="delta" value="-1"><button class="secondary">−</button></form>
      <form method="post" action="{{ url_for('change_stock', product_id=row.id) }}"><input type="hidden" name="delta" value="1"><button class="success">+</button></form>
      <a class="secondary" href="{{ url_for('edit_product', product_id=row.id) }}">Modifica</a>
      <form method="post" action="{{ url_for('delete_product', product_id=row.id) }}" onsubmit="return confirm('Eliminare questo prodotto?')"><button class="danger">Elimina</button></form>
    </div></td></tr>{% endfor %}</table>

    <div class="product-cards">{% for row in rows %}
    <div class="product-card {% if row.quantity<=1 %}low{% endif %}">
      <div class="product-head">
      {% if row.photo_data %}<img class="thumb" src="{{ row.photo_data }}">{% else %}<div class="photo-placeholder">Foto</div>{% endif %}
      <div class="product-info"><b>{{ row.brand_code }}</b><div>{{ row.supplier_code }}</div><div class="muted">{{ row.category }}</div>
      <div>Quantità: <b>{{ row.quantity }}</b></div><div class="price">€ {{ "%.2f"|format(row.price) }}</div></div></div>
      <div class="actions" style="margin-top:10px">
      <form method="post" action="{{ url_for('change_stock', product_id=row.id) }}"><input type="hidden" name="delta" value="-1"><button class="secondary">−1</button></form>
      <form method="post" action="{{ url_for('change_stock', product_id=row.id) }}"><input type="hidden" name="delta" value="1"><button class="success">+1</button></form>
      <a class="secondary" href="{{ url_for('edit_product', product_id=row.id) }}">Modifica</a>
      <form method="post" action="{{ url_for('delete_product', product_id=row.id) }}" onsubmit="return confirm('Eliminare questo prodotto?')"><button class="danger">Elimina</button></form>
      </div>
    </div>{% endfor %}</div>
    </div>''', rows=rows, query=query, categories=CATEGORIES,
    selected_category=category, availability=availability)

@app.route("/products/<int:product_id>/edit", methods=["GET","POST"])
@login_required
def edit_product(product_id):
    with connect() as db:
        product = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not product:
            flash("Prodotto non trovato.")
            return redirect(url_for("products"))
        if request.method == "POST":
            photo_data = image_to_data_url(request.files.get("photo"))
            values = (
                request.form["supplier_code"].strip().upper(),
                request.form["brand_code"].strip().upper(),
                int(request.form["quantity"]),
                float(request.form["price"].replace(",",".")),
                request.form["category"],
            )
            if photo_data:
                db.execute('''UPDATE products SET supplier_code=?,brand_code=?,quantity=?,
                    price=?,category=?,photo_data=? WHERE id=?''',
                    values + (photo_data, product_id))
            else:
                db.execute('''UPDATE products SET supplier_code=?,brand_code=?,quantity=?,
                    price=?,category=? WHERE id=?''',
                    values + (product_id,))
            db.commit()
            flash("Prodotto aggiornato.")
            return redirect(url_for("products"))

    return page("Modifica prodotto", '''
    <h1>Modifica prodotto</h1><div class="card">
    {% if product.photo_data %}<p><img class="thumb" src="{{ product.photo_data }}"></p>{% endif %}
    <form method="post" enctype="multipart/form-data">
    <p><input name="supplier_code" value="{{ product.supplier_code }}" required></p>
    <p><input name="brand_code" value="{{ product.brand_code }}" required></p>
    <p><select name="category">{% for item in categories %}<option {% if item==product.category %}selected{% endif %}>{{ item }}</option>{% endfor %}</select></p>
    <p><input name="quantity" type="number" min="0" value="{{ product.quantity }}" required></p>
    <p><input name="price" value="{{ product.price }}" required></p>
    <p><input name="photo" type="file" accept="image/*" capture="environment"></p>
    <button>Salva modifiche</button></form></div>''', product=product, categories=CATEGORIES)

@app.post("/products/<int:product_id>/stock")
@login_required
def change_stock(product_id):
    delta = int(request.form["delta"])
    with connect() as db:
        product = db.execute("SELECT quantity FROM products WHERE id=?", (product_id,)).fetchone()
        if product and product["quantity"] + delta >= 0:
            db.execute("UPDATE products SET quantity=quantity+? WHERE id=?", (delta, product_id))
            db.commit()
            flash("Quantità aggiornata.")
        else:
            flash("Quantità non valida.")
    return redirect(request.referrer or url_for("products"))

@app.post("/products/<int:product_id>/delete")
@login_required
def delete_product(product_id):
    with connect() as db:
        db.execute("DELETE FROM products WHERE id=?", (product_id,))
        db.commit()
    flash("Prodotto eliminato.")
    return redirect(url_for("products"))

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")))
