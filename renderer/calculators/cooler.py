#!/usr/bin/env python3
"""Counterflow cooler sizing — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/counterflow-cooler-sizing-calculator.html (served
whole at /tools/cooler). Model geometry, option pricing and the 2016/17 OEM price
basis are extracted verbatim into _data.py.

Two sizing paths, exactly as the original:
  pellets — volume-first:  required volume = (TPH x 2000 / 60) x retention / density
  meal    — airflow-first: required floor area = (TPH x CFM/ton) / face-velocity cap
"""
import math

from ._fmt import jsround, num
from ._data import (CL_ADDERS, CL_CHECK_DEFS, CL_DUCT_SIZES, CL_MODELS,
                    CL_OPTS, CL_PD_4500, CL_PELLETS, CL_SERIES)

PRICING_REV = "2026-07-22"
ESCALATION = 1 / 0.68          # 2016/17 OEM basis -> current MCE list
FAN_EFFICIENCY = 0.60          # radial-blade, planning level
DUCT_VELOCITY_MAX = 5700       # FPM ceiling when picking an air line
DUCT_VELOCITY_REF = 4500       # FPM the friction table is quoted at
FAN_MOTORS = [10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250, 300]
MEAL_HEIGHTS = [("std4", '-4 standard (30–40" bed)'),
                ("mid5", '-5 mid (50" capability, run part full)'),
                ("tall6", '-6 tall (60" capability, run half full)')]


def _list(n):
    return jsround(n * ESCALATION)


def _build():
    """Mirror the original's load-time work, in its original order.

    Order matters: model prices are struck from the RAW option sheet, and only
    afterwards is the option sheet itself escalated to current list. Escalating
    first would inflate every base price.
    """
    models = []
    for row in CL_MODELS:
        model, cfm, tph, vol, wt, base2016 = row
        series = int(model.split("-")[0])
        geo = CL_SERIES[str(series)]
        o = CL_OPTS[str(series)]
        price = _list(base2016 + o[5] + o[4] + (o[6] if series >= 9 and o[6] else 0)
                      + 680 + 397 + 1512)
        models.append({"model": model, "cfm": cfm, "tph": tph, "vol": vol, "wt": wt,
                       "base2016": base2016, "price": price, "series": series,
                       "dia": geo["dia"], "area": geo["area"],
                       "legs": '4"' if series <= 9 else '6"'})
    opts = {k: [None if v is None else _list(v) for v in row]
            for k, row in CL_OPTS.items()}
    adders = dict(CL_ADDERS)
    for k in ("xpAir", "xpElec", "sensor", "xpLight", "microSwitch", "inspWindow",
              "vibrators"):
        adders[k] = _list(adders[k])
    return models, opts, adders


MODELS, OPTS, ADDERS = _build()
PELLET_BY_ID = {p["id"]: p for p in CL_PELLETS}


def _interp_pd(dia):
    t = CL_PD_4500
    if dia <= t[0][0]:
        return t[0][1]
    if dia >= t[-1][0]:
        return t[-1][1]
    for (d1, p1), (d2, p2) in zip(t, t[1:]):
        if d1 <= dia <= d2:
            return p1 + (p2 - p1) * (dia - d1) / (d2 - d1)
    return t[-1][1]


def _air(req_cfm, cooler_static, fan_static, fan_est):
    if not req_cfm or req_cfm <= 0:
        return []
    pick = None
    for d in CL_DUCT_SIZES:
        area = math.pi / 4 * (d / 12.0) ** 2
        v = req_cfm / area
        if v <= DUCT_VELOCITY_MAX:
            pick = (d, v)
            break
    if not pick:
        return [{"label": "Air line", "value": '> 48" — split runs'}]
    d, v = pick
    pd = _interp_pd(d) * (v / DUCT_VELOCITY_REF) ** 2
    bhp = req_cfm * fan_static / (6356 * FAN_EFFICIENCY)
    motor = next((h for h in FAN_MOTORS if h >= bhp), math.ceil(bhp))
    cyclone = 2 * math.ceil(math.sqrt(req_cfm / 5.45) / 2)
    return [
        {"label": "System design airflow", "value": f"{num(req_cfm)} CFM"},
        {"label": "Recommended air line", "value": f'{d}" dia'},
        {"label": "Line velocity",
         "value": f"{num(v)} FPM" + (" — below 4,500" if v < DUCT_VELOCITY_REF else "")},
        {"label": "Est. friction loss", "value": f'{num(pd, 2)}" WC / 100 ft'},
        {"label": "Cooler exhaust static", "value": f'{cooler_static}" WC'},
        {"label": "Fan system static" + (" (est.)" if fan_est else ""),
         "value": f'{fan_static}" WCI w/ cyclone'},
        {"label": "Est. fan motor", "value": f"~{motor} HP (verify against the fan curve)"},
        {"label": "Est. cyclone", "value": f"HE-{cyclone} class"},
    ]


