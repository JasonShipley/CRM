#!/usr/bin/env python3
"""The four process calculators MCE had no tool for.

These are not ports — there is no MCE original to diff them against — so the
checks here are of a different kind. Each one asserts either arithmetic that has
a closed form (screw flight volume, airlock displacement, a dryer mass balance),
a physical invariant that must hold whatever the inputs (energy balances close,
saltation rises with pipe diameter, Janssen never exceeds full head), or the
refusal the calculator exists to make (a constant-pitch screw under a long slot,
an exhaust below its dew point, a valve MCE cannot size).

Where a number came from a published correlation rather than from MCE, the test
says which, so nobody later mistakes it for a house standard.
"""
import math
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from calculators import airlock, dilute_phase, dryer, live_bottom

FAILS = []


def close(a, b, rel=1e-6, abs_=1e-9):
    """Results are rounded for the wire, so compare relatively."""
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(f"{name}{': ' + str(detail) if detail else ''}")


# ============================================================ rotary airlock ==
def test_airlock():
    # displacement is a closed form: volume/hour over rev/hour over fill
    r = airlock.size({"rate": 21000, "bulkDensity": 35, "rpm": 20, "fill": 0.75})
    want_ft3_h = 21000 / 35
    check("airlock volume", close(r["required"]["volumeFt3H"], want_ft3_h),
          r["required"]["volumeFt3H"])
    check("airlock displacement",
          close(r["required"]["ft3PerRev"], want_ft3_h / (20 * 60 * 0.75)),
          r["required"]["ft3PerRev"])

    # capacity is linear in speed and in fill — halve either and it needs twice
    half = airlock.size({"rate": 21000, "bulkDensity": 35, "rpm": 10, "fill": 0.75})
    check("airlock scales with speed",
          close(half["required"]["ft3PerRev"], 2 * r["required"]["ft3PerRev"]))

    # the valve picked has to actually cover the duty
    big = airlock.size({"tph": 2, "bulkDensity": 40})
    pick = next(c for c in big["candidates"] if c["number"] == big["selected"])
    check("airlock picks a valve that fits",
          pick["ft3PerRev"] >= big["required"]["ft3PerRev"], str(pick))
    check("and the smallest one that does",
          all(c["ft3PerRev"] >= pick["ft3PerRev"]
              for c in big["candidates"] if c["fits"]))

    # MCE's own standard valve has no published displacement, and that is said out
    # loud rather than papered over with an assumed pocket volume
    check("the FT-12 gap is stated",
          any("FT-12 cannot be checked" in w for w in big["warnings"]),
          str(big["warnings"]))
    check("and it is never silently selected", big["selected"] != "FT-12")

    # past what MCE has displacements for, it refuses rather than extrapolating
    huge = airlock.size({"tph": 60, "bulkDensity": 45})
    check("an oversize duty is refused, not extrapolated",
          huge["selected"] is None
          and any("No valve with a displacement on file" in w
                  for w in huge["warnings"]), str(huge["warnings"]))

    # pocket carry-back is geometry: empty pocket fraction times swept volume
    leak = airlock.carryover_cfm(0.70, 30, 0.75)
    check("carry-back is the empty pocket fraction",
          close(leak, 0.70 * 30 * 0.25), leak)
    check("full pockets carry no air back",
          abs(airlock.carryover_cfm(0.70, 30, 1.0)) < 1e-12)

    # combustible dust routes to the certified valves, and says the DHA decides
    comb = airlock.size({"tph": 2, "bulkDensity": 30, "combustible": "1"})
    check("combustible dust names a certified valve",
          any("certified" in n and "dust hazard analysis" in n
              for n in comb["notes"]), str(comb["notes"]))

    for bad in ({"tph": 0, "rate": 0}, {"tph": 4, "bulkDensity": 0},
                {"tph": 4, "fill": 0}):
        check(f"airlock refuses {bad}", "error" in airlock.size(bad))


