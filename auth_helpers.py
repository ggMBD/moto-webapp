"""
auth_helpers.py — Shared decorators for login & admin protection
"""
from functools import wraps
from flask import session, jsonify, redirect, url_for, request

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin only"}), 403
            return redirect(url_for("dashboard.page"))
        return f(*args, **kwargs)
    return decorated
