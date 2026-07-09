"""
Price Fetcher Service
Fetches live/recent stock prices from Yahoo Finance (yfinance)
with SQLite caching to avoid rate limits.
"""

import requests
import time
import json
from datetime import datetime, timedelta
from database import get_db


# Cache duration: refresh prices older than this
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_nse_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Convert plain symbol to Yahoo Finance format."""
    symbol = symbol.upper().strip()
    # Handle special cases
    replacements = {
        "M&M": "M%26M",
        "BAJAJ-AUTO": "BAJAJ-AUTO",
        "L&T": "LT",
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    }
    if symbol in replacements:
        return replacements[symbol]
    if exchange == "BSE":
        return f"{symbol}.BO"
    return f"{symbol}.NS"


def _fetch_price_via_chart_api(symbol: str, exchange: str = "NSE") -> dict | None:
    """Fetch current price using Yahoo's chart API."""
    yf_symbol = get_nse_symbol(symbol, exchange)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
    params = {"interval": "1d", "range": "1d", "includeAdjustedClose": "true"}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        result = (payload.get("chart") or {}).get("result") or []
        if not result:
            return None

        item = result[0]
        meta = item.get("meta") or {}
        indicators = item.get("indicators") or {}
        quote = (indicators.get("quote") or [{}])[0] or {}
        closes = quote.get("close") or []
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        volumes = quote.get("volume") or []

        price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
        if price is None:
            return None

        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        change_pct = 0.0
        if prev_close and float(prev_close) != 0:
            change_pct = round(((float(price) - float(prev_close)) / float(prev_close)) * 100, 2)

        return {
            "symbol": symbol,
            "exchange": exchange,
            "price": round(float(price), 2),
            "open": round(float(opens[-1] or meta.get("chartPreviousClose") or 0), 2),
            "high": round(float(highs[-1] or meta.get("regularMarketDayHigh") or 0), 2),
            "low": round(float(lows[-1] or meta.get("regularMarketDayLow") or 0), 2),
            "volume": int(volumes[-1] or meta.get("regularMarketVolume") or 0),
            "change_pct": change_pct,
            "fetched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[Price] Chart API fetch error for {symbol}: {e}")
        return None


def fetch_price(symbol: str, exchange: str = "NSE") -> dict | None:
    """
    Fetch current price for a single stock.
    Returns cached result if fresh enough, otherwise a live quote from Yahoo.
    """
    cached = _get_cached(symbol, exchange)
    if cached:
        return cached

    price_data = _fetch_price_via_chart_api(symbol, exchange)
    if price_data and price_data["price"] > 0:
        _update_cache(price_data)
        return price_data

    return None


def fetch_prices_bulk(symbols: list[str], exchange: str = "NSE") -> dict:
    """
    Fetch prices for multiple symbols in one yfinance call.
    Returns dict: {symbol: price_data}
    """
    if not symbols:
        return {}

    results = {}
    # Separate cached from stale
    to_fetch = []
    for sym in symbols:
        cached = _get_cached(sym, exchange)
        if cached:
            results[sym] = cached
        else:
            to_fetch.append(sym)

    if not to_fetch:
        return results

    for sym in to_fetch:
        try:
            price_data = _fetch_price_via_chart_api(sym, exchange)
            if price_data and price_data["price"] > 0:
                _update_cache(price_data)
                results[sym] = price_data
        except Exception:
            pass

    return results