# ======================================================= live bottom feeder ==
def test_live_bottom():
    # flight volume is an annulus times the pitch, exactly
    v = live_bottom.flight_volume_ft3(12, 2.5, 12)
    want = math.pi / 4 * ((12 / 12) ** 2 - (2.5 / 12) ** 2) * (12 / 12)
    check("flight volume", close(v, want), v)
    check("a solid shaft moves nothing",
          abs(live_bottom.flight_volume_ft3(12, 12, 12)) < 1e-12)

    base = {"tph": 20, "bulkDensity": 35, "screwOd": 12, "shaftOd": 2.5,
            "pitch": 12, "rpm": 20, "openingLength": 8, "openingWidth": 3,
            "headHeight": 20}
    r = live_bottom.size(dict(base, taper="none"))
    # capacity is linear in speed and in screw count
    fast = live_bottom.size(dict(base, taper="none", rpm=40))
    check("capacity scales with speed",
          close(fast["capacity"]["totalLbH"], 2 * r["capacity"]["totalLbH"]))
    two = live_bottom.size(dict(base, taper="none", screws=2))
    check("capacity scales with screw count",
          close(two["capacity"]["totalLbH"], 2 * r["capacity"]["totalLbH"]))

    # THE failure mode this calculator exists to catch
    check("a constant-pitch screw under a long slot is refused",
          any("fills at the back" in w for w in r["warnings"]), str(r["warnings"]))
    short = live_bottom.size(dict(base, taper="none", openingLength=0.8))
    check("but a short opening is fine on constant pitch",
          not any("fills at the back" in w for w in short["warnings"]),
          str(short["warnings"]))

    # linear draw wants the pitch to grow with the turn count — that is the
    # geometry, and it is also why one screw cannot do a very long slot
    check("the pitch ratio needed is the turn count",
          close(r["draw"]["pitchRatioNeeded"], r["draw"]["turnsUnderOpening"]),
          str(r["draw"]))
    thin = live_bottom.size(dict(base, taper="pitch", pitchRatio=1.2))
    check("an under-tapered screw is called out",
          any("back of the slot will do most of the work" in w
              for w in thin["warnings"]), str(thin["warnings"]))
    check("and the practical 2.5:1 ceiling is stated",
          any("tops out around" in n for n in thin["notes"]), str(thin["notes"]))

    # Janssen: the wall always carries some load, and never more than all of it
    bl = r["binLoad"]
    full = 35 * 20
    check("Janssen is below full head", 0 < bl["verticalStressPsf"] < full, str(bl))
    check("and reported against it", close(bl["fullHeadPsf"], full))
    deeper = live_bottom.size(dict(base, taper="none", headHeight=60))
    check("Janssen saturates with depth — 3x the head is not 3x the load",
          deeper["binLoad"]["verticalStressPsf"] < 3 * bl["verticalStressPsf"],
          f'{deeper["binLoad"]["verticalStressPsf"]} vs {bl["verticalStressPsf"]}')
    frictionless = live_bottom.janssen_vertical_psf(35, 20, 1.09, 0)
    check("with no wall friction the full head bears on the outlet",
          close(frictionless, full), frictionless)

    # the drive is NOT sized until MCE supplies CEMA's factors
    check("the drive is left unsized, with the reason",
          r["drive"] is None
          and any("CEMA" in w and "none of them on file" in w for w in r["warnings"]),
          str(r["warnings"]))
    with_cema = live_bottom.size(dict(base, taper="pitch", pitchRatio=8,
                                      screwLength=10, cemaFd=55, cemaFb=1.0,
                                      cemaFf=1.0, cemaFm=0.8, cemaFp=1.0))
    check("and comes back when they are given",
          with_cema["drive"] and with_cema["drive"]["hpTotal"] > 0,
          str(with_cema["drive"]))
    check("but says CEMA does not cover the bin load",
          any("CEMA does not cover" in n for n in with_cema["notes"]),
          str(with_cema["notes"]))

    for bad in ({"tph": 0}, {"tph": 20, "screwOd": 6, "shaftOd": 6},
                {"tph": 20, "loading": 0}):
        check(f"live bottom refuses {bad}", "error" in live_bottom.size(bad))


