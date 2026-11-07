"""Standalone server: the dryer calculator on a phone without the quote app.

    python -m mce_engineering.equipment.dryer_calc serve --port 8095

GET  /                 the calculator (product, throughput, moisture in and out, fuel, elevation; live formulas
                       from the Excel workbook in the browser)
GET  /calculator       same page
GET  /form             plain form that posts to /run and returns the one-page sizing report
POST /api/dryer        JSON request (mce.dryer.v1) -> JSON response
POST /api/dryer/workbook  calculator entries -> sizing record + cross-check against the Python engine
POST /api/dryer/workbook/xlsx  calculator entries -> the live MCE Excel workbook for those inputs
POST /run              form post -> one-page HTML report
GET  /schema           request JSON Schema
Standard library only; the quote app can call api.run() directly instead.
"""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .api import run
from .excel import request_from_entries, workbook_filename, workbook_from_entries
from .presets import FUELS, MATERIALS
from .report import to_html
from .schema import input_json_schema


def _opts(d: dict, sel: str) -> str:
    return "".join(f"<option value='{k}'{' selected' if k == sel else ''}>{html.escape(v['label'])}</option>"
                   for k, v in d.items())


FORM = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Rotary Dryer Calculator</title>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:0 16px;background:#fff;color:#111}}
label{{display:block;margin:.6em 0 .2em;font-size:.9rem}}input,select{{width:100%;padding:.5em;font-size:1rem;
box-sizing:border-box}}button{{margin:1em 0;width:100%;padding:.8em;font-size:1rem;background:#e8731a;color:#fff;
border:0;border-radius:6px}}h1{{font-size:1.2rem}}.row{{display:flex;gap:8px}}.row>div{{flex:1}}</style></head><body>
<p>Midwest Custom Engineering, Inc.</p><h1>Rotary dryer sizing</h1><form method=post action=/run>
<label>Job number<input name=job_number value=""></label>
<label>Product<select name=material>{_opts(MATERIALS, 'wood_shavings')}</select></label>
<div class=row><div><label>Throughput<input name=throughput type=number step=any value=1.5></label></div>
<div><label>Unit<select name=throughput_unit><option>TPH</option><option>lb/hr</option></select></label></div></div>
<label>Throughput basis<select name=throughput_basis><option value=wet_feed>Wet infeed</option>
<option value=product>Dried product</option></select></label>
<div class=row><div><label>Moisture in % wb<input name=infeed_mc_wb type=number step=any placeholder="product default"></label></div>
<div><label>Moisture out % wb<input name=target_mc_wb type=number step=any placeholder="product default"></label></div></div>
<label>Fuel<select name=fuel>{_opts(FUELS, 'biomass')}</select></label>
<label>Site elevation ft<input name=elevation_ft type=number step=any value=1200></label>
<label>Advanced (JSON merged into the request, optional)<input name=advanced value=""></label>
<button type=submit>Size dryer</button></form>
<p><a href="/">Open the calculator</a> (live results, customer sheet, Excel download).</p>
<p style="font-size:.8rem;color:#555">Every run is saved as a sizing record. All defaults can be overridden in the
advanced JSON; overrides and out-of-range values are flagged.</p></body></html>"""


def _merge(a: dict, b: dict) -> dict:
    for k, v in b.items():
        a[k] = _merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a


def form_to_request(f: dict[str, str]) -> dict:
    def num(k):
        return float(f[k]) if str(f.get(k, "")).strip() else None

    proc = {"material": f["material"], "throughput": num("throughput"), "throughput_unit": f["throughput_unit"],
            "throughput_basis": f.get("throughput_basis", "wet_feed"),
            "infeed_mc_wb": num("infeed_mc_wb"), "target_mc_wb": num("target_mc_wb")}
    req = {"job": {"job_number": f.get("job_number") or "UNASSIGNED"},
           "process": {k: v for k, v in proc.items() if v is not None},
           "site": {k: v for k, v in {"elevation_ft": num("elevation_ft")}.items() if v is not None},
           "fuel": {"fuel": f["fuel"]}}
    if f.get("advanced", "").strip():
        req = _merge(req, json.loads(f["advanced"]))
    return req


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, ctype: str) -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/schema":
            return self._send(200, json.dumps(input_json_schema(), indent=2), "application/json")
        if self.path.rstrip("/") == "/form":
            return self._send(200, FORM, "text/html; charset=utf-8")
        if self.path.rstrip("/") in ("", "/calculator"):
            return self._send(200, calculator_page(), "text/html; charset=utf-8")
        return self._send(404, "not found", "text/plain")

    def do_POST(self):  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        if self.path.endswith("/api/dryer/workbook/xlsx"):
            try:
                rec = json.loads(raw)
                data = workbook_from_entries(rec.get("entries", {}))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                return self._send(400, json.dumps({"status": "error", "error": str(e)}), "application/json")
            self.send_response(200)
            self.send_header("Content-Type", XLSX)
            self.send_header("Content-Disposition", f'attachment; filename="{workbook_filename(rec.get("entries", {}))}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return None
        if self.path.endswith("/api/dryer/workbook"):
            try:
                resp = save_workbook_run(json.loads(raw))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                resp = {"status": "error", "error": str(e)}
            return self._send(200, json.dumps(resp, default=str), "application/json")
        if self.path == "/api/dryer":
            try:
                resp = run(json.loads(raw))
            except json.JSONDecodeError as e:
                resp = {"status": "error", "error": f"invalid JSON: {e}"}
            return self._send(200, json.dumps(resp, default=str), "application/json")
        if self.path == "/run":
            try:
                resp = run(form_to_request({k: v[0] for k, v in parse_qs(raw).items()}))
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                resp = {"status": "error", "error": str(e)}
            if resp.get("status") != "ok":
                msg = html.escape(json.dumps({k: resp.get(k) for k in ("status", "error", "message", "details")},
                                             indent=1, default=str))
                return self._send(200, f"<meta name=viewport content='width=device-width'><pre>{msg}</pre>"
                                       f"<a href=/>Back</a>", "text/html; charset=utf-8")
            return self._send(200, to_html(resp), "text/html; charset=utf-8")
        return self._send(404, "not found", "text/plain")


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PAGE: str | None = None


def calculator_page() -> str:
    global _PAGE
    if _PAGE is None:
        import tempfile
        from pathlib import Path

        from .html_calc import build_html
        with tempfile.TemporaryDirectory() as tmp:
            _PAGE = build_html(Path(tmp) / "calc.html").read_text()
    return _PAGE


CROSS = {"d_mf": ("results", "fuel_lb_hr"), "d_BurnerOp": ("results", "burner_operating_mmbtu_hr_lhv"),
         "d_BtuLb": ("results", "btu_per_lb_water_lhv"), "x_sEX_acfm": ("gas_balance", "streams", "dryer_exhaust", "acfm"),
         "d_Evap": ("mass_balance", "evaporation_lb_hr")}


def save_workbook_run(rec: dict, audit_root=None, files_dir=None) -> dict:
    """Calculator record -> engine run (writes the sizing record) + cross-check of the browser's numbers.
    With files_dir, the sizing report PDF, the workbook and the calculator entries are stored beside the record."""
    req, ignored = request_from_entries(rec.get("entries", {}))
    resp = run({**req, "save_record": True}, audit_root=audit_root)
    if resp.get("status") != "ok":
        return resp
    files = []
    if files_dir is not None:
        from pathlib import Path

        from mce_engineering.core.audit import AuditStore

        from .report import write_pdf
        idx = resp["record"]["index"]
        d = Path(files_dir)
        d.mkdir(parents=True, exist_ok=True)
        write_pdf(resp, d / f"{idx}.pdf")
        (d / f"{idx}.xlsx").write_bytes(workbook_from_entries(rec.get("entries", {}), record_index=idx))
        (d / f"{idx}.calculator.json").write_text(json.dumps(rec, indent=2, default=str))
        files = [f"{idx}.pdf", f"{idx}.xlsx", f"{idx}.calculator.json"]
        AuditStore(resp["record"]["store"]).attach_files(idx, files)
    diffs = {}
    for k, path in CROSS.items():
        v = resp["outputs"]
        for p in path:
            v = v[p]
        v = v["value"] if isinstance(v, dict) else v
        b = rec.get("results", {}).get(k)
        if isinstance(b, (int, float)) and v:
            diffs[k] = abs(b - v) / abs(v)
    worst = max(diffs.values()) if diffs else None
    summary = ("not checked" if worst is None else
               f"matches the engine (largest difference {worst:.1e})" if worst < 1e-4 else
               f"DIFFERS from the engine by up to {worst:.2%}: check the inputs")
    return {"status": "ok", "record": resp["record"], "summary": resp["summary"], "files": files,
            "crosscheck": {"summary": summary, "relative_differences": diffs, "workbook_only_inputs": ignored}}


def serve(port: int = 8095) -> None:
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
