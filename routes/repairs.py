from flask import Blueprint, render_template, request, jsonify, session, send_file
from db import get_db, rows, next_invoice_number
from auth_helpers import login_required
from invoice_pdf import build_invoice_pdf
import io

repairs_bp = Blueprint("repairs", __name__)
STATUSES = ["pending", "in_progress", "waiting_parts", "done", "cancelled"]

@repairs_bp.route("/repairs")
@login_required
def page():
    return render_template("repairs.html")

@repairs_bp.route("/api/repairs", methods=["GET"])
@login_required
def get_repairs():
    status = request.args.get("status","")
    q      = f"%{request.args.get('q','')}%"
    from_date = request.args.get("from_date","")
    to_date   = request.args.get("to_date","")
    with get_db() as c:
        base = """
            SELECT r.*, COALESCE(cu.name,'—') as customer_name,
                   COALESCE(u.full_name, u.username,'—') as technician,
                   b.brand as bike_brand, b.model as bike_model, b.plate as bike_plate
            FROM repairs r
            LEFT JOIN customers cu ON r.customer_id=cu.id
            LEFT JOIN users u      ON r.user_id=u.id
            LEFT JOIN bikes b      ON r.bike_id=b.id
        """
        where_parts = []
        params = []
        if status:
            where_parts.append("r.status=?"); params.append(status)
        if from_date and to_date:
            where_parts.append("DATE(r.created_at) BETWEEN ? AND ?"); params += [from_date, to_date]
        if q != "%%":
            where_parts.append("(cu.name LIKE ? OR r.vehicle LIKE ? OR b.brand LIKE ? OR b.plate LIKE ?)")
            params += [q, q, q, q]
        sql = base + (" WHERE " + " AND ".join(where_parts) if where_parts else "") + " ORDER BY r.id DESC"
        data = rows(c.execute(sql, params).fetchall())
    return jsonify(data)

@repairs_bp.route("/api/repairs/<int:rid>", methods=["GET"])
@login_required
def get_repair(rid):
    with get_db() as c:
        repair = c.execute("""
            SELECT r.*, COALESCE(cu.name,'—') as customer_name,
                   COALESCE(u.full_name, u.username,'—') as technician,
                   b.brand as bike_brand, b.model as bike_model, b.plate as bike_plate
            FROM repairs r
            LEFT JOIN customers cu ON r.customer_id=cu.id
            LEFT JOIN users u      ON r.user_id=u.id
            LEFT JOIN bikes b      ON r.bike_id=b.id
            WHERE r.id=?""", (rid,)).fetchone()
        if not repair:
            return jsonify({"error": "Not found"}), 404
        parts = rows(c.execute("""
            SELECT rp.*, p.name as product_name, p.ref
            FROM repair_parts rp JOIN products p ON rp.product_id=p.id
            WHERE rp.repair_id=?""", (rid,)).fetchall())
        labor = rows(c.execute(
            "SELECT * FROM repair_labor WHERE repair_id=? ORDER BY id", (rid,)).fetchall())
    return jsonify({"repair": dict(repair), "parts": parts, "labor": labor})