# ===================================================== dilute phase conveying ==
def test_dilute_phase():
    r = dilute_phase.size({"tph": 10, "material": "meal", "loading": 8})
    ln, air, pr = r["line"], r["air"], r["pressure"]

    # the chosen line is the smallest that stays under the loading ceiling
    ok = [t for t in r["trials"] if t["ok"]]
    check("the smallest feasible line is picked", ok[0]["nominal"] == ln["nominal"],
          f'{ok[0]["nominal"]} vs {ln["nominal"]}')
    check("and it is inside the loading ceiling", air["loading"] <= 8 + 1e-9,
          air["loading"])

    # mass balance: solids over air really is the loading
    check("loading is solids over air",
          close(air["loading"], 20000 / air["lbPerHour"], rel=1e-4),
          f'{air["loading"]} vs {20000 / air["lbPerHour"]}')

    # the line runs above saltation by the margin, which is the whole design rule
    check("velocity is the saltation margin",
          close(ln["velocityFps"], ln["saltationFps"] * ln["margin"], rel=1e-4),
          str(ln))

    # Rizk at a FIXED loading: saltation goes as the square root of the diameter,
    # because the Froude number does not depend on it. On the selection table the
    # loading falls as the line grows, which pulls the other way — so the invariant
    # is asserted against the correlation itself, not against the table.
    fixed = [(d, dilute_phase.saltation_velocity(d, 0.04, 75, 0.1, 8.0))
             for d in (2.067, 3.068, 4.026, 6.065, 10.02)]
    check("saltation rises with the root of diameter (Rizk)",
          all(b[1] > a[1] for a, b in zip(fixed, fixed[1:])), str(fixed))
    check("and goes as its square root",
          close(fixed[-1][1] / fixed[0][1],
                math.sqrt(fixed[-1][0] / fixed[0][0]), rel=1e-6),
          f"{fixed[-1][1] / fixed[0][1]} vs "
          f"{math.sqrt(fixed[-1][0] / fixed[0][0])}")
    # on the table the loading drops as the line grows, which is the real trade
    loadings = [(t["nominal"], t["loading"]) for t in r["trials"]]
    check("a bigger line runs leaner",
          all(b[1] < a[1] for a, b in zip(loadings, loadings[1:])),
          str(loadings[:4]))
    bigger = [t for t in r["trials"] if t["nominal"] > ln["nominal"]]
    check("a bigger line needs more air",
          all(t["scfm"] > air["scfm"] for t in bigger[:3]),
          str([(t["nominal"], t["scfm"]) for t in bigger[:3]]))

    # the five pressure terms have to add up to the total
    parts = (pr["gasPsi"] + pr["solidsPsi"] + pr["accelPsi"] + pr["liftPsi"]
             + pr["bendsPsi"])
    check("pressure terms sum to the total", close(parts, pr["totalPsi"], rel=1e-5),
          f'{parts} vs {pr["totalPsi"]}')
    check("bends split into gas and solids",
          close(pr["bendsGasPsi"] + pr["bendsSolidsPsi"], pr["bendsPsi"]))
    flat = dilute_phase.size({"tph": 10, "material": "meal", "loading": 8,
                              "vertical": 0})
    check("no rise means no lift term", abs(flat["pressure"]["liftPsi"]) < 1e-12)
    straight = dilute_phase.size({"tph": 10, "material": "meal", "loading": 8,
                                  "bends": 0})
    check("no bends means no bend term", abs(straight["pressure"]["bendsPsi"]) < 1e-12)
    check("and removing bends lowers the total",
          straight["pressure"]["totalPsi"] < pr["totalPsi"])

    # Colebrook must land in the physical band for turbulent commercial steel
    check("Darcy friction factor is physical", 0.008 < ln["darcyF"] < 0.08,
          ln["darcyF"])
    check("and the flow is turbulent", ln["reynolds"] > 4000, ln["reynolds"])

    # a line it cannot do is refused rather than fudged
    check("an impossible duty is refused",
          "error" in dilute_phase.size({"tph": 400, "loading": 1.0}))
    # a margin below the safe floor is called out
    risky = dilute_phase.size({"tph": 10, "velocityMargin": 1.05})
    check("an unsafe velocity margin is called out",
          any("plug on the first upset" in w for w in risky["warnings"]),
          str(risky["warnings"]))
    # the accuracy caveat is on every run, because it always applies
    check("the ±25% caveat is always stated",
          any("±25%" in n for n in r["notes"]), str(r["notes"]))
    check("and the correlations are named", "Rizk" in str(r["sources"]))


