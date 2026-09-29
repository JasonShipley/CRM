#!/usr/bin/env python3
"""Regenerate calculators/_xf_data.py out of MCE's XF fan calculator.

The LS capacity tables are 144 rows of transcribed catalog data that MCE keeps in
the calculator itself. Reading them out with the calculator's own JavaScript —
rather than retyping them — means the port and the hosted tool cannot hold
different catalogs. Run this after MCE revises the calculator:

    python3 tests/extract_xf_data.py
"""
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "calculators" / "_xf_data.py"
TOOL = HERE.parent / "tools" / "xf-fan-sizing-calculator.html"

NODE = """
const path = require("path");
const { runCalc } = require(process.argv[1]);
const { sandbox } = runCalc(process.argv[2], {},
    ["LS_DATA", "LS_MAX_SAFE_RPM_70F", "LS_SP_COLS", "NEMA_HP"]);
console.log(JSON.stringify(sandbox.__exports));
"""


def main():
    raw = subprocess.run(["node", "-e", NODE, "--", str(HERE / "domshim.js"), str(TOOL)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(raw)
    ls, mx, cols, nema = (d["LS_DATA"], d["LS_MAX_SAFE_RPM_70F"], d["LS_SP_COLS"],
                          d["NEMA_HP"])
    out = [
        "#!/usr/bin/env python3",
        '"""MCE XF / New York Blower LS series capacity tables — Bulletin 251.',
        "",
        "GENERATED from tools/xf-fan-sizing-calculator.html by tests/extract_xf_data.py.",
        "Do not hand-edit: MCE maintains the calculator, and this file is read out of",
        "it so the port and the hosted tool can never hold different catalogs.",
        "",
        "LS_DATA[size] = {inlet_od_in, wheel_dia_in, outlet_area_ft2, wheel_circ_ft,",
        '                 rows: [{cfm, ov, sp: {"2": (rpm, bhp), ...}}]}',
        "LS_MAX_SAFE_RPM_70F[size]  Chart III, mild steel, arrangements 1/9/9F at 70 °F.",
        '"""',
        f"LS_SP_COLS = {cols!r}",
        f"NEMA_HP = {nema!r}",
        f"LS_MAX_SAFE_RPM_70F = {mx!r}",
        "",
        "LS_DATA = {",
    ]
    for key, size in ls.items():
        out.append(f'    {key!r}: {{"inlet_od_in": {size["inlet_od_in"]!r}, '
                   f'"wheel_dia_in": {size["wheel_dia_in"]!r}, '
                   f'"outlet_area_ft2": {size["outlet_area_ft2"]!r}, '
                   f'"wheel_circ_ft": {size["wheel_circ_ft"]!r}, "rows": [')
        for row in size["rows"]:
            sp = ", ".join(f'"{c}": ({row["sp"][c]["rpm"]!r}, {row["sp"][c]["bhp"]!r})'
                           for c in map(str, cols) if c in row["sp"])
            out.append(f'        {{"cfm": {row["cfm"]!r}, "ov": {row["ov"]!r}, '
                       f'"sp": {{{sp}}}}},')
        out.append("    ]},")
    out.append("}")
    OUT.write_text("\n".join(out) + "\n")
    rows = sum(len(s["rows"]) for s in ls.values())
    print(f"{OUT.name}: {rows} capacity rows across {len(ls)} LS sizes")


if __name__ == "__main__":
    sys.exit(main())
