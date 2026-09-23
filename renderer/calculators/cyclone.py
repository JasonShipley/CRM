#!/usr/bin/env python3
"""Cyclone sizing — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/cyclone-cfm-calculator.html (served whole at
/tools/cyclone). The three spec charts — MCE's HE and H lines and the primed-gray
budget line — are extracted verbatim into _data.py.

    CFM  = inlet ID area (in²) / 144 × inlet velocity (FPM)     [measure mode]
    MCE  = HE series up to 12,600 CFM, H series above, matched on rated CFM
    Budget = smallest barrel size whose single rated CFM covers the requirement

Prices come from _vendor.CYCLONE_QUOTES — the HE-30, HE-39 and HE-47 sold on the
NEMO Feed proposal and the H74 on the LETEK proposal. A size MCE has not sold is
interpolated from its published shipping weight, and the line says so internally.
"""
import math

from . import _vendor
from ._data import (CY_BUDGET_SPEC, CY_H_SPEC, CY_HE_MAX_CFM, CY_HE_SPEC,
                    CY_SERIES_NOTES)
from ._fmt import fixed, jsround, num

# Inlet velocities the original offers, with the note each carries.
FPM_PRESETS = [
    ("3000", "3,000 FPM — light dust, fine material"),
    ("3500", "3,500 FPM — general dust and grain fines"),
    ("4000", "4,000 FPM — heavier grain, meal, pellets fines"),
    ("4500", "4,500 FPM — coarse or abrasive material"),
]
WG_OPTIONS = [("2", '2" WG'), ("3", '3" WG'), ("4", '4" WG')]


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def inlet_area_sq_in(f):
    """Inlet ID area in in², or None when the dimensions are not yet entered."""
    if str(f.get("inletShape") or "round") == "round":
        d = _num(f.get("inletId"))
        return (math.pi / 4) * d * d if d > 0 else None
    w, h = _num(f.get("inletW")), _num(f.get("inletH"))
    return w * h if w > 0 and h > 0 else None


def match_budget(rated):
    """(row, flag) from the budget chart — flag is 'within' or 'above'."""
    row = next((r for r in CY_BUDGET_SPEC if r["cfm"] >= rated), None)
    return (row, "within") if row else (CY_BUDGET_SPEC[-1], "above")


def match_he(rated):
    """(row, flag) from the HE chart — 'within', 'below' (under the row's rated
    minimum) or 'above' (past the largest HE)."""
    row = next((r for r in CY_HE_SPEC if rated <= r["max"]), None)
    if not row:
        return CY_HE_SPEC[-1], "above"
    return row, ("below" if rated < row["min"] else "within")


def match_h(rated, wg):
    """(row, flag) from the H chart at the given static pressure."""
    key = "cfm" + str(wg)
    row = next((r for r in CY_H_SPEC if r[key] >= rated), None)
    return (row, "within") if row else (CY_H_SPEC[-1], "above")


