from flask import Blueprint, render_template, request, jsonify, session, send_file
from db import get_db, rows, next_invoice_number
from auth_helpers import login_required
from datetime import date
from invoice_pdf import build_invoice_pdf
import io

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
        SELECT s.id, s.invoice_number, COALESCE(cu.name,'Walk-in') as customer,
               s.total, s.discount, s.note, s.created_at,
               s.payment_method, s.payment_status, s.amount_paid,
               (s.total - s.amount_paid) as balance_due,
               COALESCE(u.full_name, u.username,'—') as seller
        FROM sales s
        LEFT JOIN customers cu ON s.customer_id=cu.id
        LEFT JOIN users u      ON s.user_id=u.id
    """
    with get_db() as c:
        if from_date:
            data = rows(c.execute(
                base_select + " WHERE DATE(s.created_at) BETWEEN ? AND ? ORDER BY s.id DESC",
                (from_date, to_date)).fetchall())
        else:
            data = rows(c.execute(base_select + " ORDER BY s.id DESC LIMIT 200").fetchall())
    return jsonify(data)

@sales_bp.route("/api/sales/<int:sid>", methods=["GET"])
@login_required
def get_sale(sid):
    with get_db() as c:
        sale = c.execute("""
            SELECT s.*, COALESCE(cu.name,'Walk-in') as customer_name,
                   cu.phone as customer_phone, cu.address as customer_address,
                   COALESCE(u.full_name, u.username,'—') as seller
            FROM sales s
            LEFT JOIN customers cu ON s.customer_id=cu.id
            LEFT JOIN users u      ON s.user_id=u.id
            WHERE s.id=?""", (sid,)).fetchone()
        if not sale:
            return jsonify({"error": "Not found"}), 404
        items = rows(c.execute("""
            SELECT si.*, p.name as product_name, p.ref
            FROM sale_items si JOIN products p ON si.product_id=p.id
            WHERE si.sale_id=?""", (sid,)).fetchall())
    return jsonify({"sale": dict(sale), "items": items})

@sales_bp.route("/api/sales", methods=["POST"])
@login_required
def add_sale():
    d     = request.json
    items = d.get("items", [])
    if not items:
        return jsonify({"error": "No items"}), 400

    discount       = float(d.get("discount", 0))
    subtotal       = sum(float(i["qty"]) * float(i["unit_price"]) for i in items)
    total          = max(subtotal - discount, 0)
    payment_method = d.get("payment_method") or "cash"
    payment_status = d.get("payment_status") or "paid"
    amount_paid    = float(d.get("amount_paid", total if payment_status == "paid" else 0))

    if payment_status == "paid":   amount_paid = total
    elif payment_status == "unpaid": amount_paid = 0

    with get_db() as c:
        for item in items:
            row = c.execute("SELECT qty FROM products WHERE id=?", (item["product_id"],)).fetchone()
            if not row or row["qty"] < item["qty"]:
                return jsonify({"error": f"Not enough stock for product #{item['product_id']}"}), 400

        invoice_number = next_invoice_number(c, "sales", "INV")
        c.execute("""INSERT INTO sales
                     (invoice_number,customer_id,user_id,total,discount,
                      payment_method,payment_status,amount_paid,note)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (invoice_number, d.get("customer_id"), session["user_id"], total, discount,
                   payment_method, payment_status, amount_paid, d.get("note","")))
        sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            c.execute("INSERT INTO sale_items (sale_id,product_id,qty,unit_price) VALUES (?,?,?,?)",
                      (sid, item["product_id"], item["qty"], item["unit_price"]))
            c.execute("UPDATE products SET qty = qty - ? WHERE id=?", (item["qty"], item["product_id"]))
        if d.get("customer_id"):
            c.execute("UPDATE customers SET ts = ts + ? WHERE id=?", (total, d["customer_id"]))

    return jsonify({"id": sid, "invoice_number": invoice_number, "total": total}), 201

@sales_bp.route("/api/sales/<int:sid>/payment", methods=["PUT"])
@login_required
def update_payment(sid):
    d = request.json
    with get_db() as c:
        sale = c.execute("SELECT total FROM sales WHERE id=?", (sid,)).fetchone()
        if not sale:
            return jsonify({"error": "Not found"}), 404
        amount_paid    = float(d.get("amount_paid", 0))
        payment_status = "paid" if amount_paid >= sale["total"] else ("partial" if amount_paid > 0 else "unpaid")
        c.execute("UPDATE sales SET amount_paid=?, payment_status=?, payment_method=? WHERE id=?",
                  (amount_paid, payment_status, d.get("payment_method","cash"), sid))
    return jsonify({"ok": True, "payment_status": payment_status})

@sales_bp.route("/api/sales/<int:sid>/invoice.pdf", methods=["GET"])
@login_required
def sale_invoice_pdf(sid):
    # Accept optional overrides from query params (editable before printing)
    override_note  = request.args.get("note")
    override_disc  = request.args.get("discount")

    with get_db() as c:
        sale = c.execute("""
            SELECT s.*, cu.name as customer_name, cu.phone as customer_phone,
                   cu.address as customer_address,
                   COALESCE(u.full_name, u.username,'—') as seller
            FROM sales s
            LEFT JOIN customers cu ON s.customer_id=cu.id
            LEFT JOIN users u      ON s.user_id=u.id
            WHERE s.id=?""", (sid,)).fetchone()
        if not sale:
            return jsonify({"error": "Not found"}), 404
        items = rows(c.execute("""
            SELECT si.qty, si.unit_price, p.name as product_name
            FROM sale_items si JOIN products p ON si.product_id=p.id
            WHERE si.sale_id=?""", (sid,)).fetchall())

    customer = None
    if sale["customer_name"]:
        customer = {"name": sale["customer_name"], "phone": sale["customer_phone"], "address": sale["customer_address"]}

    note     = override_note if override_note is not None else (sale["note"] or "")
    discount = float(override_disc) if override_disc is not None else sale["discount"]
    subtotal = sum(it["qty"] * it["unit_price"] for it in items)
    total    = max(subtotal - discount, 0)

    line_items = [{"description": it["product_name"], "qty": it["qty"], "unit_price": it["unit_price"]} for it in items]

    pdf_bytes = build_invoice_pdf(
        invoice_number=sale["invoice_number"] or f"INV-{sale['id']:04d}",
        doc_type="Sale Invoice",
        customer=customer,
        line_items=line_items,
        discount=discount,
        total=total,
        amount_paid=sale["amount_paid"],
        payment_status=sale["payment_status"],
        payment_method=sale["payment_method"],
        note=note,
        staff=sale["seller"],
        created_at=(sale["created_at"] or "")[:16],
    )

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{sale['invoice_number'] or sale['id']}.pdf"
    )
