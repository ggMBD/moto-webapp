from flask import Blueprint, render_template, request, jsonify
from db import get_db, rows
from auth_helpers import login_required

suppliers_bp = Blueprint("suppliers", __name__)

@suppliers_bp.route("/suppliers")
@login_required
def page():
    return render_template("suppliers.html")

@suppliers_bp.route("/api/suppliers", methods=["GET"])
@login_required
def get_suppliers():
    q = f"%{request.args.get('q','')}%"
    with get_db() as c:
        return jsonify(rows(c.execute(
            "SELECT * FROM suppliers WHERE name LIKE ? OR phone LIKE ? ORDER BY name",
            (q,q)).fetchall()))

@suppliers_bp.route("/api/suppliers", methods=["POST"])
@login_required
def add_supplier():
    d = request.json
    with get_db() as c:
        c.execute("INSERT INTO suppliers (name,phone,email,address,notes) VALUES (:name,:phone,:email,:address,:notes)", d)
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": sid}), 201

@suppliers_bp.route("/api/suppliers/<int:sid>", methods=["PUT"])
@login_required
def update_supplier(sid):
    d = request.json; d["id"] = sid
    with get_db() as c:
        c.execute("UPDATE suppliers SET name=:name,phone=:phone,email=:email,address=:address,notes=:notes WHERE id=:id", d)
    return jsonify({"ok": True})

@suppliers_bp.route("/api/suppliers/<int:sid>", methods=["DELETE"])
@login_required
def delete_supplier(sid):
    with get_db() as c:
        c.execute("DELETE FROM suppliers WHERE id=?", (sid,))
    return jsonify({"ok": True})
