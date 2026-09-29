#!/usr/bin/env python3
"""XF fan duty and selection — a port of MCE's own XF fan sizing calculator.

This is the one that matters for MCE's own iron. fan.py sizes a duty and writes
an RFQ for AirPro or IAP; this one takes the same duty to MCE's XF line, which is
built on New York Blower's LS series, and comes back with a wheel diameter, a
speed and a brake horsepower off the published capacity tables (Bulletin 251).

Two halves, the way the calculator lays them out:

  1. the duct system    velocity, Huebscher friction, fitting losses and the
                        equipment drop -> the static the fan has to make, both at
                        site conditions and corrected to standard air
  2. the fan            that duty against the LS capacity tables, interpolated on
                        CFM and on static, for every size that reasonably covers
                        it — with each size's max safe speed from Chart III, and
                        the temperature correction from Chart IV

Selection rule, as the calculator has it: the smallest wheel that is inside its
max safe speed is the recommendation, the lowest brake horsepower in range is
flagged as the most efficient alternative, and anything read off the end of a
table is flagged as extrapolated rather than quietly used.

Sizes only. The XF price list is not on file, so every line this produces carries
needsPrice — see _pricing.UNPRICED["fan"].
"""
import math

from . import _fmt
from ._xf_data import LS_DATA, LS_MAX_SAFE_RPM_70F, LS_SP_COLS, NEMA_HP

# Chart IV — mild steel max safe speed temperature correction.
TEMP_FACTOR_POINTS = [(70, 1.0), (200, 1.0), (300, 1.0), (400, 0.97), (500, 0.94),
                      (600, 0.91), (700, 0.89), (800, 0.87), (900, 0.85), (1000, 0.82)]

# Fan classes. The radial line is MCE's own; the rest are estimates off an assumed
# static efficiency, which is what the calculator says they are.
FAN_CLASSES = [
    ("RAD", "Radial / paddle-wheel — MCE XF / NYB LS series", 0.60, 0.25),
    ("AF", "Backward-inclined / airfoil (estimate)", 0.68, 0.15),
    ("FC", "Forward-curved (estimate)", 0.55, 0.40),
    ("AX", "Vane-axial (estimate)", 0.65, 0.30),
]
CLASS_ETA = {k: eta for k, _l, eta, _k in FAN_CLASSES}
CLASS_K = {k: kk for k, _l, _e, kk in FAN_CLASSES}
CLASS_LABEL = {k: l for k, l, _e, _k in FAN_CLASSES}

ENTRY_LOSSES = [("0.5", "Sharp entry (K=0.5)"), ("0.05", "Bellmouth / rounded (K=0.05)"),
                ("0", "None")]
EXIT_LOSSES = [("1.0", "Free discharge (K=1.0)"), ("0", "Ducted / recovered")]
ELBOW_K = 0.75
TIP_SPEED_LIMIT = 16000          # fpm — above this, check the wheel rating

SOURCE = ("MCE XF fan sizing calculator; New York Blower LS series capacity tables, "
          "Bulletin 251. Duct design per Huebscher/ASHRAE, fan laws per AMCA.")


def _num(raw, default=0.0):
    try:
        v = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _opt(raw):
    if raw is None or str(raw).strip() == "":
        return None
    v = _num(raw, float("nan"))
    return None if math.isnan(v) else v


def _flag(raw):
    return str(raw or "").strip().lower() in ("1", "true", "yes", "on", "y")


# --- air properties and duct loss ----------------------------------------------

def barometric_in_hg(elevation_ft):
    return 29.92 * (1 - 6.8753e-6 * elevation_ft) ** 5.2559


def density_ratio(elevation_ft, temp_f):
    """Actual air density over standard, the calculator's own two-term form."""
    return (barometric_in_hg(elevation_ft) / 29.92) * (530 / (temp_f + 460))


def duct_area_ft2(diameter_in):
    d_ft = diameter_in / 12
    return math.pi * d_ft * d_ft / 4


def velocity_fpm(cfm, diameter_in):
    return cfm / duct_area_ft2(diameter_in)


def velocity_pressure_std(v_fpm):
    return (v_fpm / 4005) ** 2


def friction_per_100_std(cfm, diameter_in):
    """Huebscher (ASHRAE) — galvanized round duct, standard air, in. wg / 100 ft."""
    return 0.109136 * cfm ** 1.9 / diameter_in ** 5.02


