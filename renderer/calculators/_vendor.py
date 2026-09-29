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


# The fan used to be priced here by fitting the AirPro lineup's (motor, cost)
# pairs against horsepower. That is gone: MCE builds its own XF fans and has an XF
# sizing calculator, so the price comes from MCE's own line, not from a regression
# over somebody else's catalogue. Until the XF calculator is vendored the fan is
# SIZED (calculators/fan.py) and left unpriced, and _pricing.UNPRICED says so.


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

# Pocket displacement, ft³ per rotation, where the quote actually states it. This
# is what lets a valve be SIZED rather than just picked off a shelf: capacity is
# displacement x rpm x fill. The FT-12 MCE quotes as standard does not state one,
# so it cannot be checked against a duty until Airlanco gives the figure — which
# is exactly what calculators/airlock.py says instead of guessing.
AIRLOCK_DISPLACEMENT = {
    "EMVDL-RVEX-HT37": {"ft3_per_rev": 0.70, "rpm": 30, "hp": 1,
                        "source": "NEMO Feed 20260428"},
    "EMVDL-RVEX-HT45": {"ft3_per_rev": 1.23, "rpm": 30, "hp": 2,
                        "source": "NEMO Feed 20260428"},
}
AIRLOCK_NO_DISPLACEMENT = {
    "FT-12": "Airlanco quote 024350 states 1.5 HP at 18 RPM but no pocket "
             "displacement — ask Airlanco for ft³/rev and this valve sizes itself.",
    "BAV 10": "Prater KT012025111600 states no pocket displacement.",
}
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


# The feeder multiplier and the air-pan prices live in the pricing basis now
# (_pricing.py), so a price move updates the calculator, the book and the CRM at
# once. These names stay as the way the rest of the code reaches them.
import math

from ._pricing import (air_pan_price, factor as pricing_factor,  # noqa: E402
                       mill_option)

FEEDER_MULTIPLIER_SOURCE = "pricing basis — calculators/_pricing.py"


def feeder_multiplier(cup_type=None):
    """The live feeder escalation factor. Cup type is accepted for callers that
    used to vary it; the basis carries one factor for every cup."""
    return pricing_factor("feeder")


# ------------------------------------------- MCE's own names, from the book -----
# The price book is also the naming authority. "8-4ROW" is not an ambiguity to be
# resolved — it is MCE's catalog designation for the 8-row stainless round-cup
# feeder, and the book lists one designation per row count. Reading it as "8 or 4
# rows?" quoted the wrong feeder and raised an open item that never needed raising.
FEEDER_CATALOG_NAME = {
    "nylon": 'Dia. Nylon Cup Rotary Feeder',
    "ss": 'Dia. Stainless Round Cup Rotary Feeder',
    "tt": 'Dia. Tight Tolerance Stainless Round Cup Rotary Feeder',
}
# rows -> the designation the book prints, and the mill screen widths it serves
FEEDER_ROW_DESIGNATION = {
    "nylon": {2: "2-ROW", 3: "3-ROW", 4: "4-ROW", 5: "5-ROW", 6: "6-ROW", 7: "7-ROW",
              8: "8-ROW", 9: "9-ROW", 10: "10-ROW", 11: "11-ROW", 12: "12-ROW",
              14: "14-ROW"},
    "round": {2: "2-2ROW", 3: "3-2ROW", 4: "4-2ROW", 5: "5-4ROW", 6: "6-4ROW",
              7: "7-4ROW", 8: "8-4ROW", 9: "9-6ROW", 10: "10-6ROW", 11: "11-6ROW",
              12: "12-6ROW", 14: "14-8ROW"},
}
FEEDER_ROW_WIDTHS = {2: '6" & 9"', 3: '11.5" & 12"', 4: '15"', 5: '20"', 6: '24"',
                     7: '30"', 8: '30" & 36"', 9: '36"', 10: '36" & 40"', 11: '40"',
                     12: '40"-48"', 14: '60"'}


def feeder_designation(cup_type, rows):
    """MCE's own row designation — "8-4ROW" for the 8-row stainless, "8-ROW" nylon."""
    table = FEEDER_ROW_DESIGNATION["nylon" if cup_type == "nylon" else "round"]
    return table.get(int(rows or 0), f"{int(rows or 0)}-ROW")


