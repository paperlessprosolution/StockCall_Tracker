"""
Message Parser Service
Extracts structured stock call data from unstructured broker messages
Uses regex, keyword matching, and heuristics (NLP-lite)
"""

import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ─────────────────────────────────────────────
# Known NSE/BSE stock symbols for validation
# ─────────────────────────────────────────────
KNOWN_STOCKS = {
    "RELIANCE", "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM",
    "TATASTEEL", "JSWSTEEL", "SAIL", "HINDALCO", "VEDL",
    "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "BANKBARODA",
    "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "ICICIPRULI",
    "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO",
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "LUPIN",
    "ASIANPAINT", "BERGER", "TITAN", "TRENT", "DMART", "JUBLFOOD",
    "NTPC", "POWERGRID", "ADANIPOWER", "TORNTPOWER", "TATAPOWER",
    "ONGC", "BPCL", "IOC", "HINDPETRO", "GAIL",
    "ULTRACEMCO", "SHREECEM", "ACC", "AMBUJACEM",
    "NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY",
    "ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "DABUR",
    "LT", "SIEMENS", "ABB", "BHEL", "HAL",
    "ZOMATO", "PAYTM", "NYKAA", "POLICYBZR", "IRCTC",
}

# Words to exclude from stock detection
BLACKLIST = {
    "BUY", "SELL", "CMP", "LTP", "TARGET", "TGT", "STOPLOSS", "STOP",
    "LOSS", "SL", "SUPPORT", "RESISTANCE", "ENTRY", "EXIT", "ABOVE",
    "BELOW", "AT", "OR", "AND", "FOR", "WITH", "THE", "THIS", "CALL",
    "INTRADAY", "SWING", "POSITIONAL", "LONGTERM", "LONG", "TERM",
    "DAY", "WEEK", "MONTH", "DAYS", "WEEKS", "MONTHS", "DURATION",
    "TIME", "HOLD", "NSE", "BSE", "MCX", "NCDEX", "STRICTLY",
    "RECOMMENDED", "ACCUMULATE", "BOOK", "PROFIT", "PARTIAL",
    "UPDATE", "ALERT", "NEAR", "AROUND", "APPROX", "PRICE",
    "HIGH", "LOW", "OPEN", "CLOSE", "VOLUME", "SECTOR", "SECURITIES",
    "FINANCIAL", "CAPITAL", "INVESTMENT", "TRADING", "RESEARCH",
    "HDFC", "ICICI", "ZERODHA", "ANGEL", "MOTILAL", "TRADEBULLS",
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
    """
    Multi-strategy parser for broker stock recommendation messages.
    Strategies applied in order:
        1. Known symbol lookup
        2. Regex pattern matching
        3. Contextual keyword extraction
        4. Heuristic fallbacks
    """

    # ── Price extraction patterns ────────────────
    PRICE_PATTERNS = {
        "cmp":        [r"CMP\s*[:\-]?\s*(\d+(?:\.\d+)?)",
                       r"LTP\s*[:\-]?\s*(\d+(?:\.\d+)?)",
                       r"CURRENT\s+(?:PRICE\s*)?[:\-]?\s*(\d+(?:\.\d+)?)"],

        "entry":      [r"(?:ENTRY|ENTER|BUY)\s*(?:@|AT|ABOVE|AROUND|NEAR)?\s*(\d+(?:\.\d+)?)",
                       r"ABOVE\s+(\d+(?:\.\d+)?)",
                       r"@\s*(\d+(?:\.\d+)?)"],

        "target":     [r"(?:TARGET|TGT)\s*[1-3]?\s*[:\-]?\s*(\d+(?:\.\d+)?)",
                       r"T\s*[1-3]\s*[:\-]\s*(\d+(?:\.\d+)?)",
                       r"TP\s*[1-3]?\s*[:\-]?\s*(\d+(?:\.\d+)?)"],

        "stoploss":   [r"(?:STOP\s*LOSS|STOPLOSS|SL|S/L)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
                       r"SL\s*@\s*(\d+(?:\.\d+)?)"],

        "support":    [r"SUPPORT\s*[:\-]?\s*(\d+(?:\.\d+)?)"],
        "resistance": [r"RESISTANCE\s*[:\-]?\s*(\d+(?:\.\d+)?)"],
    }

    # ── Duration patterns ────────────────────────
    DURATION_PATTERNS = [
        r"(\d+[-–]\d+\s*(?:DAYS?|WEEKS?|MONTHS?))",
        r"(\d+\s+(?:TO\s+\d+\s+)?(?:DAYS?|WEEKS?|MONTHS?))",
        r"(ONE\s+WEEK|TWO\s+WEEKS?|ONE\s+MONTH)",
        r"(INTRADAY|BTST|STBT|BTST)",
    ]

    def parse(self, message: str) -> ParsedCall:
        """Main entry point. Returns a ParsedCall dataclass."""
        result = ParsedCall()
        if not message or not message.strip():
            return result

        upper = message.upper().strip()
        lines = [l.strip() for l in upper.split("\n") if l.strip()]

        # 1. Extract broker hint from first line
        result.broker_hint = self._extract_broker(lines)

        # 2. Extract stock symbol
        result.stock = self._extract_stock(upper, lines)

        # 3. Action
        result.action = self._extract_action(upper)

        # 4. Exchange
        result.exchange = self._extract_exchange(upper)

        # 5. Prices
        result.cmp         = self._extract_price(upper, "cmp")
        result.entry_price = self._extract_price(upper, "entry") or result.cmp
        result.stoploss    = self._extract_price(upper, "stoploss")
        result.support     = self._extract_price(upper, "support")
        result.resistance  = self._extract_price(upper, "resistance")

        # 6. Targets (multi)
        result.targets = self._extract_targets(upper)

        # 7. Duration and call type
        result.duration  = self._extract_duration(upper)
        result.call_type = self._infer_call_type(upper, result.duration)

        # 8. Confidence score
        result.confidence = self._score_confidence(result)

        return result

    # ── Stock Extraction ─────────────────────────
    def _extract_stock(self, upper: str, lines: list) -> str:
        # Priority 1: known symbols
        for sym in KNOWN_STOCKS:
            # word boundary match
            if re.search(r"\b" + re.escape(sym) + r"\b", upper):
                return sym

        # Priority 2: ticker-like word after BUY/SELL/ACCUMULATE
        m = re.search(r"(?:BUY|SELL|ACCUMULATE|BOOK|HOLD)\s+([A-Z&\-]{2,12})", upper)
        if m and m.group(1) not in BLACKLIST:
            return m.group(1)

        # Priority 3: ALL-CAPS standalone word not in blacklist (usually 2nd or 3rd line)
        for line in lines[1:4]:
            words = line.split()
            for w in words:
                w_clean = re.sub(r"[^A-Z&\-]", "", w)
                if (len(w_clean) >= 3 and w_clean not in BLACKLIST
                        and re.match(r"^[A-Z]", w_clean)):
                    return w_clean

        return ""

    def _extract_action(self, upper: str) -> str:
        if re.search(r"\bSELL\b", upper):
            return "SELL"
        if re.search(r"\b(?:SHORT|SHORT\s+SELL)\b", upper):
            return "SELL"
        return "BUY"

    def _extract_exchange(self, upper: str) -> str:
        if "BSE" in upper and "NSE" not in upper:
            return "BSE"
        if "MCX" in upper:
            return "MCX"
        return "NSE"

    def _extract_broker(self, lines: list) -> str:
        if lines:
            first = lines[0].rstrip(":").strip()
            # If first line has no numbers and looks like a name
            if first and not re.search(r"\d{3,}", first) and len(first) < 50:
                return first.title()
        return ""

    # ── Price Extraction ─────────────────────────
    def _extract_price(self, upper: str, field_key: str) -> Optional[float]:
        patterns = self.PRICE_PATTERNS.get(field_key, [])
        for pat in patterns:
            m = re.search(pat, upper)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    continue
        return None

    def _extract_targets(self, upper: str) -> list:
        targets = []

        # Pattern: TARGET 1510 / 1540 / 1580
        slash_m = re.search(
            r"(?:TARGET|TGT)\s*[:\-]?\s*([\d.]+(?:\s*/\s*[\d.]+)*)", upper)
        if slash_m:
            parts = re.findall(r"[\d.]+", slash_m.group(1))
            targets = [float(p) for p in parts]
            return targets[:3]

        # Pattern: TARGET1 1510 TARGET2 1540
        multi_m = re.findall(r"(?:TARGET|TGT)\s*[1-3]?\s*[:\-]?\s*([\d.]+)", upper)
        if multi_m:
            return [float(x) for x in multi_m[:3]]

        # Pattern: T1: 1510, T2: 1540
        t_m = re.findall(r"T\s*[1-3]\s*[:\-]\s*([\d.]+)", upper)
        if t_m:
            return [float(x) for x in t_m[:3]]

        return targets

    # ── Duration ─────────────────────────────────
    def _extract_duration(self, upper: str) -> str:
        for pat in self.DURATION_PATTERNS:
            m = re.search(pat, upper)
            if m:
                return m.group(1).strip().title()
        return ""

    def _infer_call_type(self, upper: str, duration: str) -> str:
        if re.search(r"\bINTRADAY\b", upper) or re.search(r"\bBTST\b", upper):
            return "Intraday"
        if re.search(r"\bPOSITIONAL\b", upper):
            return "Positional"
        if re.search(r"\bLONG\s*TERM\b", upper):
            return "Long Term"
        if duration:
            d = duration.lower()
            if "month" in d:
                return "Positional" if "1" in d or "2" in d else "Long Term"
            if "week" in d:
                return "Swing"
            if "day" in d:
                num_m = re.search(r"(\d+)", d)
                if num_m and int(num_m.group(1)) <= 2:
                    return "Intraday"
                return "Swing"
        return "Swing"

    # ── Confidence Scoring ───────────────────────
    def _score_confidence(self, r: ParsedCall) -> str:
        score = 0
        if r.stock:          score += 2
        if r.entry_price:    score += 2
        if r.targets:        score += 2
        if r.stoploss:       score += 2
        if r.cmp:            score += 1
        if r.duration:       score += 1
        if len(r.targets) > 1: score += 1

        if score >= 8:  return "High"
        if score >= 5:  return "Medium"
        return "Low"


# ─────────────────────────────────────────────
# WhatsApp Chat Export Parser
# ─────────────────────────────────────────────
class WhatsAppParser:
    """
    Parses WhatsApp exported chat .txt files.
    Extracts stock call messages from broker chats.
    """

    # Matches: 01/05/2025, 10:30 am - BrokerName: message
    WA_LINE_RE = re.compile(
        r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\s*-\s*([^:]+):\s*(.*)",
        re.IGNORECASE
    )

    def parse_file(self, filepath: str) -> list[dict]:
        messages = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return self.parse_text(content)

    def parse_text(self, text: str) -> list[dict]:
        messages = []
        current = None

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            m = self.WA_LINE_RE.match(line)
            if m:
                if current:
                    messages.append(current)
                date_str, time_str, sender, body = m.groups()
                current = {
                    "date": self._normalize_date(date_str),
                    "time": time_str.strip(),
                    "sender": sender.strip(),
                    "message": body.strip(),
                }
            elif current:
                # Continuation line (multiline message)
                current["message"] += "\n" + line

        if current:
            messages.append(current)

        # Filter: only messages that look like stock calls
        parser = MessageParser()
        result = []
        for msg in messages:
            if self._is_stock_call(msg["message"]):
                parsed = parser.parse(msg["message"])
                if parsed.stock:
                    result.append({
                        **msg,
                        "parsed": parsed.to_dict(),
                        "broker_hint": msg["sender"],
                    })
        return result

    def _is_stock_call(self, text: str) -> bool:
        upper = text.upper()
        keywords = ["BUY", "SELL", "TARGET", "TGT", "STOPLOSS", "SL", "CMP", "ENTRY"]
        return sum(1 for k in keywords if k in upper) >= 2

    def _normalize_date(self, ds: str) -> str:
        parts = ds.replace("-", "/").split("/")
        if len(parts) == 3:
            d, mo, y = parts
            y = y if len(y) == 4 else "20" + y
            return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
        return ds


# ─────────────────────────────────────────────
# Telegram Export Parser (JSON format)
# ─────────────────────────────────────────────
class TelegramParser:
    """
    Parses Telegram exported JSON (result.json).
    Filters messages that look like stock calls.
    """

    def parse_file(self, filepath: str) -> list[dict]:
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.parse_data(data)

    def parse_data(self, data: dict) -> list[dict]:
        messages = data.get("messages", [])
        parser = MessageParser()
        result = []

        for msg in messages:
            if msg.get("type") != "message":
                continue
            text = self._extract_text(msg)
            if not text or not self._is_stock_call(text):
                continue

            parsed = parser.parse(text)
            if parsed.stock:
                result.append({
                    "date": msg.get("date", "")[:10],
                    "time": msg.get("date", "")[11:16],
                    "sender": msg.get("from", ""),
                    "message": text,
                    "parsed": parsed.to_dict(),
                })
        return result

    def _extract_text(self, msg: dict) -> str:
        t = msg.get("text", "")
        if isinstance(t, str):
            return t
        if isinstance(t, list):
            parts = []
            for item in t:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("text", ""))
            return "".join(parts)
        return ""

    def _is_stock_call(self, text: str) -> bool:
        upper = text.upper()
        keywords = ["BUY", "SELL", "TARGET", "TGT", "STOPLOSS", "SL", "CMP"]
        return sum(1 for k in keywords if k in upper) >= 2


