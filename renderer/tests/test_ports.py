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
import pathlib
import random
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from calculators import baghouse as bh, cooler as cl, hammermill as hm  # noqa: E402
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
        check("hm package total", r["total"], got["total"], c)
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


def main():
    counts = {"hammermill": test_hammermill(), "baghouse": test_baghouse(),
              "cooler": test_cooler()}
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
