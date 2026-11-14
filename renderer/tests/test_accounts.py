#!/usr/bin/env python3
"""Who gets in, and what a dealer can reach.

The app is the only gate in front of MCE's quotes and pricing — Caddy passes
everything through — so this walks the whole door: the emailed-code sign-in,
every route without a session, the dealer allowlist, quote ownership between
dealerships, and switching an account off.

    cd renderer && python3 tests/test_accounts.py
"""
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["RENDERER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["SESSION_COOKIE_SECURE"] = "0"
os.environ.pop("SMTP_HOST", None)

import logging  # noqa: E402

logging.disable(logging.WARNING)       # the no-SMTP fallback logs every code

import accounts  # noqa: E402
import app as appmod  # noqa: E402
import codes  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + str(detail) if detail else ''}")


def sign_in(email):
    c = appmod.app.test_client()
    c.post("/login", data={"email": email})
    code, _ = codes.issue(email, "login")
    r = c.post("/login", data={"email": email, "step": "code", "code": code})
    return c, r


def main():
    app = appmod.app

    # 1. nothing without a session ---------------------------------------
    anon = app.test_client()
    open_rules = {"login", "static", "api_token_request", "api_token_confirm"}
    for rule in app.url_map.iter_rules():
        if rule.endpoint in open_rules or "GET" not in rule.methods:
            continue
        path = rule.rule
        for arg in rule.arguments:
            path = path.replace(f"<{arg}>", "x").replace(f"<path:{arg}>", "x")
        path = path.replace("<", "").replace(">", "")
        r = anon.get(path)
        if path.startswith("/api/"):
            check(f"anonymous {path} refused", r.status_code == 401, r.status_code)
        else:
            check(f"anonymous {path} sent to sign in", r.status_code == 302
                  and "/login" in r.headers.get("Location", ""), r.status_code)
    for path in ("/api/quotes", "/api/calc/fan", "/api/voice/session", "/api/voice/draft"):
        check(f"anonymous POST {path} refused", anon.post(path, json={}).status_code == 401)

    # 2. the code sign-in ---------------------------------------------------
    r = anon.post("/login", data={"email": "stranger@gmail.com"})
    check("an unknown address gets the same reply as a known one",
          r.status_code == 200 and b"six-digit code" in r.data)
    check("but no code is issued for it",
          "login|stranger@gmail.com" not in codes._read())
    r = anon.post("/login", data={"email": "stranger@gmail.com", "step": "code",
                                  "code": "123456"})
    check("and it cannot sign in", r.status_code == 401)

    staff, r = sign_in("jason@usemce.com")
    check("a work address signs in as staff", r.status_code == 302, r.status_code)
    bad = app.test_client()
    bad.post("/login", data={"email": "mike@usemce.com"})
    r = bad.post("/login", data={"email": "mike@usemce.com", "step": "code", "code": "000000"})
    check("a wrong code is refused", r.status_code == 401)
    check("and leaves no session", bad.get("/").status_code == 302)
    r = anon.get("/login?next=//evil.example.com")
    check("sign-in page loads", r.status_code == 200)
    _, r = sign_in("jb@usemce.com")
    check("lands on the quotes page", r.headers.get("Location", "").endswith("/"))

    # 3. staff reach everything; dealers only the allowlist -----------------
    for path in ("/", "/quotes/new", "/tools", "/tools/fan", "/crm/", "/admin/users",
                 "/api/pricing", "/api/tokens"):
        r = staff.get(path)
        check(f"staff reach {path}", r.status_code in (200, 502, 503), r.status_code)

    r = staff.post("/admin/users", data={"action": "save", "email": "Bob@DealerCo.com",
                                         "name": "Bob", "dealership": "DealerCo"})
    check("staff add a dealer", r.status_code == 200 and b"Saved" in r.data, r.status_code)
    r = staff.post("/admin/users", data={"action": "save", "email": "x@usemce.com",
                                         "dealership": "Nope"})
    check("an MCE address cannot be made a dealer", r.status_code == 400)
    staff.post("/admin/users", data={"action": "save", "email": "amy@otherdealer.com",
                                     "name": "Amy", "dealership": "Other Dealer"})

    dealer, r = sign_in("bob@dealerco.com")
    check("an added dealer signs in", r.status_code == 302, r.status_code)
    for path in ("/tools", "/tools/fan", "/crm/", "/admin/users"):
        check(f"dealer refused {path}", dealer.get(path).status_code == 403,
              dealer.get(path).status_code)
    for path in ("/api/pricing", "/api/tokens"):
        check(f"dealer refused {path}", dealer.get(path).status_code == 403)
    check("dealer cannot add people",
          dealer.post("/admin/users", data={"action": "save", "email": "e@e.com",
                                            "dealership": "E"}).status_code == 403)
    for path in ("/", "/quotes/new"):
        check(f"dealer reaches {path}", dealer.get(path).status_code == 200)
    page = dealer.get("/").get_data(as_text=True)
    check("no staff navigation for a dealer",
          "Calculators</a>" not in page and "CRM</a>" not in page and "People</a>" not in page)

    # 4. quotes belong to a dealership ----------------------------------------
    line = [{"name": "Thing", "unitPrice": 100}]
    mine = dealer.post("/api/quotes", json={"name": "Bob job", "lines": line}).get_json()["id"]
    mces = staff.post("/api/quotes", json={"name": "MCE job", "lines": line}).get_json()["id"]
    other, _ = sign_in("amy@otherdealer.com")
    theirs = other.post("/api/quotes", json={"name": "Amy job", "lines": line}).get_json()["id"]

    check("a dealer opens their own quote", dealer.get(f"/quotes/{mine}").status_code == 200)
    for qid, whose in ((mces, "MCE's"), (theirs, "another dealer's")):
        check(f"a dealer cannot open {whose} quote",
              dealer.get(f"/quotes/{qid}").status_code == 404)
        check(f"nor edit it",
              dealer.post(f"/api/quotes/{qid}", json={"name": "x", "lines": line}
                          ).status_code == 404)
        check(f"nor delete it", dealer.post(f"/api/quotes/{qid}/delete").status_code == 404)
        check(f"nor see it listed", qid not in dealer.get("/").get_data(as_text=True))
    check("staff see every dealership's quotes",
          all(q in staff.get("/").get_data(as_text=True) for q in (mine, mces, theirs)))
    import quotes_store
    saved = quotes_store.load(mine)
    check("the quote records who made it",
          saved.get("createdBy") == "bob@dealerco.com"
          and saved.get("dealership") == "DealerCo", saved)
    dealer.post(f"/api/quotes/{mine}", json={"name": "Bob job 2", "lines": line})
    check("an edit keeps the owner", quotes_store.load(mine).get("dealership") == "DealerCo")

    # 5. switching off is immediate -------------------------------------------
    staff.post("/admin/users", data={"action": "disable", "email": "bob@dealerco.com"})
    check("a switched-off dealer is out on the next click",
          dealer.get("/").status_code == 302)
    check("and cannot sign back in", accounts.get("bob@dealerco.com") is None)
    staff.post("/admin/users", data={"action": "enable", "email": "bob@dealerco.com"})
    check("and can be switched back on", accounts.get("bob@dealerco.com") is not None)

    if FAILS:
        print(f"accounts: {len(FAILS)} problems")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — sign-in by emailed code; dealers reach only their own quotes and "
          "the dealer allowlist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
