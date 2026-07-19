import base64
import os
import sqlite3
from functools import wraps

from flask import Flask, flash, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiare-questa-chiave")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/gestionale_tbs.db")

CATEGORIES = ["Ombelico", "Labret", "Clicker", "Top", "Charm", "Capezzolo", "Orecchio", "Curved barbell", "Nostril", "Septum", "Helix", "Tragus", "Daith", "Conch", "Rook", "Industrial", "Lobo", "Accessori", "Altro"]
MATERIALS = ["Titanio ASTM F136", "Oro 14K", "Oro 18K", "Acciaio", "Niobio", "Altro"]
COLORS = ["Argento", "Oro giallo", "Oro rosa", "Nero", "Blu", "Verde", "Viola", "Multicolore", "Altro"]
THREADS = ["Filettatura interna", "Filettatura esterna", "Threadless", "Clicker", "Altro"]

INITIAL_PRODUCTS = [
    ("TX51210G", "CHM-001", 1, 24.90), ("TX51210W", "CHM-002", 1, 24.90),
    ("TXV50314G-PPPK", "CHM-003", 1, 34.90), ("TXV50314-PPPK", "CHM-004", 1, 34.90),
    ("TJV5016-1608", "CUR-001", 1, 34.90), ("TL62-AQ1608", "TOP-001", 1, 19.90),
    ("TCS30505-AQ1416", "EAR-001", 1, 24.90), ("TA40701-1608LD", "CLK-001", 1, 99.90),
    ("TA40701-1610LD", "CLK-002", 1, 109.90), ("TA40701G-1610LD", "CLK-003", 1, 114.90),
    ("HTL00-16104", "LAB-001", 10, 14.90), ("HTM00-16083", "LAB-002", 3, 9.90),
    ("TD08-140858", "BEL-001", 5, 19.90), ("TD08-141058", "BEL-002", 5, 19.90),
    ("TE01-162.5", "TOP-003", 10, 9.90), ("TL08-16083", "LAB-003", 10, 19.90),
]

CSS = '''
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f5f5f7;color:#171717}
header{position:sticky;top:0;z-index:10;background:#111827;color:white;padding:14px;display:flex;gap:15px;flex-wrap:wrap;align-items:center}
header strong{margin-right:auto}header a{color:white;text-decoration:none}main{max-width:1180px;margin:20px auto;padding:0 14px}
.card{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:16px;margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.metric{font-size:28px;font-weight:bold}.muted{color:#6b7280}input,select,textarea,button{width:100%;padding:11px;border:1px solid #d1d5db;border-radius:9px;font:inherit}
textarea{min-height:90px;resize:vertical}button{background:#111827;color:white;font-weight:bold;cursor:pointer}.inline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;align-items:end}
.login{max-width:420px;margin:70px auto}.flash{padding:10px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;margin-bottom:12px}.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.product{background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden}.product.low{border-color:#fda4af;background:#fff7f8}.product-photo{width:100%;height:180px;object-fit:cover;background:#eef0f3;display:block}
.no-photo{height:180px;display:flex;align-items:center;justify-content:center;background:#eef0f3;color:#9ca3af;font-size:18px}.product-body{padding:13px}.product-title{font-size:19px;font-weight:bold}.price{font-size:23px;font-weight:bold;margin:8px 0}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;background:#eef2ff;margin:2px 4px 2px 0;font-size:12px}.actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}.actions form{margin:0}.actions button,.actions a{width:auto;padding:8px 10px;border-radius:8px;text-decoration:none;color:#fff;display:inline-block}
.secondary{background:#4b5563}.success{background:#047857}.danger{background:#b91c1c}.view{background:#1d4ed8}.detail{display:grid;grid-template-columns:minmax(240px,420px) 1fr;gap:20px}.detail-photo{width:100%;max-height:520px;object-fit:contain;background:#eef0f3;border-radius:12px}
dl{display:grid;grid-template-columns:150px 1fr;gap:9px}dt{font-weight:bold;color:#4b5563}dd{margin:0}@media(max-width:760px){header{font-size:14px}.detail{grid-template-columns:1fr}dl{grid-template-columns:115px 1fr}.product-photo,.no-photo{height:210px}}
'''

BASE = '''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }}</title><style>{{ css }}</style></head><body>{% if session.get("user") %}<header><strong>Gestionale TBS</strong><a href="{{ url_for('dashboard') }}">Dashboard</a><a href="{{ url_for('products') }}">Prodotti</a><a href="{{ url_for('logout') }}">Esci</a></header>{% endif %}<main>{% with messages=get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}{{ body|safe }}</main></body></html>'''

