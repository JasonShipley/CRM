#!/usr/bin/env python3
"""One quote format, whichever path built it.

A quote can reach the page two ways: from the builder's own store, or read out of
Twenty CRM. They used to build their template contexts independently, so the CRM
rendered a thinner document — not because anyone decided it should, but because
`from_twenty` never defined the variables the design basis, schedule and
furnished-by-others sections read, and Jinja silently omits an undefined name.

Both now go through render_ctx.base_context. These cases hold them there.

    cd renderer && python3 tests/test_quote_format.py
"""
import datetime
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import crm  # noqa: E402
import quote_from_job as qfj  # noqa: E402
import render_ctx  # noqa: E402
from test_intake import jb_request  # noqa: E402

FAILS = []
TODAY = datetime.date(2026, 9, 26)


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + detail if detail else ''}")


def template_variables():
    """Every name quote.html reads, so this test cannot fall behind the template."""
    html = (HERE.parent / "templates" / "quote.html").read_text()
    ident = r"[a-z_][a-z0-9_]*"          # logo_b64 has a digit in it
    names = set(re.findall(r"\{\{ *(" + ident + ")", html))
    names |= set(re.findall(r"\{% *(?:if|for) +(" + ident + ")", html))
    names |= set(re.findall(r"\{% *for +" + ident + r" +in +(" + ident + ")", html))
    # A `{% for X in Y %}` binds X inside the loop, so X is not a context key.
    # Derive those from the template rather than listing them here, so the test
    # cannot fall out of step with a renamed loop variable.
    locals_ = set(re.findall(r"\{% *for +(" + ident + r") +in", html))
    # `{% set x = ... %}` binds x too — the template uses one for the address and a
    # namespace to auto-number the sections, which is how an omitted section does
    # not leave a gap in the numbering.
    locals_ |= set(re.findall(r"\{% *set +(" + ident + r") *=", html))
    return names - locals_ - {"loop", "not", "and", "or", "is", "none", "true", "false"}


def fake_twenty_quote():
    """The shape crm.from_twenty builds from, with Twenty's own field names."""
    return {
        "id": "abc", "name": "XM-4460 Hammer Mills", "quoteNumber": "MCEQ2609TESTR1",
        "status": "DRAFT", "amount": {"amountMicros": "125000000000",
                                      "currencyCode": "USD"},
        "expirationDate": "2026-12-31", "terms": "50% down", "comments": "",
        "preparedBy": "JASON_SHIPLEY", "createdAt": "2026-09-26T00:00:00Z",
        "sourceCreatedAt": None, "qboEstimateId": None,
        "company": {"name": "Mid-States Companies", "address": {
            "addressStreet1": "1 Mill Rd", "addressStreet2": "", "addressCity": "Wichita",
            "addressState": "KS", "addressPostcode": "67201", "addressCountry": "USA"}},
        "contact": {"name": {"firstName": "Pat", "lastName": "Buyer"},
                    "emails": {"primaryEmail": "pat@example.com"},
                    "phones": {"primaryPhoneNumber": "5551234",
                               "primaryPhoneCallingCode": "+1"}},
        "opportunity": {"name": "8 Mills"},
        "lineItems": {"edges": [{"node": {
            "id": "l1", "name": "XM-4460 Hammermill", "itemDescription": "30\" x 60\" screen",
            "quantity": 8, "lineNumber": 1, "sku": "XM-4460",
            "unitPrice": {"amountMicros": "15000000000"},
            "unitDiscount": {"amountMicros": "0"}, "discountPercent": 0,
            "amount": {"amountMicros": "120000000000"}}}]},
    }


def main():
    wanted = template_variables()

    # 1. the shared base must cover the template, or a section can vanish silently
    missing = wanted - set(render_ctx.BASE_CONTEXT) - set(render_ctx.assets()) - {"fmt_date"}
    check("base context covers every template variable", not missing, str(sorted(missing)))

    # 2. the builder path
    q = qfj.build(jb_request(), today=TODAY, delivery_weeks="10–12")
    q["createdAt"] = TODAY.isoformat()
    q["preparedBy"] = "JASON_SHIPLEY"
    store_ctx = render_ctx.from_store(q)

    # 3. the CRM path, without touching Twenty
    real_query = crm.query
    crm.query = lambda *a, **k: {"quote": fake_twenty_quote()}
    try:
        crm_ctx = crm.from_twenty("abc")
    finally:
        crm.query = real_query

    # 4. the two must offer the template the same names — that IS the standard
    check("both paths expose the same keys",
          set(store_ctx) == set(crm_ctx),
          f"store-only={sorted(set(store_ctx) - set(crm_ctx))} "
          f"crm-only={sorted(set(crm_ctx) - set(store_ctx))}")

    for label, ctx in (("store", store_ctx), ("crm", crm_ctx)):
        gap = wanted - set(ctx)
        check(f"{label} context covers the template", not gap, str(sorted(gap)))

    # 5. both must actually render, and to the same sections where data exists
    import app as appmod
    from flask import render_template
    with appmod.app.test_request_context():
        store_html = render_template("quote.html", **store_ctx)
        crm_html = render_template("quote.html", **crm_ctx)
    for label, html in (("store", store_html), ("crm", crm_html)):
        check(f"{label} renders", len(html) > 2000, str(len(html)))
        for heading in ("SCOPE OF SUPPLY", "TOTAL"):
            check(f"{label} has {heading}", heading in html.upper())

    # 6. the schedule is one list, so it cannot drift between the two
    check("CRM carries the standard schedule",
          [r["item"] for r in crm_ctx["schedule"]]
          == [r["item"] for r in render_ctx.STANDARD_SCHEDULE],
          str(crm_ctx["schedule"]))
    check("builder carries the same schedule items",
          [r["item"] for r in store_ctx["schedule"]]
          == [r["item"] for r in render_ctx.STANDARD_SCHEDULE],
          str(store_ctx["schedule"]))
    check("builder filled the delivery line",
          "10–12 weeks" in store_ctx["schedule"][1]["basis"],
          str(store_ctx["schedule"][1]))
    check("CRM leaves delivery flagged for input",
          crm_ctx["schedule"][1].get("needsInput"), str(crm_ctx["schedule"][1]))

    if FAILS:
        print(f"{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — the builder and the CRM render the same quote format.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
