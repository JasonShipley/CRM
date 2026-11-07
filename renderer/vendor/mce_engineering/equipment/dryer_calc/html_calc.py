"""HTML calculator built from the Excel workbook.

    from mce_engineering.equipment.dryer_calc.html_calc import build_html
    build_html("rotary_dryer_calculator.html")

The page carries the workbook itself: every formula cell (rewritten to R1C1 so repeated row formulas share one
template), every defined name, the Inputs rows and pick lists, the Calc rows, and the Mass-Energy Balance sheet's
cells, borders and images. assets/xlcalc.js evaluates those formulas in the browser, so the page and the .xlsx
cannot drift: tests/dryer_calc/test_html_calc.py runs the same engine in Node against the Python engine.

Standalone: one file, works offline on a phone. When served by `server.py`, "Save sizing record" posts the
entries to the Python engine, which writes the audit record and cross-checks the numbers.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter

from .excel import HEAD_FONT, WB_VERSION, build_workbook
from .presets import FUELS, MATERIALS

ASSETS = Path(__file__).resolve().parent / "assets"
DIAGRAM = "Mass-Energy Balance"
EMU_PX = 9525

_REF = re.compile(r"(?<![A-Za-z0-9_.$])(\$?)([A-Z]{1,3})(\$?)(\d+)(?![A-Za-z0-9_(])")


def to_r1c1(formula: str, row: int, col: int) -> str:
    """A1 references (outside string literals) -> R1C1, relative to the formula's own cell."""
    parts = formula.split('"')
    for i in range(0, len(parts), 2):  # even parts are outside quotes
        def sub(m):
            cabs, letters, rabs, digits = m.group(1), m.group(2), m.group(3), m.group(4)
            c = column_index_from_string(letters)
            r = int(digits)
            rs = f"R{r}" if rabs else f"R[{r - row}]"
            cs = f"C{c}" if cabs else f"C[{c - col}]"
            return rs + cs
        parts[i] = _REF.sub(sub, parts[i])
    return '"'.join(parts)


def _range(ref: str) -> tuple[int, int, int, int]:
    ref = ref.replace("$", "")
    a, _, b = ref.partition(":")
    b = b or a
    ma, mb = re.match(r"([A-Z]+)(\d+)", a), re.match(r"([A-Z]+)(\d+)", b)
    return int(ma[2]), column_index_from_string(ma[1]), int(mb[2]), column_index_from_string(mb[1])


def _color(c) -> str | None:
    try:
        rgb = c.rgb if c is not None else None
    except AttributeError:
        return None
    if not isinstance(rgb, str) or len(rgb) < 6:
        return None
    return "#" + rgb[-6:]


def _jsonable(v):
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return str(v)