def next_motor_size(bhp):
    for hp in NEMA_HP:
        if hp >= bhp:
            return hp
    return NEMA_HP[-1]


def max_safe_speed_factor(temp_f):
    pts = TEMP_FACTOR_POINTS
    if temp_f <= pts[0][0]:
        return pts[0][1]
    for (t0, f0), (t1, f1) in zip(pts, pts[1:]):
        if t0 <= temp_f <= t1:
            return f0 + (temp_f - t0) / (t1 - t0) * (f1 - f0)
    return pts[-1][1]


# --- the LS capacity tables -----------------------------------------------------

def interp_along_cfm(rows, col, target_cfm):
    """One static-pressure column of one size, interpolated on airflow."""
    pts = [{"cfm": r["cfm"], "rpm": r["sp"][col][0], "bhp": r["sp"][col][1],
            "ov": r["ov"]}
           for r in rows if col in r["sp"]]
    if len(pts) < 2:
        return None
    pts.sort(key=lambda p: p["cfm"])
    if target_cfm <= pts[0]["cfm"]:
        i = 0
    elif target_cfm >= pts[-1]["cfm"]:
        i = len(pts) - 2
    else:
        i = next(j for j in range(len(pts) - 1)
                 if pts[j]["cfm"] <= target_cfm <= pts[j + 1]["cfm"])
    a, b = pts[i], pts[i + 1]
    t = (target_cfm - a["cfm"]) / (b["cfm"] - a["cfm"])
    return {"rpm": a["rpm"] + t * (b["rpm"] - a["rpm"]),
            "bhp": a["bhp"] + t * (b["bhp"] - a["bhp"]),
            "ov": a["ov"] + t * (b["ov"] - a["ov"]),
            "extrap": target_cfm < pts[0]["cfm"] or target_cfm > pts[-1]["cfm"],
            "minCfm": pts[0]["cfm"], "maxCfm": pts[-1]["cfm"]}


def interp_size(size_data, target_cfm, target_sp_std):
    """One LS size at the duty: interpolate on airflow, then between SP columns."""
    lo, hi = LS_SP_COLS[0], LS_SP_COLS[-1]
    for a, b in zip(LS_SP_COLS, LS_SP_COLS[1:]):
        if a <= target_sp_std <= b:
            lo, hi = a, b
            break
    if target_sp_std < LS_SP_COLS[0]:
        lo, hi = LS_SP_COLS[0], LS_SP_COLS[1]
    if target_sp_std > LS_SP_COLS[-1]:
        lo, hi = LS_SP_COLS[-2], LS_SP_COLS[-1]
    r_lo = interp_along_cfm(size_data["rows"], str(lo), target_cfm)
    r_hi = interp_along_cfm(size_data["rows"], str(hi), target_cfm)
    if not r_lo or not r_hi:
        return None
    sp_extrap = (target_sp_std < LS_SP_COLS[0] or target_sp_std > LS_SP_COLS[-1])
    t = (target_sp_std - lo) / (hi - lo)
    return {"rpm": r_lo["rpm"] + t * (r_hi["rpm"] - r_lo["rpm"]),
            "bhp": r_lo["bhp"] + t * (r_hi["bhp"] - r_lo["bhp"]),
            "ov": r_lo["ov"] + t * (r_hi["ov"] - r_lo["ov"]),
            "extrap": r_lo["extrap"] or r_hi["extrap"] or sp_extrap,
            "minCfm": r_lo["minCfm"], "maxCfm": r_lo["maxCfm"]}


def select_ls_candidates(target_cfm, target_sp_std, temp_f):
    """Every LS size that reasonably covers the duty, in catalog order."""
    out = []
    for key, size_data in LS_DATA.items():
        res = interp_size(size_data, target_cfm, target_sp_std)
        if not res:
            continue
        if target_cfm < res["minCfm"] * 0.7 or target_cfm > res["maxCfm"] * 1.8:
            continue
        max_safe = LS_MAX_SAFE_RPM_70F[key] * max_safe_speed_factor(temp_f)
        out.append({
            "key": key, "wheelDiaIn": size_data["wheel_dia_in"],
            "xf": "XF-" + str(_fmt.jsround(size_data["wheel_dia_in"])),
            "lsName": key + " LS",
            "rpm": res["rpm"], "bhp": res["bhp"], "ov": res["ov"],
            "extrap": res["extrap"], "maxSafeRpm": max_safe,
            "overSpeed": res["rpm"] > max_safe})
    return out


