"""
Analytics Service
Computes broker reliability scores, accuracy metrics,
risk-reward analysis, and sector performance.
"""

import json
from database import get_db


# ─────────────────────────────────────────────
# Broker Reliability Scoring
# ─────────────────────────────────────────────

def compute_broker_score(broker_id: int) -> float:
    """
    Analyst-style broker reliability score (0-100) based on:
    - Hit rate: target and partial-hit performance
    - Risk-reward discipline: target/SL geometry
    - P&L quality: average outcome and consistency
    - Recency: the last 10 calls matter more than older ones
    - Drawdown: consecutive SL hits reduce confidence sharply
    """
    with get_db() as conn:
        calls = conn.execute("""
            SELECT sc.id, sc.status, sc.entry_price, sc.target1, sc.stoploss,
                   sc.call_date, sc.call_time, co.pnl_pct
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            WHERE sc.broker_id = ?
              AND sc.status IN ('Target Hit','Partial Hit','SL Hit','Expired')
            ORDER BY sc.call_date DESC, sc.call_time DESC
        """, (broker_id,)).fetchall()

    if not calls or len(calls) < 3:
        return 50.0

    total = len(calls)
    target_hits = sum(1 for c in calls if c["status"] == "Target Hit")
    partial_hits = sum(1 for c in calls if c["status"] == "Partial Hit")
    sl_hits = sum(1 for c in calls if c["status"] == "SL Hit")
    wins = target_hits + partial_hits

    # Accuracy: target/partial hit rate
    hit_rate = (wins / total) * 100

    # Risk-reward component: reward / risk ratio, capped at 3.5x
    rr_values = []
    for c in calls:
        entry = c["entry_price"]
        target = c["target1"]
        stop = c["stoploss"]
        if entry and target and stop and entry != stop:
            reward = abs(target - entry)
            risk = abs(entry - stop)
            rr_values.append((reward / risk) if risk > 0 else 0)

    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 1.5
    rr_score = min(avg_rr / 3.5, 1.0) * 100

    # P&L quality: a broker with strong average return scores higher
    pnls = [c["pnl_pct"] for c in calls if c["pnl_pct"] is not None]
    if pnls:
        avg_pnl = sum(pnls) / len(pnls)
        pnl_score = max(0, min(100, 50 + avg_pnl * 3.0))
    else:
        pnl_score = 50.0

    # Consistency: low variance is a sign of disciplined execution
    if len(pnls) >= 3:
        mean_pnl = sum(pnls) / len(pnls)
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / len(pnls)
        std_dev = variance ** 0.5
        consistency = max(0, min(100, 100 - std_dev * 4))
    else:
        consistency = 60.0

    # Recency: reward recent calls more than older ones
    recent_calls = calls[: min(10, len(calls))]
    if recent_calls:
        recent_wins = sum(1 for c in recent_calls if c["status"] in ("Target Hit", "Partial Hit"))
        recent_hit_rate = (recent_wins / len(recent_calls)) * 100
        recent_pnls = [c["pnl_pct"] for c in recent_calls if c["pnl_pct"] is not None]
        recent_avg_pnl = (sum(recent_pnls) / len(recent_pnls)) if recent_pnls else 0
        recency_score = max(0, min(100, recent_hit_rate + recent_avg_pnl * 2.0))
    else:
        recency_score = 50.0

    # Drawdown penalty for consecutive stop-loss hits
    statuses = [c["status"] for c in calls]
    max_streak = 0
    cur_streak = 0
    for s in statuses:
        if s == "SL Hit":
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 0
    drawdown_score = max(0, 100 - max_streak * 20)

    # Final score: weighted, with stop-loss impact reducing score
    score = (
        hit_rate * 0.35 +
        rr_score * 0.20 +
        pnl_score * 0.15 +
        consistency * 0.15 +
        recency_score * 0.10 +
        drawdown_score * 0.05
    )
    score -= (sl_hits / total) * 18

    return round(min(max(score, 0), 100), 1)


def update_all_broker_scores():
    """Recompute and persist reliability scores for all brokers."""
    with get_db() as conn:
        brokers = conn.execute("SELECT id FROM brokers").fetchall()
    for b in brokers:
        score = compute_broker_score(b["id"])
        with get_db() as conn:
            conn.execute(
                "UPDATE brokers SET reliability = ?, updated_at = datetime('now') WHERE id = ?",
                (score, b["id"])
            )


# ─────────────────────────────────────────────
# Dashboard Analytics
# ─────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    with get_db() as conn:
        calls = conn.execute("""
            SELECT sc.*, co.pnl_pct
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
        """).fetchall()

    total   = len(calls)
    hits    = sum(1 for c in calls if c["status"] == "Target Hit")
    partial = sum(1 for c in calls if c["status"] == "Partial Hit")
    sl_hit  = sum(1 for c in calls if c["status"] == "SL Hit")
    pending = sum(1 for c in calls if c["status"] == "Pending")
    expired = sum(1 for c in calls if c["status"] == "Expired")
    closed  = hits + partial + sl_hit + expired

    accuracy = round((hits + partial) / closed * 100, 1) if closed else 0

    pnls = [c["pnl_pct"] for c in calls if c["pnl_pct"] is not None]
    avg_return  = round(sum(pnls) / len(pnls), 2) if pnls else 0
    total_pnl   = round(sum(pnls), 2)
    best_return = round(max(pnls), 2) if pnls else 0
    worst_return= round(min(pnls), 2) if pnls else 0

    return {
        "total":         total,
        "hits":          hits,
        "partial":       partial,
        "sl_hit":        sl_hit,
        "pending":       pending,
        "expired":       expired,
        "closed":        closed,
        "accuracy":      accuracy,
        "avg_return":    avg_return,
        "total_pnl":     total_pnl,
        "best_return":   best_return,
        "worst_return":  worst_return,
    }


