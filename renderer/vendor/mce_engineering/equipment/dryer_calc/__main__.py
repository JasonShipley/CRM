"""CLI:
    python -m mce_engineering.equipment.dryer_calc run --in request.json [--out DIR] [--no-record]
    python -m mce_engineering.equipment.dryer_calc schema            # JSON Schema of the request
    python -m mce_engineering.equipment.dryer_calc serve [--port 8095]  # standalone JSON + phone page

`run` prints the JSON response and writes <index>_<job>.pdf / .html / .json / .xlsx to --out.
The .xlsx is the live, formula-driven MCE workbook (customer Mass-Energy Balance sheet first).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .api import run
from .excel import build_workbook
from .report import to_html, write_pdf
from .schema import input_json_schema


def _write(resp: dict, out: Path, req: dict | None = None) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{resp['record'].get('index') or 'unsaved'}_{resp['job']['job_number']}"
    stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    files = [out / f"{stem}.json", out / f"{stem}.html", out / f"{stem}.pdf"]
    files[0].write_text(json.dumps(resp, indent=2, default=str))
    files[1].write_text(to_html(resp))
    write_pdf(resp, files[2])
    if req is not None:
        try:
            files.append(build_workbook(req, out / f"{stem}.xlsx", record_index=resp["record"].get("index") or ""))
        except ValueError as e:  # gas modes other than a fixed inlet temperature
            resp.setdefault("notes", []).append(f"workbook not written: {e}")
    return [str(f) for f in files]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dryer_calc")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--in", dest="inp", help="request JSON file (omit for the default test case)")
    r.add_argument("--out", default="outputs/dryer_calc")
    r.add_argument("--no-record", action="store_true", help="do not write the sizing record")
    r.add_argument("--audit-root", default=None)
    sub.add_parser("schema")
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8095)
    a = ap.parse_args(argv)
    if a.cmd == "schema":
        print(json.dumps(input_json_schema(), indent=2))
        return 0
    if a.cmd == "serve":
        from .server import serve
        serve(a.port)
        return 0
    req = json.loads(Path(a.inp).read_text()) if a.inp else {}
    if a.no_record:
        req["save_record"] = False
    resp = run(req, audit_root=a.audit_root)
    if resp["status"] == "ok":
        resp["files"] = _write(resp, Path(a.out), req)
    print(json.dumps(resp, indent=2, default=str))
    return 0 if resp["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