# ─────────────────────────────────────────────
# PDF Parser
# ─────────────────────────────────────────────
class PDFParser:
    """
    Extracts stock calls from PDF research reports.
    Uses pdfplumber for text extraction.
    """

    def parse_file(self, filepath: str) -> list[dict]:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("Install pdfplumber: pip install pdfplumber")

        full_text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        return self.parse_text(full_text)

    def parse_text(self, text: str) -> list[dict]:
        """Split text into chunks that look like individual recommendations."""
        parser = MessageParser()
        # Split on lines that start with BUY/SELL or contain CMP
        chunks = self._split_into_calls(text)
        result = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            parsed = parser.parse(chunk)
            if parsed.stock:
                result.append({
                    "message": chunk.strip(),
                    "parsed": parsed.to_dict(),
                })
        return result

    def _split_into_calls(self, text: str) -> list[str]:
        """Split PDF text into individual recommendation blocks."""
        lines = text.split("\n")
        chunks = []
        current = []
        for line in lines:
            upper = line.upper()
            # New recommendation starts with BUY/SELL/ACCUMULATE
            if re.match(r"^\s*(BUY|SELL|ACCUMULATE)\b", upper) and current:
                chunks.append("\n".join(current))
                current = [line]
            elif re.search(r"\bCMP\b|\bTARGET\b|\bSL\b", upper):
                current.append(line)
            elif current:
                current.append(line)
        if current:
            chunks.append("\n".join(current))
        return chunks