def feeder_description(diameter_in, cup_type, rows):
    """The line name exactly as the price book heads its column."""
    kind = FEEDER_CATALOG_NAME.get(cup_type or "nylon", FEEDER_CATALOG_NAME["nylon"])
    return f'{diameter_in}" {kind} — {feeder_designation(cup_type, rows)}'


# The fan calculator's own default static for cyclone-exhaust duty. It is MCE's
# number, not a layout calculation — every line built on it says so.
FAN_STATIC_CYCLONE = 19

# ----------------------------------------------------------- air-handling duct --
# Duct is a BOUGHT item: Nolin Milling stocks primed gray air-handling duct,
# segmented elbows, round-to-round adaptors and the square-to-round transitions.
# _nolin.py holds their 2026 catalog pages as printed; everything below turns a
# sized diameter and a stated run into that catalog's own bill of material and
# applies MCE's buy-out divisor.
#
# What MCE puts on every air-relief duct run, unless the quote says otherwise:
DUCT_STANDARD_PACKAGE = (
    "Straight run in 10 ft flanged lengths, the elbows the layout needs, a hanger "
    "strap per length, and — where the fan discharges to atmosphere — a flanged "
    "bird screen and a shielded rain and snow hood.")
DUCT_HANGER_SPACING_FT = 10      # one strap per 10 ft length; confirm against the run
DUCT_DEFAULT_MATERIAL = "carbon"

# MCE's duct standard (Jason, 2026-09-29): 14 gauge, unless the line is carrying an
# abrasive material. Air-relief duct is normally carrying fines, which is why the
# light gauge holds up — a line carrying PRODUCT wears at the elbow heel long
# before the straight run goes, so it gets a removable back sweep elbow instead of
# a segmented one, and the back is the part that gets changed.
DUCT_SERVICE = [
    ("fines", "Fines — mill or cooler air relief"),
    ("product", "Product — the line carries material"),
    ("abrasive", "Abrasive — heavier gauge, and worth a look at sweep elbows"),
]
DUCT_DEFAULT_SERVICE = "fines"
DUCT_STANDARD_GAUGE = "14"
# 10 ga on abrasive service (Jason, 2026-09-29). It is a DEFAULT, not a rule —
# gauge on an abrasive line is application driven, and the things that move it are
# the material, the velocity and how long the plant wants the duct to last. A
# severely abrasive line at high velocity may want 7 ga; a mildly abrasive one at
# low velocity may be fine on the standard. So the service picks a starting point
# and `gauge` overrides it, rather than the quote pretending there is one answer.
DUCT_ABRASIVE_GAUGE = "10"
DUCT_SERVICE_GAUGE = {"fines": DUCT_STANDARD_GAUGE, "product": DUCT_STANDARD_GAUGE,
                      "abrasive": DUCT_ABRASIVE_GAUGE}
DUCT_DEFAULT_GAUGE = DUCT_STANDARD_GAUGE      # kept for callers that name it

# Removable back sweep elbows are NEVER automatic. They are rare in MCE's
# industry, they cost several times a segmented elbow, and a quote that carries
# them without anybody deciding to is a quote that loses on price for no reason.
# So they are an explicit opt-in, and the only thing the calculator does on its
# own is ASK — and only when the service is abrasive, which is the one case where
# the answer might be yes.
DUCT_SWEEP_DEFAULT = False
DUCT_GAUGE_NOTE = (
    f"Quoted in {DUCT_STANDARD_GAUGE} ga — MCE's standard for air-handling duct, "
    "which normally carries fines.")
DUCT_ABRASIVE_NOTE = (
    f"Abrasive service: quoted in {DUCT_ABRASIVE_GAUGE} ga, MCE's default for "
    "abrasive material. Gauge here is application driven — the material, the "
    "velocity and the life the plant wants all move it, and 7 ga is the answer on "
    "a genuinely severe line.")
DUCT_GAUGE_OVERRIDE_NOTE = (
    "Gauge set on this quote rather than taken from the service — "
    "{gauge} ga in place of the {standard} ga default.")
DUCT_GAUGES = [("", "By service — 14 ga standard, "
                    f"{DUCT_ABRASIVE_GAUGE} ga abrasive")] + [
    (g, f"{g} ga" if g != "1/4" else '1/4" wall') for g in ("14", "12", "10", "7", "1/4")]
DUCT_SWEEP_NOTE = (
    "Removable back sweep elbows, as asked for. A segmented elbow wears through at "
    "the heel on an abrasive line; a sweep lets the back be replaced without "
    "cutting the duct out of the ceiling.")


