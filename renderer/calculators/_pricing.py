#!/usr/bin/env python3
"""The pricing basis: one set of escalation factors, everything else derived.

MCE prices its own equipment off one model, which the calculator states on its
own face: *Bliss Jan-2016 pricebook × multiplier ... raise it as steel moves.*
The Bliss base figures are engineering history and do not change. What changes is
the ESCALATION — the multiplier that carries a 2016 book to today's money — and
that is the only thing anyone should ever edit.

Before this module those factors lived in four places: the calculator's form
defaults, the port's fallbacks, the registry's field defaults and the price book
on someone's desktop. Four copies drift, and they had: the book's implied feeder
factor was 1.515 against the calculator's 2.00, a 32% gap on every feeder line.

Now there is one place. A vendor increase or a steel move is applied here, and:

    pricing_cli.py sync-tools   writes the factors into the calculator HTML
    pricing_cli.py book         regenerates the price book workbook
    the quote builder           reads them through the ports, unchanged

so the calculator, the book and the CRM cannot disagree without the test saying so.
"""
import datetime

from ._book_inputs import MILL_OPTIONS
from ._data import FEEDER_PRICING, MILL_PRICING

BLISS_BASIS = "Bliss Jan-2016 price book"

# --------------------------------------------------------------- the factors --
# `value` is what everything downstream uses. `since` and `source` are how it got
# there. Change a value ONLY through apply_increase() so the log stays true.
FACTORS = {
    "mill": {
        "value": 1.73, "unit": f"× {BLISS_BASIS}", "since": "2026-09-29",
        "source": "as found in hammermill-sizing-calculator.html",
        "note": 'CRM list tracks ~1.73× on 38"/44" frames and ~1.69× on 22"',
    },
    "feeder": {
        "value": 2.00, "unit": f"× {BLISS_BASIS}", "since": "2026-09-29",
        "source": "as found in hammermill-sizing-calculator.html",
        "note": "feeders priced at 2× book per MCE practice",
    },
    "plenum_duty": {
        "value": 1.35, "unit": "× structure weight", "since": "2026-09-29",
        "source": "as found in hammermill-sizing-calculator.html",
        "note": '10 ga → 7 ga ≈ 1.35 · → 3/16" ≈ 1.40 · → 1/4" ≈ 1.86',
    },
    "plenum_rate": {
        "value": 15.25, "unit": "$/lb", "since": "2026-09-29",
        "source": "as found in hammermill-sizing-calculator.html",
        "note": "Bliss 2017 structure basis $8.80/lb × escalation — raise it as steel moves",
    },
    # Options the calculator has no formula for. They escalate as one scope until
    # someone has a better rule for them.
    "mill_options": {
        "value": 1.00, "unit": "× the price book as received", "since": "2026-09-29",
        "source": "MCE hammermill price book (JB), received 2026-09-29",
        "note": "air pan, sanitary design, AR plates, vibration pads, magnet adapter, "
                "rock trap and SF300 magnet",
    },
}

# Append-only. Every entry says what moved, by how much, when and who saw it.
ESCALATIONS = [
    {"scope": "*", "kind": "seed", "to": None, "effective": "2026-09-29",
     "source": "factors as found in the calculator and the price book",
     "note": "starting point — nothing was changed when the basis was created"},
]

# What the price book SHOULD say if it were regenerated from the factors above.
# Where the received book disagrees, `pricing_cli.py check` prints the delta and
# nothing is quietly reconciled — see docs/quote-builder.md.
KNOWN_DIVERGENCE = {
    "feeder": {"book_implies": 1.515, "basis": 2.00,
               "evidence": "all 36 rows of the 10\" tables, exact to the dollar "
                           "(tight tolerance is 2.000 in both)"},
    "mill": {"book_implies": "≈1.631 on 19\"/22\", ≈1.655 on 38\"/44\"", "basis": 1.73,
             "evidence": "32 models, no single factor fits; XM-1920 is an outlier "
                         "at 1.4925"},
}


