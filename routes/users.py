import sqlite3
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash
from db import get_db, rows
from auth_helpers import login_required, admin_required

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
            "SELECT id,username,full_name,role,created_at FROM users ORDER BY id").fetchall()))

@users_bp.route("/api/users", methods=["POST"])
@login_required
@admin_required
def add_user():
    d = request.json
    if not d.get("username") or not d.get("password"):
        return jsonify({"error": "Username and password required"}), 400
    with get_db() as c:
        try:
            c.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                      (d["username"].strip(), generate_password_hash(d["password"]),
                       d.get("full_name",""), d.get("role","staff")))
            uid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 409
    return jsonify({"id": uid}), 201

@users_bp.route("/api/users/<int:uid>", methods=["PUT"])
@login_required
@admin_required
def update_user(uid):
    d = request.json
    with get_db() as c:
        if d.get("password"):
            c.execute("UPDATE users SET full_name=?,role=?,password=? WHERE id=?",
                      (d.get("full_name",""), d.get("role","staff"),
                       generate_password_hash(d["password"]), uid))
        else:
            c.execute("UPDATE users SET full_name=?,role=? WHERE id=?",
                      (d.get("full_name",""), d.get("role","staff"), uid))
    return jsonify({"ok": True})

@users_bp.route("/api/users/<int:uid>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(uid):
    if uid == session.get("user_id"):
        return jsonify({"error": "Cannot delete your own account"}), 400
    with get_db() as c:
        c.execute("UPDATE sales SET user_id=NULL WHERE user_id=?", (uid,))
        c.execute("UPDATE purchases SET user_id=NULL WHERE user_id=?", (uid,))
        c.execute("UPDATE repairs SET user_id=NULL WHERE user_id=?", (uid,))
        c.execute("DELETE FROM users WHERE id=?", (uid,))
    return jsonify({"ok": True})
