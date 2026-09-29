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

    if FAILS:
        print(f"{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — tokens are self-issued to work addresses and reach only the quote API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
