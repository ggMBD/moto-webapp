"""
MotoShop Manager — Flask Backend (Production Ready)
Run locally:  python app.py
PythonAnywhere: configured via WSGI
"""

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import sqlite3, os
from datetime import datetime, date
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__, template_folder="templates", static_folder="static")

# ─── CONFIG ─────────────────────────────────────────────────
app.secret_key = os.environ.get("SECRET_KEY", "zmoto-change-this-in-production-xyz987")
DB_FILE = os.environ.get("DB_FILE", os.path.join(os.path.dirname(__file__), "motoshop.db"))

# ─── DATABASE ───────────────────────────────────────────────
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # better concurrency
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                full_name   TEXT DEFAULT '',
                role        TEXT DEFAULT 'staff',
                created_at  TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ref         TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                category    TEXT DEFAULT '',
                brand       TEXT DEFAULT '',
                qty         INTEGER DEFAULT 0,
                buy_price   REAL DEFAULT 0,
                sell_price  REAL DEFAULT 0,
                min_stock   INTEGER DEFAULT 5,
                created_at  TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS customers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                phone       TEXT DEFAULT '',
                email       TEXT DEFAULT '',
                address     TEXT DEFAULT '',
                notes       TEXT DEFAULT '',
                ts          REAL DEFAULT 0,
                created_at  TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                phone       TEXT DEFAULT '',
                email       TEXT DEFAULT '',
                address     TEXT DEFAULT '',
                notes       TEXT DEFAULT '',
                created_at  TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS sales (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                user_id     INTEGER,
                total       REAL DEFAULT 0,
                discount    REAL DEFAULT 0,
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS sale_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id     INTEGER NOT NULL,
                product_id  INTEGER NOT NULL,
                qty         INTEGER NOT NULL,
                unit_price  REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER,
                product_id  INTEGER NOT NULL,
                user_id     INTEGER,
                qty         INTEGER NOT NULL,
                unit_price  REAL DEFAULT 0,
                total       REAL DEFAULT 0,
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
        """)
        count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            c.execute(
                "INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                ("admin", generate_password_hash("admin123"), "Administrator", "admin")
            )
            print("\n  👤  Default admin — username: admin  password: admin123")
            print("      ⚠️   Change the password after first login!\n")

def rows_to_list(rows):
    return [dict(r) for r in rows]

# ─── AUTH HELPERS ───────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin only"}), 403
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

# ─── ERROR HANDLERS ─────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return redirect(url_for("index"))

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Server error", "detail": str(e)}), 500

# ─── AUTH ROUTES ────────────────────────────────────────────
@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    d = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "")
    with get_db() as c:
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid username or password"}), 401
    session.permanent = True
    session["user_id"]   = user["id"]
    session["username"]  = user["username"]
    session["full_name"] = user["full_name"]
    session["role"]      = user["role"]
    return jsonify({"ok": True, "role": user["role"], "full_name": user["full_name"]})

@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/auth/me")
def api_me():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "user_id":   session["user_id"],
        "username":  session["username"],
        "full_name": session["full_name"],
        "role":      session["role"],
    })

# ─── USER MANAGEMENT ────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
@login_required
@admin_required
def get_users():
    with get_db() as c:
        rows = c.execute("SELECT id,username,full_name,role,created_at FROM users ORDER BY id").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/users", methods=["POST"])
@login_required
@admin_required
def add_user():
    d = request.json
    if not d.get("username") or not d.get("password"):
        return jsonify({"error": "Username and password required"}), 400
    with get_db() as c:
        try:
            c.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                      (d["username"].strip(), generate_password_hash(d["password"]),
                       d.get("full_name",""), d.get("role","staff")))
            uid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 409
    return jsonify({"id": uid}), 201

@app.route("/api/users/<int:uid>", methods=["PUT"])
@login_required
@admin_required
def update_user(uid):
    d = request.json
    with get_db() as c:
        if d.get("password"):
            c.execute("UPDATE users SET full_name=?,role=?,password=? WHERE id=?",
                      (d.get("full_name",""), d.get("role","staff"), generate_password_hash(d["password"]), uid))
        else:
            c.execute("UPDATE users SET full_name=?,role=? WHERE id=?",
                      (d.get("full_name",""), d.get("role","staff"), uid))
    return jsonify({"ok": True})

@app.route("/api/users/<int:uid>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(uid):
    if uid == session.get("user_id"):
        return jsonify({"error": "Cannot delete your own account"}), 400
    with get_db() as c:
        c.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({"ok": True})

@app.route("/api/users/<int:uid>/password", methods=["PUT"])
@login_required
def change_password(uid):
    if uid != session["user_id"] and session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    d = request.json
    if not d.get("new_password"):
        return jsonify({"error": "new_password required"}), 400
    with get_db() as c:
        c.execute("UPDATE users SET password=? WHERE id=?",
                  (generate_password_hash(d["new_password"]), uid))
    return jsonify({"ok": True})

# ─── MAIN PAGE ──────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html")

# ─── DASHBOARD ──────────────────────────────────────────────
@app.route("/api/dashboard")
@login_required
def dashboard():
    today = date.today().isoformat()
    with get_db() as c:
        return jsonify({
            "products":    c.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "customers":   c.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "suppliers":   c.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
            "sales_today": c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0],
            "low_stock":   rows_to_list(c.execute("SELECT id,ref,name,qty,min_stock FROM products WHERE qty <= min_stock ORDER BY qty").fetchall()),
            "recent_sales": rows_to_list(c.execute("""
                SELECT s.id, COALESCE(cu.name,'Walk-in') as customer, s.total, s.created_at,
                       COALESCE(u.full_name, u.username, '—') as seller
                FROM sales s LEFT JOIN customers cu ON s.customer_id=cu.id
                LEFT JOIN users u ON s.user_id=u.id
                ORDER BY s.id DESC LIMIT 5""").fetchall()),
        })

# ─── PRODUCTS ───────────────────────────────────────────────
@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    q = f"%{request.args.get('q','')}%"
    with get_db() as c:
        rows = c.execute("""SELECT * FROM products WHERE name LIKE ? OR ref LIKE ? OR category LIKE ? OR brand LIKE ?
                            ORDER BY name""", (q,q,q,q)).fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/products", methods=["POST"])
@login_required
def add_product():
    d = request.json
    with get_db() as c:
        try:
            c.execute("""INSERT INTO products (ref,name,category,brand,qty,buy_price,sell_price,min_stock)
                         VALUES (:ref,:name,:category,:brand,:qty,:buy_price,:sell_price,:min_stock)""", d)
            pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"error": "Ref already exists"}), 409
    return jsonify({"id": pid}), 201

@app.route("/api/products/<int:pid>", methods=["PUT"])
@login_required
def update_product(pid):
    d = request.json; d["id"] = pid
    with get_db() as c:
        c.execute("""UPDATE products SET ref=:ref,name=:name,category=:category,brand=:brand,
                     qty=:qty,buy_price=:buy_price,sell_price=:sell_price,min_stock=:min_stock WHERE id=:id""", d)
    return jsonify({"ok": True})

@app.route("/api/products/<int:pid>", methods=["DELETE"])
@login_required
def delete_product(pid):
    with get_db() as c:
        c.execute("DELETE FROM products WHERE id=?", (pid,))
    return jsonify({"ok": True})

# ─── CUSTOMERS ──────────────────────────────────────────────
@app.route("/api/customers", methods=["GET"])
@login_required
def get_customers():
    q = f"%{request.args.get('q','')}%"
    with get_db() as c:
        rows = c.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name", (q,q)).fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/customers", methods=["POST"])
@login_required
def add_customer():
    d = request.json
    with get_db() as c:
        c.execute("INSERT INTO customers (name,phone,email,address,notes) VALUES (:name,:phone,:email,:address,:notes)", d)
        cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": cid}), 201

@app.route("/api/customers/<int:cid>", methods=["PUT"])
@login_required
def update_customer(cid):
    d = request.json; d["id"] = cid
    with get_db() as c:
        c.execute("UPDATE customers SET name=:name,phone=:phone,email=:email,address=:address,notes=:notes WHERE id=:id", d)
    return jsonify({"ok": True})

@app.route("/api/customers/<int:cid>", methods=["DELETE"])
@login_required
def delete_customer(cid):
    with get_db() as c:
        c.execute("DELETE FROM customers WHERE id=?", (cid,))
    return jsonify({"ok": True})

# ─── SUPPLIERS ──────────────────────────────────────────────
@app.route("/api/suppliers", methods=["GET"])
@login_required
def get_suppliers():
    q = f"%{request.args.get('q','')}%"
    with get_db() as c:
        rows = c.execute("SELECT * FROM suppliers WHERE name LIKE ? OR phone LIKE ? ORDER BY name", (q,q)).fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/suppliers", methods=["POST"])
@login_required
def add_supplier():
    d = request.json
    with get_db() as c:
        c.execute("INSERT INTO suppliers (name,phone,email,address,notes) VALUES (:name,:phone,:email,:address,:notes)", d)
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": sid}), 201

@app.route("/api/suppliers/<int:sid>", methods=["PUT"])
@login_required
def update_supplier(sid):
    d = request.json; d["id"] = sid
    with get_db() as c:
        c.execute("UPDATE suppliers SET name=:name,phone=:phone,email=:email,address=:address,notes=:notes WHERE id=:id", d)
    return jsonify({"ok": True})

@app.route("/api/suppliers/<int:sid>", methods=["DELETE"])
@login_required
def delete_supplier(sid):
    with get_db() as c:
        c.execute("DELETE FROM suppliers WHERE id=?", (sid,))
    return jsonify({"ok": True})

# ─── SALES ──────────────────────────────────────────────────
@app.route("/api/sales", methods=["GET"])
@login_required
def get_sales():
    with get_db() as c:
        rows = c.execute("""
            SELECT s.id, COALESCE(cu.name,'Walk-in') as customer, s.total, s.discount, s.note, s.created_at,
                   COALESCE(u.full_name, u.username, '—') as seller
            FROM sales s LEFT JOIN customers cu ON s.customer_id=cu.id
            LEFT JOIN users u ON s.user_id=u.id
            ORDER BY s.id DESC LIMIT 200""").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/sales", methods=["POST"])
@login_required
def add_sale():
    d = request.json
    items = d.get("items", [])
    if not items:
        return jsonify({"error": "No items"}), 400
    discount = float(d.get("discount", 0))
    total = sum(float(i["qty"]) * float(i["unit_price"]) for i in items) - discount
    with get_db() as c:
        for item in items:
            row = c.execute("SELECT qty FROM products WHERE id=?", (item["product_id"],)).fetchone()
            if not row or row["qty"] < item["qty"]:
                return jsonify({"error": f"Insufficient stock for product #{item['product_id']}"}), 400
        c.execute("INSERT INTO sales (customer_id,user_id,total,discount,note) VALUES (?,?,?,?,?)",
                  (d.get("customer_id"), session["user_id"], max(total,0), discount, d.get("note","")))
        sale_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            c.execute("INSERT INTO sale_items (sale_id,product_id,qty,unit_price) VALUES (?,?,?,?)",
                      (sale_id, item["product_id"], item["qty"], item["unit_price"]))
            c.execute("UPDATE products SET qty = qty - ? WHERE id=?", (item["qty"], item["product_id"]))
            if d.get("customer_id"):
                c.execute("UPDATE customers SET ts = ts + ? WHERE id=?", (max(total,0), d["customer_id"]))
    return jsonify({"id": sale_id, "total": max(total,0)}), 201

# ─── PURCHASES ──────────────────────────────────────────────
@app.route("/api/purchases", methods=["GET"])
@login_required
def get_purchases():
    with get_db() as c:
        rows = c.execute("""
            SELECT p.id, COALESCE(s.name,'—') as supplier, pr.name as product, pr.ref,
                   p.qty, p.unit_price, p.total, p.note, p.created_at,
                   COALESCE(u.full_name, u.username, '—') as buyer
            FROM purchases p
            LEFT JOIN suppliers s  ON p.supplier_id=s.id
            LEFT JOIN products pr  ON p.product_id=pr.id
            LEFT JOIN users u      ON p.user_id=u.id
            ORDER BY p.id DESC""").fetchall()
    return jsonify(rows_to_list(rows))

@app.route("/api/purchases", methods=["POST"])
@login_required
def add_purchase():
    d = request.json
    qty = int(d["qty"]); unit = float(d["unit_price"])
    with get_db() as c:
        c.execute("INSERT INTO purchases (supplier_id,product_id,user_id,qty,unit_price,total,note) VALUES (?,?,?,?,?,?,?)",
                  (d.get("supplier_id"), d["product_id"], session["user_id"], qty, unit, qty*unit, d.get("note","")))
        c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (qty, d["product_id"]))
    return jsonify({"ok": True}), 201

# ─── REPORTS ────────────────────────────────────────────────
@app.route("/api/reports")
@login_required
def get_reports():
    with get_db() as c:
        return jsonify({
            "overview": {
                "total_sales":       c.execute("SELECT COUNT(*) FROM sales").fetchone()[0],
                "total_revenue":     c.execute("SELECT COALESCE(SUM(total),0) FROM sales").fetchone()[0],
                "total_stock_value": c.execute("SELECT COALESCE(SUM(qty*buy_price),0) FROM products").fetchone()[0],
                "low_stock_count":   c.execute("SELECT COUNT(*) FROM products WHERE qty <= min_stock").fetchone()[0],
            },
            "top_products": rows_to_list(c.execute("""
                SELECT p.name, SUM(si.qty) as total_sold, SUM(si.qty*si.unit_price) as revenue
                FROM sale_items si JOIN products p ON si.product_id=p.id
                GROUP BY p.id ORDER BY total_sold DESC LIMIT 10""").fetchall()),
            "sales_by_customer": rows_to_list(c.execute("""
                SELECT COALESCE(cu.name,'Walk-in') as customer, COUNT(s.id) as nb_sales, SUM(s.total) as total_spent
                FROM sales s LEFT JOIN customers cu ON s.customer_id=cu.id
                GROUP BY s.customer_id ORDER BY total_spent DESC LIMIT 10""").fetchall()),
            "stock_value": rows_to_list(c.execute("""
                SELECT ref,name,qty,qty*buy_price as stock_value
                FROM products ORDER BY stock_value DESC LIMIT 20""").fetchall()),
            "monthly_sales": rows_to_list(c.execute("""
                SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as nb, SUM(total) as revenue
                FROM sales GROUP BY month ORDER BY month DESC LIMIT 12""").fetchall()),
            "sales_by_user": rows_to_list(c.execute("""
                SELECT COALESCE(u.full_name, u.username,'Unknown') as seller,
                       COUNT(s.id) as nb_sales, SUM(s.total) as total_revenue
                FROM sales s LEFT JOIN users u ON s.user_id=u.id
                GROUP BY s.user_id ORDER BY total_revenue DESC""").fetchall()),
        })

# ─── RUN ────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("\n  🏍  Z-MOTO Manager — http://localhost:5000\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
