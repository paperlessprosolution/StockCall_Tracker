"""
app/utils/parser.py  —  Stock call message parser
Handles all common broker message formats via regex + keyword matching.
"""

import re
from typing import Optional


# ── Known NSE/BSE ticker list (common large caps) ────────────────────────────
KNOWN_STOCKS = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "INFOSYS", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC", "LT", "AXISBANK", "MARUTI",
    "TITAN", "BAJFINANCE", "BAJAJFINSV", "WIPRO", "HCLTECH", "ULTRACEMCO",
    "ASIANPAINT", "POWERGRID", "NTPC", "ONGC", "COALINDIA", "TECHM",
    "NESTLEIND", "DIVISLAB", "APOLLOHOSP", "DRREDDY", "CIPLA", "SUNPHARMA",
    "TATAMOTORS", "TATASTEEL", "TATACONSUM", "TATACHEM", "JSWSTEEL",
    "HINDALCO", "VEDL", "ADANIENT", "ADANIPORTS", "ADANIGREEN",
    "GRASIM", "SHREECEM", "AMBUJACEM", "ACC", "DABUR", "MARICO",
    "PIDILITIND", "BERGEPAINT", "GODREJCP", "VOLTAS", "HAVELLS",
    "BAJAJ-AUTO", "BAJAJ_AUTO", "BAJAJFINSV", "HDFC", "HDFCLIFE",
    "ICICIPRULI", "SBILIFE", "MUTHOOTFIN", "M&M", "MAHINDRA",
    "INDUSINDBK", "FEDERALBNK", "RBLBANK", "BANDHANBNK", "PNB",
    "CANBK", "BANKBARODA", "IDFCFIRSTB", "SAIL", "NMDC", "HPCL",
    "BPCL", "IOC", "GAIL", "TATAPOWER", "TORNTPOWER", "CESC",
    "LUPIN", "BIOCON", "ALKEM", "TORNTPHARM", "AUROPHARMA",
    "ZOMATO", "PAYTM", "NYKAA", "DELHIVERY", "POLICYBAZAAR",
    "IRCTC", "HAL", "BEL", "BHEL", "RVNL", "IRFC",
    "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY",
}

STOP_WORDS = {
    "BUY", "SELL", "CMP", "LTP", "TARGET", "TGT", "TGTS",
    "STOPLOSS", "STOP", "LOSS", "SL", "SUPPORT", "SUP",
    "RESISTANCE", "RES", "ABOVE", "BELOW", "NEAR", "AROUND",
    "INTRADAY", "SWING", "POSITIONAL", "LONG", "TERM", "SHORT",
    "WEEK", "WEEKS", "DAY", "DAYS", "MONTH", "MONTHS",
    "CALL", "RECO", "RECOMMENDATION", "ENTRY", "EXIT",
    "PROFIT", "LOSS", "PARTIAL", "BOOK", "HOLD",
    "ACCUMULATE", "REDUCE", "NEUTRAL", "INITIATE", "COVERAGE",
    "NSE", "BSE", "MCX", "NCDEX", "FNO", "FUTURES", "OPTIONS",
    "SECURITIES", "FINANCIAL", "CAPITAL", "TRADING", "INVEST",
    "HIGH", "LOW", "OPEN", "CLOSE", "VOLUME", "OI",
    "THE", "AND", "FOR", "WITH", "FROM", "INTO", "UPON",
    "AT", "OF", "IN", "ON", "IS", "IT", "TO", "AS", "BE",
    "CAN", "MAY", "WILL", "SHALL", "SHOULD", "WOULD",
}

CALL_TYPE_PATTERNS = {
    "Intraday":  [r"\bINTRADAY\b", r"\bINTRA\b", r"\bDAY\s*TRADE\b"],
    "Swing":     [r"\bSWING\b", r"\b2[-–]\d+\s*DAYS?\b", r"\b\d[-–]\d\s*DAYS?\b"],
    "Positional":[r"\bPOSITIONAL\b", r"\bPOSITION\b", r"\b\d[-–]\d\s*WEEKS?\b"],
    "Long Term": [r"\bLONG\s*TERM\b", r"\bLT\b", r"\b\d[-–]\d\s*MONTHS?\b", r"\bFUNDAMENTAL\b"],
}


def parse_message(text: str) -> dict:
    """
    Main parsing function. Returns structured dict from raw broker message.
    """
    raw   = text.strip()
    upper = raw.upper()

    result = {
        "stock_symbol":   _extract_stock(upper),
        "action":         _extract_action(upper),
        "call_type":      _extract_call_type(upper),
        "cmp":            _extract_number(upper, [r"CMP\s*[:\-]?\s*(\d+(?:\.\d+)?)", r"LTP\s*[:\-]?\s*(\d+(?:\.\d+)?)"]),
        "entry_price":    _extract_entry(upper),
        "targets":        _extract_targets(upper),
        "stoploss":       _extract_number(upper, [r"(?:STOPLOSS|STOP\s*LOSS|SL)\s*[:\-]?\s*(\d+(?:\.\d+)?)"]),
        "support":        _extract_number(upper, [r"SUPPORT\s*[:\-]?\s*(\d+(?:\.\d+)?)", r"SUP\s*[:\-]?\s*(\d+(?:\.\d+)?)"]),
        "resistance":     _extract_number(upper, [r"RESISTANCE\s*[:\-]?\s*(\d+(?:\.\d+)?)", r"RES\s*[:\-]?\s*(\d+(?:\.\d+)?)"]),
        "duration":       _extract_duration(upper),
        "exchange":       "BSE" if "BSE" in upper else "NSE",
        "confidence":     0,
    }

    # Fill in entry from CMP if missing
    if not result["entry_price"] and result["cmp"]:
        result["entry_price"] = result["cmp"]

    result["confidence"] = _confidence_score(result)
    result["probability_label"] = _probability_label(result["confidence"])

    return result


