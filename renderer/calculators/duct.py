#!/usr/bin/env python3
"""Duct sizing — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/duct-sizing-calculator.html (served whole at
/tools/duct). Pure geometry, no tables:

    CFM      = pi/4 x D^2 / 144 x velocity        [from a diameter]
    diameter = 2 x sqrt((CFM / velocity x 144)/pi)  [from an airflow]

and the recommendation rounds up to the next even inch, which is how duct is
bought. MCE has no price basis for ductwork, so this sizes only.
"""
import math

from ._fmt import fixed, jsround, locale, num

VELOCITY_PRESETS = [
    ("4000", "4,000 FPM — grain / feed"),
    ("4500", "4,500 FPM — sawdust"),
]
DEFAULT_VELOCITY = 4000


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def cfm_from_diameter(diameter_in, velocity_fpm):
    return ((math.pi / 4) * diameter_in * diameter_in / 144) * velocity_fpm


def diameter_from_cfm(cfm, velocity_fpm):
    return 2 * math.sqrt((cfm / velocity_fpm * 144) / math.pi)


def next_even(n):
    """Next even inch at or above n — duct is bought in even diameters."""
    ceil = math.ceil(n)
    return ceil if ceil % 2 == 0 else ceil + 1


def size(f):
    mode = "dia" if f.get("mode") == "dia" else "cfm"
    velocity = _num(f.get("velocity"), DEFAULT_VELOCITY)
    if velocity <= 0:
        return {"error": "Minimum conveying velocity must be greater than zero."}

    outputs = []
    if mode == "cfm":
        d = _num(f.get("diameter"))
        if d <= 0:
            return {"error": "A duct diameter is required."}
        r = d / 2
        area = r * r * math.pi
        sqft = area / 144
        cfm = sqft * velocity
        formula = (f"radius² {fixed(r * r, 1)} × π = {fixed(area, 1)} in² ÷ 144 = "
                   f"{fixed(sqft, 2)} ft² × {num(velocity)} FPM = {num(jsround(cfm))} CFM")
        outputs = [
            {"label": "Minimum airflow", "value": f"{num(jsround(cfm))} CFM", "headline": True},
            {"label": "Duct diameter", "value": f'{d:g}"'},
            {"label": "Conveying velocity", "value": f"{num(velocity)} FPM"},
        ]
        return {"calculator": "Duct Sizing", "outputs": outputs, "warnings": [],
                "lines": [], "total": 0.0, "formula": formula,
                "cfm": jsround(cfm), "diameter": d, "velocity": velocity}

    cfm = _num(f.get("cfm"))
    if cfm <= 0:
        return {"error": "An airflow (CFM) is required."}
    sqft = cfm / velocity
    area = sqft * 144
    dia = 2 * math.sqrt(area / math.pi)
    rec = next_even(dia)
    formula = (f"{locale(cfm)} CFM ÷ {num(velocity)} FPM = {fixed(sqft, 3)} ft² × 144 = "
               f"{fixed(area, 1)} in² → D = {fixed(dia, 2)} in")
    outputs = [
        {"label": "Recommended duct", "value": f'{rec}"', "headline": True},
        {"label": "Minimum diameter", "value": f'{fixed(dia, 2)}"'},
        {"label": "Fit", "value": "Exact fit" if abs(rec - dia) < 0.05 and rec % 2 == 0
                                  else "Rounded up"},
        {"label": "Conveying velocity", "value": f"{num(velocity)} FPM"},
    ]
    return {"calculator": "Duct Sizing", "outputs": outputs, "warnings": [],
            "lines": [], "total": 0.0, "formula": formula,
            "cfm": cfm, "diameter": rec, "minDiameter": dia, "velocity": velocity}
