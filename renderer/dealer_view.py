#!/usr/bin/env python3
"""What a dealer may see — one filter, used everywhere a dealer is answered.

Dealers quote MCE equipment at list price. They never see what MCE pays for it
or who MCE buys it from: no vendor names, vendor quote numbers, cost figures,
markups or pricing basis, and none of the internal open items a draft carries
for MCE. Calculator results and quotes are full of that — it is the audit trail
MCE's own staff rely on — so this module does not try to delete the bad parts.
It copies out the parts a dealer needs (an allowlist) and then drops any line of
text inside them that still names a vendor or a cost.

    dealer_view.calc(result)     a calculator result, for /api/calc
    dealer_view.quote(quote)     a quote dict, for interpret, drafts and views
    dealer_view.locked_inputs    inputs a dealer may not set (pricing factors)
    dealer_view.is_internal(s)   would this text tell a dealer something internal

tests/test_dealer_view.py runs every calculator and the intake quotes through
this and checks nothing internal survives.
"""
import copy
import re

# Who MCE buys from, and whose prices sit behind MCE's. Matched as words, any case.
VENDORS = ["AirPro", "Air Pro", "Airlanco", "Prater", "Boss Products", "Boss",
           "LETEK", "Nolin", "Kice", "IAP", "Bliss", "CPM", "Insta-Pro", "Winsmith",
           "Baldor", "Twin City", "Donaldson", "Camfil", "NYB",
           "New York Blower", "PneuJet"]

_PATTERNS = [re.compile(r"\b" + re.escape(v) + r"\b", re.I) for v in VENDORS] + [
    re.compile(p, re.I) for p in (
        r"\bKT\d{6,}",                 # Prater quote numbers
        r"\bQ-?\d{5,}",                # AirPro / Boss quote numbers
        r"\bEst\.? ?\d{3,}",           # estimate numbers
        r"\bquote \d{4,}",             # "quote 024350"
        r"\bPO \d{4,}",
        r"\bcosts?\b", r"\bbuy-?out\b", r"\bmark-?up\b", r"\bmargin on\b",
        r"\bprice basis\b", r"\bpricing basis\b", r"\bbasis \$", r"\bCRM list\b",
        r"\bdistributor\b", r"\bnet to MCE\b", r"\bMCE pays\b",
        r"÷ ?0\.\d", r"\bdivisor\b",
    )]

# Pricing factors on the calculator forms. A dealer quotes at list, so these
# are fixed at MCE's own values whatever a dealer's browser sends.
locked_inputs = {"hammermill": {"millMult", "feederMult", "plenumDuty", "plenumRate"}}

CALC_KEEP = ("calculator", "key", "error", "formula", "model", "total", "needsPrice")
LINE_KEEP = ("name", "description", "quantity", "unitPrice", "unitDiscount",
             "discountPercent", "amount", "sku", "needsPrice", "budgetPrice")
OPTION_KEEP = ("ref", "name", "description", "quantity", "unitPrice", "needsPrice",
               "budgetPrice")


def is_internal(text):
    s = str(text or "")
    return any(p.search(s) for p in _PATTERNS)


def _clean_text(text):
    """Drop the lines of a multi-line text that carry anything internal."""
    if text is None:
        return text
    lines = str(text).split("\n")
    return "\n".join(l for l in lines if not is_internal(l))


def clean_sentences(text):
    """Drop the sentences, dash clauses and comma clauses of a blurb that are
    internal, keeping the rest readable — "Duty to fan selection — … with the
    RFQ block MCE sends to AirPro" keeps its first half."""
    pieces = re.split(r"((?<=[.!?])\s+|\s+[—–]\s+|,\s+)", str(text or ""))
    out = []
    pending_sep = ""
    dropped_end = False
    for i, piece in enumerate(pieces):
        if i % 2:
            pending_sep = pending_sep or piece
            continue
        if not piece or is_internal(piece):
            dropped_end = dropped_end or piece.endswith((".", "!", "?"))
            continue
        if out:
            sep = pending_sep
            if dropped_end or (not sep.strip() and not out[-1].endswith((".", "!", "?"))):
                sep = ". "              # a sentence end was dropped between these
            out.append(sep)
        out.append(piece)
        pending_sep = ""
        dropped_end = False
    text = "".join(out).strip()
    return text if not text or text.endswith((".", "!", "?")) else text + "."


