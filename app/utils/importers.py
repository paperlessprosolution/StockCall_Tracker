"""
app/utils/importers.py  —  Multi-source import parsers

Supports:
  - CSV / Excel (structured columns)
  - WhatsApp exported chat (.txt)
  - Telegram exported chat (JSON)
  - PDF (text extraction via pdfplumber + OCR fallback via pytesseract)
"""

import re
import json
import io
import logging
from datetime import datetime, date
from typing import Generator

import pandas as pd

logger = logging.getLogger(__name__)


# ── CSV / Excel ──────────────────────────────────────────────────────────────

COLUMN_ALIASES = {
    "stock_symbol": ["stock", "symbol", "ticker", "scrip", "stock_symbol", "name"],
    "action":       ["action", "buy_sell", "type", "call"],
    "broker_name":  ["broker", "broker_name", "source"],
    "cmp":          ["cmp", "current_price", "ltp", "price"],
    "entry_price":  ["entry", "entry_price", "buy_price", "buy at"],
    "target1":      ["target", "target1", "tgt", "tgt1", "tp1"],
    "target2":      ["target2", "tgt2", "tp2"],
    "stoploss":     ["sl", "stoploss", "stop_loss", "stop loss"],
    "call_type":    ["type", "call_type", "category", "duration_type"],
    "duration":     ["duration", "time", "time_frame"],
    "call_date":    ["date", "call_date", "rec_date", "recommendation_date"],
    "exchange":     ["exchange", "exch"],
    "original_message": ["message", "original", "original_message", "raw"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map any CSV header variant to our canonical column names."""
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if col.lower().strip() in aliases:
                rename_map[col] = canonical
                break
    return df.rename(columns=rename_map)


def _row_to_call_dict(row: pd.Series, default_broker: str = "CSV Import") -> dict:
    def _float(v):
        try:
            return float(str(v).replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    def _date(v):
        if pd.isna(v):
            return date.today()
        try:
            return pd.to_datetime(v).date()
        except Exception:
            return date.today()

    action = str(row.get("action", "BUY")).upper().strip()
    if action not in ("BUY", "SELL"):
        action = "BUY"

    return {
        "stock_symbol":    str(row.get("stock_symbol", "")).upper().strip(),
        "broker_name":     str(row.get("broker_name", default_broker)).strip(),
        "action":          action,
        "call_type":       str(row.get("call_type", "Swing")).strip(),
        "cmp":             _float(row.get("cmp")),
        "entry_price":     _float(row.get("entry_price")) or _float(row.get("cmp")),
        "target1":         _float(row.get("target1")),
        "target2":         _float(row.get("target2")),
        "stoploss":        _float(row.get("stoploss")),
        "duration":        str(row.get("duration", "")).strip() or None,
        "call_date":       _date(row.get("call_date")),
        "exchange":        str(row.get("exchange", "NSE")).upper().strip(),
        "original_message": str(row.get("original_message", "")).strip() or None,
        "source_channel":  "CSV",
    }


def parse_csv(file_bytes: bytes, broker_name: str = "CSV Import") -> list:
    df = pd.read_csv(io.BytesIO(file_bytes))
    df = _normalize_columns(df)
    calls, errors = [], []
    for i, row in df.iterrows():
        try:
            c = _row_to_call_dict(row, broker_name)
            if not c["stock_symbol"]:
                errors.append(f"Row {i+2}: missing stock symbol")
                continue
            calls.append(c)
        except Exception as e:
            errors.append(f"Row {i+2}: {e}")
    return calls, errors


def parse_excel(file_bytes: bytes, broker_name: str = "Excel Import") -> list:
    df = pd.read_excel(io.BytesIO(file_bytes))
    df = _normalize_columns(df)
    calls, errors = [], []
    for i, row in df.iterrows():
        try:
            c = _row_to_call_dict(row, broker_name)
            if not c["stock_symbol"]:
                errors.append(f"Row {i+2}: missing stock symbol")
                continue
            calls.append(c)
        except Exception as e:
            errors.append(f"Row {i+2}: {e}")
    return calls, errors


# ── WhatsApp Chat Export ─────────────────────────────────────────────────────
# Format: "DD/MM/YYYY, HH:MM - Sender: message"  or
#         "[DD/MM/YYYY, HH:MM:SS] Sender: message"

WA_PATTERN = re.compile(
    r"(?:(?P<d1>\d{1,2}/\d{1,2}/\d{2,4}),?\s+(?P<t1>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\s*[-–]\s*"
    r"|(?:\[(?P<d2>\d{1,2}/\d{1,2}/\d{2,4}),?\s+(?P<t2>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)\]))\s*"
    r"(?P<sender>[^:]+):\s*(?P<msg>.+)"
)

STOCK_CALL_KEYWORDS = [
    "CMP", "TARGET", "TGT", "STOPLOSS", "SL ", " SL", "BUY ", "SELL ",
    "ACCUMULATE", "INTRADAY", "SWING", "SUPPORT", "RESISTANCE",
]


def _looks_like_call(text: str) -> bool:
    upper = text.upper()
    matches = sum(1 for kw in STOCK_CALL_KEYWORDS if kw in upper)
    return matches >= 2


def parse_whatsapp(file_bytes: bytes, broker_name: str = "WhatsApp") -> tuple:
    """
    Parse WhatsApp exported chat .txt file.
    Multi-line messages are joined before parsing.
    """
    from .parser import parse_message

    text = file_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()

    # Group lines into messages
    messages = []
    current = None
    for line in lines:
        m = WA_PATTERN.match(line)
        if m:
            if current:
                messages.append(current)
            d = m.group("d1") or m.group("d2")
            t = m.group("t1") or m.group("t2")
            try:
                dt = datetime.strptime(d.strip(), "%d/%m/%Y")
                call_date = dt.date()
            except Exception:
                call_date = date.today()
            current = {
                "sender": m.group("sender").strip(),
                "date":   call_date,
                "time":   t.strip()[:5],
                "text":   m.group("msg").strip(),
            }
        elif current:
            current["text"] += "\n" + line.strip()

    if current:
        messages.append(current)

    calls, errors = [], []
    for msg in messages:
        if not _looks_like_call(msg["text"]):
            continue
        try:
            parsed = parse_message(msg["text"])
            if not parsed.get("stock_symbol"):
                continue
            calls.append({
                **_parsed_to_call(parsed, msg["text"]),
                "broker_name":    broker_name,
                "call_date":      msg["date"],
                "call_time":      msg["time"],
                "source_channel": "WhatsApp",
            })
        except Exception as e:
            errors.append(str(e))

    return calls, errors


# ── Telegram Export ──────────────────────────────────────────────────────────
# Telegram exports as JSON: {"messages": [{...}]}

def parse_telegram(file_bytes: bytes, broker_name: str = "Telegram") -> tuple:
    from .parser import parse_message

    try:
        data = json.loads(file_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        return [], [f"Invalid JSON: {e}"]

    msgs = data.get("messages", [])
    calls, errors = [], []

    for msg in msgs:
        if msg.get("type") != "message":
            continue
        # Text can be a string or list of text entities
        raw_text = msg.get("text", "")
        if isinstance(raw_text, list):
            raw_text = "".join(
                (p["text"] if isinstance(p, dict) else p) for p in raw_text
            )
        raw_text = str(raw_text).strip()
        if not _looks_like_call(raw_text):
            continue
        try:
            dt_str = msg.get("date", "")
            try:
                dt = datetime.fromisoformat(dt_str)
                call_date = dt.date()
                call_time = dt.strftime("%H:%M")
            except Exception:
                call_date = date.today()
                call_time = None

            parsed = parse_message(raw_text)
            if not parsed.get("stock_symbol"):
                continue
            calls.append({
                **_parsed_to_call(parsed, raw_text),
                "broker_name":    broker_name,
                "call_date":      call_date,
                "call_time":      call_time,
                "source_channel": "Telegram",
            })
        except Exception as e:
            errors.append(str(e))

    return calls, errors


# ── PDF Import ───────────────────────────────────────────────────────────────

def parse_pdf(file_bytes: bytes, broker_name: str = "PDF") -> tuple:
    """
    Extract stock calls from PDF using pdfplumber (text layer),
    with pytesseract OCR fallback for scanned PDFs.
    """
    from .parser import parse_message

    calls, errors = [], []

    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        errors.append(f"PDF text extraction failed: {e}")
        full_text = ""

    # OCR fallback for scanned PDFs
    if not full_text.strip():
        try:
            import pytesseract
            from PIL import Image
            import pdfplumber
            ocr_parts = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    img = page.to_image(resolution=200).original
                    ocr_parts.append(pytesseract.image_to_string(img))
            full_text = "\n".join(ocr_parts)
        except Exception as e:
            errors.append(f"OCR fallback failed: {e}")

    if not full_text.strip():
        return calls, errors + ["No text extracted from PDF"]

    # Split into call blocks by double-newline or known separators
    blocks = re.split(r"\n{2,}|={3,}|[-]{3,}", full_text)
    for block in blocks:
        block = block.strip()
        if not block or not _looks_like_call(block):
            continue
        try:
            parsed = parse_message(block)
            if not parsed.get("stock_symbol"):
                continue
            calls.append({
                **_parsed_to_call(parsed, block),
                "broker_name":    broker_name,
                "call_date":      date.today(),
                "source_channel": "PDF",
            })
        except Exception as e:
            errors.append(str(e))

    return calls, errors


# ── Shared helper ────────────────────────────────────────────────────────────

def _parsed_to_call(parsed: dict, original_msg: str) -> dict:
    targets = parsed.get("targets", [])
    return {
        "stock_symbol":    parsed.get("stock_symbol", ""),
        "action":          parsed.get("action", "BUY"),
        "call_type":       parsed.get("call_type", "Swing"),
        "cmp":             parsed.get("cmp"),
        "entry_price":     parsed.get("entry_price") or parsed.get("cmp"),
        "target1":         targets[0] if len(targets) > 0 else None,
        "target2":         targets[1] if len(targets) > 1 else None,
        "target3":         targets[2] if len(targets) > 2 else None,
        "stoploss":        parsed.get("stoploss"),
        "support":         parsed.get("support"),
        "resistance":      parsed.get("resistance"),
        "duration":        parsed.get("duration"),
        "exchange":        parsed.get("exchange", "NSE"),
        "original_message": original_msg,
        "parsed_data":     json.dumps(parsed),
        "status":          "Pending",
    }
