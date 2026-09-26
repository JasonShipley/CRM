#!/usr/bin/env python3
"""Vendor cost bases MCE quotes from, and the markups applied to them.

Every figure here is transcribed from a real vendor quotation, with its source
and expiry recorded so a stale basis shows on the proposal instead of quietly
going out. Update the numbers when a new vendor quote lands; the calculators
read them from here.
"""
import datetime

# ---------------------------------------------------------------- AirPro fans --
# MCE baghouse model -> the AirPro fan selected for it, from the OEM lineup
# spreadsheet "FILTER LINE — HAND-OFF v4 (FAN SELECTIONS COMPLETE —
# AirPro Q117935R1)", 2026-07-31. All arrangement 4V (vertical, direct-mounted
# on the filter housing) with a CS outlet damper included in the cost, 12 in.wg
# design. Cost is MCE's net cost for fan + damper.
AIRPRO_QUOTE = "Q117935R1"
AIRPRO_QUOTE_EXPIRES = datetime.date(2026, 8, 27)
# The quote's own expiry has passed, but Jason confirmed on this date that the
# pricing still stands. A confirmation is treated as good for six months; after
# that the fan lines start flagging again. Clear this when a new quote lands.
AIRPRO_CONFIRMED = datetime.date(2026, 9, 23)
AIRPRO_CONFIRMED_GOOD_FOR = datetime.timedelta(days=183)
# "use the fan price of the airpro unit and double our cost" — Jason, 2026-09-23.
FAN_MARKUP = 2.0

#            model:   (fan,        duty ACFM@12wg, RPM,  motor/frame, ship lb, cost)
AIRPRO_FANS = {
    "9-4":    ("BIMS 150", 1055,  3466, "5/184T",    300,  3288),
    "9-6":    ("BIMS 150", 1055,  3466, "5/184T",    300,  3288),
    "9-8":    ("BIMS 150", 1055,  3466, "5/184T",    300,  3288),
    "9-10":   ("BIMS 150", 1055,  3466, "5/184T",    300,  3288),
    "16-4":   ("BIMS 150", 1055,  3466, "5/184T",    300,  3288),
    "16-6":   ("BIMS 150", 1055,  3466, "5/184T",    300,  3288),
    "16-8":   ("BIMS 150", 1405,  3480, "5/184T",    300,  3288),
    "16-10":  ("BIMS 150", 1755,  3503, "7.5/213T",  400,  3423),
    "25-4":   ("BIMS 150", 1405,  3480, "5/184T",    300,  3288),
    "25-6":   ("BIMS 150", 1755,  3503, "7.5/213T",  400,  3423),
    "25-8":   ("BIMS 150", 2200,  3516, "7.5/213T",  400,  3423),
    "25-10":  ("BIMS 165", 2750,  3488, "10/215T",   400,  3650),
    "36-4":   ("BIMS 150", 1755,  3503, "7.5/213T",  400,  3423),
    "36-6":   ("BIMS 165", 2750,  3488, "10/215T",   400,  3650),
    "36-8":   ("BIHS 165", 3165,  3484, "10/215T",   400,  4168),
    "36-10":  ("BIHS 165", 3955,  3483, "10/215T",   400,  4168),
    "49-4":   ("BIMS 150", 2200,  3516, "7.5/213T",  400,  3423),
    "49-6":   ("BIHS 165", 3955,  3483, "10/215T",   400,  4168),
    "49-8":   ("BIHS 165", 4310,  3552, "15/254T",   500,  4443),
    "49-10":  ("BIHS 165", 5390,  3541, "15/254T",   500,  4443),
    "64-4":   ("BIHS 165", 3165,  3484, "10/215T",   400,  4168),
    "64-6":   ("BIHS 165", 4310,  3552, "15/254T",   500,  4443),
    "64-8":   ("BIHS 165", 5630,  3534, "15/254T",   500,  4443),
    "64-10":  ("BIHS 182", 7035,  3476, "20/256T",   600,  5410),
    "81-4":   ("BIHS 165", 3955,  3483, "10/215T",   400,  4168),
    "81-6":   ("BIHS 165", 5390,  3541, "15/254T",   500,  4443),
    "81-8":   ("BIHS 182", 8905,  3494, "25/256T",   700,  5410),
    "81-10":  ("BIHS 182", 8905,  3494, "25/256T",   700,  6487),
    "100-4":  ("BIHS 165", 5390,  3541, "15/254T",   500,  4443),
    "100-6":  ("BIHS 182", 7035,  3476, "20/256T",   600,  5410),
    "100-8":  ("BIHS 182", 8905,  3494, "25/256T",   700,  5656),
    "100-10": ("BIHS 200", 10995, 3516, "40/324TS", 1000,  7117),
    "121-4":  ("BIHS 182", 5390,  3541, "15/254T",   500,  5410),
    "121-6":  ("BIHS 182", 8905,  3494, "25/256T",   700,  5656),
    "121-8":  ("BIHS 200", 10995, 3516, "40/324TS", 1000,  7117),
    "121-10": ("BIHS 330", 13305, 1750, "40/324T",  1500,  9862),
}
# The 9-4 row was not in AirPro's own sheet — it was assumed to take the
# smallest duty fan. Flag it rather than let it pass as quoted.
AIRPRO_FANS_BY_MODEL = {f[0] for f in AIRPRO_FANS.values()}
AIRPRO_ASSUMED = {"9-4"}


