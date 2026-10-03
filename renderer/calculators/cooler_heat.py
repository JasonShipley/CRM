#!/usr/bin/env python3
"""Cooler heat balance — the thermal analysis behind a cooler selection.

The counterflow cooler calculator (cooler.py) picks a model off MCE's capacity
tables. This one answers the question the tables cannot: with this product, at
this temperature, in this ambient, will that cooler actually reach the discharge
temperature MCE promised, and how much air does it take.

Ported from MCE_Cooler_Heat_Balance.xlsx (rev 2026-09-29), which is built on
K. Kaff's CoolerMassGasflowchart energy balance with a transfer-rate model and a
field-calibration step added. The workbook's own method sheet is the spec; the
section numbers below are its section numbers.

    4. energy balance    what the air must carry, and the airflow to carry it
    5. transfer rate     ε-NTU on a volumetric coefficient — how fast the heat
                         actually moves, which is what sets the discharge
    6. calibration       a measured discharge from a running cooler, back out to
                         the volumetric coefficient it implies

Three cooler types, because the flow arrangement is the whole argument: a
counterflow bed and a counter-current drum let the exhaust climb toward the
product INLET temperature, while a co-current drum only lets both streams reach
a common temperature. That is why MCE's 2019 co-current sheet balanced on paper
at a 75 °F approach and could not physically deliver 80 °F product.

Nothing here is priced. It sizes and it verifies; the money is in cooler.py.
"""
import math

from . import _fmt

# --- constants, all from the workbook -----------------------------------------
CP_HUMID_AIR = 0.245           # BTU/lb·°F — the '1 CFM ~ 1.08 BTU/h.°F' rule
R_DRY_AIR = 287.055            # J/kg·K
P0_KPA = 101.325
LOF_HAWLEY = (0.79, 0.7)       # packed bed: 0.79 * (G/dp)^0.7, dp in FEET
FRIEDMAN_MARSHALL = (0.5, 0.67)  # rotary drum: 0.5 * G^0.67 / D, D in feet
CANNOT_SATURATE = 9.0          # sentinel: above ~200 °F the exhaust cannot saturate
BED_VELOCITY_CAP = 130         # CFM/ft² of bed floor
DRUM_VELOCITY_CAP = 350        # ft/min, cake fines carryover
CAKE_RETENTION_MIN = 15.0      # min, for 2 in-minus cake in a bed

TYPES = [("bed", "Counter flow bed"),
         ("drum_counter", "Rotary drum counter-current"),
         ("drum_co", "Rotary drum co-current")]
TYPE_LABELS = dict(TYPES)

SOURCE = ("MCE_Cooler_Heat_Balance.xlsx rev 2026-09-29 — Kaff energy balance, "
          "ε-NTU transfer rate, field calibration")

# The one cell of the workbook this port does not reproduce. The workbook's air
# mass flow implies a dry-air density of 0.07203 lb/ft³ at the reference case's
# 1,150 ft and 70 °F; the barometric formula below — which reproduces the
# workbook's own atmospheric pressure cell (97.18 kPa) exactly — gives 0.07182,
# a 0.3 % difference nobody has accounted for. It moves the minimum airflow about
# 25 CFM and the predicted discharge about 0.05 °F. Left as physics rather than
# back-fitted to the cell; `airDensity` overrides it, which is how the reference
# case is asserted exactly in tests/test_cooler_heat.py.
# Where this port knowingly does not do what the workbook does.
DEVIATIONS = {
    "arrangement_floor": {
        "workbook": "section 5 holds the predicted discharge at the inlet air "
                    "temperature only",
        "this_port": "also holds it at the section-4 floor for the flow "
                     "arrangement — the ideal counterflow discharge, or the "
                     "co-current common temperature",
        "why": "section 5 credits the moisture flash on top of an ε-weighted "
               "sensible exchange, so on a co-current drum it can return a "
               "discharge below the common temperature both streams are heading "
               "for. On the workbook's own 9 × 30 co-current case that is 103 °F "
               "against a 113 °F floor. Counterflow cases are unaffected — the "
               "reference case does not reach its floor.",
        "source": SOURCE,
    },
}

