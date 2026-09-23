#!/usr/bin/env python3
"""Baghouse filter sizing — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/baghouse-filter-calculator.html (served whole at
/tools/baghouse). Geometry constants and the Kice PneuJet comparison table are
extracted verbatim into _data.py.

    required cloth area = CFM / air-to-cloth ratio
    MCE model           = smallest square-grid unit that meets it
"""
import math

from ._data import BH_BAG_COUNTS, BH_BAG_LENGTHS, BH_KICE_MODELS

CLOTH_PER_BAG_FT = math.pi * 0.5   # ft² of cloth per bag-foot (6.0" dia bags)
PULSE_PER_BAG_FT = 0.0221          # SCFM pulse air per bag-foot
BAG_PITCH = 8                      # in, bag centerline spacing
CAP_HT = 16                        # in, air cap / manifold above the tube sheet
MILL_CFM_PER_IN2 = 1.3             # same basis the hammermill plenum uses

RATIO_PRESETS = [
    ("6.25", "6.25:1 — conservative"),
    ("7", "7:1 — MCE standard"),
    ("7.5", "7.5:1 — aggressive"),
]


def _models():
    out = []
    for length in BH_BAG_LENGTHS:
        for n in BH_BAG_COUNTS:
            side = int(math.isqrt(n))
            out.append({
                "model": f"{n}-{length}", "bags": n, "grid": f"{side}×{side}",
                "len": length, "area": n * length * CLOTH_PER_BAG_FT,
                "pulse": n * length * PULSE_PER_BAG_FT, "plan": side * BAG_PITCH,
                "housingH": length * 12 + CAP_HT,
            })
    out.sort(key=lambda m: (m["area"], m["len"]))
    return out


MCE_MODELS = _models()
# The original sorts its Kice comparison table by cloth area before searching it;
# the extracted literal is in catalog order, so sort it the same way here.
KICE_MODELS = sorted(BH_KICE_MODELS, key=lambda m: m["area"])


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def size(f):
    mode = "mill" if f.get("mode") == "mill" else "cfm"
    ratio = _num(f.get("ratio"), 7)
    len_filter = str(f.get("lenFilter") or "any")

    if mode == "mill":
        screen_area = _num(f.get("screenArea"))
        if screen_area <= 0:
            return {"error": "Mill screen area is required."}
        cfm = screen_area * MILL_CFM_PER_IN2
        basis = f"{screen_area:,.0f} in² mill screen × {MILL_CFM_PER_IN2} = {cfm:,.0f} CFM"
    else:
        cfm = _num(f.get("cfm"))
        if cfm <= 0:
            return {"error": "System airflow (CFM) is required."}
        basis = f"{cfm:,.0f} CFM system airflow"
    if ratio <= 0:
        return {"error": "Air-to-cloth ratio must be greater than zero."}

    req_area = cfm / ratio
    warnings, outputs = [], []
    formula = f"{basis} ÷ {ratio:g}:1 = {req_area:,.0f} ft² cloth"

    pool = [m for m in MCE_MODELS
            if len_filter == "any" or m["len"] == int(float(len_filter))]
    mce = next((m for m in pool if m["area"] >= req_area), None)
    kice = next((m for m in KICE_MODELS if m["area"] >= req_area), None)

    outputs.append({"label": "System airflow", "value": f"{cfm:,.0f} CFM", "headline": True})
    outputs.append({"label": "Required cloth area", "value": f"{req_area:,.0f} ft²",
                    "headline": True})
    outputs.append({"label": "Air-to-cloth ratio", "value": f"{ratio:g}:1"})

    lines = []
    if mce:
        actual = cfm / mce["area"]
        if actual > 7.5:
            warnings.append(f"{mce['model']} runs at {actual:.1f}:1 — above MCE's 7.5:1 "
                            "comfort limit. Step up a size or add bag length.")
        outputs += [
            {"label": "MCE filter", "value": mce["model"], "headline": True},
            {"label": "Configuration",
             "value": f'{mce["grid"]} grid of {mce["len"]} ft bags ({mce["bags"]} bags)'},
            {"label": "Cloth area", "value": f'{mce["area"]:,.0f} ft²'},
            {"label": "Actual ratio", "value": f"{actual:.2f}:1"},
            {"label": "Pulse air", "value": f'{mce["pulse"]:.2f} SCFM'},
            {"label": "Plan", "value": f'{mce["plan"]}" × {mce["plan"]}"'},
            {"label": "Housing height", "value": f'{mce["housingH"]}"'},
        ]
        lines.append({
            "name": f'Baghouse Filter — MCE {mce["model"]}', "quantity": 1,
            "unitPrice": 0, "needsPrice": True,
            "description": "\n".join([
                f'{mce["bags"]} × {mce["len"]} ft bags in a {mce["grid"]} grid, '
                f'6" dia on {BAG_PITCH}" centers',
                f'{mce["area"]:,.0f} ft² cloth — runs at {actual:.2f}:1 on {cfm:,.0f} CFM',
                f'{mce["plan"]}" × {mce["plan"]}" plan, {mce["housingH"]}" housing height, '
                "plenum-mount (no hopper)",
                f'{mce["pulse"]:.2f} SCFM pulse air required',
                "Price from the fabrication estimate — this calculator sizes only",
            ])})
    else:
        limit = f" at {len_filter} ft bags" if len_filter != "any" else ""
        warnings.append(
            f"{req_area:,.0f} ft² exceeds the largest single MCE unit{limit} — split "
            f"across multiple filters ({cfm / 2:,.0f} CFM each) or relax the bag-length limit.")
        outputs.append({"label": "MCE filter", "value": "Consult engineering", "headline": True})

    if kice:
        outputs.append({
            "label": "Kice equivalent",
            "value": f'{kice["model"]} — {kice["area"]:,} ft² at {cfm / kice["area"]:.1f}:1, '
                     f'{kice["wt"]:,} lb'})
    else:
        outputs.append({"label": "Kice equivalent",
                        "value": "Beyond S 121-10 (1,425 ft²) — multiple units"})

    return {"calculator": "Baghouse Filter", "outputs": outputs, "warnings": warnings,
            "lines": lines, "total": 0.0, "formula": formula,
            "required_area": round(req_area), "cfm": round(cfm)}
