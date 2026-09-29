#!/usr/bin/env python3
"""Fan sizing — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/fan-sizing-calculator.html (served whole at
/tools/fan). Efficiencies, wheel types, velocity bands, motor sizes and line sizes
are extracted verbatim into _data.py.

    density factor df = (530 / (460 + T)) x (1 - 6.87535e-6 x alt) ^ 5.2559
    BHP               = ACFM x SP / (6356 x efficiency)
    motor             = first standard frame >= shaft load x 1.05
    line size         = smallest listed diameter whose velocity <= the band max

This is a SELECTION tool, not a price: it produces the duty, the wheel, the motor
and the RFQ block MCE sends to AirPro or IAP. The fan's price still comes from a
vendor selection — which is exactly what the RFQ text is for.
"""
import math

from . import _vendor
from ._data import (FN_DUCT_SIZES, FN_EFF, FN_MOTORS, FN_SERVICE, FN_SPDEF,
                    FN_VBAND, FN_WHEEL)
from ._fmt import jsround, num

SERVICE_OPTIONS = [
    ("radial", "Cooler / cyclone exhaust — straight radial"),
    ("hmAssist", "Hammermill air assist — fan after filter"),
    ("hmNeg", "Hammermill negative air — fan after filter"),
    ("convey", "Material conveying — straight radial"),
    ("rtip", "Dust-laden air — radial tipped"),
    ("bi", "Clean air after filter — backward inclined"),
]
ACCESSORIES = [
    ("accDamper", "outlet damper", True),
    ("accTrans", "outlet transition", True),
    ("accSeal", "shaft seal", False),
    ("accIso", "vibration isolators", False),
    ("accSpark", "spark-resistant construction (AMCA)", False),
    ("accVfd", "fan VFD (comms-ready to MCE cooler control system)", False),
]
STANDING_ACCESSORY = "belt/shaft/bearing guards"


def _js(value):
    """String(Number) the way JavaScript concatenation does it — no grouping.

    The original writes the temperature, the altitude's label and the motor size
    straight into strings, so `100` must render "100" and not "100.0".
    """
    v = float(value)
    return str(int(v)) if v.is_integer() else repr(v)


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _flag(raw, default=False):
    """A missing key takes the form's default; an empty one is an explicit no.

    The original's defaults live in the HTML's `checked` attributes, which the
    registry mirrors as the field defaults. So "" has to mean off, or a box the
    rep cleared would come back ticked.
    """
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def density_factor(temp_f, altitude_ft):
    """MCE's own density term: temperature x US standard atmosphere."""
    return (530 / (460 + temp_f)) * math.pow(1 - 6.87535e-6 * altitude_ft, 5.2559)