# Drum coolers carry a calibration by default; beds do not. Jason, 2026-10-03:
# "2.9 in both" — then "be at the same thing they are at", so the rotary
# cooler's sizing K was calibrated on its own method to the same rating
# (rotary_cooler.K_UA_DEFAULT); this one stays at 2.9.
# 2.9 puts the Insta-Pro 900 (46" × 96", 2,500 ACFM) at its 4,000 lb/h rating
# 20 °F over a 100 °F ambient with one point of moisture flashed, at ambient
# with two — "something close to their recommendations" while the
# evaporative credit is real. A measured discharge (section 6) replaces it.
DRUM_CAL_DEFAULT = 2.9
DRUM_CAL_SOURCE = ("Insta-Pro Model 900 rating — 4,000 lb/h, 46\" × 96\" drum, "
                   "2,500 ACFM, 100 °F ambient (Jason, 2026-10-03)")

KNOWN_DIVERGENCE = {
    "air_density": {
        "workbook_implies": 0.0720346,
        "this_port": "p_atm / (R * T) on the standard atmosphere",
        "at": "1,150 ft, 70 °F",
        "effect": "minimum airflow ~0.3 % low, predicted discharge ~0.05 °F",
        "source": SOURCE,
    },
}


# Field data from running coolers, kept beside the model they test. An entry
# whose discharge is not known cannot be calibrated against (section 6); it is
# recorded so the gap between the correlation and the field stays visible.
FIELD_DATA = {
    "tumble_4x8_soy": {
        "reported_by": "Jason",
        "reported": "2026-10-03",
        "cooler": "4 ft dia × 8 ft tumble (rotary drum) cooler",
        "product": "soy meal",
        "tph": 2.0,
        "t_product_in_f": 250,
        "fan_hp": 2,
        "result": "2 TPH of cooled meal",
        "unknown": ["discharge temperature", "ambient dry bulb / RH",
                    "moisture in and out", "fan CFM and static",
                    "flow arrangement (counter- or co-current)", "drum fill"],
        # What this model says about it, at cp 0.45, 38 lb/ft³, 7→6 % moisture,
        # 70 °F / 50 % RH, counter-current, 15 % fill (2026-10-03):
        "model_says": {
            "min_airflow_acfm": 1445,     # the air side: a 2 HP fan carries it
            "discharge_f_at_acfm": {1500: 171, 2000: 160, 2500: 151, 3000: 143},
            "cal_factor_if_discharge_100f_at_2500": 2.70,
        },
        "reading": "The energy balance agrees with the field: 2 HP of fan moves "
                   "more than the ~1,450 ACFM the heat load needs. The "
                   "Friedman-Marshall transfer rate (K 0.5) does not: it "
                   "predicts ~150 °F out of this drum, so if the meal really "
                   "leaves near ambient, the correlation is ~2.5-3× low for "
                   "meal in a flighted tumble cooler. Calibrate with a measured "
                   "discharge before carrying a factor.",
    },
    # Insta-Pro's published maximums for its extruded-meal rotary coolers, all
    # "100 °F ambient maximum" (Jason, 2026-10-03). The 900 is the 4 × 8 above;
    # 46" × 96" with 48 flights and the 700's 36" × 72" are from used-equipment
    # listings, not Insta-Pro. 400 and 950 dimensions are not on file.
    "instapro_ratings": {
        "reported_by": "Jason",
        "reported": "2026-10-03",
        "models": {
            "400": {"max_lb_h": 1000},
            "700": {"max_lb_h": 2000, "dia_in": 36, "length_in": 72,
                    "drive_hp": 0.75, "weight_lb": 1500,
                    "overall": '85"H x 48"W x 115"L', "serves": "one extruder"},
            "900": {"max_lb_h": 4000, "dia_in": 46, "length_in": 96,
                    "flights": 48, "drive_hp": 0.75, "weight_lb": 1850,
                    "overall": '90"H x 55"W x 139"L', "serves": "two extruders",
                    "fan_acfm": 2500, "fan_hp_field": 2,
                    # Aaron Equipment stock 47056001, 304 SS, photos from
                    # Jason 2026-10-03. Both nameplates date June 2011.
                    "drive": {
                        "motor": "Baldor Super-E XEX VECP3587T, 2 HP, 1755 rpm, "
                                 "145TC, TEFC, 1.15 SF",
                        "reducer": "Winsmith E35MDTD, 75:1, 1.0 SF rating 2.883 "
                                   "input HP / 6,891 in-lb output",
                        "reducer_output_rpm": 23.4,
                        "chain_ratio": "2:1 or 3:1 (Jason) — not confirmed",
                        "drum_rpm_if_2_to_1": 11.7,   # 147 ft/min shell speed
                        "drum_rpm_if_3_to_1": 7.8,    # 98 ft/min
                    }},
            "950": {"max_lb_h": 6000},
        },
        # Insta-Pro overview brochure (Jason, 2026-10-03): auxiliary equipment
        # spec table gives drive HP, weight and overall size above, and one
        # "Cooler Fan" at 3 HP, 190 lb; Jason's field fan is 2 HP. "Fan pulls
        # air through drum and exhausts it through cyclone fines collector."
        # Extruded soybeans leave the barrel at 300 °F; the 2000R extruder
        # makes 1,300-2,000 lb/h, so the 900 is two of them.
        "brochure": {"cooler_fan_hp": 3, "cooler_fan_weight_lb": 190,
                     "cyclone": '80"H x 43"W x 36"L, 147 lb',
                     "extruder_discharge_f": 300},
        # 2,500 ACFM on the 900 is Jason's figure (2026-10-03). At its rating
        # that is 1,250 CFM/ton, the middle row below. It also settles the
        # arrangement: co-current, the 900 at 4,000 lb/h and 2,500 ACFM
        # cannot get the meal below ~153 °F, so the rating only holds
        # counter-current.
        "ambient_max_f": 100,
        "unknown": ["discharge temperature or approach the rating holds",
                    "product moisture"],
        # Drum volume per lb/h is the one number that needs no assumption:
        # 700 → 47.2 lb/h per ft³, 900 → 43.3.
        "lb_h_per_ft3": {"700": 47.2, "900": 43.3},
        # calFactor that makes each drum hit its rating at 250 °F in, 100 °F /
        # 40 % RH, 7→6 % moisture, counter-current, 15 % fill, by assumed
        # airflow (CFM/ton) and approach to ambient (°F). Both sizes imply the
        # same factor to within ~3 %, so the correlation scales with drum size
        # the way Insta-Pro's ratings do and is off by a constant; which
        # constant depends on the two unknowns. Each pair is (900, 700).
        "implied_cal_factor": {
            1000: {10: (5.38, 5.25), 15: (4.59, 4.48), 20: (3.96, 3.87), 30: (3.00, 2.93)},
            1250: {10: (3.79, 3.70), 15: (3.31, 3.23), 20: (2.91, 2.84), 30: (2.28, 2.23)},
            1500: {10: (3.01, 2.94), 15: (2.66, 2.60), 20: (2.36, 2.31), 30: (1.88, 1.84)},
        },
    },
}


