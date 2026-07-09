"""
Shared parser module extracted from backend/services/parser.py
This module provides `MessageParser` and related parsers for reuse.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import re

# A compact known-stocks list (kept in sync with backend/services/parser)
KNOWN_STOCKS = {
    "RELIANCE", "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM",
}


@dataclass
class ParsedCall:
    stock: str = ""
    exchange: str = "NSE"
    action: str = "BUY"
    cmp: Optional[float] = None
    entry_price: Optional[float] = None
    targets: list = field(default_factory=list)
    stoploss: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    duration: str = ""
    call_type: str = "Swing"
    confidence: str = "Medium"
    broker_hint: str = ""
    raw_fields: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d["target1"] = self.targets[0] if len(self.targets) > 0 else None
        d["target2"] = self.targets[1] if len(self.targets) > 1 else None
        d["target3"] = self.targets[2] if len(self.targets) > 2 else None
        return d


class MessageParser:
    PRICE_PATTERNS = {
        "cmp": [r"CMP\s*[:\-]?\s*(\d+(?:\.\d+)?)"],
        "entry": [r"(?:ENTRY|ENTER|BUY)\s*(?:@|AT|ABOVE|AROUND|NEAR)?\s*(\d+(?:\.\d+)?)"],
        "stoploss": [r"(?:STOP\s*LOSS|STOPLOSS|SL|S/L)\s*[:\-]?\s*(\d+(?:\.\d+)?)"],
    }

    def parse(self, message: str) -> ParsedCall:
        result = ParsedCall()
        if not message:
            return result
        upper = message.upper()
        # stock
        for sym in KNOWN_STOCKS:
            if re.search(r"\b" + re.escape(sym) + r"\b", upper):
                result.stock = sym
                break
        # simple price extracts
        m = re.search(self.PRICE_PATTERNS["cmp"][0], upper)
        if m:
            try:
                result.cmp = float(m.group(1))
            except Exception:
                pass
        m = re.search(self.PRICE_PATTERNS["entry"][0], upper)
        if m:
            try:
                result.entry_price = float(m.group(1))
            except Exception:
                pass
        m = re.search(self.PRICE_PATTERNS["stoploss"][0], upper)
        if m:
            try:
                result.stoploss = float(m.group(1))
            except Exception:
                pass
        return result
