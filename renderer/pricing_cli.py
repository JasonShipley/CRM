#!/usr/bin/env python3
"""Move a price once; update the calculator, the price book and the CRM.

    python3 pricing_cli.py check                     what disagrees with the basis
    python3 pricing_cli.py apply plenum_rate --pct 6 --source "steel, Oct 2026"
    python3 pricing_cli.py sync-tools                write factors into the tools
    python3 pricing_cli.py book out.xlsx             regenerate the price book

`apply` edits calculators/_pricing.py in place: it moves the factor and appends to
the escalation log, so the next reader sees what moved, by how much and who said
so. Then sync-tools and book push it outward. Nothing else holds a copy.
"""
import argparse
import datetime
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from calculators import _pricing, _vendor  # noqa: E402
from calculators._book_inputs import MILL_OPTIONS  # noqa: E402
from calculators._data import FEEDER_PRICING, MCE_XM_MILLS, MILL_PRICING  # noqa: E402

TOOL = HERE / "tools" / "hammermill-sizing-calculator.html"
BASIS = HERE / "calculators" / "_pricing.py"
TOOL_FIELDS = {"mill-mult": "mill", "feeder-mult": "feeder",
               "plenum-duty": "plenum_duty", "plenum-rate": "plenum_rate"}


def tool_values():
    """What the served calculator currently defaults to."""
    html = TOOL.read_text()
    out = {}
    for field, scope in TOOL_FIELDS.items():
        m = re.search(rf'id="{field}"[^>]*?value="([\d.]+)"', html)
        if m:
            out[scope] = float(m.group(1))
    return out


def cmd_check(_args):
    bad = 0
    print("factors")
    for scope, f in _pricing.FACTORS.items():
        print(f"  {scope:<14} {f['value']:<8g} {f['unit']}")
    print("\ncalculator defaults vs the basis")
    for scope, value in tool_values().items():
        live = _pricing.factor(scope)
        flag = "ok" if abs(value - live) < 1e-9 else "DRIFTED"
        if flag != "ok":
            bad += 1
        print(f"  {scope:<14} tool {value:<8g} basis {live:<8g} {flag}")
    print("\nthe price book as received vs what the basis would generate")
    for scope, d in _pricing.KNOWN_DIVERGENCE.items():
        print(f"  {scope:<14} book implies {d['book_implies']}, basis says {d['basis']}")
        print(f"                 {d['evidence']}")
    print("\nnot priced from anything yet")
    for scope, gap in _pricing.UNPRICED.items():
        print(f"  {scope}\n      needs: {gap['needs']}\n      one edit: {gap['one_edit']}")
    return 1 if bad else 0


def cmd_apply(args):
    new, entry = _pricing.apply_increase(
        args.scope, pct=args.pct, to=args.to, effective=args.effective,
        source=args.source)
    src = BASIS.read_text()
    old_line = re.search(rf'"{args.scope}": {{\n        "value": [\d.]+,', src)
    if not old_line:
        sys.exit(f"could not find the {args.scope} factor to edit")
    src = src.replace(old_line.group(0),
                      old_line.group(0).replace(
                          re.search(r'"value": ([\d.]+),', old_line.group(0)).group(0),
                          f'"value": {new:g},'))
    # the factor's provenance follows the move
    src = re.sub(rf'("{args.scope}": {{\n        "value": {new:g},[^}}]*?"since": ")[\d-]+(")',
                 rf'\g<1>{entry["effective"]}\g<2>', src, count=1)
    src = src.replace(
        "ESCALATIONS = [",
        "ESCALATIONS = [\n    " + repr(entry) + ",", 1)
    BASIS.write_text(src)
    print(f'{args.scope}: {entry["from"]:g} → {entry["to"]:g} '
          f'({entry["effective"]}, {entry["source"]})')
    print("now run:  pricing_cli.py sync-tools  and  pricing_cli.py book <out.xlsx>")
    return 0


