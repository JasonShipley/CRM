#!/usr/bin/env python3
"""The quote form builder.

One page where a sales rep builds a quote end to end: customer and job details,
a sizing calculator that drops priced equipment straight into the line items,
free-hand lines for anything else, live totals, then save and print the branded
PDF. Nothing here needs the CRM — quotes live in quotes_store.

Every sizing run is kept on the quote (`sizing`), with its inputs, so an engineer
reviewing the PDF can see exactly what the numbers came from.
"""
from flask import (Blueprint, abort, current_app, g, jsonify, render_template,
                   request, url_for)

import accounts
import calculators
import dealer_view
import interpret
import quote_from_job
import quotes_store as store
import render_ctx

bp = Blueprint("builder", __name__)

PREPARED_BY = [("JASON_SHIPLEY", "Jason Shipley")]
DEFAULT_TERMS = ("50% down with order, balance before shipment. "
                 "FOB shipping point. Prices valid for 30 days.")


def _clean_lines(rows):
    """Form rows -> stored lines. Blank-named rows are dropped, not saved empty."""
    out = []
    for row in rows or []:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name[:255],
            "description": (row.get("description") or "")[:10000],
            "quantity": row.get("quantity") or 1,
            "unitPrice": row.get("unitPrice") or 0,
            "unitDiscount": row.get("unitDiscount") or "",
            "discountPercent": row.get("discountPercent") or "",
            "amount": row.get("amount") or "",
            "sku": (row.get("sku") or "")[:255],
            "needsPrice": bool(row.get("needsPrice")),
        })
    return out


def _from_payload(payload, existing=None):
    quote = dict(existing or {})
    quote["name"] = (payload.get("name") or "").strip()[:255]
    quote["quoteNumber"] = (payload.get("quoteNumber") or "").strip()[:64]
    quote["status"] = payload.get("status") or "DRAFT"
    quote["project"] = (payload.get("project") or "").strip()[:255]
    quote["expirationDate"] = (payload.get("expirationDate") or "").strip()[:10]
    quote["terms"] = (payload.get("terms") or "")[:10000]
    quote["comments"] = (payload.get("comments") or "")[:10000]
    quote["preparedBy"] = payload.get("preparedBy") or ""
    quote["amount"] = payload.get("amount") or ""
    quote["customer"] = {
        k: (payload.get("customer") or {}).get(k, "") or ""
        for k in ("company", "contact", "email", "phone", "street1", "street2",
                  "city", "state", "postcode", "country")
    }
    quote["lines"] = _clean_lines(payload.get("lines"))
    quote["sizing"] = payload.get("sizing") or []
    # Proposal sections. Absent keys mean "keep what's stored" on an update, so a
    # quote built from a description doesn't lose its design basis when a rep
    # edits a line item and saves.
    for key in ("designBasis", "byOthers", "schedule", "options", "netItems",
                "openItems", "discountPercent", "sourceRequest"):
        if key in payload:
            quote[key] = payload[key]
    return quote


# ------------------------------------------------------- who sees what ---

def _user():
    return getattr(g, "user", None) or {"role": "staff",
                                         "dealership": accounts.STAFF_DEALERSHIP}


def is_dealer():
    return _user().get("role") == "dealer"


def _dealership(quote):
    # quotes from before dealers existed were all MCE's own
    return quote.get("dealership") or accounts.STAFF_DEALERSHIP


def _visible(quote):
    return bool(quote) and (not is_dealer()
                            or _dealership(quote) == _user().get("dealership"))


def _load(quote_id):
    """A quote this person may see, or a 404 — a dealer is never told another
    dealer's quote exists."""
    quote = store.load(quote_id)
    if not _visible(quote):
        abort(404)
    return quote


def for_viewer(quote):
    """The quote as the person asking may see it."""
    return dealer_view.quote(quote) if is_dealer() else quote


def _form_calculators():
    """The calculators for the quote form — pricing factors and internal help
    taken out for a dealer."""
    if not is_dealer():
        return calculators.CALCULATORS
    return dealer_view.calculators_for_dealer(calculators.CALCULATORS)


def _product_defaults():
    return (dealer_view.product_defaults(calculators.PRODUCT_DEFAULTS) if is_dealer()
            else calculators.PRODUCT_DEFAULTS)


def _stamp_owner(quote):
    user = _user()
    quote["createdBy"] = user.get("email") or ""
    quote["dealership"] = user.get("dealership") or accounts.STAFF_DEALERSHIP
    return quote


# ------------------------------------------------------------------- pages ---

@bp.route("/")
def index():
    quotes = [q for q in store.all_quotes() if _visible(q)]
    rows = []
    for q in quotes:
        t = store.totals(q)
        rows.append({**q, "_total": render_ctx.fmt_money(t["total"]),
                     "_date": render_ctx.fmt_date(q.get("createdAt"))})
    return render_template("index.html", nav="quotes", rows=rows,
                           show_dealer=not is_dealer())


@bp.route("/quotes/new")
def new_quote():
    return render_template(
        "quote_form.html", nav="new", quote=None,
        quote_number=store.next_quote_number(),
        calculators=_form_calculators(), planned=calculators.PLANNED,
        product_defaults=_product_defaults(),
        cooler_options=calculators.COOLER_OPTION_DEFS,
        prepared_by=PREPARED_BY, statuses=store.STATUSES,
        default_terms=DEFAULT_TERMS)


