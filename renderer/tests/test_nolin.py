#!/usr/bin/env python3
"""Nolin's catalog tables, checked the way the printed page reads.

Every figure in _nolin.py was transcribed from a page image, so the risk here is
a typo, not a formula. These checks are the shape the catalog has: a heavier
gauge costs more than a lighter one at the same size, a bigger duct costs more
than a smaller one at the same gauge, and a 90° elbow costs more than a 60, a 45
and a 30. A fat-fingered digit breaks one of them.

Where the catalog is genuinely not monotonic — the clamp band table really does
print 8" cheaper than 7" — the table is excluded by name and the exception is
written down, so nobody "fixes" it back to a wrong number later.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from calculators import _nolin as n
from calculators import _vendor

fails = []


def bad(msg):
    fails.append(msg)


# --- heavier gauge costs more, at every size -----------------------------------
for name, table in (("duct stick", n.DUCT_STICK), ("spouting", n.SPOUTING_PER_FT),
                    ("galvanized spouting", n.GALVANIZED_PER_FT),
                    ("304 spouting", n.STAINLESS_304_PER_FT)):
    for dia, row in table.items():
        printed = [(g, row[g]) for g in n.GAUGES if g in row]
        for (g1, p1), (g2, p2) in zip(printed, printed[1:]):
            if p2 <= p1:
                bad(f'{name} {dia}": {g2} ga (${p2}) is not above {g1} ga (${p1})')

# --- a bigger size costs more, at every gauge ----------------------------------
# 7 in is an odd size and Nolin charges a premium for it: 7" 12 ga spouting is
# $15.69 against $15.29 for 8", and a 7" clamp band is $14.99 against $10.99 for
# an 8". Both are the page, so 7 in sits out of the size-ordering check.
ODD_SIZE_PREMIUM = {7}
for name, table in (("duct stick", n.DUCT_STICK), ("spouting", n.SPOUTING_PER_FT)):
    for gauge in n.GAUGES:
        sizes = sorted(d for d, row in table.items()
                       if gauge in row and d not in ODD_SIZE_PREMIUM)
        for a, b in zip(sizes, sizes[1:]):
            if table[b][gauge] < table[a][gauge]:
                bad(f'{name} {gauge} ga: {b}" (${table[b][gauge]}) is below '
                    f'{a}" (${table[a][gauge]})')

# --- elbows: sharper angle costs more, and gauge and size still order ----------
for dia, angles in n.ELBOW.items():
    for gauge in ("14", "12", "10", "7"):
        series = [(a, angles[a][gauge]) for a in ("90", "60", "45", "30")
                  if gauge in angles.get(a, {})]
        for (a1, p1), (a2, p2) in zip(series, series[1:]):
            if p2 > p1:
                bad(f'elbow {dia}" {gauge} ga: {a2}° (${p2}) is above {a1}° (${p1})')
    for angle, prices in angles.items():
        printed = [(g, prices[g]) for g in ("14", "12", "10", "7") if g in prices]
        for (g1, p1), (g2, p2) in zip(printed, printed[1:]):
            if p2 <= p1:
                bad(f'elbow {dia}" {angle}°: {g2} ga (${p2}) not above {g1} ga (${p1})')

for angle in ("90", "60", "45", "30"):
    for gauge in ("14", "12", "10", "7"):
        sizes = [d for d in sorted(n.ELBOW) if gauge in n.ELBOW[d].get(angle, {})]
        for a, b in zip(sizes, sizes[1:]):
            pa, pb = n.ELBOW[a][angle][gauge], n.ELBOW[b][angle][gauge]
            if pb < pa:
                bad(f'elbow {angle}° {gauge} ga: {b}" (${pb}) is below {a}" (${pa})')

# Replacement backs follow the same angle order as the elbows they fit.
for name, table in (("sweep back 10 ga", n.SWEEP_BACK_10GA),
                    ("sweep back 7 ga AR", n.SWEEP_BACK_7GA_AR)):
    for dia, row in table.items():
        for i, (p1, p2) in enumerate(zip(row, row[1:])):
            if p2 > p1:
                bad(f'{name} {dia}": angles out of order {row}')
    sizes = sorted(table)
    for a, b in zip(sizes, sizes[1:]):
        for col, (pa, pb) in enumerate(zip(table[a], table[b])):
            if pb < pa:
                bad(f'{name} col {col}: {b}" (${pb}) is below {a}" (${pa})')
for dia in n.SWEEP_BACK_10GA:
    for angle in ("90", "60", "45", "30"):
        ten = n.sweep_back(dia, angle)[0]
        seven = n.sweep_back(dia, angle, grade="7ga")[0]
        if seven <= ten:
            bad(f'7 ga AR back at {dia}" {angle}° (${seven}) should be above '
                f"10 ga (${ten})")

# Sweep elbows are one gauge, so only the angle order applies.
for dia, row in n.SWEEP_ELBOW.items():
    series = [row[a] for a in ("90", "60", "45", "30")]
    for p1, p2 in zip(series, series[1:]):
        if p2 > p1:
            bad(f'sweep elbow {dia}": angles out of order {series}')

# --- banded tables: bigger never costs less ------------------------------------
# CLAMP_BAND is left out on purpose: the catalog prints 7" at $14.99 and 8" at
# $10.99, and 9" above 10". That is the page, not a typo.
for name, table in (("flange ring", n.FLANGE_RING), ("hanger strap", n.HANGER_STRAP),
                    ("blast gate", n.BLAST_GATE), ("slim blast gate", n.SLIM_BLAST_GATE),
                    ("round damper", n.ROUND_DAMPER),
                    ("compression coupling", n.COMPRESSION_COUPLING),
                    ("45 offset branch", n.BRANCH_45_OFFSET),
                    ("45 Y branch", n.BRANCH_45_Y),
                    ("45 three way branch", n.BRANCH_45_THREE_WAY),
                    ("90 T branch", n.BRANCH_90_T),
                    ("hat rain hood", n.HAT_RAIN_HOOD),
                    ("shielded rain hood", n.SHIELDED_RAIN_HOOD),
                    ("bird screen", n.BIRD_SCREEN_ROUND),
                    ("priming", n.PRIMING_PER_FT)):
    sizes = sorted(table)
    for a, b in zip(sizes, sizes[1:]):
        for col, (pa, pb) in enumerate(zip(table[a], table[b])):
            if pb < pa:
                bad(f'{name} col {col}: {b}" (${pb}) is below {a}" (${pa})')

# The odd-size premium is real and stays recorded, in both tables that show it.
assert n.CLAMP_BAND[8][0] < n.CLAMP_BAND[7][0], \
    'the catalog prints 8" clamp bands cheaper than 7" — do not "correct" this'
assert n.SPOUTING_PER_FT[8]["12"] < n.SPOUTING_PER_FT[7]["12"], \
    'the catalog prints 8" 12 ga spouting cheaper than 7" — do not "correct" this'

# --- material adders are measured, not invented --------------------------------
for key in ("galvanized", "stainless"):
    a = n.MATERIAL_ADDER[key]
    if a["samples"] < 10:
        bad(f'{key} adder rests on only {a["samples"]} overlapping cells')
    if not a["low"] <= a["factor"] <= a["high"]:
        bad(f'{key} adder {a["factor"]} is outside its own range')
    if not a["source"].startswith(n.SOURCE):
        bad(f'{key} adder does not cite the catalog')
if not 1.0 < n.MATERIAL_ADDER["galvanized"]["factor"] < n.MATERIAL_ADDER["stainless"]["factor"]:
    bad("galvanized should sit between carbon and 304")

# --- lookups behave -------------------------------------------------------------
price, dia, gauge = n.stick(20)
assert (price, dia, gauge) == (639.0, 20, "14"), (price, dia, gauge)
assert n.stick(25)[1] == 26, "an unprinted size falls up to the next one printed"
assert n.stick(200) is None, "past the end of the table is None, not a guess"
assert n.elbow(20)[0] == 709.0 and n.elbow(20)[3] == 48
assert n.elbow(20, "30")[0] == 349.0
assert n.reducer(16, 12)[0] == 159.0
assert n.transition(14, 12)[0] == 109.0

# --- the package MCE actually quotes --------------------------------------------
pkg = _vendor.duct_package(20, run_ft=60, elbows=4)
names = " | ".join(i["name"] for i in pkg["items"])
for want in ("10 ft flanged length", "hanger strap", "90° segmented elbow",
             "bird screen", "rain and snow hood"):
    if want not in names:
        bad(f"the standard duct package is missing the {want}: {names}")
if pkg["items"][0]["quantity"] != 6:
    bad(f'60 ft should be 6 × 10 ft lengths, got {pkg["items"][0]["quantity"]}')
# 55 ft still buys six lengths — you cannot order two thirds of a stick
if _vendor.duct_package(20, run_ft=55, elbows=0)["items"][0]["quantity"] != 6:
    bad("a part length has to round up to a whole stick")
if pkg["total"] <= pkg["listTotal"]:
    bad("MCE's price has to sit above Nolin's list")
if abs(pkg["total"] - pkg["listTotal"] / _vendor.BUYOUT_DIVISOR) > 0.02:
    bad("the duct package is not at MCE's buy-out divisor")

# Under 16 in the catalog sends you to spouting, and the package follows it.
small = _vendor.duct_package(8, run_ft=60, elbows=2)
if not small["spouting"] or "spouting" not in small["items"][0]["name"]:
    bad("an 8 in run should be quoted as spouting, per the ductwork page's own note")
if not any("primer" in i["name"] for i in small["items"]):
    bad("plain-end spouting has to carry its priming charge")
if not any("clamp band" in i["name"] for i in small["items"]):
    bad("plain-end spouting has to carry its joints")
if not any("under the flanged ductwork table" in w for w in small["warnings"]):
    bad("the quote has to say why a small run is spouting")

# --- MCE's service rule: 14 ga, heavier only on abrasive, sweeps only on request --
fines = _vendor.duct_package(20, run_ft=60, elbows=4, service="fines")
product = _vendor.duct_package(20, run_ft=60, elbows=4, service="product")
abrasive = _vendor.duct_package(20, run_ft=60, elbows=4, service="abrasive")
asked = _vendor.duct_package(20, run_ft=60, elbows=4, service="abrasive",
                             sweep_elbows=True)

for name, pkg in (("fines", fines), ("product", product)):
    if pkg["gauge"] != _vendor.DUCT_STANDARD_GAUGE:
        bad(f'{name} should be {_vendor.DUCT_STANDARD_GAUGE} ga, got {pkg["gauge"]}')
if fines["total"] != product["total"]:
    bad("fines and product price the same — only abrasive moves the gauge")
if abrasive["gauge"] != _vendor.DUCT_ABRASIVE_GAUGE:
    bad(f'abrasive should be {_vendor.DUCT_ABRASIVE_GAUGE} ga, got {abrasive["gauge"]}')
if abrasive["total"] <= fines["total"]:
    bad("a heavier gauge has to cost more")
if not any("has not named the gauge" in n for n in abrasive["notes"]):
    bad("the one number MCE did not set has to stay flagged")

# Sweep elbows are NEVER automatic. They are rare and expensive, and a quote that
# carries them without anybody deciding to loses on price for no reason.
for name, pkg in (("fines", fines), ("product", product), ("abrasive", abrasive)):
    if pkg["sweepElbows"]:
        bad(f"{name} quoted sweep elbows without being asked to")
    if any("sweep elbow" in i["name"] for i in pkg["items"]):
        bad(f"{name} has a sweep elbow on the bill of material")
    if not any("segmented elbow" in i["name"] for i in pkg["items"]):
        bad(f"{name} should carry segmented elbows")

# The only thing the calculator does on its own is ASK — and only on abrasive,
# which is the one service where the answer might be yes.
if fines["questions"] or product["questions"]:
    bad(f"nothing to ask on a fines or product line: "
        f'{fines["questions"] + product["questions"]}')
if len(abrasive["questions"]) != 1:
    bad(f'abrasive should raise exactly one question: {abrasive["questions"]}')
q = abrasive["questions"][0]
if "?" not in q:
    bad(f"it has to read as a question: {q}")
for want in ("right nearly every time", "Say yes only"):
    if want not in q:
        bad(f'the question has to say sweeps are the rare answer: {q}')
if f'${abrasive["sweepPremium"]:,.0f}' not in q:
    bad(f"the question has to carry what the answer costs: {q}")
if abrasive["sweepPremium"] is None or abrasive["sweepPremium"] <= 0:
    bad(f'the premium has to be a real number: {abrasive["sweepPremium"]}')

# asked for explicitly, they are quoted, priced and explained
if not asked["sweepElbows"] or asked["questions"]:
    bad("an explicit yes quotes them and stops asking")
if not any("removable back sweep elbow" in i["name"] for i in asked["items"]):
    bad("an explicit yes has to put sweeps on the bill of material")
if asked["total"] <= abrasive["total"]:
    bad("sweeps cost more than segmented")
if not any("as asked for" in n for n in asked["notes"]):
    bad("the quote should say the sweeps were asked for, not assumed")
if abs((asked["total"] - abrasive["total"]) - abrasive["sweepPremium"]) > 1:
    bad(f'the quoted premium has to be what the question said: '
        f'{asked["total"] - abrasive["total"]} vs {abrasive["sweepPremium"]}')

# a line with no elbows has nothing to ask about
no_elbows = _vendor.duct_package(20, run_ft=60, elbows=0, service="abrasive")
if no_elbows["questions"]:
    bad(f'no elbows, nothing to ask: {no_elbows["questions"]}')

# the replacement back is the wear part and is quotable as a spare
spare = _vendor.duct_package(20, run_ft=60, elbows=4, service="abrasive",
                             sweep_elbows=True, spare_backs=2)
backs = [i for i in spare["items"] if "replacement back" in i["name"]]
if len(backs) != 1 or backs[0]["quantity"] != 2:
    bad(f"spare backs should quote as one line of two: {backs}")
if backs[0]["listUnit"] >= next(i["listUnit"] for i in spare["items"]
                                if "sweep elbow" in i["name"]):
    bad("a replacement back costs less than the whole elbow")

# an unknown service falls back to the standard rather than erroring
if _vendor.duct_package(20, run_ft=10, service="nonsense")["gauge"] != "14":
    bad("an unknown service falls back to MCE's standard")

# A material change is a flagged budget number, never a silent one.
ss = _vendor.duct_package(20, run_ft=60, elbows=4, material="stainless")
if ss["total"] <= pkg["total"]:
    bad("304 has to cost more than carbon")
if not any("budgetary" in w for w in ss["warnings"]):
    bad("a stainless duct price has to say it is budgetary, not a catalog price")

if fails:
    print(f"nolin catalog: {len(fails)} problem(s)")
    for f in fails[:40]:
        print("  " + f)
    sys.exit(1)
print(f"OK — Nolin's tables read like the page ({len(n.DUCT_STICK)} duct sizes, "
      f"{len(n.ELBOW)} elbow sizes, {len(n.SPOUTING_PER_FT)} spouting sizes), "
      "and the standard package prices itself.")
