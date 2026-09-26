#!/usr/bin/env python3
"""Twenty CRM quote views — the pre-existing path, kept working.

The quote builder now stands alone, but the CRM still holds every quote migrated
from HubSpot, and the Accepted -> QuickBooks estimate sync reads from it. These
routes render those quotes with the same branded template the builder uses.

When the CRM tie-in lands, the builder will write into Twenty through here.
"""
from flask import Blueprint, abort, render_template

import render_ctx
from twenty_api import TwentyError, fmt_date, fmt_money, m2d, query

bp = Blueprint("crm", __name__, url_prefix="/crm")

QUOTE_QUERY = """
query Q($id: UUID!) {
  quote(filter: {id: {eq: $id}}) {
    id name quoteNumber status amount { amountMicros currencyCode }
    expirationDate terms comments preparedBy createdAt sourceCreatedAt qboEstimateId
    company { name address { addressStreet1 addressStreet2 addressCity addressState addressPostcode addressCountry } }
    contact { name { firstName lastName } emails { primaryEmail } phones { primaryPhoneNumber primaryPhoneCallingCode } }
    opportunity { name }
    lineItems {
      edges { node { id name itemDescription quantity lineNumber sku
        unitPrice { amountMicros } unitDiscount { amountMicros } discountPercent
        amount { amountMicros } } }
    }
  }
}
"""


def from_twenty(quote_id):
    q = query(QUOTE_QUERY, {"id": quote_id})["quote"]
    if not q:
        return None
    items = [e["node"] for e in q["lineItems"]["edges"]]
    items.sort(key=lambda x: (x.get("lineNumber") or 9999, x.get("name") or ""))
    total_discount = 0.0
    subtotal = 0.0
    for it in items:
        qty = it.get("quantity") or 1
        unit = m2d((it.get("unitPrice") or {}).get("amountMicros"))
        unit_disc = m2d((it.get("unitDiscount") or {}).get("amountMicros"))
        pct = it.get("discountPercent") or 0
        disc_per_unit = unit_disc + unit * pct / 100.0
        net = m2d((it.get("amount") or {}).get("amountMicros")) or (qty * (unit - disc_per_unit))
        it["_qty"] = int(qty) if float(qty).is_integer() else qty
        it["_unit"] = fmt_money(unit)
        it["_unit_discount"] = fmt_money(disc_per_unit) if disc_per_unit else "—"
        it["_net"] = fmt_money(net)
        it["_desc_lines"] = [ln for ln in (it.get("itemDescription") or "").splitlines()
                             if ln.strip()]
        total_discount += disc_per_unit * qty
        subtotal += net
    total = m2d((q.get("amount") or {}).get("amountMicros")) or subtotal

    contact = q.get("contact")
    buyer_name = buyer_line = ""
    if contact:
        buyer_name = f"{contact['name']['firstName']} {contact['name']['lastName']}".strip()
        em = (contact.get("emails") or {}).get("primaryEmail") or ""
        ph = (contact.get("phones") or {}).get("primaryPhoneNumber") or ""
        buyer_line = " · ".join(x for x in (em, ph) if x)

    # Through the one shared builder, so a CRM quote is the same document as a
    # builder quote. Twenty holds no design basis, schedule or furnished-by-others,
    # so those come back as the empty defaults and the template omits their
    # sections — the parts it does have are laid out identically.
    return render_ctx.base_context(
        q=q,
        items=items,
        seller_contact=render_ctx.seller_contact(q.get("preparedBy")),
        buyer_name=buyer_name,
        buyer_line=buyer_line,
        is_draft=(q.get("status") == "DRAFT"),
        ref=q.get("quoteNumber") or "",
        issue_date=fmt_date(q.get("sourceCreatedAt") or q.get("createdAt")),
        expires=fmt_date(q.get("expirationDate")),
        subtotal=fmt_money(subtotal),
        total_discount=fmt_money(total_discount),
        total=fmt_money(total),
        has_discount=total_discount > 0,
        # Twenty carries a standard schedule on every quote even though it stores
        # none per-quote: without it a CRM quote would silently drop the freight,
        # delivery and installation terms that every MCE proposal carries.
        schedule=render_ctx.STANDARD_SCHEDULE,
    )


@bp.route("/")
def index():
    try:
        d = query("""query { quotes(first: 200, orderBy: {createdAt: DescNullsLast}) {
          edges { node { id name quoteNumber status amount { amountMicros } } } } }""")
    except TwentyError as e:
        # The builder does not need the CRM, so a CRM outage is a message on this
        # page, not a broken app.
        return render_template("crm_index.html", nav="crm", rows=[], error=str(e))
    rows = [e["node"] for e in d["quotes"]["edges"]]
    for r in rows:
        r["_amount"] = fmt_money(m2d((r.get("amount") or {}).get("amountMicros")))
    return render_template("crm_index.html", nav="crm", rows=rows, error=None)


@bp.route("/quotes/<quote_id>")
def quote_view(quote_id):
    ctx = from_twenty(quote_id)
    if not ctx:
        abort(404)
    return render_template("quote.html", **ctx)


@bp.route("/quotes/<quote_id>/pdf")
def quote_pdf(quote_id):
    ctx = from_twenty(quote_id)
    if not ctx:
        abort(404)
    pdf = render_ctx.to_pdf(render_template("quote.html", **ctx))
    from flask import current_app
    return current_app.response_class(
        pdf, mimetype="application/pdf",
        headers=render_ctx.pdf_headers(ctx["q"].get("name") or "quote"))


@bp.app_errorhandler(TwentyError)
def _twenty_error(e):
    return render_template("error.html", nav="", title="CRM unreachable",
                           message=str(e)), 502
