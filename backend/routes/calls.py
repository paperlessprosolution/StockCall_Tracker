"""
Routes: /api/calls
CRUD for stock recommendations
"""

from flask import Blueprint, request, jsonify
from database import get_db
from services.analytics import compute_broker_score
import json

calls_bp = Blueprint("calls", __name__)


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    # Parse parsed_data JSON
    if d.get("parsed_data"):
        try:
            d["parsed_data"] = json.loads(d["parsed_data"])
        except Exception:
            pass
    return d


@calls_bp.route("/", methods=["GET"])
def list_calls():
    """List all calls with optional filters."""
    broker    = request.args.get("broker")
    call_type = request.args.get("call_type")
    status    = request.args.get("status")
    stock     = request.args.get("stock")
    action    = request.args.get("action")
    start     = request.args.get("start_date")
    end       = request.args.get("end_date")
    limit     = int(request.args.get("limit", 200))
    offset    = int(request.args.get("offset", 0))

    query  = """
        SELECT sc.*,
               co.exit_price, co.exit_date, co.pnl_pct, co.pnl_abs,
               b.reliability AS broker_score
        FROM stock_calls sc
        LEFT JOIN call_outcomes co ON co.call_id = sc.id
        LEFT JOIN brokers b ON b.id = sc.broker_id
        WHERE 1=1
    """
    params = []

    if broker:    query += " AND sc.broker_name LIKE ?";  params.append(f"%{broker}%")
    if call_type: query += " AND sc.call_type = ?";       params.append(call_type)
    if status:    query += " AND sc.status = ?";          params.append(status)
    if stock:     query += " AND sc.stock LIKE ?";        params.append(f"%{stock.upper()}%")
    if action:    query += " AND sc.action = ?";          params.append(action)
    if start:     query += " AND sc.call_date >= ?";      params.append(start)
    if end:       query += " AND sc.call_date <= ?";      params.append(end)

    query += " ORDER BY sc.call_date DESC, sc.call_time DESC"
    query += f" LIMIT {limit} OFFSET {offset}"

    with get_db() as conn:
        rows  = conn.execute(query, params).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM stock_calls WHERE 1=1", []
        ).fetchone()[0]

    return jsonify({
        "calls":  [_row_to_dict(r) for r in rows],
        "total":  total,
        "limit":  limit,
        "offset": offset,
    })


@calls_bp.route("/<int:call_id>", methods=["GET"])
def get_call(call_id):
    with get_db() as conn:
        row = conn.execute("""
            SELECT sc.*, co.exit_price, co.exit_date, co.pnl_pct
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            WHERE sc.id = ?
        """, (call_id,)).fetchone()
    if not row:
        return jsonify({"error": "Call not found"}), 404
    return jsonify(_row_to_dict(row))


