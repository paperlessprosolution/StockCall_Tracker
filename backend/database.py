"""
Database initialization and schema for StockCall Tracker
Uses SQLite with full schema for all entities
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = os.environ.get("DATABASE_URL", "stockcall.db")

if os.path.isabs(DEFAULT_DB):
    DB_PATH = DEFAULT_DB
else:
    DB_PATH = str((BASE_DIR / DEFAULT_DB).resolve())


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
    print("[DB] Database initialized")


# ─────────────────────────────────────────────
# Full SQL Schema
# ─────────────────────────────────────────────
SCHEMA_SQL = """

-- ── Brokers ─────────────────────────────────
CREATE TABLE IF NOT EXISTS brokers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    category        TEXT    DEFAULT 'Unknown',
    contact         TEXT,
    source          TEXT    DEFAULT 'Manual',   -- WhatsApp / Telegram / Email / SMS
    reliability     REAL    DEFAULT 50.0,        -- 0-100 computed score
    notes           TEXT,
    active          INTEGER DEFAULT 1,
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- ── Stock Calls ─────────────────────────────
CREATE TABLE IF NOT EXISTS stock_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    broker_id       INTEGER REFERENCES brokers(id) ON DELETE SET NULL,
    broker_name     TEXT,                        -- denormalized for speed
    call_date       TEXT    NOT NULL,
    call_time       TEXT,
    stock           TEXT    NOT NULL,
    exchange        TEXT    DEFAULT 'NSE',
    action          TEXT    DEFAULT 'BUY',       -- BUY / SELL
    cmp             REAL,                        -- current market price at call time
    entry_price     REAL,
    target1         REAL,
    target2         REAL,
    target3         REAL,
    stoploss        REAL,
    support         REAL,
    resistance      REAL,
    duration        TEXT,
    call_type       TEXT    DEFAULT 'Swing',     -- Intraday / Swing / Positional / Long Term
    status          TEXT    DEFAULT 'Pending',   -- Pending / Target Hit / Partial Hit / SL Hit / Expired
    original_msg    TEXT,
    parsed_data     TEXT,                        -- JSON blob of parsed fields
    notes           TEXT,
    confidence      TEXT    DEFAULT 'Medium',    -- High / Medium / Low
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

-- ── Call Outcomes ────────────────────────────
CREATE TABLE IF NOT EXISTS call_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id         INTEGER NOT NULL REFERENCES stock_calls(id) ON DELETE CASCADE,
    exit_price      REAL,
    exit_date       TEXT,
    pnl_pct         REAL,
    pnl_abs         REAL,
    holding_days    INTEGER,
    outcome_notes   TEXT,
    recorded_at     TEXT    DEFAULT (datetime('now'))
);

-- ── Price Cache ──────────────────────────────
CREATE TABLE IF NOT EXISTS price_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT    NOT NULL,
    exchange        TEXT    DEFAULT 'NSE',
    price           REAL,
    open            REAL,
    high            REAL,
    low             REAL,
    volume          INTEGER,
    change_pct      REAL,
    fetched_at      TEXT    DEFAULT (datetime('now')),
    UNIQUE(symbol, exchange)
);

-- ── Alerts ──────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id         INTEGER REFERENCES stock_calls(id) ON DELETE CASCADE,
    stock           TEXT    NOT NULL,
    alert_type      TEXT    NOT NULL,            -- TARGET / SL / PRICE
    trigger_price   REAL    NOT NULL,
    direction       TEXT    DEFAULT 'ABOVE',     -- ABOVE / BELOW
    triggered       INTEGER DEFAULT 0,
    triggered_at    TEXT,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ── Import Log ───────────────────────────────
CREATE TABLE IF NOT EXISTS import_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type     TEXT    NOT NULL,            -- CSV / Excel / WhatsApp / PDF / Telegram
    filename        TEXT,
    total_rows      INTEGER DEFAULT 0,
    imported_rows   INTEGER DEFAULT 0,
    failed_rows     INTEGER DEFAULT 0,
    errors          TEXT,                        -- JSON array of error strings
    imported_at     TEXT    DEFAULT (datetime('now'))
);

-- ── Indexes ──────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_calls_date       ON stock_calls(call_date DESC);
CREATE INDEX IF NOT EXISTS idx_calls_broker     ON stock_calls(broker_id);
CREATE INDEX IF NOT EXISTS idx_calls_stock      ON stock_calls(stock);
CREATE INDEX IF NOT EXISTS idx_calls_status     ON stock_calls(status);
CREATE INDEX IF NOT EXISTS idx_calls_type       ON stock_calls(call_type);
CREATE INDEX IF NOT EXISTS idx_price_symbol     ON price_cache(symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_call      ON alerts(call_id);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(triggered);

-- ── Sample data ──────────────────────────────
INSERT OR IGNORE INTO brokers (name, category, contact, source, reliability)
VALUES
    ('TradeBulls Securities', 'Full Service',   'info@tradebulls.com',      'WhatsApp', 78),
    ('HDFC Securities',       'Bank Broker',    'research@hdfcsec.com',     'Email',    82),
    ('Angel One Signals',     'Discount Broker','signals@angelone.in',      'Telegram', 71),
    ('Zerodha Varsity',       'Discount Broker','varsity@zerodha.com',      'Telegram', 88),
    ('Motilal Oswal',         'Full Service',   'research@motilaloswal.com','WhatsApp', 75);
"""
