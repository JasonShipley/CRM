"""MCE engineering calculators inside the quote app (quotes.usemce.com/calc).

Routes (all behind the same Caddy basic auth as the quotes):
  GET  /calc                                  calculator list
  GET  /calc/dryer/                           rotary dryer calculator (HTML built from the Excel workbook)
  POST /calc/dryer/api/dryer/workbook         save a sizing record: engine run + PDF report + Excel workbook
  POST /calc/dryer/api/dryer/workbook/xlsx    Excel workbook for the current inputs (download)
  POST /calc/dryer/api/dryer                  full engine JSON contract (mce.dryer.v1)
  GET  /calc/dryer/records                    saved sizing records with their PDF, Excel and JSON
  GET  /calc/dryer/records/<file>             one record file

The engine is the vendored snapshot in vendor/ (see vendor/VENDORED.txt and vendor/sync_from_engineering.sh).
Sizing records are written to MCE_AUDIT_ROOT (a Docker volume, backed up nightly by deploy/backup.sh).
"""
import json
import os
import pathlib
import re
import sys
import threading

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, send_from_directory

VENDOR = pathlib.Path(__file__).resolve().parent / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from mce_engineering.equipment.dryer_calc.api import run  # noqa: E402
from mce_engineering.equipment.dryer_calc.excel import workbook_filename, workbook_from_entries  # noqa: E402
from mce_engineering.equipment.dryer_calc.html_calc import build_html  # noqa: E402
from mce_engineering.equipment.dryer_calc.server import save_workbook_run  # noqa: E402

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
RECORD_FILE = re.compile(r"^RD-\d{6}(\.pdf|\.xlsx|\.calculator\.json|\.json)$")

bp = Blueprint("calc", __name__)
_page = {"html": None}
_page_lock = threading.Lock()


def audit_root() -> pathlib.Path:
    return pathlib.Path(os.environ.get("MCE_AUDIT_ROOT", "/data/audit"))


def files_dir() -> pathlib.Path:
    return audit_root() / "files"


def vendored() -> str:
    try:
        return (VENDOR / "VENDORED.txt").read_text().splitlines()[1].replace("Commit: ", "")
    except (OSError, IndexError):
        return "unknown"


@bp.route("/calc")
def calc_index():
    return render_template("calc_index.html", vendored=vendored())


@bp.route("/calc/dryer")
def dryer_redirect():
    return redirect("/calc/dryer/", code=301)


@bp.route("/calc/dryer/")
def dryer_page():
    with _page_lock:
        if _page["html"] is None:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                _page["html"] = build_html(pathlib.Path(tmp) / "calc.html").read_text()
    html = _page["html"].replace(
        '<footer><span>',
        '<footer><span><a href="/calc/dryer/records" style="color:#575D5E;margin-right:14px">Sizing records</a>'
        '<a href="/" style="color:#575D5E;margin-right:14px">Quotes</a>', 1)
    return Response(html, mimetype="text/html")


@bp.route("/calc/dryer/api/dryer/workbook", methods=["POST"])
def dryer_save():
    rec = request.get_json(force=True, silent=True) or {}
    try:
        resp = save_workbook_run(rec, audit_root=audit_root(), files_dir=files_dir())
    except (KeyError, ValueError) as e:
        resp = {"status": "error", "error": str(e)}
    return jsonify(json.loads(json.dumps(resp, default=str)))


@bp.route("/calc/dryer/api/dryer/workbook/xlsx", methods=["POST"])
def dryer_xlsx():
    rec = request.get_json(force=True, silent=True) or {}
    ent = rec.get("entries", {})
    try:
        data = workbook_from_entries(ent)
    except (KeyError, ValueError) as e:
        return jsonify({"status": "error", "error": str(e)}), 400
    return Response(data, mimetype=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{workbook_filename(ent)}"'})


@bp.route("/calc/dryer/api/dryer", methods=["POST"])
def dryer_api():
    resp = run(request.get_json(force=True, silent=True) or {}, audit_root=audit_root())
    return jsonify(json.loads(json.dumps(resp, default=str)))


def _value(x):
    return x.get("value") if isinstance(x, dict) else x


@bp.route("/calc/dryer/records")
def dryer_records():
    root = audit_root()
    idx_file = root / "index.jsonl"
    rows = []
    if idx_file.exists():
        for line in reversed(idx_file.read_text().splitlines()[-500:]):
            meta = json.loads(line)
            if meta.get("family") != "rotary_dryer":
                continue
            row = {"index": meta["index"], "job": meta.get("job_number", ""), "time": meta.get("timestamp", "")[:16]}
            try:
                body = json.loads((root / f"{meta['index']}.json").read_text())
                res, drum = body["results"]["results"], body["results"]["drum"]["recommended"]
                row["burner"] = f"{_value(res['burner_operating_mmbtu_hr_lhv']):.2f}"
                row["design"] = f"{_value(res['burner_design_mmbtu_hr_lhv']):.2f}"
                row["evap"] = f"{_value(body['results']['mass_balance']['evaporation_lb_hr']):,.0f}"
                row["drum"] = drum["size"] if drum else "none passes"
                row["customer"] = body["inputs"]["request"]["job"].get("customer", "")
            except (OSError, KeyError, TypeError, ValueError):
                pass
            row["files"] = [n for n in (f"{meta['index']}.pdf", f"{meta['index']}.xlsx")
                            if (files_dir() / n).exists()]
            rows.append(row)
    return render_template("calc_records.html", rows=rows)


@bp.route("/calc/dryer/records/<name>")
def dryer_record_file(name):
    if not RECORD_FILE.match(name):
        abort(404)
    folder = audit_root() if re.match(r"^RD-\d{6}\.json$", name) else files_dir()
    if not (folder / name).exists():
        abort(404)
    return send_from_directory(folder, name, as_attachment=not name.endswith(".pdf"))