def _clean_rows(rows, keep):
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        clean = {k: copy.deepcopy(row[k]) for k in keep if k in row}
        if is_internal(clean.get("name")):
            kept = [p for p in re.split(r"\s+[—–-]\s+", clean["name"]) if not is_internal(p)]
            clean["name"] = " — ".join(kept) or "Item"
        if "description" in clean:
            clean["description"] = _clean_text(clean["description"])
        if "sku" in clean and is_internal(clean["sku"]):
            clean["sku"] = ""
        out.append(clean)
    return out


def _clean_outputs(outputs):
    out = []
    for o in outputs or []:
        if not isinstance(o, dict):
            continue
        if is_internal(o.get("label")) or is_internal(o.get("value")):
            continue
        o = {k: o[k] for k in ("label", "value", "unit", "note", "headline") if k in o}
        if is_internal(o.get("note")):
            o.pop("note")
        out.append(o)
    return out


def _clean_strings(items):
    return [s for s in (items or []) if isinstance(s, str) and not is_internal(s)]


def calc(result):
    """A calculator result as a dealer sees it."""
    result = result or {}
    out = {k: copy.deepcopy(result[k]) for k in CALC_KEEP if k in result}
    if isinstance(out.get("model"), (dict, list)) or is_internal(out.get("model")):
        out.pop("model", None)
    if is_internal(out.get("formula")):
        out.pop("formula")
    out["outputs"] = _clean_outputs(result.get("outputs"))
    out["warnings"] = _clean_strings(result.get("warnings"))
    out["notes"] = _clean_strings(result.get("notes"))
    out["lines"] = _clean_rows(result.get("lines"), LINE_KEEP)
    out["options"] = _clean_rows(result.get("options"), OPTION_KEEP)
    return out


def quote(q):
    """A quote (built, drafted or saved) as a dealer sees it."""
    q = copy.deepcopy(q or {})
    q.pop("openItems", None)          # MCE's internal list, never a dealer's
    q["sizing"] = []                  # the audit trail carries every basis
    for key, keep in (("lines", LINE_KEEP), ("netItems", LINE_KEEP),
                      ("options", OPTION_KEEP)):
        if key in q:
            q[key] = _clean_rows(q.get(key), keep)
    if "designBasis" in q:
        rows = []
        for row in q.get("designBasis") or []:
            if not isinstance(row, dict):
                continue
            if any(is_internal(row.get(k)) for k in ("parameter", "value")):
                continue
            row = dict(row)
            if is_internal(row.get("notes")):
                row["notes"] = ""
            rows.append(row)
        q["designBasis"] = rows
    for key in ("byOthers", "schedule"):
        if isinstance(q.get(key), list):
            q[key] = [r for r in q[key]
                      if not (isinstance(r, str) and is_internal(r))
                      and not (isinstance(r, dict)
                               and any(is_internal(v) for v in r.values()))]
    for key in ("comments", "terms", "project", "name", "sourceRequest"):
        if isinstance(q.get(key), str):
            q[key] = _clean_text(q[key])
    return q


def calculators_for_dealer(calcs):
    """The calculator registry as a dealer's form and assistant see it."""
    return {k: {**c, "blurb": clean_sentences(c.get("blurb", "")),
                "fields": form_fields(c["fields"], k)}
            for k, c in calcs.items()}


def form_fields(fields, key):
    """A calculator's form fields with the pricing factors removed and any
    internal help text dropped, for the dealer's quote form."""
    locked = locked_inputs.get(key, set())
    out = []
    for f in fields:
        if f.get("key") in locked:
            continue
        f = dict(f)
        if is_internal(f.get("help")):
            f["help"] = clean_sentences(f["help"])
        if f.get("options"):
            f["options"] = [_clean_option(o) for o in f["options"]]
        out.append(f)
    return out


def _clean_option(option):
    """A select option with any vendor clause taken out of its label."""
    if isinstance(option, (list, tuple)) and len(option) >= 2 and is_internal(option[1]):
        label = clean_sentences(option[1]).rstrip(".") or str(option[0])
        return type(option)([option[0], label, *option[2:]])
    return option


def product_defaults(defaults):
    """The product presets for the hammermill form, without the price-book
    references their chart labels carry."""
    out = []
    for d in defaults:
        d = copy.deepcopy(d)
        chart = d.get("chart")
        if isinstance(chart, dict) and is_internal(chart.get("label")):
            chart["label"] = ""
        out.append(d)
    return out


def lock_inputs(key, form):
    """Drop pricing factors a dealer's browser sent, so MCE's own values apply."""
    form = dict(form or {})
    for k in locked_inputs.get(key, ()):
        form.pop(k, None)
    return form