def export_model(xlsx: Path) -> dict[str, Any]:
    wb = openpyxl.load_workbook(xlsx)
    sheets = wb.sheetnames
    sidx = {n: i for i, n in enumerate(sheets)}
    templates: list[str] = []
    tid: dict[str, int] = {}
    cells: list[dict[str, dict[str, Any]]] = []
    for ws in wb:
        sc: dict[str, dict[str, Any]] = {}
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if v is None:
                    continue
                if isinstance(v, str) and v.startswith("=") and c.data_type == "f":
                    t = to_r1c1(v[1:], c.row, c.column)
                    if t not in tid:
                        tid[t] = len(templates)
                        templates.append(t)
                    val: Any = {"f": tid[t]}
                else:
                    val = _jsonable(v)
                sc.setdefault(str(c.row), {})[str(c.column)] = val
        cells.append(sc)
    names = {}
    for nm, dn in wb.defined_names.items():
        sh, ref = list(dn.destinations)[0]
        r1, c1, r2, c2 = _range(ref)
        names[nm] = [sidx[sh], r1, c1, r2, c2]

    # ---------------- Inputs rows, sections and pick lists
    wsI = wb["Inputs"]
    picks: dict[int, list] = {}
    for dv in wsI.data_validations.dataValidation:
        f = dv.formula1.lstrip("=")
        if f in names:
            s, r1, c1, r2, c2 = names[f]
        else:
            sh, _, ref = f.partition("!")
            s = sidx[sh.strip("'")]
            r1, c1, r2, c2 = _range(ref)
        ws = wb[sheets[s]]
        vals = [ws.cell(r, c).value for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]
        for rng in dv.sqref.ranges:
            for r in range(rng.min_row, rng.max_row + 1):
                picks[r] = [v for v in vals if v is not None]
    by_row = {v[1]: k for k, v in names.items() if v[0] == sidx["Inputs"] and v[2] == 5}
    sections = []
    for r in range(1, wsI.max_row + 1):
        b = wsI.cell(r, 2).value
        if r in by_row:
            lo, hi = wsI.cell(r, 7).value, wsI.cell(r, 8).value
            sections[-1]["rows"].append({
                "name": by_row[r], "row": r, "label": b, "unit": wsI.cell(r, 6).value or "",
                "lo": lo, "hi": hi, "src": wsI.cell(r, 10).value or "", "pick": picks.get(r),
                "numeric": isinstance(lo, (int, float)),
                "entry": _jsonable(wsI.cell(r, 4).value)})
        elif isinstance(b, str) and b.isupper() and wsI.cell(r, 3).value is None and r > 5:
            sections.append({"title": b, "rows": []})

    # ---------------- Calc rows
    wsC = wb["Calc"]
    calc = []
    cnames = {v[1]: k for k, v in names.items() if v[0] == sidx["Calc"] and v[2] == 3 and v[1] == v[3]}
    for r in range(6, wsC.max_row + 1):
        b = wsC.cell(r, 2).value
        if b is None:
            continue
        if wsC.cell(r, 3).value is None and isinstance(b, str) and b.isupper():
            calc.append({"section": b})
            continue
        calc.append({"row": r, "label": b, "name": cnames.get(r, ""), "unit": wsC.cell(r, 4).value or "",
                     "fmt": wsC.cell(r, 3).number_format, "si": wsC.cell(r, 5).value is not None,
                     "si_unit": wsC.cell(r, 6).value or "", "note": wsC.cell(r, 7).value or ""})

    # ---------------- customer sheet layout
    ws = wb[DIAGRAM]
    ncol = ws.max_column
    # Excel: px = TRUNC(((256 w + TRUNC(128 / 7)) / 256) * 7) for a 7 px maximum digit width
    colpx = [int(((256 * (ws.column_dimensions[get_column_letter(c)].width or 8.43) + 18) / 256) * 7)
             for c in range(1, ncol + 1)]
    nrow = ws.max_row
    rowpx = [round((ws.row_dimensions[r].height or 15) * 96 / 72, 2) for r in range(1, nrow + 1)]
    merged = {}
    covered = set()
    for mr in ws.merged_cells.ranges:
        merged[(mr.min_row, mr.min_col)] = (mr.max_row, mr.max_col)
        for r in range(mr.min_row, mr.max_row + 1):
            for c in range(mr.min_col, mr.max_col + 1):
                if (r, c) != (mr.min_row, mr.min_col):
                    covered.add((r, c))
    boxes, texts = [], []
    def sides(cell):
        out = {}
        for side in ("left", "top", "right", "bottom"):
            sd = getattr(cell.border, side)
            if sd is not None and sd.style:
                out[side[0]] = [sd.style, _color(sd.color) or "#000000"]
        return out

    for r in range(1, nrow + 1):
        for c in range(1, ncol + 1):
            if (r, c) in covered:
                continue  # Excel draws a merged area with its top-left cell's format
            cell = ws.cell(r, c)
            r2, c2 = merged.get((r, c), (r, c))
            fill = _color(cell.fill.fgColor) if cell.fill and cell.fill.fill_type == "solid" else None
            bd = sides(cell)
            if (r2, c2) != (r, c):  # outer edges may also sit on the edge cells
                for k, edge in (("r", ws.cell(r, c2)), ("b", ws.cell(r2, c))):
                    e = sides(edge)
                    if k in e and k not in bd:
                        bd[k] = e[k]
            if fill or bd:
                boxes.append([r, c, fill, bd, r2, c2])
            if cell.value is None:
                continue
            f = cell.font
            al = cell.alignment
            texts.append({"r": r, "c": c, "r2": r2, "c2": c2, "fmt": cell.number_format,
                          "b": bool(f.b), "i": bool(f.i), "sz": float(f.sz or 10), "color": _color(f.color) or "#000000",
                          "head": f.name == HEAD_FONT, "h": al.horizontal or "", "v": al.vertical or "",
                          "wrap": bool(al.wrap_text), "indent": al.indent or 0})
    imgs, data = [], {}
    for im in ws._images:
        raw = im._data()
        h = hashlib.sha1(raw).hexdigest()[:12]
        data.setdefault(h, "data:image/png;base64," + base64.b64encode(raw).decode())
        a = im.anchor
        imgs.append({"id": h, "c": a._from.col + 1, "r": a._from.row + 1, "dx": a._from.colOff / EMU_PX,
                     "dy": a._from.rowOff / EMU_PX, "w": a.ext.cx / EMU_PX, "h": a.ext.cy / EMU_PX})
    pa = ws.print_area
    if isinstance(pa, (list, tuple)):
        pa = pa[0]
    pr = _range(str(pa).split("!")[-1]) if pa else (1, 1, nrow, ncol)
    diagram = {"sheet": sidx[DIAGRAM], "colpx": colpx, "rowpx": rowpx, "boxes": boxes, "texts": texts,
               "imgs": imgs, "rows": pr[2], "cols": pr[3]}
    return {"version": WB_VERSION, "sheets": sheets, "templates": templates, "cells": cells, "names": names,
            "inputs": sections, "calc": calc, "diagram": diagram, "images": data,
            "material_keys": {m["label"]: k for k, m in MATERIALS.items()},
            "fuel_keys": {f["label"]: k for k, f in FUELS.items()}}


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rotary Dryer Calculator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{--orange:#FF6602;--black:#000;--steel:#575D5E;--silver:#C8C7C7;--white:#fff;--field:#F1F1F1;--panel:#F5F5F5;
--muted:#9A9A9A;--entry:#FFF4E5;--head:'Oswald','Arial Narrow',Arial,sans-serif;--body:'Inter',Arial,Helvetica,sans-serif}
*{box-sizing:border-box}
html,body{margin:0;overflow-x:hidden;background:#fff;color:#000;font-family:var(--body);font-size:14px}
header{background:var(--black);color:#fff;padding:10px 16px 8px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
header img{height:44px}
header .t{flex:1;min-width:200px;text-align:right}
header h1{font-family:var(--head);font-size:20px;margin:0;letter-spacing:.3px}
header .s{color:var(--orange);font-family:var(--head);font-size:14px;font-weight:600}
.rule{height:4px;background:var(--orange)}
main{max-width:1180px;margin:0 auto;padding:12px 16px 40px}
.grid{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:18px;align-items:start}
.form{display:grid;grid-template-columns:1fr 1fr;gap:10px 12px;margin-top:8px}
.form .f{min-width:0}.form .f.wide{grid-column:1/-1}
.panel{min-width:0}
.form label{display:block;font-size:12px;color:var(--steel);margin-bottom:3px;text-transform:uppercase;font-family:var(--head);letter-spacing:.3px}
.form .ctl{display:flex;gap:6px;align-items:center}
.form input,.form select{flex:1;min-width:0;padding:10px 8px;font-size:16px;border:1px solid var(--silver);border-radius:4px;
background:var(--entry);color:#000;font-weight:600;font-family:var(--body)}
.form select#in_p_TUnit{flex:0 0 92px}
.form input::placeholder{color:#555;font-weight:400}
.form .u{font-size:12px;color:var(--steel);white-space:nowrap}
details{margin-top:18px;border:1px solid var(--silver);border-radius:4px;padding:0 12px}
details>summary{cursor:pointer;padding:12px 0;font-family:var(--head);text-transform:uppercase;letter-spacing:.4px;font-size:15px}
details[open]{padding-bottom:12px}
.bar:first-child{margin-top:0}
.bar{background:var(--steel);color:#fff;font-family:var(--head);text-transform:uppercase;letter-spacing:.4px;padding:6px 10px;
margin:18px 0 6px;border-left:6px solid var(--orange);font-size:14px}
.row{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr) auto;gap:8px;align-items:center;padding:6px 2px;
border-bottom:1px solid #eee}
.row label{font-size:13px}.row .src{grid-column:1/-1;font-size:11px;color:var(--muted);margin-top:-2px}
.row input,.row select{width:100%;padding:8px;font-size:15px;border:1px solid var(--silver);border-radius:4px;background:var(--entry);
color:#0000FF;font-weight:600;font-family:var(--body)}
.row input::placeholder{color:#777;font-weight:400}
.row .u{font-size:12px;color:var(--steel);min-width:70px}
.badge{display:inline-block;font-size:10px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px;vertical-align:middle}
.b-ov{background:#eee;color:var(--steel)}.b-bad{background:var(--orange);color:#fff}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin-top:8px}
.card{border:1px solid var(--silver);border-top:4px solid #000;padding:10px 12px;background:#fff}
.card .k{font-size:11px;text-transform:uppercase;color:var(--steel);font-family:var(--head);letter-spacing:.4px}
.card .v{font-size:22px;font-weight:700;margin-top:2px}.card .v.or{color:var(--orange)}
.card .m{font-size:12px;color:var(--steel);margin-top:2px}
table{border-collapse:collapse;width:100%;font-size:13px}
td,th{border-bottom:1px solid #eee;padding:5px 6px;text-align:left;vertical-align:top}
th{background:#E4E4E4;font-weight:600}
td.n,th.n{text-align:right;white-space:nowrap}
.warn{border-left:4px solid var(--orange);background:var(--panel);padding:8px 10px;margin:6px 0;font-size:13px}
.ok{border-left:4px solid var(--steel);background:var(--panel);padding:8px 10px;margin:6px 0;font-size:13px}
.btns{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.btns button{border:0;background:#000;color:#fff;padding:11px 16px;font-family:var(--head);font-size:14px;letter-spacing:.4px;
text-transform:uppercase;border-radius:4px;cursor:pointer}
.btns button.alt{background:var(--steel)}
.note{font-size:12px;color:var(--steel)}
#sheetWrap{width:100%;overflow:hidden;border:1px solid var(--silver)}
#sheet{position:relative;transform-origin:0 0;background:#fff}
#sheet .bx,#sheet .tx,#sheet img{position:absolute}
#sheet .tx{display:flex;padding:0 2px;line-height:1.05;overflow:visible;white-space:nowrap}
#sheet .tx.wrap{white-space:normal;align-items:flex-start}
.calc td:nth-child(2),.calc td:nth-child(4){text-align:right;white-space:nowrap}
.calc td.note{color:var(--muted);font-size:11px}
footer{border-top:1px solid var(--silver);margin-top:24px;padding:10px 16px;font-size:12px;color:var(--steel);
display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
footer b{font-family:var(--head);letter-spacing:.4px}
footer .tag{color:var(--muted)}
@media (max-width:860px){.grid{grid-template-columns:1fr}}
@media (max-width:560px){header .t{text-align:left}.row{grid-template-columns:1fr 1fr}.row .u{grid-column:2}
.cards{grid-template-columns:1fr 1fr}.card .v{font-size:18px}}
@media print{
  @page{size:letter landscape;margin:0.3in}
  header,.rule,footer,.grid,details{display:none !important}
  details#d-sheet{display:block !important;border:0;padding:0}
  details#d-sheet>summary,details#d-sheet .note{display:none !important}
  main{padding:0;max-width:none}
  #sheetWrap{border:0;page-break-inside:avoid;break-inside:avoid}
}
</style>
</head>
<body>
<header><img alt="Midwest Custom Engineering" src="__LOGO__"><div class="t"><h1>ROTARY DRYER CALCULATOR</h1>
<div class="s">Mass and energy balance, burner, drum, fan</div></div></header>
<div class="rule"></div>
<main>
<div class="grid">
<section class="panel" id="p-in"><div class="bar">Dryer duty</div><div id="simple" class="form"></div>
<p class="note" id="prodNote"></p>
<div class="btns"><button id="xlsx">Download Excel (full details)</button><button class="alt" id="print">Print customer sheet</button>
<button class="alt" id="save">Save sizing record</button></div><div id="saveMsg" class="note"></div></section>
<section class="panel" id="p-out"><div class="bar">Results</div><div id="results"></div></section>
</div>
<details id="d-sheet"><summary>Customer sheet (mass and energy balance)</summary>
<div id="sheetWrap"><div id="sheet"></div></div><p class="note">One landscape page. Print or save as PDF to send.</p></details>
<details id="d-adv"><summary>All inputs<span id="advCount"></span></summary>
<p class="note">Everything here starts at the workbook default (shown grey) and only needs changing for a special case.
Product and fuel set their own defaults. Changed values are marked; values outside the normal range are flagged.</p>
<div class="btns"><button class="alt" id="reset">Reset all inputs</button><button class="alt" id="download">Download record (JSON)</button></div>
<div id="inputs"></div></details>
<details id="d-calc"><summary>Calculation (every workbook line)</summary><div id="calc"></div></details>
</main>
<footer><span><b>MIDWEST CUSTOM ENGINEERING</b> <span class="tag">PRECISION. QUALITY. INTEGRITY.</span></span>
<span id="ver"></span></footer>
<script>__XLCALC__</script>
<script>var MODEL = __MODEL__;</script>
<script>__UI__</script>
</body>
</html>
"""


def build_html(path: str | Path = "rotary_dryer_calculator.html", request: dict | None = None) -> Path:
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        x = build_workbook(request or {}, Path(tmp) / "model.xlsx")
        model = export_model(x)
    logo = "data:image/png;base64," + base64.b64encode((ASSETS / "mce_logo_520.png").read_bytes()).decode()
    page = (PAGE.replace("__LOGO__", logo)
            .replace("__XLCALC__", (ASSETS / "xlcalc.js").read_text())
            .replace("__UI__", (ASSETS / "calculator_ui.js").read_text())
            .replace("__MODEL__", json.dumps(model, separators=(",", ":")).replace("</", "<\\/")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page)
    return path


def model_json(request: dict | None = None) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        return json.dumps(export_model(build_workbook(request or {}, Path(tmp) / "m.xlsx")))


_ = html
