#!/usr/bin/env python3
"""Dryer heat and mass balance — a rotary drum dryer run as the cooler in reverse.

cooler_heat.py takes heat out of a product with ambient air. This puts it in with
hot gas, and the same psychrometric machinery runs backwards. MCE builds the
XD-36 Mk.2 drum dryer, so this sizes that kind of machine: a direct-fired,
co-current or counter-current rotating drum.

The chain:

  1. mass balance    wet feed, dry solids, product out, water evaporated. On a
                     dryer this is the number everything else scales off, and it
                     is brutally sensitive to the inlet moisture — a point of
                     moisture on the feed is a lot of water and a lot of fuel
  2. heat demand     heating the water to boiling, evaporating it, superheating
                     the vapour to the exhaust, heating the product, and the
                     losses. Sum of five terms, each visible
  3. gas flow        the mass of gas that carries that heat between the burner
                     outlet and the exhaust, and the exhaust's own dew point
  4. fuel            natural gas or propane at the burner's efficiency
  5. drum            volumetric heat transfer the same way the rotary cooler does
                     it, with Friedman-Marshall retention, against MCE's grid

Two things this refuses to do:

  - It will not let the exhaust go below the dew point of the gas leaving it. A
    dryer whose exhaust is at its dew point rains inside the ducting and the dust
    filter, and the answer is a hotter exhaust, not a bigger fan.
  - It will not quietly evaporate more water than the gas can carry. If the
    exhaust would be saturated it says so.

Nothing here is priced. MCE has no dryer price list on file.
"""
import math

from . import _fmt
from .rotary_cooler import DRUMS, PSY, STD_MOTORS, std_motor, _div, _log, _pow

# Fuels, higher heating value.
FUELS = [("ng", "Natural gas", 1020.0, "BTU/ft³"),
         ("lp", "Propane", 91500.0, "BTU/gal"),
         ("oil", "No. 2 fuel oil", 138500.0, "BTU/gal"),
         ("biomass", "Biomass, 20% MC", 6500.0, "BTU/lb")]
FUEL_BY_ID = {f[0]: f for f in FUELS}

FLOW = [("counter", "Counter-current — gas meets the driest product"),
        ("co", "Co-current — gas meets the wettest product")]

# Heat loss through the shell as a fraction of the gross demand. A lagged drum
# runs 3-5%, bare steel outdoors much more. It is an input.
DEFAULT_SHELL_LOSS = 0.05
# Minimum margin between the exhaust and its own dew point.
MIN_DEW_MARGIN_F = 20.0
CP_WATER = 1.0                  # BTU/lb·°F
CP_VAPOR = 0.45                 # BTU/lb·°F, superheated steam near atmospheric
BOILING_F = 212.0

SOURCE = ("Mass and energy balance with ASHRAE IP psychrometrics; drum transfer "
          "per Friedman & Marshall, the same basis as the rotary cooler")


def _num(raw, default=0.0):
    try:
        v = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def latent_heat(t_f):
    """Latent heat of vaporisation at temperature, BTU/lb — the cooler's own form."""
    return 1093 - 0.556 * t_f