def get_broker_analytics() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                b.id, b.name, b.category, b.source, b.reliability,
                COUNT(sc.id)                                           AS total_calls,
                SUM(sc.status = 'Target Hit')                         AS target_hits,
                SUM(sc.status = 'Partial Hit')                        AS partial_hits,
                SUM(sc.status = 'SL Hit')                             AS sl_hits,
                SUM(sc.status = 'Pending')                            AS pending,
                AVG(co.pnl_pct)                                       AS avg_pnl,
                MAX(co.pnl_pct)                                       AS best_pnl,
                MIN(co.pnl_pct)                                       AS worst_pnl
            FROM brokers b
            LEFT JOIN stock_calls sc ON sc.broker_id = b.id
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            GROUP BY b.id
            ORDER BY b.reliability DESC
        """).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        closed = (d["target_hits"] or 0) + (d["partial_hits"] or 0) + (d["sl_hits"] or 0)
        wins   = (d["target_hits"] or 0) + (d["partial_hits"] or 0)
        d["win_rate"]    = round(wins / closed * 100, 1) if closed else 0
        d["avg_pnl"]     = round(d["avg_pnl"] or 0, 2)
        d["best_pnl"]    = round(d["best_pnl"] or 0, 2)
        d["worst_pnl"]   = round(d["worst_pnl"] or 0, 2)
        d["reliability"] = round(d["reliability"] or 50.0, 1)
        result.append(d)
    return result


def get_accuracy_by_call_type() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                call_type,
                COUNT(*)                                AS total,
                SUM(status IN ('Target Hit','Partial Hit')) AS wins,
                SUM(status = 'SL Hit')                  AS losses,
                AVG(co.pnl_pct)                         AS avg_pnl
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            GROUP BY call_type
        """).fetchall()
    return [
        {
            **dict(r),
            "accuracy": round((r["wins"] or 0) / r["total"] * 100, 1) if r["total"] else 0,
            "avg_pnl":  round(r["avg_pnl"] or 0, 2),
        }
        for r in rows
    ]


def get_monthly_performance() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                strftime('%Y-%m', sc.call_date)         AS month,
                COUNT(sc.id)                            AS total,
                SUM(sc.status IN ('Target Hit','Partial Hit')) AS wins,
                AVG(co.pnl_pct)                         AS avg_pnl,
                SUM(co.pnl_pct)                         AS total_pnl
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            WHERE sc.status != 'Pending'
            GROUP BY month
            ORDER BY month ASC
        """).fetchall()

    result = []
    cumulative = 0.0
    for r in rows:
        d = dict(r)
        d["accuracy"]  = round((d["wins"] or 0) / d["total"] * 100, 1) if d["total"] else 0
        d["avg_pnl"]   = round(d["avg_pnl"] or 0, 2)
        d["total_pnl"] = round(d["total_pnl"] or 0, 2)
        cumulative    += d["total_pnl"]
        d["cumulative_pnl"] = round(cumulative, 2)
        result.append(d)
    return result


def get_rr_analysis() -> list[dict]:
    """Risk-reward analysis for all calls with entry + target + SL."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT sc.id, sc.stock, sc.action, sc.entry_price,
                   sc.target1, sc.stoploss, sc.status, sc.call_type,
                   co.pnl_pct
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            WHERE sc.entry_price IS NOT NULL
              AND sc.target1 IS NOT NULL
              AND sc.stoploss IS NOT NULL
        """).fetchall()

    result = []
    for r in rows:
        entry  = r["entry_price"]
        t1     = r["target1"]
        sl     = r["stoploss"]
        reward = abs(t1 - entry)
        risk   = abs(entry - sl)
        rr     = round(reward / risk, 2) if risk > 0 else 0
        result.append({
            "id":        r["id"],
            "stock":     r["stock"],
            "action":    r["action"],
            "call_type": r["call_type"],
            "status":    r["status"],
            "rr_ratio":  rr,
            "reward_pct": round(reward / entry * 100, 2) if entry else 0,
            "risk_pct":   round(risk / entry * 100, 2) if entry else 0,
            "pnl_pct":   round(r["pnl_pct"] or 0, 2),
        })
    return sorted(result, key=lambda x: x["rr_ratio"], reverse=True)


def get_top_stocks() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                stock,
                COUNT(*)                                 AS total,
                SUM(status IN ('Target Hit','Partial Hit')) AS wins,
                AVG(co.pnl_pct)                          AS avg_pnl
            FROM stock_calls sc
            LEFT JOIN call_outcomes co ON co.call_id = sc.id
            GROUP BY stock
            HAVING total >= 2
            ORDER BY avg_pnl DESC
            LIMIT 10
        """).fetchall()

    return [
        {
            **dict(r),
            "win_rate": round((r["wins"] or 0) / r["total"] * 100, 1),
            "avg_pnl":  round(r["avg_pnl"] or 0, 2),
        }
        for r in rows
    ]