def size(f):
    svc = str(f.get("service") or "radial")
    if svc not in FN_EFF:
        return {"error": f"{svc!r} is not one of MCE's fan services."}
    cfm0 = max(_num(f.get("cfm")), 0.0)
    sp0 = max(_num(f.get("sp"), FN_SPDEF.get(svc, 19)), 0.0)
    temp = _num(f.get("temp"), 70) or 70
    alt = max(_num(f.get("alt")), 0.0)
    margin = 1 + max(_num(f.get("margin")), 0.0) / 100
    belt = str(f.get("drive") or "belt") == "belt"
    stainless = str(f.get("material") or "ms") == "ss"

    if cfm0 <= 0:
        return {"error": "Design airflow (ACFM) is required."}
    if sp0 <= 0:
        return {"error": "Design static pressure is required."}

    cfm = cfm0 * margin
    sp = sp0 * margin
    eff = FN_EFF[svc]
    df = density_factor(temp, alt)
    scfm = cfm * df
    sp_eq = sp / df if df > 0 else sp
    bhp = cfm * sp / (6356 * eff)
    shaft = bhp * (1.05 if belt else 1.0)
    motor = next((h for h in FN_MOTORS if h >= shaft * 1.05), math.ceil(shaft * 1.05))

    v_min, v_max = FN_VBAND[svc]
    duct = None
    for d in FN_DUCT_SIZES:
        v = cfm / (math.pi / 4 * (d / 12) ** 2)
        if v <= v_max:
            duct = {"d": d, "v": v}
            break

    line = ((f'{_js(duct["d"])}" dia ({num(duct["v"], 0)} FPM'
             + (f' ⚠ below {num(v_min, 0)}' if duct["v"] < v_min else "") + ")")
            if duct else '> 48"')

    warnings = []
    if duct and duct["v"] < v_min:
        warnings.append(
            f'The line runs at {num(duct["v"], 0)} FPM, below the {num(v_min, 0)} FPM '
            f"floor for {FN_SERVICE[svc].lower()} — material drops out of a line that "
            "slow. Step the line down a size or check the airflow.")
    if not duct:
        warnings.append('Line size is beyond 48" at this airflow — take the layout to '
                        "engineering.")
    if svc in ("radial", "convey"):
        warnings.append("Material-handling duty: backward-inclined wheels are not "
                        "accepted, the RFQ says so explicitly.")

    outputs = [
        {"label": "Design airflow", "value": f"{num(jsround(cfm), 0)} ACFM", "headline": True},
        {"label": "Design static", "value": f'{num(sp, 1)}" WC', "headline": True},
        {"label": "Std-air equivalent SP", "value": f'{num(sp_eq, 1)}" WC'},
        {"label": "Estimated motor", "value": f"{_js(motor)} HP", "headline": True},
        {"label": "Service", "value": FN_SERVICE[svc]},
        {"label": "Wheel", "value": FN_WHEEL[svc]},
        {"label": "Density factor",
         "value": f"{num(df, 3)}  ({_js(temp)} °F, {num(alt, 0)} ft)"},
        {"label": "Std-air airflow", "value": f"{num(jsround(scfm), 0)} SCFM"},
        {"label": "Est. brake HP",
         "value": f"{num(bhp, 1)} BHP (η {num(eff * 100, 0)}%)"},
        {"label": "Est. shaft load" + (" (belt)" if belt else ""),
         "value": f"{num(shaft, 1)} HP"},
        {"label": "Recommended motor",
         "value": f"{_js(motor)} HP · TEFC · 460V/3φ/60Hz"},
        {"label": "Line connection", "value": line},
        {"label": "Line velocity target",
         "value": f"{num(v_min, 0)}–{num(v_max, 0)} FPM"},
    ]

    chosen = [label for key, label, default in ACCESSORIES if _flag(f.get(key), default)]
    chosen.append(STANDING_ACCESSORY)
    rfq = "\n".join([
        "MCE FAN SPECIFICATION — FOR AIRPRO / IAP SELECTION",
        f"Service: {FN_SERVICE[svc]}",
        f"Design airflow: {num(jsround(cfm), 0)} ACFM at {_js(temp)} °F, "
        f"{num(alt, 0)} ft elevation (≈{num(jsround(scfm), 0)} SCFM)",
        f'Static pressure: {num(sp, 1)}" WC at conditions (≈{num(sp_eq, 1)}" WC '
        "std-air equivalent)",
        f"Density factor: {num(df, 3)}",
        f"Wheel: {FN_WHEEL[svc]}"
        + (" — BI wheels not accepted for this duty" if svc in ("radial", "convey") else ""),
        f"Est. power: {num(bhp, 1)} BHP → {_js(motor)} HP motor, TEFC, premium "
        "efficiency, 460V/3ph/60Hz",
        f'Drive: {"V-belt, 1.3 service factor minimum" if belt else "Direct"}',
        "Arrangement / rotation / discharge: per layout (TBD)",
        "Connections: slip-fit inlet & outlet; line size "
        + (f'{_js(duct["d"])}" dia' if duct else "TBD")
        + f" (target {num(v_min, 0)}–{num(v_max, 0)} FPM)",
        f'Material: {"304 SS wetted parts" if stainless else "mild steel, standard enamel"}',
        "Accessories: " + ", ".join(chosen),
        "Selection: verify BHP, RPM & class on curve in IAP / AirPro software",
    ])

    # SIZED here, priced elsewhere. MCE builds its own XF fans and has an XF sizing
    # calculator; until that is vendored the line carries the full duty and no
    # number, rather than a figure regressed off somebody else's catalogue.
    fan_notes = [
        f"{FN_SERVICE[svc]} fan, {FN_WHEEL[svc].lower()}",
        f'{num(jsround(cfm), 0)} ACFM at {num(sp, 1)}" WC, {_js(temp)} °F and '
        f"{num(alt, 0)} ft elevation (≈{num(jsround(scfm), 0)} SCFM)",
        f"{num(bhp, 1)} BHP estimated → {_js(motor)} HP TEFC premium efficiency, "
        "460 V/3/60",
        f'{"V-belt drive with guards" if belt else "Direct drive"}; ' + ", ".join(chosen),
        (f'{_js(duct["d"])}" dia slip-fit inlet and outlet connections' if duct
         else "Connection size per layout"),
        "Price on selection — the duty above is the RFQ",
    ]
    lines = [{"name": f"Fan — {_js(motor)} HP, {num(jsround(cfm), 0)} ACFM",
              "quantity": 1, "unitPrice": 0, "needsPrice": True,
              "description": "\n".join(fan_notes)}]

    return {"calculator": "Fan Sizing", "outputs": outputs, "warnings": warnings,
            "lines": lines, "total": 0.0, "rfq": rfq,
            "formula": f'{num(jsround(cfm), 0)} ACFM × {num(sp, 1)}" WC ÷ '
                       f"(6,356 × {num(eff, 2)}) = {num(bhp, 1)} BHP",
            "motorHp": motor, "bhp": round(bhp, 2), "cfm": jsround(cfm),
            "lineDiameter": duct["d"] if duct else None,
            "densityFactor": round(df, 4)}