@bp.route("/quotes/<quote_id>/edit")
def edit_quote(quote_id):
    quote = for_viewer(_load(quote_id))
    return render_template(
        "quote_form.html", nav="quotes", quote=quote,
        quote_number=quote.get("quoteNumber") or store.next_quote_number(),
        calculators=_form_calculators(), planned=calculators.PLANNED,
        product_defaults=_product_defaults(),
        cooler_options=calculators.COOLER_OPTION_DEFS,
        prepared_by=PREPARED_BY, statuses=store.STATUSES,
        default_terms=DEFAULT_TERMS)


def _pdf_name(quote, quote_id):
    ref = quote.get("quoteNumber") or quote_id
    return f"MCE Proposal {ref} - {quote.get('name') or 'Quote'}"


@bp.route("/quotes/<quote_id>")
def quote_view(quote_id):
    quote = for_viewer(_load(quote_id))
    # the on-screen page only: in the Home Screen app it has no browser bar, so it
    # carries its own way back, Edit and Share PDF. The PDF render leaves it out.
    app_bar = {"back": url_for("builder.index"), "back_label": "Quotes",
               "edit": url_for("builder.edit_quote", quote_id=quote_id),
               "pdf": url_for("builder.quote_pdf", quote_id=quote_id),
               "filename": _pdf_name(quote, quote_id) + ".pdf"}
    return render_template("quote.html", **{**render_ctx.from_store(quote), "app_bar": app_bar})


@bp.route("/quotes/<quote_id>/pdf")
def quote_pdf(quote_id):
    quote = for_viewer(_load(quote_id))
    html = render_template("quote.html", **render_ctx.from_store(quote))
    pdf = render_ctx.to_pdf(html)
    return current_app.response_class(pdf, mimetype="application/pdf",
                                      headers=render_ctx.pdf_headers(_pdf_name(quote, quote_id)))


# --------------------------------------------------------------------- API ---

@bp.route("/api/interpret", methods=["POST"])
def api_interpret():
    """Free-text job description -> a complete draft proposal.

    Claude reads the sentence; MCE's calculators produce every number. The reply
    is a quote the rep can review and edit — it is not saved until they save it.
    """
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    try:
        job = interpret.interpret(text)
    except interpret.InterpretError as e:
        return jsonify({"error": str(e)}), 400
    quote = quote_from_job.build(job)
    quote["sourceRequest"] = text
    quote = for_viewer(quote)
    return jsonify({"quote": quote, "openItems": quote.get("openItems", []),
                    "job": job.model_dump()})


@bp.route("/api/pricing")
def api_pricing():
    """The pricing basis, machine-readable — so every quote uses the same numbers.

    A quote built in one chat and a quote built in another have to agree, and they
    only agree if they read from one place. This is that place: the live escalation
    factors, what they derive, what is NOT priced and why, and the vendor bases
    behind the buy-out lines. Anything quoting MCE equipment should start here
    rather than from a number someone remembered.
    """
    from calculators import _pricing_api

    return jsonify(_pricing_api.payload())


@bp.route("/api/calc/<key>", methods=["POST"])
def api_calc(key):
    form = request.get_json(silent=True) or request.form.to_dict()
    if is_dealer():
        result = dealer_view.calc(
            calculators.run_with_defaults(key, dealer_view.lock_inputs(key, form)))
    else:
        result = calculators.run_with_defaults(key, form)
    return jsonify(result), (400 if result.get("error") else 200)


@bp.route("/api/quotes", methods=["POST"])
def api_create():
    payload = request.get_json(silent=True) or {}
    quote = _from_payload(payload)
    problems = []
    if not quote["name"]:
        problems.append("Give the quote a name.")
    if not quote["lines"]:
        problems.append("Add at least one line item.")
    if problems:
        return jsonify({"error": " ".join(problems)}), 400
    if not quote["quoteNumber"]:
        quote["quoteNumber"] = store.next_quote_number()
    if is_dealer():
        quote = dealer_view.quote(quote)
    saved = store.save(_stamp_owner(quote))
    return jsonify({"id": saved["id"],
                    "url": url_for("builder.quote_view", quote_id=saved["id"]),
                    "pdfUrl": url_for("builder.quote_pdf", quote_id=saved["id"]),
                    "editUrl": url_for("builder.edit_quote", quote_id=saved["id"])})


@bp.route("/api/quotes/<quote_id>", methods=["POST"])
def api_update(quote_id):
    existing = store.load(quote_id)
    if not _visible(existing):
        return jsonify({"error": "That quote no longer exists."}), 404
    payload = request.get_json(silent=True) or {}
    quote = _from_payload(payload, existing)
    if not quote["name"]:
        return jsonify({"error": "Give the quote a name."}), 400
    if not quote["lines"]:
        return jsonify({"error": "Add at least one line item."}), 400
    if is_dealer():
        quote = dealer_view.quote(quote)
    saved = store.save(quote)
    return jsonify({"id": saved["id"],
                    "url": url_for("builder.quote_view", quote_id=saved["id"]),
                    "pdfUrl": url_for("builder.quote_pdf", quote_id=saved["id"]),
                    "editUrl": url_for("builder.edit_quote", quote_id=saved["id"])})


@bp.route("/api/quotes/<quote_id>/delete", methods=["POST"])
def api_delete(quote_id):
    if not _visible(store.load(quote_id)) or not store.delete(quote_id):
        return jsonify({"error": "That quote no longer exists."}), 404
    return jsonify({"ok": True, "url": url_for("builder.index")})
