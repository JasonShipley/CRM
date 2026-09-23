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
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import quote_from_job as qfj  # noqa: E402
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
    # auto match — but the shortfall has to be stated.
    check("named mill is honoured", "XM-4430" in q["name"], q["name"])
    area = design(q, "Screen area")
    check("undersize flagged orange", area and area["needsInput"], str(area))
    check("auto match named", "XM-4440" in open_text(q))

    # The ambiguity Claude reported must survive into the proposal, not be resolved.
    check("feeder ambiguity survives", "8-4row" in open_text(q))
    check("product confidence flagged", "high fat" in open_text(q).lower())

    names = [l["name"] for l in q["lines"]]
    check("mill quoted", any("XM-4430 Hammermill" == n for n in names), str(names))
    check("feeder quoted", any("Rotary Feeder" in n for n in names))
    check("plenum quoted", any("Plenum Chamber" in n for n in names))
    check("screw quoted", any("Screw Conveyor" in n for n in names))
    check("baghouse sized from the mill", any("Baghouse" in n for n in names))
    for item in ("Fan", "Cyclone", "Ductwork", "Airlock"):
        check(f"{item} listed unpriced", any(n.startswith(item) for n in names), str(names))

    unpriced = [l["name"] for l in q["lines"] + q["netItems"] if l.get("needsPrice")]
    check("uncalculated items are unpriced, not zero-priced",
          all(l.get("unitPrice") in (0, "", None) for l in q["lines"] if l.get("needsPrice")))
    check("motor is net-priced and flagged",
          q["netItems"] and q["netItems"][0].get("needsPrice"), str(q["netItems"]))
    check("air system openly unpriced", "no MCE calculator" in open_text(q), str(unpriced))

    check("proposal sections present",
          all(q[k] for k in ("designBasis", "byOthers", "schedule")))
    check("draft by default", q["status"] == "DRAFT")


def test_motor_conflict():
    """JB said 200 HP. At index 50 the math says 100 HP — that must not pass silently."""
    q = qfj.build(jb_request(product_match="Pet Food (regular / whole kibble)"), today=TODAY)
    check("motor conflict reported", "200 HP" in open_text(q) and "100 HP" in open_text(q),
          open_text(q))
    drive = design(q, "Mill drive")
    check("motor conflict is orange", drive and drive["needsInput"], str(drive))

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
    check("air moved to by-others",
          any("Air-relief system" in x for x in q["byOthers"]), str(q["byOthers"]))


def test_quantity():
    q = qfj.build(jb_request(quantity=8), today=TODAY)
    check("quantity on every line", all(l["quantity"] == 8 for l in q["lines"]))
    check("quantity in the title", "(8 Mills)" in q["name"], q["name"])


def test_reference_slug():
    cases = {"Mid-States Companies": "MCEQ2609MIDSTATESR1",       # matches MCE's real ref
             "Fairview Mills": "MCEQ2609FAIRVIEWMILLSR1",
             "": "MCEQ2609CUSTOMERR1"}
    for company, want in cases.items():
        got = qfj.quote_number(company, TODAY)
        check(f"reference for {company!r}", got == want, f"got {got}, want {want}")


def main():
    for fn in (test_jb_request, test_motor_conflict, test_thin_request,
               test_no_air_system, test_quantity, test_reference_slug):
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