def size(f):
    mode = "measure" if f.get("mode") == "measure" else "cfm"
    series = "budget" if f.get("series") == "budget" else "mce"
    wg = str(f.get("wg") or "3")
    if wg not in ("2", "3", "4"):
        wg = "3"

    warnings, outputs, lines = [], [], []
    alt_note = ""

    if mode == "measure":
        area = inlet_area_sq_in(f)
        if area is None:
            return {"error": "Inlet dimensions are required to compute CFM."}
        fpm = _num(f.get("fpm"), 3500)
        if fpm <= 0:
            return {"error": "Inlet velocity must be greater than zero."}
        sqft = area / 144
        rated = sqft * fpm
        formula = (f"Inlet ID area {fixed(area, 1)} in² ÷ 144 = {fixed(sqft, 2)} ft² × "
                   f"{num(fpm)} FPM = {num(jsround(rated))} CFM")
    else:
        rated = _num(f.get("cfm"))
        if rated <= 0:
            return {"error": "A CFM requirement is required."}
        formula = f"{num(jsround(rated))} CFM rated airflow"

    outputs.append({"label": "Rated airflow", "value": f"{num(jsround(rated))} CFM",
                    "headline": True})

    if series == "budget":
        row, flag = match_budget(rated)
        model = match_size = f'{row["size"]}"'
        outputs.append({"label": "Cyclone", "value": f'Budget {model}', "headline": True})
        if flag == "above":
            detail = (f'Exceeds the {model} (largest budget size) rating of '
                      f'{num(row["cfm"])} CFM — consider the MCE line or multiple units.')
            fit = "Above Max"
            warnings.append(detail)
        else:
            pct = jsround((row["cfm"] - rated) / row["cfm"] * 100)
            detail = (f'Rated {num(row["cfm"])} CFM at this barrel size · {pct}% headroom '
                      f'over your {num(jsround(rated))} CFM requirement')
            fit = "Tight fit" if pct < 5 else "Fits"
            if pct < 5:
                warnings.append(f"Only {pct}% headroom on the {model} barrel — step up "
                                "a size if the airflow may grow.")
        outputs += [
            {"label": "Fit", "value": fit},
            {"label": "Rated CFM", "value": f'{num(row["cfm"])} CFM'},
            {"label": "Barrel dia × height", "value": f'{row["A"]}" × {row["B"]}"'},
            {"label": "Cone height", "value": f'{row["C"]}"'},
            {"label": "Inlet / air outlet / cone outlet",
             "value": f'{row["D"]}" / {row["E"]}" / {row["F"]}"'},
            {"label": "Overall height", "value": f'{row["G"]}"'},
            {"label": "Rain hood", "value": f'{row["H"]}"'},
            {"label": "Weight (12 Ga – 1/4\")",
             "value": f'{num(row["w12"])}–{num(row["w25"])} lb'},
        ]
        price, price_basis = _vendor.cyclone_price(f'Budget {model}', row["w10"])
        lines.append({
            "name": f'Cyclone — Budget {model}', "quantity": 1,
            "unitPrice": round(price, 2) if price else 0,
            "needsPrice": not price, "description": "\n".join([
                f'{row["A"]}" dia barrel × {row["B"]}" straight side, {row["C"]}" cone, '
                f'{row["G"]}" overall height',
                f'{row["D"]}" inlet, {row["E"]}" air outlet, {row["F"]}" cone outlet, '
                f'{row["H"]}" rain hood',
                f'Rated {num(row["cfm"])} CFM · {detail}',
                "Three-piece construction, primed gray",
                f'Shipping weight {num(row["w12"])} lb (12 Ga) to {num(row["w25"])} lb (1/4")',
            ])})
        note = CY_SERIES_NOTES["budget"]
    elif rated > CY_HE_MAX_CFM:
        row, flag = match_h(rated, wg)
        key = "cfm" + wg
        match_size = row["series"]
        outputs.append({"label": "Cyclone", "value": row["series"], "headline": True})
        if flag == "above":
            detail = (f'Exceeds {row["series"]} (largest H size) at {wg}" WG — consider '
                      "multiple units.")
            fit = "Above Max"
            warnings.append(detail)
        else:
            pct = jsround((row[key] - rated) / row[key] * 100)
            detail = (f'Rated {num(row[key])} CFM at {wg}" WG · {pct}% headroom over your '
                      f'{num(jsround(rated))} CFM requirement')
            fit = "Tight fit" if pct < 5 else "Fits"
            if pct < 5:
                warnings.append(f'Only {pct}% headroom on the {row["series"]} at {wg}" WG '
                                "— step up a size if the airflow may grow.")
        outputs += [
            {"label": "Fit", "value": fit},
            {"label": f'Rated CFM @ {wg}" WG', "value": f'{num(row[key])} CFM'},
            {"label": "Barrel diameter", "value": f'{row["d1"]["A"]}"'},
            {"label": "Overall height", "value": str(row["d1"]["B"])},
            {"label": "Weight", "value": f'~{num(row["weight"])} lb'},
        ]
        price, price_basis = _vendor.cyclone_price(row["series"], row["weight"])
        lines.append({
            "name": f'Cyclone — MCE {row["series"]}', "quantity": 1,
            "unitPrice": round(price, 2) if price else 0,
            "needsPrice": not price, "description": "\n".join([
                f'{row["d1"]["A"]}" dia barrel, {row["d1"]["B"]} overall height',
                f'Rated {num(row[key])} CFM at {wg}" WG · {detail}',
                f'{num(row["cfm2"])} / {num(row["cfm3"])} / {num(row["cfm4"])} CFM at '
                '2" / 3" / 4" WG',
                f'Shipping weight ~{num(row["weight"])} lb',
            ])})
        note = CY_SERIES_NOTES["mce"]
    else:
        row, flag = match_he(rated)
        d = row["d"]
        match_size = row["series"]
        outputs.append({"label": "Cyclone", "value": row["series"], "headline": True})
        if flag == "above":
            detail = (f'Exceeds {row["series"]} (largest HE series) maximum of '
                      f'{num(row["max"])} CFM — matching against the H range instead.')
            fit = "Above Max"
            warnings.append(detail)
        elif flag == "below":
            detail = (f'Below the minimum rated volume for {row["series"]} (smallest HE '
                      "series) — verify sizing.")
            fit = "Below Min"
            warnings.append(detail)
        else:
            dev = jsround(abs(rated - row["opt"]) / row["opt"] * 100)
            detail = (f'{num(row["min"])}–{num(row["max"])} CFM range · {dev}% from '
                      f'optimal ({num(row["opt"])} CFM)')
            fit = "Optimal" if dev <= 10 else "Within Range"
        outputs += [
            {"label": "Fit", "value": fit},
            {"label": "Rated range",
             "value": f'{num(row["min"])} – {num(row["opt"])} – {num(row["max"])} CFM'},
            {"label": "Barrel dia × overall height", "value": f'{d["A"]}" × {d["B"]}"'},
            {"label": "Cone height", "value": f'{d["C"]}"'},
            {"label": "Inlet", "value": f'{d["D"]}"'},
            {"label": "Weight", "value": f'~{num(row["weight"])} lb'},
        ]
        desc = [
            f'{d["A"]}" dia barrel, {d["C"]}" cone, {d["B"]}" overall height, {d["D"]}" inlet',
            f'Rated {num(row["min"])}–{num(row["max"])} CFM (optimal {num(row["opt"])}) · {detail}',
            f'Shipping weight ~{num(row["weight"])} lb',
        ]
        # Overlap zone: the original surfaces the H alternative so the trade-off is a
        # conscious call rather than a silent default.
        alt = next((r for r in CY_H_SPEC if r["cfm3"] >= rated), None)
        if flag == "within" and alt and rated >= CY_H_SPEC[0]["cfm2"]:
            alt_note = (f'Overlap zone — {alt["series"]} also covers this at 3" WG '
                        f'({num(alt["cfm3"])} CFM). HE = better fine-particle separation; '
                        "H = lower cost-per-CFM at volume.")
            outputs.append({"label": "Alternative", "value": alt_note})
            desc.append(alt_note)
        price, price_basis = _vendor.cyclone_price(row["series"], row["weight"])
        lines.append({"name": f'Cyclone — MCE {row["series"]}', "quantity": 1,
                      "unitPrice": round(price, 2) if price else 0,
                      "needsPrice": not price, "description": "\n".join(desc)})
        note = CY_SERIES_NOTES["mce"]

    if price:
        outputs.append({"label": "Cyclone price", "value": f"${price:,.0f}"})
    outputs.append({"label": "Series basis", "value": note})
    return {"calculator": "Cyclone", "outputs": outputs, "warnings": warnings,
            "lines": lines, "total": round(price or 0.0, 2), "formula": formula,
            "priceBasis": price_basis,
            "cfm": jsround(rated), "model": lines[0]["name"].split("— ", 1)[1],
            "matchSize": match_size, "fit": fit, "detail": detail,
            "altNote": alt_note}