# ------------------------------------------------------------ SCC screw conveyor --
# MCE does not buy the same screw twice, so there is no table to look up — the
# budget comes from a cost model fitted to every SCC quotation on file. Each
# quote is a complete unit: conveyor plus drive, assembled, net cost ex-factory.
#
#   quote,        date,        dia, ft, material, cost,   notes
SCREW_QUOTES = [
    ("H49887CK-1", "2025-12-10", 6,  10, "CS", 7875,  "choke fed, variable-pitch feeder screw"),
    ("H49887CK-2", "2025-12-10", 6,  20, "CS", 8975,  "30° incline, hanger"),
    ("H49887CK-3", "2025-12-10", 9,  15, "CS", 10775, "20° incline, hi-temp paint, vents"),
    ("H49887CK-4", "2025-12-10", 9,  25, "CS", 15775, "20° incline, paddles, 2 hangers"),
    ("H49887CK-5", "2025-12-10", 9,  15, "CS", 9875,  "20° incline"),
    ("H49887CK-6", "2025-12-10", 9,  10, "CS", 6975,  "30° incline"),
    ("H51445AW",   "2026-06-29", 9,   8, "CS", 6175,  "horizontal, 1 HP Baldor"),
    ("H51006CK",   "2026-05-01", 18, 21, "CS", 20875, "horizontal, 10 HP Baldor + Dodge"),
    ("H51032CK",   "2026-05-06", 12, 20, "SS", 15495, "T304 throughout, 3 HP Nord"),
]

# Least-squares fit of cost = BASE + PER_IN x dia + PER_IN_FT x dia x length over
# the eight carbon-steel quotes, each escalated to SCREW_MODEL_DATE first. Mean
# absolute error 6.6%, worst 16%. Re-fit with tests/fit_screw_model.py when a new
# quote lands.
# OPEN — two more SS points surfaced from MCE PO 520244-BSC (2026-06-10, SCC quote
# H47978CK) that the fit above does NOT explain and that are NOT in the fit set:
#     12" T304, 36 ft  $18,955      model predicts $28,375  (+50%)
#     12" T304, 18 ft  $7,425 ea    model predicts $14,530  (+96%)
# Neither PO line mentions a drive, while most of the fitted quotes carry a motor
# (the 12" x 20 ft T304 in the fit set is $15,495 WITH a 3 HP Nord). If those two
# are bare conveyors, the model is pricing a drive into every budget and reads
# high for a screw supplied without one. Do not refit on these until SCC confirms
# what H47978CK included — refitting on an unknown scope would be worse than the
# current over-prediction, which at least errs toward covering MCE.
SCREW_MODEL_DATE = datetime.date(2026, 9, 23)
SCREW_MODEL = {"base": 6612.0, "per_in": -494.0, "per_in_ft": 64.10}
# Implied by the one like-for-like pair across time: a 9" x 8 ft unit that the
# Dec-2025 quotes put at $5,815 was quoted at $6,175 six and a half months later.
SCREW_ESCALATION = 0.115
# The quotes span these sizes. Outside them the model is extrapolating and says so.
SCREW_FIT_DIA = (6, 18)
SCREW_FIT_LENGTH = (8, 25)
# The one T304 stainless quote lands within 1% of what the model predicts for
# carbon at that size, so no material premium is applied. That is a single data
# point against a model that may simply over-predict at 12" — worth confirming
# with SCC before leaning on it for a sanitary job.
SCREW_STAINLESS_FACTOR = 1.0

