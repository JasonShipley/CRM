#!/usr/bin/env python3
"""Hammermill + plenum sizing — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/hammermill-sizing-calculator.html (served whole
at /tools/hammermill). Every table it uses is extracted verbatim into _data.py;
the arithmetic below mirrors that file's compute() step for step so the form
builder and the standalone calculator can never disagree.

Sizing chain:
    HP        = PPH / index / screen-64ths        -> next standard motor
    screen    = motor HP x in2/HP                 -> smallest XM mill in family
    plenum    = mill screen area x 1.3 CFM        -> flange area at design velocity
    feeder    = PPH / 60 / density / (cu ft/rev x 0.9 pocket fill)
    screw     = PPH / density                     -> first table row that carries it
    price     = Bliss basis x multiplier, plenum by weight x $/lb
"""
import math

from . import _vendor
from ._fmt import jsround, money, num
from ._data import (FAMILY_SETS, FEEDER_10, FEEDER_14, FEEDER_PRICING,
                    MCE_XM_MILLS, MILL_PRICING, MOTOR_SIZES, PLENUM_V_IDX,
                    PRODUCTS, ROTOR_INFO, SCREW_TABLES, TROUGH_LABELS,
                    WIDTH_TO_ROW, XM_CHART)

# Rotary feeders are sized at 90% pocket fill — catalog cu ft/rev is rated at
# 100%, but it's not a perfect world.
POCKET_FILL = 0.90
IDEAL_RPM_MIN, IDEAL_RPM_MAX = 20, 30
STANDARD_LENGTH_MIN = 10        # screw conveyors ship in whole feet, 10 ft minimum
PLENUM_CFM_PER_IN2 = 1.3
BLISS_RATE_LB = 8.80


def next_motor_hp(hp):
    for s in MOTOR_SIZES:
        if s >= hp - 1e-9:
            return s
    return math.ceil(hp)


def family_of(model):
    return model.replace("XM-", "")[:2]


def size_code_of(model):
    return int(model.replace("XM-", "")[2:])


def _num(raw, default):
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return default
    return v


