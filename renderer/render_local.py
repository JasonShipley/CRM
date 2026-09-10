#!/usr/bin/env python3
"""Render a quote to HTML + PDF from a local JSON file, without Twenty.

Use this to (re)issue a quote offline — e.g. a revision of a quote that lives in
HubSpot/Twenty but needs a few line changes — using the same MCE-branded
template the renderer serves at /quote/<id>/pdf.

    python renderer/render_local.py docs/quotes/my-quote.json out/my-quote.pdf

JSON shape (dollars, not micros):
{
  "name": "...", "quoteNumber": "...", "issueDate": "2026-09-10",
  "expirationDate": "2026-12-09", "preparedBy": "JASON_SHIPLEY",
  "comments": "...", "terms": "...", "amount": 123.45,          # optional; else sum of lines
  "company": {"name": "...", "address": {"addressStreet1": "...", "addressCity": "...",
              "addressState": "..", "addressPostcode": "...", "addressCountry": "..."}},
  "contact": {"firstName": "...", "lastName": "...", "email": "...", "phone": "..."},
  "lineItems": [{"name": "...", "itemDescription": "...", "quantity": 1,
                 "unitPrice": 100.0, "unitDiscount": 0, "discountPercent": 0}]
}
"""
import base64
import glob
import json
import os
import pathlib
import sys

from jinja2 import Environment, FileSystemLoader

import app as renderer  # reuse SELLER, OWNER_CONTACTS, fmt_money, fmt_date

ROOT = pathlib.Path(__file__).resolve().parent


def build_context(q):
    items = []
    subtotal = 0.0
    total_discount = 0.0
    for n, it in enumerate(q["lineItems"], start=1):
        it = dict(it)
        qty = it.get("quantity") or 1
        unit = float(it.get("unitPrice") or 0)
        unit_disc = float(it.get("unitDiscount") or 0)
        pct = float(it.get("discountPercent") or 0)
        disc_per_unit = unit_disc + unit * pct / 100.0
        net = round(qty * (unit - disc_per_unit), 2)
        it["_qty"] = int(qty) if float(qty).is_integer() else qty
        it["_unit"] = renderer.fmt_money(unit)
        it["_unit_discount"] = renderer.fmt_money(disc_per_unit) if disc_per_unit else "—"
        it["_net"] = renderer.fmt_money(net)
        it["_desc_lines"] = [ln for ln in (it.get("itemDescription") or "").splitlines() if ln.strip()]
        it.setdefault("lineNumber", n)
        subtotal += net
        total_discount += disc_per_unit * qty
        items.append(it)
    total = float(q.get("amount") or subtotal)

    owner = renderer.OWNER_CONTACTS.get(q.get("preparedBy") or "")
    prepared_name = (q.get("preparedBy") or "").replace("_", " ").title()
    c = q.get("contact") or {}
    nm = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
    buyer_contact = f"{nm} ({c['email']})" if c.get("email") else (nm or None)

    qv = {
        "name": q.get("name"), "comments": q.get("comments"), "terms": q.get("terms"),
        "company": q.get("company"),
    }
    return {
        "q": qv,
        "items": items,
        "logo_b64": base64.b64encode((ROOT / "assets" / "mce-logo.png").read_bytes()).decode(),
        "seller": renderer.SELLER,
        "seller_contact": owner or (prepared_name, "", ""),
        "buyer_contact": buyer_contact,
        "ref": q.get("quoteNumber") or "",
        "issue_date": renderer.fmt_date(q.get("issueDate")),
        "expires": renderer.fmt_date(q.get("expirationDate")),
        "subtotal": renderer.fmt_money(subtotal),
        "total_discount": renderer.fmt_money(total_discount),
        "total": renderer.fmt_money(total),
        "has_discount": total_discount > 0,
        "fmt_date": renderer.fmt_date,
    }


def render_html(q):
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    return env.get_template("quote.html").render(**build_context(q))


def html_to_pdf(html, out_pdf, scale=None, prefer_css_page_size=False):
    from playwright.sync_api import sync_playwright
    chromium_path = os.environ.get("CHROMIUM_PATH")
    if not chromium_path:
        cands = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
        chromium_path = cands[0] if cands else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium_path,
                                     args=["--no-sandbox"] if os.geteuid() == 0 else [])
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        opts = dict(path=str(out_pdf), print_background=True,
                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        if prefer_css_page_size:
            opts["prefer_css_page_size"] = True
        else:
            opts["format"] = "A4"
        if scale:
            opts["scale"] = scale
        page.pdf(**opts)
        browser.close()


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, out_pdf = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    q = json.loads(src.read_text())
    html = render_html(q)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.with_suffix(".html").write_text(html)
    html_to_pdf(html, out_pdf)
    print(f"wrote {out_pdf} and {out_pdf.with_suffix('.html')}")


if __name__ == "__main__":
    main()