# MCE's screw markup is "divide by 0.8" (Jason to Lorand, 2026-01-09). The budget
# comes off a fitted model rather than a firm quote, so it carries 10% more cover
# — equivalent to dividing by 0.727 instead (Jason, 2026-09-23).
SCREW_DIVISOR = 0.80
SCREW_COVER = 1.10
SCREW_MARKUP = (1 / SCREW_DIVISOR) * SCREW_COVER


def screw_cost(diameter_in, length_ft, stainless=False, today=None):
    """Modelled SCC net cost for a complete screw conveyor, escalated to today.

    Returns (cost, notes) where notes lists anything that weakens the estimate —
    a size outside the quoted range, or a stainless build.
    """
    dia, length = float(diameter_in), float(length_ft)
    m = SCREW_MODEL
    cost = m["base"] + m["per_in"] * dia + m["per_in_ft"] * dia * length
    years = ((today or datetime.date.today()) - SCREW_MODEL_DATE).days / 365.25
    if years > 0:
        cost *= (1 + SCREW_ESCALATION) ** years
    if stainless:
        cost *= SCREW_STAINLESS_FACTOR

    notes = []
    lo_d, hi_d = SCREW_FIT_DIA
    lo_l, hi_l = SCREW_FIT_LENGTH
    if not lo_d <= dia <= hi_d:
        notes.append(f'{dia:g}" is outside the {lo_d}-{hi_d}" range MCE has quotes for')
    if not lo_l <= length <= hi_l:
        notes.append(f"{length:g} ft is outside the {lo_l}-{hi_l} ft range MCE has "
                     "quotes for")
    if stainless:
        notes.append("stainless is modelled at carbon cost — MCE has only one T304 "
                     "quote and it sits on the carbon curve")
    # The model can invert on very short runs, where the diameter term dominates.
    if dia > lo_d and cost < screw_cost_raw(dia - 2, length):
        notes.append("the model is unreliable at this length — it prices this unit "
                     "below a smaller one")
    return max(cost, 0.0), notes


def screw_cost_raw(diameter_in, length_ft):
    m = SCREW_MODEL
    return m["base"] + m["per_in"] * float(diameter_in) + \
        m["per_in_ft"] * float(diameter_in) * float(length_ft)


def fan_for(baghouse_model):
    """(fan, duty, rpm, motor, weight, cost, assumed) or None."""
    row = AIRPRO_FANS.get(baghouse_model)
    if not row:
        return None
    return (*row, baghouse_model in AIRPRO_ASSUMED)


def fan_quote_stale(today=None):
    """True when the fan pricing needs reconfirming before it goes on a quote."""
    today = today or datetime.date.today()
    if AIRPRO_CONFIRMED and today <= AIRPRO_CONFIRMED + AIRPRO_CONFIRMED_GOOD_FOR:
        return False
    return today > AIRPRO_QUOTE_EXPIRES


# ------------------------------------------------------- MCE's own markup rules --
# Transcribed from MCE's own cost sheets, not inferred:
#
#   Buy-out equipment  price = cost / 0.70   "1D3D-60 CYCLONE - BUDGET PRICE MODEL",
#                                            dial "Buy-out margin 0.3". Verified
#                                            exactly against a real pair: Airlanco
#                                            quote 024350 priced the 49AST10 filter
#                                            at $32,321 cost and the NEMO Feed
#                                            proposal sold it at $46,172.
#   MCE fabrication    sell  = (cost x 1.10) / 0.75   same sheet: contingency 0.10
#                                            of cost, margin 0.25 *of sell*.
#   Replacement parts  sell  = cost / 0.77   HET Levelland Q-20260713-HET internal
#                                            note, "23% gross margin".
# OPEN — MCE currently has three different markups in play on bought-in equipment:
#   fans   x2.00   ("double our cost", Jason, 2026-09-23)
#   screws x1.375  (1/0.80 with 10% cover, Jason, 2026-09-23)
#   sheet  x1.4286 (1/0.70, MCE's own buy-out dial)
# The calculators use whichever Jason specified for that item, so nothing here
# quietly overrides an instruction. Worth a single ruling.
BUYOUT_DIVISOR = 0.70
FAB_CONTINGENCY = 0.10
FAB_MARGIN = 0.25                       # of sell, not of cost
PARTS_DIVISOR = 0.77

