"""
app/utils/analytics.py  —  Analytics computation engine
"""

from datetime import datetime, timedelta, date
from collections import defaultdict
import statistics
from ..models import StockCall, Broker
from .. import db


def get_dashboard_stats() -> dict:
    calls = StockCall.query.all()
    total = len(calls)
    if total == 0:
        return _empty_stats()

    status_counts = defaultdict(int)
    for c in calls:
        status_counts[c.status] += 1

    completed = [c for c in calls if c.pnl_pct is not None]
    wins  = [c for c in completed if c.pnl_pct > 0]
    loss  = [c for c in completed if c.pnl_pct < 0]

    avg_return   = sum(c.pnl_pct for c in completed) / len(completed) if completed else 0
    win_rate     = round((status_counts["Target Hit"] + status_counts["Partial Hit"]) / total * 100, 1)
    best_call    = max(completed, key=lambda c: c.pnl_pct).to_dict() if completed else None
    worst_call   = min(completed, key=lambda c: c.pnl_pct).to_dict() if completed else None

    # 30-day rolling accuracy
    thirty_ago   = datetime.utcnow().date() - timedelta(days=30)
    recent_calls = [c for c in calls if c.call_date and c.call_date >= thirty_ago]
    recent_wins  = sum(1 for c in recent_calls if c.status in ("Target Hit", "Partial Hit"))
    recent_acc   = round(recent_wins / len(recent_calls) * 100, 1) if recent_calls else 0

    return {
        "total_calls":    total,
        "target_hit":     status_counts["Target Hit"],
        "partial_hit":    status_counts["Partial Hit"],
        "sl_hit":         status_counts["SL Hit"],
        "pending":        status_counts["Pending"],
        "expired":        status_counts["Expired"],
        "win_rate":       win_rate,
        "avg_return":     round(avg_return, 2),
        "best_call":      best_call,
        "worst_call":     worst_call,
        "recent_accuracy": recent_acc,
        "status_dist":    dict(status_counts),
    }


def get_broker_analytics() -> list:
    brokers = Broker.query.filter_by(is_active=True).all()
    result  = []
    for b in brokers:
        calls = b.calls.all()
        if not calls:
            result.append({**b.to_dict(), "monthly_acc": [], "call_type_breakdown": {}})
            continue

        # Monthly accuracy for sparkline
        monthly = defaultdict(lambda: {"wins": 0, "total": 0})
        for c in calls:
            if c.call_date:
                key = c.call_date.strftime("%Y-%m")
                monthly[key]["total"] += 1
                if c.status in ("Target Hit", "Partial Hit"):
                    monthly[key]["wins"] += 1
        monthly_acc = [
            {
                "month": k,
                "accuracy": round(v["wins"] / v["total"] * 100, 1),
                "total": v["total"],
            }
            for k, v in sorted(monthly.items())[-6:]
        ]

        # Call type breakdown
        type_map = defaultdict(lambda: {"total": 0, "wins": 0})
        for c in calls:
            type_map[c.call_type]["total"] += 1
            if c.status in ("Target Hit", "Partial Hit"):
                type_map[c.call_type]["wins"] += 1
        call_type_breakdown = {
            k: {"total": v["total"], "win_rate": round(v["wins"] / v["total"] * 100, 1)}
            for k, v in type_map.items()
        }

        result.append({
            **b.to_dict(),
            "monthly_acc": monthly_acc,
            "call_type_breakdown": call_type_breakdown,
        })

    return sorted(result, key=lambda x: x["reliability_score"], reverse=True)


def get_accuracy_trends(days: int = 90) -> list:
    """Weekly accuracy buckets over the past N days."""
    since = datetime.utcnow().date() - timedelta(days=days)
    calls = StockCall.query.filter(StockCall.call_date >= since).all()

    weekly = defaultdict(lambda: {"wins": 0, "total": 0})
    for c in calls:
        if not c.call_date:
            continue
        # ISO week key
        key = c.call_date.strftime("%Y-W%W")
        weekly[key]["total"] += 1
        if c.status in ("Target Hit", "Partial Hit"):
            weekly[key]["wins"] += 1

    return [
        {
            "week": k,
            "accuracy": round(v["wins"] / v["total"] * 100, 1) if v["total"] else 0,
            "total": v["total"],
            "wins": v["wins"],
        }
        for k, v in sorted(weekly.items())
    ]


def get_pnl_series() -> dict:
    """Cumulative P&L series for equity curve chart."""
    completed = (
        StockCall.query
        .filter(StockCall.pnl_pct.isnot(None))
        .order_by(StockCall.closed_at)
        .all()
    )
    cum = 0.0
    series = []
    for c in completed:
        cum += c.pnl_pct
        series.append({
            "date":   c.closed_at.isoformat() if c.closed_at else c.call_date.isoformat(),
            "pnl":    round(c.pnl_pct, 2),
            "cum":    round(cum, 2),
            "stock":  c.stock_symbol,
            "broker": c.broker_name,
            "status": c.status,
        })
    return {
        "series": series,
        "total_return": round(cum, 2),
        "total_trades": len(completed),
    }


def get_call_type_stats() -> list:
    call_types = ["Intraday", "Swing", "Positional", "Long Term"]
    result = []
    for ct in call_types:
        calls = StockCall.query.filter_by(call_type=ct).all()
        total = len(calls)
        wins  = sum(1 for c in calls if c.status in ("Target Hit", "Partial Hit"))
        sl    = sum(1 for c in calls if c.status == "SL Hit")
        pnls  = [c.pnl_pct for c in calls if c.pnl_pct is not None]
        result.append({
            "call_type":  ct,
            "total":      total,
            "wins":       wins,
            "sl_hits":    sl,
            "accuracy":   round(wins / total * 100, 1) if total else 0,
            "avg_return": round(sum(pnls) / len(pnls), 2) if pnls else 0,
        })
    return result


def get_risk_reward_stats() -> list:
    calls = StockCall.query.filter(
        StockCall.entry_price.isnot(None),
        StockCall.stoploss.isnot(None),
        StockCall.target1.isnot(None),
    ).all()
    return [
        {
            "stock":       c.stock_symbol,
            "broker":      c.broker_name,
            "risk_reward": c.risk_reward,
            "status":      c.status,
            "pnl_pct":     c.pnl_pct,
            "call_type":   c.call_type,
            "call_date":   c.call_date.isoformat() if c.call_date else None,
        }
        for c in calls
        if c.risk_reward
    ]


def _empty_stats() -> dict:
    return {
        "total_calls": 0, "target_hit": 0, "partial_hit": 0,
        "sl_hit": 0, "pending": 0, "expired": 0,
        "win_rate": 0, "avg_return": 0,
        "best_call": None, "worst_call": None,
        "recent_accuracy": 0, "status_dist": {},
    }
