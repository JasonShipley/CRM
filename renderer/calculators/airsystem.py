#!/usr/bin/env python3
"""Air system — the one calculator that drives the others.

Everything downstream of a mill or a cooler sizes off a single airflow. Given that
one number, the filter, the fan, the airlock and the duct all follow, and the
question "size me a fan, baghouse and airlock for this mill" has one answer rather
than four separate lookups.

This module owns that chain. It does not re-derive anything — it calls the same
ports the standalone calculators use, so a filter sized here and a filter sized on
/tools/baghouse are the same filter.

    airflow, from whichever basis the caller has:
      cfm        a figure already in hand
      mill       mill screen area x 1.3      (x1.25 as well on an air-swept pan)
      millModel  an XM model -> its screen area -> as above
      cooler     a cooler's own airflow requirement

    then the air cleaner, one of three:
      baghouse         CFM / air-to-cloth -> MCE filter -> its matched AirPro fan
      filter_receiver  the same filter with a hopper under it, so it collects and
                       discharges rather than sitting on the mill plenum
      cyclone          CFM -> HE or H series (no filter, so the fan ducts to atmosphere)

    and then:
      airlock    the standard drop-through under the hopper
      duct       CFM / conveying velocity -> next even inch

Say the dust is combustible and the chain adds what NFPA asks for and prices what
it honestly can: isolation as a certified rotary valve with a real price range, and
deflagration venting as an unpriced option with the burst switches separated out
(calculators/nfpa.py). It sizes neither — the vent area comes from a dust hazard
analysis, not from here.
"""
from . import _vendor, baghouse, cooler, cyclone, duct, nfpa
from ._data import MCE_XM_MILLS

AIR_SWEPT_FACTOR = 1.25            # a drop-down pan is sized on 1.25 x screen area
DEFAULT_RATIO = 7                  # MCE's air-to-cloth standard
DEFAULT_WG = "3"
CLEANERS = [("baghouse", "Baghouse filter — fan discharges to atmosphere after it"),
            ("filter_receiver", "Filter receiver — the same filter with a hopper"),
            ("cyclone", "Cyclone — no filter, fan ducts to atmosphere")]
CLEANER_KEYS = [k for k, _ in CLEANERS]
CLEANER_LABELS = {"baghouse": "Baghouse filter",
                  "filter_receiver": "Filter receiver (hopper-bottom)",
                  "cyclone": "Cyclone"}
TRUE = ("1", "true", "yes", "on", "y")


def _flag(raw):
    return str(raw or "").strip().lower() in TRUE