# Shop dials from the same fabrication model, for reference when a weldment has
# to be estimated from scratch rather than from a sold price.
SHOP_RATE_PER_HR = 85.0
STEEL_SHEET_PER_LB = 0.85
STEEL_PLATE_PER_LB = 0.75
FLAT_BAR_PER_LB = 1.10


def buyout_price(cost):
    """Vendor cost -> MCE sell price, at MCE's documented buy-out margin."""
    return cost / BUYOUT_DIVISOR


def fab_price(cost):
    """MCE shop cost -> sell price, at MCE's documented fabrication margin."""
    return cost * (1 + FAB_CONTINGENCY) / (1 - FAB_MARGIN)


# ------------------------------------------------------------------- cyclones --
# Sell prices MCE has actually put in front of a customer, by the model the
# cyclone calculator selects. 10 ga mild steel unless noted.
#   HE-30 / HE-39 / HE-47   NEMO Feed "Budgetary quote - Wheat Straw Line",
#                           ref 20260428-101712645, April 28 2026.
#   H74                     LETEK DCG MCE-Q-2609-LETEK-R2, September 12 2026,
#                           listed there as "HE-74" but rated 16,263 CFM at 3 in
#                           WG, which is the H74 line of MCE's own H chart. That
#                           one carries a weather hood, lined inlet and first-
#                           impact area and a removable top, so it prices high
#                           per pound against the plain HE units.
CYCLONE_QUOTES = {
    "HE-30": (7950.0, "2026-04-28", "NEMO Feed 20260428", '10 ga mild steel, rated to 4,900 CFM'),
    "HE-39": (11950.0, "2026-04-28", "NEMO Feed 20260428", '10 ga mild steel, rated to 8,800 CFM'),
    "HE-47": (15950.0, "2026-04-28", "NEMO Feed 20260428", '10 ga mild steel, rated to 12,600 CFM'),
    "H74": (30940.0, "2026-09-12", "LETEK MCE-Q-2609-LETEK-R2",
            "three-piece with weather hood, lined inlet and first-impact area, removable top"),
}
CYCLONE_QUOTE_DATE = datetime.date(2026, 4, 28)

# Sizes with no sold price fall back to dollars per pound of published shipping
# weight. The four quotes above land at $11.39-13.03/lb; the fabrication model
# for a bare 12 ga cyclone computes $10.03/lb of finished weldment, which brackets
# it from below. $11.50/lb is the low end of the sold range, so an interpolated
# price is never optimistic about a size MCE has not actually sold.
CYCLONE_PER_LB = 11.50

# Adders quoted alongside the HE cyclones, same NEMO Feed proposal.
CYCLONE_ADDERS = {
    "HE-30": {"stand": 2500.0, "insulated": 2995.0},
    "HE-39": {"stand": 2500.0, "insulated": 4995.0},
    "HE-47": {"stand": 3500.0, "insulated": 5995.0, "ss304": 9000.0},
}

# -------------------------------------------------------------------- airlocks --
# (brand, model number, cost, sell, date, source, description). The brand and the
# quote reference are internal; only the model number and the specification go on
# a customer line. Sell is MCE's own quoted price where one exists; where only a
# cost exists, sell is None and buyout_price() applies. The FT-12 is the
# mill-scale drop-through that goes under a hammermill filter hopper, and is the
# default this quote builder uses.
AIRLOCK_QUOTES = [
    ("Airlanco", "FT-12", 9026.0, None, "2026-04-23", "Airlanco quote 024350",
     "Drop-through rotary valve, cast iron housing and end plates, 8-vane open-end "
     "mild steel bevelled rotor, outboard bearings with three moly-urethane U-cup "
     "packing rings per side, 1.5 HP TEFC gearmotor at 18 RPM"),
    ("Prater", "BAV 10", 23124.0, None, "2025-04-03",
     "MCE PO 520214 / Prater KT012025111600",
     "BAV 10 configured, engineering master, ambient service"),
    ("", "EMVDL-RVEX-HT37", None, 10272.50, "2026-04-28", "NEMO Feed 20260428",
     "ATEX EN 15089 and NFPA 69 certified rotary valve to 40 in WG, cast iron, "
     "8-vane polyurethane flex-tip rotor, 1 HP at 30 RPM, 0.70 ft³ per rotation"),
    ("", "EMVDL-RVEX-HT45", None, 22998.0, "2026-04-28", "NEMO Feed 20260428",
     "ATEX EN 15089 and NFPA 69 certified rotary valve to 40 in WG, cast iron, "
     "8-vane polyurethane flex-tip rotor, 2 HP at 30 RPM, 1.23 ft³ per rotation"),
]
AIRLOCK_DEFAULT = "FT-12"
# The two certified valves above are the ones MCE has sell prices for. They are
# DIFFERENT SIZES, so neither is a drop-in for the other or for the standard
# FT-12 — they are carried as a range, and the size gets picked against the real
# duty. Anything that offers a certified valve quotes the range, not a model.
CERTIFIED_VALVES = ("EMVDL-RVEX-HT37", "EMVDL-RVEX-HT45")


