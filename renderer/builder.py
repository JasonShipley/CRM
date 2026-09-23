#!/usr/bin/env python3
"""The quote form builder.

One page where a sales rep builds a quote end to end: customer and job details,
a sizing calculator that drops priced equipment straight into the line items,
free-hand lines for anything else, live totals, then save and print the branded
PDF. Nothing here needs the CRM — quotes live in quotes_store.

Every sizing run is kept on the quote (`sizing`), with its inputs, so an engineer
reviewing the PDF can see exactly what the numbers came from.
"""
from flask import (Blueprint, abort, current_app, jsonify, render_template,
                   request, url_for)

import calculators
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
    return quote


# ------------------------------------------------------------------- pages ---

@bp.route("/")
def index():
    quotes = store.all_quotes()
    rows = []
    for q in quotes:
        _, _, total = store.totals(q)
        rows.append({**q, "_total": render_ctx.fmt_money(total),
                     "_date": render_ctx.fmt_date(q.get("createdAt"))})
    return render_template("index.html", nav="quotes", rows=rows)


@bp.route("/quotes/new")
def new_quote():
    return render_template(
        "quote_form.html", nav="new", quote=None,
        quote_number=store.next_quote_number(),
        calculators=calculators.CALCULATORS, planned=calculators.PLANNED,
        product_defaults=calculators.PRODUCT_DEFAULTS,
        cooler_options=calculators.COOLER_OPTION_DEFS,
        prepared_by=PREPARED_BY, statuses=store.STATUSES,
        default_terms=DEFAULT_TERMS)


@bp.route("/quotes/<quote_id>/edit")
def edit_quote(quote_id):
    quote = store.load(quote_id)
    if not quote:
        abort(404)
    return render_template(
        "quote_form.html", nav="quotes", quote=quote,
        quote_number=quote.get("quoteNumber") or store.next_quote_number(),
        calculators=calculators.CALCULATORS, planned=calculators.PLANNED,
        product_defaults=calculators.PRODUCT_DEFAULTS,
        cooler_options=calculators.COOLER_OPTION_DEFS,
        prepared_by=PREPARED_BY, statuses=store.STATUSES,
        default_terms=DEFAULT_TERMS)


@bp.route("/quotes/<quote_id>")
def quote_view(quote_id):
    quote = store.load(quote_id)
    if not quote:
        abort(404)
    return render_template("quote.html", **render_ctx.from_store(quote))


@bp.route("/quotes/<quote_id>/pdf")
def quote_pdf(quote_id):
    quote = store.load(quote_id)
    if not quote:
        abort(404)
    html = render_template("quote.html", **render_ctx.from_store(quote))
    pdf = render_ctx.to_pdf(html)
    ref = quote.get("quoteNumber") or quote_id
    name = f"MCE Proposal {ref} - {quote.get('name') or 'Quote'}"
    return current_app.response_class(pdf, mimetype="application/pdf",
                                      headers=render_ctx.pdf_headers(name))


# --------------------------------------------------------------------- API ---

@bp.route("/api/calc/<key>", methods=["POST"])
def api_calc(key):
    form = request.get_json(silent=True) or request.form.to_dict()
    result = calculators.run(key, form)
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
    saved = store.save(quote)
    return jsonify({"id": saved["id"],
                    "url": url_for("builder.quote_view", quote_id=saved["id"]),
                    "pdfUrl": url_for("builder.quote_pdf", quote_id=saved["id"]),
                    "editUrl": url_for("builder.edit_quote", quote_id=saved["id"])})


@bp.route("/api/quotes/<quote_id>", methods=["POST"])
def api_update(quote_id):
    existing = store.load(quote_id)
    if not existing:
        return jsonify({"error": "That quote no longer exists."}), 404
    payload = request.get_json(silent=True) or {}
    quote = _from_payload(payload, existing)
    if not quote["name"]:
        return jsonify({"error": "Give the quote a name."}), 400
    if not quote["lines"]:
        return jsonify({"error": "Add at least one line item."}), 400
    saved = store.save(quote)
    return jsonify({"id": saved["id"],
                    "url": url_for("builder.quote_view", quote_id=saved["id"]),
                    "pdfUrl": url_for("builder.quote_pdf", quote_id=saved["id"]),
                    "editUrl": url_for("builder.edit_quote", quote_id=saved["id"])})


@bp.route("/api/quotes/<quote_id>/delete", methods=["POST"])
def api_delete(quote_id):
    if not store.delete(quote_id):
        return jsonify({"error": "That quote no longer exists."}), 404
    return jsonify({"ok": True, "url": url_for("builder.index")})
