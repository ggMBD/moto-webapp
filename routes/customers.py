from flask import Blueprint, render_template, request, jsonify
from db import get_db, rows
from auth_helpers import login_required

customers_bp = Blueprint("customers", __name__)

@customers_bp.route("/customers")
@login_required
def page():
    return render_template("customers.html")

@customers_bp.route("/api/customers", methods=["GET"])
@login_required
def get_customers():
    q = f"%{request.args.get('q','')}%"
    with get_db() as c:
        return jsonify(rows(c.execute(
            "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? OR cin LIKE ? ORDER BY name",
            (q,q,q)).fetchall()))

@customers_bp.route("/api/customers/<int:cid>", methods=["GET"])
@login_required
def get_customer(cid):
    with get_db() as c:
        cust = c.execute("SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
        if not cust:
            return jsonify({"error": "Not found"}), 404
        bikes = rows(c.execute("SELECT * FROM bikes WHERE owner_id=? ORDER BY id DESC", (cid,)).fetchall())
        sales = rows(c.execute("""
            SELECT s.id, s.invoice_number, s.total, s.payment_status, s.created_at
            FROM sales s WHERE s.customer_id=? ORDER BY s.id DESC LIMIT 10""", (cid,)).fetchall())
        repairs = rows(c.execute("""
            SELECT r.id, r.invoice_number, r.vehicle, r.status, r.total, r.payment_status, r.created_at
            FROM repairs r WHERE r.customer_id=? ORDER BY r.id DESC LIMIT 10""", (cid,)).fetchall())
    return jsonify({"customer": dict(cust), "bikes": bikes, "sales": sales, "repairs": repairs})

@customers_bp.route("/api/customers", methods=["POST"])
@login_required
def add_customer():
    d = request.json or {}
    if not d.get("name"):
        return jsonify({"error": "Name is required"}), 400
    payload = {
        "name": d.get("name",""), "cin": d.get("cin",""),
        "phone": d.get("phone",""), "email": d.get("email",""), "address": d.get("address",""),
    }
    with get_db() as c:
        c.execute("INSERT INTO customers (name,cin,phone,email,address) VALUES (:name,:cin,:phone,:email,:address)", payload)
        cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": cid}), 201

@customers_bp.route("/api/customers/<int:cid>", methods=["PUT"])
@login_required
def update_customer(cid):
    d = request.json or {}
    if not d.get("name"):
        return jsonify({"error": "Name is required"}), 400
    payload = {
        "id": cid, "name": d.get("name",""), "cin": d.get("cin",""),
        "phone": d.get("phone",""), "email": d.get("email",""), "address": d.get("address",""),
    }
    with get_db() as c:
        c.execute("UPDATE customers SET name=:name,cin=:cin,phone=:phone,email=:email,address=:address WHERE id=:id", payload)
    return jsonify({"ok": True})

@customers_bp.route("/api/customers/<int:cid>", methods=["DELETE"])
@login_required
def delete_customer(cid):
    with get_db() as c:
        c.execute("DELETE FROM customers WHERE id=?", (cid,))
    return jsonify({"ok": True})
