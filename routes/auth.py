from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db
from auth_helpers import login_required

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("dashboard.page"))
    return render_template("login.html")

@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    d = request.json or {}
    with get_db() as c:
        user = c.execute("SELECT * FROM users WHERE username=?", (d.get("username","").strip(),)).fetchone()
    if not user or not check_password_hash(user["password"], d.get("password","")):
        return jsonify({"error": "Invalid username or password"}), 401
    session.permanent = True
    session["user_id"]   = user["id"]
    session["username"]  = user["username"]
    session["full_name"] = user["full_name"]
    session["role"]      = user["role"]
    return jsonify({"ok": True, "role": user["role"], "full_name": user["full_name"]})

@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@auth_bp.route("/api/auth/me")
def api_me():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "user_id":   session["user_id"],
        "username":  session["username"],
        "full_name": session["full_name"],
        "role":      session["role"],
    })

@auth_bp.route("/api/auth/password/<int:uid>", methods=["PUT"])
@login_required
def change_password(uid):
    if uid != session["user_id"] and session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    d = request.json or {}
    if not d.get("new_password"):
        return jsonify({"error": "new_password required"}), 400
    with get_db() as c:
        c.execute("UPDATE users SET password=? WHERE id=?",
                  (generate_password_hash(d["new_password"]), uid))
    return jsonify({"ok": True})