def _checkbox_defaults(series, opts):
    state = {}
    for c in CL_CHECK_DEFS:
        std = bool(c.get("std")) or (c["id"] == "leveler" and series is not None
                                     and series >= 9 and opts and opts[6] is not None)
        state[c["id"]] = std
    return state


def _quote(best, units, form, opts):
    """Port of the original quote(): priced lines for the selected cooler."""
    lines = []
    series = best["series"]
    checks = _checkbox_defaults(series, opts)
    supplied = form.get("options")
    if isinstance(supplied, dict):
        for k, v in supplied.items():
            if k in checks:
                checks[k] = bool(v)

    lines.append({"label": f"CC {best['model']} cooler w/ standard equipment",
                  "amount": best["price"]})

    f_acts = 2 if series >= 13 else 1
    pellet = PELLET_BY_ID.get(form.get("pellet") or "p6", {})
    if f_acts == 2:
        act_label = "Linear-actuator floor (2×) & exhaust damper"
    elif pellet.get("meal"):
        act_label = "Linear-actuator floor (1×, verify double drive) & exhaust damper"
    else:
        act_label = "Linear-actuator floor & exhaust damper"
    lines.append({"label": act_label, "amount": 0, "included": True})

    for c in CL_CHECK_DEFS:
        is_std = bool(c.get("std")) or (c["id"] == "leveler" and series >= 9)
        not_rec = c["id"] == "leveler" and opts[6] is None
        if not_rec:
            continue
        val = ADDERS[c["fix"]] if c.get("fix") else opts[c["idx"]]
        if val is None:
            continue
        label = c["label"]
        if c["id"] == "rotFeeder":
            label += f" (RF 14×{12 if series <= 9 else 18})"
        if is_std:
            if checks[c["id"]]:
                lines.append({"label": label, "amount": 0, "included": True})
            else:
                lines.append({"label": "Deduct: " + label, "amount": -val})
        elif checks[c["id"]]:
            lines.append({"label": label, "amount": val})

    xp = form.get("xp") or "none"
    if xp == "air":
        lines.append({"label": "XP electrics (feeder, floor & sensors) — air floor",
                      "amount": ADDERS["xpAir"]})
    if xp == "elec":
        lines.append({"label": "XP electrics (feeder, floor & sensors) — electric floor",
                      "amount": ADDERS["xpElec"]})

    # Per-cooler items scale with the unit count; sensors stay a user count.
    if units > 1:
        for ln in lines:
            ln["label"] = f"{units} × {ln['label']}"
            ln["amount"] *= units

    try:
        sensors = max(int(float(form.get("sensors") or 0)), 0)
    except (TypeError, ValueError):
        sensors = 0
    if sensors > 0:
        lines.append({"label": f"Extra rotary level sensors × {sensors}",
                      "amount": ADDERS["sensor"] * sensors})

    if (form.get("panel") or "mce") == "mce":
        prefix = f"{units} × " if units > 1 else ""
        lines.append({"label": prefix + "MCE Cooler Control System",
                      "amount": ADDERS["mcePanel"] * units})

    return lines, sum(ln["amount"] for ln in lines), checks


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def size(f):
    pellet = PELLET_BY_ID.get(f.get("pellet") or "p6")
    if not pellet:
        return {"error": f"Unknown product: {f.get('pellet')}"}
    tph = max(_num(f.get("tph"), 0), 0)
    if tph <= 0:
        return {"error": "Production rate (TPH) is required."}
    if pellet.get("special"):
        return {"error": f"{pellet['label'].replace(' *', '')} needs factory sizing — "
                         "no standard CFM/ton constant. Send it to engineering."}
    density = max(_num(f.get("density"), pellet.get("dens") or 40), 1)
    margin = 1 + max(_num(f.get("margin"), 0), 0) / 100
    try:
        upsize = max(int(float(f.get("upsize") or 0)), 0)
    except (TypeError, ValueError):
        upsize = 0

    if pellet.get("meal"):
        return _meal(f, pellet, tph, density, margin, upsize)
    return _pellet(f, pellet, tph, density, margin, upsize)