@calls_bp.route("/", methods=["POST"])
def create_call():
    data = request.json or {}
    required = ["stock", "call_date"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Missing required field: {f}"}), 400

    # Resolve broker_id
    broker_id = data.get("broker_id")
    broker_name = data.get("broker_name", "")
    if broker_name and not broker_id:
        with get_db() as conn:
            b = conn.execute(
                "SELECT id FROM brokers WHERE name = ?", (broker_name,)
            ).fetchone()
            if b:
                broker_id = b["id"]

    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO stock_calls (
                broker_id, broker_name, call_date, call_time,
                stock, exchange, action, cmp, entry_price,
                target1, target2, target3,
                stoploss, support, resistance,
                duration, call_type, status,
                original_msg, parsed_data, notes, confidence
            ) VALUES (
                :broker_id, :broker_name, :call_date, :call_time,
                :stock, :exchange, :action, :cmp, :entry_price,
                :target1, :target2, :target3,
                :stoploss, :support, :resistance,
                :duration, :call_type, :status,
                :original_msg, :parsed_data, :notes, :confidence
            )
        """, {
            "broker_id":   broker_id,
            "broker_name": broker_name,
            "call_date":   data.get("call_date"),
            "call_time":   data.get("call_time", ""),
            "stock":       data.get("stock", "").upper(),
            "exchange":    data.get("exchange", "NSE"),
            "action":      data.get("action", "BUY"),
            "cmp":         data.get("cmp"),
            "entry_price": data.get("entry_price"),
            "target1":     data.get("target1"),
            "target2":     data.get("target2"),
            "target3":     data.get("target3"),
            "stoploss":    data.get("stoploss"),
            "support":     data.get("support"),
            "resistance":  data.get("resistance"),
            "duration":    data.get("duration", ""),
            "call_type":   data.get("call_type", "Swing"),
            "status":      data.get("status", "Pending"),
            "original_msg":data.get("original_msg", ""),
            "parsed_data": json.dumps(data.get("parsed_data", {})),
            "notes":       data.get("notes", ""),
            "confidence":  data.get("confidence", "Medium"),
        })
        new_id = cur.lastrowid

        # Auto-create alerts
        if data.get("target1") and data.get("stock"):
            _create_alert(conn, new_id, data["stock"],
                          "TARGET", data["target1"],
                          "ABOVE" if data.get("action","BUY") == "BUY" else "BELOW")
        if data.get("stoploss") and data.get("stock"):
            _create_alert(conn, new_id, data["stock"],
                          "SL", data["stoploss"],
                          "BELOW" if data.get("action","BUY") == "BUY" else "ABOVE")

    return jsonify({"id": new_id, "message": "Call created"}), 201


@calls_bp.route("/<int:call_id>", methods=["PUT"])
def update_call(call_id):
    data = request.json or {}
    allowed = [
        "status", "notes", "call_type", "entry_price",
        "target1", "target2", "stoploss", "cmp", "confidence"
    ]

    set_clauses = []
    params = []
    for field in allowed:
        if field in data:
            set_clauses.append(f"{field} = ?")
            params.append(data[field])

    if not set_clauses:
        return jsonify({"error": "Nothing to update"}), 400

    set_clauses.append("updated_at = datetime('now')")
    params.append(call_id)

    with get_db() as conn:
        conn.execute(
            f"UPDATE stock_calls SET {', '.join(set_clauses)} WHERE id = ?",
            params
        )

        # If status changed to Target Hit / SL Hit, record outcome
        if data.get("status") in ("Target Hit", "SL Hit", "Partial Hit"):
            call = conn.execute(
                "SELECT entry_price, target1, stoploss, action FROM stock_calls WHERE id = ?",
                (call_id,)
            ).fetchone()
            if call:
                entry  = call["entry_price"]
                exit_p = call["target1"] if data["status"] in ("Target Hit","Partial Hit") else call["stoploss"]
                if entry and exit_p:
                    pnl = (exit_p - entry) / entry * 100
                    if call["action"] == "SELL":
                        pnl = -pnl
                    conn.execute("""
                        INSERT OR REPLACE INTO call_outcomes
                            (call_id, exit_price, exit_date, pnl_pct)
                        VALUES (?, ?, date('now'), ?)
                    """, (call_id, exit_p, round(pnl, 2)))

        broker_row = conn.execute(
            "SELECT broker_id FROM stock_calls WHERE id = ?",
            (call_id,)
        ).fetchone()
        if broker_row and broker_row["broker_id"]:
            broker_id = broker_row["broker_id"]
            score = compute_broker_score(broker_id)
            conn.execute(
                "UPDATE brokers SET reliability = ?, updated_at = datetime('now') WHERE id = ?",
                (score, broker_id)
            )

    return jsonify({"message": "Updated"})


@calls_bp.route("/<int:call_id>", methods=["DELETE"])
def delete_call(call_id):
    with get_db() as conn:
        conn.execute("DELETE FROM stock_calls WHERE id = ?", (call_id,))
    return jsonify({"message": "Deleted"})


@calls_bp.route("/parse", methods=["POST"])
def parse_message():
    """Parse a raw broker message and return structured data."""
    from services.parser import MessageParser
    data = request.json or {}
    msg  = data.get("message", "")
    if not msg:
        return jsonify({"error": "No message provided"}), 400
    parser = MessageParser()
    parsed = parser.parse(msg)
    return jsonify(parsed.to_dict())


def _create_alert(conn, call_id, stock, alert_type, price, direction):
    conn.execute("""
        INSERT INTO alerts (call_id, stock, alert_type, trigger_price, direction)
        VALUES (?, ?, ?, ?, ?)
    """, (call_id, stock, alert_type, price, direction))
