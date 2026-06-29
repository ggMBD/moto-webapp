from flask import Blueprint, render_template, request, jsonify, session
from db import get_db, rows, next_invoice_number
from auth_helpers import login_required

purchases_bp = Blueprint("purchases", __name__)

@purchases_bp.route("/purchases")
@login_required
def page():
    return render_template("purchases.html")

@purchases_bp.route("/api/purchases", methods=["GET"])
@login_required
def get_purchases():
    q = f"%{request.args.get('q','')}%"
    from_date = request.args.get("from_date","")
    to_date   = request.args.get("to_date","")
    with get_db() as c:
        base = """
            SELECT p.id, p.invoice_number, COALESCE(s.name,'—') as supplier,
                   pr.name as product, pr.ref,
                   p.qty, p.unit_price, p.total, p.note, p.created_at,
                   COALESCE(u.full_name, u.username,'—') as buyer
            FROM purchases p
            LEFT JOIN suppliers s  ON p.supplier_id=s.id
            LEFT JOIN products  pr ON p.product_id=pr.id
            LEFT JOIN users     u  ON p.user_id=u.id
        """
        if from_date and to_date:
            data = rows(c.execute(base + " WHERE DATE(p.created_at) BETWEEN ? AND ? ORDER BY p.id DESC", (from_date, to_date)).fetchall())
        elif q != "%%":
            data = rows(c.execute(base + " WHERE pr.name LIKE ? OR s.name LIKE ? ORDER BY p.id DESC", (q,q)).fetchall())
        else:
            data = rows(c.execute(base + " ORDER BY p.id DESC LIMIT 200").fetchall())
    return jsonify(data)

@purchases_bp.route("/api/purchases", methods=["POST"])
@login_required
def add_purchase():
    d    = request.json
    qty  = int(d["qty"])
    unit = float(d["unit_price"])
    with get_db() as c:
        inv = next_invoice_number(c, "purchases", "PO")
        c.execute("""INSERT INTO purchases
                     (invoice_number,supplier_id,product_id,user_id,qty,unit_price,total,note)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (inv, d.get("supplier_id"), d["product_id"],
                   session["user_id"], qty, unit, qty*unit, d.get("note","")))
        c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (qty, d["product_id"]))
    return jsonify({"ok": True, "invoice_number": inv}), 201

@purchases_bp.route("/api/purchases/<int:pid>", methods=["DELETE"])
@login_required
def delete_purchase(pid):
    with get_db() as c:
        p = c.execute("SELECT product_id, qty FROM purchases WHERE id=?", (pid,)).fetchone()
        if not p:
            return jsonify({"error": "Not found"}), 404
        c.execute("UPDATE products SET qty = qty - ? WHERE id=?", (p["qty"], p["product_id"]))
        c.execute("DELETE FROM purchases WHERE id=?", (pid,))
    return jsonify({"ok": True})