def infer_category(code):
    return {"BEL":"Ombelico","LAB":"Labret","CLK":"Clicker","TOP":"Top","CHM":"Charm","NIP":"Capezzolo","EAR":"Orecchio","CUR":"Curved barbell","TOOL":"Accessori"}.get((code or "").upper().split("-")[0], "Altro")

def connect():
    db = sqlite3.connect(DB_PATH); db.row_factory = sqlite3.Row; return db

def ensure_column(db, name, definition):
    if name not in [r["name"] for r in db.execute("PRAGMA table_info(products)").fetchall()]:
        db.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")

def init_db():
    with connect() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL);CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,supplier_code TEXT UNIQUE NOT NULL,brand_code TEXT UNIQUE NOT NULL,quantity INTEGER NOT NULL DEFAULT 0,price REAL NOT NULL DEFAULT 0);''')
        for name, definition in [("category","TEXT DEFAULT 'Altro'"),("photo_data","TEXT"),("material","TEXT"),("color","TEXT"),("size","TEXT"),("stone","TEXT"),("thread_type","TEXT"),("notes","TEXT")]: ensure_column(db,name,definition)
        db.execute("INSERT OR IGNORE INTO users(username,password_hash) VALUES(?,?)",(os.environ.get("ADMIN_USERNAME","admin"),generate_password_hash(os.environ.get("ADMIN_PASSWORD","cambia-subito"))))
        if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for s,b,q,p in INITIAL_PRODUCTS: db.execute("INSERT INTO products(supplier_code,brand_code,quantity,price,category,material,color) VALUES(?,?,?,?,?,?,?)",(s,b,q,p,infer_category(b),"Titanio ASTM F136","Argento"))
        db.commit()

def page(title, body, **ctx): return render_template_string(BASE,title=title,css=CSS,body=render_template_string(body,**ctx))
def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**k): return redirect(url_for("login")) if not session.get("user") else fn(*a,**k)
    return wrapped

def photo_data(upload):
    if not upload or not upload.filename: return None
    raw=upload.read(); return f"data:{upload.mimetype or 'image/jpeg'};base64,{base64.b64encode(raw).decode()}" if raw else None

def values(form):
    brand=form["brand_code"].strip().upper()
    return (form["supplier_code"].strip().upper(),brand,int(form["quantity"]),float(form["price"].replace(",",".")),form.get("category") or infer_category(brand),form.get("material",""),form.get("color",""),form.get("size",""),form.get("stone",""),form.get("thread_type",""),form.get("notes",""))

@app.get("/health")
def health(): return {"status":"ok","version":"0.3"}

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        with connect() as db: user=db.execute("SELECT * FROM users WHERE username=?",(request.form["username"].strip(),)).fetchone()
        if user and check_password_hash(user["password_hash"],request.form["password"]): session["user"]=user["username"]; return redirect(url_for("dashboard"))
        flash("Credenziali non corrette.")
    return page("Login",'''<div class="login card"><h1>Gestionale TBS</h1><p class="muted">Accesso riservato</p><form method="post"><p><input name="username" placeholder="Utente" required></p><p><input name="password" type="password" placeholder="Password" required></p><button>Accedi</button></form></div>''')

@app.get("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.get("/")
@login_required
def dashboard():
    with connect() as db:
        r=db.execute("SELECT COUNT(*) FROM products").fetchone()[0]; p=db.execute("SELECT COALESCE(SUM(quantity),0) FROM products").fetchone()[0]; l=db.execute("SELECT COUNT(*) FROM products WHERE quantity<=1").fetchone()[0]; f=db.execute("SELECT COUNT(*) FROM products WHERE COALESCE(photo_data,'')<>''").fetchone()[0]
    return page("Dashboard",'''<h1>Dashboard</h1><div class="grid"><div class="card"><div class="muted">Referenze</div><div class="metric">{{r}}</div></div><div class="card"><div class="muted">Pezzi disponibili</div><div class="metric">{{p}}</div></div><div class="card"><div class="muted">Scorte ≤ 1</div><div class="metric">{{l}}</div></div><div class="card"><div class="muted">Prodotti con foto</div><div class="metric">{{f}}</div></div></div>''',r=r,p=p,l=l,f=f)

@app.route("/products",methods=["GET","POST"])
@login_required
def products():
    if request.method=="POST":
        try:
            v=values(request.form); ph=photo_data(request.files.get("photo"))
            with connect() as db: db.execute("INSERT INTO products(supplier_code,brand_code,quantity,price,category,material,color,size,stone,thread_type,notes,photo_data) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",v+(ph,)); db.commit()
            flash("Prodotto aggiunto.")
        except Exception as e: flash(f"Errore: {e}")
    q=request.args.get("q","").strip(); cat=request.args.get("category",""); mat=request.args.get("material",""); col=request.args.get("color",""); av=request.args.get("availability","")
    sql="SELECT * FROM products WHERE (supplier_code LIKE ? OR brand_code LIKE ? OR COALESCE(notes,'') LIKE ?)"; params=[f"%{q}%",f"%{q}%",f"%{q}%"]
    for field,val in [("category",cat),("material",mat),("color",col)]:
        if val: sql+=f" AND {field}=?"; params.append(val)
    if av=="available": sql+=" AND quantity>0"
    elif av=="low": sql+=" AND quantity<=1"
    sql+=" ORDER BY category,brand_code"
    with connect() as db: rows=db.execute(sql,params).fetchall()
    return page("Prodotti",'''<h1>Prodotti</h1><div class="card"><h3>Filtri</h3><form class="inline" method="get"><input name="q" value="{{q}}" placeholder="Codice, brand o note"><select name="category"><option value="">Tutte le categorie</option>{% for x in categories %}<option {% if x==cat %}selected{% endif %}>{{x}}</option>{% endfor %}</select><select name="material"><option value="">Tutti i materiali</option>{% for x in materials %}<option {% if x==mat %}selected{% endif %}>{{x}}</option>{% endfor %}</select><select name="color"><option value="">Tutti i colori</option>{% for x in colors %}<option {% if x==col %}selected{% endif %}>{{x}}</option>{% endfor %}</select><select name="availability"><option value="">Qualsiasi disponibilità</option><option value="available" {% if av=='available' %}selected{% endif %}>Disponibili</option><option value="low" {% if av=='low' %}selected{% endif %}>Scorte basse</option></select><button>Filtra</button></form></div>
