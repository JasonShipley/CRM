#!/usr/bin/env python3
"""The Home Screen app: installable, never caching data, and usable full screen.

What it holds:

  * the manifest and service worker load before anyone signs in, and give away
    nothing
  * every icon the manifest names exists at the size it claims
  * every page a person sees carries what iOS needs to install it
  * the service worker caches only its offline page — never a quote, price or API
  * the proposal page has its own way back and Share PDF, and the PDF render
    has none of it
  * switching to Mail for the sign-in code and back does not lose the code step,
    for a stranger's address exactly as for a dealer's

    cd renderer && python3 tests/test_app_install.py
"""
import json
import logging
import os
import pathlib
import re
import struct
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
os.environ["RENDERER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["SESSION_COOKIE_SECURE"] = "0"
os.environ.pop("SMTP_HOST", None)
logging.disable(logging.WARNING)

import accounts  # noqa: E402
import app as appmod  # noqa: E402
import codes  # noqa: E402

FAILS = []
APP_HEAD = ('rel="manifest"', 'rel="apple-touch-icon"', "apple-mobile-web-app-capable",
            "viewport-fit=cover")


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + str(detail)[:300] if detail else ''}")


def png_size(path):
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def sign_in(email):
    c = appmod.app.test_client()
    code, _ = codes.issue(email, "login")
    c.post("/login", data={"email": email, "step": "code", "code": code})
    return c


def main():
    app = appmod.app
    anon = app.test_client()

    # 1. the manifest and service worker -----------------------------------
    r = anon.get("/manifest.webmanifest")
    check("manifest loads without signing in", r.status_code == 200, r.status_code)
    check("as a manifest", r.mimetype == "application/manifest+json", r.mimetype)
    m = json.loads(r.get_data(as_text=True))
    for k, v in (("display", "standalone"), ("start_url", "/"), ("scope", "/"),
                 ("short_name", "MCE Quotes")):
        check(f"manifest {k}", m.get(k) == v, m.get(k))
    purposes = set()
    for icon in m["icons"]:
        p = ROOT / icon["src"].lstrip("/").replace("assets/", "assets/", 1)
        size = png_size(p)
        w, h = map(int, icon["sizes"].split("x"))
        check(f"icon {icon['src']} is a {icon['sizes']} PNG", size == (w, h), size)
        check(f"icon {icon['src']} is served", anon.get(icon["src"]).status_code == 200)
        purposes.add(icon.get("purpose", "any"))
    check("a maskable icon for Android", "maskable" in purposes, purposes)
    check("the manifest says nothing internal",
          not re.search(r"cost|vendor|price basis", r.get_data(as_text=True), re.I))

    r = anon.get("/sw.js")
    check("service worker loads without signing in", r.status_code == 200, r.status_code)
    check("as JavaScript", "javascript" in r.mimetype, r.mimetype)
    check("and is never cached itself", "no-cache" in r.headers.get("Cache-Control", ""))
    sw = r.get_data(as_text=True)
    r.close()
    pre = re.search(r"const OFFLINE = \[(.*?)\]", sw, re.S)
    cached = re.findall(r'"([^"]+)"', pre.group(1)) if pre else []
    check("it precaches the offline page", "/assets/offline.html" in cached, cached)
    check("and nothing but static assets",
          cached and all(u.startswith("/assets/") for u in cached), cached)
    check("never a page, quote or API",
          not re.search(r"cache\.put|/api/|/quotes|/tools|/crm", sw), "found")
    check("it leaves everything but page loads alone", 'req.mode !== "navigate"' in sw)
    for u in cached:
        rr = anon.get(u)
        check(f"precached {u} is served", rr.status_code == 200, rr.status_code)
        rr.close()

    # 2. every page carries what iOS needs -----------------------------------
    login = anon.get("/login").get_data(as_text=True)
    for bit in APP_HEAD:
        check(f"sign-in page carries {bit}", bit in login)

    accounts.save_dealer("dee@dealerco.com", "Dee", "DealerCo")
    staff = sign_in("jason@usemce.com")
    dealer = sign_in("dee@dealerco.com")
    line = [{"name": "Thing", "unitPrice": 100, "quantity": 1}]
    qid = dealer.post("/api/quotes", json={"name": "App job", "lines": line}).get_json()["id"]

    for who, c in (("staff", staff), ("dealer", dealer)):
        for path in ("/", "/quotes/new", f"/quotes/{qid}/edit", f"/quotes/{qid}"):
            page = c.get(path).get_data(as_text=True)
            for bit in APP_HEAD:
                check(f"{who} {path} carries {bit}", bit in page)
    lst = dealer.get("/").get_data(as_text=True)
    check("the list's PDF link opens the proposal inside the app",
          f'app-only" href="/quotes/{qid}"' in lst)

    # 3. the proposal page in the app, and the PDF without it -------------------
    view = dealer.get(f"/quotes/{qid}").get_data(as_text=True)
    check("the proposal has a way back", 'class="appbar"' in view and "&larr; Quotes" in view)
    check("and Share PDF", 'id="share-pdf"' in view and f"/quotes/{qid}/pdf" in view)
    check("and Edit", f"/quotes/{qid}/edit" in view)
    import render_ctx
    seen = {}
    real = render_ctx.to_pdf
    render_ctx.to_pdf = lambda html: (seen.setdefault("html", html), b"%PDF-1.4 stub")[1]
    try:
        pdf = dealer.get(f"/quotes/{qid}/pdf")
    finally:
        render_ctx.to_pdf = real
    check("the PDF still renders", pdf.status_code == 200, pdf.status_code)
    html = seen.get("html", "")
    check("and its HTML has no app bar, manifest or script",
          html and "appbar" not in html and "manifest" not in html
          and "share-pdf" not in html, "app bits in the PDF")

    # 4. the code step survives a trip to Mail ----------------------------------
    for addr, kind in (("dee@dealerco.com", "a dealer"), ("nobody@gmail.com", "a stranger")):
        c = app.test_client()
        c.post("/login", data={"email": addr, "next": "/quotes/new"})
        # iOS relaunched the app at "/", which sends a signed-out visitor to sign in
        again = c.get("/login?next=/%3F").get_data(as_text=True)
        check(f"{kind}: back on the code step", 'name="step" value="code"' in again
              and addr in again, again[:200])
        check(f"{kind}: still going where they were going",
              'name="next" value="/quotes/new"' in again)
        fresh = c.get("/login?restart=1").get_data(as_text=True)
        check(f"{kind}: 'use a different email' starts over",
              'name="step" value="code"' not in fresh)
        check(f"{kind}: and stays over", 'name="step" value="code"' not in
              c.get("/login").get_data(as_text=True))

    c = app.test_client()
    c.post("/login", data={"email": "dee@dealerco.com"})
    with c.session_transaction() as s:
        s["pending_login"]["at"] -= codes.CODE_TTL_S + 1
    check("an expired code step is not brought back",
          'name="step" value="code"' not in c.get("/login").get_data(as_text=True))

    c = app.test_client()
    c.post("/login", data={"email": "dee@dealerco.com"})
    code, _ = codes.issue("dee@dealerco.com", "login")
    c.post("/login", data={"email": "dee@dealerco.com", "step": "code", "code": code})
    with c.session_transaction() as s:
        check("signing in clears the pending step", "pending_login" not in s)
    check("and lands signed in", c.get("/").status_code == 200)

    if FAILS:
        print(f"app install: {len(FAILS)} problems")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — installable on a Home Screen, caches nothing but its offline page, "
          "and keeps the sign-in step across an app switch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
