#!/usr/bin/env python3
"""Tests for the free-text intake path.

Claude's part (interpret.py) is a single extraction call and is not exercised
here — these tests cover everything downstream of it, which is where the numbers
come from. They feed quote_from_job.build() the JobRequest objects Claude is
instructed to produce and assert on the proposal that falls out.

    cd renderer && python3 tests/test_intake.py
"""
import datetime
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import quote_from_job as qfj  # noqa: E402
from calculators import _vendor as _v  # noqa: E402
from interpret import FeederSpec, JobRequest  # noqa: E402

TODAY = datetime.date(2026, 9, 23)
FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + detail if detail else ''}")


def design(quote, parameter):
    return next((r for r in quote["designBasis"] if r["parameter"] == parameter), None)


def open_text(quote):
    return " || ".join(quote["openItems"])


def jb_request(**over):
    """The request JB actually sent, as Claude is instructed to extract it."""
    base = dict(
        customer_company="Fairview Mills", customer_contact="Dennis Heideman",
        mill_model="XM-4430", motor_hp=200,
        product_as_written="grain ration pet food",
        product_match="Pet Food (high fat)", product_confidence="unsure",
        capacity_tph=15, screen_64ths=6,
        feeder=FeederSpec(diameter_in="10", cup_type="ss", rows=None,
                          magnet_clean="scmaa",
                          as_written='SS round cup 8-4row 10" auto selfclean feeder'),
        include_plenum=True, include_screw=True, include_air_system=True,
        ambiguities=['Feeder rows written as "8-4row" — 8-row or 4-row?'],
    )
    base.update(over)
    return JobRequest(**base)


