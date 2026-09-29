#!/usr/bin/env python3
"""Rotary airlock sizing — how big a valve the duty actually needs.

Until now the air system chain dropped in MCE's standard FT-12 with a warning
that it had never been sized against anything. This sizes it.

A rotary valve is a positive-displacement machine: it moves

    pocket displacement (ft³/rev) × speed (rpm) × 60 × fill efficiency

cubic feet an hour, and it leaks air backwards through the pockets returning
empty and through the rotor-to-housing clearances. The first two are geometry and
are computed here. The third — clearance leakage — depends on the rotor tip
design, the wear state and the differential, and only the vendor's own curve
gives it, so this says so rather than inventing a number.

What it will not do is invent a displacement. MCE has ft³/rev on record for the
two certified NEMO valves and not for the Airlanco FT-12 it quotes as standard,
so a duty is checked against the ones it can check and the gap is named
(_vendor.AIRLOCK_NO_DISPLACEMENT).

Fill efficiency is the one judgement call, and it is an input with its basis on
the face of the calculator: 85–90 % for free-flowing pellets and grain, 70–80 %
for meal and mash, and down to 50–60 % for a light, fluffy or aerated material
that will not drop into a pocket in the time it is open. Under vacuum on the
inlet, take the low end.
"""
import math

from . import _fmt, _vendor

FILL_PRESETS = [
    ("0.88", "Free-flowing pellets, grain, granules — 88%"),
    ("0.75", "Meal, mash, ground feed — 75%"),
    ("0.60", "Light, fluffy or aerated — 60%"),
    ("0.50", "Under vacuum on the inlet, or very light — 50%"),
]
DEFAULT_FILL = 0.75
# Rotor tip speed. A drop-through valve is normally run slowly: fast rotors shear
# and smear product and wear the tips. This is the band MCE's own valves on record
# sit in (FT-12 at 18 RPM, the NEMO valves at 30 RPM), not a published standard.
RPM_PRESETS = [("15", "15 RPM — gentle, minimum smear"),
               ("18", "18 RPM — the FT-12's own speed"),
               ("22", "22 RPM"),
               ("30", "30 RPM — the certified valves' speed")]
DEFAULT_RPM = 18
RPM_BAND = (12, 35)

SERVICE = [("gravity", "Gravity discharge — under a filter or cyclone hopper"),
           ("feeder", "Feeding a pressure or vacuum line")]

SOURCE = ("Positive-displacement capacity from the valve's own pocket volume; "
          "displacements from the vendor quotes on file in _vendor.py")


def _num(raw, default=0.0):
    try:
        v = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def required_displacement(rate_lb_h, bulk_density, rpm, fill):
    """(ft³/h required, ft³/rev required) for a duty."""
    volume_ft3_h = rate_lb_h / bulk_density
    per_rev = volume_ft3_h / (rpm * 60 * fill)
    return volume_ft3_h, per_rev


def carryover_cfm(ft3_per_rev, rpm, fill):
    """Air the empty pockets carry back, ACFM at the inlet side.

    Pure geometry: whatever the pockets do not hold as product, they hold as air,
    and every pocket comes back round. It is the floor on leakage, not the whole
    of it — clearance leakage past the rotor tips is on top and comes off the
    vendor's curve.
    """
    return ft3_per_rev * rpm * (1 - fill)


def candidates(per_rev_needed):
    """Valves on file whose displacement MCE actually has, with their headroom."""
    out = []
    for number, spec in _vendor.AIRLOCK_DISPLACEMENT.items():
        found = _vendor.airlock(number)
        out.append({
            "number": number, "ft3PerRev": spec["ft3_per_rev"],
            "vendorRpm": spec["rpm"], "vendorHp": spec["hp"],
            "source": spec["source"],
            "headroom": spec["ft3_per_rev"] / per_rev_needed if per_rev_needed else None,
            "fits": spec["ft3_per_rev"] >= per_rev_needed,
            "certified": number in _vendor.CERTIFIED_VALVES,
            "sell": found[1] if found else None,
        })
    return sorted(out, key=lambda c: c["ft3PerRev"])


