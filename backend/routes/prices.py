"""prices route — /api/prices"""
from flask import Blueprint, request, jsonify
prices_bp = Blueprint("prices", __name__)

@prices_bp.route("/<symbol>")
def get_price(symbol):
    from services.price_fetcher import fetch_price
    exchange = request.args.get("exchange","NSE")
    data = fetch_price(symbol.upper(), exchange)
    if not data: return jsonify({"error":f"No price for {symbol}"}),404
    return jsonify(data)

@prices_bp.route("/bulk", methods=["POST"])
def bulk():
    from services.price_fetcher import fetch_prices_bulk
    body = request.json or {}
    return jsonify(fetch_prices_bulk(body.get("symbols",[]), body.get("exchange","NSE")))

@prices_bp.route("/history/<symbol>")
def history(symbol):
    from services.price_fetcher import get_price_history
    return jsonify(get_price_history(symbol.upper(),
        request.args.get("exchange","NSE"), int(request.args.get("days",30))))

@prices_bp.route("/update-statuses", methods=["POST"])
def update():
    from services.price_fetcher import update_call_statuses
    return jsonify(update_call_statuses())