def _nolin_item(name, qty, unit_list, source):
    return {"name": name, "quantity": qty, "listUnit": round(unit_list, 2),
            "listExtended": round(qty * unit_list, 2), "source": source}


def duct_package(diameter_in, run_ft=0, elbows=0, adaptors=0, *,
                 gauge=None, material=DUCT_DEFAULT_MATERIAL,
                 service=DUCT_DEFAULT_SERVICE, sweep_elbows=DUCT_SWEEP_DEFAULT,
                 elbow_angle="90", to_atmosphere=True, transition_from=None,
                 spare_backs=0, quantity=1):
    """The catalog bill of material for a duct run, priced.

    Returns None when the diameter is off the end of Nolin's tables, which is the
    honest answer — 38 in and up is "call for pricing and availability" on the page
    itself, and this does not invent what the page will not print.
    """
    from . import _nolin

    dia = int(diameter_in or 0)
    if dia <= 0:
        return None
    if service not in DUCT_SERVICE_GAUGE:
        service = DUCT_DEFAULT_SERVICE
    overridden = bool(gauge) and gauge != DUCT_SERVICE_GAUGE[service]
    if not gauge:
        gauge = DUCT_SERVICE_GAUGE[service]
    sweeps = bool(sweep_elbows)
    # Nolin prints flanged primed gray duct in a fixed set of sizes, and its own
    # header sends everything from 3 in to 16 in to the spouting page instead. So a
    # size the duct table prints is bought as flanged duct; a small size it does not
    # is bought as plain-end spouting, primed, with clamp bands at the joints.
    spouted = dia not in _nolin.DUCT_STICK and dia <= 16
    items, warnings, questions = [], [], []

    if spouted:
        sp_dia, sp_row = _nolin._nearest(_nolin.SPOUTING_PER_FT, dia)
        if not sp_row:
            return None
        actual_gauge = next((g for g in _nolin.GAUGES[_nolin.GAUGE_ORDER.get(gauge, 0):]
                             if g in sp_row), None)
        if not actual_gauge:
            return None
        actual_dia = sp_dia
        per_ft = sp_row[actual_gauge]
        prime_ft = _nolin.band(_nolin.PRIMING_PER_FT, actual_dia) or 0
        warnings.append(
            f'{actual_dia}" is under the flanged ductwork table, so it is quoted as '
            "plain-end spouting with shop primer and clamp band joints — which is what "
            "the catalog's own ductwork page says to do below 16 in.")
    else:
        stick = _nolin.stick(dia, gauge)
        if not stick:
            return None
        stick_price, actual_dia, actual_gauge = stick
        per_ft = prime_ft = 0

    if actual_dia != dia:
        warnings.append(
            f'{dia}" is not a size Nolin prints — priced on the {actual_dia}", '
            "the next size the catalog carries.")
    if actual_gauge != gauge:
        warnings.append(f'{gauge} ga is not printed at {actual_dia}" — priced in '
                        f"{actual_gauge} ga.")

    lengths = math.ceil(run_ft / _nolin.STICK_FT) if run_ft else 0
    if run_ft and spouted:
        items.append(_nolin_item(
            f'{actual_dia}" dia spouting, {actual_gauge} ga, plain end',
            run_ft, per_ft, f"{_nolin.SOURCE} p. 3"))
        if prime_ft:
            items.append(_nolin_item("Shop coat gray primer", run_ft, prime_ft,
                                     f"{_nolin.SOURCE} p. 3"))
        clamp = _nolin.band(_nolin.CLAMP_BAND, actual_dia)
        if clamp:
            items.append(_nolin_item(f'{actual_dia}" two piece clamp band', lengths,
                                     clamp, f"{_nolin.SOURCE} p. 44"))
    elif run_ft:
        items.append(_nolin_item(
            f'{actual_dia}" dia duct, {actual_gauge} ga, {_nolin.STICK_FT} ft flanged length',
            lengths, stick_price, f"{_nolin.SOURCE} p. 43"))
    if run_ft:
        straps = _nolin.band(_nolin.HANGER_STRAP, actual_dia)
        if straps:
            items.append(_nolin_item(f'{actual_dia}" hanger strap', lengths, straps,
                                     f"{_nolin.SOURCE} p. 45"))
    if elbows:
        el = _nolin.sweep_elbow(actual_dia, elbow_angle) if sweeps else None
        if el:
            price, _d, centerline = el
            items.append(_nolin_item(
                f'{actual_dia}" {elbow_angle}° removable back sweep elbow, 10 ga, '
                f'{centerline}" centerline', elbows, price,
                f"{_nolin.SOURCE} p. 45"))
            if spare_backs:
                back = _nolin.sweep_back(actual_dia, elbow_angle)
                if back:
                    b_price, _bd, grade = back
                    items.append(_nolin_item(
                        f'{actual_dia}" {elbow_angle}° replacement back, '
                        f'{grade.replace("ga", " ga")}', spare_backs, b_price,
                        f"{_nolin.SOURCE} p. 45"))
        else:
            if sweeps:
                warnings.append(
                    f'Nolin prints no removable back sweep elbow at {actual_dia}" — '
                    "quoted as a segmented elbow. On a product line that is the part "
                    "that wears out first, so ask them to make one.")
            seg = _nolin.elbow(actual_dia, elbow_angle, gauge)
            if not seg:
                seg = None
            if seg:
                price, _d, el_gauge, centerline = seg
                items.append(_nolin_item(
                    f'{actual_dia}" {elbow_angle}° segmented elbow, {el_gauge} ga, '
                    f'{centerline}" centerline', elbows, price,
                    f"{_nolin.SOURCE} p. 43"))
    if adaptors:
        red = _nolin.reducer(actual_dia, max(actual_dia - 2, 4), gauge)
        if red:
            price, (large, small), red_gauge = red
            items.append(_nolin_item(
                f'{large}" to {small}" round adaptor, {red_gauge} ga', adaptors, price,
                f"{_nolin.SOURCE} p. 44"))
            warnings.append(
                f'Adaptor priced as the {large}" to {small}" reducer. Nolin prints a '
                "fixed set of reductions — give the actual pair and it prices exactly.")
    if transition_from:
        tr = _nolin.transition(transition_from, actual_dia, gauge)
        if tr:
            price, (sq, rd), tr_gauge = tr
            items.append(_nolin_item(
                f'{sq}" square to {rd}" round transition, {tr_gauge} ga', 1, price,
                f"{_nolin.SOURCE} p. 44"))
    if to_atmosphere:
        screen = _nolin.band(_nolin.BIRD_SCREEN_ROUND, actual_dia)
        hood = _nolin.band(_nolin.SHIELDED_RAIN_HOOD, actual_dia)
        if screen:
            items.append(_nolin_item(f'{actual_dia}" flanged bird screen discharge', 1,
                                     screen, f"{_nolin.SOURCE} p. 45"))
        if hood:
            items.append(_nolin_item(f'{actual_dia}" shielded rain and snow hood, 12 ga',
                                     1, hood, f"{_nolin.SOURCE} p. 45"))

    if not items:
        return None

    list_total = sum(i["listExtended"] for i in items)
    adder = _nolin.MATERIAL_ADDER.get(material, _nolin.MATERIAL_ADDER["carbon"])
    list_total *= adder["factor"]
    if material != "carbon":
        warnings.append(
            f'{adder["material"].capitalize()} priced at × {adder["factor"]:g} on the '
            f'carbon steel catalog price — the median of {adder["samples"]} sizes where '
            f'Nolin prints both ({adder["low"]:g}–{adder["high"]:g} across the range). '
            "The catalog prints ductwork in primed gray carbon only, so this is "
            "budgetary: Nolin quotes a firm price on the actual run.")

    basis = (f'{_nolin.SOURCE} ({_nolin.CATALOG_DATE}) list, '
             f'{adder["material"]}, at MCE\'s buy-out divisor {BUYOUT_DIVISOR:g}')
    if overridden:
        notes = [DUCT_GAUGE_OVERRIDE_NOTE.format(
            gauge=actual_gauge, standard=DUCT_SERVICE_GAUGE[service])]
    else:
        notes = [DUCT_ABRASIVE_NOTE if service == "abrasive" else DUCT_GAUGE_NOTE]

    # What the swap actually costs, either way round: quoted with sweeps, it is
    # what they added; quoted without on an abrasive line, it is what the question
    # is worth. Nobody should have to work it out on the phone.
    seg = _nolin.elbow(actual_dia, elbow_angle, gauge) if elbows else None
    sw = _nolin.sweep_elbow(actual_dia, elbow_angle) if elbows else None
    delta = ((sw[0] - seg[0]) * elbows / BUYOUT_DIVISOR) if (seg and sw) else None

    if sweeps:
        notes.append(DUCT_SWEEP_NOTE)
        if delta:
            notes.append(
                f'The {elbows} sweep elbow{"s" if elbows != 1 else ""} add '
                f"${delta:,.0f} over segmented elbows at this size.")
    elif service == "abrasive" and elbows:
        # the one question worth asking, and only here
        questions.append(
            "Is this line abrasive enough to want removable back sweep elbows? "
            "It is quoted with segmented elbows, which is right nearly every time "
            + (f"— sweeps would add about ${delta:,.0f}. " if delta else "— ")
            + "Say yes only if the material is genuinely cutting elbows out, "
            "because on that line the heel is what fails first.")

    return {"items": items, "listTotal": round(list_total, 2),
            "total": round(buyout_price(list_total) * quantity, 2),
            "diameter": actual_dia, "gauge": actual_gauge, "material": material,
            "service": service, "sweepElbows": sweeps, "notes": notes,
            "questions": questions,
            "sweepPremium": round(delta, 2) if delta else None,
            "lengths": lengths, "spouting": spouted, "basis": basis, "warnings": warnings,
            "terms": _nolin.TERMS}


