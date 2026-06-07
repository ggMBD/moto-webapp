from flask import Blueprint, render_template, request, jsonify, session
from db import get_db, rows
from auth_helpers import login_required

purchases_bp = Blueprint("purchases", __name__)

@purchases_bp.route("/purchases")
@login_required
def page():
    return render_template("purchases.html")

@purchases_bp.route("/api/purchases", methods=["GET"])
@login_required
def get_purchases():
    with get_db() as c:
        return jsonify(rows(c.execute("""
            SELECT p.id, COALESCE(s.name,'—') as supplier,
                   pr.name as product, pr.ref,
                   p.qty, p.unit_price, p.total, p.note, p.created_at,
                   COALESCE(u.full_name, u.username,'—') as buyer
            FROM purchases p
            LEFT JOIN suppliers s  ON p.supplier_id=s.id
            LEFT JOIN products  pr ON p.product_id=pr.id
            LEFT JOIN users     u  ON p.user_id=u.id
            ORDER BY p.id DESC""").fetchall()))

@purchases_bp.route("/api/purchases", methods=["POST"])
@login_required
def add_purchase():
    d    = request.json
    qty  = int(d["qty"])
    unit = float(d["unit_price"])
    with get_db() as c:
        c.execute("""INSERT INTO purchases
                     (supplier_id,product_id,user_id,qty,unit_price,total,note)
                     VALUES (?,?,?,?,?,?,?)""",
                  (d.get("supplier_id"), d["product_id"],
                   session["user_id"], qty, unit, qty*unit, d.get("note","")))
        c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (qty, d["product_id"]))
    return jsonify({"ok": True}), 201
