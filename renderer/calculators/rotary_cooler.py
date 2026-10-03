#!/usr/bin/env python3
"""Rotary cooler sizing — a port of MCE's direct air-swept drum calculator.

cooler.py sizes a counterflow bed off MCE's capacity tables. cooler_heat.py
verifies either arrangement thermally. This one sizes the third machine: a
direct air-swept rotating drum, counter-current, which is what MCE builds for
biochar, torrefied biomass, DDGS, fertilizer and mineral products that a bed
cooler cannot hold.

The chain the calculator runs, in its own order:

  1. design ambient    ASHRAE IP psychrometrics at the site's barometric pressure
  2. moisture          feed, dry solids, water evaporated in the drum
  3. heat balance      product heat released, latent credit, sensible to the air,
                       and the achievable outlet floor the ambient allows
  4. airflow           the largest of three: thermal, moisture-carrying capacity
                       at a maximum exhaust RH, and a sweep-air minimum
  5. drum selection    every drum in MCE's proposed grid against three limits —
                       thermal volume, superficial air velocity and holdup — with
                       the first that clears all three as the pick
  6. prediction        eps-NTU on the selected drum at any ambient
  7. drive and fan     rotating load and drum drive HP, then the exhaust fan with
                       a cold-start check
  8. summer sweep      predicted product outlet across the ambient range

Ported faithfully, including the parts that are estimates: the volumetric heat
transfer coefficient is the Friedman-Marshall rotary dryer correlation, the
retention time is their holdup equation, and the drive horsepower is a standard
rotating-load formula. tests/test_ports.py diffs it against the original.
"""
import math

from . import _fmt

STD_MOTORS = [1, 1.5, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125,
              150, 200, 250, 300, 350, 400]

PRESETS = [
    {"id": "feed", "label": "Feed pellets", "cp": 0.45, "rho": 40, "tin": 180,
     "tout": 105, "mcin": 15, "mcout": 12.5, "dp": 4000, "vmax": 800},
    {"id": "wood", "label": "Wood pellets", "cp": 0.40, "rho": 40, "tin": 190,
     "tout": 105, "mcin": 8, "mcout": 6.5, "dp": 6000, "vmax": 800},
    {"id": "biochar", "label": "Biochar", "cp": 0.30, "rho": 15, "tin": 500,
     "tout": 120, "mcin": 2, "mcout": 2, "dp": 1500, "vmax": 350},
    {"id": "torr", "label": "Torrefied biomass", "cp": 0.35, "rho": 18, "tin": 450,
     "tout": 130, "mcin": 2, "mcout": 2, "dp": 3000, "vmax": 400},
    {"id": "chips", "label": "Dried wood chips / sawdust", "cp": 0.40, "rho": 12,
     "tin": 200, "tout": 110, "mcin": 12, "mcout": 10, "dp": 2000, "vmax": 450},
    {"id": "ddgs", "label": "DDGS", "cp": 0.45, "rho": 30, "tin": 200, "tout": 110,
     "mcin": 12, "mcout": 10, "dp": 800, "vmax": 500},
    {"id": "fert", "label": "Fertilizer granules", "cp": 0.35, "rho": 65, "tin": 220,
     "tout": 110, "mcin": 1.5, "mcout": 1.0, "dp": 2500, "vmax": 700},
    {"id": "sand", "label": "Sand / mineral aggregate", "cp": 0.20, "rho": 100,
     "tin": 300, "tout": 140, "mcin": 0.5, "mcout": 0.2, "dp": 600, "vmax": 900},
    {"id": "custom", "label": "Custom (enter values)"},
]
PRESET_BY_ID = {p["id"]: p for p in PRESETS}

# Calibrated so this sizing method reproduces Insta-Pro's Model 900 rating
# exactly: a 4 ft × 8 ft drum cooling 4,000 lb/h of soy meal from 250 °F to
# 120 °F on a 100 °F / 40 % RH day (their "100 °F ambient maximum"; 120 °F is
# what cooler_heat.py's ×2.9 calibration predicts for that drum there). Jason,
# 2026-10-03: "We need to basically be at the same thing they are at because
# it works." 3.36 is Friedman-Marshall's 0.5 × 6.7 (3.351 exactly, rounded up so the 4 × 8 passes) — more than the heat
# balance's 2.9 because this method carries its own conservatism (15 %
# margin, LMTD on a planned exhaust), which the calibration now absorbs.
# The page this is ported from shipped 0.5; its default moved with it.
K_UA_DEFAULT = 3.36