def _num(raw, default=0.0):
    try:
        v = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _opt(raw):
    """A blank input means 'use the correlation' — not zero."""
    if raw is None:
        return None
    s = str(raw).replace(",", "").strip()
    if s == "":
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


# --- psychrometrics ------------------------------------------------------------

def atmospheric_kpa(elevation_ft):
    """Standard atmosphere. Reproduces the workbook's 97.18 kPa at 1,150 ft."""
    return P0_KPA * (1 - 6.8753e-6 * elevation_ft) ** 5.2559


def air_density(elevation_ft, dry_bulb_f):
    """Dry-air density at site pressure, lb/ft³."""
    t_k = (dry_bulb_f - 32) * 5 / 9 + 273.15
    kg_m3 = atmospheric_kpa(elevation_ft) * 1000 / (R_DRY_AIR * t_k)
    return kg_m3 / 16.018463


def magnus_kpa(t_f):
    """Saturation vapor pressure, Magnus-Tetens.

    The 0.6108 / 17.27 / 237.3 coefficients, not the 0.61094 / 17.625 / 243.04
    set: this pair is what reproduces the workbook's own vapor-pressure cell
    (136.74 kPa at the reference exhaust) and its 288 lb/h of ambient moisture.
    """
    t_c = (t_f - 32) * 5 / 9
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def wet_bulb_f(dry_bulb_f, rh_pct):
    """Stull (2011), the workbook's own correlation."""
    t = (dry_bulb_f - 32) * 5 / 9
    rh = rh_pct
    tw = (t * math.atan(0.151977 * (rh + 8.313659) ** 0.5)
          + math.atan(t + rh) - math.atan(rh - 1.676331)
          + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
          - 4.686035)
    return tw * 9 / 5 + 32


