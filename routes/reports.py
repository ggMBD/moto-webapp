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

    # Build a reusable date filter for queries against `sales` and `repairs`
    # (both have created_at). If no from_date given, no date filter is applied
    # (keeps full all-time view as the default, like before).
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

        # Profit = revenue from sale_items at sell_price minus cost at buy_price,
        # restricted to sales within the date range (if any).
        if from_date:
            profit_row = c.execute(f"""
                SELECT COALESCE(SUM((si.unit_price - p.buy_price) * si.qty), 0)
                FROM sale_items si
                JOIN sales s    ON si.sale_id = s.id
                JOIN products p ON si.product_id = p.id
                WHERE DATE(s.created_at) BETWEEN ? AND ?
            """, (from_date, to_date)).fetchone()
        else:
            profit_row = c.execute("""
                SELECT COALESCE(SUM((si.unit_price - p.buy_price) * si.qty), 0)
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
            """).fetchone()
        gross_profit = profit_row[0]

        total_repairs    = c.execute(f"SELECT COUNT(*) FROM repairs r{repairs_where}", params_rep).fetchone()[0]
        repairs_done_where = (repairs_where + " AND r.status='done'") if repairs_where else " WHERE r.status='done'"
        repairs_revenue  = c.execute(f"SELECT COALESCE(SUM(r.total),0) FROM repairs r{repairs_done_where}", params_rep).fetchone()[0]

        # These are point-in-time snapshots, not date-ranged (current stock state)
        total_stock_value = c.execute("SELECT COALESCE(SUM(qty*buy_price),0) FROM products").fetchone()[0]
        low_stock_count   = c.execute("SELECT COUNT(*) FROM products WHERE qty <= min_stock").fetchone()[0]

        top_products = rows(c.execute(f"""
            SELECT p.name, SUM(si.qty) as total_sold, SUM(si.qty*si.unit_price) as revenue
            FROM sale_items si
            JOIN products p ON si.product_id=p.id
            JOIN sales s    ON si.sale_id=s.id
            {sales_where}
            GROUP BY p.id ORDER BY total_sold DESC LIMIT 10
        """, params_sales).fetchall())

        sales_by_customer = rows(c.execute(f"""
            SELECT COALESCE(cu.name,'Walk-in') as customer,
                   COUNT(s.id) as nb_sales, SUM(s.total) as total_spent
            FROM sales s LEFT JOIN customers cu ON s.customer_id=cu.id
            {sales_where}
            GROUP BY s.customer_id ORDER BY total_spent DESC LIMIT 10
        """, params_sales).fetchall())

        stock_value = rows(c.execute("""
            SELECT ref, name, qty, qty*buy_price as stock_value
            FROM products ORDER BY stock_value DESC LIMIT 20
        """).fetchall())

        # Daily revenue series for the chart — within range if given,
        # otherwise last 30 days by default so the chart isn't overwhelming.
        if from_date:
            daily_sales = rows(c.execute(f"""
                SELECT DATE(s.created_at) as day, COUNT(*) as nb, SUM(s.total) as revenue
                FROM sales s
                {sales_where}
                GROUP BY day ORDER BY day ASC
            """, params_sales).fetchall())
        else:
            daily_sales = rows(c.execute("""
                SELECT DATE(s.created_at) as day, COUNT(*) as nb, SUM(s.total) as revenue
                FROM sales s
                WHERE DATE(s.created_at) >= DATE('now', '-30 days')
                GROUP BY day ORDER BY day ASC
            """).fetchall())

        monthly_sales = rows(c.execute(f"""
            SELECT strftime('%Y-%m', s.created_at) as month,
                   COUNT(*) as nb, SUM(s.total) as revenue
            FROM sales s
            {sales_where}
            GROUP BY month ORDER BY month DESC LIMIT 12
        """, params_sales).fetchall())

        sales_by_user = rows(c.execute(f"""
            SELECT COALESCE(u.full_name, u.username,'Unknown') as seller,
                   COUNT(s.id) as nb_sales, SUM(s.total) as total_revenue
            FROM sales s LEFT JOIN users u ON s.user_id=u.id
            {sales_where}
            GROUP BY s.user_id ORDER BY total_revenue DESC
        """, params_sales).fetchall())

        repairs_by_status = rows(c.execute(f"""
            SELECT r.status, COUNT(*) as nb, SUM(r.total) as revenue
            FROM repairs r
            {repairs_where}
            GROUP BY r.status
        """, params_rep).fetchall())

        # Most active bikes/customers for repairs in range — useful for spotting
        # regulars and high-maintenance vehicles
        top_repair_customers = rows(c.execute(f"""
            SELECT COALESCE(cu.name,'—') as customer, COUNT(r.id) as nb_repairs, SUM(r.total) as total_spent
            FROM repairs r LEFT JOIN customers cu ON r.customer_id=cu.id
            {repairs_where}
            GROUP BY r.customer_id ORDER BY total_spent DESC LIMIT 10
        """, params_rep).fetchall())

        avg_sale = (total_revenue / total_sales) if total_sales else 0

        return jsonify({
            "range": {"from": from_date, "to": to_date},
            "overview": {
                "total_sales":        total_sales,
                "total_revenue":      total_revenue,
                "gross_profit":       gross_profit,
                "avg_sale":           avg_sale,
                "total_stock_value":  total_stock_value,
                "low_stock_count":    low_stock_count,
                "total_repairs":      total_repairs,
                "repairs_revenue":    repairs_revenue,
            },
            "top_products":         top_products,
            "sales_by_customer":    sales_by_customer,
            "stock_value":          stock_value,
            "daily_sales":          daily_sales,
            "monthly_sales":        monthly_sales,
            "sales_by_user":        sales_by_user,
            "repairs_by_status":    repairs_by_status,
            "top_repair_customers": top_repair_customers,
        })