# ─────────────────────────────────────────────
# CSV / Excel Import
# ─────────────────────────────────────────────
class SpreadsheetParser:
    """
    Imports stock calls from CSV or Excel files.
    Supports flexible column name mapping.
    """

    COLUMN_ALIASES = {
        "stock":      ["stock", "symbol", "scrip", "ticker", "name"],
        "action":     ["action", "side", "type", "buy/sell", "signal"],
        "entry_price":["entry", "entry_price", "buy_price", "price", "cmp"],
        "target1":    ["target", "target1", "tgt", "tgt1", "t1"],
        "target2":    ["target2", "tgt2", "t2"],
        "stoploss":   ["stoploss", "sl", "stop_loss", "stop"],
        "call_date":  ["date", "call_date", "signal_date"],
        "broker_name":["broker", "source", "sender", "channel"],
        "call_type":  ["type", "call_type", "duration_type"],
        "duration":   ["duration", "time_frame", "holding_period"],
        "original_msg":["message", "original", "notes", "remark"],
    }

    def parse_csv(self, filepath: str) -> list[dict]:
        import pandas as pd
        df = pd.read_csv(filepath)
        return self._process_df(df)

    def parse_excel(self, filepath: str, sheet=0) -> list[dict]:
        import pandas as pd
        df = pd.read_excel(filepath, sheet_name=sheet)
        return self._process_df(df)

    def _process_df(self, df) -> list[dict]:
        import pandas as pd
        # Normalize column names
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        col_map = {}
        for field, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in df.columns:
                    col_map[alias] = field
                    break

        df = df.rename(columns=col_map)
        df = df.where(pd.notnull(df), None)

        records = []
        for _, row in df.iterrows():
            rec = row.to_dict()
            # Ensure required fields
            if not rec.get("stock"):
                continue
            rec["stock"] = str(rec["stock"]).upper().strip()
            records.append(rec)
        return records