def get_price_history(symbol: str, exchange: str = "NSE", days: int = 30) -> list[dict]:
    """
    Fetch historical OHLCV data for charts.
    """
    yf_symbol = get_nse_symbol(symbol, exchange)
    try:
        ticker = yf.Ticker(yf_symbol)
        period = f"{days}d" if days <= 365 else "2y"
        hist = ticker.history(period=period)
        if hist.empty:
            return []
        records = []
        for dt, row in hist.iterrows():
            records.append({
                "date":   dt.strftime("%Y-%m-%d"),
                "open":   round(float(row["Open"]), 2),
                "high":   round(float(row["High"]), 2),
                "low":    round(float(row["Low"]), 2),
                "close":  round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception as e:
        print(f"[Price] History fetch error for {symbol}: {e}")
        return []


def check_alerts(call_id: int = None) -> list[dict]:
    """
    Check pending alerts against current prices.
    Returns list of triggered alerts.
    """
    triggered = []
    with get_db() as conn:
        query = """
            SELECT a.*, sc.exchange
            FROM alerts a
            JOIN stock_calls sc ON sc.id = a.call_id
            WHERE a.triggered = 0
        """
        if call_id:
            query += f" AND a.call_id = {call_id}"
        alerts = conn.execute(query).fetchall()

    if not alerts:
        return []

    # Get unique symbols
    symbols = list(set(a["stock"] for a in alerts))
    prices = fetch_prices_bulk(symbols)

    with get_db() as conn:
        for alert in alerts:
            sym = alert["stock"]
            price_data = prices.get(sym)
            if not price_data:
                continue
            current_price = price_data["price"]
            trigger = alert["trigger_price"]
            direction = alert["direction"]

            fired = (
                (direction == "ABOVE" and current_price >= trigger) or
                (direction == "BELOW" and current_price <= trigger)
            )

            if fired:
                conn.execute("""
                    UPDATE alerts
                    SET triggered = 1, triggered_at = datetime('now')
                    WHERE id = ?
                """, (alert["id"],))
                triggered.append({
                    "alert_id":    alert["id"],
                    "call_id":     alert["call_id"],
                    "stock":       sym,
                    "alert_type":  alert["alert_type"],
                    "trigger_price": trigger,
                    "current_price": current_price,
                })

    return triggered


def update_call_statuses() -> dict:
    """
    Auto-update call statuses based on live prices.
    Called periodically (e.g., every 5 min during market hours).
    Returns summary of updates.
    """
    updates = {"target_hit": 0, "sl_hit": 0, "checked": 0}

    with get_db() as conn:
        pending = conn.execute("""
            SELECT id, stock, exchange, action, entry_price,
                   target1, target2, stoploss, call_type
            FROM stock_calls
            WHERE status = 'Pending'
        """).fetchall()

    if not pending:
        return updates

    symbols = list(set(c["stock"] for c in pending))
    prices  = fetch_prices_bulk(symbols)

    with get_db() as conn:
        for call in pending:
            sym   = call["stock"]
            pdata = prices.get(sym)
            if not pdata:
                continue

            cp     = pdata["price"]
            action = call["action"]
            t1     = call["target1"]
            sl     = call["stoploss"]
            updates["checked"] += 1

            if action == "BUY":
                if t1 and cp >= t1:
                    new_status = "Target Hit"
                    updates["target_hit"] += 1
                elif sl and cp <= sl:
                    new_status = "SL Hit"
                    updates["sl_hit"] += 1
                else:
                    continue
            else:  # SELL
                if t1 and cp <= t1:
                    new_status = "Target Hit"
                    updates["target_hit"] += 1
                elif sl and cp >= sl:
                    new_status = "SL Hit"
                    updates["sl_hit"] += 1
                else:
                    continue

            # Compute P&L
            entry = call["entry_price"] or cp
            exit_p = t1 if new_status == "Target Hit" else sl
            if exit_p and entry:
                if action == "BUY":
                    pnl = round((exit_p - entry) / entry * 100, 2)
                else:
                    pnl = round((entry - exit_p) / entry * 100, 2)
            else:
                pnl = 0.0

            conn.execute("""
                UPDATE stock_calls
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (new_status, call["id"]))

            conn.execute("""
                INSERT OR REPLACE INTO call_outcomes
                    (call_id, exit_price, exit_date, pnl_pct)
                VALUES (?, ?, date('now'), ?)
            """, (call["id"], exit_p, pnl))

    return updates


# ── Cache helpers ─────────────────────────────
def _get_cached(symbol: str, exchange: str) -> dict | None:
    cutoff = (datetime.now() - timedelta(seconds=CACHE_TTL_SECONDS)).isoformat()
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM price_cache
            WHERE symbol = ? AND exchange = ? AND fetched_at > ?
        """, (symbol, exchange, cutoff)).fetchone()
    if row:
        return dict(row)
    return None


def _update_cache(data: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO price_cache
                (symbol, exchange, price, open, high, low, volume, change_pct, fetched_at)
            VALUES (:symbol, :exchange, :price, :open, :high, :low, :volume, :change_pct, :fetched_at)
            ON CONFLICT(symbol, exchange) DO UPDATE SET
                price      = excluded.price,
                open       = excluded.open,
                high       = excluded.high,
                low        = excluded.low,
                volume     = excluded.volume,
                change_pct = excluded.change_pct,
                fetched_at = excluded.fetched_at
        """, data)