def duct_price(diameter_in, run_ft=0, elbows=0, adaptors=0, **kw):
    """(price, basis) for a duct run off Nolin's catalog, or None if it is off the
    end of their tables."""
    pkg = duct_package(diameter_in, run_ft, elbows, adaptors, **kw)
    if not pkg:
        return None
    return pkg["total"], pkg["basis"]


# A venturi pickup takes the mill discharge straight into the air stream: a venturi
# throat under the mill and an adaptor that opens out to the duct diameter. It is
# the same item the price book calls a DROP DOWN AIR PAN — different wording, one
# product (Jason, 2026-09-29) — so it prices off that mill's pan line.
VENTURI_PICKUP_SCOPE = [
    "Venturi pickup fitting under the mill discharge, so the ground product is picked "
    "up into the air stream without a plenum",
    "Air adaptor from the venturi throat out to the duct diameter",
    "Replaces the plenum chamber and the discharge screw: the product leaves the mill "
    "in the air and is collected at the cyclone",
]



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
# MCE buys its protection through High Tech Duct Werks (Darryl Lind), who is the
# Florida rep for Boss Products. Four documents are on record and between them they
# price the whole package:
#
#   Est 7659      2026-08-28  Ductwerks -> MCE, the complete NFPA 660 package for a
#                             lumber cyclone: vent panel, burst sensor, certified
#                             rotary valve, two flap isolation valves, the UL control
#                             panel and the dust level sensors, less 15% OEM discount
#   ref 0609-RCRI 2026-06-09  Ductwerks -> MCE, 36" x 44" panels for a corn mill
#   Q-25602       2026-05-07  Boss -> Ductwerks, domed vs flameless for the XM-4460
#                             plenum bin vent. DISTRIBUTOR pricing, not MCE's cost
#   Q-26693       2026-07-23  Ductwerks -> MCE for Nix; the PDF is a scan this
#                             project cannot read, but Est 7659 prices the same panel
#
# Vent AREA still comes from the vendor's calculation against a dust hazard
# analysis. Nothing here sizes a vent.
EXPLOSION_VENT_VENDOR = "High Tech Duct Werks, Inc."
EXPLOSION_VENT_CONTACT = "Darryl Lind · ductwerks@aol.com · 772-473-0538"
# Darryl's estimate carried a 15% OEM discount off every line, so that is what MCE
# actually pays on the items it covered. Items quoted in an email without it are
# carried at the quoted rate — conservative, and the open items say so.
DUCTWERKS_OEM_DISCOUNT = 0.15
# Boss quotes its distributors off a list sheet at list less 25% ("your net cost is
# -25% off the above list pricing", 2024-12-06). That is DUCTWERKS' discount, not
# MCE's, and it is recorded so nobody mistakes a Boss-to-Ductwerks figure for a cost
# MCE can buy at.
BOSS_LIST_DISCOUNT = 0.25
BOSS_LIST_PRICES = {
    '18" VDL HT certified rotary valve, 460 V, 15 RPM':
        (15856.00, "2024-12-06", "Boss list via High Tech Duct Werks"),
    '18" VDL HT certified rotary valve, 460 V, 30 RPM':
        (16099.00, "2024-12-06", "Boss list via High Tech Duct Werks"),
    "Spark detection, single zone":
        (9023.00, "2024-10-29", "Boss Raptor, via High Tech Duct Werks"),
}


