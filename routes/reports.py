from flask import Blueprint, render_template, request, jsonify
from db import get_db, rows
from auth_helpers import login_required
from datetime import date

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/reports")
@login_required
def page():
    return render_template("reports.html")

@reports_bp.route("/api/reports")
@login_required
def get_reports():
    from_date = request.args.get("from_date") or ""
    to_date   = request.args.get("to_date") or date.today().isoformat()

    sales_where   = ""
    repairs_where = ""
    params_sales  = ()
    params_rep    = ()
    if from_date:
        sales_where   = " WHERE DATE(s.created_at) BETWEEN ? AND ?"
        repairs_where = " WHERE DATE(r.created_at) BETWEEN ? AND ?"
        params_sales  = (from_date, to_date)
        params_rep    = (from_date, to_date)

    with get_db() as c:
        total_sales   = c.execute(f"SELECT COUNT(*) FROM sales s{sales_where}", params_sales).fetchone()[0]
        total_revenue = c.execute(f"SELECT COALESCE(SUM(s.total),0) FROM sales s{sales_where}", params_sales).fetchone()[0]

        if from_date:
            profit_row = c.execute("""
                SELECT COALESCE(SUM((si.unit_price - p.buy_price) * si.qty), 0)
                FROM sale_items si
                JOIN sales s    ON si.sale_id = s.id
                JOIN products p ON si.product_id = p.id
                WHERE DATE(s.created_at) BETWEEN ? AND ?
            """, (from_date, to_date)).fetchone()
        else:
            profit_row = c.execute("""
                SELECT COALESCE(SUM((si.unit_price - p.buy_price) * si.qty), 0)
                FROM sale_items si JOIN products p ON si.product_id = p.id
            """).fetchone()
        gross_profit = profit_row[0]

        total_repairs   = c.execute(f"SELECT COUNT(*) FROM repairs r{repairs_where}", params_rep).fetchone()[0]
        rdone_where     = (repairs_where + " AND r.status='done'") if repairs_where else " WHERE r.status='done'"
        repairs_revenue = c.execute(f"SELECT COALESCE(SUM(r.total),0) FROM repairs r{rdone_where}", params_rep).fetchone()[0]

        total_stock_value = c.execute("SELECT COALESCE(SUM(qty*buy_price),0) FROM products").fetchone()[0]
        low_stock_count   = c.execute("SELECT COUNT(*) FROM products WHERE qty <= min_stock").fetchone()[0]

        monthly_sales = rows(c.execute("""
            SELECT strftime('%Y-%m', created_at) as month,
                   COUNT(*) as count, COALESCE(SUM(total),0) as revenue
            FROM sales GROUP BY month ORDER BY month DESC LIMIT 12
        """).fetchall())

        monthly_repairs = rows(c.execute("""
            SELECT strftime('%Y-%m', created_at) as month,
                   COUNT(*) as count, COALESCE(SUM(total),0) as revenue
            FROM repairs WHERE status='done' GROUP BY month ORDER BY month DESC LIMIT 12
        """).fetchall())

        top_products = rows(c.execute("""
            SELECT p.name, p.ref, SUM(si.qty) as total_sold,
                   SUM(si.qty * si.unit_price) as revenue
            FROM sale_items si JOIN products p ON si.product_id=p.id
            GROUP BY p.id ORDER BY total_sold DESC LIMIT 10
        """).fetchall())

        top_customers = rows(c.execute("""
            SELECT cu.name, cu.phone, COUNT(s.id) as total_orders,
                   COALESCE(SUM(s.total),0) as total_spent
            FROM sales s JOIN customers cu ON s.customer_id=cu.id
            GROUP BY cu.id ORDER BY total_spent DESC LIMIT 10
        """).fetchall())

        return jsonify({
            "total_sales": total_sales, "total_revenue": round(total_revenue, 2),
            "gross_profit": round(gross_profit, 2),
            "total_repairs": total_repairs, "repairs_revenue": round(repairs_revenue, 2),
            "total_stock_value": round(total_stock_value, 2), "low_stock_count": low_stock_count,
            "monthly_sales": monthly_sales, "monthly_repairs": monthly_repairs,
            "top_products": top_products, "top_customers": top_customers,
        })
