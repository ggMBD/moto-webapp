"""
Z-MOTO Manager v5.0
Entry point — registers all blueprints
Run: python app.py
"""
from flask import Flask, redirect, url_for
import os
from db import init_db
from routes.auth       import auth_bp
from routes.dashboard  import dashboard_bp
from routes.inventory  import inventory_bp
from routes.sales      import sales_bp
from routes.purchases  import purchases_bp
from routes.repairs    import repairs_bp
from routes.customers  import customers_bp
from routes.bikes      import bikes_bp
from routes.suppliers  import suppliers_bp
from routes.reports    import reports_bp
from routes.users      import users_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "zmoto-secret-change-in-production")

# ── Register blueprints ──────────────────────────────────────
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(purchases_bp)
app.register_blueprint(repairs_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(bikes_bp)
app.register_blueprint(suppliers_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(users_bp)

@app.route("/")
def index():
    return redirect(url_for("dashboard.page"))

@app.errorhandler(404)
def not_found(e):
    return redirect(url_for("dashboard.page"))

if __name__ == "__main__":
    init_db()
    print("\n  🏍  Z-MOTO Manager v4 — http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