def _cleaner(raw):
    """What the rep picked, however they spelled it. Defaults to a baghouse."""
    want = str(raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    if want in CLEANER_KEYS:
        return want
    if "receiver" in want:
        return "filter_receiver"
    if "cyclone" in want:
        return "cyclone"
    return "baghouse"


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def mill_area(model):
    """Screen area for an XM model, or None if it is not one of MCE's."""
    want = str(model or "").strip().upper()
    if want and not want.startswith("XM-"):
        want = "XM-" + want.lstrip("XM").lstrip("-")
    row = next((m for m in MCE_XM_MILLS if m["model"].upper() == want), None)
    return row["area"] if row else None


def airflow(f):
    """(cfm, formula, notes) for whichever basis the caller supplied.

    Returns cfm None when the basis is not there — the caller says what is missing,
    since only it knows what the rep actually typed.
    """
    mode = str(f.get("mode") or "cfm")
    air_swept = str(f.get("airSwept") or "").lower() in ("1", "true", "yes", "on")
    swept = AIR_SWEPT_FACTOR if air_swept else 1.0
    swept_note = (f" × {AIR_SWEPT_FACTOR:g} (air-swept drop-down pan)"
                  if air_swept else "")

    if mode == "cfm":
        cfm = _num(f.get("cfm"))
        return (cfm or None), f"{cfm:,.0f} CFM as given", []

    if mode == "cooler":
        res = cooler.size(f)
        if res.get("error"):
            return None, "", [res["error"]]
        cfm = res.get("req_cfm")
        return cfm, (f"{cfm:,.0f} CFM cooler airflow requirement" if cfm else ""), []

    # both mill modes end at screen area x 1.3
    if mode == "millModel":
        area = mill_area(f.get("millModel"))
        if not area:
            return None, "", [f'{f.get("millModel")!r} is not one of MCE\'s XM mills.']
        basis = f'{f.get("millModel")} at {area:,} in² screen'
    else:
        area = _num(f.get("screenArea"))
        if area <= 0:
            return None, "", ["A mill screen area is required."]
        basis = f"{area:,.0f} in² mill screen"

    cfm = area * swept * baghouse.MILL_CFM_PER_IN2
    return cfm, (f"{basis}{swept_note} × {baghouse.MILL_CFM_PER_IN2} CFM/in² "
                 f"= {cfm:,.0f} CFM"), []


def size(f):
    cfm, formula, problems = airflow(f)
    if problems:
        return {"error": " ".join(problems)}
    if not cfm or cfm <= 0:
        return {"error": "An airflow is required — give a CFM, a mill or a cooler."}

    cleaner = _cleaner(f.get("cleaner"))
    combustible = _flag(f.get("combustible"))
    indoors = (None if str(f.get("indoors") or "") == ""
               else _flag(f.get("indoors")))
    ratio = _num(f.get("ratio"), DEFAULT_RATIO) or DEFAULT_RATIO
    velocity = _num(f.get("velocity"), duct.DEFAULT_VELOCITY) or duct.DEFAULT_VELOCITY
    want = {k for k in ("cleaner", "fan", "airlock", "duct")
            if str(f.get("include_" + k, "1")).lower() not in ("0", "false", "no", "")}

    outputs = [{"label": "System airflow", "value": f"{cfm:,.0f} CFM", "headline": True},
               {"label": "Air cleaning", "value": CLEANER_LABELS[cleaner]}]
    warnings, lines, sizing, options = [], [], [], []
    total = 0.0
    vessel = None

    # --- the air cleaner, and with a filter its matched fan ---------------------
    fan_from_filter = False
    if "cleaner" in want:
        if cleaner in ("baghouse", "filter_receiver"):
            res = baghouse.size({"mode": "cfm", "cfm": cfm, "ratio": ratio,
                                 "lenFilter": f.get("lenFilter") or "any",
                                 "style": "receiver" if cleaner == "filter_receiver"
                                          else "plenum"})
            fan_from_filter = "fan" in want
        else:
            res = cyclone.size({"mode": "cfm", "cfm": cfm,
                                "series": f.get("series") or "mce",
                                "wg": f.get("wg") or DEFAULT_WG})
        if res.get("error"):
            return {"error": res["error"]}
        sizing.append(res)
        warnings += res.get("warnings", [])
        for line in res["lines"]:
            # the baghouse port bundles its matched fan; drop it if the fan was
            # not asked for, rather than sizing a fan nobody wanted
            if line["name"].startswith("Fan") and not fan_from_filter:
                continue
            lines.append(line)
            total += line["unitPrice"]
        for o in res.get("outputs", []):
            if o["label"] in ("MCE filter", "Cyclone"):
                vessel = f'MCE {o["value"]} {res["calculator"].lower()}'
            if o["label"] not in ("System airflow",):
                outputs.append(o)

    # --- a fan with no filter in front of it -----------------------------------
    if "fan" in want and not fan_from_filter:
        warnings.append(
            "Fan not sized: MCE's fan selection comes with a filter model, and there is "
            "no standalone fan calculator yet. With a cyclone the fan has to be picked "
            "against the cyclone's pressure drop — take it to engineering, or add the "
            "fan calculator from Drive and this will size it.")
        lines.append({"name": "Fan — size and price TBD", "quantity": 1, "unitPrice": 0,
                      "needsPrice": True, "description": "\n".join([
                          f"Fan for {cfm:,.0f} CFM of mill or cooler air",
                          "No MCE fan calculator yet — engineering to select against the "
                          "actual system static",
                      ])})

    # --- airlock ---------------------------------------------------------------
    if "airlock" in want:
        al = _vendor.airlock()
        if al:
            number, price, date, brand, source, desc = al
            outputs.append({"label": "Airlock", "value": number})
            lines.append({"name": f"Rotary Airlock — {number}", "quantity": 1,
                          "unitPrice": round(price, 2), "sku": number,
                          "description": "\n".join([
                              desc, "Mounts under the dust filter or cyclone hopper",
                              "Budgetary price — firm on receipt of a current vendor quote"])})
            total += price
            warnings.append(
                f"Airlock priced as {brand} {number} from {source} ({date}) at MCE's "
                f"buy-out divisor {_vendor.BUYOUT_DIVISOR:g}. It is the standard mill-scale "
                "drop-through, not sized against this duty.")

    # --- duct ------------------------------------------------------------------
    if "duct" in want:
        res = duct.size({"mode": "dia", "cfm": cfm, "velocity": velocity})
        if not res.get("error"):
            sizing.append(res)
            outputs.append({"label": "Duct", "value": f'{res["diameter"]}" dia at '
                                                      f"{velocity:,.0f} FPM"})
            lines.append({
                "name": "Ductwork — priced upon request", "quantity": 1, "unitPrice": 0,
                "needsPrice": True, "description": "\n".join([
                    f'{res["diameter"]}" dia duct at {velocity:,.0f} FPM on {cfm:,.0f} CFM '
                    f'({res["minDiameter"]:.2f}" minimum, rounded up to the next even inch)',
                    "Straight run, elbows, transitions and supports to suit the layout",
                    "Priced upon request once the layout is determined"])})

    # --- combustible dust ------------------------------------------------------
    # Not priced into the scope: isolation goes out as a certified valve with a real
    # range, the vent and its switches as unpriced options. Both carry the basis, and
    # the warnings say what has to come back before anyone sends this.
    if combustible:
        airlock_line = next((l for l in lines if l["name"].startswith("Rotary Airlock")),
                            None)
        outputs.insert(1, {"label": "Dust classification", "value": "Combustible dust",
                           "note": "Protection per NFPA 652/654 and NFPA 68/69 — sized "
                                   "off the dust hazard analysis, not off this calculator"})
        _added, notes = nfpa.protection(
            options, quantity=1, material=f.get("material"), vessel=vessel,
            replacing=airlock_line["sku"] if airlock_line else None, indoors=indoors)
        warnings += notes

    return {"calculator": "Air System", "outputs": outputs, "warnings": warnings,
            "lines": lines, "options": options, "total": round(total, 2),
            "formula": formula, "cfm": round(cfm), "cleaner": cleaner,
            "combustible": combustible,
            "chain": [s["calculator"] for s in sizing]}
