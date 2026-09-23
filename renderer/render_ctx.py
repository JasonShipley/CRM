#!/usr/bin/env python3
"""Build the branded-quote template context, and render it to PDF.

templates/quote.html is MCE's Equipment Proposal layout and stays untouched: both
sources feed it the same context shape — the standalone builder's own quotes
(`from_store`) and quotes read out of Twenty (`from_twenty`, in app.py).
"""
import base64
import functools
import glob
import os
import pathlib
import threading

ROOT = pathlib.Path(__file__).resolve().parent

SELLER = {
    "company": "Midwest Custom Engineering, Inc.",
    "address": ["6526 S Kanner Hwy #215", "Stuart, FL 34997", "United States"],
}
OWNER_CONTACTS = {
    # select value -> (display name, title, email, phone line)
    "JASON_SHIPLEY": ("Jason Shipley", "President, Midwest Custom Engineering, Inc.",
                      "jason@usemce.com", "772-200-4060 · cell 620-200-9109"),
}
FOOTER_RIGHT = "Stuart, FL · 772-200-4060 · midwestcustomengineering.com"


def fmt_money(v):
    return "${:,.2f}".format(v)


def fmt_date(iso):
    if not iso:
        return ""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%b %-d, %Y")
    except ValueError:
        return str(iso)[:10]


@functools.lru_cache(maxsize=1)
def assets():
    """Logo and brand fonts, base64'd once — the PDF must be self-contained."""
    return {
        "logo_b64": base64.b64encode((ROOT / "assets" / "mce-logo.png").read_bytes()).decode(),
        "fonts": {n: base64.b64encode(
            (ROOT / "assets" / "fonts" / f"{n}.woff2").read_bytes()).decode()
            for n in ("oswald", "inter")},
    }


def seller_contact(prepared_by):
    owner = OWNER_CONTACTS.get(prepared_by or "")
    if owner:
        return owner
    name = (prepared_by or "").replace("_", " ").title()
    return (name, "Midwest Custom Engineering, Inc.", "", "")


def from_store(quote):
    """Template context for a quote held by quotes_store."""
    import quotes_store as store

    cust = quote.get("customer") or {}

    def render_lines(rows):
        out = []
        for line in rows or []:
            total, per_unit_discount = store.line_total(line)
            try:
                qty = float(line.get("quantity") or 1)
            except (TypeError, ValueError):
                qty = 1
            try:
                unit = float(line.get("unitPrice") or 0)
            except (TypeError, ValueError):
                unit = 0.0
            out.append({
                "name": line.get("name") or "",
                "sku": line.get("sku") or "",
                "needs_price": bool(line.get("needsPrice")),
                "_qty": int(qty) if float(qty).is_integer() else qty,
                "_unit": "TBD" if line.get("needsPrice") else fmt_money(unit),
                "_unit_discount": fmt_money(per_unit_discount) if per_unit_discount else "—",
                "_net": "TBD" if line.get("needsPrice") else fmt_money(total),
                "_desc_lines": [ln for ln in (line.get("description") or "").splitlines()
                                if ln.strip()],
            })
        return out

    items = render_lines(quote.get("lines"))
    net_items = render_lines(quote.get("netItems"))
    t = store.totals(quote)

    buyer_line = " · ".join(x for x in (cust.get("email"), cust.get("phone")) if x)
    q = {
        "name": quote.get("name") or "",
        "quoteNumber": quote.get("quoteNumber") or "",
        "status": quote.get("status") or "DRAFT",
        "terms": quote.get("terms") or "",
        "comments": quote.get("comments") or "",
        "preparedBy": quote.get("preparedBy") or "",
        "company": ({"name": cust.get("company"), "address": {
            "addressStreet1": cust.get("street1") or "",
            "addressStreet2": cust.get("street2") or "",
            "addressCity": cust.get("city") or "",
            "addressState": cust.get("state") or "",
            "addressPostcode": cust.get("postcode") or "",
            "addressCountry": cust.get("country") or "",
        }} if cust.get("company") else None),
        "opportunity": ({"name": quote["project"]} if quote.get("project") else None),
    }
    return {
        "q": q,
        "items": items,
        "seller": SELLER,
        "seller_contact": seller_contact(quote.get("preparedBy")),
        "buyer_name": cust.get("contact") or "",
        "buyer_line": buyer_line,
        "footer_right": FOOTER_RIGHT,
        "is_draft": q["status"] == "DRAFT",
        "ref": q["quoteNumber"],
        "issue_date": fmt_date(quote.get("createdAt")),
        "expires": fmt_date(quote.get("expirationDate")),
        "net_items": net_items,
        "design_basis": quote.get("designBasis") or [],
        "options": quote.get("options") or [],
        "by_others": quote.get("byOthers") or [],
        "schedule": quote.get("schedule") or [],
        "open_items": quote.get("openItems") or [],
        "source_request": quote.get("sourceRequest") or "",
        "subtotal": fmt_money(t["subtotal"]),
        "total_discount": fmt_money(t["line_discount"]),
        "has_discount": t["line_discount"] > 0,
        "discount_percent": t["discount_percent"],
        "project_discount": fmt_money(t["project_discount"]),
        "net_subtotal": fmt_money(t["net_subtotal"]),
        "has_net": t["has_net"],
        "total": fmt_money(t["total"]),
        "fmt_date": fmt_date,
        **assets(),
    }


def pdf_headers(filename):
    """Content-Disposition that survives a non-ASCII quote name.

    Browsers need a plain-ASCII `filename` to fall back on; `filename*` carries
    the real one (MCE quote names routinely contain em dashes and ampersands).
    """
    from urllib.parse import quote as urlquote
    safe = filename.replace("/", "-").replace("\\", "-").replace('"', "'")[:110]
    ascii_name = safe.encode("ascii", "replace").decode("ascii").replace("?", "-")
    return {"Content-Disposition":
            f'inline; filename="{ascii_name}.pdf"; '
            f"filename*=UTF-8''{urlquote(safe + '.pdf')}"}


# ------------------------------------------------------------------- PDF ------

_pdf_lock = threading.Lock()


def to_pdf(html):
    """Print the rendered quote with headless Chromium.

    Serialized: one Chromium at a time keeps memory predictable on the small
    production box.
    """
    from playwright.sync_api import sync_playwright
    chromium_path = os.environ.get("CHROMIUM_PATH")
    if not chromium_path:
        cands = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
        chromium_path = cands[0] if cands else None
    with _pdf_lock, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium_path)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            return page.pdf(
                format="Letter", print_background=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    "<div style='width:100%;font-size:7px;color:#8a8a8a;"
                    "font-family:Helvetica,Arial,sans-serif;padding-right:44px;"
                    "text-align:right;'>Page <span class='pageNumber'></span> of "
                    "<span class='totalPages'></span></div>"),
                margin={"top": "0", "bottom": "22px", "left": "0", "right": "0"})
        finally:
            browser.close()
