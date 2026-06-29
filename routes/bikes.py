from flask import Blueprint, render_template, request, jsonify
from db import get_db, rows
from auth_helpers import login_required

bikes_bp = Blueprint("bikes", __name__)

@bikes_bp.route("/bikes")
@login_required
def page():
    return render_template("bikes.html")

@bikes_bp.route("/api/bikes", methods=["GET"])
@login_required
def get_bikes():
    q        = f"%{request.args.get('q','')}%"
    owner_id = request.args.get("owner_id")
    with get_db() as c:
        if owner_id:
            data = rows(c.execute("""
                SELECT b.*, cu.name as owner_name, cu.phone as owner_phone
                FROM bikes b JOIN customers cu ON b.owner_id = cu.id
                WHERE b.owner_id = ? ORDER BY b.id DESC""", (owner_id,)).fetchall())
        else:
            data = rows(c.execute("""
                SELECT b.*, cu.name as owner_name, cu.phone as owner_phone
                FROM bikes b JOIN customers cu ON b.owner_id = cu.id
                WHERE b.brand LIKE ? OR b.model LIKE ? OR b.plate LIKE ? OR cu.name LIKE ?
                ORDER BY b.id DESC""", (q,q,q,q)).fetchall())
    return jsonify(data)

@bikes_bp.route("/api/bikes/<int:bid>", methods=["GET"])
@login_required
def get_bike(bid):
    with get_db() as c:
        bike = c.execute("""
            SELECT b.*, cu.name as owner_name, cu.phone as owner_phone
            FROM bikes b JOIN customers cu ON b.owner_id = cu.id
            WHERE b.id=?""", (bid,)).fetchone()
        if not bike:
            return jsonify({"error": "Not found"}), 404
        history = rows(c.execute(
            "SELECT id, description, status, total, created_at FROM repairs WHERE bike_id=? ORDER BY id DESC", (bid,)).fetchall())
    return jsonify({"bike": dict(bike), "repairs": history})

@bikes_bp.route("/api/bikes", methods=["POST"])
@login_required
def add_bike():
    d = request.json
    if not d.get("owner_id") or not d.get("brand"):
        return jsonify({"error": "Owner and Brand are required"}), 400
    with get_db() as c:
        c.execute("""INSERT INTO bikes (owner_id,brand,model,year,plate,vin,color,mileage,note)
                     VALUES (:owner_id,:brand,:model,:year,:plate,:vin,:color,:mileage,:note)""", {
            "owner_id": d["owner_id"], "brand": d.get("brand",""), "model": d.get("model",""),
            "year": d.get("year") or None, "plate": d.get("plate",""), "vin": d.get("vin",""),
            "color": d.get("color",""), "mileage": d.get("mileage") or 0, "note": d.get("note",""),
        })
        bid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"id": bid}), 201

@bikes_bp.route("/api/bikes/<int:bid>", methods=["PUT"])
@login_required
def update_bike(bid):
    d = request.json
    if not d.get("owner_id") or not d.get("brand"):
        return jsonify({"error": "Owner and Brand are required"}), 400
    with get_db() as c:
        c.execute("""UPDATE bikes SET
                     owner_id=:owner_id, brand=:brand, model=:model, year=:year,
                     plate=:plate, vin=:vin, color=:color, mileage=:mileage, note=:note,
                     updated_at=date('now') WHERE id=:id""", {
            "id": bid, "owner_id": d["owner_id"], "brand": d.get("brand",""),
            "model": d.get("model",""), "year": d.get("year") or None,
            "plate": d.get("plate",""), "vin": d.get("vin",""), "color": d.get("color",""),
            "mileage": d.get("mileage") or 0, "note": d.get("note",""),
        })
    return jsonify({"ok": True})

@bikes_bp.route("/api/bikes/<int:bid>", methods=["DELETE"])
@login_required
def delete_bike(bid):
    with get_db() as c:
        c.execute("UPDATE repairs SET bike_id=NULL WHERE bike_id=?", (bid,))
        c.execute("DELETE FROM bikes WHERE id=?", (bid,))
    return jsonify({"ok": True})
