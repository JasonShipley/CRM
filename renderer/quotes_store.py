#!/usr/bin/env python3
"""Local quote storage for the standalone quote builder.

One JSON file per quote under RENDERER_DATA_DIR (default renderer/data/quotes).
No database and no CRM dependency — the builder works on its own today, and the
record shape is deliberately tool-agnostic so pushing these into Twenty later is
a mapping job, not a rewrite.

Concurrency is file-level: a save writes to a temp file in the same directory and
renames over the target, so a reader never sees a half-written quote.
"""
import json
import os
import pathlib
import re
import secrets
import tempfile
from datetime import date, datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = pathlib.Path(os.environ.get("RENDERER_DATA_DIR") or (ROOT / "data"))
QUOTE_DIR = DATA_DIR / "quotes"

STATUSES = [("DRAFT", "Draft"), ("PUBLISHED", "Published"), ("ACCEPTED", "Accepted"),
            ("DECLINED", "Declined"), ("EXPIRED", "Expired")]

_ID_RE = re.compile(r"^q[0-9a-f]{12}$")


def _now():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return "q" + secrets.token_hex(6)


def _path(quote_id):
    """Resolve a quote id to its file, refusing anything that isn't an id.

    Ids reach this from the URL, so nothing but the known shape gets through —
    no separators, no traversal.
    """
    if not _ID_RE.match(quote_id or ""):
        return None
    return QUOTE_DIR / f"{quote_id}.json"


def load(quote_id):
    p = _path(quote_id)
    if not p or not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save(quote):
    QUOTE_DIR.mkdir(parents=True, exist_ok=True)
    quote.setdefault("id", new_id())
    quote.setdefault("createdAt", _now())
    quote["updatedAt"] = _now()
    p = _path(quote["id"])
    if not p:
        raise ValueError(f"bad quote id: {quote.get('id')!r}")
    fd, tmp = tempfile.mkstemp(dir=str(QUOTE_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(quote, fh, indent=2)
        os.replace(tmp, p)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise
    return quote


def delete(quote_id):
    p = _path(quote_id)
    if p and p.exists():
        p.unlink()
        return True
    return False


def all_quotes():
    """Every stored quote, newest first. Unreadable files are skipped, not fatal."""
    if not QUOTE_DIR.exists():
        return []
    out = []
    for p in QUOTE_DIR.glob("q*.json"):
        try:
            out.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    out.sort(key=lambda q: q.get("createdAt") or "", reverse=True)
    return out


def next_quote_number(today=None):
    """MCE's reference format: YYYYMMDD-N, N counting up within the day."""
    stamp = (today or date.today()).strftime("%Y%m%d")
    used = set()
    for q in all_quotes():
        ref = str(q.get("quoteNumber") or "")
        if ref.startswith(stamp + "-"):
            tail = ref[len(stamp) + 1:]
            if tail.isdigit():
                used.add(int(tail))
    n = 1
    while n in used:
        n += 1
    return f"{stamp}-{n}"


# ------------------------------------------------------------------ totals ----

def line_total(line):
    """qty x (unit - discount), unless an explicit line total was entered.

    Same rule the renderer already used for CRM quotes, so a quote reads the same
    whichever side it came from.
    """
    try:
        qty = float(line.get("quantity") or 1)
        unit = float(line.get("unitPrice") or 0)
        unit_disc = float(line.get("unitDiscount") or 0)
        pct = float(line.get("discountPercent") or 0)
    except (TypeError, ValueError):
        return 0.0, 0.0
    per_unit_discount = unit_disc + unit * pct / 100.0
    explicit = line.get("amount")
    if str(explicit or "").strip() != "":
        try:
            return float(explicit), per_unit_discount
        except (TypeError, ValueError):
            pass
    return qty * (unit - per_unit_discount), per_unit_discount


def _sum(rows):
    subtotal = line_discount = 0.0
    for line in rows or []:
        total, per_unit = line_total(line)
        try:
            qty = float(line.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        subtotal += total
        line_discount += per_unit * qty
    return subtotal, line_discount


def totals(quote):
    """Proposal totals, in the order MCE's own proposals present them.

    Any project discount applies to the scope lines only; `netItems` (main drive
    motors, in
    MCE's Mid-States proposal) sit outside it and are quoted net.
    """
    subtotal, line_discount = _sum(quote.get("lines"))
    net_subtotal, net_line_discount = _sum(quote.get("netItems"))
    try:
        pct = float(quote.get("discountPercent") or 0)
    except (TypeError, ValueError):
        pct = 0.0
    project_discount = subtotal * pct / 100.0
    grand = subtotal - project_discount + net_subtotal
    amount = quote.get("amount")
    try:
        if str(amount or "").strip() != "":
            grand = float(amount)
    except (TypeError, ValueError):
        pass
    return {
        "subtotal": subtotal,
        "line_discount": line_discount + net_line_discount,
        "discount_percent": pct,
        "project_discount": project_discount,
        "net_subtotal": net_subtotal,
        "has_net": bool(quote.get("netItems")),
        "total": grand,
    }
