"""
app/utils/price_engine.py  —  Live stock price fetching (NSE/BSE via yfinance)
"""

import yfinance as yf
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def _build_yf_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Convert NSE/BSE symbol to Yahoo Finance format."""
    symbol = symbol.upper().strip()
    # Remove any existing suffix
    symbol = symbol.replace(".NS", "").replace(".BO", "")
    # Some special cases
    aliases = {
        "M&M": "M&M",
        "BAJAJ-AUTO": "BAJAJ-AUTO",
    }
    symbol = aliases.get(symbol, symbol)
    suffix = ".BO" if exchange == "BSE" else ".NS"
    return symbol + suffix


def get_live_price(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch live / latest price for a single stock.
    Returns dict with price, change_pct, day_high, day_low, volume, prev_close.
    """
    yf_sym = _build_yf_symbol(symbol, exchange)
    try:
        ticker = yf.Ticker(yf_sym)
        info   = ticker.fast_info
        price  = float(getattr(info, "last_price", 0) or 0)

        if not price:
            # Fallback: 1-day history
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        prev_close = float(getattr(info, "previous_close", 0) or 0)
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0

        return {
            "symbol":      symbol,
            "exchange":    exchange,
            "price":       round(price, 2),
            "day_high":    round(float(getattr(info, "day_high", 0) or 0), 2),
            "day_low":     round(float(getattr(info, "day_low",  0) or 0), 2),
            "prev_close":  round(prev_close, 2),
            "change_pct":  change_pct,
            "volume":      int(getattr(info, "volume",  0) or 0),
            "fetched_at":  datetime.utcnow().isoformat(),
            "success":     price > 0,
        }
    except Exception as e:
        logger.warning(f"Price fetch failed for {yf_sym}: {e}")
        return {
            "symbol": symbol, "exchange": exchange,
            "price": 0, "success": False, "error": str(e),
            "fetched_at": datetime.utcnow().isoformat(),
        }


def get_bulk_prices(symbols_exchanges: list) -> dict:
    """
    Fetch prices for multiple symbols in one yfinance call.
    symbols_exchanges: list of (symbol, exchange) tuples
    Returns {symbol: price_dict}
    """
    results = {}
    if not symbols_exchanges:
        return results

    yf_map = {}
    for sym, exch in symbols_exchanges:
        yf_sym = _build_yf_symbol(sym, exch)
        yf_map[yf_sym] = (sym, exch)

    try:
        tickers_str = " ".join(yf_map.keys())
        data = yf.download(
            tickers_str,
            period="1d",
            interval="1m",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            timeout=15,
        )
        now = datetime.utcnow().isoformat()

        for yf_sym, (sym, exch) in yf_map.items():
            try:
                if len(yf_map) == 1:
                    close_series = data["Close"]
                else:
                    close_series = data[yf_sym]["Close"]

                price = float(close_series.dropna().iloc[-1]) if not close_series.dropna().empty else 0
                results[sym] = {
                    "symbol": sym, "exchange": exch,
                    "price": round(price, 2),
                    "success": price > 0,
                    "fetched_at": now,
                }
            except Exception:
                results[sym] = {
                    "symbol": sym, "exchange": exch,
                    "price": 0, "success": False, "fetched_at": now,
                }
    except Exception as e:
        logger.error(f"Bulk price fetch failed: {e}")
        now = datetime.utcnow().isoformat()
        for sym, exch in symbols_exchanges:
            results[sym] = {
                "symbol": sym, "exchange": exch,
                "price": 0, "success": False,
                "error": str(e), "fetched_at": now,
            }

    return results


def refresh_pending_call_prices():
    """
    Background job: refresh current_price for all Pending calls,
    then auto-update statuses.
    """
    from .. import db
    from ..models import StockCall, PriceHistory

    pending = StockCall.query.filter(StockCall.status == "Pending").all()
    if not pending:
        return

    symbols = list({(c.stock_symbol, c.exchange) for c in pending})
    prices  = get_bulk_prices(symbols)

    updated = 0
    for call in pending:
        pd = prices.get(call.stock_symbol)
        if pd and pd.get("success") and pd["price"] > 0:
            call.current_price    = pd["price"]
            call.price_updated_at = datetime.utcnow()
            call.auto_update_status()

            # Store in price history
            ph = PriceHistory(
                symbol=call.stock_symbol,
                exchange=call.exchange,
                price=pd["price"],
                change_pct=pd.get("change_pct"),
                day_high=pd.get("day_high"),
                day_low=pd.get("day_low"),
                prev_close=pd.get("prev_close"),
                volume=pd.get("volume"),
            )
            db.session.add(ph)
            updated += 1

    db.session.commit()

    # Recalculate broker scores after batch update
    broker_ids = {c.broker_id for c in pending}
    from ..models import Broker
    for bid in broker_ids:
        b = Broker.query.get(bid)
        if b:
            b.recalculate_score()
    db.session.commit()

    logger.info(f"Price refresh complete: {updated}/{len(pending)} calls updated")
    return updated