# MCE's proposed rotary cooler grid: diameter (ft) -> lengths (ft)
GRID = {3: [12, 16, 20, 24, 30], 4: [16, 20, 24, 30, 36],
        5: [20, 24, 30, 36, 40, 50], 6: [24, 30, 36, 40, 50, 60],
        7: [30, 36, 40, 50, 60, 70], 8: [40, 50, 60, 70, 80],
        9: [50, 60, 70, 80, 90], 10: [50, 60, 70, 80, 100],
        12: [60, 70, 80, 100, 120]}
DRUMS = []
for _d, _lengths in GRID.items():
    for _L in _lengths:
        _A = math.pi * _d * _d / 4
        DRUMS.append({"d": _d, "L": _L, "name": f"RC {_d}×{_L}", "A": _A, "V": _A * _L})
DRUMS.sort(key=lambda x: (x["V"], x["d"]))

# Short, tumble-cooler drums at Insta-Pro's proportions (L/D about 2-3: the
# 700 is 3 × 6, the 900 4 × 8), added to the cooler's selection so a duty that
# a 4 × 8 handles in the field is not sold as a 4 × 16 (Jason, 2026-10-03).
# Coolers only — dryer.py selects from DRUMS, which these stay out of.
SHORT_GRID = {3: [6, 8, 10], 4: [8, 10, 12], 5: [10, 12, 16]}
COOLER_DRUMS = list(DRUMS)
for _d, _lengths in SHORT_GRID.items():
    for _L in _lengths:
        _A = math.pi * _d * _d / 4
        COOLER_DRUMS.append({"d": _d, "L": _L, "name": f"RC {_d}×{_L}", "A": _A,
                             "V": _A * _L})
COOLER_DRUMS.sort(key=lambda x: (x["V"], x["d"]))

HUM_MODES = [("wb", "Wet bulb, °F"), ("rh", "Relative humidity, %")]
SWEEP_MODES = [("w", "Hold the design humidity ratio"),
               ("rh", "Hold the design relative humidity")]
FAN_LOCATIONS = [("id", "Induced draft, after cyclone"),
                 ("fd", "Forced draft, ambient inlet")]



# JavaScript arithmetic does not raise: x/0 is Infinity, log of a negative is NaN,
# and both propagate to a dash on the page. The port has to do the same or it
# crashes where the calculator merely prints "—".
def _div(a, b):
    if b == 0:
        return math.nan if a == 0 else math.copysign(math.inf, a) * (
            1 if not (isinstance(b, float) and math.copysign(1, b) < 0) else -1)
    try:
        return a / b
    except (ZeroDivisionError, OverflowError):
        return math.nan


def _log(x):
    if isinstance(x, float) and math.isnan(x):
        return math.nan
    if x < 0:
        return math.nan
    if x == 0:
        return -math.inf
    if math.isinf(x):
        return math.inf
    return math.log(x)


def _pow(base, exp):
    try:
        v = base ** exp
        return v if isinstance(v, (int, float)) else math.nan
    except (ValueError, OverflowError, ZeroDivisionError):
        return math.nan


def std_motor(hp):
    for m in STD_MOTORS:
        if m >= hp:
            return m
    return math.ceil(hp / 50) * 50


# --- psychrometrics, ASHRAE IP ---------------------------------------------------