def _net(rate, discount=0.0):
    """MCE's cost from a quoted rate and whatever discount that quote carried."""
    return rate * (1 - discount)


# ---- vent panels -------------------------------------------------------------
# `rate` is as quoted to MCE; `discount` is what that document applied. Price does
# NOT scale with panel area — the 23" x 36" is $1,614 and the 36" x 44" is $2,775,
# so a panel is priced from its own quote, never interpolated from another size.
VENT_PANELS = {
    "23x36": {"model": 'EV-VD 23" x 36"', "rate": 1614.00,
              "discount": DUCTWERKS_OEM_DISCOUNT, "date": "2026-08-28",
              "source": "High Tech Duct Werks estimate 7659",
              "size": '23" x 36" (586 x 920 mm)', "relief_sqft": None},
    "36x44": {"model": "EV-VD9151118", "rate": 2775.00, "discount": 0.0,
              "date": "2026-06-09",
              "source": "High Tech Duct Werks, EV calc ref 0609-RCRI",
              "size": '36" x 44" (915 x 1118 mm)', "relief_sqft": 10.9792},
}
# The size MCE has bought most recently, and on two jobs. Not a sizing decision —
# the vendor's calculation picks the real one, and every other size on file prices
# from its own quote.
VENT_PANEL_DEFAULT = "23x36"
VENT_PANEL_SPEC = [
    "EV-VD domed vent panel, 304L stainless steel with integrated flange and EPDM "
    "gasket — the domed form is for negative-pressure service with frequent cycling "
    "or pulsation, which is what a pulse-cleaned filter is",
    "Pstat 0.1 bar (1.45 PSI) ±15%, rated to Kst 500 bar·m/s, Pmax < 12 bar, "
    'Pred max < 1.8 bar, max vacuum -80" WG',
    "Certified ATEX II GD, EN 14491, EN 14994, EN 14797, EN 1127.1 "
    "(INERIS15ATEX0001)",
]
VENT_SENSOR = {
    "rate": 445.00, "discount": DUCTWERKS_OEM_DISCOUNT, "date": "2026-08-28",
    "source": "High Tech Duct Werks estimate 7659 (same rate as ref 0609-RCRI)",
    "spec": "Magnetic burst sensor for the explosion panel — breaking signal, "
            "12-60 VDC, ATEX zone 21",
}

