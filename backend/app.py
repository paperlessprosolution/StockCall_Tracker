"""
StockCall Tracker - Flask Backend
Main application entry point
"""

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import threading
from database import init_db
from routes.calls import calls_bp
from routes.brokers import brokers_bp
from routes.analytics import analytics_bp
from routes.prices import prices_bp
from routes.import_routes import import_bp
from routes.alerts import alerts_bp

socketio = SocketIO()


def _run_status_refresh_loop(app, interval_seconds, stop_event):
    while not stop_event.is_set():
        try:
            with app.app_context():
                result = update_call_statuses()
                print(
                    f"[StatusRefresh] checked={result.get('checked')} "
                    f"target_hit={result.get('target_hit')} sl_hit={result.get('sl_hit')}"
                )
        except Exception as exc:
            print(f"[StatusRefresh] error: {exc}")
        stop_event.wait(interval_seconds)


def _start_status_refresh_scheduler(app):
    if app.config.get("STATUS_REFRESH_ENABLED", True) is False:
        return

    if app.extensions.get("status_refresh_thread") is not None:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    from services.price_fetcher import update_call_statuses

    interval_seconds = int(app.config.get("STATUS_REFRESH_SECONDS", os.environ.get("STATUS_REFRESH_SECONDS", "300")))
    stop_event = threading.Event()

    with app.app_context():
        update_call_statuses()

    thread = threading.Thread(
        target=_run_status_refresh_loop,
        args=(app, interval_seconds, stop_event),
        daemon=True,
        name="status-refresh",
    )
    app.extensions["status_refresh_thread"] = thread
    app.extensions["status_refresh_stop_event"] = stop_event
    thread.start()


def create_app(config=None):
    app = Flask(__name__)

    # Config
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "stockcall-dev-secret-2025")
    app.config["DATABASE"] = os.environ.get("DATABASE_URL", "stockcall.db")
    app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.config["STATUS_REFRESH_ENABLED"] = os.environ.get("STATUS_REFRESH_ENABLED", "true").lower() == "true"
    app.config["STATUS_REFRESH_SECONDS"] = int(os.environ.get("STATUS_REFRESH_SECONDS", "300"))

    # CORS for React frontend
    CORS(app, origins=["http://localhost:3000", "http://localhost:5173"])

    # SocketIO for real-time price alerts
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    # Init database
    with app.app_context():
        init_db()

    # Register blueprints
    app.register_blueprint(calls_bp,     url_prefix="/api/calls")
    app.register_blueprint(brokers_bp,   url_prefix="/api/brokers")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(prices_bp,    url_prefix="/api/prices")
    app.register_blueprint(import_bp,    url_prefix="/api/import")
    app.register_blueprint(alerts_bp,    url_prefix="/api/alerts")

    _start_status_refresh_scheduler(app)

    @app.route("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    return app


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