# ------------------------------------------------------- what is NOT priced --
# Everything MCE quotes is priced from something on file. These two are not, and
# saying so in one place beats each of them being a surprise on a proposal. Each
# names the ONE input that would close it.
UNPRICED = {
    "ductwork": {
        "needs": "Nolin Milling's air-handling pages (43-45 of the 2026 catalog): "
                 "primed gray duct per foot and segmented elbows by size",
        "why": "duct is a bought item — Nolin stocks it, High Tech Duct Werks sells "
               "Nordfab — so it is never estimated from the steel",
        "one_edit": "fill DUCT_PRICES in _vendor.py; every duct line then prices "
                    "itself from its own bill of material",
        "blocked_by": "Drive's text extraction stops at page 32 and the 37 MB file is "
                      "over the download limit — the pages are needed as images or a "
                      "trimmed PDF",
    },
    "fan": {
        "needs": "MCE's XF fan sizing calculator, and the XF price list behind it",
        "why": "MCE builds its own XF fans — a fan price regressed off another "
               "maker's catalogue is not MCE's price, whatever its error band",
        "one_edit": "vendor the XF calculator into tools/ the way the other six "
                    "were, port it, and the fan line prices itself",
    },
}

# A venturi pickup IS the drop down air pan — same item, different wording
# (Jason, 2026-09-29). So it prices off the book's air pan line for that mill,
# and the quote calls it what the book calls it.
def venturi_price(model=None):
    """(price, basis) for a venturi pickup: the mill's drop down air pan."""
    found = air_pan_price(model)
    if not found:
        return None
    price, basis = found
    return price, basis + " — the book's drop down air pan is this same item"


def factor(scope):
    """The live escalation factor for a scope."""
    return FACTORS[scope]["value"]


def provenance(scope):
    f = FACTORS[scope]
    return f'{f["value"]:g} {f["unit"]} — {f["source"]}, {f["since"]}'


def apply_increase(scope, pct=None, to=None, effective=None, source=""):
    """Record a price move and return the new factor.

    Either a percentage (what a vendor letter or a steel index gives you) or an
    absolute new value. The caller writes the result back with pricing_cli.
    """
    if scope not in FACTORS:
        raise KeyError(f"unknown pricing scope: {scope}")
    if (pct is None) == (to is None):
        raise ValueError("give exactly one of pct= or to=")
    old = FACTORS[scope]["value"]
    new = round(old * (1 + pct / 100), 4) if pct is not None else float(to)
    entry = {"scope": scope, "kind": "increase" if new > old else "decrease",
             "from": old, "to": new, "pct": pct,
             "effective": effective or datetime.date.today().isoformat(),
             "source": source}
    return new, entry


# ------------------------------------------------------- derived price lists --

def mill_price(model):
    """Bliss base × the mill factor — what the calculator quotes."""
    row = MILL_PRICING.get(model)
    if not row:
        return None
    return round(row["bliss"] * factor("mill"))


def feeder_price(diameter_in, cup_type, rows, clean=None):
    """Bliss base (+ magnet/cleanout) × the feeder factor."""
    table = FEEDER_PRICING.get(f"d{int(diameter_in)}")
    if not table or cup_type not in table:
        return None
    try:
        i = FEEDER_PRICING["rows"].index(int(rows))
    except ValueError:
        return None
    base = table[cup_type][i]
    if clean:
        base += FEEDER_PRICING["clean"][clean][i]
    return round(base * factor("feeder"))


def mill_option(model, option):
    """A book option price, escalated by the mill_options factor."""
    row = MILL_OPTIONS.get(model) or {}
    value = row.get(option)
    if value is None:
        return None
    return round(value * factor("mill_options"))


def air_pan_price(model):
    """(price, basis) for the drop-down air pan on this mill, or None."""
    want = str(model or "").strip().upper()
    if want and not want.startswith("XM-"):
        want = "XM-" + want.lstrip("XM").lstrip("-")
    price = mill_option(want, "air_pan")
    if price is None:
        return None
    src = FACTORS["mill_options"]["source"]
    return (float(price), f"{want} drop-down air pan at ${price:,.0f} from {src}")


def plenum_price(bliss_weight_lb):
    """Structure weight × duty factor × the rate, the way the calculator does."""
    return round(bliss_weight_lb * factor("plenum_duty") * factor("plenum_rate"))
