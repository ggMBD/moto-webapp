from flask import Blueprint, render_template, jsonify
from db import get_db, rows
from auth_helpers import login_required

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/reports")
@login_required
def page():
    return render_template("reports.html")

@reports_bp.route("/api/reports")
@login_required
def get_reports():
    with get_db() as c:
        return jsonify({
            "overview": {
                "total_sales":        c.execute("SELECT COUNT(*) FROM sales").fetchone()[0],
                "total_revenue":      c.execute("SELECT COALESCE(SUM(total),0) FROM sales").fetchone()[0],
                "total_stock_value":  c.execute("SELECT COALESCE(SUM(qty*buy_price),0) FROM products").fetchone()[0],
                "low_stock_count":    c.execute("SELECT COUNT(*) FROM products WHERE qty <= min_stock").fetchone()[0],
                "total_repairs":      c.execute("SELECT COUNT(*) FROM repairs").fetchone()[0],
                "repairs_revenue":    c.execute("SELECT COALESCE(SUM(total),0) FROM repairs WHERE status='done'").fetchone()[0],
            },
            "top_products": rows(c.execute("""
                SELECT p.name, SUM(si.qty) as total_sold, SUM(si.qty*si.unit_price) as revenue
                FROM sale_items si JOIN products p ON si.product_id=p.id
                GROUP BY p.id ORDER BY total_sold DESC LIMIT 10""").fetchall()),
            "sales_by_customer": rows(c.execute("""
                SELECT COALESCE(cu.name,'Walk-in') as customer,
                       COUNT(s.id) as nb_sales, SUM(s.total) as total_spent
                FROM sales s LEFT JOIN customers cu ON s.customer_id=cu.id
                GROUP BY s.customer_id ORDER BY total_spent DESC LIMIT 10""").fetchall()),
            "stock_value": rows(c.execute("""
                SELECT ref, name, qty, qty*buy_price as stock_value
                FROM products ORDER BY stock_value DESC LIMIT 20""").fetchall()),
            "monthly_sales": rows(c.execute("""
                SELECT strftime('%Y-%m', created_at) as month,
                       COUNT(*) as nb, SUM(total) as revenue
                FROM sales GROUP BY month ORDER BY month DESC LIMIT 12""").fetchall()),
            "sales_by_user": rows(c.execute("""
                SELECT COALESCE(u.full_name, u.username,'Unknown') as seller,
                       COUNT(s.id) as nb_sales, SUM(s.total) as total_revenue
                FROM sales s LEFT JOIN users u ON s.user_id=u.id
                GROUP BY s.user_id ORDER BY total_revenue DESC""").fetchall()),
            "repairs_by_status": rows(c.execute("""
                SELECT status, COUNT(*) as nb, SUM(total) as revenue
                FROM repairs GROUP BY status""").fetchall()),
        })
