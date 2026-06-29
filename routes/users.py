import sqlite3, json
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash
from db import get_db, rows
from auth_helpers import login_required, admin_required, DEFAULT_PERMISSIONS

users_bp = Blueprint("users", __name__)

@users_bp.route("/users")
@login_required
@admin_required
def page():
    return render_template("users.html")

@users_bp.route("/api/users", methods=["GET"])
@login_required
@admin_required
def get_users():
    with get_db() as c:
        return jsonify(rows(c.execute(
            "SELECT id,username,full_name,role,is_active,permissions,created_at FROM users ORDER BY id").fetchall()))

@users_bp.route("/api/users", methods=["POST"])
@login_required
@admin_required
def add_user():
    d = request.json
    if not d.get("username") or not d.get("password"):
        return jsonify({"error": "Username and password required"}), 400
    perms = json.dumps(d.get("permissions", DEFAULT_PERMISSIONS))
    with get_db() as c:
        try:
            c.execute("INSERT INTO users (username,password,full_name,role,is_active,permissions) VALUES (?,?,?,?,?,?)",
                      (d["username"].strip(), generate_password_hash(d["password"]),
                       d.get("full_name",""), d.get("role","staff"),
                       1 if d.get("is_active", True) else 0, perms))
            uid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 409
    return jsonify({"id": uid}), 201

@users_bp.route("/api/users/<int:uid>", methods=["PUT"])
@login_required
@admin_required
def update_user(uid):
    d = request.json
    perms = json.dumps(d.get("permissions", DEFAULT_PERMISSIONS))
    is_active = 1 if d.get("is_active", True) else 0
    with get_db() as c:
        if d.get("password"):
            c.execute("UPDATE users SET full_name=?,role=?,is_active=?,permissions=?,password=? WHERE id=?",
                      (d.get("full_name",""), d.get("role","staff"), is_active, perms,
                       generate_password_hash(d["password"]), uid))
        else:
            c.execute("UPDATE users SET full_name=?,role=?,is_active=?,permissions=? WHERE id=?",
                      (d.get("full_name",""), d.get("role","staff"), is_active, perms, uid))
    return jsonify({"ok": True})

@users_bp.route("/api/users/<int:uid>/permissions", methods=["PUT"])
@login_required
@admin_required
def update_permissions(uid):
    """Quick update just permissions + active status (used by toggle switches)."""
    d = request.json
    with get_db() as c:
        if "permissions" in d:
            c.execute("UPDATE users SET permissions=? WHERE id=?", (json.dumps(d["permissions"]), uid))
        if "is_active" in d:
            c.execute("UPDATE users SET is_active=? WHERE id=?", (1 if d["is_active"] else 0, uid))
    return jsonify({"ok": True})

@users_bp.route("/api/users/<int:uid>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(uid):
    if uid == session.get("user_id"):
        return jsonify({"error": "Cannot delete your own account"}), 400
    with get_db() as c:
        c.execute("UPDATE sales     SET user_id=NULL WHERE user_id=?", (uid,))
        c.execute("UPDATE purchases SET user_id=NULL WHERE user_id=?", (uid,))
        c.execute("UPDATE repairs   SET user_id=NULL WHERE user_id=?", (uid,))
        c.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({"ok": True})
