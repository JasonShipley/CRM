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
    return (today or datetime.date.today()) > AIRPRO_QUOTE_EXPIRES
