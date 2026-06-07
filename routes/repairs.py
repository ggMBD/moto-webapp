from flask import Blueprint, render_template, request, jsonify, session
from db import get_db, rows
from auth_helpers import login_required

repairs_bp = Blueprint("repairs", __name__)

STATUSES = ["pending", "in_progress", "waiting_parts", "done", "cancelled"]

@repairs_bp.route("/repairs")
@login_required
def page():
    return render_template("repairs.html")

@repairs_bp.route("/api/repairs", methods=["GET"])
@login_required
def get_repairs():
    status = request.args.get("status", "")
    q      = f"%{request.args.get('q','')}%"
    with get_db() as c:
        if status:
            data = rows(c.execute("""
                SELECT r.*, COALESCE(cu.name,'—') as customer_name,
                       COALESCE(u.full_name, u.username,'—') as technician
                FROM repairs r
                LEFT JOIN customers cu ON r.customer_id=cu.id
                LEFT JOIN users u      ON r.user_id=u.id
                WHERE r.status=? AND (cu.name LIKE ? OR r.vehicle LIKE ?)
                ORDER BY r.id DESC""", (status, q, q)).fetchall())
        else:
            data = rows(c.execute("""
                SELECT r.*, COALESCE(cu.name,'—') as customer_name,
                       COALESCE(u.full_name, u.username,'—') as technician
                FROM repairs r
                LEFT JOIN customers cu ON r.customer_id=cu.id
                LEFT JOIN users u      ON r.user_id=u.id
                WHERE (cu.name LIKE ? OR r.vehicle LIKE ?)
                ORDER BY r.id DESC""", (q, q)).fetchall())
    return jsonify(data)

@repairs_bp.route("/api/repairs/<int:rid>", methods=["GET"])
@login_required
def get_repair(rid):
    with get_db() as c:
        repair = c.execute("""
            SELECT r.*, COALESCE(cu.name,'—') as customer_name,
                   COALESCE(u.full_name, u.username,'—') as technician
            FROM repairs r
            LEFT JOIN customers cu ON r.customer_id=cu.id
            LEFT JOIN users u      ON r.user_id=u.id
            WHERE r.id=?""", (rid,)).fetchone()
        if not repair:
            return jsonify({"error": "Not found"}), 404
        parts = rows(c.execute("""
            SELECT rp.*, p.name as product_name, p.ref
            FROM repair_parts rp
            JOIN products p ON rp.product_id=p.id
            WHERE rp.repair_id=?""", (rid,)).fetchall())
    return jsonify({"repair": dict(repair), "parts": parts})

@repairs_bp.route("/api/repairs", methods=["POST"])
@login_required
def add_repair():
    d          = request.json
    labor      = float(d.get("labor_cost", 0))
    parts_cost = 0.0
    total      = labor
    with get_db() as c:
        c.execute("""INSERT INTO repairs
                     (customer_id,user_id,vehicle,description,status,labor_cost,parts_cost,total,note)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (d.get("customer_id"), session["user_id"],
                   d.get("vehicle",""), d.get("description",""),
                   d.get("status","pending"), labor, parts_cost, total,
                   d.get("note","")))
        rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": rid}), 201

@repairs_bp.route("/api/repairs/<int:rid>", methods=["PUT"])
@login_required
def update_repair(rid):
    d = request.json
    with get_db() as c:
        c.execute("""UPDATE repairs SET
                     customer_id=?, vehicle=?, description=?, status=?,
                     labor_cost=?, note=?, updated_at=datetime('now')
                     WHERE id=?""",
                  (d.get("customer_id"), d.get("vehicle",""),
                   d.get("description",""), d.get("status","pending"),
                   float(d.get("labor_cost",0)), d.get("note",""), rid))
        # Recalculate total
        parts_cost = c.execute(
            "SELECT COALESCE(SUM(qty*unit_price),0) FROM repair_parts WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        total = float(d.get("labor_cost",0)) + parts_cost
        c.execute("UPDATE repairs SET parts_cost=?, total=? WHERE id=?", (parts_cost, total, rid))
    return jsonify({"ok": True})

@repairs_bp.route("/api/repairs/<int:rid>/parts", methods=["POST"])
@login_required
def add_repair_part(rid):
    d = request.json
    product_id = int(d["product_id"])
    qty        = int(d["qty"])
    with get_db() as c:
        product = c.execute("SELECT qty, sell_price FROM products WHERE id=?", (product_id,)).fetchone()
        if not product or product["qty"] < qty:
            return jsonify({"error": "Not enough stock"}), 400
        unit_price = float(d.get("unit_price") or product["sell_price"])
        c.execute("INSERT INTO repair_parts (repair_id,product_id,qty,unit_price) VALUES (?,?,?,?)",
                  (rid, product_id, qty, unit_price))
        c.execute("UPDATE products SET qty = qty - ? WHERE id=?", (qty, product_id))
        # Update repair totals
        parts_cost = c.execute(
            "SELECT COALESCE(SUM(qty*unit_price),0) FROM repair_parts WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        labor = c.execute("SELECT labor_cost FROM repairs WHERE id=?", (rid,)).fetchone()[0]
        c.execute("UPDATE repairs SET parts_cost=?, total=? WHERE id=?",
                  (parts_cost, labor + parts_cost, rid))
    return jsonify({"ok": True}), 201

@repairs_bp.route("/api/repairs/<int:rid>/parts/<int:pid>", methods=["DELETE"])
@login_required
def delete_repair_part(rid, pid):
    with get_db() as c:
        part = c.execute("SELECT * FROM repair_parts WHERE id=? AND repair_id=?", (pid, rid)).fetchone()
        if not part:
            return jsonify({"error": "Not found"}), 404
        # Return stock
        c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (part["qty"], part["product_id"]))
        c.execute("DELETE FROM repair_parts WHERE id=?", (pid,))
        # Update repair totals
        parts_cost = c.execute(
            "SELECT COALESCE(SUM(qty*unit_price),0) FROM repair_parts WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        labor = c.execute("SELECT labor_cost FROM repairs WHERE id=?", (rid,)).fetchone()[0]
        c.execute("UPDATE repairs SET parts_cost=?, total=? WHERE id=?",
                  (parts_cost, labor + parts_cost, rid))
    return jsonify({"ok": True})

@repairs_bp.route("/api/repairs/<int:rid>", methods=["DELETE"])
@login_required
def delete_repair(rid):
    with get_db() as c:
        # Return all parts to stock
        parts = rows(c.execute(
            "SELECT product_id, qty FROM repair_parts WHERE repair_id=?", (rid,)).fetchall())
        for p in parts:
            c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (p["qty"], p["product_id"]))
        c.execute("DELETE FROM repair_parts WHERE repair_id=?", (rid,))
        c.execute("DELETE FROM repairs WHERE id=?", (rid,))
    return jsonify({"ok": True})