def humidity_ratio(dry_bulb_f, rh_pct, p_kpa):
    pv = (rh_pct / 100.0) * magnus_kpa(dry_bulb_f)
    if pv >= p_kpa:
        return CANNOT_SATURATE
    return 0.62198 * pv / (p_kpa - pv)


# --- ε-NTU -------------------------------------------------------------------

def effectiveness(ntu, cr, co_current=False):
    if co_current:
        return (1 - math.exp(-ntu * (1 + cr))) / (1 + cr)
    if abs(1 - cr) < 1e-9:
        return ntu / (1 + ntu)
    e = math.exp(-ntu * (1 - cr))
    return (1 - e) / (1 - cr * e)


def ntu_from_effectiveness(eps, cr, co_current=False):
    """Invert the relation — section 6 works backwards from a measurement."""
    if co_current:
        inner = 1 - eps * (1 + cr)
        if inner <= 0:
            return None
        return -math.log(inner) / (1 + cr)
    if abs(1 - cr) < 1e-9:
        if eps >= 1:
            return None
        return eps / (1 - eps)
    inner_top, inner_bot = 1 - eps * cr, 1 - eps
    if inner_bot <= 0 or inner_top <= 0:
        return None
    return math.log(inner_top / inner_bot) / (1 - cr)


# --- the calculator ------------------------------------------------------------