def test_jb_request():
    q = qfj.build(jb_request(), today=TODAY)

    check("reference format", q["quoteNumber"] == "MCEQ2609FAIRVIEWMILLSR1", q["quoteNumber"])
    check("customer carried through",
          q["customer"]["company"] == "Fairview Mills"
          and q["customer"]["contact"] == "Dennis Heideman")

    # The rep named the mill, so it must be quoted — not silently swapped for the
    # auto match. The shortfall is reported to MCE internally and must NOT reach
    # the customer-facing design basis (Jason, 2026-09-23).
    check("named mill is honoured", "XM-4430" in q["name"], q["name"])
    area = design(q, "Screen area")
    check("undersize kept off the proposal", area and not area["needsInput"], str(area))
    check("no undersize wording on the design basis",
          area and "undersized" not in (area["notes"] + area["value"]).lower(), str(area))
    # the shortfall is whatever the mill table says it is — assert that it is
    # reported and points at the right requirement, not a number frozen in a test
    check("undersize still reported internally",
          re.search(r"Screen area is [\d,]+ in² short of the [\d,]+ in² requirement",
                    open_text(q)) is not None, open_text(q))
    check("auto match named internally", "XM-4440" in open_text(q))

    # The ambiguity Claude reported must survive into the proposal, not be resolved.
    check("feeder ambiguity survives", "8-4row" in open_text(q))
    check("product confidence flagged", "high fat" in open_text(q).lower())

    names = [l["name"] for l in q["lines"]]
    check("mill quoted", any("XM-4430 Hammermill" == n for n in names), str(names))
    check("feeder quoted", any("Rotary Feeder" in n for n in names))
    check("plenum quoted", any("Plenum Chamber" in n for n in names))
    check("screw quoted", any("Screw Conveyor" in n for n in names))
    check("baghouse sized from the mill", any("Baghouse" in n for n in names))
    # A baghouse cleans the air and the fan discharges to atmosphere after it,
    # so no cyclone is quoted and the fan comes from the AirPro lineup, priced.
    check("no cyclone alongside a baghouse",
          not any(n.startswith("Cyclone") for n in names), str(names))
    fan = next((l for l in q["lines"] if l["name"].startswith("Fan")), None)
    # the line carries the model number, not the vendor — see
    # test_no_vendor_brands_on_customer_lines
    check("fan selected from the AirPro lineup",
          fan and fan.get("sku") in _v.AIRPRO_FANS_BY_MODEL, str(fan))
    check("fan is priced, not TBD", fan and not fan.get("needsPrice") and fan["unitPrice"] > 0,
          str(fan))
    check("ductwork listed unpriced — still no calculator or basis for it",
          any(n.startswith("Ductwork") for n in names), str(names))
    # The airlock is a buy-out with a real vendor cost on file, so it is priced.
    airlock = next((l for l in q["lines"] if l["name"].startswith("Rotary Airlock")), None)
    check("airlock priced from the vendor basis",
          airlock and airlock["unitPrice"] > 0 and not airlock.get("needsPrice"),
          str(airlock))
    check("no vendor quote number on the airlock line",
          airlock and "024350" not in airlock["description"], str(airlock))
    check("airlock basis is internal",
          "buy-out divisor" in open_text(q), open_text(q))
    # The baghouse budget is scaled from one Airlanco pair — it must say so.
    bh = next((l for l in q["lines"] if "Baghouse" in l["name"]), None)
    check("baghouse carries a budget price", bh and bh["unitPrice"] > 0, str(bh))
    check("baghouse budget flagged internally",
          "budget figure only" in open_text(q), open_text(q))
    check("no vendor name on the baghouse line",
          bh and "Airlanco" not in bh["description"], str(bh))
    screw = next((l for l in q["lines"] if "Screw Conveyor" in l["name"]), None)
    check("screw priced from the SCC basis",
          screw and not screw.get("needsPrice") and screw["unitPrice"] > 0, str(screw))
    # Pricing provenance stays internal — the line says what is supplied.
    check("no vendor quote number on the customer line",
          screw and "SCC H51" not in screw["description"], str(screw))
    check("no stainless commentary on the customer line",
          screw and "stainless" not in screw["description"].lower(), str(screw))
    # The budget is modelled from MCE's SCC quote history, so it must say so and
    # point at getting a real quote.
    check("modelled budget says so", "not a quote for this unit" in open_text(q),
          open_text(q))
    check("points at SCC for a real price", "have scc price" in open_text(q).lower(),
          open_text(q))

    unpriced = [l["name"] for l in q["lines"] + q["netItems"] if l.get("needsPrice")]
    check("uncalculated items are unpriced, not zero-priced",
          all(l.get("unitPrice") in (0, "", None) for l in q["lines"] if l.get("needsPrice")))
    motor = q["netItems"][0] if q["netItems"] else None
    check("motor priced from the vendor cost on file",
          motor and motor["unitPrice"] > 0 and not motor.get("needsPrice"), str(motor))
    check("motor still says it is net-priced",
          motor and "Priced net" in motor["description"], str(motor))
    check("motor basis is internal",
          "buy-out divisor" in open_text(q) and "Teco" in open_text(q), open_text(q))
    check("no motor make on the customer line",
          motor and "Teco" not in motor["description"], str(motor))
    duct = next((l for l in q["lines"] if l["name"].startswith("Ductwork")), None)
    check("ductwork is sized but priced on request",
          duct and duct.get("needsPrice") and "priced upon request" in duct["name"],
          str(duct))
    check("ductwork carries a diameter from the calculator",
          duct and "dia duct at" in duct["description"], str(duct))
    check("ductwork reason is recorded internally",
          "priced on request" in open_text(q), open_text(q))
    check("screw budget flagged as modelled",
          "modelled budget" in open_text(q).lower(), open_text(q))

    check("proposal sections present",
          all(q[k] for k in ("designBasis", "byOthers", "schedule")))
    check("draft by default", q["status"] == "DRAFT")


def test_motor_conflict():
    """JB said 200 HP. At index 50 the math says 100 HP — that must not pass silently."""
    q = qfj.build(jb_request(product_match="Pet Food (regular / whole kibble)"), today=TODAY)
    check("motor conflict reported internally",
          "200 HP" in open_text(q) and "100 HP" in open_text(q), open_text(q))
    drive = design(q, "Mill drive")
    check("motor conflict kept off the proposal", drive and not drive["needsInput"], str(drive))

    # And when they agree, no conflict is raised.
    q2 = qfj.build(jb_request(motor_hp=200), today=TODAY)
    check("no false conflict at the matching index",
          "Confirm which governs" not in open_text(q2))


