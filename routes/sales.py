from flask import Blueprint, render_template, request, jsonify, session
from db import get_db, rows
from auth_helpers import login_required

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/sales")
@login_required
def page():
    return render_template("sales.html")

@sales_bp.route("/api/sales", methods=["GET"])
@login_required
def get_sales():
    with get_db() as c:
        return jsonify(rows(c.execute("""
            SELECT s.id, COALESCE(cu.name,'Walk-in') as customer,
                   s.total, s.discount, s.note, s.created_at,
                   COALESCE(u.full_name, u.username,'—') as seller
            FROM sales s
            LEFT JOIN customers cu ON s.customer_id=cu.id
            LEFT JOIN users u      ON s.user_id=u.id
            ORDER BY s.id DESC LIMIT 200""").fetchall()))

@sales_bp.route("/api/sales", methods=["POST"])
@login_required
def add_sale():
    d     = request.json
    items = d.get("items", [])
    if not items:
        return jsonify({"error": "No items"}), 400
    discount = float(d.get("discount", 0))
    total    = sum(float(i["qty"]) * float(i["unit_price"]) for i in items) - discount
    with get_db() as c:
        for item in items:
            row = c.execute("SELECT qty FROM products WHERE id=?", (item["product_id"],)).fetchone()
            if not row or row["qty"] < item["qty"]:
                return jsonify({"error": f"Not enough stock for product #{item['product_id']}"}), 400
        c.execute("INSERT INTO sales (customer_id,user_id,total,discount,note) VALUES (?,?,?,?,?)",
                  (d.get("customer_id"), session["user_id"], max(total,0), discount, d.get("note","")))
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            c.execute("INSERT INTO sale_items (sale_id,product_id,qty,unit_price) VALUES (?,?,?,?)",
                      (sid, item["product_id"], item["qty"], item["unit_price"]))
            c.execute("UPDATE products SET qty = qty - ? WHERE id=?", (item["qty"], item["product_id"]))
            if d.get("customer_id"):
                c.execute("UPDATE customers SET ts = ts + ? WHERE id=?", (max(total,0), d["customer_id"]))
    return jsonify({"id": sid, "total": max(total,0)}), 201
