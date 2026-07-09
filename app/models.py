"""
app/models.py  —  Complete database schema
"""

from datetime import datetime
from . import db
import json


class Broker(db.Model):
    __tablename__ = "brokers"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False, unique=True)
    category      = db.Column(db.String(60))          # Full Service / Discount / Bank
    contact       = db.Column(db.String(200))
    source        = db.Column(db.String(60))           # WhatsApp / Telegram / Email / SMS
    reliability_score = db.Column(db.Float, default=70.0)
    is_active     = db.Column(db.Boolean, default=True)
    notes         = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    calls = db.relationship("StockCall", back_populates="broker_rel", lazy="dynamic")

    # ── Computed Stats ───────────────────────────────────────────────────────
    @property
    def total_calls(self):
        return self.calls.count()

    @property
    def wins(self):
        return self.calls.filter_by(status="Target Hit").count()

    @property
    def partial_wins(self):
        return self.calls.filter_by(status="Partial Hit").count()

    @property
    def sl_hits(self):
        return self.calls.filter_by(status="SL Hit").count()

    @property
    def win_rate(self):
        t = self.total_calls
        if t == 0:
            return 0.0
        return round((self.wins + self.partial_wins) / t * 100, 1)

    @property
    def avg_return(self):
        completed = [c.pnl_pct for c in self.calls if c.pnl_pct is not None]
        if not completed:
            return 0.0
        return round(sum(completed) / len(completed), 2)

    def recalculate_score(self):
        """AI-style reliability score: accuracy × 0.5 + risk_reward × 0.3 + consistency × 0.2"""
        if self.total_calls < 3:
            return self.reliability_score

        accuracy = self.win_rate / 100
        rets = [c.pnl_pct for c in self.calls if c.pnl_pct is not None]
        if len(rets) >= 2:
            import statistics
            consistency = max(0, 1 - (statistics.stdev(rets) / (abs(statistics.mean(rets)) + 1)))
        else:
            consistency = 0.5

        rr_list = []
        for c in self.calls:
            if c.entry and c.stoploss and c.target1:
                risk   = abs(c.entry - c.stoploss)
                reward = abs(c.target1 - c.entry)
                if risk > 0:
                    rr_list.append(reward / risk)
        avg_rr = (sum(rr_list) / len(rr_list)) if rr_list else 1.0
        rr_score = min(avg_rr / 3.0, 1.0)

        score = (accuracy * 50) + (rr_score * 30) + (consistency * 20)
        self.reliability_score = round(min(max(score, 0), 100), 1)
        return self.reliability_score

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "contact": self.contact,
            "source": self.source,
            "reliability_score": self.reliability_score,
            "is_active": self.is_active,
            "notes": self.notes,
            "total_calls": self.total_calls,
            "wins": self.wins,
            "partial_wins": self.partial_wins,
            "sl_hits": self.sl_hits,
            "win_rate": self.win_rate,
            "avg_return": self.avg_return,
            "created_at": self.created_at.isoformat(),
        }


