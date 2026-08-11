#!/usr/bin/env python3
"""MCE Quote Renderer — reads a quote from Twenty via GraphQL, renders a branded
web view and PDF matching MCE's quote layout (see docs/examples/).

Routes:
  GET /                  quote list (pick one to render)
  GET /quote/<id>        branded web view
  GET /quote/<id>/pdf    branded PDF (chromium print)

Config (env):
  TWENTY_URL       default http://localhost:3000
  TWENTY_EMAIL / TWENTY_PASSWORD   (or read from deploy/credentials.local)
  CHROMIUM_PATH    default: auto-detect playwright chromium
"""
import base64
import glob
import json
import os
import pathlib
import threading
import time
import urllib.request

from flask import Flask, abort, render_template, url_for
from jinja2 import Environment  # noqa: F401  (flask uses jinja2)

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
TWENTY_URL = os.environ.get("TWENTY_URL", "http://localhost:3000")

SELLER = {
    "company": "Midwest Custom Engineering, Inc.",
    "address": ["6526 S Kanner Hwy #215", "Stuart, FL 34997", "United States"],
}
OWNER_CONTACTS = {
    # select value -> (display name, email, phone) for "Prepared by" / seller contact
    "JASON_SHIPLEY": ("Jason Shipley", "jason@usemce.com", "+16202009109"),
}

app = Flask(__name__)
_token = {"value": None, "at": 0}


def _creds():
    email = os.environ.get("TWENTY_EMAIL")
    password = os.environ.get("TWENTY_PASSWORD")
    if email and password:
        return email, password
    creds = {}
    for line in (REPO / "deploy" / "credentials.local").read_text().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            creds[k.strip().lower()] = v.strip()
    return creds["email"], creds["password"]


def gql(query, variables=None, endpoint="/graphql", token=None):
    req = urllib.request.Request(
        TWENTY_URL + endpoint,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"content-type": "application/json",
                 **({"authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if out.get("errors"):
        raise RuntimeError(json.dumps(out["errors"])[:1000])
    return out["data"]


def token():
    if _token["value"] and time.time() - _token["at"] < 1800:
        return _token["value"]
    email, password = _creds()
    d = gql(f'mutation {{ getLoginTokenFromCredentials(email: "{email}", '
            f'password: "{password}", origin: "{TWENTY_URL}") {{ loginToken {{ token }} }} }}',
            endpoint="/metadata")
    lt = d["getLoginTokenFromCredentials"]["loginToken"]["token"]
    d = gql(f'mutation {{ getAuthTokensFromLoginToken(loginToken: "{lt}", origin: "{TWENTY_URL}") '
            '{ tokens { accessOrWorkspaceAgnosticToken { token } } } }', endpoint="/metadata")
    _token["value"] = d["getAuthTokensFromLoginToken"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]
    _token["at"] = time.time()
    return _token["value"]


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


def m2d(m):
    """amountMicros -> dollars (float)."""
    return (m or 0) / 1_000_000


def fmt_money(v):
    return "${:,.2f}".format(v)


def fmt_date(iso):
    if not iso:
        return ""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %-d, %Y")
    except ValueError:
        return iso[:10]


def load_quote(quote_id):
    q = gql(QUOTE_QUERY, {"id": quote_id}, token=token())["quote"]
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
        it["_desc_lines"] = [ln for ln in (it.get("itemDescription") or "").splitlines() if ln.strip()]
        total_discount += disc_per_unit * qty
        subtotal += net
    total = m2d((q.get("amount") or {}).get("amountMicros")) or subtotal

    owner = OWNER_CONTACTS.get(q.get("preparedBy") or "", None)
    prepared_name = (q.get("preparedBy") or "").replace("_", " ").title()
    contact = q.get("contact")
    buyer_contact = None
    if contact:
        nm = f"{contact['name']['firstName']} {contact['name']['lastName']}".strip()
        em = (contact.get("emails") or {}).get("primaryEmail") or ""
        buyer_contact = f"{nm} ({em})" if em else nm

    logo = base64.b64encode((ROOT / "assets" / "mce-logo.png").read_bytes()).decode()
    return {
        "q": q,
        "items": items,
        "logo_b64": logo,
        "seller": SELLER,
        "seller_contact": owner or (prepared_name, "", ""),
        "buyer_contact": buyer_contact,
        "ref": q.get("quoteNumber") or "",
        "issue_date": fmt_date(q.get("sourceCreatedAt") or q.get("createdAt")),
        "expires": fmt_date(q.get("expirationDate")),
        "subtotal": fmt_money(subtotal),
        "total_discount": fmt_money(total_discount),
        "total": fmt_money(total),
        "has_discount": total_discount > 0,
        "fmt_date": fmt_date,
    }


@app.route("/")
def index():
    d = gql("""query { quotes(first: 200, orderBy: {createdAt: DescNullsLast}) {
      edges { node { id name quoteNumber status amount { amountMicros } } } } }""",
            token=token())
    rows = [e["node"] for e in d["quotes"]["edges"]]
    for r in rows:
        r["_amount"] = fmt_money(m2d((r.get("amount") or {}).get("amountMicros")))
    return render_template("index.html", rows=rows)


@app.route("/quote/<quote_id>")
def quote_view(quote_id):
    ctx = load_quote(quote_id)
    if not ctx:
        abort(404)
    return render_template("quote.html", **ctx)


_pdf_lock = threading.Lock()


@app.route("/quote/<quote_id>/pdf")
def quote_pdf(quote_id):
    ctx = load_quote(quote_id)
    if not ctx:
        abort(404)
    html = render_template("quote.html", **ctx)
    from playwright.sync_api import sync_playwright
    chromium_path = os.environ.get("CHROMIUM_PATH")
    if not chromium_path:
        cands = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
        chromium_path = cands[0] if cands else None
    with _pdf_lock, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium_path)
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        pdf = page.pdf(format="A4", print_background=True,
                       margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    name = (ctx["q"].get("name") or "quote").replace("/", "-")[:80]
    return app.response_class(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{name}.pdf"'})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8090")))