def certified_valve_range():
    """(low, high, source) sell prices across the certified valves on file."""
    prices, source = [], ""
    for number in CERTIFIED_VALVES:
        found = airlock(number)
        if found:
            prices.append(found[1])
            source = found[4]
    if not prices:
        return None
    return min(prices), max(prices), source

# -------------------------------------------------------- baghouse, bought out --
# One real pair: Airlanco quote 024350 (April 23 2026) costed the 60 Series
# 49AST10 Style II at $32,321 for 804 ft2 of cloth on 6,240 CFM of ground corn
# dust, and the NEMO Feed proposal sold it at $46,172.
#
# That is an Airlanco A-60: a free-standing filter with a hopper, ladder, cage,
# guardrail and safety gate. MCE's own line is plenum-mount with no hopper and
# none of that access steel, so this rate is an UPPER bound on an MCE-built unit
# of the same cloth area, not a price for one. It is carried here so the quote
# shows a defensible budget number instead of a zero, and every line built from
# it says which it is.
BAGHOUSE_REF = ("Airlanco 49AST10 Style II", 32321.0, 804.0, "2026-04-23",
                "Airlanco quote 024350")
BAGHOUSE_COST_PER_SQFT = 32321.0 / 804.0          # $40.20/ft2 of cloth, vendor cost
BAGHOUSE_QUOTE_DATE = datetime.date(2026, 4, 23)


def airlock(number=None):
    """(model number, sell price, date, brand, source, description) for one airlock.

    `number` is what goes on the customer line; `brand` and `source` are internal.
    """
    want = number or AIRLOCK_DEFAULT
    for brand, model, cost, sell, date, source, desc in AIRLOCK_QUOTES:
        if model == want:
            price = sell if sell is not None else buyout_price(cost)
            return model, price, date, brand, source, desc
    return None


def cyclone_price(model, weight_lb=None):
    """(price, basis) for a cyclone model the calculator selected.

    A model MCE has sold prices at that price. Anything else is interpolated from
    the published shipping weight at CYCLONE_PER_LB, and the basis string says so
    — the caller keeps that out of the customer-facing description.
    """
    quoted = CYCLONE_QUOTES.get(model)
    if quoted:
        price, date, source, note = quoted
        return price, f"sold price, {source} ({date}) — {note}"
    if weight_lb:
        return (weight_lb * CYCLONE_PER_LB,
                f"interpolated at ${CYCLONE_PER_LB:.2f}/lb on {weight_lb:,.0f} lb "
                f"shipping weight — MCE has sold {', '.join(sorted(CYCLONE_QUOTES))} "
                f"at $11.39–13.03/lb; not a quoted price for this size")
    return None, ""


def baghouse_budget(cloth_sqft, hopper=False):
    """(price, basis) for a filter of this cloth area, from the one Airlanco pair.

    `hopper=True` means a filter receiver — a hopper-bottom free-standing unit. The
    reference IS one of those, so for a receiver the rate is a like-for-like scale
    rather than an upper bound, and the basis string says which it is. The rate
    itself is the same either way: one data point supports one rate, and a hopper
    adder nobody has costed would be a guess dressed up as a price.
    """
    cost = cloth_sqft * BAGHOUSE_COST_PER_SQFT
    ref, ref_cost, ref_area, ref_date, ref_source = BAGHOUSE_REF
    scale = (
        "That unit is a free-standing filter receiver with a hopper, ladder, cage and "
        "guardrail, which is what is being priced here, so this is a like-for-like "
        "scale on cloth area — still a budget figure, since nothing but the cloth area "
        "was matched"
        if hopper else
        "That unit is a free-standing Airlanco with hopper and access steel, so this is "
        "an upper bound on an MCE plenum-mount build, not a quote for one")
    return (buyout_price(cost),
            f"budget only — scaled from {ref} at ${BAGHOUSE_COST_PER_SQFT:.2f}/ft² "
            f"cost ({ref_source}, {ref_date}: ${ref_cost:,.0f} for {ref_area:,.0f} ft²), "
            f"marked up at MCE's buy-out divisor {BUYOUT_DIVISOR:g}. {scale}")