def _pellet(f, p, tph, density, margin, upsize):
    warnings, outputs = [], []
    req_cfm = tph * p["cfmTon"] * margin
    req_vol = (tph * 2000 / 60) * p["ret"] / density * margin
    req_tph = tph * margin

    hits = sorted((m for m in MODELS
                   if m["vol"] >= req_vol and m["cfm"] >= req_cfm and m["tph"] >= req_tph),
                  key=lambda m: (m["vol"], m["price"]))
    formula = (f"{tph:g} TPH × {p['cfmTon']:,} CFM/ton × {margin:.2f} = {num(req_cfm)} CFM · "
               f"volume ({tph:g} × 2000 ÷ 60) × {p['ret']} min ÷ {density:g} lb/ft³ × "
               f"{margin:.2f} = {num(req_vol)} ft³")

    if not hits:
        half = sorted((m for m in MODELS if m["vol"] >= req_vol / 2
                       and m["cfm"] >= req_cfm / 2 and m["tph"] >= req_tph / 2),
                      key=lambda m: (m["vol"], m["price"]))
        msg = (f"{num(req_tph, 1)} TPH exceeds the largest single cooler "
               f"(CC 21-880-6, 105.6 TPH basis).")
        if half:
            msg += f" Two coolers at {num(req_tph / 2, 1)} TPH each → 2 × CC {half[0]['model']}."
        warnings.append(msg + " Confirm with engineering.")
        return {"calculator": "Counterflow Cooler", "outputs": [
            {"label": "Required airflow", "value": f"{num(req_cfm)} CFM", "headline": True},
            {"label": "Required volume", "value": f"{num(req_vol)} ft³", "headline": True},
        ] + _air(req_cfm, p["wci"], p["wci"] + 8, True),
            "warnings": warnings, "lines": [], "total": 0.0, "formula": formula,
            "pricing_rev": PRICING_REV}

    best = hits[min(upsize, len(hits) - 1)]
    bed_depth = req_vol / best["area"]
    velocity = req_cfm / best["area"]
    util = req_vol / best["vol"] * 100
    if util > 97:
        warnings.append(f"Volume utilization is {num(util)}% — no headroom at this rate. "
                        "Consider the next size up.")
    if best["series"] >= 11:
        warnings.append(f"CC {best['model']} needs a split grid.")
    if best["series"] >= 13:
        warnings.append(f"CC {best['model']} needs a double grid floor with 2 actuators.")

    outputs = [
        {"label": "Required airflow", "value": f"{num(req_cfm)} CFM", "headline": True},
        {"label": "Required volume", "value": f"{num(req_vol)} ft³", "headline": True},
        {"label": "Retention", "value": f"{p['ret']} min"},
        {"label": "Cooler exhaust static", "value": f'{p["wci"]}" WC'},
        {"label": "Cooler", "value": f"CC {best['model']}", "headline": True},
        {"label": "Diameter", "value": f'{num(best["dia"], 1)}"'},
        {"label": "Floor area", "value": f'{num(best["area"], 2)} ft²'},
        {"label": "Chamber volume", "value": f'{best["vol"]:,} ft³'},
        {"label": "Volume utilization", "value": f"{num(util)}%"},
        {"label": "Operating bed depth", "value": f"{num(bed_depth, 1)} ft"},
        {"label": "Bed face velocity", "value": f"{num(velocity)} FPM"},
        {"label": "Rated capacity (basis)", "value": f'{num(best["tph"], 2)} TPH'},
        {"label": "Floor actuators",
         "value": "2 (double grid)" if best["series"] >= 13 else "1"},
        {"label": "Shipping weight", "value": f'{best["wt"]:,} lb'},
    ] + _air(req_cfm, p["wci"], p["wci"] + 8, True)

    return _finish(f, p, best, 1, outputs, warnings, formula, hits, req_cfm)