# ── Private helpers ──────────────────────────────────────────────────────────

def _extract_stock(upper: str) -> Optional[str]:
    # 1. Check against known tickers first
    tokens = re.split(r"[\s\n\r:,/\-]+", upper)
    for tok in tokens:
        clean = re.sub(r"[^A-Z0-9&\-_]", "", tok)
        if clean in KNOWN_STOCKS:
            return clean

    # 2. Heuristic: uppercase word 3–12 chars, not a stop word
    candidates = []
    for tok in tokens:
        clean = re.sub(r"[^A-Z]", "", tok)
        if 3 <= len(clean) <= 12 and clean not in STOP_WORDS:
            candidates.append(clean)

    # Prefer tokens near BUY/SELL keywords
    action_pos = -1
    for i, tok in enumerate(tokens):
        if tok in ("BUY", "SELL", "ACCUMULATE"):
            action_pos = i
            break

    if action_pos >= 0:
        for offset in [1, 2, -1]:
            idx = action_pos + offset
            if 0 <= idx < len(tokens):
                c = re.sub(r"[^A-Z]", "", tokens[idx])
                if 3 <= len(c) <= 12 and c not in STOP_WORDS:
                    return c

    return candidates[0] if candidates else None


def _extract_action(upper: str) -> str:
    sell_pats = [r"\bSELL\b", r"\bSHORT\b", r"\bSHORT\s*SELL\b"]
    for p in sell_pats:
        if re.search(p, upper):
            return "SELL"
    return "BUY"


def _extract_call_type(upper: str) -> str:
    for ctype, patterns in CALL_TYPE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, upper):
                return ctype
    return "Swing"


def _extract_number(upper: str, patterns: list) -> Optional[float]:
    for pat in patterns:
        m = re.search(pat, upper)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def _extract_entry(upper: str) -> Optional[float]:
    patterns = [
        r"ENTRY\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        r"ABOVE\s*(\d+(?:\.\d+)?)",
        r"BELOW\s*(\d+(?:\.\d+)?)",
        r"BUY\s+\w+\s+@\s*(\d+(?:\.\d+)?)",
        r"BUY\s+\w+\s+AT\s*(\d+(?:\.\d+)?)",
        r"BUY\s+ABOVE\s*(\d+(?:\.\d+)?)",
    ]
    return _extract_number(upper, patterns)


def _extract_targets(upper: str) -> list:
    targets = []

    # Slash-separated targets: TARGET 1510 / 1540 / 1580
    slash = re.search(
        r"(?:TARGET|TGT)\s*[:\-]?\s*(\d+(?:\.\d+)?)(?:\s*/\s*(\d+(?:\.\d+)?))?(?:\s*/\s*(\d+(?:\.\d+)?))?",
        upper
    )
    if slash:
        for g in slash.groups():
            if g:
                try:
                    targets.append(float(g.replace(",", "")))
                except ValueError:
                    pass
        if targets:
            return targets

    # Multiple labeled targets: TGT1 840 TGT2 860
    for pat in [r"TGT\s*1\s*[:\-]?\s*(\d+(?:\.\d+)?)", r"TARGET\s*1\s*[:\-]?\s*(\d+(?:\.\d+)?)"]:
        m = re.search(pat, upper)
        if m:
            targets.append(float(m.group(1)))
    for pat in [r"TGT\s*2\s*[:\-]?\s*(\d+(?:\.\d+)?)", r"TARGET\s*2\s*[:\-]?\s*(\d+(?:\.\d+)?)"]:
        m = re.search(pat, upper)
        if m:
            targets.append(float(m.group(1)))
    for pat in [r"TGT\s*3\s*[:\-]?\s*(\d+(?:\.\d+)?)", r"TARGET\s*3\s*[:\-]?\s*(\d+(?:\.\d+)?)"]:
        m = re.search(pat, upper)
        if m:
            targets.append(float(m.group(1)))

    if not targets:
        m = re.search(r"(?:TARGET|TGT)\s*[:\-]?\s*(\d+(?:\.\d+)?)", upper)
        if m:
            targets.append(float(m.group(1)))

    return targets


def _extract_duration(upper: str) -> Optional[str]:
    patterns = [
        r"(\d+[-–]\d+\s*(?:DAYS?|WEEKS?|MONTHS?))",
        r"(\d+\s*(?:DAYS?|WEEKS?|MONTHS?))",
        r"(INTRADAY)",
        r"(OVERNIGHT)",
    ]
    for pat in patterns:
        m = re.search(pat, upper)
        if m:
            return m.group(1).strip().title()
    return None


def _confidence_score(r: dict) -> int:
    """0-100 confidence that parsing was successful."""
    score = 0
    if r["stock_symbol"]: score += 25
    if r["entry_price"]:  score += 20
    if r["targets"]:      score += 20
    if r["stoploss"]:     score += 20
    if r["duration"]:     score += 10
    if r["cmp"]:          score += 5
    return score


def _probability_label(score: int) -> str:
    if score >= 80:
        return "High"
    elif score >= 50:
        return "Medium"
    return "Low"
