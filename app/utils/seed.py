"""
app/utils/seed.py  —  Initial database seed with sample data
"""

from datetime import date, timedelta
from .. import db
from ..models import Broker, StockCall


BROKERS = [
    {"name": "TradeBulls Securities", "category": "Full Service",   "contact": "info@tradebulls.com",      "source": "WhatsApp", "reliability_score": 78},
    {"name": "HDFC Securities",        "category": "Bank Broker",    "contact": "hdfc@securities.in",       "source": "Email",    "reliability_score": 82},
    {"name": "Angel One Signals",      "category": "Discount Broker","contact": "signals@angelone.in",      "source": "Telegram", "reliability_score": 71},
    {"name": "Zerodha Varsity",        "category": "Discount Broker","contact": "varsity@zerodha.com",      "source": "Telegram", "reliability_score": 88},
    {"name": "Motilal Oswal Research", "category": "Full Service",   "contact": "research@motilaloswal.com","source": "WhatsApp", "reliability_score": 75},
]

CALLS_TEMPLATE = [
    {"stock_symbol": "TATASTEEL",  "action": "BUY",  "call_type": "Swing",    "cmp": 202,   "entry_price": 202,   "target1": 236,   "stoploss": 185,  "duration": "2-3 Days",   "status": "Target Hit",  "pnl_pct": 16.8, "original_message": "TATA STEEL\nCMP 202\nTARGET 236\nSUPPORT 211\nDURATION 2-3 DAYS"},
    {"stock_symbol": "INFY",       "action": "BUY",  "call_type": "Swing",    "cmp": 1780,  "entry_price": 1780,  "target1": 1820,  "stoploss": 1710, "duration": "1 Week",     "status": "Pending",     "pnl_pct": None, "original_message": "ACCUMULATE INFY\nTARGET 1820\nSL 1710\nTIME 1 WEEK"},
    {"stock_symbol": "RELIANCE",   "action": "BUY",  "call_type": "Intraday", "cmp": 1445,  "entry_price": 1450,  "target1": 1510,  "target2": 1540, "stoploss": 1420, "duration": "Intraday",   "status": "Partial Hit", "pnl_pct": 4.1,  "original_message": "BUY RELIANCE ABOVE 1450\nTARGET 1510 / 1540\nSTOPLOSS 1420\nINTRADAY"},
    {"stock_symbol": "HDFCBANK",   "action": "BUY",  "call_type": "Swing",    "cmp": 1625,  "entry_price": 1625,  "target1": 1680,  "stoploss": 1590, "duration": "3-5 Days",   "status": "Target Hit",  "pnl_pct": 3.4,  "original_message": "BUY HDFCBANK CMP 1625\nTGT 1680\nSL 1590"},
    {"stock_symbol": "TCS",        "action": "SELL", "call_type": "Swing",    "cmp": 3950,  "entry_price": 3950,  "target1": 3880,  "stoploss": 4010, "duration": "2 Days",     "status": "SL Hit",      "pnl_pct": -1.5, "original_message": "SELL TCS @3950\nTARGET 3880\nSL 4010"},
    {"stock_symbol": "SBIN",       "action": "BUY",  "call_type": "Swing",    "cmp": 798,   "entry_price": 800,   "target1": 840,   "target2": 860,  "stoploss": 775,  "duration": "1 Week",     "status": "Target Hit",  "pnl_pct": 5.0,  "original_message": "BUY SBI\nCMP 798\nTGT1 840 TGT2 860\nSL 775"},
    {"stock_symbol": "WIPRO",      "action": "BUY",  "call_type": "Swing",    "cmp": 468,   "entry_price": 470,   "target1": 495,   "stoploss": 455,  "duration": "5-7 Days",   "status": "Expired",     "pnl_pct": -0.4, "original_message": "WIPRO BUY ABOVE 470\nTARGET 495\nSL 455\n5-7 DAYS"},
    {"stock_symbol": "ICICIBANK",  "action": "BUY",  "call_type": "Intraday", "cmp": 1102,  "entry_price": 1105,  "target1": 1145,  "stoploss": 1075, "duration": "Intraday",   "status": "Target Hit",  "pnl_pct": 3.6,  "original_message": "ICICI BANK BUY 1105\nTGT 1145\nSL 1075\nINTRADAY"},
    {"stock_symbol": "BAJFINANCE", "action": "BUY",  "call_type": "Swing",    "cmp": 7200,  "entry_price": 7220,  "target1": 7450,  "stoploss": 7050, "duration": "3 Days",     "status": "SL Hit",      "pnl_pct": -2.4, "original_message": "BUY BAJFINANCE\nCMP 7200 ENTRY 7220\nTARGET 7450\nSL 7050"},
    {"stock_symbol": "MARUTI",     "action": "BUY",  "call_type": "Positional","cmp": 12400, "entry_price": 12400, "target1": 12800, "stoploss": 12100,"duration": "1-2 Weeks",  "status": "Pending",     "pnl_pct": None, "original_message": "MARUTI ACCUMULATE\nTGT 12800\nSL 12100\n1-2 WEEKS"},
]

BROKER_CALL_MAP = [0, 1, 2, 3, 4, 0, 1, 3, 2, 4]   # index into BROKERS


def seed_data():
    broker_objs = []
    for bd in BROKERS:
        b = Broker(**bd)
        db.session.add(b)
        broker_objs.append(b)
    db.session.flush()

    today = date.today()
    for i, ct in enumerate(CALLS_TEMPLATE):
        broker = broker_objs[BROKER_CALL_MAP[i]]
        call_date = today - timedelta(days=i * 2 + 1)
        c = StockCall(
            call_date    = call_date,
            call_time    = "10:00",
            broker_id    = broker.id,
            broker_name  = broker.name,
            exchange     = "NSE",
            source_channel = "Manual",
            support      = ct.get("cmp", 0) * 0.97 if ct.get("cmp") else None,
            resistance   = ct.get("target1", 0) * 1.05 if ct.get("target1") else None,
            **{k: v for k, v in ct.items() if k not in ("support", "resistance")},
        )
        db.session.add(c)

    db.session.commit()
