from flask import Blueprint, render_template, request, jsonify, session
from db import get_db, rows
from auth_helpers import login_required
from datetime import date, timedelta

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/sales")
@login_required
def page():
    return render_template("sales.html")

@sales_bp.route("/api/sales", methods=["GET"])
@login_required
def get_sales():
    from_date = request.args.get("from_date") or ""
    to_date   = request.args.get("to_date") or date.today().isoformat()

    base_select = """
        SELECT s.id, COALESCE(cu.name,'Walk-in') as customer,
               s.total, s.discount, s.note, s.created_at,
               COALESCE(u.full_name, u.username,'—') as seller
        FROM sales s
        LEFT JOIN customers cu ON s.customer_id=cu.id
        LEFT JOIN users u      ON s.user_id=u.id
    """

    with get_db() as c:
        if from_date:
            # Inclusive range: from 00:00:00 on from_date through 23:59:59 on to_date
            data = rows(c.execute(
                base_select + " WHERE DATE(s.created_at) BETWEEN ? AND ? ORDER BY s.id DESC",
                (from_date, to_date)
            ).fetchall())
        else:
            # No filter supplied: keep original behaviour (most recent 200 sales overall)
            data = rows(c.execute(base_select + " ORDER BY s.id DESC LIMIT 200").fetchall())

    return jsonify(data)

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