def test_thin_request():
    """A request missing the governing specs must refuse to invent them."""
    q = qfj.build(JobRequest(customer_company="Acme Feed",
                             product_as_written="corn", capacity_tph=None), today=TODAY)
    check("missing throughput flagged", "Throughput was not stated" in open_text(q))
    check("missing screen flagged", "Screen size was not stated" in open_text(q))
    check("nothing invented", q["lines"] == [], str(q["lines"]))
    check("still a usable skeleton", q["quoteNumber"].startswith("MCEQ")
          and bool(q["designBasis"]))
    cap = design(q, "Capacity")
    check("capacity row is orange TBD", cap and cap["needsInput"] and cap["value"] == "TBD")


def test_no_air_system():
    """Not asking for an air system moves it to furnished-by-others."""
    q = qfj.build(jb_request(include_air_system=False), today=TODAY)
    names = [l["name"] for l in q["lines"]]
    check("no air lines quoted", not any(n.startswith("Fan") for n in names), str(names))
    check("no baghouse quoted", not any("Baghouse" in n for n in names), str(names))
    check("air moved to by-others",
          any("Air-relief system" in x for x in q["byOthers"]), str(q["byOthers"]))


def test_cyclone_when_the_rep_asks_for_one():
    """A rep who names a cyclone gets a sized cyclone and no baghouse. The
    cyclone is priced from MCE's own sold prices, and the provenance stays off the
    customer's page."""
    q = qfj.build(jb_request(dust_collection="cyclone"), today=TODAY)
    names = [l["name"] for l in q["lines"]]
    check("no baghouse quoted", not any("Baghouse" in n for n in names), str(names))
    cyc = next((l for l in q["lines"] if l["name"].startswith("Cyclone")), None)
    check("cyclone line present", cyc is not None, str(names))
    if cyc:
        check("cyclone is sized, not TBD", "TBD" not in cyc["name"], cyc["name"])
        check("cyclone is priced", cyc["unitPrice"] > 0 and not cyc.get("needsPrice"),
              str(cyc))
        check("no pricing provenance on the customer line",
              "NEMO" not in cyc["description"] and "$" not in cyc["description"],
              cyc["description"])
    # the fan came with the baghouse; without one it is back to TBD
    check("fan back to TBD", any(n.startswith("Fan — size and price TBD") for n in names),
          str(names))
    check("cyclone price basis recorded internally",
          "cyclone" in open_text(q).lower(), open_text(q))
    # and the size itself is the calculator's, off the mill's own plenum airflow
    cy = next((s for s in q["sizing"] if s["calculator"] == "Cyclone"), None)
    check("cyclone sizing recorded", cy is not None, str([s["calculator"] for s in q["sizing"]]))


def test_baghouse_is_still_the_default():
    """Silence about dust collection keeps MCE's standard: a filter, and with it
    no cyclone at all."""
    q = qfj.build(jb_request(), today=TODAY)
    names = [l["name"] for l in q["lines"]]
    check("baghouse quoted by default", any("Baghouse" in n for n in names), str(names))
    check("no cyclone alongside a baghouse",
          not any(n.startswith("Cyclone") for n in names), str(names))


def test_no_vendor_brands_on_customer_lines():
    """Buy-out lines carry the model number and the specification — airflow,
    speeds, HP — but never the vendor's name. Which vendor supplies it, and which
    quote priced it, are MCE's business and stay in the internal open items."""
    brands = ["AirPro", "Airlanco", "Prater", "Kice", "SCC", "Coperion"]
    for over in ({}, {"dust_collection": "cyclone"}):
        q = qfj.build(jb_request(**over), today=TODAY)
        for line in q["lines"] + q["netItems"]:
            blob = " ".join([line["name"], line.get("description") or "",
                             str(line.get("sku") or "")]).lower()
            for b in brands:
                check(f"no {b} on a customer line",
                      b.lower() not in blob, f'{line["name"]}: {blob[:140]}')
    # and the specs the rep needs are still there
    q = qfj.build(jb_request(), today=TODAY)
    fan = next(l for l in q["lines"] if l["name"].startswith("Fan"))
    for token in ("ACFM", "RPM", "HP"):
        check(f"fan line still shows {token}", token in fan["description"], fan["description"])
    air = next(l for l in q["lines"] if l["name"].startswith("Rotary Airlock"))
    for token in ("HP", "RPM"):
        check(f"airlock line still shows {token}", token in air["description"],
              air["description"])
    # the provenance is not lost — it moved
    check("fan basis recorded internally", "AirPro" in open_text(q), open_text(q))
    check("airlock basis recorded internally", "Airlanco" in open_text(q), open_text(q))


