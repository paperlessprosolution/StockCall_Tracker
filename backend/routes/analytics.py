"""
Routes: /api/analytics  /api/prices  /api/alerts  /api/import
"""

# ── analytics.py ──────────────────────────────
from flask import Blueprint, request, jsonify
import os, json, tempfile

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/dashboard", methods=["GET"])
def dashboard():
    from services.analytics import get_dashboard_stats
    return jsonify(get_dashboard_stats())


@analytics_bp.route("/brokers", methods=["GET"])
def broker_analytics():
    from services.analytics import get_broker_analytics
    return jsonify(get_broker_analytics())


@analytics_bp.route("/by-type", methods=["GET"])
def by_type():
    from services.analytics import get_accuracy_by_call_type
    return jsonify(get_accuracy_by_call_type())


@analytics_bp.route("/monthly", methods=["GET"])
def monthly():
    from services.analytics import get_monthly_performance
    return jsonify(get_monthly_performance())


@analytics_bp.route("/rr", methods=["GET"])
def rr_analysis():
    from services.analytics import get_rr_analysis
    return jsonify(get_rr_analysis())


@analytics_bp.route("/top-stocks", methods=["GET"])
def top_stocks():
    from services.analytics import get_top_stocks
    return jsonify(get_top_stocks())


@analytics_bp.route("/rescore-all", methods=["POST"])
def rescore_all():
    from services.analytics import update_all_broker_scores
    update_all_broker_scores()
    return jsonify({"message": "All broker scores updated"})


# ── prices.py ─────────────────────────────────
prices_bp = Blueprint("prices", __name__)


@prices_bp.route("/<symbol>", methods=["GET"])
def get_price(symbol):
    from services.price_fetcher import fetch_price
    exchange = request.args.get("exchange", "NSE")
    data = fetch_price(symbol.upper(), exchange)
    if not data:
        return jsonify({"error": f"Could not fetch price for {symbol}"}), 404
    return jsonify(data)


@prices_bp.route("/bulk", methods=["POST"])
def bulk_prices():
    from services.price_fetcher import fetch_prices_bulk
    body     = request.json or {}
    symbols  = body.get("symbols", [])
    exchange = body.get("exchange", "NSE")
    if not symbols:
        return jsonify({"error": "No symbols provided"}), 400
    return jsonify(fetch_prices_bulk(symbols, exchange))


@prices_bp.route("/history/<symbol>", methods=["GET"])
def price_history(symbol):
    from services.price_fetcher import get_price_history
    exchange = request.args.get("exchange", "NSE")
    days     = int(request.args.get("days", 30))
    return jsonify(get_price_history(symbol.upper(), exchange, days))


@prices_bp.route("/update-statuses", methods=["POST"])
def update_statuses():
    from services.price_fetcher import update_call_statuses
    result = update_call_statuses()
    return jsonify(result)