# ---- isolation and shutdown, all from Est 7659 -------------------------------
# NFPA 660 wants the deflagration kept out of everything connected to the vessel.
# Two different devices do that and the lumber job bought both: a certified rotary
# valve on the material discharge, and flap valves in the duct. The flap valves are
# passive — held open by flow, slammed shut by the pressure front — and Boss's own
# installation drawing puts one on the INLET and one on the OUTLET of the vessel.
ISOLATION_ITEMS = {
    "rotary": {
        "name": "VDL HT250 certified explosion-proof rotary valve",
        "rate": 7121.00, "qty": 1, "discount": DUCTWERKS_OEM_DISCOUNT,
        "desc": 'Certified explosion-proof rotary valve, 10" — isolates the material '
                "discharge so a deflagration cannot propagate back through it"},
    "flap": {
        "name": "Vigilex Vigiflap certified explosion isolation valve",
        "rate": 4410.00, "qty": 2, "discount": DUCTWERKS_OEM_DISCOUNT,
        "desc": 'Passive flap isolation valve, 10" flanged ends, with shutdown '
                "sensors. One on the inlet and one on the outlet of the vessel: held "
                "open by process flow, closed by the pressure front, so flame and "
                "pressure stay out of the connected duct"},
    "control": {
        "name": "UL listed explosion protection control panel",
        "rate": 2835.00, "qty": 1, "discount": DUCTWERKS_OEM_DISCOUNT,
        "desc": "UL listed control panel that takes the vent burst sensor and the "
                "isolation valve sensors and signals the plant shutdown"},
    "level": {
        "name": "Organic dust level sensors for the isolation valves",
        "rate": 639.00, "qty": 2, "discount": DUCTWERKS_OEM_DISCOUNT,
        "desc": "Level sensors on the flap valves, so a valve buried in accumulated "
                "dust is detected rather than found after an event"},
}
# The whole package as Darryl quoted it, for a sanity check against anything built
# from the parts above.
NFPA_PACKAGE_ON_RECORD = {
    "estimate": "7659", "date": "2026-08-28", "standard": "NFPA 660",
    "job": "lumber project with cyclone, 10\" valves",
    "subtotal": 22113.00, "discount": DUCTWERKS_OEM_DISCOUNT, "total": 18796.05,
    "terms": "freight not included; 50% on order, 50% net 30",
}

