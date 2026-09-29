#!/usr/bin/env python3
"""Live bottom conveyance — screws drawing down the full length of a bin opening.

A live bottom is not a conveyor with a bin on top of it. A conveyor moves what is
handed to it; a live bottom feeder has to take material along the WHOLE opening,
and that is where they go wrong: a constant-pitch screw under a long slot fills up
at the back end and after that it conveys a full trough and draws nothing from the
front, so the bin ratholes over the back of the screw and the plant swears the bin
is bridging.

So this calculator answers three separate questions, and it is honest about which
of them is arithmetic and which needs data MCE has to supply:

  1. capacity      pure geometry, and exact:
                   (π/4)(D² − d²) × pitch × rpm × 60 × trough loading
  2. uniform draw  does the screw's capacity actually rise along the opening? The
                   capacity at each pitch has to grow in step with the material it
                   has already collected, which means increasing pitch, a tapered
                   shaft, or both. A constant-pitch screw under a slot longer than
                   about one diameter does not draw uniformly, and this says so.
  3. drive         the bin's own weight bears on the feeder, so a live bottom takes
                   far more torque than the same screw conveying. The vertical
                   stress at the outlet is Janssen (1895), which is published and
                   computed here. Turning that into horsepower needs CEMA's
                   material, bearing and flight factors, which are table lookups
                   MCE has not put on file — so the CEMA terms are inputs, and with
                   nothing entered the drive comes back unsized rather than guessed.

Nothing here is priced. Screws are a bought item and _vendor.SCREW_QUOTES is where
a price comes from.
"""
import math

from . import _fmt

# Janssen's lateral stress ratio. 0.4 is the usual design value for a bin in the
# filling (active) state; a discharging bin sees more.
K_JANSSEN = 0.4
JANSSEN_SOURCE = "Janssen (1895) silo stress; K = 0.4, active state"

# Trough loading. A feeder under a bin runs full by definition — the load is what
# the bin puts in it, not what a feed chute meters. The CEMA loadings (15/30/45%)
# are for a CONVEYOR, and using one here is the classic way to undersize a live
# bottom by a factor of two.
LOADING_PRESETS = [("1.0", "100% — a feeder under a bin runs full"),
                   ("0.9", "90% — some freeboard at the discharge end"),
                   ("0.45", "45% — conveyor loading (only past the opening)")]
DEFAULT_LOADING = 1.0

# Screw peripheral speed. Feeders run slowly; fast flights grind product and wear.
MAX_TIP_FPM = 100

# A single increasing-pitch screw stops making sense somewhere around 2.5:1 —
# past that the last flights are so open they stop conveying and start
# stirring. Past it the answer is a tapered shaft or another screw.
MAX_PITCH_RATIO = 2.5

TAPER_STYLES = [
    ("pitch", "Increasing pitch — cheapest, most common"),
    ("shaft", "Tapered shaft (cone), constant pitch"),
    ("both", "Tapered shaft and increasing pitch"),
    ("none", "Constant pitch and shaft — conveyor geometry"),
]
SOURCE = ("Screw capacity from flight geometry; bin load from Janssen (1895); "
          "drive factors per CEMA Book No. 350 where MCE supplies them")


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


def flight_volume_ft3(screw_od_in, shaft_od_in, pitch_in):
    """Volume swept by one turn of flight, ft³."""
    d = screw_od_in / 12.0
    s = shaft_od_in / 12.0
    p = pitch_in / 12.0
    return math.pi / 4 * (d * d - s * s) * p


def janssen_vertical_psf(bulk_density, head_ft, hyd_radius_ft, wall_friction,
                         k=K_JANSSEN):
    """Vertical stress at depth, lb/ft². Saturates with depth — which is the whole
    point of Janssen and the reason a tall bin does not crush its feeder."""
    if wall_friction <= 0 or hyd_radius_ft <= 0:
        return bulk_density * head_ft          # no wall support: full head
    limit = bulk_density * hyd_radius_ft / (wall_friction * k)
    return limit * (1 - math.exp(-wall_friction * k * head_ft / hyd_radius_ft))