def size(f):
    rate = _num(f.get("rate"))
    tph = _num(f.get("tph"), 4)
    if not rate and tph:
        rate = tph * 2000
    bulk = _num(f.get("bulkDensity"), 40)
    rpm = _num(f.get("rpm"), DEFAULT_RPM)
    fill = _num(f.get("fill"), DEFAULT_FILL)
    dp = _num(f.get("differential"), 0)
    service = str(f.get("service") or "gravity")
    combustible = str(f.get("combustible") or "").strip().lower() in (
        "1", "true", "yes", "on", "y")

    if rate <= 0:
        return {"error": "A material rate is required — either lb/h or TPH."}
    if bulk <= 0:
        return {"error": "A bulk density is required."}
    if rpm <= 0:
        return {"error": "A rotor speed is required."}
    if not 0 < fill <= 1:
        return {"error": "Fill efficiency is a fraction between 0 and 1."}

    volume_ft3_h, per_rev = required_displacement(rate, bulk, rpm, fill)
    cands = candidates(per_rev)
    fits = [c for c in cands if c["fits"]]
    pick = fits[0] if fits else None

    warnings, notes = [], []
    if not RPM_BAND[0] <= rpm <= RPM_BAND[1]:
        notes.append(
            f"{_fmt.locale(rpm)} RPM is outside the {RPM_BAND[0]}–{RPM_BAND[1]} RPM "
            "band MCE's own valves on record run at. Faster shears and smears "
            "product and wears the tips; slower may not keep up with a surge.")

    # the standard valve MCE quotes, which cannot be checked
    for number, why in _vendor.AIRLOCK_NO_DISPLACEMENT.items():
        found = _vendor.airlock(number)
        if found:
            warnings.append(
                f"{number} cannot be checked against this duty: {why}")

    if pick:
        leak = carryover_cfm(pick["ft3PerRev"], rpm, fill)
        notes.append(
            f'{pick["number"]} carries {_fmt.fixed(leak, 1)} ACFM of air back through '
            "the returning pockets at this fill. That is the floor on leakage — "
            "clearance leakage past the rotor tips is on top of it and only the "
            "vendor's curve gives it. Add both to the filter or the blower duty.")
    else:
        warnings.append(
            f"No valve with a displacement on file covers {_fmt.fixed(per_rev, 3)} "
            "ft³/rev at this speed and fill. Either slow nothing down and take a "
            "bigger valve, or raise the speed within the band and re-check.")

    if dp > 0:
        notes.append(
            f'At {_fmt.locale(dp)}" WG differential the carried-back air expands as it '
            "crosses to the low-pressure side, so the volume the filter sees is above "
            "the figure here. The vendor's leakage curve is stated at a differential "
            "— match it to this one.")
    if service == "feeder" and dp <= 0:
        warnings.append(
            "Feeding a pressure or vacuum line with no differential stated. The "
            "leakage, the fill and often the rotor style all change with it — give "
            "the differential.")
    if combustible:
        certified = [c for c in cands if c["certified"] and c["fits"]]
        if certified:
            notes.append(
                f'Combustible dust: {certified[0]["number"]} is one of the certified '
                "valves on file (ATEX EN 15089 / NFPA 69) and covers this duty. A "
                "certified valve is an isolation device — its selection follows the "
                "dust hazard analysis, not this calculator.")
        else:
            warnings.append(
                "Combustible dust, and neither certified valve on file covers this "
                "duty. NFPA 69 isolation has to be sized against the deflagration, "
                "not against the material rate — take it to the dust hazard analysis.")

    outputs = [
        {"label": "Required displacement",
         "value": f"{_fmt.fixed(per_rev, 3)} ft³/rev", "headline": True,
         "note": f"at {_fmt.locale(rpm)} RPM and {_fmt.fixed(fill * 100, 0)}% fill"},
        {"label": "Material volume", "value": f"{_fmt.num(volume_ft3_h)} ft³/h",
         "note": f"{_fmt.num(rate)} lb/h at {_fmt.locale(bulk)} lb/ft³"},
        {"label": "Valve", "value": pick["number"] if pick else "None on file fits"},
    ]
    if pick:
        outputs.append({"label": "Headroom",
                        "value": f'{_fmt.fixed((pick["headroom"] - 1) * 100, 0)}%',
                        "note": f'{pick["number"]} displaces '
                                f'{_fmt.locale(pick["ft3PerRev"])} ft³/rev'})
        outputs.append({"label": "Pocket carry-back",
                        "value": f'{_fmt.fixed(carryover_cfm(pick["ft3PerRev"], rpm, fill), 1)} ACFM',
                        "note": "geometry only — clearance leakage is on top"})

    lines = []
    if pick and pick["sell"]:
        lines.append({
            "name": f'Rotary Airlock — {pick["number"]}', "quantity": 1,
            "unitPrice": round(pick["sell"], 2), "sku": pick["number"],
            "description": "\n".join([
                f'{_fmt.locale(pick["ft3PerRev"])} ft³/rev drop-through rotary valve at '
                f'{_fmt.locale(rpm)} RPM',
                f"Sized for {_fmt.num(rate)} lb/h at {_fmt.locale(bulk)} lb/ft³ and "
                f"{_fmt.fixed(fill * 100, 0)}% pocket fill",
                "Budgetary price — firm on receipt of a current vendor quote"])})
    else:
        lines.append({
            "name": "Rotary Airlock — size and price TBD", "quantity": 1,
            "unitPrice": 0, "needsPrice": True,
            "description": "\n".join([
                f"Rotary valve for {_fmt.num(rate)} lb/h at "
                f"{_fmt.locale(bulk)} lb/ft³",
                f"Needs {_fmt.fixed(per_rev, 3)} ft³/rev at {_fmt.locale(rpm)} RPM and "
                f"{_fmt.fixed(fill * 100, 0)}% fill",
                "No valve with a published displacement on file covers it — vendor "
                "to select"])})

    return {
        "calculator": "Rotary Airlock", "outputs": outputs, "warnings": warnings,
        "notes": notes, "lines": lines, "options": [],
        "total": round(sum(l["unitPrice"] for l in lines), 2),
        "source": SOURCE,
        "required": {"volumeFt3H": round(volume_ft3_h, 4),
                     "ft3PerRev": round(per_rev, 6), "rpm": rpm, "fill": fill},
        "candidates": cands,
        "selected": pick["number"] if pick else None,
    }