def dew_point_f(w, p_psia):
    """Dew point of moist air at a humidity ratio, by inverting the saturation
    curve. Bisection, because the ASHRAE saturation pressure does not invert."""
    if w <= 0:
        return -60.0
    pw = w * p_psia / (0.621945 + w)
    lo, hi = -60.0, 400.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if PSY.pws(mid) > pw:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def size(f):
    tph = _num(f.get("tph"), 10)
    units = int(_num(f.get("units"), 1)) or 1
    rate = tph * 2000 / units
    cp = _num(f.get("cp"), 0.45)
    rho = _num(f.get("rho"), 25)
    mcin = _num(f.get("mcin"), 45) / 100
    mcout = _num(f.get("mcout"), 12) / 100
    tin = _num(f.get("tin"), 60)
    tout = _num(f.get("tout"), 180)

    gas_in = _num(f.get("gasIn"), 900)
    gas_out = _num(f.get("gasOut"), 250)
    amb = _num(f.get("amb"), 60)
    amb_rh = _num(f.get("ambRh"), 60)
    elev = _num(f.get("elev"), 1000)
    flow = str(f.get("flow") or "counter")
    shell_loss = _num(f.get("shellLoss"), DEFAULT_SHELL_LOSS * 100) / 100
    fuel_id = str(f.get("fuel") or "ng")
    fuel = FUEL_BY_ID.get(fuel_id, FUEL_BY_ID["ng"])
    burner_eff = _num(f.get("burnerEff"), 0.92)

    k_ua = _num(f.get("kua"), 0.5)
    rpm = _num(f.get("rpm"), 4)
    slope = _num(f.get("slope"), 0.5)
    hold_max = _num(f.get("holdMax"), 12) / 100
    dp = _num(f.get("dp"), 2000)
    vmax = _num(f.get("vmax"), 700)

    if tph <= 0:
        return {"error": "A production rate is required."}
    if not 0 < mcin < 1:
        return {"error": "Inlet moisture has to be a wet-basis percentage under 100."}
    if mcout >= mcin:
        return {"error": "Outlet moisture is at or above inlet moisture — nothing to "
                         "dry. A dryer removes water."}
    if rho <= 0 or cp <= 0:
        return {"error": "A bulk density and a specific heat are required."}
    if gas_in <= gas_out:
        return {"error": "The gas inlet has to be hotter than the exhaust."}

    warnings, notes = [], []

    # --- 1. mass balance ---------------------------------------------------------
    dry = rate * (1 - mcin)
    product_out = _div(dry, 1 - mcout)
    water_in = rate - dry
    water_out = product_out - dry
    evaporated = water_in - water_out
    water_per_ton = _div(evaporated, tph / units)

    # --- 2. heat demand ----------------------------------------------------------
    hfg = latent_heat(BOILING_F)
    q_heat_water = evaporated * CP_WATER * max(BOILING_F - tin, 0)
    q_evaporate = evaporated * hfg
    q_superheat = evaporated * CP_VAPOR * max(gas_out - BOILING_F, 0)
    q_product = (dry + water_out) * cp * (tout - tin)
    q_net = q_heat_water + q_evaporate + q_superheat + q_product
    q_gross = _div(q_net, 1 - shell_loss)
    q_loss = q_gross - q_net

    # --- 3. gas flow --------------------------------------------------------------
    patm = PSY.patm(elev)
    w_amb = PSY.w_rh(amb, min(max(amb_rh, 1), 100) / 100, patm)
    cpg = PSY.cp(w_amb)
    gas_lb_h = _div(q_gross, cpg * (gas_in - gas_out))
    w_exhaust = w_amb + _div(evaporated, gas_lb_h)
    dew = dew_point_f(w_exhaust, patm)
    dew_margin = gas_out - dew
    rh_exhaust = PSY.rh(gas_out, w_exhaust, patm)
    acfm_exhaust = _div(gas_lb_h * PSY.v(gas_out, w_exhaust, patm), 60)
    acfm_inlet = _div(gas_lb_h * PSY.v(amb, w_amb, patm), 60)
    scfm = _div(gas_lb_h, 0.075 * 60)

    if dew_margin < 0:
        warnings.append(
            f"The exhaust at {_fmt.jsround(gas_out)} °F is BELOW its own dew point of "
            f"{_fmt.jsround(dew)} °F. That dryer rains inside the ducting and blinds "
            "the dust filter. Raise the exhaust temperature or put more gas through — "
            "a bigger fan does not fix condensation.")
    elif dew_margin < MIN_DEW_MARGIN_F:
        warnings.append(
            f"Only {_fmt.fixed(dew_margin, 0)} °F between the exhaust and its dew "
            f"point of {_fmt.jsround(dew)} °F. On a cold morning, or with a wetter "
            f"feed, it condenses. MCE wants at least {MIN_DEW_MARGIN_F:g} °F.")
    if rh_exhaust >= 1:
        warnings.append(
            "The exhaust would be saturated — the gas cannot carry this much water at "
            "that temperature. Either less water, a hotter exhaust, or more gas.")

    if flow == "co" and tout > gas_out - 20:
        warnings.append(
            f"Co-current: the product leaves with the gas, so it cannot get hotter "
            f"than the exhaust. A {_fmt.jsround(tout)} °F product against a "
            f"{_fmt.jsround(gas_out)} °F exhaust does not work — counter-current, or "
            "accept a cooler product.")
    if flow == "counter" and gas_in > 1000:
        notes.append(
            f"Counter-current at {_fmt.jsround(gas_in)} °F puts the hottest gas on the "
            "driest product. That is the efficient arrangement and the one that "
            "scorches — for anything combustible, co-current is the safer machine.")
    if gas_in > 1200:
        warnings.append(
            f"{_fmt.jsround(gas_in)} °F inlet gas on an organic product is a fire "
            "risk before it is a drying problem. Run a combustion review, and expect "
            "to need spark detection and abort gates ahead of the dust filter.")

    # --- 4. fuel ------------------------------------------------------------------
    fuel_input = _div(q_gross, burner_eff)
    fuel_rate = _div(fuel_input, fuel[2])
    btu_per_lb_water = _div(fuel_input, evaporated)
    if btu_per_lb_water > 2000:
        notes.append(
            f"{_fmt.num(btu_per_lb_water)} BTU per lb of water is high — a well-run "
            "direct-fired drum lands nearer 1,300–1,600. The exhaust temperature and "
            "the shell loss are the two dials.")

    # --- 5. drum ------------------------------------------------------------------
    lmtd_hot = gas_in - tout
    lmtd_cold = gas_out - tin
    if flow == "co":
        lmtd_hot, lmtd_cold = gas_in - tin, gas_out - tout
    lmtd = (lmtd_hot if abs(lmtd_hot - lmtd_cold) < 1e-6
            else _div(lmtd_hot - lmtd_cold, _log(_div(lmtd_hot, lmtd_cold))))
    q_vol = _div(rate, rho)
    s_slope = slope / 12
    b_factor = _div(5, math.sqrt(dp) if dp > 0 else 0)

    cands = []
    for dr in DRUMS:
        g = _div(gas_lb_h, dr["A"])
        ua = _div(k_ua * _pow(g, 0.67), dr["d"])
        v_req = _div(q_gross, ua * lmtd)
        vel = _div(acfm_exhaust, dr["A"])
        f_load = _div(dry, dr["A"])
        theta = (_div(0.23 * dr["L"], s_slope * _pow(rpm, 0.9) * dr["d"])
                 + _div(0.6 * b_factor * dr["L"] * g, f_load))
        hold = _div(theta / 60 * q_vol, dr["V"])
        util = _div(v_req, dr["V"])
        ratios = {"Thermal": util, "Gas velocity": _div(vel, vmax),
                  "Holdup": _div(hold, hold_max)}
        gov = list(ratios)[0]
        for key in list(ratios)[1:]:
            if ratios[key] > ratios[gov]:
                gov = key
        fails = [k for k in ratios if ratios[k] > 1]
        cands.append({**dr, "G": g, "Ua": ua, "Vreq": v_req, "vel": vel,
                      "theta": theta, "hold": hold, "util": util, "gov": gov,
                      "fails": fails, "ok": not fails})
    best = next((c for c in cands if c["ok"]), None)
    if not best:
        warnings.append(
            "Duty exceeds the largest drum in MCE's grid. Split the rate across "
            "parallel dryers, or take it to engineering for a purpose-built shell.")

    drive = None
    if best:
        live = best["hold"] * best["V"] * rho
        shell = 15.3 * math.pi * best["d"] * best["L"] * 1.6
        weight = live + shell
        bhp = rpm * (4.75 * best["d"] * live + 0.1925 * (best["d"] + 1) * weight
                     + 0.33 * weight) / 1e5
        drive = {"live": round(live, 2), "shell": round(shell, 2),
                 "weight": round(weight, 2), "bhp": round(bhp, 4),
                 "motor": std_motor(bhp / 0.85 * 1.15)}
        if best["theta"] < 8:
            notes.append(
                f'Retention on {best["name"]} is {_fmt.fixed(best["theta"], 1)} min. '
                "Drying is diffusion-limited inside the particle — a short retention "
                "dries the surface and leaves the core wet, and the product rewets in "
                "the bin. Slow the drum or take a longer shell.")

    outputs = [
        {"label": "Water evaporated", "headline": True,
         "value": f"{_fmt.num(evaporated)} lb/h",
         "note": f"{_fmt.fixed(mcin * 100, 1)}% → {_fmt.fixed(mcout * 100, 1)}% wb, "
                 f"{_fmt.num(water_per_ton)} lb per ton of feed"},
        {"label": "Drum", "value": (best["name"] + (f" × {units}" if units > 1 else ""))
                                   if best else "No standard drum fits"},
        {"label": "Heat demand", "value": f"{_fmt.num(q_gross / 1000)} MBH",
         "note": f"{_fmt.num(q_net / 1000)} MBH net plus "
                 f"{_fmt.fixed(shell_loss * 100, 0)}% shell loss"},
        {"label": "Fuel", "value": f"{_fmt.num(fuel_rate)} {fuel[3].split('/')[1]}/h",
         "note": f"{fuel[1]} at {_fmt.fixed(burner_eff * 100, 0)}% burner efficiency — "
                 f"{_fmt.num(btu_per_lb_water)} BTU per lb of water"},
        {"label": "Gas flow", "value": f"{_fmt.num(scfm)} SCFM",
         "note": f"{_fmt.num(acfm_exhaust)} ACFM at the {_fmt.jsround(gas_out)} °F "
                 "exhaust"},
        {"label": "Exhaust dew point", "value": f"{_fmt.jsround(dew)} °F",
         "note": f"{_fmt.fixed(dew_margin, 0)} °F of margin"},
    ]
    if best:
        outputs.append({"label": "Retention",
                        "value": f'{_fmt.fixed(best["theta"], 1)} min',
                        "note": f'{best["gov"]} governs the drum size'})
    if drive:
        outputs.append({"label": "Drum drive",
                        "value": f'{_fmt.locale(drive["motor"])} HP',
                        "note": f'{_fmt.fixed(drive["bhp"], 1)} bhp'})

    balance = [
        ("Wet feed", f"{_fmt.num(rate)} lb/h"),
        ("Dry solids", f"{_fmt.num(dry)} lb/h"),
        ("Product out", f"{_fmt.num(product_out)} lb/h"),
        ("Water in / out", f"{_fmt.num(water_in)} / {_fmt.num(water_out)} lb/h"),
        ("Water evaporated", f"{_fmt.num(evaporated)} lb/h"),
        ("Heat the water to boiling", f"{_fmt.num(q_heat_water / 1000)} MBH"),
        ("Evaporate it", f"{_fmt.num(q_evaporate / 1000)} MBH"),
        ("Superheat the vapour to exhaust", f"{_fmt.num(q_superheat / 1000)} MBH"),
        ("Heat the product", f"{_fmt.num(q_product / 1000)} MBH"),
        ("Shell loss", f"{_fmt.num(q_loss / 1000)} MBH"),
        ("Gross demand", f"{_fmt.num(q_gross / 1000)} MBH"),
        ("Gas mass flow", f"{_fmt.num(gas_lb_h)} lb/h"),
        ("Exhaust humidity ratio", f"{_fmt.num(w_exhaust * 7000)} gr/lb"),
        ("Exhaust RH", f"{_fmt.fixed(rh_exhaust * 100, 1)}%"),
        ("Counter-current LMTD" if flow == "counter" else "Co-current LMTD",
         f"{_fmt.fixed(lmtd, 1)} °F"),
    ]

    line = {"name": f'Rotary Dryer — MCE {best["name"]}' if best
                    else "Rotary Dryer — no standard drum fits",
            "quantity": units, "unitPrice": 0, "needsPrice": True,
            "description": "\n".join(filter(None, [
                f"{_fmt.locale(tph)} TPH wet feed, {_fmt.fixed(mcin * 100, 1)}% to "
                f"{_fmt.fixed(mcout * 100, 1)}% moisture — "
                f"{_fmt.num(evaporated * units)} lb/h evaporated",
                (f'{best["d"]} ft × {best["L"]} ft direct-fired '
                 f'{"counter-current" if flow == "counter" else "co-current"} drum'
                 if best else ""),
                f"{_fmt.num(q_gross / 1000)} MBH at the burner, {fuel[1].lower()}",
                f"{_fmt.num(acfm_exhaust)} ACFM exhaust at {_fmt.jsround(gas_out)} °F",
                "MCE build — no dryer price list on file"]))}

    return {
        "calculator": "Rotary Dryer", "outputs": outputs,
        "balance": [{"label": k, "value": v} for k, v in balance],
        "warnings": warnings, "notes": notes, "lines": [line], "options": [],
        "total": 0.0, "needsPrice": True, "source": SOURCE,
        "model": best["name"] if best else None, "units": units, "flow": flow,
        "mass": {"feed": round(rate, 3), "dry": round(dry, 3),
                 "productOut": round(product_out, 3), "waterIn": round(water_in, 3),
                 "waterOut": round(water_out, 3), "evaporated": round(evaporated, 3),
                 "waterPerTon": round(water_per_ton, 3)},
        "heat": {"heatWater": round(q_heat_water, 1),
                 "evaporate": round(q_evaporate, 1),
                 "superheat": round(q_superheat, 1), "product": round(q_product, 1),
                 "shellLoss": round(q_loss, 1), "net": round(q_net, 1),
                 "gross": round(q_gross, 1), "latentHeat": round(hfg, 3)},
        "gas": {"massFlow": round(gas_lb_h, 3), "scfm": round(scfm, 3),
                "acfmExhaust": round(acfm_exhaust, 3),
                "acfmInlet": round(acfm_inlet, 3),
                "humidityIn": round(w_amb, 8), "humidityOut": round(w_exhaust, 8),
                "dewPoint": round(dew, 4), "dewMargin": round(dew_margin, 4),
                "exhaustRh": round(rh_exhaust, 6), "lmtd": round(lmtd, 4),
                "patm": round(patm, 6)},
        "fuel": {"id": fuel[0], "label": fuel[1], "heatingValue": fuel[2],
                 "unit": fuel[3], "input": round(fuel_input, 1),
                 "rate": round(fuel_rate, 4),
                 "btuPerLbWater": round(btu_per_lb_water, 2),
                 "efficiency": burner_eff},
        "drive": drive,
        "candidates": [{"name": c["name"], "d": c["d"], "L": c["L"],
                        "util": round(c["util"], 6), "vel": round(c["vel"], 3),
                        "theta": round(c["theta"], 4), "hold": round(c["hold"], 8),
                        "gov": c["gov"], "ok": c["ok"], "selected": c is best}
                       for c in cands],
    }
