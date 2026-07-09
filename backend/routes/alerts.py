"""alerts route — /api/alerts"""
from flask import Blueprint, jsonify
alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/")
def list_alerts():
    from database import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, sc.broker_name FROM alerts a
            JOIN stock_calls sc ON sc.id=a.call_id
            ORDER BY a.triggered ASC, a.created_at DESC
        """).fetchall()
    return jsonify([dict(r) for r in rows])

@alerts_bp.route("/check", methods=["POST"])
def check():
    from services.price_fetcher import check_alerts
    triggered = check_alerts()
    return jsonify({"triggered": triggered, "count": len(triggered)})

@alerts_bp.route("/<int:alert_id>", methods=["DELETE"])
def delete(alert_id):
    from database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
    return jsonify({"message":"deleted"})