def size(f):
    """Run the calculator. `f` is the raw form dict; unknown keys are ignored."""
    pph = _num(f.get("pph"), 0)
    screen64 = _num(f.get("screen64"), 0)
    index = _num(f.get("index"), 0)
    sq_in_hp = _num(f.get("sqInHp"), 0)
    density = _num(f.get("bulkDensity"), 0)
    family = f.get("family") if f.get("family") in FAMILY_SETS else "grain"
    velocity = str(int(_num(f.get("plenumVelocity"), 300)))
    if velocity not in PLENUM_V_IDX:
        velocity = "300"
    trough = f.get("trough") if f.get("trough") in SCREW_TABLES else "45"
    feeder_dia = "14" if str(f.get("feederDia")) == "14" else "10"
    cup_type = f.get("cupType") if f.get("cupType") in ("nylon", "ss", "tt") else "nylon"
    magnet_clean = f.get("magnetClean") if f.get("magnetClean") in ("sma", "scmam", "scmaa") else "sma"
    run_length = _num(f.get("runLength"), 0)
    mill_mult = _num(f.get("millMult"), 1.73)
    feeder_mult = _num(f.get("feederMult"), 2.00)
    plenum_duty = _num(f.get("plenumDuty"), 1.35)
    plenum_rate = _num(f.get("plenumRate"), 15.25)

    errors, warnings, outputs = [], [], []
    if pph <= 0:
        errors.append("Capacity (PPH) is required.")
    if screen64 <= 0:
        errors.append("Screen size in 64ths is required.")
    if index <= 0:
        errors.append("Grinding index is required.")
    if sq_in_hp <= 0:
        errors.append("Screen area per HP is required.")
    if errors:
        return {"error": " ".join(errors)}

    # --- HP and required screen area -----------------------------------------
    hp = pph / index / screen64
    motor_hp = next_motor_hp(hp)
    area_req = motor_hp * sq_in_hp
    formula = (f"{num(pph)} PPH ÷ {index:g} (index) ÷ {screen64:g} (64ths) = {num(hp, 1)} HP "
               f"→ {motor_hp:g} HP motor × {sq_in_hp:g} in²/HP = {num(area_req)} in²")

    # --- mill match ------------------------------------------------------------
    pool = sorted((m for m in MCE_XM_MILLS if family_of(m["model"]) in FAMILY_SETS[family]),
                  key=lambda m: m["area"])
    auto = next((m for m in pool if m["area"] >= area_req), pool[-1])
    manual = f.get("millModel") or ""
    mill = next((m for m in MCE_XM_MILLS if m["model"] == manual), None) or auto
    is_manual = mill["model"] != auto["model"]

    headroom_pct = jsround((mill["area"] - area_req) / mill["area"] * 100)
    hp_headroom_pct = jsround((mill["hpMax"] - motor_hp) / mill["hpMax"] * 100)
    hp_in_range = mill["hpMin"] <= motor_hp <= mill["hpMax"]
    area_ok = mill["area"] >= area_req
    if not area_ok:
        warnings.append(
            f"Screen area is {num(area_req - mill['area'])} in² short of the "
            f"{num(area_req)} in² requirement — check the next size up.")
    if not hp_in_range:
        warnings.append(
            f"A {motor_hp:g} HP motor falls outside {mill['model']}'s rated "
            f"{mill['hpMin']}–{mill['hpMax']} HP range.")
    if area_ok and hp_in_range and headroom_pct < 5:
        warnings.append(f"{headroom_pct}% screen-area headroom — tight fit with a "
                        f"{motor_hp:g} HP motor.")
    if is_manual:
        warnings.append(f"{mill['model']} was picked by hand; the auto match is {auto['model']}.")

    fam = family_of(mill["model"])
    rotor = ROTOR_INFO[fam]
    outputs += [
        {"label": "Calculated HP", "value": f"{num(hp, 1)} HP"},
        {"label": "Motor size", "value": f"{motor_hp:g} HP", "headline": True},
        {"label": "Screen area required", "value": f"{num(area_req)} in²"},
        {"label": "Mill", "value": mill["model"], "headline": True},
        {"label": "Mill screen area", "value": f"{mill['area']:,} in² ({mill['screenSize']})"},
        {"label": "Screen-area headroom", "value": f"{headroom_pct}%"},
        {"label": "HP headroom", "value": f"{hp_headroom_pct}% — {motor_hp:g}/{mill['hpMax']} HP"},
        {"label": "Rotor", "value": f'{fam}" @ {rotor["rpm"]:,} RPM ({rotor["tip"]} FPM tip)'},
        {"label": "Bearing", "value": mill["bearing"]},
        {"label": "Magnet width", "value": f'{mill["magnet"]}"'},
    ]

    # --- feeder ----------------------------------------------------------------
    table = FEEDER_14 if feeder_dia == "14" else FEEDER_10
    auto_row = WIDTH_TO_ROW.get(str(size_code_of(mill["model"])))
    row_count = int(_num(f.get("rowCount"), auto_row or table[0]["rows"]))
    feeder = next((r for r in table if r["rows"] == row_count), None)
    feeder_rpm = None
    if feeder and density > 0:
        cuft = feeder["cuft"] if feeder_dia == "14" else (
            feeder["nylon"] if cup_type == "nylon" else feeder["ss"])
        eff_cuft = cuft * POCKET_FILL
        feeder_rpm = pph / 60 / density / eff_cuft
        if feeder_rpm < IDEAL_RPM_MIN:
            warnings.append(f"Feeder shaft speed {num(feeder_rpm, 1)} RPM is below the ideal "
                            f"{IDEAL_RPM_MIN}–{IDEAL_RPM_MAX} RPM band — it may surge.")
        elif feeder_rpm > IDEAL_RPM_MAX:
            warnings.append(f"Feeder shaft speed {num(feeder_rpm, 1)} RPM is above the ideal "
                            f"{IDEAL_RPM_MIN}–{IDEAL_RPM_MAX} RPM band — consider a larger feeder.")
        outputs += [
            {"label": "Rotary feeder",
             "value": f'{feeder_dia}" dia, {feeder["rows"]}-row, {feeder["width"]} wide'},
            {"label": "Feeder shaft speed", "value": f"{num(feeder_rpm, 1)} RPM"},
            {"label": "Feeder drive", "value": f'{feeder["hp"]} HP'},
        ]
    elif density <= 0:
        warnings.append("Bulk density is needed to size the feeder and the screw conveyor.")

    # --- plenum ----------------------------------------------------------------
    cfm = mill["area"] * PLENUM_CFM_PER_IN2
    flange_area = cfm / float(velocity)
    outputs += [
        {"label": "Plenum airflow", "value": f"{num(cfm)} CFM", "headline": True},
        {"label": "Plenum flange area", "value": f"{num(flange_area, 2)} ft² @ {velocity} FPM"},
    ]
    plenum_formula = (f"{mill['area']:,} in² × {PLENUM_CFM_PER_IN2} = {num(cfm)} CFM ÷ "
                      f"{velocity} FPM = {num(flange_area, 2)} ft²")

    # --- screw conveyor --------------------------------------------------------
    min_len_ft = mill["glen"] / 12.0
    total_len_ft = min_len_ft + run_length
    std_len_ft = max(jsround(total_len_ft), STANDARD_LENGTH_MIN)
    screw = None
    if density > 0:
        cuft_hr = pph / density
        rows = SCREW_TABLES[trough]
        screw = next((r for r in rows if r["atMax"] >= cuft_hr), None)
        if screw is None:
            screw = rows[-1]
            warnings.append(
                f'{num(cuft_hr)} ft³/hr exceeds the 36" screw at '
                f"{TROUGH_LABELS[trough].lower()} — this needs a larger screw, dual "
                "conveyors, or a higher trough loading if the product allows it.")
        screw_rpm = cuft_hr / screw["at1"]
        outputs += [
            {"label": "Screw conveyor", "value": f'{screw["dia"]}" dia'},
            {"label": "Screw speed",
             "value": f'{num(screw_rpm, 1)} RPM (max {screw["maxRpm"]} at '
                      f'{TROUGH_LABELS[trough].lower()})'},
            {"label": "Conveyed volume", "value": f"{num(cuft_hr)} ft³/hr"},
            {"label": "Screw length",
             "value": f'{std_len_ft} ft standard ({num(min_len_ft, 1)} ft to the plenum '
                      f'flange + {num(run_length, 1)} ft run)'},
        ]

    # --- pricing ---------------------------------------------------------------
    price = MILL_PRICING.get(mill["model"])
    lines, price_notes = [], []
    total = 0.0
    if price and mill_mult > 0:
        mill_price = price["bliss"] * mill_mult
        total += mill_price
        crm_delta = (price["crm"] - mill_price) / mill_price * 100
        price_notes.append(
            f"Mill: ${price['bliss']:,} Bliss basis × {mill_mult:.2f} = {money(mill_price)} "
            f"(CRM list ${price['crm']:,}, {crm_delta:+.0f}%)"
            + (" · closest Bliss frame, not an exact match" if price["analog"] else ""))
        if crm_delta < -1:
            warnings.append(
                f"CRM list (${price['crm']:,}) is {abs(crm_delta):.0f}% below the current "
                f"basis price for {mill['model']} — the CRM price is lagging.")

        desc = [
            f"{mill['model']} hammermill — {mill['screenSize']} screen, "
            f"{mill['area']:,} in² open area",
            f"{motor_hp:g} HP motor ({mill['hpMin']}–{mill['hpMax']} HP rated range), "
            f"{headroom_pct}% screen-area headroom",
            f'{fam}" rotor at {rotor["rpm"]:,} RPM, {rotor["tip"]} FPM tip speed',
            f'{mill["bearing"]} bearings, {mill["magnet"]}" magnet',
            f"Sized for {num(pph)} PPH at index {index:g} through a "
            f"{screen64:g}/64\" ({screen64 / 64:.3f}\") screen",
        ]
        if price["analog"]:
            desc.append("Price basis is the closest Bliss frame — confirm before issue")
        lines.append({"name": f"{mill['model']} Hammermill", "quantity": 1,
                      "unitPrice": round(mill_price, 2), "sku": mill["model"],
                      "description": "\n".join(desc)})

        feeder_price = None
        try:
            f_idx = FEEDER_PRICING["rows"].index(row_count)
        except ValueError:
            f_idx = -1
        if feeder and f_idx >= 0 and feeder_mult > 0:
            dia_key = "d14" if feeder_dia == "14" else "d10"
            base = FEEDER_PRICING[dia_key][cup_type][f_idx]
            clean_add = FEEDER_PRICING["clean"][magnet_clean][f_idx]
            feeder_price = (base + clean_add) * feeder_mult
            total += feeder_price
            price_notes.append(
                f"Feeder: (${base:,} + ${clean_add:,} magnet/cleanout) × {feeder_mult:.2f} "
                f"= {money(feeder_price)}")
            lines.append({
                "name": f'{feeder_dia}" Rotary Feeder — {feeder["rows"]}-row',
                "quantity": 1, "unitPrice": round(feeder_price, 2),
                "description": "\n".join([
                    f'{feeder["rows"]}-row, {feeder["width"]} wide, {cup_type} cups',
                    (f"{num(feeder_rpm, 1)} RPM shaft speed at {num(pph)} PPH and "
                     f"{density:g} lb/ft³, figured at 90% pocket fill"
                     if feeder_rpm else "Shaft speed pending bulk density"),
                    f'{feeder["hp"]} HP drive',
                    f'Includes {mill["magnet"]}" magnet and cleanout',
                ])})

        w_bliss = price["pw"][PLENUM_V_IDX[velocity]]
        w_duty = w_bliss * plenum_duty
        plenum_price = w_duty * plenum_rate
        total += plenum_price
        price_notes.append(
            f"Plenum: {w_bliss:,} lb × {plenum_duty:.2f} duty = {num(w_duty)} lb × "
            f"${plenum_rate:.2f}/lb = {money(plenum_price)} "
            f"(Bliss 2017 basis {money(w_bliss * BLISS_RATE_LB)})")
        lines.append({
            "name": f"Plenum Chamber — {mill['model']}", "quantity": 1,
            "unitPrice": round(plenum_price, 2),
            "description": "\n".join([
                f"{num(cfm)} CFM at {velocity} FPM design velocity",
                f"{num(flange_area, 2)} ft² discharge flange open area",
                f"{num(w_duty)} lb fabricated weight at {plenum_duty:.2f} duty factor",
                f'Discharge screw flange {num(min_len_ft, 1)} ft from the mill ("G" dimension)',
            ])})

        if screw:
            screw_cost, screw_notes = _vendor.screw_cost(screw["dia"], std_len_ft)
            screw_price = screw_cost * _vendor.SCREW_MARKUP
            price_notes.append(
                f'Screw: modelled SCC cost {money(screw_cost)} × '
                f"{_vendor.SCREW_MARKUP:.3f} = {money(screw_price)} "
                f"(1/{_vendor.SCREW_DIVISOR:g} plus {_vendor.SCREW_COVER - 1:.0%} cover)")
            warnings.append(
                f'The {screw["dia"]}" × {std_len_ft} ft screw is a modelled budget from '
                f"MCE's {len(_vendor.SCREW_QUOTES)} SCC quotations, not a quote for this "
                "unit — have SCC price the actual configuration before release.")
            for note in screw_notes:
                warnings.append(f"Screw budget: {note}.")
            lines.append({
                "name": f'{screw["dia"]}" Screw Conveyor — {std_len_ft} ft',
                "quantity": 1, "unitPrice": round(screw_price, 2),
                "description": "\n".join([
                    f'{screw["dia"]}" dia at {TROUGH_LABELS[trough].lower()}',
                    f"{num(cuft_hr)} ft³/hr at {num(pph)} PPH and {density:g} lb/ft³",
                    f'{std_len_ft} ft standard length ({num(min_len_ft, 1)} ft to the '
                    f"plenum flange + {num(run_length, 1)} ft to the discharge point)",
                    f"Mating flange must give at least {num(flange_area, 2)} ft² open area",
                    "Complete with drive motor, reducer, guard and approval drawings",
                ])})

    else:
        warnings.append(f"No price basis on file for {mill['model']}.")

    lines_total = sum(l.get("unitPrice") or 0 for l in lines)
    return {
        "calculator": "Hammermill + Plenum",
        "outputs": outputs,
        "warnings": warnings,
        "lines": lines,
        # `package_total` is what MCE's own calculator totals — mill, feeder and
        # plenum. `total` is every priced line, including the screw conveyor,
        # which comes from a vendor quote the original never carried.
        "package_total": round(total, 2),
        "total": round(lines_total, 2),
        "formula": formula,
        "plenum_formula": plenum_formula,
        "price_notes": price_notes,
        "mill": mill["model"],
        "plenum_cfm": round(cfm),
        "screen_area": round(mill["area"]),
        "chart": XM_CHART.get(_product_name(f), None),
    }


def _product_name(f):
    try:
        return PRODUCTS[int(f.get("product", 0))]["name"]
    except (TypeError, ValueError, IndexError):
        return ""
