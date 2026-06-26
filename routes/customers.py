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

@customers_bp.route("/api/customers", methods=["POST"])
@login_required
def add_customer():
    d = request.json
    if not d.get("name") or not d.get("cin"):
        return jsonify({"error": "Name and CIN are required"}), 400
    with get_db() as c:
        c.execute("INSERT INTO customers (name,cin,phone,email,address) VALUES (:name,:cin,:phone,:email,:address)", d)
        cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": cid}), 201

@customers_bp.route("/api/customers/<int:cid>", methods=["PUT"])
@login_required
def update_customer(cid):
    d = request.json; d["id"] = cid
    if not d.get("name") or not d.get("cin"):
        return jsonify({"error": "Name and CIN are required"}), 400
    with get_db() as c:
        c.execute("UPDATE customers SET name=:name,cin=:cin,phone=:phone,email=:email,address=:address WHERE id=:id", d)
    return jsonify({"ok": True})

@customers_bp.route("/api/customers/<int:cid>", methods=["DELETE"])
@login_required
def delete_customer(cid):
    with get_db() as c:
        c.execute("DELETE FROM customers WHERE id=?", (cid,))
    return jsonify({"ok": True})
