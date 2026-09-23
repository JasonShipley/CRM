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
# Screw Conveyor Corporation, complete units: conveyor + drive, assembled,
# net cost ex-factory. Each entry records what was actually quoted, because the
# material matters as much as the size — a stainless unit carries a large
# premium over the carbon-steel equivalent.
SCREW_MARKUP = 1 / 0.8   # "We will divide by 0.8 for pricing" — Jason, 2026-01-09

SCREW_BASES = [
    {
        "dia": 9, "length_ft": 8.0, "cost": 6175.00,
        "material": "carbon steel", "stainless": False,
        "drive": "1 HP Baldor, Dodge reducer, 48 RPM",
        "quote": "SCC H51445AW", "date": datetime.date(2026, 6, 29),
        "duty": "400 CFH (4,000 PPH) sawdust at 10 PCF, 45% trough loading",
    },
    {
        # Ordered on PO 40140 / SCC order 175260. All-stainless: T304 screw,
        # pipe, trough, cover and hardware, for rice bran.
        "dia": 12, "length_ft": 20.0, "cost": 15495.00,
        "material": "T304 stainless", "stainless": True,
        "drive": "3 HP Nord shaft-mount gearmotor, 42 RPM",
        "quote": "SCC H51032CK", "date": datetime.date(2026, 5, 6),
        "duty": "10 TPH (572 CFH) rice bran at 32-35 PCF, 30% trough loading",
    },
]


def screw_basis_for(diameter_in, length_ft=None):
    """Pick the vendor basis to budget a screw conveyor from.

    Prefers the basis for the calculated diameter, but only when that basis is
    long enough to stand in for the run — stretching an 8 ft quote over a 12 ft
    conveyor understates it. Otherwise it steps up to the next basis that does
    cover the length, which quotes high rather than low. Returns
    (basis, substituted) or (None, False).
    """
    dia = int(diameter_in)
    exact = next((b for b in SCREW_BASES if b["dia"] == dia), None)
    if exact and (length_ft is None or length_ft <= exact["length_ft"] + 0.5):
        return exact, False
    covering = [b for b in SCREW_BASES
                if b["dia"] >= dia and (length_ft is None
                                        or length_ft <= b["length_ft"] + 0.5)]
    if covering:
        best = min(covering, key=lambda b: (b["dia"], b["cost"]))
        return best, best is not exact
    # Nothing on file is long enough. Fall back to the longest basis at or above
    # the diameter (else the longest on file) so a long run budgets high rather
    # than low; the caller states the gap either way.
    pool = [b for b in SCREW_BASES if b["dia"] >= dia] or SCREW_BASES
    best = max(pool, key=lambda b: (b["length_ft"], b["dia"]))
    return best, best is not exact


def fan_for(baghouse_model):
    """(fan, duty, rpm, motor, weight, cost, assumed) or None."""
    row = AIRPRO_FANS.get(baghouse_model)
    if not row:
        return None
    return (*row, baghouse_model in AIRPRO_ASSUMED)


def fan_quote_stale(today=None):
    return (today or datetime.date.today()) > AIRPRO_QUOTE_EXPIRES
