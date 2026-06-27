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
        low_stock_list  = rows(c.execute("SELECT ref,name,qty,min_stock FROM products WHERE qty <= min_stock ORDER BY qty").fetchall())
        pending_repairs = c.execute("SELECT COUNT(*) FROM repairs WHERE status IN ('pending','waiting_parts')").fetchone()[0]

        return jsonify({
            "products":         c.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "customers":        c.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "suppliers":        c.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0],
            "bikes":            c.execute("SELECT COUNT(*) FROM bikes").fetchone()[0],
            "sales_today":      c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE created_at LIKE ?", (f"{today}%",)).fetchone()[0],
            "repairs_open":     c.execute("SELECT COUNT(*) FROM repairs WHERE status != 'done'").fetchone()[0],
            "low_stock_count":  len(low_stock_list),
            "pending_invoices": pending_repairs,
            "low_stock":        low_stock_list,
            "recent_sales": rows(c.execute("""
                SELECT s.id, COALESCE(cu.name,'Walk-in') as customer,
                       s.total, s.created_at,
                       COALESCE(u.full_name, u.username,'—') as seller
                FROM sales s
                LEFT JOIN customers cu ON s.customer_id=cu.id
                LEFT JOIN users u      ON s.user_id=u.id
                ORDER BY s.id DESC LIMIT 5""").fetchall()),
            "recent_repairs": rows(c.execute("""
                SELECT r.id, COALESCE(cu.name,'—') as customer,
                       COALESCE(b.brand || ' ' || COALESCE(b.model,''), r.vehicle, '—') as vehicle,
                       r.status, r.total, r.created_at
                FROM repairs r
                LEFT JOIN customers cu ON r.customer_id=cu.id
                LEFT JOIN bikes b      ON r.bike_id=b.id
                ORDER BY r.id DESC LIMIT 5""").fetchall()),
        })
