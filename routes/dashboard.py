from flask import Blueprint, render_template, jsonify
from datetime import date
from db import get_db, rows
from auth_helpers import login_required

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@login_required
def page():
    return render_template("dashboard.html")

@dashboard_bp.route("/api/dashboard")
@login_required
def api_dashboard():
    today = date.today().isoformat()
    with get_db() as c:
        low_stock_list = rows(c.execute(
            "SELECT ref,name,qty,min_stock FROM products WHERE qty <= min_stock ORDER BY qty"
        ).fetchall())

        pending_sales_balance = c.execute(
            "SELECT COALESCE(SUM(total - amount_paid),0) FROM sales WHERE payment_status != 'paid'"
        ).fetchone()[0]
        pending_repairs_balance = c.execute(
            "SELECT COALESCE(SUM(total - amount_paid),0) FROM repairs WHERE payment_status != 'paid'"
        ).fetchone()[0]
        pending_count = c.execute(
            "SELECT COUNT(*) FROM sales WHERE payment_status != 'paid'"
        ).fetchone()[0] + c.execute(
            "SELECT COUNT(*) FROM repairs WHERE payment_status != 'paid'"
        ).fetchone()[0]

        return jsonify({
            "products":         c.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "customers":        c.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "suppliers":        c.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
            "bikes":            c.execute("SELECT COUNT(*) FROM bikes").fetchone()[0],
            "sales_today":      c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0],
            "repairs_open":     c.execute("SELECT COUNT(*) FROM repairs WHERE status NOT IN ('done','cancelled')").fetchone()[0],
            "low_stock_count":  len(low_stock_list),
            "pending_invoices": pending_count,
            "pending_balance":  round(pending_sales_balance + pending_repairs_balance, 2),
            "low_stock":        low_stock_list,
            "recent_sales": rows(c.execute("""
                SELECT s.id, s.invoice_number, COALESCE(cu.name,'Walk-in') as customer,
                       s.total, s.created_at, s.payment_status,
                       COALESCE(u.full_name, u.username,'—') as seller
                FROM sales s
                LEFT JOIN customers cu ON s.customer_id=cu.id
                LEFT JOIN users u      ON s.user_id=u.id
                ORDER BY s.id DESC LIMIT 6""").fetchall()),
            "recent_repairs": rows(c.execute("""
                SELECT r.id, r.invoice_number, COALESCE(cu.name,'—') as customer,
                       COALESCE(b.brand || ' ' || COALESCE(b.model,''), r.vehicle, '—') as vehicle,
                       r.status, r.total, r.created_at, r.payment_status
                FROM repairs r
                LEFT JOIN customers cu ON r.customer_id=cu.id
                LEFT JOIN bikes b      ON r.bike_id=b.id
                ORDER BY r.id DESC LIMIT 6""").fetchall()),
        })