class PSY:
    @staticmethod
    def patm(z):
        return 14.696 * (1 - 6.8754e-6 * z) ** 5.2559

    @staticmethod
    def pws(t_f):
        t = t_f + 459.67
        if t_f >= 32:
            return math.exp(-1.0440397e4 / t - 1.129465e1 - 2.7022355e-2 * t
                            + 1.289036e-5 * t * t - 2.4780681e-9 * t ** 3
                            + 6.5459673 * math.log(t))
        return math.exp(-1.0214165e4 / t - 4.8932428 - 5.3765794e-3 * t
                        + 1.9202377e-7 * t * t + 3.5575832e-10 * t ** 3
                        - 9.0344688e-14 * t ** 4 + 4.1635019 * math.log(t))

    @staticmethod
    def ws(t, p):
        pw = PSY.pws(t)
        return 0.621945 * pw / (p - pw)

    @staticmethod
    def w_wb(tdb, twb, p):
        wsw = PSY.ws(twb, p)
        return ((1093 - 0.556 * twb) * wsw - 0.24 * (tdb - twb)) / \
               (1093 + 0.444 * tdb - twb)

    @staticmethod
    def w_rh(tdb, rh, p):
        pw = rh * PSY.pws(tdb)
        return 0.621945 * pw / (p - pw)

    @staticmethod
    def rh(tdb, w, p):
        pw = w * p / (0.621945 + w)
        return pw / PSY.pws(tdb)

    @staticmethod
    def wb(tdb, w, p):
        lo, hi = -40.0, tdb
        for _ in range(60):
            mid = (lo + hi) / 2
            if PSY.w_wb(tdb, mid, p) > w:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    @staticmethod
    def v(t, w, p):
        return 0.370486 * (t + 459.67) * (1 + 1.607858 * w) / p

    @staticmethod
    def rho(t, w, p):
        return (1 + w) / PSY.v(t, w, p)

    @staticmethod
    def cp(w):
        return 0.240 + 0.444 * w


def _num(raw, default=0.0):
    try:
        v = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _f(x, d=0):
    """The calculator's own fmt(): grouped, fixed decimals, em dash if not finite."""
    if x is None or not math.isfinite(x):
        return "—"
    return _fmt.num(x, d)