class StockCall(db.Model):
    __tablename__ = "stock_calls"

    id              = db.Column(db.Integer, primary_key=True)
    call_date       = db.Column(db.Date,    nullable=False, default=datetime.utcnow)
    call_time       = db.Column(db.String(8))
    broker_id       = db.Column(db.Integer, db.ForeignKey("brokers.id"), nullable=False)
    broker_name     = db.Column(db.String(120))        # denormalized for fast queries
    stock_symbol    = db.Column(db.String(30),  nullable=False)
    stock_name      = db.Column(db.String(120))
    exchange        = db.Column(db.String(10),  default="NSE")
    action          = db.Column(db.String(10),  default="BUY")  # BUY / SELL
    call_type       = db.Column(db.String(20),  default="Swing") # Intraday/Swing/Positional/LT
    cmp             = db.Column(db.Float)
    entry_price     = db.Column(db.Float)
    target1         = db.Column(db.Float)
    target2         = db.Column(db.Float)
    target3         = db.Column(db.Float)
    stoploss        = db.Column(db.Float)
    support         = db.Column(db.Float)
    resistance      = db.Column(db.Float)
    duration        = db.Column(db.String(50))
    original_message= db.Column(db.Text)
    parsed_data     = db.Column(db.Text)              # JSON blob of parser output
    status          = db.Column(db.String(30),  default="Pending")
    # Pending / Target Hit / Partial Hit / SL Hit / Expired
    current_price   = db.Column(db.Float)
    price_updated_at= db.Column(db.DateTime)
    pnl_pct         = db.Column(db.Float)
    closed_at       = db.Column(db.DateTime)
    notes           = db.Column(db.Text)
    source_channel  = db.Column(db.String(30))        # WhatsApp / Telegram / Manual / CSV
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    broker_rel = db.relationship("Broker", back_populates="calls")

    @property
    def targets(self):
        return [t for t in [self.target1, self.target2, self.target3] if t]

    @property
    def risk_reward(self):
        if self.entry_price and self.stoploss and self.target1:
            risk   = abs(self.entry_price - self.stoploss)
            reward = abs(self.target1 - self.entry_price)
            return round(reward / risk, 2) if risk else None
        return None

    @property
    def unrealized_pnl(self):
        if self.current_price and self.entry_price:
            mult = 1 if self.action == "BUY" else -1
            return round((self.current_price - self.entry_price) / self.entry_price * 100 * mult, 2)
        return None

    def auto_update_status(self):
        """Check current price against targets / SL and auto-update status."""
        if not self.current_price or self.status in ("Target Hit", "SL Hit", "Expired"):
            return
        cp = self.current_price
        if self.action == "BUY":
            if self.stoploss and cp <= self.stoploss:
                self.status   = "SL Hit"
                self.pnl_pct  = round((cp - self.entry_price) / self.entry_price * 100, 2)
                self.closed_at= datetime.utcnow()
            elif self.target1 and cp >= self.target1:
                self.status   = "Target Hit"
                self.pnl_pct  = round((cp - self.entry_price) / self.entry_price * 100, 2)
                self.closed_at= datetime.utcnow()
        else:  # SELL
            if self.stoploss and cp >= self.stoploss:
                self.status   = "SL Hit"
                self.pnl_pct  = round((self.entry_price - cp) / self.entry_price * 100, 2)
                self.closed_at= datetime.utcnow()
            elif self.target1 and cp <= self.target1:
                self.status   = "Target Hit"
                self.pnl_pct  = round((self.entry_price - cp) / self.entry_price * 100, 2)
                self.closed_at= datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "call_date": self.call_date.isoformat() if self.call_date else None,
            "call_time": self.call_time,
            "broker_id": self.broker_id,
            "broker_name": self.broker_name,
            "stock_symbol": self.stock_symbol,
            "stock_name": self.stock_name,
            "exchange": self.exchange,
            "action": self.action,
            "call_type": self.call_type,
            "cmp": self.cmp,
            "entry_price": self.entry_price,
            "targets": self.targets,
            "target1": self.target1,
            "target2": self.target2,
            "target3": self.target3,
            "stoploss": self.stoploss,
            "support": self.support,
            "resistance": self.resistance,
            "duration": self.duration,
            "original_message": self.original_message,
            "parsed_data": json.loads(self.parsed_data) if self.parsed_data else None,
            "status": self.status,
            "current_price": self.current_price,
            "price_updated_at": self.price_updated_at.isoformat() if self.price_updated_at else None,
            "pnl_pct": self.pnl_pct,
            "unrealized_pnl": self.unrealized_pnl,
            "risk_reward": self.risk_reward,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "notes": self.notes,
            "source_channel": self.source_channel,
            "created_at": self.created_at.isoformat(),
        }


class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id           = db.Column(db.Integer, primary_key=True)
    symbol       = db.Column(db.String(30), nullable=False, index=True)
    exchange     = db.Column(db.String(10), default="NSE")
    price        = db.Column(db.Float, nullable=False)
    volume       = db.Column(db.BigInteger)
    day_high     = db.Column(db.Float)
    day_low      = db.Column(db.Float)
    prev_close   = db.Column(db.Float)
    change_pct   = db.Column(db.Float)
    fetched_at   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "price": self.price,
            "volume": self.volume,
            "day_high": self.day_high,
            "day_low": self.day_low,
            "prev_close": self.prev_close,
            "change_pct": self.change_pct,
            "fetched_at": self.fetched_at.isoformat(),
        }


class ImportLog(db.Model):
    __tablename__ = "import_logs"

    id           = db.Column(db.Integer, primary_key=True)
    source_type  = db.Column(db.String(30))  # csv / excel / whatsapp / telegram / pdf
    filename     = db.Column(db.String(255))
    total_rows   = db.Column(db.Integer, default=0)
    imported     = db.Column(db.Integer, default=0)
    skipped      = db.Column(db.Integer, default=0)
    errors       = db.Column(db.Text)         # JSON list
    status       = db.Column(db.String(20), default="pending")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type,
            "filename": self.filename,
            "total_rows": self.total_rows,
            "imported": self.imported,
            "skipped": self.skipped,
            "errors": json.loads(self.errors) if self.errors else [],
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
