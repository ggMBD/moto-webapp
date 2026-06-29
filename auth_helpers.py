"""
auth_helpers.py — Shared decorators for login & permission protection
"""
import json
from functools import wraps
from flask import session, jsonify, redirect, url_for, request

# Default permissions for staff
DEFAULT_PERMISSIONS = {
    "dashboard": True,
    "inventory": True,
    "sales": True,
    "repairs": True,
    "purchases": True,
    "customers": True,
    "bikes": True,
    "suppliers": True,
    "reports": False,
    "users": False,
}

def get_user_permissions():
    if session.get("role") == "admin":
        return {k: True for k in DEFAULT_PERMISSIONS}
    try:
        return json.loads(session.get("permissions") or "{}")
    except Exception:
        return DEFAULT_PERMISSIONS.copy()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("auth.login_page"))
        if not session.get("is_active", True):
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"error": "Account disabled"}), 403
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

def perm_required(perm):
    """Decorator: requires a specific permission or admin role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("role") == "admin":
                return f(*args, **kwargs)
            perms = get_user_permissions()
            if not perms.get(perm, False):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Permission denied"}), 403
                return redirect(url_for("dashboard.page"))
            return f(*args, **kwargs)
        return decorated
    return decorator
