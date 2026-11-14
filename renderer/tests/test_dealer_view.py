#!/usr/bin/env python3
"""Nothing internal reaches a dealer — and list prices are untouched.

Runs every calculator at its defaults and the intake quotes through the app as a
dealer would, and scans every answer, the quote page and the voice tools for
vendor names, vendor quote numbers, costs, markups and the pricing basis. The
same requests as staff must still carry them (the filter is not over-eager in the
wrong place) and must price identically.

    cd renderer && python3 tests/test_dealer_view.py
"""
import json
import logging
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["RENDERER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["SESSION_COOKIE_SECURE"] = "0"
os.environ.pop("SMTP_HOST", None)
logging.disable(logging.WARNING)

import accounts  # noqa: E402
import app as appmod  # noqa: E402
import calculators  # noqa: E402
import codes  # noqa: E402
import dealer_view  # noqa: E402

FAILS = []
INTERNAL_KEYS = {"price_notes", "priceBasis", "rfq", "source", "sources", "pricing_rev",
                 "openItems", "candidates", "chain", "cleaner", "referenceBom"}

JOBS = {
    "fairview venturi filter receiver": dict(
        customer_company="Fairview Mills", mill_model="XM-4430", motor_hp=200,
        product_as_written="grain ration pet food", product_match="Pet Food (high fat)",
        product_confidence="unsure", capacity_tph=15, screen_64ths=6,
        feeder=dict(diameter_in="10", cup_type="ss", rows=8, magnet_clean="scmaa"),
        include_air_system=True, air_swept=True, air_pickup="venturi",
        dust_collection="filter_receiver", airlock_fill=0.9, airlock_rpm=12,
        duct_run_ft=60, duct_elbows=4, combustible_dust=True),
    "cyclone, plenum and screw": dict(
        customer_company="Acme Feed", mill_model="XM-4430", motor_hp=200,
        product_match="Corn / Milo", product_confidence="stated", capacity_tph=20,
        screen_64ths=8, include_plenum=True, include_screw=True,
        include_air_system=True, dust_collection="cyclone"),
    "bin vent, indoors": dict(
        customer_company="Acme Feed", mill_model="XM-4430", motor_hp=200,
        product_match="Corn / Milo", product_confidence="stated", capacity_tph=15,
        screen_64ths=6, include_plenum=True, include_air_system=True,
        combustible_dust=True, indoor_install=True),
}


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}: {str(detail)[:400]}")


def sign_in(email):
    c = appmod.app.test_client()
    code, _ = codes.issue(email, "login")
    c.post("/login", data={"email": email, "step": "code", "code": code})
    return c


def leaks(obj):
    """Every internal thing in an answer, as (where, what)."""
    found = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in INTERNAL_KEYS:
                    found.append((f"{path}.{k}", "internal key"))
                if "cost" in str(k).lower():
                    found.append((f"{path}.{k}", "cost key"))
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, str) and dealer_view.is_internal(o):
            found.append((path, o[:120]))
    walk(obj, "")
    return found


def prices(lines):
    return [(l.get("name"), l.get("unitPrice"), l.get("quantity")) for l in lines or []]


def main():
    accounts.save_dealer("dee@dealerco.com", "Dee", "DealerCo")
    dealer = sign_in("dee@dealerco.com")
    staff = sign_in("jason@usemce.com")

    # 1. every calculator, through the API and the voice tool ---------------
    staff_leaky = 0
    for key in calculators.CALCULATORS:
        d = dealer.post(f"/api/calc/{key}", json={})
        s = staff.post(f"/api/calc/{key}", json={})
        dj, sj = d.get_json(), s.get_json()
        check(f"{key}: dealer answer has nothing internal", not leaks(dj), leaks(dj))
        staff_leaky += bool(leaks(sj))
        check(f"{key}: same list total", dj.get("total") == sj.get("total"),
              (dj.get("total"), sj.get("total")))
        check(f"{key}: same priced lines (by price)",
              [p[1] for p in prices(dj.get("lines"))] == [p[1] for p in prices(sj.get("lines"))],
              (prices(dj.get("lines")), prices(sj.get("lines"))))
        v = dealer.post(f"/api/voice/size/{key}", json={"inputs": {}}).get_json()
        check(f"{key}: voice tool has nothing internal", not leaks(v), leaks(v))
        f = dealer.get(f"/api/voice/fields/{key}").get_json()
        check(f"{key}: field list has nothing internal", not leaks(f), leaks(f))
        check(f"{key}: no pricing factors offered",
              not any(i["key"] in dealer_view.locked_inputs.get(key, ())
                      for i in f.get("inputs", [])))
    check("the staff answers still carry the basis (the filter is dealer-only)",
          staff_leaky >= 3, staff_leaky)
    eq = dealer.get("/api/voice/equipment").get_json()
    check("equipment list has nothing internal", not leaks(eq), leaks(eq))

    # 2. a dealer cannot move the pricing factors ------------------------------
    base = dealer.post("/api/calc/hammermill", json={}).get_json()["total"]
    pushed = dealer.post("/api/calc/hammermill",
                         json={"millMult": 0.5, "feederMult": 0.5}).get_json()["total"]
    check("a dealer's multipliers are ignored", base == pushed, (base, pushed))
    moved = staff.post("/api/calc/hammermill", json={"millMult": 0.5}).get_json()["total"]
    check("staff still can move them", moved != base, (moved, base))

    # 3. drafts and quotes ---------------------------------------------------
    for name, job in JOBS.items():
        d = dealer.post("/api/voice/draft", json={"job": job}).get_json()
        s = staff.post("/api/voice/draft", json={"job": job}).get_json()
        check(f"{name}: draft built", "quote" in d, d.get("error"))
        if "quote" not in d:
            continue
        check(f"{name}: dealer draft has nothing internal", not leaks(d), leaks(d))
        check(f"{name}: same list prices",
              [p[1] for p in prices(d["quote"]["lines"])]
              == [p[1] for p in prices(s["quote"]["lines"])],
              (prices(d["quote"]["lines"]), prices(s["quote"]["lines"])))
        check(f"{name}: staff draft keeps MCE's open items",
              bool(s["quote"].get("openItems")))
        saved = dealer.post("/api/quotes", json={**d["quote"], "name": name}).get_json()
        page = dealer.get(f"/quotes/{saved['id']}").get_data(as_text=True)
        check(f"{name}: proposal page has nothing internal",
              not dealer_view.is_internal(page),
              [p.pattern for p in dealer_view._PATTERNS if p.search(page)])
        form = dealer.get(f"/quotes/{saved['id']}/edit").get_data(as_text=True)
        check(f"{name}: edit form has nothing internal",
              not dealer_view.is_internal(form),
              [p.pattern for p in dealer_view._PATTERNS if p.search(form)])

    page = dealer.get("/quotes/new").get_data(as_text=True)
    check("the new-quote form has nothing internal", not dealer_view.is_internal(page),
          [p.pattern for p in dealer_view._PATTERNS if p.search(page)])

    if FAILS:
        print(f"dealer view: {len(FAILS)} problems")
        for f in FAILS:
            print("  " + f)
        return 1
    print(f"OK — {len(calculators.CALCULATORS)} calculators and {len(JOBS)} quotes reach "
          "a dealer with nothing internal, at the same list prices.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
