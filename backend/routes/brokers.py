"""
Routes: /api/brokers
CRUD for broker management
"""

from flask import Blueprint, request, jsonify
from database import get_db
from services.analytics import compute_broker_score

brokers_bp = Blueprint("brokers", __name__)


@brokers_bp.route("/", methods=["GET"])
def list_brokers():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT b.*,
                COUNT(sc.id)                                      AS total_calls,
                SUM(sc.status IN ('Target Hit','Partial Hit'))    AS wins,
                SUM(sc.status = 'SL Hit')                        AS sl_hits
            FROM brokers b
            LEFT JOIN stock_calls sc ON sc.broker_id = b.id
            WHERE b.active = 1
            GROUP BY b.id
            ORDER BY b.reliability DESC
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@brokers_bp.route("/", methods=["POST"])
def create_broker():
    data = request.json or {}
    if not data.get("name"):
        return jsonify({"error": "Broker name required"}), 400
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO brokers (name, category, contact, source, reliability, notes)
            VALUES (:name, :category, :contact, :source, :reliability, :notes)
        """, {
            "name":        data["name"],
            "category":    data.get("category", "Unknown"),
            "contact":     data.get("contact", ""),
            "source":      data.get("source", "Manual"),
            "reliability": data.get("reliability", 50),
            "notes":       data.get("notes", ""),
        })
        return jsonify({"id": cur.lastrowid, "message": "Broker created"}), 201


@brokers_bp.route("/<int:broker_id>", methods=["PUT"])
def update_broker(broker_id):
    data = request.json or {}
    allowed = ["name", "category", "contact", "source", "reliability", "notes", "active"]
    sets, params = [], []
    for f in allowed:
        if f in data:
            sets.append(f"{f} = ?")
            params.append(data[f])
    if not sets:
        return jsonify({"error": "Nothing to update"}), 400
    sets.append("updated_at = datetime('now')")
    params.append(broker_id)
    with get_db() as conn:
        conn.execute(f"UPDATE brokers SET {', '.join(sets)} WHERE id = ?", params)
    return jsonify({"message": "Updated"})


@brokers_bp.route("/<int:broker_id>/rescore", methods=["POST"])
def rescore_broker(broker_id):
    score = compute_broker_score(broker_id)
    with get_db() as conn:
        conn.execute(
            "UPDATE brokers SET reliability = ?, updated_at = datetime('now') WHERE id = ?",
            (score, broker_id)
        )
    return jsonify({"broker_id": broker_id, "new_score": score})


@brokers_bp.route("/<int:broker_id>", methods=["DELETE"])
def delete_broker(broker_id):
    with get_db() as conn:
        conn.execute("UPDATE brokers SET active = 0 WHERE id = ?", (broker_id,))
    return jsonify({"message": "Broker deactivated"})