def shortlist(candidates):
    """The calculator's own window: the recommendation, one size below for
    context, and up to three above so the efficiency trade is visible."""
    if not candidates:
        return [], None, None
    all_sorted = sorted(candidates, key=lambda c: c["wheelDiaIn"])
    feasible_all = [c for c in all_sorted if not c["overSpeed"]]
    recommended = feasible_all[0] if feasible_all else all_sorted[0]
    idx = all_sorted.index(recommended)
    window = all_sorted[max(0, idx - 1):idx + 4]
    feasible = [c for c in window if not c["overSpeed"]]
    most_eff = min(feasible or window, key=lambda c: c["bhp"])
    return window, recommended, most_eff


# --- the calculator -------------------------------------------------------------

def size(f):
    elev = _num(f.get("elev"), 0)
    temp = _num(f.get("temp"), 70)
    df = density_ratio(elev, temp)

    cfm1 = _num(f.get("cfm1"), 5000)
    dia1 = _num(f.get("dia1"), 18)
    len1 = _num(f.get("len1"), 60)
    elbows = _num(f.get("elbows"), 2)
    entry_k = _num(f.get("entry"), 0.5)
    exit_k = _num(f.get("exit"), 1.0)
    equip = _num(f.get("equip1"), 2.0)

    if dia1 <= 0:
        return {"error": "A duct diameter is required."}
    if cfm1 <= 0:
        return {"error": "A duct airflow is required."}

    vel = velocity_fpm(cfm1, dia1)
    vp_std = velocity_pressure_std(vel)
    total_k = elbows * ELBOW_K + entry_k + exit_k
    fric_std = friction_per_100_std(cfm1, dia1) * (len1 / 100)
    fit_std = total_k * vp_std
    duct_loss_actual = (fric_std + fit_std) * df
    total_actual = duct_loss_actual + equip
    total_std_equiv = total_actual / df if df else 0

    # --- the fan duty ----------------------------------------------------------
    cfm2 = _num(f.get("cfm2"), 5000)
    sp2_actual = _num(f.get("sp2"), 4.0)
    if _flag(f.get("useSystem")):
        cfm2, sp2_actual = cfm1, total_actual
    sp2_std = sp2_actual / df if df else 0

    fan_class = str(f.get("fanClass") or "RAD").strip().upper()
    if fan_class not in CLASS_ETA:
        fan_class = "RAD"
    eta, curve_k = CLASS_ETA[fan_class], CLASS_K[fan_class]
    is_radial = fan_class == "RAD"

    warnings, notes = [], []
    candidates, window, recommended, most_eff, chosen = [], [], None, None, None
    tip_dia = _opt(f.get("assumedDia"))
    tip_rpm = None
    solve = []

    if is_radial:
        candidates = select_ls_candidates(cfm2, sp2_std, temp)
        window, recommended, most_eff = shortlist(candidates)
        want = str(f.get("lsSize") or "").strip()
        chosen = next((c for c in window if c["key"] == want or c["xf"] == want),
                      recommended)
        if chosen:
            bhp_std = chosen["bhp"]
            tip_dia = chosen["wheelDiaIn"]
            tip_rpm = chosen["rpm"]
            solve = [("Selected size", f'{chosen["xf"]} ({chosen["lsName"]})'),
                     ("Fan speed", f'{_fmt.fixed(chosen["rpm"], 0)} RPM')]
            if chosen["overSpeed"]:
                solve.append(("Max safe speed",
                              f'exceeds {_fmt.fixed(chosen["maxSafeRpm"], 0)} RPM limit'))
                warnings.append(
                    f'{chosen["xf"]} runs at {_fmt.fixed(chosen["rpm"], 0)} RPM against a '
                    f'{_fmt.fixed(chosen["maxSafeRpm"], 0)} RPM max safe speed for mild '
                    "steel at this temperature (Chart III with the Chart IV correction). "
                    "Take the next size up, or have it built in a heavier class.")
            if chosen["extrap"]:
                warnings.append(
                    f'{chosen["xf"]} is read off the end of its capacity table — the '
                    "duty is outside what Bulletin 251 publishes for that size, so the "
                    "RPM and BHP are extrapolated. Confirm against a factory selection.")
        else:
            bhp_std = 0.0
            warnings.append(
                "No MCE XF / NYB LS size in the catalog reasonably covers this duty "
                "point — check the target CFM and static.")
    elif _flag(f.get("useRef")):
        q1 = _num(f.get("refQ"))
        sp1 = _num(f.get("refSP"))
        rpm1 = _num(f.get("refRPM"))
        bhp1 = _num(f.get("refBHP"))
        d1 = _num(f.get("refDia"))
        if q1 and sp1 and rpm1:
            if d1:
                # solve diameter and speed together off the fan laws
                x4 = (cfm2 / q1) ** 2 * (sp1 / sp2_std) if sp2_std else 0
                x = max(x4, 1e-9) ** 0.25
                y = (cfm2 / q1) / x ** 3
                tip_dia, tip_rpm = d1 * x, rpm1 * y
                bhp_std = bhp1 * x ** 5 * y ** 3
                solve = [("Solved wheel diameter", f"{_fmt.fixed(tip_dia, 1)} in"),
                         ("Solved fan speed", f"{_fmt.fixed(tip_rpm, 0)} RPM")]
            else:
                n2 = rpm1 * (cfm2 / q1)
                sp_check = sp1 * (n2 / rpm1) ** 2
                diff_pct = (sp_check - sp2_std) / sp2_std * 100 if sp2_std else 0
                bhp_std = bhp1 * (n2 / rpm1) ** 3
                tip_rpm = n2
                # the original carries the deviation in the row's label, beside the
                # name, not in the value — keep it there so the two read alike
                delta = (f'{"+" if diff_pct >= 0 else ""}'
                         f'{_fmt.fixed(diff_pct, 0)}% vs target')
                solve = [("Required fan speed (same wheel)", f"{_fmt.fixed(n2, 0)} RPM"),
                         (f"SP this speed actually gives {delta}",
                          f"{_fmt.fixed(sp_check, 2)} in.wg")]
                if abs(diff_pct) > 10:
                    warnings.append(
                        f"Holding the reference wheel and running it to {cfm2:,.0f} CFM "
                        f'gives {_fmt.fixed(sp_check, 2)} in.wg, '
                        f'{_fmt.fixed(abs(diff_pct), 0)}% off the target static. The '
                        "wheel has to change, not just the speed.")
        else:
            bhp_std = cfm2 * sp2_std / (6356 * eta)
            notes.append("Enter reference CFM, SP and RPM to solve off the fan laws.")
    else:
        bhp_std = cfm2 * sp2_std / (6356 * eta)
        solve = [("Estimated static efficiency", f"{_fmt.fixed(eta * 100, 0)}%")]
        notes.append(
            f"{CLASS_LABEL[fan_class]} is sized off an assumed static efficiency, not "
            "off a capacity table. It is an estimate until a vendor selects against it.")

    bhp_actual = bhp_std * df
    margin = _num(f.get("margin"), 15)
    motor = next_motor_size(bhp_actual * (1 + margin / 100))

    tip_speed = None
    if tip_dia and tip_rpm:
        tip_speed = math.pi * (tip_dia / 12) * tip_rpm
        if tip_speed > TIP_SPEED_LIMIT:
            warnings.append(
                f"Tip speed is {_fmt.fixed(tip_speed, 0)} fpm, over the "
                f"{TIP_SPEED_LIMIT:,} fpm this calculator treats as the typical range. "
                "Check the wheel rating.")

    if temp > 200:
        notes.append(
            f"At {_fmt.jsround(temp)} °F the max safe speeds carry the Chart IV mild "
            "steel correction. A high-temperature wheel or a different arrangement may "
            "be the right answer instead.")

    outputs = [
        {"label": "Fan duty", "value": f"{_fmt.num(cfm2)} CFM at "
                                       f"{_fmt.fixed(sp2_actual, 2)} in.wg",
         "headline": True},
        {"label": "Standard-air equivalent static",
         "value": f"{_fmt.fixed(sp2_std, 2)} in.wg",
         "note": f"density factor {_fmt.fixed(df, 3)} at {_fmt.jsround(elev)} ft and "
                 f"{_fmt.jsround(temp)} °F"},
        {"label": "Brake horsepower", "value": f"{_fmt.fixed(bhp_actual, 2)} BHP"},
        {"label": "Motor", "value": f"{_fmt.locale(motor)} HP",
         "note": f"next NEMA size above BHP + {_fmt.jsround(margin)}%"},
    ]
    if is_radial and chosen:
        outputs.insert(1, {"label": "MCE model", "value": chosen["xf"],
                           "note": f'New York Blower {chosen["lsName"]}, '
                                   f'{_fmt.fixed(chosen["wheelDiaIn"], 2)}" wheel at '
                                   f'{_fmt.fixed(chosen["rpm"], 0)} RPM'})
    outputs.append({"label": "Tip speed",
                    "value": (f"{_fmt.fixed(tip_speed, 0)} fpm" if tip_speed
                              else "— (enter wheel dia.)"),
                    "note": ("check wheel rating"
                             if tip_speed and tip_speed > TIP_SPEED_LIMIT
                             else "typical range" if tip_speed else "")})

    system = [
        {"label": "Duct velocity", "value": f"{_fmt.fixed(vel, 0)} fpm"},
        {"label": "Friction loss", "value": f"{_fmt.fixed(fric_std * df, 2)} in.wg",
         "note": f"Huebscher over {_fmt.locale(len1)} ft of {_fmt.locale(dia1)}\" duct"},
        {"label": "Fitting loss", "value": f"{_fmt.fixed(fit_std * df, 2)} in.wg",
         "note": f"K = {_fmt.locale(round(total_k, 4))} on "
                 f"{_fmt.fixed(vp_std * df, 3)} in.wg velocity pressure"},
        {"label": "Equipment loss", "value": f"{_fmt.fixed(equip, 2)} in.wg"},
        {"label": "Total system resistance",
         "value": f"{_fmt.fixed(total_actual, 2)} in.wg", "headline": True},
        {"label": "Standard-air equivalent",
         "value": f"{_fmt.fixed(total_std_equiv, 2)} in.wg"},
    ]

    line = {
        "name": (f'Fan — MCE {chosen["xf"]}' if is_radial and chosen
                 else "Fan — size and price TBD"),
        "quantity": 1, "unitPrice": 0, "needsPrice": True,
        "description": "\n".join(filter(None, [
            f"{_fmt.num(cfm2)} CFM at {_fmt.fixed(sp2_actual, 2)}\" WC, "
            f"{_fmt.jsround(temp)} °F, {_fmt.jsround(elev)} ft elevation",
            (f'{chosen["xf"]} radial wheel, {_fmt.fixed(chosen["wheelDiaIn"], 2)}" dia at '
             f'{_fmt.fixed(chosen["rpm"], 0)} RPM' if is_radial and chosen else ""),
            f"{_fmt.fixed(bhp_actual, 2)} BHP, {_fmt.locale(motor)} HP motor",
            "MCE build — priced on release of the XF price list",
        ]))}

    return {
        "calculator": "XF Fan Duty & Curve", "outputs": outputs, "system": system,
        "warnings": warnings, "notes": notes, "lines": [line], "options": [],
        "total": 0.0, "needsPrice": True, "source": SOURCE,
        "solve": [{"label": k, "value": v} for k, v in solve],
        "candidates": [dict(c, recommended=c is recommended, mostEfficient=c is most_eff,
                            selected=c is chosen) for c in window],
        "densityFactor": round(df, 6),
        "duct": {"velocity": round(vel, 2), "velocityPressureStd": round(vp_std, 6),
                 "frictionStd": round(fric_std, 6), "fittingStd": round(fit_std, 6),
                 "totalK": round(total_k, 4),
                 "lossActual": round(duct_loss_actual, 6),
                 "totalActual": round(total_actual, 6),
                 "totalStdEquiv": round(total_std_equiv, 6)},
        "fan": {"cfm": cfm2, "spActual": round(sp2_actual, 6),
                "spStd": round(sp2_std, 6), "bhpStd": round(bhp_std, 6),
                "bhpActual": round(bhp_actual, 6), "motorHp": motor,
                "tipDiaIn": round(tip_dia, 4) if tip_dia else None,
                "tipRpm": round(tip_rpm, 4) if tip_rpm else None,
                "tipSpeed": round(tip_speed, 2) if tip_speed else None,
                "class": fan_class, "curveK": curve_k},
        "curve": {"k": curve_k, "shutoff": round(sp2_actual * (1 + curve_k), 6),
                  "resistance": (round(sp2_actual / (cfm2 * cfm2), 12)
                                 if cfm2 else None)},
    }