def size(f):
    rate_tph = _num(f.get("tph"), 20)
    rate = _num(f.get("rate")) or rate_tph * 2000
    bulk = _num(f.get("bulkDensity"), 35)

    screw_od = _num(f.get("screwOd"), 12)
    shaft_od = _num(f.get("shaftOd"), 2.5)
    pitch = _num(f.get("pitch"), screw_od)          # standard pitch = diameter
    rpm = _num(f.get("rpm"), 20)
    loading = _num(f.get("loading"), DEFAULT_LOADING)
    screws = int(_num(f.get("screws"), 1)) or 1
    taper = str(f.get("taper") or "pitch")
    pitch_ratio = _num(f.get("pitchRatio"), 0)      # last pitch / first pitch

    opening_l = _num(f.get("openingLength"), 0)
    opening_w = _num(f.get("openingWidth"), 0)
    head = _num(f.get("headHeight"), 0)
    wall_friction = _num(f.get("wallFriction"), 0.45)

    # CEMA drive terms — table lookups MCE has not put on file
    fd = _opt(f.get("cemaFd"))
    fb = _opt(f.get("cemaFb"))
    ff = _opt(f.get("cemaFf"))
    fm = _opt(f.get("cemaFm"))
    fp = _opt(f.get("cemaFp"))
    fo = _num(f.get("cemaFo"), 1.0) or 1.0
    eff = _num(f.get("driveEff"), 0.88) or 0.88
    length = _num(f.get("screwLength"), opening_l)

    if rate <= 0:
        return {"error": "A draw-down rate is required — either lb/h or TPH."}
    if bulk <= 0:
        return {"error": "A bulk density is required."}
    if screw_od <= 0 or pitch <= 0 or rpm <= 0:
        return {"error": "A screw diameter, a pitch and a speed are required."}
    if shaft_od >= screw_od:
        return {"error": "The centre pipe cannot be as large as the screw."}
    if not 0 < loading <= 1:
        return {"error": "Trough loading is a fraction between 0 and 1."}

    warnings, notes = [], []

    # --- capacity ---------------------------------------------------------------
    per_rev = flight_volume_ft3(screw_od, shaft_od, pitch)
    per_screw_ft3_h = per_rev * rpm * 60 * loading
    total_ft3_h = per_screw_ft3_h * screws
    total_lb_h = total_ft3_h * bulk
    required_ft3_h = rate / bulk
    utilisation = required_ft3_h / total_ft3_h if total_ft3_h else float("inf")
    tip_fpm = math.pi * (screw_od / 12) * rpm

    if total_lb_h < rate:
        warnings.append(
            f"The screws move {_fmt.num(total_lb_h)} lb/h and the duty is "
            f"{_fmt.num(rate)} lb/h. Bigger screws, more of them, or more speed.")
    if tip_fpm > MAX_TIP_FPM:
        notes.append(
            f"Flight tip speed is {_fmt.fixed(tip_fpm, 0)} ft/min, above the "
            f"{MAX_TIP_FPM} ft/min a feeder normally runs at. Fast flights grind "
            "product and wear; slow the screw and take a bigger one.")
    if loading > 0.5 and not opening_l:
        notes.append(
            "Running at feeder loading with no opening stated. If this screw is past "
            "the bin and simply conveying, take conveyor loading instead — it will "
            "not run full.")

    # --- uniform draw-down ------------------------------------------------------
    draw = None
    if opening_l > 0:
        turns = opening_l / (pitch / 12)
        slot_ratio = opening_l / (screw_od / 12)
        # capacity has to grow in step with what has already been collected, so the
        # last turn under the opening must swallow the whole rate and the first only
        # its own share. For increasing pitch that is a pitch ratio of about the
        # number of turns.
        needed_ratio = turns if turns > 1 else 1.0
        draw = {"turnsUnderOpening": round(turns, 2),
                "slotToDiameter": round(slot_ratio, 2),
                "pitchRatioNeeded": round(needed_ratio, 2),
                "pitchRatioGiven": pitch_ratio or None, "style": taper}
        if taper == "none" and slot_ratio > 1:
            warnings.append(
                f"Constant pitch and shaft under an opening {_fmt.fixed(slot_ratio, 1)} "
                "screw diameters long. The trough fills at the back and the front of "
                "the slot draws nothing — the bin will rathole and everyone will call "
                "it a bridging problem. Use increasing pitch, a tapered shaft, or both.")
        elif taper == "pitch" and pitch_ratio and pitch_ratio < needed_ratio * 0.7:
            warnings.append(
                f"Pitch grows {_fmt.fixed(pitch_ratio, 2)}× over the opening but needs "
                f"roughly {_fmt.fixed(needed_ratio, 2)}× to draw evenly across "
                f"{_fmt.fixed(turns, 1)} turns. The back of the slot will do most of "
                "the work.")
        elif taper == "pitch" and not pitch_ratio:
            notes.append(
                f"Increasing pitch selected but no ratio given. Across "
                f"{_fmt.fixed(turns, 1)} turns under the opening the last pitch wants "
                f"to be about {_fmt.fixed(needed_ratio, 2)}× the first.")
        if needed_ratio > MAX_PITCH_RATIO:
            notes.append(
                f"Drawing evenly across {_fmt.fixed(turns, 1)} turns with pitch alone "
                f"wants {_fmt.fixed(needed_ratio, 1)}:1, and a single screw tops out "
                f"around {MAX_PITCH_RATIO}:1 before the flight geometry stops making "
                "sense. Add a tapered shaft, shorten the slot, or split it across "
                "more screws.")
        if slot_ratio > 6:
            notes.append(
                f"An opening {_fmt.fixed(slot_ratio, 1)} diameters long is a lot to "
                "draw with one screw even tapered. Two shorter screws side by side, "
                "or a larger diameter, usually behaves better.")

    # --- what the bin puts on the feeder ---------------------------------------
    bin_load = None
    if opening_l > 0 and opening_w > 0 and head > 0:
        area = opening_l * opening_w
        perimeter = 2 * (opening_l + opening_w)
        hyd_radius = area / perimeter
        sigma_v = janssen_vertical_psf(bulk, head, hyd_radius, wall_friction)
        full_head = bulk * head
        load_lb = sigma_v * area
        bin_load = {"openingArea": round(area, 4),
                    "hydraulicRadius": round(hyd_radius, 4),
                    "verticalStressPsf": round(sigma_v, 2),
                    "fullHeadPsf": round(full_head, 2),
                    "loadLb": round(load_lb, 1),
                    "wallSupport": round(1 - sigma_v / full_head, 4)
                                   if full_head else None,
                    "source": JANSSEN_SOURCE}
        notes.append(
            f"Janssen puts {_fmt.num(sigma_v)} lb/ft² on the outlet — "
            f"{_fmt.num(load_lb)} lb over the opening — against "
            f"{_fmt.num(full_head)} lb/ft² if the full head bore on it. The walls "
            "carry the rest. That load is what a live bottom drive has to shear, "
            "and it is why a feeder takes several times the power of the same screw "
            "conveying.")
    elif opening_l > 0:
        notes.append(
            "Give the opening width and the head height and the bin load on the "
            "feeder comes back too — it is what actually sizes the drive.")

    # --- drive -------------------------------------------------------------------
    drive = None
    have_cema = all(x is not None for x in (fd, fb, ff, fm, fp)) and length > 0
    if have_cema:
        hp_friction = length * rpm * fd * fb / 1e6
        hp_material = total_ft3_h * length * bulk * ff * fm * fp / 1e6
        hp_total = (hp_friction + hp_material) * fo / eff
        drive = {"hpFriction": round(hp_friction, 4),
                 "hpMaterial": round(hp_material, 4),
                 "hpTotal": round(hp_total, 4),
                 "basis": "CEMA Book No. 350, factors as supplied"}
        notes.append(
            "The CEMA figure is a CONVEYOR horsepower. A live bottom also shears the "
            "bin load above, which CEMA does not cover — the screw vendor sizes the "
            "drive against the actual bin, and it lands well above this.")
    else:
        warnings.append(
            "Drive not sized. CEMA's horsepower needs the diameter, bearing, flight, "
            "material and paddle factors (Book No. 350) and MCE has none of them on "
            "file. Enter them, or take the drive from the screw vendor — which is the "
            "better answer on a live bottom anyway, since CEMA does not cover the bin "
            "load.")

    outputs = [
        {"label": "Draw-down capacity", "headline": True,
         "value": f"{_fmt.num(total_lb_h)} lb/h",
         "note": f"{_fmt.num(total_ft3_h)} ft³/h across "
                 f"{screws} screw{'s' if screws != 1 else ''}"},
        {"label": "Duty", "value": f"{_fmt.num(rate)} lb/h",
         "note": f"{_fmt.fixed(utilisation * 100, 0)}% of capacity"
                 if math.isfinite(utilisation) else ""},
        {"label": "Screw", "value": f'{_fmt.locale(screw_od)}" dia × '
                                    f'{_fmt.locale(pitch)}" pitch at '
                                    f"{_fmt.locale(rpm)} RPM"},
        {"label": "Per revolution", "value": f"{_fmt.fixed(per_rev, 4)} ft³"},
        {"label": "Flight tip speed", "value": f"{_fmt.fixed(tip_fpm, 0)} ft/min"},
    ]
    if draw:
        outputs.append({"label": "Opening",
                        "value": f'{_fmt.fixed(draw["slotToDiameter"], 1)} screw '
                                 f'diameters, {_fmt.fixed(draw["turnsUnderOpening"], 1)} turns'})
    if bin_load:
        outputs.append({"label": "Bin load on the feeder",
                        "value": f'{_fmt.num(bin_load["loadLb"])} lb',
                        "note": f'{_fmt.num(bin_load["verticalStressPsf"])} lb/ft² '
                                "(Janssen)"})
    if drive:
        outputs.append({"label": "Conveying horsepower",
                        "value": f'{_fmt.fixed(drive["hpTotal"], 2)} HP',
                        "note": "CEMA conveying only — the bin load is on top"})

    line = {"name": f'Live Bottom — {screws} × {_fmt.locale(screw_od)}" screw',
            "quantity": 1, "unitPrice": 0, "needsPrice": True,
            "description": "\n".join(filter(None, [
                f"Live bottom screw feeder, {_fmt.num(rate)} lb/h of material at "
                f"{_fmt.locale(bulk)} lb/ft³",
                f'{screws} × {_fmt.locale(screw_od)}" dia screw on '
                f'{_fmt.locale(shaft_od)}" pipe, {_fmt.locale(pitch)}" pitch at '
                f"{_fmt.locale(rpm)} RPM",
                (f'{_fmt.locale(opening_l)} ft opening, '
                 + {"pitch": "increasing pitch", "shaft": "tapered shaft",
                    "both": "tapered shaft and increasing pitch",
                    "none": "constant pitch and shaft"}[taper] if opening_l else ""),
                "Drive and price by the screw vendor against the actual bin load"]))}

    return {
        "calculator": "Live Bottom Conveyance", "outputs": outputs,
        "warnings": warnings, "notes": notes, "lines": [line], "options": [],
        "total": 0.0, "needsPrice": True, "source": SOURCE,
        "capacity": {"perRevFt3": round(per_rev, 8),
                     "perScrewFt3H": round(per_screw_ft3_h, 4),
                     "totalFt3H": round(total_ft3_h, 4),
                     "totalLbH": round(total_lb_h, 2),
                     "requiredFt3H": round(required_ft3_h, 4),
                     "utilisation": (round(utilisation, 6)
                                     if math.isfinite(utilisation) else None),
                     "tipFpm": round(tip_fpm, 3), "screws": screws},
        "draw": draw, "binLoad": bin_load, "drive": drive,
    }