def test_delivery_weeks():
    """Lead time moves with the backlog, so there is no default: unset it stays a
    blank flagged for input, and set it prints and stops being flagged."""
    q = qfj.build(jb_request(), today=TODAY)
    d = next(r for r in q["schedule"] if r["item"] == "Delivery")
    check("unset delivery stays a blank", d.get("needsInput") and "__" in d["basis"], str(d))
    q = qfj.build(jb_request(), today=TODAY, delivery_weeks="10–12")
    d = next(r for r in q["schedule"] if r["item"] == "Delivery")
    check("set delivery prints", "10–12 weeks after receipt of order" in d["basis"], str(d))
    check("set delivery is no longer flagged", not d.get("needsInput"), str(d))
    check("delivery carried on the quote", q["deliveryWeeks"] == "10–12", str(q.get("deliveryWeeks")))


def test_quantity():
    q = qfj.build(jb_request(quantity=8), today=TODAY)
    check("quantity on every line", all(l["quantity"] == 8 for l in q["lines"]))
    check("quantity in the title", "(8 Mills)" in q["name"], q["name"])


def test_fan_quote_validity():
    """A confirmed quote stops flagging, but only for as long as the confirmation
    is good for — it must start flagging again on its own."""
    from calculators import _vendor as v
    check("confirmed quote does not flag",
          not v.fan_quote_stale(v.AIRPRO_CONFIRMED))
    check("still good inside the confirmation window",
          not v.fan_quote_stale(v.AIRPRO_CONFIRMED + datetime.timedelta(days=120)))
    check("flags again once the confirmation lapses",
          v.fan_quote_stale(v.AIRPRO_CONFIRMED + v.AIRPRO_CONFIRMED_GOOD_FOR
                            + datetime.timedelta(days=1)))
    # and with no confirmation at all, the quote's own expiry governs
    saved = v.AIRPRO_CONFIRMED
    try:
        v.AIRPRO_CONFIRMED = None
        check("unconfirmed expired quote flags",
              v.fan_quote_stale(v.AIRPRO_QUOTE_EXPIRES + datetime.timedelta(days=1)))
        check("unconfirmed live quote does not flag",
              not v.fan_quote_stale(v.AIRPRO_QUOTE_EXPIRES - datetime.timedelta(days=1)))
    finally:
        v.AIRPRO_CONFIRMED = saved


def test_reference_slug():
    cases = {"Mid-States Companies": "MCEQ2609MIDSTATESR1",       # matches MCE's real ref
             "Fairview Mills": "MCEQ2609FAIRVIEWMILLSR1",
             "": "MCEQ2609CUSTOMERR1"}
    for company, want in cases.items():
        got = qfj.quote_number(company, TODAY)
        check(f"reference for {company!r}", got == want, f"got {got}, want {want}")


def main():
    for fn in (test_jb_request, test_motor_conflict, test_thin_request,
               test_no_air_system, test_cyclone_when_the_rep_asks_for_one,
               test_baghouse_is_still_the_default,
               test_no_vendor_brands_on_customer_lines, test_delivery_weeks,
               test_quantity,
               test_fan_quote_validity, test_reference_slug):
        fn()
        print(f"  {fn.__name__}")
    if FAILS:
        print(f"\n{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("\nOK — intake builds the proposal MCE's format expects, and flags rather "
          "than guesses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
