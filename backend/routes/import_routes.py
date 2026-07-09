"""import routes — /api/import"""
import os, json, tempfile
from flask import Blueprint, request, jsonify
import_bp = Blueprint("import", __name__)

ALLOWED = {"csv","xlsx","xls","txt","json","pdf"}

def allowed(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED

@import_bp.route("/parse-message", methods=["POST"])
def parse_message():
    from services.parser import MessageParser
    msg = (request.json or {}).get("message","")
    if not msg.strip(): return jsonify({"error":"empty"}),400
    return jsonify(MessageParser().parse(msg).to_dict())

@import_bp.route("/whatsapp", methods=["POST"])
def whatsapp():
    from services.parser import WhatsAppParser
    if "file" not in request.files: return jsonify({"error":"no file"}),400
    content = request.files["file"].read().decode("utf-8","ignore")
    msgs = WhatsAppParser().parse_text(content)
    return jsonify({"parsed": msgs, "count": len(msgs)})

@import_bp.route("/telegram", methods=["POST"])
def telegram():
    from services.parser import TelegramParser
    if "file" not in request.files: return jsonify({"error":"no file"}),400
    data = json.loads(request.files["file"].read().decode("utf-8"))
    msgs = TelegramParser().parse_data(data)
    return jsonify({"parsed": msgs, "count": len(msgs)})

@import_bp.route("/csv", methods=["POST"])
def csv_import():
    from services.parser import SpreadsheetParser
    if "file" not in request.files: return jsonify({"error":"no file"}),400
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        request.files["file"].save(tmp.name)
        records = SpreadsheetParser().parse_csv(tmp.name)
    os.unlink(tmp.name)
    return jsonify({"records": records, "count": len(records)})

@import_bp.route("/excel", methods=["POST"])
def excel_import():
    from services.parser import SpreadsheetParser
    if "file" not in request.files: return jsonify({"error":"no file"}),400
    f = request.files["file"]
    suffix = "." + f.filename.rsplit(".",1)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        records = SpreadsheetParser().parse_excel(tmp.name)
    os.unlink(tmp.name)
    return jsonify({"records": records, "count": len(records)})

@import_bp.route("/pdf", methods=["POST"])
def pdf_import():
    from services.parser import PDFParser
    if "file" not in request.files: return jsonify({"error":"no file"}),400
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        request.files["file"].save(tmp.name)
        try: records = PDFParser().parse_file(tmp.name)
        except ImportError as e: return jsonify({"error":str(e)}),500
    os.unlink(tmp.name)
    return jsonify({"records": records, "count": len(records)})

@import_bp.route("/bulk-save", methods=["POST"])
def bulk_save():
    from database import get_db
    records = (request.json or {}).get("records",[])
    if not records: return jsonify({"error":"no records"}),400
    saved, errors = 0, []
    with get_db() as conn:
        for i, rec in enumerate(records):
            try:
                p = rec.get("parsed", rec)
                if not p.get("stock"): continue
                conn.execute("""
                    INSERT INTO stock_calls
                        (broker_name,call_date,call_time,stock,action,cmp,
                         entry_price,target1,target2,stoploss,duration,call_type,
                         original_msg,parsed_data)
                    VALUES
                        (:bn,:dt,:tm,:st,:ac,:cmp,
                         :ep,:t1,:t2,:sl,:dur,:ct,:msg,:pd)
                """,{"bn":rec.get("broker_hint",rec.get("sender","")),"dt":rec.get("date",""),
                     "tm":rec.get("time",""),"st":p.get("stock","").upper(),
                     "ac":p.get("action","BUY"),"cmp":p.get("cmp"),
                     "ep":p.get("entry_price"),"t1":p.get("target1"),
                     "t2":p.get("target2"),"sl":p.get("stoploss"),
                     "dur":p.get("duration",""),"ct":p.get("call_type","Swing"),
                     "msg":rec.get("message",""),"pd":json.dumps(p)})
                saved += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        conn.execute("""
            INSERT INTO import_log (source_type,total_rows,imported_rows,failed_rows,errors)
            VALUES ('bulk',?,?,?,?)
        """,(len(records), saved, len(errors), json.dumps(errors)))
    return jsonify({"saved": saved, "errors": errors})