# ---- flameless, which MCE has never bought ------------------------------------
# Boss quoted Ductwerks both ways for the same vessel on Q-25602: two domed panels
# at $2,758 each, or THREE flameless assemblies at $46,623 each. Those are the
# distributor's own costs, not MCE's, so they never reach a price on a proposal —
# but they are the reason flameless is a different conversation, not a line swap.
FLAMELESS_ON_RECORD = {
    "job": "XM-4460 plenum bin vent", "date": "2026-05-07", "quote": "Q-25602",
    "domed_panels": 2, "flameless_panels": 3,
    "domed_each_distributor": 2758.00, "flameless_each_distributor": 46623.00,
    "domed_total_distributor": 5516.00, "flameless_total_distributor": 139869.00,
    "model": 'EV-VQ11301130-VL, 44" x 44", arrestor in painted mild steel with an '
             "EV-VL 304L panel, inductive breaking-signal sensor included",
    "note": "distributor-level pricing (Boss to High Tech Duct Werks) — MCE's own "
            "cost is higher and has never been quoted, so flameless stays on request",
}

# ---- dust figures MCE has actually worked to ---------------------------------
# (low, high). A range means the vendor was given a range; the DHA replaces it.
DUST_ON_RECORD = {
    "wood": {"kst": (150, 150), "pmax": (8.0, 8.0),
             "source": "Nix Forest Industries, coarse wood dust through 1/4\" screen"},
    "corn": {"kst": (130, 150), "pmax": (8.0, 9.0),
             "source": "MCE's own figures for ground corn, given to the vent vendor"},
}

VENT_SELECTIONS = [
    {"job": "Nix Forest Industries", "quote": "Q-26693 (ref 72326RN / 0723-R0UD)",
     "date": "2026-07-23", "material": 'wood ground through a 1/4" screen',
     "kst": 150, "pmax": 8.0, "pred": 0.2,
     "vessel": "25AST-8 dust filter, vent below the hopper on the screw conveyor",
     "selection": '1 x EV-VD domed, 23" x 36" panel', "type": "domed"},
    {"job": "lumber project with cyclone", "quote": "estimate 7659",
     "date": "2026-08-28", "material": "wood / lumber dust",
     "kst": 150, "pmax": 8.0, "pred": 0.2,
     "vessel": 'cyclone with 10" valves, to comply with NFPA 660',
     "selection": '1 x EV-VD domed, 23" x 36" panel, plus a certified rotary valve '
                  "and two flap isolation valves", "type": "domed"},
    # The vendor's calc table for this one is in the attachment; what MCE stated to
    # him was the range, so the range is what goes on record here.
    {"job": "corn mill air system", "quote": "EV calc ref 0609-RCRI",
     "date": "2026-06-09", "material": "ground corn",
     "kst": (130, 150), "pmax": (8.0, 9.0), "pred": 0.2,
     "vessel": "below the baghouse extension, above the discharge screw",
     "selection": '2 x EV-VD domed, 36" x 44" panels', "type": "domed"},
    {"job": "XM-4460 plenum bin vent", "quote": "Q-25602 (refs 0507-BR82, 0507-RCCO)",
     "date": "2026-05-07", "material": "corn ground to 500 micron",
     "kst": 150, "pmax": 9.0, "pred": 0.2,
     "vessel": "bin vent bolted to the plenum chamber, indoors, 37.56 ft² plenum",
     "selection": '2 x EV-VD domed 44" x 44", or 3 x EV-VQ flameless 44" x 44"',
     "type": "both"},
]

# Darryl's installation rule, verbatim in substance. It is why MCE fabricates an
# adaptor section: the vent needs flat unobstructed housing wall, and a bin vent
# bolted straight onto a plenum chamber does not offer one.
VENT_INSTALL_RULE = (
    "Explosion vents install on a clear, unobstructed flat surface on the main body "
    "of the collector. Areas near structural supports, motors, ducts, platforms, "
    "corners or hopper sections have to be avoided, or the panel cannot relieve "
    "properly.")
