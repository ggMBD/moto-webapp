import sqlite3
from flask import Blueprint, render_template, request, jsonify
from db import get_db, rows
from auth_helpers import login_required

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.route("/inventory")
@login_required
def page():
    return render_template("inventory.html")

@inventory_bp.route("/api/products", methods=["GET"])
@login_required
def get_products():
    q = f"%{request.args.get('q','')}%"
    with get_db() as c:
        return jsonify(rows(c.execute(
            "SELECT * FROM products WHERE name LIKE ? OR ref LIKE ? OR category LIKE ? OR brand LIKE ? ORDER BY name",
            (q,q,q,q)).fetchall()))

@inventory_bp.route("/api/products", methods=["POST"])
@login_required
def add_product():
    d = request.json
    with get_db() as c:
        try:
            c.execute("""INSERT INTO products (ref,name,category,brand,qty,buy_price,sell_price,min_stock)
                         VALUES (:ref,:name,:category,:brand,:qty,:buy_price,:sell_price,:min_stock)""", d)
            pid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"error": "Reference already exists"}), 409
    return jsonify({"id": pid}), 201

@inventory_bp.route("/api/products/<int:pid>", methods=["PUT"])
@login_required
def update_product(pid):
    d = request.json; d["id"] = pid
    with get_db() as c:
        c.execute("""UPDATE products SET ref=:ref,name=:name,category=:category,brand=:brand,
                     qty=:qty,buy_price=:buy_price,sell_price=:sell_price,min_stock=:min_stock
                     WHERE id=:id""", d)
    return jsonify({"ok": True})

@inventory_bp.route("/api/products/<int:pid>", methods=["DELETE"])
@login_required
def delete_product(pid):
    with get_db() as c:
        c.execute("DELETE FROM products WHERE id=?", (pid,))
    return jsonify({"ok": True})