# ── alerts.py ─────────────────────────────────
alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/", methods=["GET"])
def list_alerts():
    from database import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, sc.stock, sc.broker_name
            FROM alerts a
            JOIN stock_calls sc ON sc.id = a.call_id
            ORDER BY a.triggered ASC, a.created_at DESC
        """).fetchall()
    return jsonify([dict(r) for r in rows])


@alerts_bp.route("/check", methods=["POST"])
def check_alerts():
    from services.price_fetcher import check_alerts
    triggered = check_alerts()
    return jsonify({"triggered": triggered, "count": len(triggered)})


@alerts_bp.route("/<int:alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    from database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    return jsonify({"message": "Alert deleted"})


# ── import_routes.py ──────────────────────────
import_bp = Blueprint("import", __name__)
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "txt", "json", "pdf"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@import_bp.route("/parse-message", methods=["POST"])
def parse_single_message():
    """Quick parse endpoint (no DB write)."""
    from services.parser import MessageParser
    data = request.json or {}
    msg  = data.get("message", "")
    if not msg.strip():
        return jsonify({"error": "Empty message"}), 400
    parsed = MessageParser().parse(msg)
    return jsonify(parsed.to_dict())


@import_bp.route("/whatsapp", methods=["POST"])
def import_whatsapp():
    """Import WhatsApp chat export (.txt)."""
    from services.parser import WhatsAppParser
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    if not _allowed(f.filename):
        return jsonify({"error": "Invalid file type"}), 400

    content = f.read().decode("utf-8", errors="ignore")
    messages = WhatsAppParser().parse_text(content)
    return jsonify({"parsed": messages, "count": len(messages)})


@import_bp.route("/telegram", methods=["POST"])
def import_telegram():
    """Import Telegram JSON export."""
    from services.parser import TelegramParser
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f    = request.files["file"]
    data = json.loads(f.read().decode("utf-8"))
    messages = TelegramParser().parse_data(data)
    return jsonify({"parsed": messages, "count": len(messages)})


@import_bp.route("/csv", methods=["POST"])
def import_csv():
    """Import stock calls from CSV file."""
    from services.parser import SpreadsheetParser
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        f.save(tmp.name)
        records = SpreadsheetParser().parse_csv(tmp.name)
    os.unlink(tmp.name)
    return jsonify({"records": records, "count": len(records)})


@import_bp.route("/excel", methods=["POST"])
def import_excel():
    """Import stock calls from Excel file."""
    from services.parser import SpreadsheetParser
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f    = request.files["file"]
    ext  = f.filename.rsplit(".", 1)[1].lower()
    suffix = "." + ext

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        records = SpreadsheetParser().parse_excel(tmp.name)
    os.unlink(tmp.name)
    return jsonify({"records": records, "count": len(records)})


@import_bp.route("/pdf", methods=["POST"])
def import_pdf():
    """Extract stock calls from PDF research reports."""
    from services.parser import PDFParser
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        f.save(tmp.name)
        try:
            records = PDFParser().parse_file(tmp.name)
        except ImportError as e:
            return jsonify({"error": str(e)}), 500
    os.unlink(tmp.name)
    return jsonify({"records": records, "count": len(records)})


@import_bp.route("/bulk-save", methods=["POST"])
def bulk_save():
    """Save multiple parsed calls to the database."""
    from database import get_db
    data    = request.json or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    saved = 0
    errors = []
    with get_db() as conn:
        for i, rec in enumerate(records):
            try:
                parsed = rec.get("parsed", rec)
                if not parsed.get("stock"):
                    continue
                broker_name = rec.get("broker_hint") or rec.get("sender") or ""
                conn.execute("""
                    INSERT INTO stock_calls (
                        broker_name, call_date, call_time,
                        stock, action, cmp, entry_price,
                        target1, target2, stoploss,
                        duration, call_type, original_msg, parsed_data
                    ) VALUES (
                        :broker_name, :call_date, :call_time,
                        :stock, :action, :cmp, :entry_price,
                        :target1, :target2, :stoploss,
                        :duration, :call_type, :original_msg, :parsed_data
                    )
                """, {
                    "broker_name":  broker_name,
                    "call_date":    rec.get("date", ""),
                    "call_time":    rec.get("time", ""),
                    "stock":        parsed.get("stock", "").upper(),
                    "action":       parsed.get("action", "BUY"),
                    "cmp":          parsed.get("cmp"),
                    "entry_price":  parsed.get("entry_price"),
                    "target1":      parsed.get("target1"),
                    "target2":      parsed.get("target2"),
                    "stoploss":     parsed.get("stoploss"),
                    "duration":     parsed.get("duration", ""),
                    "call_type":    parsed.get("call_type", "Swing"),
                    "original_msg": rec.get("message", ""),
                    "parsed_data":  json.dumps(parsed),
                })
                saved += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        # Log import
        conn.execute("""
            INSERT INTO import_log (source_type, total_rows, imported_rows, failed_rows, errors)
            VALUES (?, ?, ?, ?, ?)
        """, ("bulk", len(records), saved, len(errors), json.dumps(errors)))

    return jsonify({"saved": saved, "errors": errors})