VENT_ADAPTOR_SCOPE = [
    "Fabricated adaptor section below the bin vent, drilled and flanged for the "
    "vent panel, so the panel sits on flat unobstructed wall rather than on the "
    "housing or the hopper",
    "Panel mounted sideways, ducted through the building wall with a rain hood "
    "outside — a lasered and bent flange welded to the adaptor, bolted to the duct",
    'Nix took roughly a 40" x 28" duct about 5 ft long through the wall',
]

# MCE's own certified rotary valves also carry the NFPA 69 flame-passage
# certification, and are already in AIRLOCK_QUOTES with sell prices.
ISOLATION_NOTE = ("NFPA 69 isolation is served by a certified rotary valve — the "
                  "flex-tip design is certified to prevent flame passage per NFPA 69 "
                  "12.2.4.3.6. See the certified-valve option.")


def vent_panel(size=None):
    """(key, model, sell, cost, date, source, size text, relief ft²) or None.

    Only sizes MCE has a quote for. A panel is never priced by scaling another
    panel's area: the two on file are $1,614 and $2,775 for 5.75 and 11.0 ft².
    """
    key = size or VENT_PANEL_DEFAULT
    row = VENT_PANELS.get(key)
    if not row:
        return None
    cost = _net(row["rate"], row["discount"])
    return (key, row["model"], buyout_price(cost), cost, row["date"], row["source"],
            row["size"], row["relief_sqft"])


def vent_panel_menu():
    """Every panel size on file, as (size text, sell price) — cheapest first."""
    rows = [(k, VENT_PANELS[k]) for k in VENT_PANELS]
    out = []
    for key, row in rows:
        cost = _net(row["rate"], row["discount"])
        out.append((row["size"], buyout_price(cost)))
    return sorted(out, key=lambda r: r[1])


def vent_sensor():
    """(sell, cost, date, source, spec) for one burst indicator sensor."""
    v = VENT_SENSOR
    cost = _net(v["rate"], v["discount"])
    return (buyout_price(cost), cost, v["date"], v["source"], v["spec"])


def protection_item(key):
    """(name, sell each, cost each, quoted qty, date, source, description)."""
    row = ISOLATION_ITEMS.get(key)
    if not row:
        return None
    cost = _net(row["rate"], row["discount"])
    return (row["name"], buyout_price(cost), cost, row["qty"],
            NFPA_PACKAGE_ON_RECORD["date"],
            f'High Tech Duct Werks estimate {NFPA_PACKAGE_ON_RECORD["estimate"]}',
            row["desc"])


def dust_on_record(material):
    """(name, record) for a dust MCE has figures for, or None."""
    want = str(material or "").lower()
    for name, rec in DUST_ON_RECORD.items():
        if name in want:
            return name, rec
    return None


def _span(value, unit=""):
    """A figure, or a range where the vendor was given one. Never averaged."""
    if isinstance(value, (tuple, list)):
        lo, hi = value
        if lo != hi:
            return f"{lo:g}-{hi:g}{unit}"
        value = lo
    return f"{value:g}{unit}"


def vent_selection_lines():
    """What comparable vessels actually took — for an internal note, not a quote."""
    out = []
    for sel in VENT_SELECTIONS:
        out.append(f'{sel["job"]} ({sel["date"]}, {sel["quote"]}): {sel["material"]}, '
                   f'Kst {_span(sel["kst"])}, Pmax {_span(sel["pmax"])}, '
                   f'Pred {_span(sel["pred"])} — {sel["vessel"]} took {sel["selection"]}')
    return out


def explosion_vent_basis():
    """The whole vent basis, as lines for an internal note."""
    f = FLAMELESS_ON_RECORD
    return ([f"Sized and quoted by {EXPLOSION_VENT_VENDOR} ({EXPLOSION_VENT_CONTACT})"]
            + vent_selection_lines()
            + [f'Flameless: on {f["job"]} ({f["quote"]}) the same vessel took '
               f'{f["flameless_panels"]} flameless assemblies at '
               f'${f["flameless_each_distributor"]:,.0f} each against '
               f'{f["domed_panels"]} domed at ${f["domed_each_distributor"]:,.0f} — '
               f'${f["flameless_total_distributor"]:,.0f} vs '
               f'${f["domed_total_distributor"]:,.0f}, {f["note"]}',
               VENT_INSTALL_RULE])
