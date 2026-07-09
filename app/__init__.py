"""
app/__init__.py  —  Application factory
"""

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
import os

db = SQLAlchemy()
migrate = Migrate()
scheduler = BackgroundScheduler()


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # ── Config ──────────────────────────────────────────────────────────────
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-change-in-prod"),
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(base_dir, 'data', 'stockcall.db')}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(base_dir, "uploads"),
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,   # 32 MB upload limit
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        PRICE_REFRESH_MINUTES=int(os.getenv("PRICE_REFRESH_MINUTES", "15")),
        YFINANCE_TIMEOUT=int(os.getenv("YFINANCE_TIMEOUT", "10")),
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(base_dir, "data"), exist_ok=True)

    # ── Extensions ──────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=app.config["CORS_ORIGINS"])

    # ── Blueprints ──────────────────────────────────────────────────────────
    from .routes.brokers import brokers_bp
    from .routes.calls import calls_bp
    from .routes.prices import prices_bp
    from .routes.analytics import analytics_bp
    from .routes.imports import imports_bp
    from .routes.parser import parser_bp

    app.register_blueprint(brokers_bp,   url_prefix="/api/brokers")
    app.register_blueprint(calls_bp,     url_prefix="/api/calls")
    app.register_blueprint(prices_bp,    url_prefix="/api/prices")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(imports_bp,   url_prefix="/api/import")
    app.register_blueprint(parser_bp,    url_prefix="/api/parser")

    # ── DB init + seed ───────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_if_empty()

    # ── Background price refresh ─────────────────────────────────────────────
    if not scheduler.running:
        from .utils.price_engine import refresh_pending_call_prices
        scheduler.add_job(
            func=lambda: _price_job(app),
            trigger="interval",
            minutes=app.config["PRICE_REFRESH_MINUTES"],
            id="price_refresh",
            replace_existing=True,
        )
        scheduler.start()

    return app


def _price_job(app):
    with app.app_context():
        from .utils.price_engine import refresh_pending_call_prices
        refresh_pending_call_prices()


def _seed_if_empty():
    from .models import Broker, StockCall
    if Broker.query.count() == 0:
        from .utils.seed import seed_data
        seed_data()