def size(f):
    warnings_raw = []

    units = int(_num(f.get("units"), 1)) or 1
    preset = PRESET_BY_ID.get(str(f.get("preset") or "feed"), PRESET_BY_ID["feed"])

    def p(key, default=None):
        return _num(f.get(key), preset.get(key, default if default is not None else 0))

    tph = _num(f.get("tph"), 10) / units
    cp = p("cp")
    rho = p("rho")
    tin = p("tin")
    tout_target = p("tout")
    mcin = p("mcin") / 100
    mcout = p("mcout") / 100
    dp = p("dp")
    vmax = p("vmax")

    elev = _num(f.get("elev"), 1000)
    tmax = _num(f.get("tmax"), 95)
    tavg = _num(f.get("tavg"), 85)
    tlow = _num(f.get("tlow"), 70)
    hum_mode = str(f.get("humMode") or "wb")
    hum = _num(f.get("humVal"), 76)
    sweep_mode = str(f.get("sweepMode") or "w")
    ap_hot = _num(f.get("apHot"), 40)
    ap_cold = _num(f.get("apCold"), 15)
    margin = _num(f.get("margin"), 15) / 100
    min_cfm_ton = _num(f.get("minCfmTon"), 250)
    rh_max = _num(f.get("rhMax"), 60) / 100
    k_ua = _num(f.get("kua"), K_UA_DEFAULT)
    rpm = _num(f.get("rpm"), 4)
    slope = _num(f.get("slope"), 0.375)
    hold_max = _num(f.get("holdMax"), 12) / 100
    sp_drum = _num(f.get("spDrum"), 0.5)
    sp_cyc = _num(f.get("spCyc"), 4)
    sp_duct = _num(f.get("spDuct"), 1)
    fan_loc = str(f.get("fanLoc") or "id")
    eta = _num(f.get("eta"), 0.6)
    tcold = _num(f.get("tcold"), 20)

    if tph <= 0:
        return {"error": "A production rate is required."}
    if rho <= 0 or cp <= 0:
        return {"error": "A bulk density and a specific heat are required."}

    # --- design ambient state --------------------------------------------------
    patm = PSY.patm(elev)
    if hum_mode == "wb":
        twb_d = min(hum, tmax)
        w_in = max(PSY.w_wb(tmax, twb_d, patm), 0.0005)
    else:
        w_in = PSY.w_rh(tmax, min(max(hum, 1), 100) / 100, patm)
        twb_d = PSY.wb(tmax, w_in, patm)
    rh_d = PSY.rh(tmax, w_in, patm)
    rho_amb = PSY.rho(tmax, w_in, patm)

    # --- product mass and moisture ---------------------------------------------
    m_in = tph * 2000
    dry = m_in * (1 - mcin)
    m_out = dry / (1 - mcout)
    m_evap = m_in - m_out
    if m_evap < 0:
        warnings_raw.append(("warn", "Moisture out is higher than moisture in — no "
                                     "evaporation credited. Check the moisture numbers."))
        m_evap = 0.0

    # --- achievable floor, then the balance at the sizing outlet ----------------
    qp_t = m_in * cp * (tin - tout_target)
    hfg0 = 1093 - 0.556 * (tin + tout_target) / 2
    evap_frac0 = min(m_evap * hfg0 / qp_t, 0.9) if qp_t > 0 else 0
    floor = tmax + ap_cold - (tmax - twb_d) * evap_frac0
    tout = tout_target
    if tout_target < floor:
        tout = floor
        warnings_raw.append(("bad",
            f"Target outlet {_f(tout_target)}°F is below the achievable floor of "
            f"{_f(floor, 1)}°F at the design ambient ({_f(tmax)}°F DB / "
            f"{_f(twb_d, 1)}°F WB). Sized to the floor — lower the ambient basis, add "
            "evaporative capacity, or accept a warmer product."))
    if tin <= tout + 5:
        warnings_raw.append(("bad", "Product inlet must be well above the outlet. "
                                    "Nothing to cool."))

    hfg = 1093 - 0.556 * (tin + tout) / 2
    qp = m_in * cp * (tin - tout)
    qlat = m_evap * hfg
    if qlat > 0.9 * qp:
        qlat = 0.9 * qp
        warnings_raw.append(("warn", "Evaporation is limited by the heat available in "
            "the product — the moisture drop entered cannot all be flashed. Latent "
            "credit capped at 90% of product heat."))
    qair = max(qp - qlat, 1)
    evap_frac = qlat / qp if qp > 0 else 0

    # --- air quantity: thermal, moisture-carrying, sweep minimum ----------------
    ta_out = tin - ap_hot
    cpa = PSY.cp(w_in)
    d_tair = ta_out - tmax
    if d_tair < 15:
        warnings_raw.append(("warn",
            f"Only {_f(d_tair)}°F between exhaust air ({_f(ta_out)}°F) and design "
            "ambient — the hot-end approach is eating the driving force. Airflow "
            "balloons; consider a smaller approach or accept it."))
    if d_tair < 3:
        d_tair = 3
        warnings_raw.append(("bad", "Exhaust air cannot be cooler than the ambient it "
            "started as. Reduce the hot-end approach or the ambient basis."))
    m_thermal = _div(qair * (1 + margin), cpa * d_tair)
    pw_lim = rh_max * PSY.pws(ta_out)
    w_lim = 0.621945 * pw_lim / (patm - pw_lim)
    m_moist = m_evap / (w_lim - w_in) if m_evap > 0 and w_lim > w_in else 0
    m_sweep = min_cfm_ton * tph * 60 * 0.075
    m_air = max(m_thermal, m_moist, m_sweep)
    air_gov = ("Thermal" if m_air == m_thermal else
               "Moisture carry" if m_air == m_moist else "Sweep-air minimum")
    ta_out_act = tmax + _div(qair, m_air * cpa)
    w_out = w_in + _div(m_evap, m_air)
    rh_out = PSY.rh(ta_out_act, w_out, patm)
    if rh_out >= 1:
        warnings_raw.append(("bad", "Exhaust air would be saturated — fog and wet dust "
            "in the cyclone. Increase airflow (raise the sweep-air minimum or lower "
            "max exhaust RH)."))
    elif rh_out > 0.85:
        warnings_raw.append(("warn",
            f"Exhaust RH {_f(rh_out * 100)}% — condensation risk in the cyclone and "
            "duct on cool mornings. Consider more air or insulated exhaust ducting."))

    # --- LMTD and volumes -------------------------------------------------------
    d_th, d_tc = tin - ta_out_act, tout - tmax
    lmtd = (d_th if abs(d_th - d_tc) < 1e-6
            else _div(d_th - d_tc, _log(_div(d_th, d_tc))))
    acfm_out = m_air * PSY.v(ta_out_act, w_out, patm) / 60
    acfm_in = m_air * PSY.v(tmax, w_in, patm) / 60
    scfm = m_air / 0.075 / 60

    # --- drum candidates --------------------------------------------------------
    q_vol = _div(m_in, rho)
    s_slope = slope / 12
    b_factor = _div(5, math.sqrt(dp) if dp > 0 else 0)
    cands = []
    for dr in COOLER_DRUMS:
        g = _div(m_air, dr["A"])
        ua = _div(k_ua * _pow(g, 0.67), dr["d"])
        v_req = _div(qair * (1 + margin), ua * lmtd)
        vel = _div(acfm_out, dr["A"])
        f_load = _div(dry, dr["A"])
        theta = (_div(0.23 * dr["L"], s_slope * _pow(rpm, 0.9) * dr["d"])
                 + _div(0.6 * b_factor * dr["L"] * g, f_load))
        hold = _div(theta / 60 * q_vol, dr["V"])
        util = _div(v_req, dr["V"])
        ratios = {"Thermal": util, "Air velocity": _div(vel, vmax),
                  "Holdup": _div(hold, hold_max)}
        # the original reduces left to right and keeps the earlier key on a tie
        gov = list(ratios)[0]
        for key in list(ratios)[1:]:
            if ratios[key] > ratios[gov]:
                gov = key
        fails = [k for k in ratios if ratios[k] > 1]
        cands.append({**dr, "G": g, "Ua": ua, "Vreq": v_req, "vel": vel, "F": f_load,
                      "theta": theta, "hold": hold, "util": util, "gov": gov,
                      "fails": fails, "ok": not fails, "UA": ua * dr["V"]})
    best = next((c for c in cands if c["ok"]), None)
    bi = cands.index(best) if best else -1
    if not best:
        warnings_raw.append(("bad", "Duty exceeds the largest drum in the standard "
            "grid. Split the rate across parallel coolers (selector above) or raise the "
            "velocity / holdup limits with engineering."))
    if best and tin > 400:
        warnings_raw.append(("warn",
            f"Product enters at {_f(tin)}°F in a direct air-swept drum — run a "
            "combustion / dust-deflagration review. Biochar and torrefied material "
            "usually call for an indirect (water-jacketed) or inerted cooler."))

    # --- eps-NTU prediction on a fixed drum and airflow -------------------------
    def predict(t_amb, w, drum):
        c_prod = m_in * cp * (1 - evap_frac)
        c_air = m_air * PSY.cp(w)
        c_min, c_max = min(c_prod, c_air), max(c_prod, c_air)
        cr = _div(c_min, c_max)
        ntu = _div(drum["UA"], c_min)
        if cr < 0.999:
            e = math.exp(-ntu * (1 - cr))
            eps = (1 - e) / (1 - cr * e)
        else:
            eps = ntu / (1 + ntu)
        q = eps * c_min * max(tin - t_amb, 0)
        return {"tpOut": tin - _div(q, c_prod), "taOut": t_amb + _div(q, c_air),
                "eps": eps, "NTU": ntu}

    # --- drive ------------------------------------------------------------------
    drive, periph = None, 0.0
    if best:
        live = best["hold"] * best["V"] * rho
        shell = 15.3 * math.pi * best["d"] * best["L"] * 1.6
        weight = live + shell
        d_ring = best["d"] + 1
        bhp = rpm * (4.75 * best["d"] * live + 0.1925 * d_ring * weight
                     + 0.33 * weight) / 1e5
        drive = {"live": live, "shell": shell, "Wt": weight, "bhp": bhp,
                 "motor": std_motor(bhp / 0.85 * 1.15)}
        periph = math.pi * best["d"] * rpm
        if periph < 20 or periph > 100:
            warnings_raw.append(("warn",
                f"Shell peripheral speed {_f(periph)} ft/min is outside the usual "
                "20–100 ft/min band — adjust drum RPM."))
        if best["hold"] < 0.05:
            warnings_raw.append(("warn",
                f'Holdup on {best["name"]} is only {_f(best["hold"] * 100, 1)}% — '
                "flights will run thin. Slow the drum, flatten the slope, or take the "
                "next-smaller drum if thermal allows."))

    # --- fan --------------------------------------------------------------------
    t_fan = ta_out_act if fan_loc == "id" else tmax
    w_fan = w_out if fan_loc == "id" else w_in
    acfm_fan = m_air * PSY.v(t_fan, w_fan, patm) / 60
    rho_fan = PSY.rho(t_fan, w_fan, patm)
    df = rho_fan / 0.075
    sp_act = sp_drum + sp_cyc + sp_duct
    sp_std = _div(sp_act, df)
    bhp_fan = _div(acfm_fan * sp_act, 6356 * eta)
    rho_cold = PSY.rho(tcold, 0.002, patm)
    bhp_cold = _div(bhp_fan * rho_cold, rho_fan)
    # Sized on hot running, not the cold start (Jason, 2026-10-03: "go with
    # 5 HP, size it on hot running"). The fan starts with its inlet damper
    # closed or on a VFD, so it never pulls the cold-air BHP; that figure is
    # still reported so the start-up interlock is not forgotten.
    fan_motor = std_motor(bhp_fan * 1.05 * 1.05)
    cyc_d = math.sqrt(acfm_fan / 5.45)
    duct_d = math.sqrt(acfm_fan / 4500 * 4 / math.pi) * 12

    # --- summer sweep -----------------------------------------------------------
    temps = set()
    t = tlow
    while t < tmax:
        temps.add(_fmt.jsround(t))
        t += 5
    temps.add(_fmt.jsround(tavg))
    temps.add(_fmt.jsround(tmax))
    sweep = []
    for t in sorted(x for x in temps if tlow <= x <= tmax):
        w = (min(w_in, PSY.ws(t, patm)) if sweep_mode == "w"
             else PSY.w_rh(t, rh_d, patm))
        pt = predict(t, w, best) if best else {"tpOut": float("nan"),
                                               "taOut": float("nan")}
        m_req = max(_div(qair, PSY.cp(w) * max(ta_out - t, 3)), m_moist, m_sweep)
        w_out_r = w + _div(m_evap, m_req)
        ta_out_r = t + _div(qair, m_req * PSY.cp(w))
        acfm_req = m_req * PSY.v(ta_out_r if fan_loc == "id" else t,
                                 w_out_r if fan_loc == "id" else w, patm) / 60
        t_fan_s = pt["taOut"] if fan_loc == "id" else t
        w_fan_s = (w + _div(m_evap, m_air)) if fan_loc == "id" else w
        df_s = (PSY.rho(t_fan_s, w_fan_s, patm) / 0.075
                if math.isfinite(t_fan_s) else float("nan"))
        sweep.append({"t": t, "wb": PSY.wb(t, w, patm), "rh": PSY.rh(t, w, patm),
                      "rhoA": PSY.rho(t, w, patm), "tpOut": pt["tpOut"],
                      "taOut": pt["taOut"], "acfmReq": acfm_req, "df": df_s,
                      "isAvg": t == _fmt.jsround(tavg), "isMax": t == _fmt.jsround(tmax)})
    design = predict(tmax, w_in, best) if best else None
    avg_pt = next((r for r in sweep if r["isAvg"]), None)

    # --- render -----------------------------------------------------------------
    per = f" each of {units}" if units > 1 else ""
    outputs = [
        {"label": "Model", "headline": True,
         "value": (best["name"] + (f" × {units}" if units > 1 else "")) if best
                  else "No standard drum fits"},
        {"label": "Sensible to air", "value": f"{_f(qair / 1000)} MBH{per}"},
        {"label": "Design airflow", "value": f"{_f(scfm)} SCFM{per}",
         "note": f"{air_gov} sets airflow"},
        {"label": "Fan duty", "value": f'{_f(acfm_fan)} ACFM @ {_f(sp_act, 1)}" WC'},
        {"label": "Predicted outlet",
         "value": (f'{_f(design["tpOut"])} °F' if design else "—"),
         "note": f"target {_f(tout_target)} °F"},
    ]
    drum_specs = []
    if best:
        drum_specs = [
            ("Drum diameter × length", f'{best["d"]} ft × {best["L"]} ft'),
            ("L / D", _f(_div(best["L"], best["d"]), 1)),
            ("Drum volume", f'{_f(best["V"])} ft³'),
            ("Thermal volume required",
             f'{_f(best["Vreq"])} ft³ ({_f(best["util"] * 100)}%)'),
            ("Ua (K·G^0.67/D)", f'{_f(best["Ua"], 2)} Btu/h·ft³·°F'),
            ("Air mass velocity G", f'{_f(best["G"])} lb/h·ft²'),
            ("Superficial air velocity", f'{_f(best["vel"])} FPM (max {_f(vmax)})'),
            ("Retention (Friedman–Marshall)", f'{_f(best["theta"], 1)} min'),
            ("Holdup", f'{_f(best["hold"] * 100, 1)}% (max {_f(hold_max * 100)}%)'),
            ("Speed / slope",
             f'{_fmt.locale(rpm)} RPM · {_fmt.locale(slope)} in/ft · {_f(periph)} ft/min'),
            ("Live load / rotating load",
             f'{_f(drive["live"])} / {_f(drive["Wt"])} lb'),
            ("Drum drive", f'{_f(drive["bhp"], 1)} bhp → {_fmt.locale(drive["motor"])} HP'),
        ]
    thermal_specs = [
        ("Feed (wet)", f'{_f(m_in)} lb/h{" each" if per else ""}'),
        ("Product ΔT", f"{_f(tin)} → {_f(tout)} °F ({_f(tin - tout)} °F)"),
        ("Product heat released", f"{_f(qp / 1000)} MBH"),
        ("Water evaporated",
         f"{_f(m_evap)} lb/h ({_f(mcin * 100, 1)} → {_f(mcout * 100, 1)} % wb)"),
        ("Latent credit", f"{_f(qlat / 1000)} MBH ({_f(evap_frac * 100)}%)"),
        ("Sensible to air", f"{_f(qair / 1000)} MBH"),
        ("Achievable outlet floor", f"{_f(floor, 1)} °F"),
        ("Air in → out", f"{_f(tmax)} → {_f(ta_out_act)} °F"),
        ("Counter-current LMTD", f"{_f(lmtd, 1)} °F"),
        ("Air: thermal / moisture / sweep",
         f"{_f(m_thermal / 4.5)} / {_f(m_moist / 4.5)} / {_f(m_sweep / 4.5)} SCFM"),
        ("Design air mass flow", f"{_f(m_air)} lb/h · {_f(_div(scfm, tph))} SCFM/ton"),
        ("Design margin", f"{_f(margin * 100)}% on duty"),
    ]
    psy_specs = [
        ("Barometric pressure", f"{_f(patm, 2)} psia @ {_f(elev)} ft"),
        ("Design ambient", f"{_f(tmax)} °F DB / {_f(twb_d, 1)} °F WB"),
        ("Relative humidity", f"{_f(rh_d * 100)}%"),
        ("Humidity ratio in", f"{_f(w_in * 7000)} gr/lb"),
        ("Ambient air density", f"{_f(rho_amb, 4)} lb/ft³"),
        ("Inlet volume", f"{_f(acfm_in)} ACFM"),
        ("Exhaust state", f"{_f(ta_out_act)} °F · {_f(w_out * 7000)} gr/lb"),
        ("Exhaust RH", f"{_f(rh_out * 100)}%"),
        ("Exhaust volume", f"{_f(acfm_out)} ACFM"),
        ("Average-summer outlet",
         f'{_f(avg_pt["tpOut"])} °F @ {_f(tavg)} °F DB'
         if avg_pt and math.isfinite(avg_pt["tpOut"]) else "—"),
    ]
    fan_specs = [
        ("Fan location", "Induced draft, after cyclone" if fan_loc == "id"
                         else "Forced draft, ambient inlet"),
        ("Air at fan", f"{_f(t_fan)} °F · {_f(rho_fan, 4)} lb/ft³"),
        ("Volume at fan", f"{_f(acfm_fan)} ACFM ({_f(scfm)} SCFM)"),
        ("Actual static", f'{_f(sp_act, 1)}" WC'),
        ("Density factor", _f(df, 3)),
        ("Curve-selection static (std air)", f'{_f(sp_std, 1)}" WC'),
        ("Brake HP at design", f"{_f(bhp_fan, 1)} bhp (η {_fmt.locale(eta)})"),
        ("Cold-start BHP", f"{_f(bhp_cold, 1)} bhp @ {_f(tcold)} °F — start "
                           "damper-closed or on a VFD"),
        ("Fan motor", f"{_fmt.locale(fan_motor)} HP · radial wheel"),
        ("Exhaust duct @ 4,500 FPM", f"{_f(duct_d)} in dia"),
        ("Cyclone class (verify)", f"HE-{_f(cyc_d)}"),
    ]

    def block(pairs):
        return [{"label": k, "value": v} for k, v in pairs]

    warnings = [m for level, m in warnings_raw if level == "bad"]
    notes = [m for level, m in warnings_raw if level != "bad"]

    line = {"name": f'Rotary Cooler — MCE {best["name"]}' if best
                    else "Rotary Cooler — no standard drum fits",
            "quantity": units, "unitPrice": 0, "needsPrice": True,
            "description": "\n".join(filter(None, [
                f"{_f(tph * units)} TPH of {preset['label'].lower()} at "
                f"{_f(tin)} °F to {_f(tout)} °F",
                (f'{best["d"]} ft × {best["L"]} ft direct air-swept counter-current '
                 f'drum, {_fmt.locale(rpm)} RPM, {_fmt.locale(drive["motor"])} HP drive'
                 if best else ""),
                f"{_f(acfm_fan)} ACFM exhaust at {_f(sp_act, 1)}\" WC, "
                f"{_fmt.locale(fan_motor)} HP fan",
                "MCE build — no rotary cooler price list on file",
            ]))}

    return {
        "calculator": "Rotary Cooler Sizing", "outputs": outputs,
        "drum": block(drum_specs), "thermal": block(thermal_specs),
        "psychrometrics": block(psy_specs), "fan": block(fan_specs),
        "warnings": warnings, "notes": notes, "lines": [line], "options": [],
        "total": 0.0, "needsPrice": True,
        "chips": ([f'{best["gov"]} governs', "Counter-current",
                   f"{air_gov} sets airflow"]
                  + ([f"{_f(evap_frac * 100)}% evaporative"] if evap_frac > 0.3 else [])
                  if best else []),
        "model": best["name"] if best else None, "units": units,
        "candidates": [{"name": c["name"], "d": c["d"], "L": c["L"],
                        "V": round(c["V"], 3), "Vreq": round(c["Vreq"], 3),
                        "util": round(c["util"], 6), "vel": round(c["vel"], 4),
                        "theta": round(c["theta"], 6), "hold": round(c["hold"], 8),
                        "gov": c["gov"], "ok": c["ok"], "fails": c["fails"],
                        "selected": c is best}
                       for c in cands],
        "sweep": [{k: (None if isinstance(v, float) and not math.isfinite(v)
                       else round(v, 6) if isinstance(v, float) else v)
                   for k, v in row.items()} for row in sweep],
        "balance": {"feed": round(m_in, 4), "dry": round(dry, 4),
                    "evaporated": round(m_evap, 4), "qProduct": round(qp, 2),
                    "qLatent": round(qlat, 2), "qAir": round(qair, 2),
                    "evapFraction": round(evap_frac, 8), "floor": round(floor, 6),
                    "outlet": round(tout, 6), "lmtd": round(lmtd, 6),
                    "airMassFlow": round(m_air, 4), "scfm": round(scfm, 4),
                    "airGovernor": air_gov, "acfmIn": round(acfm_in, 4),
                    "acfmOut": round(acfm_out, 4), "patm": round(patm, 6),
                    "wetBulb": round(twb_d, 6), "humidityIn": round(w_in, 8),
                    "humidityOut": round(w_out, 8), "exhaustRh": round(rh_out, 8),
                    "exhaustTemp": round(ta_out_act, 6)},
        "design": ({k: round(v, 8) for k, v in design.items()} if design else None),
        "drive": ({k: (round(v, 6) if isinstance(v, float) else v)
                   for k, v in drive.items()} if drive else None),
        "fanDuty": {"acfm": round(acfm_fan, 4), "spActual": round(sp_act, 6),
                    "spStd": round(sp_std, 6), "densityFactor": round(df, 8),
                    "bhp": round(bhp_fan, 6), "bhpCold": round(bhp_cold, 6),
                    "motor": fan_motor, "cycloneDia": round(cyc_d, 4),
                    "ductDia": round(duct_d, 4)},
    }