# --------------------------------------------------------------- drive motors --
# Main drive motors are a buy-out. Cost is MCE's net cost; the sell price uses
# the documented buy-out divisor like any other bought-in item.
#   hp: (make, model, cost, date, source)
MOTOR_QUOTES = {
    200: ("Teco", "EP2004", 10125.70, "2026-09-23", "Jason, current Teco cost"),
}
# A Toshiba equivalent was requested and is not back yet — when it lands, add it
# here rather than overwriting the Teco line, so both bases stay visible.
MOTOR_ALTERNATE_PENDING = {200: "Toshiba equivalent quoted, price not yet received"}


def motor(hp):
    """(model, sell price, date, make, source) for a main drive motor, or None
    when MCE has no cost on file for that horsepower."""
    entry = MOTOR_QUOTES.get(int(hp)) if hp else None
    if not entry:
        return None
    make, model, cost, date, source = entry
    return model, buyout_price(cost), date, make, source


# ------------------------------------------- combustible dust: NFPA protection --
# MCE's precedent is the Nix Forest Industries job: wood ground through a 1/4"
# screen, vented on the 25AST-8 filter. High Tech Duct Werks (Darryl Lind) sized
# and quoted it — quote Q-26693, ref 72326RN, 2026-07-23. The engineering basis is
# recorded here; the DOLLAR FIGURE IS NOT, because it is in an attachment MCE has
# but this project has not read, and a protection package is not a number to guess.
EXPLOSION_VENT_VENDOR = "High Tech Duct Werks, Inc."
EXPLOSION_VENT_CONTACT = "Darryl Lind · ductwerks@aol.com · 772-473-0538"
EXPLOSION_VENT_PRECEDENT = {
    "job": "Nix Forest Industries",
    "quote": "Q-26693 (ref 72326RN)",
    "date": "2026-07-23",
    "material": 'wood ground through a 1/4" screen',
    "kst": 150,                 # bar·m/s, coarse wood dust
    "pmax": 8.0,                # bar
    "pred": 0.2,                # bar(g) design reduced pressure
    "vessel": "25AST-8 dust filter",
    "selection": 'one EV-VD domed vent, 23" x 36" panel, below the hopper',
    "ducting": 'roughly 40" x 28" duct, about 5 ft, through the wall with a rain hood',
}
# Kst values MCE has actually worked to. Anything else comes from a dust hazard
# analysis, not from here — Kst drives the vent area, so a guessed Kst is a
# guessed protection package.
KST_ON_RECORD = {"wood": 150}

# An NFPA 69 isolation device stops flame and pressure propagating back down the
# duct. MCE's certified rotary valves do that job (flex-tip, certified to NFPA 69
# 12.2.4.3.6) and are already in AIRLOCK_QUOTES, so isolation is priced from there
# rather than as a separate line.
ISOLATION_NOTE = ("NFPA 69 isolation is served by a certified rotary valve — the "
                  "flex-tip design is certified to prevent flame passage per NFPA 69 "
                  "12.2.4.3.6. See the certified-valve option.")


def explosion_vent_basis():
    """The Nix precedent, as a list of lines for an internal note."""
    p = EXPLOSION_VENT_PRECEDENT
    return [
        f'Sized and quoted by {EXPLOSION_VENT_VENDOR} ({EXPLOSION_VENT_CONTACT})',
        f'Precedent: {p["job"]}, {p["quote"]}, {p["date"]} — {p["material"]}',
        f'Dust basis Kst {p["kst"]} bar·m/s, Pmax {p["pmax"]} bar, design Pred '
        f'{p["pred"]} bar(g)',
        f'That job took {p["selection"]} on the {p["vessel"]}',
        f'Vented outdoors through {p["ducting"]}',
        "Indoors needs a FLAMELESS vent instead of a standard panel",
    ]