@repairs_bp.route("/api/repairs", methods=["POST"])
@login_required
def add_repair():
    d = request.json
    with get_db() as c:
        inv = next_invoice_number(c, "repairs", "REP")
        c.execute("""INSERT INTO repairs
                     (invoice_number,customer_id,bike_id,user_id,vehicle,description,status,labor_cost,parts_cost,discount,total,note,payment_method,payment_status,amount_paid)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (inv, d.get("customer_id"), d.get("bike_id"), session["user_id"],
                   d.get("vehicle",""), d.get("description",""),
                   d.get("status","pending"), 0, 0, 0, 0, d.get("note",""), "cash", "unpaid", 0))
        rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": rid, "invoice_number": inv}), 201

@repairs_bp.route("/api/repairs/<int:rid>", methods=["PUT"])
@login_required
def update_repair(rid):
    d = request.json
    with get_db() as c:
        # Recalculate parts total from DB
        parts_cost = c.execute(
            "SELECT COALESCE(SUM(qty*unit_price),0) FROM repair_parts WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        labor_cost = float(d.get("labor_cost", 0))
        discount   = float(d.get("discount", 0))
        total      = max(labor_cost + parts_cost - discount, 0)

        payment_status = d.get("payment_status","unpaid")
        amount_paid    = float(d.get("amount_paid",0))
        if payment_status == "paid": amount_paid = total
        elif payment_status == "unpaid": amount_paid = 0

        c.execute("""UPDATE repairs SET
                     customer_id=?, bike_id=?, vehicle=?, description=?, status=?,
                     labor_cost=?, parts_cost=?, discount=?, total=?,
                     payment_method=?, payment_status=?, amount_paid=?,
                     note=?, updated_at=datetime('now')
                     WHERE id=?""",
                  (d.get("customer_id"), d.get("bike_id"), d.get("vehicle",""),
                   d.get("description",""), d.get("status","pending"),
                   labor_cost, parts_cost, discount, total,
                   d.get("payment_method","cash"), payment_status, amount_paid,
                   d.get("note",""), rid))
    return jsonify({"ok": True, "total": total})

@repairs_bp.route("/api/repairs/<int:rid>/parts", methods=["POST"])
@login_required
def add_repair_part(rid):
    d          = request.json
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
        parts_cost = c.execute(
            "SELECT COALESCE(SUM(qty*unit_price),0) FROM repair_parts WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        r = c.execute("SELECT labor_cost, discount FROM repairs WHERE id=?", (rid,)).fetchone()
        total = max(r["labor_cost"] + parts_cost - (r["discount"] or 0), 0)
        c.execute("UPDATE repairs SET parts_cost=?, total=? WHERE id=?", (parts_cost, total, rid))
    return jsonify({"ok": True}), 201

@repairs_bp.route("/api/repairs/<int:rid>/parts/<int:pid>", methods=["DELETE"])
@login_required
def delete_repair_part(rid, pid):
    with get_db() as c:
        part = c.execute("SELECT * FROM repair_parts WHERE id=? AND repair_id=?", (pid, rid)).fetchone()
        if not part:
            return jsonify({"error": "Not found"}), 404
        c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (part["qty"], part["product_id"]))
        c.execute("DELETE FROM repair_parts WHERE id=?", (pid,))
        parts_cost = c.execute(
            "SELECT COALESCE(SUM(qty*unit_price),0) FROM repair_parts WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        r = c.execute("SELECT labor_cost, discount FROM repairs WHERE id=?", (rid,)).fetchone()
        total = max(r["labor_cost"] + parts_cost - (r["discount"] or 0), 0)
        c.execute("UPDATE repairs SET parts_cost=?, total=? WHERE id=?", (parts_cost, total, rid))
    return jsonify({"ok": True})

@repairs_bp.route("/api/repairs/<int:rid>/labor", methods=["POST"])
@login_required
def add_labor(rid):
    d = request.json
    with get_db() as c:
        c.execute("INSERT INTO repair_labor (repair_id, description, price) VALUES (?,?,?)",
                  (rid, d["description"], float(d["price"])))
        labor_cost = c.execute(
            "SELECT COALESCE(SUM(price),0) FROM repair_labor WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        r = c.execute("SELECT parts_cost, discount FROM repairs WHERE id=?", (rid,)).fetchone()
        total = max(labor_cost + r["parts_cost"] - (r["discount"] or 0), 0)
        c.execute("UPDATE repairs SET labor_cost=?, total=? WHERE id=?", (labor_cost, total, rid))
    return jsonify({"ok": True}), 201

@repairs_bp.route("/api/repairs/<int:rid>/labor/<int:lid>", methods=["DELETE"])
@login_required
def delete_labor(rid, lid):
    with get_db() as c:
        c.execute("DELETE FROM repair_labor WHERE id=? AND repair_id=?", (lid, rid))
        labor_cost = c.execute(
            "SELECT COALESCE(SUM(price),0) FROM repair_labor WHERE repair_id=?", (rid,)
        ).fetchone()[0]
        r = c.execute("SELECT parts_cost, discount FROM repairs WHERE id=?", (rid,)).fetchone()
        total = max(labor_cost + r["parts_cost"] - (r["discount"] or 0), 0)
        c.execute("UPDATE repairs SET labor_cost=?, total=? WHERE id=?", (labor_cost, total, rid))
    return jsonify({"ok": True})

@repairs_bp.route("/api/repairs/<int:rid>", methods=["DELETE"])
@login_required
def delete_repair(rid):
    with get_db() as c:
        parts = rows(c.execute(
            "SELECT product_id, qty FROM repair_parts WHERE repair_id=?", (rid,)).fetchall())
        for p in parts:
            c.execute("UPDATE products SET qty = qty + ? WHERE id=?", (p["qty"], p["product_id"]))
        c.execute("DELETE FROM repair_parts WHERE repair_id=?", (rid,))
        c.execute("DELETE FROM repair_labor WHERE repair_id=?", (rid,))
        c.execute("DELETE FROM repairs WHERE id=?", (rid,))
    return jsonify({"ok": True})

@repairs_bp.route("/api/repairs/<int:rid>/invoice.pdf", methods=["GET"])
@login_required
def repair_invoice_pdf(rid):
    override_note   = request.args.get("note")
    override_disc   = request.args.get("discount")
    override_labor  = request.args.get("labor_cost")

    with get_db() as c:
        repair = c.execute("""
            SELECT r.*, cu.name as customer_name, cu.phone as customer_phone,
                   cu.address as customer_address,
                   COALESCE(u.full_name, u.username,'—') as technician,
                   b.brand as bike_brand, b.model as bike_model, b.plate as bike_plate
            FROM repairs r
            LEFT JOIN customers cu ON r.customer_id=cu.id
            LEFT JOIN users u      ON r.user_id=u.id
            LEFT JOIN bikes b      ON r.bike_id=b.id
            WHERE r.id=?""", (rid,)).fetchone()
        if not repair:
            return jsonify({"error": "Not found"}), 404
        parts = rows(c.execute("""
            SELECT rp.qty, rp.unit_price, p.name as product_name
            FROM repair_parts rp JOIN products p ON rp.product_id=p.id
            WHERE rp.repair_id=?""", (rid,)).fetchall())
        labor_items = rows(c.execute(
            "SELECT description, price FROM repair_labor WHERE repair_id=? ORDER BY id", (rid,)).fetchall())

    customer = None
    if repair["customer_name"]:
        customer = {"name": repair["customer_name"], "phone": repair["customer_phone"], "address": repair["customer_address"]}

    note      = override_note if override_note is not None else (repair["note"] or "")
    discount  = float(override_disc) if override_disc is not None else (repair["discount"] or 0)
    labor_val = float(override_labor) if override_labor is not None else repair["labor_cost"]

    line_items = [{"description": p["product_name"], "qty": p["qty"], "unit_price": p["unit_price"]} for p in parts]
    for l in labor_items:
        line_items.append({"description": f"[Labor] {l['description']}", "qty": 1, "unit_price": l["price"]})

    subtotal = sum(it["qty"] * it["unit_price"] for it in line_items)
    total    = max(subtotal - discount, 0)

    vehicle_info = []
    bike_str = " ".join(filter(None, [repair["bike_brand"], repair["bike_model"]]))
    if bike_str: vehicle_info.append(("Vehicle", bike_str))
    if repair["bike_plate"]: vehicle_info.append(("Plate", repair["bike_plate"]))

    pdf_bytes = build_invoice_pdf(
        invoice_number=repair["invoice_number"] or f"REP-{repair['id']:04d}",
        doc_type="Repair Invoice",
        customer=customer,
        line_items=line_items,
        discount=discount,
        total=total,
        amount_paid=repair["amount_paid"],
        payment_status=repair["payment_status"],
        payment_method=repair["payment_method"],
        note=note,
        staff=repair["technician"],
        created_at=(repair["created_at"] or "")[:16],
        extra_info=vehicle_info,
    )

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{repair['invoice_number'] or repair['id']}.pdf"
    )