def size(f):
    tph = _num(f.get("tph"), 12.0)
    cp = _num(f.get("cp"), 0.50)
    bulk = _num(f.get("bulkDensity"), 35.0)
    t_in = _num(f.get("tProductIn"), 240.0)
    approach = _num(f.get("approach"), 15.0)
    moist_in = _num(f.get("moistIn"), 7.0)
    moist_out = _num(f.get("moistOut"), 5.0)
    hfg = _num(f.get("hfg"), 1010.0)

    t_db = _num(f.get("airDryBulb"), 70.0)
    rh = _num(f.get("airRh"), 50.0)
    elev = _num(f.get("elevation"), 1150.0)
    acfm = _num(f.get("acfm"), 8200.0)
    eff_sizing = _num(f.get("effSizing"), 0.92)

    kind = str(f.get("coolerType") or "bed").strip().lower()
    if kind not in TYPE_LABELS:
        kind = "bed"
    bed_area = _num(f.get("bedArea"), 67.8)
    bed_depth = _num(f.get("bedDepth"), 30.0)
    piece = _num(f.get("pieceSize"), 1.50)
    drum_dia = _num(f.get("drumDia"), 9.0)
    drum_len = _num(f.get("drumLength"), 30.0)
    fill = _num(f.get("drumFill"), 15.0)
    uv_override = _opt(f.get("uvOverride"))
    cal_raw = _opt(f.get("calFactor"))
    cal_default = cal_raw is None or cal_raw <= 0
    if cal_default:
        cal = DRUM_CAL_DEFAULT if kind != "bed" else 1.0
    else:
        cal = cal_raw
    rho_override = _opt(f.get("airDensity"))
    measured = _opt(f.get("measuredDischarge"))

    if tph <= 0:
        return {"error": "A production rate is required."}
    if acfm <= 0:
        return {"error": "A design airflow is required."}
    if t_in <= t_db:
        return {"error": "The product is already at or below the cooling air "
                         "temperature — there is nothing to remove."}
    if moist_out > moist_in:
        return {"error": "Moisture out is above moisture in. A cooler does not "
                         "add water."}
    if not 0 < moist_in < 100 or not 0 <= moist_out < 100:
        return {"error": "Moisture has to be a wet-basis percentage under 100."}

    co = kind == "drum_co"
    warnings, notes = [], []

    # --- 1-2. streams ----------------------------------------------------------
    m_prod = tph * 2000.0
    dry = m_prod * (1 - moist_in / 100.0)
    water_in = m_prod - dry
    m_out = dry / (1 - moist_out / 100.0)
    water_out = m_out - dry
    flashed = water_in - water_out

    # --- 4. energy balance -----------------------------------------------------
    t_target = t_db + approach
    q_sensible = m_prod * cp * (t_in - t_target)
    q_latent = flashed * hfg
    q_air_load = q_sensible - q_latent
    c_prod = m_prod * cp

    p_atm = atmospheric_kpa(elev)
    rho = rho_override if rho_override is not None else air_density(elev, t_db)
    m_air = acfm * 60.0 * rho
    c_air = m_air * CP_HUMID_AIR
    per_cfm = c_air / acfm
    cfm_per_ton = acfm / tph

    t_air_out_full = t_db + q_air_load / c_air
    # ideal counterflow: the exhaust leaves at the product inlet temperature
    t_floor_counter = t_in - (c_air * (t_in - t_db) + q_latent) / c_prod
    # ideal co-current: both streams leave at one temperature
    t_floor_co = (c_prod * t_in + c_air * t_db - q_latent) / (c_prod + c_air)

    c_air_min = q_air_load / (eff_sizing * (t_in - t_db))
    cfm_min = c_air_min / (CP_HUMID_AIR * 60.0 * rho)

    if q_air_load <= 0:
        verdict_air = ("The moisture flash alone carries the load — the air is "
                       "there to remove the vapor, not the heat.")
    elif acfm >= cfm_min:
        verdict_air = ("Airflow carries the heat load — discharge is set by "
                       "transfer rate (section 5)")
    else:
        verdict_air = (f"Airflow is short: {_fmt.num(cfm_min)} ACFM is the minimum "
                       f"at effectiveness {eff_sizing:g}")
        warnings.append(
            f"The design airflow of {_fmt.num(acfm)} ACFM is below the "
            f"{_fmt.num(cfm_min)} ACFM this duty needs at effectiveness "
            f"{eff_sizing:g}. No cooler geometry recovers that — the air has to "
            "carry the heat before the transfer rate matters.")

    # --- 5. transfer rate ------------------------------------------------------
    if kind == "bed":
        if bed_area <= 0 or bed_depth <= 0:
            return {"error": "A bed floor area and operating depth are required."}
        volume = bed_area * bed_depth / 12.0
        material_volume = volume          # a bed is full of product
        air_section = bed_area
        if piece <= 0:
            return {"error": "An effective piece size is required for the bed "
                             "film coefficient."}
        geometry = (f"{_fmt.fixed(bed_area, 1)} ft² floor × "
                    f"{_fmt.fixed(bed_depth, 0)} in deep")
    else:
        if drum_dia <= 0 or drum_len <= 0:
            return {"error": "A drum diameter and length are required."}
        if not 0 < fill < 100:
            return {"error": "Drum fill has to be a percentage of drum volume."}
        # The Friedman & Marshall coefficient is per unit of TOTAL drum volume —
        # the fill fraction sets the holdup, not the volume the coefficient acts
        # on. Taking the filled fraction instead puts the workbook's own 9 x 30
        # reference drum at 171 °F rather than the ~90 °F its method sheet
        # records.
        volume = math.pi / 4 * drum_dia ** 2 * drum_len
        material_volume = volume * fill / 100.0
        air_section = math.pi / 4 * drum_dia ** 2
        geometry = (f"{_fmt.fixed(drum_dia, 1)} ft × {_fmt.fixed(drum_len, 1)} ft "
                    f"drum at {_fmt.fixed(fill, 0)} % fill")

    holdup = material_volume * bulk
    retention = holdup / m_prod * 60.0
    g_mass = m_air / air_section
    velocity = acfm / air_section

    if kind == "bed":
        coef, expo = LOF_HAWLEY
        uv_corr = coef * (g_mass / (piece / 12.0)) ** expo
        uv_basis = "Löf & Hawley packed bed 0.79 × (G/dp)^0.7"
    else:
        coef, expo = FRIEDMAN_MARSHALL
        uv_corr = coef * g_mass ** expo / drum_dia
        uv_basis = ("Friedman & Marshall 0.5 × G^0.67 / D — a rotary DRYER "
                    "correlation, conservative for a well-flighted cooler")

    uv = uv_override if uv_override is not None else uv_corr * cal
    ua = uv * volume
    c_min, c_max = min(c_air, c_prod), max(c_air, c_prod)
    cr = c_min / c_max
    ntu = ua / c_min
    eps = effectiveness(ntu, cr, co_current=co)

    q_exchanged = eps * c_min * (t_in - t_db)
    t_discharge = t_in - (q_exchanged + q_latent) / c_prod

    # The section-5 model takes the sensible exchange at ε and then credits the
    # whole moisture flash on top, so it can return a discharge below what the
    # flow arrangement in section 4 can physically reach. The workbook guards
    # only against the inlet air temperature; this port also holds the prediction
    # at the section-4 floor for the arrangement, which on a co-current drum is
    # well above the inlet air. See DEVIATIONS.
    arrangement_floor = t_floor_co if co else t_floor_counter
    floor = max(t_db, arrangement_floor)
    clamped = t_discharge < floor
    if clamped:
        if floor > t_db:
            notes.append(
                f"Predicted discharge held at {_fmt.jsround(floor)} °F — the best "
                f"{'co-current' if co else 'counterflow'} exchange this airflow "
                "allows (section 4). The transfer-rate model on its own returned "
                f"{_fmt.jsround(t_discharge)} °F, which the arrangement cannot do.")
        else:
            notes.append("Predicted discharge held at the inlet air temperature — "
                         "evaporative sub-cooling toward the wet bulb is not "
                         "credited.")
        t_discharge = floor
        q_exchanged = c_prod * (t_in - t_discharge) - q_latent
    t_air_out = t_db + q_exchanged / c_air
    above_air = t_discharge - t_db
    meets = above_air <= approach + 0.5

    # --- psychrometric check on the exhaust ------------------------------------
    w_in = humidity_ratio(t_db, rh, p_atm)
    w_out = w_in + flashed / m_air
    pv_out = magnus_kpa(t_air_out)
    if pv_out >= p_atm:
        w_sat = CANNOT_SATURATE
    else:
        w_sat = 0.62198 * pv_out / (p_atm - pv_out)
    exhaust_ok = w_out < w_sat

    # --- warnings --------------------------------------------------------------
    if kind == "bed" and velocity > BED_VELOCITY_CAP:
        warnings.append(
            f"Superficial air velocity is {_fmt.num(velocity)} CFM/ft², over the "
            f"{BED_VELOCITY_CAP} CFM/ft² bed cap — expect fluidization and carryover. "
            "Widen the bed or cut the airflow.")
    if kind != "bed" and velocity > DRUM_VELOCITY_CAP:
        warnings.append(
            f"Superficial air velocity is {_fmt.num(velocity)} ft/min, over the "
            f"{DRUM_VELOCITY_CAP} ft/min limit for cake fines — the drum will carry "
            "product to the dust filter.")
    if not co and t_air_out >= t_in:
        warnings.append(
            "The exhaust is at or above the product inlet temperature, which "
            "counterflow cannot do. Check the airflow and the inlet temperature.")
    if co and t_air_out >= t_discharge + 1:
        warnings.append(
            "Co-current: the exhaust cannot leave above the product it leaves with. "
            "Check the inputs.")
    if kind == "bed" and piece >= 1.5 and retention < CAKE_RETENTION_MIN:
        warnings.append(
            f"Retention is {_fmt.fixed(retention, 1)} min on {_fmt.fixed(piece, 2)} in "
            f"pieces. Conduction inside a large piece is not modeled — MCE wants "
            f"{CAKE_RETENTION_MIN:g} min or more on 2 in-minus cake in a bed.")
    if co:
        warnings.append(
            "Co-current: product and air can only approach a common temperature "
            f"({_fmt.jsround(t_floor_co)} °F here), whatever the cooler's size. "
            "If the target is below that, the arrangement is wrong, not the cooler.")
    if not exhaust_ok:
        warnings.append(
            "The exhaust would have to hold more moisture than it can at that "
            "temperature — it will condense in the duct or the filter. Raise the "
            "airflow or take less moisture out in the cooler.")
    if uv_override is not None:
        notes.append(f"Volumetric coefficient overridden at {_fmt.fixed(uv, 1)} "
                     "BTU/h·ft³·°F — the correlation is not in play.")
    elif cal_default and kind != "bed":
        notes.append(f"Drum correlation calibrated × {_fmt.fixed(cal, 2)} to the "
                     f"{DRUM_CAL_SOURCE}. No discharge has been measured yet — "
                     "a measured run (section 6) replaces it.")
    elif abs(cal - 1.0) > 1e-9:
        notes.append(f"Correlation calibrated × {_fmt.fixed(cal, 2)} from field data.")
    if kind != "bed" and uv_override is None and abs(cal - 1.0) < 1e-9:
        notes.append(
            "The drum correlation is an uncalibrated rotary dryer number — it gives "
            "no credit for flight design or cascade quality. Calibrate it against a "
            "running drum (section 6) before promising this discharge.")
    if rho_override is not None:
        notes.append(f"Air density overridden at {rho_override:g} lb/ft³.")

    # --- 6. field calibration ---------------------------------------------------
    calibration = None
    if measured is not None:
        span = c_min * (t_in - t_db)
        eps_imp = (c_prod * (t_in - measured) - q_latent) / span if span else None
        entry = {"measured": measured, "effectiveness": None, "ntu": None,
                 "uv": None, "factor": None, "note": ""}
        if eps_imp is None or not 0 < eps_imp < 1:
            entry["note"] = (
                "That discharge implies an effectiveness outside 0–1 — the measured "
                "run and the inputs above do not describe the same cooler. Set every "
                "input to the measured run before reading this.")
        else:
            n_imp = ntu_from_effectiveness(eps_imp, cr, co_current=co)
            if n_imp is None:
                entry["note"] = ("That effectiveness is beyond what this flow "
                                 "arrangement can reach at this capacity ratio.")
            else:
                uv_imp = n_imp * c_min / volume
                entry.update({"effectiveness": round(eps_imp, 4),
                              "ntu": round(n_imp, 3),
                              "uv": round(uv_imp, 2),
                              "factor": round(uv_imp / uv_corr, 3) if uv_corr else None,
                              "note": "Carry the factor, or the coefficient itself, "
                                      "into new sizings of the same cooler family."})
        calibration = entry

    # --- outputs ----------------------------------------------------------------
    outputs = [
        {"label": "Predicted discharge temperature",
         "value": f"{_fmt.jsround(t_discharge)} °F", "headline": True,
         "note": f"{_fmt.jsround(above_air)} °F above the {_fmt.jsround(t_db)} °F "
                 f"inlet air — target is {_fmt.jsround(approach)} °F"},
        {"label": "Verdict",
         "value": "MEETS the target approach" if meets else "MISSES the target approach"},
        {"label": "Cooler", "value": f"{TYPE_LABELS[kind]} — {geometry}"},
        {"label": "Design airflow", "value": f"{_fmt.num(acfm)} ACFM"},
        {"label": "Minimum airflow to reach the target",
         "value": f"{_fmt.num(cfm_min)} ACFM",
         "note": f"counterflow at effectiveness {eff_sizing:g}"},
        {"label": "Airflow per ton", "value": f"{_fmt.num(cfm_per_ton)} CFM/ton"},
        {"label": "Sensible heat to remove", "value": f"{_fmt.num(q_sensible)} BTU/h"},
        {"label": "Heat taken by the moisture flash",
         "value": f"{_fmt.num(q_latent)} BTU/h",
         "note": f"{_fmt.num(flashed)} lb/h flashed, leaves as vapor"},
        {"label": "Heat the air carries as temperature rise",
         "value": f"{_fmt.num(q_air_load)} BTU/h"},
        {"label": "Exhaust temperature", "value": f"{_fmt.jsround(t_air_out)} °F"},
        {"label": "Retention time", "value": f"{_fmt.fixed(retention, 1)} min"},
        {"label": "Superficial air velocity",
         "value": (f"{_fmt.num(velocity)} CFM/ft²" if kind == "bed"
                   else f"{_fmt.num(velocity)} ft/min")},
        {"label": "Volumetric coefficient",
         "value": f"{_fmt.fixed(uv, 1)} BTU/h·ft³·°F", "note": uv_basis},
        {"label": "NTU / effectiveness",
         "value": f"{_fmt.fixed(ntu, 2)} / {_fmt.fixed(eps, 2)}"},
        {"label": "Air-side verdict", "value": verdict_air},
    ]

    streams = [
        {"item": "1", "description": "Ambient air", "temp": _fmt.jsround(t_db),
         "moisture": f"{_fmt.fixed(rh, 1)} %", "dry": _fmt.num(m_air),
         "water": _fmt.num(m_air * w_in), "q": "", "volume": _fmt.num(acfm)},
        {"item": "2", "description": "Cooler inlet air", "temp": _fmt.jsround(t_db),
         "moisture": f"{_fmt.fixed(rh, 1)} %", "dry": _fmt.num(m_air),
         "water": _fmt.num(m_air * w_in), "q": "", "volume": _fmt.num(acfm)},
        {"item": "3", "description": "Cooler outlet / exhaust air",
         "temp": _fmt.jsround(t_air_out), "moisture": _fmt.fixed(w_out, 4),
         "dry": _fmt.num(m_air), "water": _fmt.num(m_air * w_out),
         "q": _fmt.num(q_exchanged + q_latent),
         "volume": _fmt.num(acfm * (t_air_out + 459.67) / (t_db + 459.67))},
        {"item": "A", "description": "Feed to cooler", "temp": _fmt.jsround(t_in),
         "moisture": f"{_fmt.fixed(moist_in, 1)} %", "dry": _fmt.num(dry),
         "water": _fmt.num(water_in), "q": "", "volume": ""},
        {"item": "B", "description": "Cooled product", "temp": _fmt.jsround(t_discharge),
         "moisture": f"{_fmt.fixed(moist_out, 1)} %", "dry": _fmt.num(dry),
         "water": _fmt.num(water_out), "q": _fmt.num(q_exchanged + q_latent),
         "volume": ""},
        {"item": "C", "description": "Moisture flashed",
         "temp": _fmt.jsround(t_discharge), "moisture": "", "dry": "",
         "water": _fmt.num(flashed), "q": _fmt.num(q_latent), "volume": ""},
    ]

    return {
        "calculator": "Cooler Heat Balance", "outputs": outputs,
        "warnings": warnings, "notes": notes, "lines": [], "options": [],
        "total": 0.0, "needsPrice": False,
        "streams": streams, "calibration": calibration,
        "coolerType": kind, "source": SOURCE,
        "balance": {
            "productMassFlow": round(m_prod, 1), "drySolids": round(dry, 1),
            "waterIn": round(water_in, 1), "waterOut": round(water_out, 1),
            "waterFlashed": round(flashed, 1),
            "targetDischarge": round(t_target, 2),
            "qSensible": round(q_sensible, 0), "qLatent": round(q_latent, 0),
            "qAir": round(q_air_load, 0),
            "cProduct": round(c_prod, 1), "cAir": round(c_air, 1),
            "airDensity": round(rho, 6), "airMassFlow": round(m_air, 1),
            "atmosphericKpa": round(p_atm, 4),
            "btuPerCfmPerF": round(per_cfm, 4),
            "cfmPerTon": round(cfm_per_ton, 1),
            "airOutFullLoad": round(t_air_out_full, 2),
            "floorCounterflow": round(t_floor_counter, 2),
            "floorCoCurrent": round(t_floor_co, 2),
            "minimumAcfm": round(cfm_min, 1),
        },
        "transfer": {
            "volume": round(volume, 2), "materialVolume": round(material_volume, 2),
            "holdup": round(holdup, 1),
            "retentionMin": round(retention, 2), "airSection": round(air_section, 2),
            "massVelocity": round(g_mass, 2), "velocity": round(velocity, 2),
            "uvCorrelation": round(uv_corr, 3), "uvUsed": round(uv, 3),
            "ua": round(ua, 1), "cMin": round(c_min, 1), "cr": round(cr, 4),
            "ntu": round(ntu, 3), "effectiveness": round(eps, 4),
            "discharge": round(t_discharge, 2), "aboveAir": round(above_air, 2),
            "airOut": round(t_air_out, 2), "meets": meets, "clamped": clamped,
        },
        "psychrometrics": {
            "wetBulb": round(wet_bulb_f(t_db, rh), 2),
            "humidityIn": round(w_in, 4), "humidityOut": round(w_out, 4),
            "vaporPressureOut": round(pv_out, 2),
            "saturationOut": round(w_sat, 4), "exhaustOk": exhaust_ok,
        },
    }
