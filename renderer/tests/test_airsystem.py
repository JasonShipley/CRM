#!/usr/bin/env python3
"""The air-system chain, and that it agrees with the quote builder.

One airflow drives the filter, the fan, the airlock and the duct. Two things can go
wrong: the chain derives the wrong airflow, or it derives the right one and then
disagrees with what the quote builder would have produced for the same mill. Both
are covered here.

    cd renderer && python3 tests/test_airsystem.py
"""
import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import quote_from_job as qfj  # noqa: E402
from calculators import _vendor, airsystem  # noqa: E402
from calculators._fmt import money  # noqa: E402
from calculators._data import MCE_XM_MILLS  # noqa: E402
from test_intake import jb_request  # noqa: E402

FAILS = []
TODAY = datetime.date(2026, 9, 26)


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + detail if detail else ''}")


def main():
    # 1. every basis that should reach the same airflow, does
    area = next(m["area"] for m in MCE_XM_MILLS if m["model"] == "XM-4430")
    by_model = airsystem.size({"mode": "millModel", "millModel": "XM-4430"})
    by_area = airsystem.size({"mode": "mill", "screenArea": area})
    by_cfm = airsystem.size({"mode": "cfm", "cfm": area * 1.3})
    check("model, area and CFM bases agree",
          by_model["cfm"] == by_area["cfm"] == by_cfm["cfm"],
          f'{by_model["cfm"]} / {by_area["cfm"]} / {by_cfm["cfm"]}')
    check("and they pick the same equipment",
          [l["name"] for l in by_model["lines"]] == [l["name"] for l in by_cfm["lines"]])

    # a bare model number is what a rep would actually type
    check("a bare model number works",
          airsystem.size({"mode": "millModel", "millModel": "4430"})["cfm"]
          == by_model["cfm"])

    # 2. the XM-4460 cross-check: MCE's own Mid-States proposal states 9,360 CFM
    #    for that mill, which is 7,200 in² x 1.3. Independent of this code.
    check("XM-4460 matches MCE's own stated 9,360 CFM",
          airsystem.size({"mode": "millModel", "millModel": "XM-4460"})["cfm"] == 9360,
          str(airsystem.size({"mode": "millModel", "millModel": "XM-4460"})["cfm"]))

    # 3. the air-swept pan raises it by exactly the factor
    swept = airsystem.size({"mode": "millModel", "millModel": "XM-4430", "airSwept": "1"})
    check("air-swept applies the factor",
          swept["cfm"] == round(by_model["cfm"] * airsystem.AIR_SWEPT_FACTOR),
          f'{swept["cfm"]} vs {by_model["cfm"]}')
    check("and the filter grows with it",
          next(l["name"] for l in swept["lines"] if "Bin Vent" in l["name"])
          != next(l["name"] for l in by_model["lines"] if "Bin Vent" in l["name"]))

    # 4. a cyclone means no filter, and the fan cannot be selected from one
    cyc = airsystem.size({"mode": "millModel", "millModel": "XM-4430",
                          "cleaner": "cyclone"})
    names = [l["name"] for l in cyc["lines"]]
    check("cyclone path has no filter", not any("Bin Vent" in n for n in names), str(names))
    check("cyclone path has a cyclone", any(n.startswith("Cyclone") for n in names), str(names))
    check("cyclone path is honest about the fan",
          any("Fan — size and price TBD" in n for n in names)
          and any("no standalone fan calculator" in w for w in cyc["warnings"]),
          str(names))

    # 5. opting items out actually removes them
    bare = airsystem.size({"mode": "millModel", "millModel": "XM-4430",
                           "include_airlock": "", "include_duct": "", "include_fan": ""})
    names = [l["name"] for l in bare["lines"]]
    check("airlock removed", not any("Airlock" in n for n in names), str(names))
    check("duct removed", not any("Ductwork" in n for n in names), str(names))
    check("fan removed", not any(n.startswith("Fan") for n in names), str(names))
    check("the filter is still there", any("Bin Vent" in n for n in names), str(names))

    # 6. THE important one: the chain and the quote builder must not diverge.
    #    Both size a filter, a fan and an airlock off a mill; if they ever disagree,
    #    a rep gets one answer on /tools and a different one on the quote.
    q = qfj.build(jb_request(), today=TODAY)
    quoted = {l["name"] for l in q["lines"]}
    chained = {l["name"] for l in
               airsystem.size({"mode": "millModel", "millModel": "XM-4430"})["lines"]}
    for kind in ("Bin Vent", "Fan —", "Rotary Airlock", "Ductwork"):
        a = next((n for n in quoted if n.startswith(kind)), None)
        b = next((n for n in chained if n.startswith(kind)), None)
        check(f"{kind} agrees between the builder and the chain", a == b, f"{a!r} vs {b!r}")

    # 7. a cooler drives the same chain — its own airflow requirement, not a mill's
    from calculators import cooler
    from calculators._data import CL_PELLETS
    cool_form = {"pellet": "p6", "tph": 20, "density": 40}
    direct = cooler.size(cool_form)
    chained = airsystem.size({"mode": "cooler", **cool_form})
    check("cooler exposes its airflow", direct.get("req_cfm"), str(direct.get("req_cfm")))
    check("the chain uses the cooler's own airflow",
          chained["cfm"] == direct["req_cfm"],
          f'{chained["cfm"]} vs {direct["req_cfm"]}')
    check("and sizes a filter off it",
          any("Bin Vent" in l["name"] for l in chained["lines"]),
          str([l["name"] for l in chained["lines"]]))
    # a meal cooler sizes on airflow rather than volume, and must still report one
    meal = next(x["id"] for x in CL_PELLETS if x.get("meal"))
    check("a meal cooler reports its airflow too",
          cooler.size({"pellet": meal, "tph": 20, "density": 40}).get("req_cfm"))

    # 8. the three air cleaners: a filter receiver is the same filter with a hopper,
    #    priced the same and sized the same, and it says so on the line
    bh = airsystem.size({"mode": "millModel", "millModel": "XM-4430"})
    rec = airsystem.size({"mode": "millModel", "millModel": "XM-4430",
                          "cleaner": "filter_receiver"})
    bh_line = next(l for l in bh["lines"] if l["name"].startswith("Bin Vent"))
    rec_line = next((l for l in rec["lines"] if l["name"].startswith("Filter Receiver")), None)
    check("a filter receiver is offered", rec_line, str([l["name"] for l in rec["lines"]]))
    if rec_line:
        check("the receiver is the same filter",
              rec_line["name"].split("MCE ")[-1] == bh_line["name"].split("MCE ")[-1],
              f'{rec_line["name"]} vs {bh_line["name"]}')
        check("and the same price — one data point supports one rate",
              rec_line["unitPrice"] == bh_line["unitPrice"])
        check("the receiver line says it has a hopper",
              "hopper" in rec_line["description"].lower())
        check("the baghouse line says it does not",
              "no hopper" in bh_line["description"].lower())
    check("the receiver still gets its matched fan",
          any(l["name"].startswith("Fan —") and "TBD" not in l["name"]
              for l in rec["lines"]))
    check("however the rep spells it",
          airsystem._cleaner("Filter Receiver") == airsystem._cleaner("receiver")
          == "filter_receiver")
    check("and an unknown cleaner falls back to the standard filter",
          airsystem._cleaner("") == airsystem._cleaner("dust sock") == "baghouse")

    # 9. combustible dust: the protection package appears as OPTIONS. What MCE has a
    #    price for is priced; what it does not, is not.
    for cleaner in ("baghouse", "filter_receiver", "cyclone"):
        hot = airsystem.size({"mode": "millModel", "millModel": "XM-4430",
                              "cleaner": cleaner, "combustible": "1",
                              "material": "pet food"})
        names = [o["name"] for o in hot["options"]]
        check(f"{cleaner}: isolation offered",
              any("NFPA 69 isolation" in n for n in names), str(names))
        check(f"{cleaner}: vent panel offered",
              any(n.startswith("Explosion vent panel") for n in names), str(names))
        check(f"{cleaner}: the adaptor section is its own item",
              any("adaptor section" in n for n in names), str(names))
        check(f"{cleaner}: burst switch is its own option",
              any("burst indicator switch" in n for n in names), str(names))
        check(f"{cleaner}: options are A-D in order",
              [o["ref"] for o in hot["options"]] == ["A", "B", "C", "D"],
              str([o["ref"] for o in hot["options"]]))
        by_name = {o["name"]: o for o in hot["options"]}
        panel = next(o for o in hot["options"]
                     if o["name"].startswith("Explosion vent panel"))
        switch = next(o for o in hot["options"] if "burst indicator" in o["name"])
        # the two MCE has a real quote for carry a price, at cost / the buy-out divisor
        _k, _m, sell, cost, *_rest = _vendor.vent_panel()
        check(f"{cleaner}: the panel is priced from the real quote",
              panel["unitPrice"] == round(sell, 2)
              and round(cost / _vendor.BUYOUT_DIVISOR, 2) == panel["unitPrice"],
              f'{panel["unitPrice"]} vs {sell}')
        sw_sell, sw_cost = _vendor.vent_sensor()[0], _vendor.vent_sensor()[1]
        check(f"{cleaner}: the switch is priced from the real quote",
              switch["unitPrice"] == round(sw_sell, 2), str(switch.get("unitPrice")))
        check(f"{cleaner}: the panel says the COUNT is not sized here",
              "PRICED PER PANEL" in panel["description"], panel["description"][:200])
        # and the two MCE cannot price, are not priced
        for unpriced in ("NFPA 69 isolation", "adaptor section"):
            o = next(x for x in hot["options"] if unpriced in x["name"])
            check(f"{cleaner}: {unpriced} is not priced",
                  o.get("needsPrice") and not o.get("unitPrice"), str(o.get("unitPrice")))
        check(f"{cleaner}: the vent names the vessel it goes on",
              any("MCE" in n for n in names if n.startswith("Explosion vent panel")),
              str(names))
        iso = next(o for o in hot["options"] if "isolation" in o["name"])
        lo, hi, _src = _vendor.certified_valve_range()
        check(f"{cleaner}: the isolation range is the one on file",
              money(lo) in iso["description"] and money(hi) in iso["description"],
              iso["description"])
        check(f"{cleaner}: the DHA is called out, not assumed",
              any("dust hazard analysis" in w for w in hot["warnings"]), str(hot["warnings"]))
        check(f"{cleaner}: no dust figures are invented for an untested product",
              any("No dust figures on record" in w for w in hot["warnings"]),
              str(hot["warnings"]))
        check(f"{cleaner}: the vendor basis is on the internal notes",
              any("High Tech Duct Werks" in w and "Nix" in w for w in hot["warnings"]))
        check(f"{cleaner}: the priced scope is unchanged by the hazard",
              [l["name"] for l in hot["lines"]]
              == [l["name"] for l in airsystem.size({"mode": "millModel",
                                                     "millModel": "XM-4430",
                                                     "cleaner": cleaner})["lines"]])

    # dust figures MCE has actually worked to come through as reference, with their
    # range intact where the vendor was given a range
    from calculators import nfpa
    woody = nfpa.design_basis("wood dust through a 1/4 screen")
    check("a tested Kst is offered as reference", "Kst 150" in woody["notes"], woody["notes"])
    check("and still asks for this product's own sample",
          "own sample" in woody["notes"], woody["notes"])
    check("a range stays a range", "Kst 130-150" in nfpa.design_basis("corn")["notes"],
          nfpa.design_basis("corn")["notes"])
    check("an untested material gets no Kst figure at all",
          "Kst 1" not in nfpa.design_basis("pet food")["notes"],
          nfpa.design_basis("pet food")["notes"])

    # saying nothing about the dust offers no protection package
    quiet = airsystem.size({"mode": "millModel", "millModel": "XM-4430"})
    check("no protection unless the rep said combustible", quiet["options"] == [],
          str(quiet["options"]))

    # indoors decides domed vs flameless, and flameless is the one with no price
    wants = {"1": ("FLAMELESS", True), "0": ("exterior wall", False),
             "": ("flameless panel instead", False)}
    for indoors, (want, unpriced) in wants.items():
        hot = airsystem.size({"mode": "millModel", "millModel": "XM-4430",
                              "combustible": "1", "indoors": indoors})
        vent = next(o for o in hot["options"] if o["name"].startswith("Explosion vent")
                    and "switch" not in o["name"] and "adaptor" not in o["name"])
        check(f"indoors={indoors!r} states the vent type", want in vent["description"],
              vent["description"][:160])
        check(f"indoors={indoors!r} prices the vent only where MCE has a price",
              bool(vent.get("needsPrice")) == unpriced, str(vent.get("unitPrice")))
    indoor = airsystem.size({"mode": "millModel", "millModel": "XM-4430",
                             "combustible": "1", "indoors": "1"})
    check("a flameless job says there is no price on file",
          any("no flameless price on file" in w for w in indoor["warnings"]),
          str(indoor["warnings"][-3:]))

    # 10. the quote builder agrees with the chain on all of it
    hot_job = jb_request()
    hot_job.combustible_dust = True
    hot_job.dust_collection = "filter_receiver"
    hq = qfj.build(hot_job, today=TODAY)
    check("the builder carries the same four protection options",
          [o["name"] for o in hq["options"]][:4]
          == [o["name"] for o in airsystem.size(
              {"mode": "millModel", "millModel": "XM-4430", "cleaner": "filter_receiver",
               "combustible": "1"})["options"]],
          str([o["name"] for o in hq["options"]]))
    check("and quotes the receiver, not the plenum-mount filter",
          any(l["name"].startswith("Filter Receiver") for l in hq["lines"]),
          str([l["name"] for l in hq["lines"]]))
    check("the dust classification reaches the design basis",
          any(r["parameter"] == "Dust classification" for r in hq["designBasis"]))
    check("and it prints as needing MCE input",
          next(r for r in hq["designBasis"]
               if r["parameter"] == "Dust classification")["needsInput"])
    cold = qfj.build(jb_request(), today=TODAY)
    check("a quiet job still offers the certified valve, as one option",
          sum(1 for o in cold["options"] if "certified rotary valve" in o["name"]) == 1,
          str([o["name"] for o in cold["options"]]))

    # 11. a basis that is not there is refused, not guessed
    for bad, why in (({"mode": "millModel", "millModel": "9999"}, "unknown model"),
                     ({"mode": "mill", "screenArea": 0}, "no screen area"),
                     ({"mode": "cfm", "cfm": 0}, "no CFM")):
        check(f"{why} is refused", airsystem.size(bad).get("error"), str(airsystem.size(bad)))

    if FAILS:
        print(f"{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — one airflow drives the chain, and it matches the quote builder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