def _meal(f, p, tph, density, margin, upsize):
    warnings, outputs = [], []
    req_cfm = tph * p["cfmTon"] * margin
    req_area = req_cfm / p["faceMax"]
    hv = f.get("mealHeight") if f.get("mealHeight") in ("std4", "mid5", "tall6") else "std4"
    suffix = {"std4": "-4", "mid5": "-5", "tall6": "-6"}[hv]
    formula = (f"{tph:g} TPH × {p['cfmTon']:,} CFM/ton × {margin:.2f} = {num(req_cfm)} CFM ÷ "
               f"{p['faceMax']} CFM/ft² face cap = {num(req_area)} ft² bed area")

    units, best = 1, None
    while units <= 4 and not best:
        per = req_area / units
        cands = sorted((m for m in MODELS
                        if m["area"] >= per and m["model"].endswith(suffix)),
                       key=lambda m: (m["area"], m["price"]))
        if cands:
            best = cands[min(upsize, len(cands) - 1)]
            break
        units += 1

    if not best:
        warnings.append(
            f"Required bed area {num(req_area)} ft² exceeds four CC 21{suffix} coolers "
            f"(largest {suffix} height). Confirm with engineering.")
        return {"calculator": "Counterflow Cooler (meal)",
                "req_cfm": round(req_cfm), "outputs": [
            {"label": "Required airflow", "value": f"{num(req_cfm)} CFM", "headline": True},
            {"label": "Required bed area", "value": f"{num(req_area)} ft²", "headline": True},
        ], "warnings": warnings, "lines": [], "total": 0.0, "formula": formula,
            "pricing_rev": PRICING_REV}

    tot_area = best["area"] * units
    face = req_cfm / tot_area
    act_ret = (tot_area * p["bedFt"] * density) / (tph * 2000 / 60)
    warnings.append(
        f"Meal cooler — airflow governs: {p['cfmTon']:,} CFM/ton at a {p['faceMax']} "
        "CFM/ft² bed face cap. Historical Bliss quotes carried margin above this rule; "
        "add design margin to match that practice. Meal coolers may need double drives — "
        "confirm final airflow with engineering.")
    if best["series"] >= 11:
        warnings.append(f"CC {best['model']} needs a split grid.")

    outputs = [
        {"label": "Required airflow", "value": f"{num(req_cfm)} CFM", "headline": True},
        {"label": "Required bed area", "value": f"{num(req_area)} ft²", "headline": True},
        {"label": "Cooler",
         "value": (f"{units} × " if units > 1 else "") + f"CC {best['model']}",
         "headline": True},
        {"label": "Floor area", "value": f'{num(best["area"], 2)} ft² ea'
                                        + (f" ({num(tot_area, 1)} total)" if units > 1 else "")},
        {"label": "Bed face velocity",
         "value": f"{num(face)} CFM/ft² (cap {p['faceMax']})"},
        {"label": "Airflow basis", "value": f'{p["cfmTon"]:,} CFM/ton'},
        {"label": "Operating bed depth",
         "value": {"tall6": '30" (of 60" capability — half full)',
                   "mid5": '30" (of 50" capability)', "std4": '30–40"'}[hv]},
        {"label": "Retention @ 30\" bed",
         "value": f'≈{num(act_ret)} min (spec {p.get("retLabel", p["ret"])})'},
        {"label": "Floor actuators",
         "value": ("2 (double grid)" if best["series"] >= 13
                   else "1–2 (verify double drive)") + (" per cooler" if units > 1 else "")},
        {"label": "Shipping weight", "value": f'{best["wt"]:,} lb ea'},
    ] + _air(req_cfm, 12, 25 if req_cfm > 10000 else 20, False)

    return _finish(f, p, best, units, outputs, warnings, formula, None, req_cfm)


def _finish(f, p, best, units, outputs, warnings, formula, hits, req_cfm=0.0):
    opts = OPTS[str(best["series"])]
    quote_lines, total, checks = _quote(best, units, f, opts)

    spec = [ln["label"] for ln in quote_lines if ln.get("included")]
    desc = [
        f'CC {best["model"]} counterflow cooler — {num(best["dia"], 1)}" dia, '
        f'{num(best["area"], 2)} ft² floor, {best["vol"]:,} ft³ chamber',
        f'Rated {num(best["tph"], 2)} TPH basis, {best["cfm"]:,} CFM, {best["wt"]:,} lb',
        f'Product: {p["label"].replace(" *", "")}',
    ] + [f"Includes: {s}" for s in spec]

    lines = [{
        "name": (f"{units} × " if units > 1 else "") + f"CC {best['model']} Counterflow Cooler",
        "quantity": 1, "unitPrice": round(total, 2), "sku": f"CC {best['model']}",
        "description": "\n".join(desc + [
            f"Package price at MCE list rev {PRICING_REV}",
        ])}]

    alts = []
    if hits:
        for m in hits[:4]:
            alts.append({"model": f"CC {m['model']}", "cfm": m["cfm"], "tph": m["tph"],
                         "vol": m["vol"], "price": m["price"]})

    return {"calculator": "Counterflow Cooler", "outputs": outputs, "warnings": warnings,
            "lines": lines, "total": round(total, 2), "formula": formula,
            "quote_lines": quote_lines, "checks": checks, "alternates": alts,
            # what every downstream air item sizes off, so callers do not have to
            # scrape it back out of the display outputs
            "req_cfm": round(req_cfm), "pricing_rev": PRICING_REV,
            "model": best["model"], "units": units}