def cmd_sync_tools(_args):
    html = TOOL.read_text()
    changed = []
    for field, scope in TOOL_FIELDS.items():
        live = _pricing.factor(scope)
        pattern = rf'(id="{field}"[^>]*?value=")([\d.]+)(")'
        m = re.search(pattern, html)
        if m and abs(float(m.group(2)) - live) > 1e-9:
            html = re.sub(pattern, rf"\g<1>{live:g}\g<3>", html, count=1)
            changed.append(f"{field} {m.group(2)} → {live:g}")
    if changed:
        TOOL.write_text(html)
        print("\n".join("  " + c for c in changed))
        print("re-run tests/extract_data.py, then the differential test.")
    else:
        print("  calculator already matches the basis")
    return 0


def cmd_book(args):
    """Regenerate the price book from the basis."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    stamp = datetime.date.today().isoformat()
    ws.append([f"MCE Hammermill Prices — generated from the pricing basis {stamp}"])
    ws.append([f"{_pricing.BLISS_BASIS} × the escalation factors in "
               "calculators/_pricing.py — do not hand-edit, regenerate"])
    for scope, f in _pricing.FACTORS.items():
        ws.append([scope, f["value"], f["unit"], f["source"], f["since"]])
    ws.append([])

    families = [(19, "XM-19"), (22, "XM-22"), (38, "XM-38"), (44, "XM-44")]
    options = [("Base Price", "base"), ("Sanitary Design", "sanitary"),
               ("AR Internal Wear Plates", "ar_plates"),
               ("Rubber Vibration Pads", "vibration_pads"),
               ("Drop Down Air Pan", "air_pan"), ("Manual Clean", "magnet_manual"),
               ("Auto Self Clean", "magnet_auto"), ("Rock Trap", "rock_trap"),
               ("SF300 Magnet", "sf300_magnet")]
    for _size, prefix in families:
        models = [m["model"] for m in MCE_XM_MILLS if m["model"].startswith(prefix)]
        if not models:
            continue
        ws.append([f'XM {_size}" Hammermill'])
        ws.append(["Hammer Pins"] + models)
        ws.append(["HP Range"] + [f'{m["hpMin"]}-{m["hpMax"]}HP'
                                  for m in MCE_XM_MILLS if m["model"] in models])
        ws.append(["Screen Size"] + [m["screenSize"] for m in MCE_XM_MILLS
                                     if m["model"] in models])
        ws.append(["Sq. In. Screen Area"] + [m["area"] for m in MCE_XM_MILLS
                                             if m["model"] in models])
        for label, key in options:
            if key == "base":
                row = [_pricing.mill_price(m) for m in models]
            else:
                row = [_pricing.mill_option(m, key) for m in models]
            ws.append([label] + row)
        ws.append([])

    for dia in (10, 14):
        for cup, name in (("nylon", "NYLON CUP"), ("ss", "STAINLESS ROUND CUP"),
                          ("tt", "TIGHT TOLERANCE STAINLESS ROUND CUP")):
            ws.append([f'{dia}" DIA. {name} ROTARY FEEDER'])
            rows = FEEDER_PRICING["rows"]
            ws.append(["Designation"]
                      + [_vendor.feeder_designation(cup, r) for r in rows])
            ws.append(["Screen width"]
                      + [_vendor.FEEDER_ROW_WIDTHS.get(r, "") for r in rows])
            ws.append(["Price"] + [_pricing.feeder_price(dia, cup, r) for r in rows])
            for clean, label in (("sma", "Manual Clean"), ("scmam", "Manual Self Clean"),
                                 ("scmaa", "Auto Self Clean")):
                ws.append([label] + [
                    (_pricing.feeder_price(dia, cup, r, clean) or 0)
                    - (_pricing.feeder_price(dia, cup, r) or 0) for r in rows])
            ws.append([])

    out = pathlib.Path(args.out)
    wb.save(out)
    print(f"wrote {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    a = sub.add_parser("apply")
    a.add_argument("scope", choices=sorted(_pricing.FACTORS))
    a.add_argument("--pct", type=float)
    a.add_argument("--to", type=float)
    a.add_argument("--effective")
    a.add_argument("--source", required=True)
    sub.add_parser("sync-tools")
    b = sub.add_parser("book")
    b.add_argument("out")
    args = ap.parse_args()
    return {"check": cmd_check, "apply": cmd_apply, "sync-tools": cmd_sync_tools,
            "book": cmd_book}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
