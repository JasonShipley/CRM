#!/usr/bin/env python3
"""Self-service API tokens: who gets one, what it reaches, and what it leaks.

    cd renderer && python3 tests/test_tokens.py
"""
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["RENDERER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["RENDERER_PASSWORD"] = "browser-password"

import app as appmod  # noqa: E402
import tokens  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + detail if detail else ''}")



def production_shape():
    """A second app the way it actually runs on the server.

    RENDERER_PASSWORD is UNSET in production — Caddy holds the password for the
    pages a person uses. app.py reads it at import, so this reloads the module
    with a clean environment and its own data directory.
    """
    import importlib
    saved_pw = os.environ.get("RENDERER_PASSWORD")
    saved_dir = os.environ["RENDERER_DATA_DIR"]
    os.environ["RENDERER_PASSWORD"] = ""
    os.environ["RENDERER_DATA_DIR"] = tempfile.mkdtemp()
    importlib.reload(tokens)
    prod = importlib.reload(appmod)
    client = prod.app.test_client()

    def restore():
        os.environ["RENDERER_PASSWORD"] = saved_pw or ""
        os.environ["RENDERER_DATA_DIR"] = saved_dir
        importlib.reload(tokens)
        importlib.reload(appmod)

    return client, restore


def test_api_is_closed_without_a_token():
    """The one that matters in production.

    Caddy routes /api/ straight through with NO basic auth, because a basic-auth
    challenge rejects the bearer header before the app ever sees it. That makes
    app.py the only guard in front of the API — and in production
    RENDERER_PASSWORD is unset.

    So an /api/ request with no valid token has to be refused even with no
    RENDERER_PASSWORD. Getting this wrong publishes MCE's pricing basis and every
    quote to the internet, which is exactly what an unguarded /api/ did the first
    time it was routed past Caddy.
    """
    c, restore = production_shape()
    try:
        check("the app really has no password of its own",
              appmod.RENDERER_PASSWORD == "", repr(appmod.RENDERER_PASSWORD))
        for path in ("/api/tokens", "/api/pricing"):
            r = c.get(path)
            check(f"{path} is refused without a token", r.status_code == 401,
                  f"{r.status_code} {r.get_data()[:120]}")
            check(f"{path} leaks nothing in the refusal",
                  "Bliss" not in r.get_data(as_text=True), r.get_data(as_text=True)[:120])
        check("and a write is refused too",
              c.post("/api/quotes", json={}).status_code == 401)
        check("an invalid token is refused",
              c.get("/api/pricing",
                    headers={"Authorization": "Bearer mceq_nope"}).status_code == 401)

        # the self-service flow stays open — nobody could get a token otherwise
        check("issuing a token stays open",
              c.post("/api/tokens/request",
                     json={"email": "jb@usemce.com"}).status_code == 200)
        check("but still only to a work address",
              c.post("/api/tokens/request",
                     json={"email": "someone@gmail.com"}).status_code == 400)

        # the pages a person uses are left to Caddy; double-locking them here
        # would break the deployed login
        check("browser pages are left to Caddy", c.get("/tools").status_code == 200)

        # and a real token gets in
        code, _ = tokens.request_code("jb@usemce.com")
        token = c.post("/api/tokens/confirm",
                       json={"email": "jb@usemce.com", "code": code}).get_json()["token"]
        r = c.get("/api/pricing", headers={"Authorization": f"Bearer {token}"})
        check("a valid token reaches the API", r.status_code == 200, r.status_code)
    finally:
        restore()


def main():
    c = appmod.app.test_client()


    # 1. only work domains
    r = c.post("/api/tokens/request", json={"email": "someone@gmail.com"})
    check("an outside address is refused", r.status_code == 400, str(r.status_code))
    check("and told why", "work domain" in r.get_json()["error"], str(r.get_json()))
    check("a work address is accepted",
          c.post("/api/tokens/request",
                 json={"email": "jb@usemce.com"}).status_code == 200)

    # 2. the code is the gate
    code, _ = tokens.request_code("jb@usemce.com")
    bad = c.post("/api/tokens/confirm", json={"email": "jb@usemce.com", "code": "000000"})
    check("a wrong code gets nothing", bad.status_code == 400, str(bad.get_json()))
    ok = c.post("/api/tokens/confirm",
                json={"email": "jb@usemce.com", "code": code, "label": "JB laptop"})
    check("the right code issues a token", ok.status_code == 200, str(ok.get_json()))
    token = ok.get_json()["token"]
    check("the token is prefixed so it is recognisable", token.startswith("mceq_"))

    # 3. the token is stored as a hash, never in the clear
    stored = json.loads((pathlib.Path(os.environ["RENDERER_DATA_DIR"])
                         / "api_tokens.json").read_text())
    check("no token in the store", not any(token in json.dumps(v) for v in stored.values()),
          "a token appears in the token file")
    check("the store keys on a hash", all(len(k) == 64 for k in stored), str(list(stored)))

    # 4. what a token reaches, and what it does not
    h = {"Authorization": "Bearer " + token}
    check("no credential, no entry", c.get("/quotes/new").status_code == 302)
    check("the basis is readable", c.get("/api/pricing", headers=h).status_code == 200)
    check("the calculators run",
          c.post("/api/calc/fan", json={"cfm": 5850, "sp": 19, "service": "radial"},
                 headers=h).status_code == 200)
    denied = c.get("/quotes/new", headers=h)
    check("but the browser app is not a token's to roam", denied.status_code == 403,
          str(denied.status_code))
    check("and the refusal says what a token is for",
          "quote and calculator APIs" in denied.get_json()["error"],
          str(denied.get_json()))

    bad_tok = c.get("/api/pricing", headers={"Authorization": "Bearer mceq_nonsense"})
    check("a made-up token is refused", bad_tok.status_code == 401, str(bad_tok.status_code))

    # 5. revocation is immediate, and scoped to the owner
    mine = c.get("/api/tokens", headers=h).get_json()["tokens"]
    check("a holder sees only their own", all(t["email"] == "jb@usemce.com" for t in mine),
          str(mine))
    check("and never the token itself",
          not any("token" in t for t in mine), str(mine))
    tid = mine[0]["id"]
    check("revoke reports success",
          c.post(f"/api/tokens/{tid}/revoke", headers=h).status_code == 200)
    check("and the token stops working straight away",
          c.get("/api/pricing", headers=h).status_code == 401)

    # 6. one person cannot revoke another's
    code2, _ = tokens.request_code("mike@usemce.com")
    t2 = c.post("/api/tokens/confirm",
                json={"email": "mike@usemce.com", "code": code2}).get_json()["token"]
    code3, _ = tokens.request_code("jason@usemce.com")
    t3 = c.post("/api/tokens/confirm",
                json={"email": "jason@usemce.com", "code": code3}).get_json()["token"]
    mikes = c.get("/api/tokens", headers={"Authorization": "Bearer " + t2}
                  ).get_json()["tokens"][0]["id"]
    stolen = c.post(f"/api/tokens/{mikes}/revoke",
                    headers={"Authorization": "Bearer " + t3})
    check("someone else's token is not yours to revoke", stolen.status_code == 404,
          str(stolen.status_code))
    check("and it still works",
          c.get("/api/pricing", headers={"Authorization": "Bearer " + t2}
                ).status_code == 200)

    # 6. and the production shape: no app password, Caddy not in front of /api/
    test_api_is_closed_without_a_token()

    if FAILS:
        print(f"{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — tokens are self-issued to work addresses and reach only the quote API.")
    return 0



if __name__ == "__main__":
    sys.exit(main())