<div class="card"><h3>Aggiungi prodotto</h3><form class="inline" method="post" enctype="multipart/form-data"><input name="supplier_code" placeholder="Codice fornitore" required><input name="brand_code" placeholder="Codice brand" required><select name="category"><option value="">Categoria automatica</option>{% for x in categories %}<option>{{x}}</option>{% endfor %}</select><select name="material"><option value="">Materiale</option>{% for x in materials %}<option>{{x}}</option>{% endfor %}</select><select name="color"><option value="">Colore</option>{% for x in colors %}<option>{{x}}</option>{% endfor %}</select><input name="size" placeholder="Misura, es. 1.6×10"><input name="stone" placeholder="Pietra"><select name="thread_type"><option value="">Filettatura</option>{% for x in threads %}<option>{{x}}</option>{% endfor %}</select><input name="quantity" type="number" min="0" value="1" required><input name="price" placeholder="Prezzo" required><input name="photo" type="file" accept="image/*" capture="environment"><textarea name="notes" placeholder="Note"></textarea><button>Aggiungi</button></form></div>
<div class="gallery">{% for p in rows %}<article class="product {% if p.quantity<=1 %}low{% endif %}">{% if p.photo_data %}<img class="product-photo" src="{{p.photo_data}}">{% else %}<div class="no-photo">Nessuna foto</div>{% endif %}<div class="product-body"><div class="product-title">{{p.brand_code}}</div><div class="muted">{{p.supplier_code}}</div><span class="badge">{{p.category}}</span>{% if p.material %}<span class="badge">{{p.material}}</span>{% endif %}{% if p.color %}<span class="badge">{{p.color}}</span>{% endif %}<div>Quantità: <b>{{p.quantity}}</b></div><div class="price">€ {{'%.2f'|format(p.price)}}</div><div class="actions"><a class="view" href="{{url_for('product_detail',product_id=p.id)}}">Apri</a><form method="post" action="{{url_for('change_stock',product_id=p.id)}}"><input type="hidden" name="delta" value="-1"><button class="secondary">−1</button></form><form method="post" action="{{url_for('change_stock',product_id=p.id)}}"><input type="hidden" name="delta" value="1"><button class="success">+1</button></form><a class="secondary" href="{{url_for('edit_product',product_id=p.id)}}">Modifica</a><form method="post" action="{{url_for('delete_product',product_id=p.id)}}" onsubmit="return confirm('Eliminare il prodotto?')"><button class="danger">Elimina</button></form></div></div></article>{% endfor %}</div>''',rows=rows,q=q,cat=cat,mat=mat,col=col,av=av,categories=CATEGORIES,materials=MATERIALS,colors=COLORS,threads=THREADS)

@app.get("/products/<int:product_id>")
@login_required
def product_detail(product_id):
    with connect() as db: p=db.execute("SELECT * FROM products WHERE id=?",(product_id,)).fetchone()
    if not p: flash("Prodotto non trovato."); return redirect(url_for("products"))
    return page("Scheda prodotto",'''<p><a href="{{url_for('products')}}">← Torna ai prodotti</a></p><div class="card detail"><div>{% if p.photo_data %}<img class="detail-photo" src="{{p.photo_data}}">{% else %}<div class="no-photo" style="height:350px">Nessuna foto</div>{% endif %}</div><div><h1>{{p.brand_code}}</h1><div class="price">€ {{'%.2f'|format(p.price)}}</div><dl><dt>Codice fornitore</dt><dd>{{p.supplier_code}}</dd><dt>Categoria</dt><dd>{{p.category or '-'}}</dd><dt>Quantità</dt><dd>{{p.quantity}}</dd><dt>Materiale</dt><dd>{{p.material or '-'}}</dd><dt>Colore</dt><dd>{{p.color or '-'}}</dd><dt>Misura</dt><dd>{{p.size or '-'}}</dd><dt>Pietra</dt><dd>{{p.stone or '-'}}</dd><dt>Filettatura</dt><dd>{{p.thread_type or '-'}}</dd><dt>Note</dt><dd>{{p.notes or '-'}}</dd></dl><div class="actions"><a class="secondary" href="{{url_for('edit_product',product_id=p.id)}}">Modifica</a></div></div></div>''',p=p)

@app.route("/products/<int:product_id>/edit",methods=["GET","POST"])
@login_required
def edit_product(product_id):
    with connect() as db:
        p=db.execute("SELECT * FROM products WHERE id=?",(product_id,)).fetchone()
        if not p: flash("Prodotto non trovato."); return redirect(url_for("products"))
        if request.method=="POST":
            v=values(request.form); ph=photo_data(request.files.get("photo"))
            if ph: db.execute("UPDATE products SET supplier_code=?,brand_code=?,quantity=?,price=?,category=?,material=?,color=?,size=?,stone=?,thread_type=?,notes=?,photo_data=? WHERE id=?",v+(ph,product_id))
            else: db.execute("UPDATE products SET supplier_code=?,brand_code=?,quantity=?,price=?,category=?,material=?,color=?,size=?,stone=?,thread_type=?,notes=? WHERE id=?",v+(product_id,))
            db.commit(); flash("Prodotto aggiornato."); return redirect(url_for("product_detail",product_id=product_id))
    return page("Modifica prodotto",'''<h1>Modifica prodotto</h1><div class="card"><form method="post" enctype="multipart/form-data"><p><input name="supplier_code" value="{{p.supplier_code}}" required></p><p><input name="brand_code" value="{{p.brand_code}}" required></p><p><select name="category">{% for x in categories %}<option {% if x==p.category %}selected{% endif %}>{{x}}</option>{% endfor %}</select></p><p><select name="material"><option value="">Materiale</option>{% for x in materials %}<option {% if x==p.material %}selected{% endif %}>{{x}}</option>{% endfor %}</select></p><p><select name="color"><option value="">Colore</option>{% for x in colors %}<option {% if x==p.color %}selected{% endif %}>{{x}}</option>{% endfor %}</select></p><p><input name="size" value="{{p.size or ''}}" placeholder="Misura"></p><p><input name="stone" value="{{p.stone or ''}}" placeholder="Pietra"></p><p><select name="thread_type"><option value="">Filettatura</option>{% for x in threads %}<option {% if x==p.thread_type %}selected{% endif %}>{{x}}</option>{% endfor %}</select></p><p><input name="quantity" type="number" min="0" value="{{p.quantity}}" required></p><p><input name="price" value="{{p.price}}" required></p><p><input name="photo" type="file" accept="image/*" capture="environment"></p><p><textarea name="notes">{{p.notes or ''}}</textarea></p><button>Salva modifiche</button></form></div>''',p=p,categories=CATEGORIES,materials=MATERIALS,colors=COLORS,threads=THREADS)

@app.post("/products/<int:product_id>/stock")
@login_required
def change_stock(product_id):
    d=int(request.form["delta"])
    with connect() as db:
        p=db.execute("SELECT quantity FROM products WHERE id=?",(product_id,)).fetchone()
        if p and p["quantity"]+d>=0: db.execute("UPDATE products SET quantity=quantity+? WHERE id=?",(d,product_id)); db.commit(); flash("Quantità aggiornata.")
        else: flash("Quantità non valida.")
    return redirect(request.referrer or url_for("products"))

@app.post("/products/<int:product_id>/delete")
@login_required
def delete_product(product_id):
    with connect() as db: db.execute("DELETE FROM products WHERE id=?",(product_id,)); db.commit()
    flash("Prodotto eliminato."); return redirect(url_for("products"))

init_db()
if __name__ == "__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