# ================================================================== dryer ==
def test_dryer():
    r = dryer.size({"tph": 10, "mcin": 45, "mcout": 12})
    m, h, g = r["mass"], r["heat"], r["gas"]

    # mass balance closes, on a wet basis
    check("dry solids", close(m["dry"], 20000 * 0.55), m["dry"])
    check("product out", close(m["productOut"], m["dry"] / 0.88), m["productOut"])
    check("water evaporated closes",
          close(m["evaporated"], m["feed"] - m["productOut"]), m["evaporated"])
    check("and the solids are conserved",
          close(m["productOut"] * (1 - 0.12), m["dry"]))

    # the five heat terms add up to the net, and the gross carries the shell loss
    net = h["heatWater"] + h["evaporate"] + h["superheat"] + h["product"]
    check("heat terms sum to net", close(net, h["net"]), f'{net} vs {h["net"]}')
    check("gross carries the shell loss", close(h["gross"] * 0.95, h["net"]),
          f'{h["gross"]} vs {h["net"]}')
    check("shell loss is the difference",
          close(h["gross"] - h["net"], h["shellLoss"]))

    # the gas carries exactly the gross demand across its temperature drop
    from calculators.rotary_cooler import PSY
    cpg = PSY.cp(g["humidityIn"])
    check("gas mass carries the gross demand",
          close(g["massFlow"] * cpg * (900 - 250), h["gross"], rel=1e-5),
          g["massFlow"])
    # and picks up exactly the water evaporated
    check("exhaust humidity is inlet plus what was evaporated",
          close(g["humidityOut"] - g["humidityIn"],
                m["evaporated"] / g["massFlow"], rel=1e-5),
          g["humidityOut"])

    # the dew point check is the one that stops a dryer that rains inside
    check("dew margin is exhaust minus dew point",
          close(g["dewMargin"], 250 - g["dewPoint"], rel=1e-5), str(g))
    wet = dryer.size({"tph": 10, "mcin": 45, "mcout": 12, "gasOut": 120})
    check("an exhaust near its dew point is refused",
          any("dew point" in w for w in wet["warnings"]), str(wet["warnings"]))

    # fuel: input over heating value, and the BTU/lb of water sanity figure
    fu = r["fuel"]
    check("fuel input carries the burner efficiency",
          close(fu["input"] * fu["efficiency"], h["gross"]), str(fu))
    check("fuel rate is input over heating value",
          close(fu["rate"], fu["input"] / fu["heatingValue"]), str(fu))
    check("BTU per lb of water is in the sane band",
          1200 < fu["btuPerLbWater"] < 1800, fu["btuPerLbWater"])

    # co-current cannot make a product hotter than the gas it leaves with
    co = dryer.size({"tph": 10, "mcin": 45, "mcout": 12, "flow": "co",
                     "tout": 240, "gasOut": 250})
    check("co-current is held to its exhaust",
          any("cannot get hotter than the exhaust" in w for w in co["warnings"]),
          str(co["warnings"]))

    # more water to remove is strictly more heat
    wetter = dryer.size({"tph": 10, "mcin": 55, "mcout": 12})
    check("a wetter feed costs more heat", wetter["heat"]["gross"] > h["gross"])
    check("and evaporates more water",
          wetter["mass"]["evaporated"] > m["evaporated"])

    # a hot inlet on an organic product is a combustion question, not a drying one
    hot = dryer.size({"tph": 10, "mcin": 45, "mcout": 12, "gasIn": 1400})
    check("a very hot inlet raises the fire question",
          any("fire risk" in w for w in hot["warnings"]), str(hot["warnings"]))

    for bad in ({"tph": 0}, {"tph": 10, "mcin": 12, "mcout": 45},
                {"tph": 10, "gasIn": 200, "gasOut": 250}):
        check(f"dryer refuses {bad}", "error" in dryer.size(bad))


def main():
    for fn in (test_airlock, test_live_bottom, test_dilute_phase, test_dryer):
        print("  " + fn.__name__)
        fn()
    if FAILS:
        print(f"\n{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("\nOK — the four process calculators hold their balances, their "
          "correlations behave, and each refuses what it cannot size.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
