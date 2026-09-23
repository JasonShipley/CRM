#!/usr/bin/env python3
"""Differential test: every Python calculator port vs MCE's original calculator.

The originals in renderer/tools/ are the engineering source of truth. The Python
ports in renderer/calculators/ are what the quote builder sizes and prices with.
This test runs the originals' own JavaScript headless (Node + a small DOM shim in
domshim.js), feeds both sides the same randomized inputs, and asserts they agree
— model selection, every displayed figure, and every price.

    cd renderer && python3 tests/test_ports.py

Run it after changing either side. Needs node on PATH; nothing else.
"""
import json
import math
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from calculators import (baghouse as bh, cooler as cl, cyclone as cy,  # noqa: E402
                         duct as dc, hammer_pattern as hp, hammermill as hm)
from calculators._data import CL_PELLETS, PRODUCTS  # noqa: E402

FAILS = []


def node(script, *args):
    r = subprocess.run(["node", script, *args], cwd=HERE,
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{script} failed:\n{r.stderr}")
    return json.loads(r.stdout)


def check(name, want, have, case=None):
    if isinstance(want, float) and isinstance(have, (int, float)):
        ok = abs(want - have) <= 0.02
    else:
        ok = want == have
    if not ok:
        FAILS.append(f"{name}: original={want!r} port={have!r}"
                     + (f"\n    case={case}" if case else ""))
    return ok


def out(result, label):
    return next((o["value"] for o in result["outputs"] if o["label"] == label), None)


def test_hammermill():
    random.seed(7)
    cases = [{"pph": 24000, "screen64": 8, "index": 40, "sqInHp": 15,
              "bulkDensity": 45, "runLength": 2}]
    for _ in range(120):
        p = random.choice(PRODUCTS)
        cases.append({
            "pph": random.choice([1200, 4000, 8000, 12000, 24000, 40000, 60000, 90000, 150000]),
            "screen64": random.choice([2, 3, 4, 6, 8, 12, 16, 24, 48]),
            "index": p["index"], "sqInHp": p["sqInHp"], "bulkDensity": p["bulkDensity"],
            "runLength": random.choice([0, 2, 5, 12]),
            "plenumVelocity": random.choice([200, 250, 300, 350, 400, 450]),
            "feederDia": random.choice([10, 14]),
            "cupType": random.choice(["nylon", "ss", "tt"]),
            "magnetClean": random.choice(["sma", "scmam", "scmaa"]),
            "family": random.choice(["grain", "render"]),
            "trough": random.choice(["45", "30a", "30b", "15"]),
        })
    ref = node("hm_ref.js", json.dumps(cases))
    for c, r in zip(cases, ref):
        got = hm.size(c)
        check("hm mill", r["mill"], got["mill"], c)
        check("hm screen area", r["millArea"], got["screen_area"], c)
        check("hm plenum CFM", round(r["cfm"]), got["plenum_cfm"], c)
        check("hm motor", f"{r['motorHp']:g} HP", out(got, "Motor size"), c)
        check("hm area required", f"{r['fAreaReq']} in²", out(got, "Screen area required"), c)
        check("hm headroom", f"{r['headroom']}%", out(got, "Screen-area headroom"), c)
        # compare the mill/feeder/plenum package the original prices; the port's
        # `total` also carries the vendor-quoted screw, which the original has no
        # concept of
        check("hm package total", r["total"], got["package_total"], c)
    return len(cases)


def test_baghouse():
    random.seed(11)
    cases = [{"mode": "cfm", "cfm": 3000, "ratio": 7, "lenFilter": "any"}]
    for _ in range(60):
        cases.append({
            "mode": random.choice(["cfm", "mill"]),
            "cfm": random.choice([800, 1500, 3000, 6300, 12000, 25000]),
            "screenArea": random.choice([312, 1160, 2400, 4720, 7080]),
            "ratio": random.choice([6.25, 7, 7.5, 5, 10]),
            "lenFilter": random.choice(["any", "4", "6", "8", "10"]),
        })
    ref = node("cl_bh_ref.js", "baghouse", json.dumps(cases))
    check("bh model count", ref["count"], len(bh.MCE_MODELS))
    for c, r in zip(cases, ref["results"]):
        got = bh.size(c)
        if got.get("error"):
            FAILS.append(f"bh port errored: {got['error']} case={c}")
            continue
        # the port rounds these for display; compare on the same footing
        check("bh cfm", round(r["cfm"]), got["cfm"], c)
        check("bh required area", round(r["reqArea"]), got["required_area"], c)
        check("bh model", r["mce"] or "Consult engineering", out(got, "MCE filter"), c)
        if r["mce"]:
            check("bh pulse", f'{r["mcePulse"]:.2f} SCFM', out(got, "Pulse air"), c)
            check("bh plan", f'{r["mcePlan"]}" × {r["mcePlan"]}"', out(got, "Plan"), c)
        if r["kice"]:
            check("bh kice", True,
                  str(out(got, "Kice equivalent")).startswith(r["kice"]), c)
    return len(cases)


def test_cooler():
    random.seed(11)
    pellets = [p for p in CL_PELLETS if not p.get("special")]
    cases = [{"tph": 20, "pellet": "p6", "density": 40, "margin": 0, "upsize": 0}]
    for _ in range(90):
        p = random.choice(pellets)
        cases.append({
            "tph": random.choice([2, 5, 10, 20, 35, 50, 80, 120]), "pellet": p["id"],
            "density": random.choice([30, 35, 40, 45, 55]),
            "margin": random.choice([0, 10, 20, 35]),
            "upsize": random.choice([0, 1, 2]),
            "mealHeight": random.choice(["std4", "mid5", "tall6"]),
        })
    ref = node("cl_bh_ref.js", "cooler", json.dumps(cases))
    # The load-time price build is the subtle part: model prices are struck from
    # the RAW option sheet, and only then is the option sheet escalated.
    for model, price in ref["modelPrices"].items():
        check(f"cl price {model}", price,
              next(m["price"] for m in cl.MODELS if m["model"] == model))
    for k, row in ref["opts"].items():
        for i, v in enumerate(row):
            check(f"cl OPTS[{k}][{i}]", v, cl.OPTS[k][i])
    for k, v in ref["adders"].items():
        check(f"cl ADDERS[{k}]", v, cl.ADDERS[k])

    for c, r in zip(cases, ref["results"]):
        got = cl.size(c)
        if got.get("error"):
            FAILS.append(f"cl port errored: {got['error']} case={c}")
            continue
        check("cl airflow", f'{r["fCfm"]} CFM', out(got, "Required airflow"), c)
        if r["meal"]:
            check("cl bed area", f'{r["fArea"]} ft²', out(got, "Required bed area"), c)
            if r["model"]:
                want = (f'{r["units"]} × ' if r["units"] > 1 else "") + f'CC {r["model"]}'
                check("cl meal model", want, out(got, "Cooler"), c)
        else:
            check("cl volume", f'{r["fVol"]} ft³', out(got, "Required volume"), c)
            if r["model"]:
                check("cl model", f'CC {r["model"]}', out(got, "Cooler"), c)
                check("cl bed depth", f'{r["fBed"]} ft', out(got, "Operating bed depth"), c)
                check("cl face velocity", f'{r["fVel"]} FPM', out(got, "Bed face velocity"), c)
                check("cl utilization", f'{r["fUtil"]}%', out(got, "Volume utilization"), c)
                if r["air"]:
                    check("cl air line", f'{r["air"]["d"]}" dia',
                          out(got, "Recommended air line"), c)
                    check("cl fan motor",
                          f'~{r["air"]["motor"]} HP (verify against the fan curve)',
                          out(got, "Est. fan motor"), c)
                    check("cl cyclone", f'HE-{r["air"]["cyc"]} class',
                          out(got, "Est. cyclone"), c)
    return len(cases)


def test_cyclone():
    """Drives the original's own compute() and diffs everything it renders:
    matched model, fit pill, the detail sentence and the overlap note."""
    random.seed(11)
    cases = [
        {"mode": "cfm", "cfm": 3200}, {"mode": "cfm", "cfm": 2510},
        {"mode": "cfm", "cfm": 12600}, {"mode": "cfm", "cfm": 12601},
        {"mode": "cfm", "cfm": 2000}, {"mode": "cfm", "cfm": 90000},
        {"mode": "cfm", "series": "budget", "cfm": 4600},
        {"mode": "cfm", "series": "budget", "cfm": 25000},
        {"mode": "measure", "inletId": 12}, {"mode": "measure", "inletId": 6},
        {"mode": "measure", "inletShape": "rect", "inletW": 10, "inletH": 18},
    ]
    for _ in range(90):
        mode = random.choice(["cfm", "cfm", "measure"])
        c = {"mode": mode, "series": random.choice(["mce", "mce", "budget"]),
             "wg": random.choice([2, 3, 4])}
        if mode == "cfm":
            c["cfm"] = random.choice([900, 2150, 2500, 2525, 6000, 9800, 12600,
                                      12700, 18000, 31000, 52000, 71605, 88000])
        else:
            c["fpm"] = random.choice([3000, 3500, 4000, 4500])
            if random.random() < 0.5:
                c["inletId"] = random.choice([4, 6, 8, 10, 12, 16, 20, 26, 33])
            else:
                c["inletShape"] = "rect"
                c["inletW"] = random.choice([6, 8, 10, 14, 20])
                c["inletH"] = random.choice([8, 12, 18, 24, 30])
        cases.append(c)

    ref = node("cy_hp_ref.js", "cyclone", json.dumps(cases))
    for c, r in zip(cases, ref):
        got = cy.size(c)
        if got.get("error"):
            FAILS.append(f"cy errored: {got['error']}\n    case={c}")
            continue
        check("cy rated cfm", r["ratedCfm"], f'{got["cfm"]:,}', c)
        check("cy match", r["matchSize"], got["matchSize"], c)
        check("cy pill", r["pill"], got["fit"], c)
        check("cy detail", r["detail"], got["detail"], c)
        check("cy alt note", r["altNote"], got["altNote"], c)
        # the original only renders the formula strip in measure mode
        if c["mode"] == "measure":
            check("cy formula", r["formula"], got["formula"], c)
    return len(cases)


def test_hammer_pattern():
    random.seed(13)
    cases = [
        {"motorHp": 200, "hpPerHammer": 1.5, "rows": 8, "pinLength": 40,
         "thickness": 0.25, "pinAllowance": 7.5},
        {"motorHp": 200, "hpPerHammer": 1.75, "rows": 8, "pinLength": 40,
         "thickness": 0.25, "pinAllowance": 7.5},
        {"motorHp": 300, "hpPerHammer": 1.5, "rows": 4, "pinLength": 40,
         "thickness": 0.25, "pinAllowance": 7.5},
        # an odd override, and one that cannot physically stack
        {"motorHp": 200, "hpPerHammer": 1.5, "rows": 8, "pinLength": 40,
         "thickness": 0.25, "pinAllowance": 7.5, "countOverride": 101},
        {"motorHp": 400, "hpPerHammer": 1.5, "rows": 4, "pinLength": 22,
         "thickness": 0.25, "pinAllowance": 7.5},
    ]
    for _ in range(75):
        c = {"motorHp": random.choice([30, 60, 75, 100, 150, 200, 250, 300, 400, 600]),
             "hpPerHammer": random.choice([1.5, 1.75, 1.2, 2.0, 2.5]),
             "rows": random.choice([4, 8]),
             "pinLength": random.choice([20, 28, 34, 40, 48]),
             "thickness": random.choice([0.25, 0.3125, 0.375, 0.5]),
             "pinAllowance": random.choice([0, 4, 7.5, 10])}
        if random.random() < 0.25:
            c["countOverride"] = random.choice([2, 33, 64, 101, 132, 180])
        cases.append(c)

    ref = node("cy_hp_ref.js", "hammer", json.dumps(cases))
    for c, r in zip(cases, ref):
        got = hp.size(c)
        if got.get("error"):
            FAILS.append(f"hp errored: {got['error']}\n    case={c}")
            continue
        check("hp count", r["count"], out(got, "Hammers"), c)
        check("hp pill", r["pill"], got["pill"], c)
        check("hp actual hp/hammer", r["actualHph"], got["actualHph"], c)
        check("hp capacity range", r["capacityRange"], got["capacityRange"], c)
        check("hp count note", r["countNote"], got["countNote"], c)
        check("hp dist detail", r["distDetail"], got["distDetail"], c)
        check("hp balance note", r["balanceNote"], got["balanceNote"], c)
        check("hp stack note", r["stackNote"], got["stackNote"], c)
        check("hp row split", r["perPair"], got["perPair"], c)
        # compare the port's own rendered strings, not a re-format here — the
        # point of the diff is that the two sides print the same thing
        check("hp stack hammers", r["stackHammers"],
              out(got, "Hammers / loaded pin (max)"), c)
        check("hp stack length", r["stackLength"], out(got, "Hammer + collar stack"), c)
        check("hp spacer length", r["spacerLength"], out(got, "Left for spacers"), c)
        check("hp spacer total", r["spacerTotal"],
              out(got, "Spacer fill (all loaded pins)"), c)
        check("hp bom", [list(x) for x in r["bom"]],
              [[b["item"], b["qty"]] for b in got["bom"]], c)
    return len(cases)


def test_duct():
    random.seed(17)
    cases = [{"mode": "dia", "cfm": 4602, "velocity": 4000},
             {"mode": "cfm", "diameter": 8, "velocity": 4000},
             # an exact even-inch hit, so the "Exact fit" branch is covered
             {"mode": "dia", "cfm": 4000 * (math.pi / 4) * 16 * 16 / 144, "velocity": 4000}]
    for _ in range(70):
        mode = random.choice(["cfm", "dia"])
        c = {"mode": mode, "velocity": random.choice([4000, 4500, 3500, 5000, 2750])}
        if mode == "cfm":
            c["diameter"] = random.choice([4, 6, 7.5, 8, 10, 12, 14, 17, 21, 26, 30])
        else:
            c["cfm"] = random.choice([400, 900, 1400, 2300, 4602, 6240, 11000, 22000])
        cases.append(c)

    ref = node("cy_hp_ref.js", "duct", json.dumps(cases))
    for c, r in zip(cases, ref):
        got = dc.size(c)
        if got.get("error"):
            FAILS.append(f"dc errored: {got['error']}\n    case={c}")
            continue
        check("dc formula", r["formula"], got["formula"], c)
        if c["mode"] == "cfm":
            check("dc min cfm", r["minCfm"], out(got, "Minimum airflow").replace(" CFM", ""), c)
        else:
            check("dc min dia", r["minDia"],
                  out(got, "Minimum diameter").rstrip('"'), c)
            check("dc recommended", r["recDia"], out(got, "Recommended duct").rstrip('"'), c)
            check("dc fit pill", r["pill"], out(got, "Fit"), c)
    return len(cases)


def main():
    counts = {"hammermill": test_hammermill(), "baghouse": test_baghouse(),
              "cooler": test_cooler(), "cyclone": test_cyclone(),
              "hammer pattern": test_hammer_pattern(), "duct": test_duct()}
    for name, n in counts.items():
        print(f"  {name}: {n} cases")
    if FAILS:
        print(f"\n{len(FAILS)} MISMATCH(ES) vs the original calculators:\n")
        for f in FAILS[:25]:
            print("  " + f)
        if len(FAILS) > 25:
            print(f"  ... and {len(FAILS) - 25} more")
        return 1
    print(f"\nOK — {sum(counts.values())} cases, ports match the originals exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
