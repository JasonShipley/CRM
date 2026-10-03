#!/usr/bin/env python3
"""The cooler heat balance port, against the workbook's own reference case.

The other ports are diffed against their originals by running the original's own
JavaScript (test_ports.py). This one has no JavaScript — the original is
MCE_Cooler_Heat_Balance.xlsx — so the workbook's Ozark Organics case stands in
for it: every cell the workbook computes for that case is asserted here to the
precision the workbook displays.

The one input that is pinned rather than computed is the air density. The
workbook's air mass flow implies 0.0720346 lb/ft³ where the barometric formula
gives 0.07182 at the same 1,150 ft and 70 °F — see cooler_heat.KNOWN_DIVERGENCE.
Pinning it isolates the model from that one unexplained cell, so a failure here
means the model moved, not the density.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from decimal import ROUND_HALF_UP, Decimal

from calculators import cooler_heat

fails = []


def _round(value, places):
    """Excel rounds half away from zero; Python's round() rounds half to even."""
    q = Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return float(q)


def check(name, got, want, places=0):
    """The workbook displays rounded; compare at the displayed precision."""
    ok = _round(got, places) == _round(want, places)
    if not ok:
        fails.append(f"{name}: workbook {want}, port {got}")
    return ok


# The workbook's reference case: Ozark Organics soy cake, 2026-09.
OZARK = {"tph": 12.0, "cp": 0.50, "bulkDensity": 35, "tProductIn": 240,
         "approach": 15, "moistIn": 7.0, "moistOut": 5.0, "hfg": 1010,
         "airDryBulb": 70, "airRh": 50, "elevation": 1150, "acfm": 8200,
         "effSizing": 0.92, "coolerType": "bed", "bedArea": 67.8,
         "bedDepth": 30, "pieceSize": 1.50, "calFactor": 1.00,
         "airDensity": 0.0720346}

r = cooler_heat.size(OZARK)
assert not r.get("error"), r.get("error")
b, t, psy = r["balance"], r["transfer"], r["psychrometrics"]

# --- sections 1-2, the streams -------------------------------------------------
check("product mass flow", b["productMassFlow"], 24000)
check("dry solids", b["drySolids"], 22320)
check("water in", b["waterIn"], 1680)
check("water out", b["waterOut"], 1175)
check("water flashed", b["waterFlashed"], 505)

# --- section 4, the energy balance ---------------------------------------------
check("target discharge", b["targetDischarge"], 85)
check("sensible heat", b["qSensible"], 1_860_000)
check("moisture flash heat", b["qLatent"], 510_316)
check("heat the air carries", b["qAir"], 1_349_684)
check("product capacity rate", b["cProduct"], 12_000)
check("air mass flow", b["airMassFlow"], 35_441)
check("air capacity rate", b["cAir"], 8_683)
check("BTU/h per °F per CFM", b["btuPerCfmPerF"], 1.06, 2)
check("CFM per ton", b["cfmPerTon"], 683)
check("atmospheric pressure", b["atmosphericKpa"], 97.18, 2)
check("air out at full load", b["airOutFullLoad"], 225)
check("counterflow floor", b["floorCounterflow"], 74)
check("co-current floor", b["floorCoCurrent"], 144)
check("minimum airflow", b["minimumAcfm"], 8_150)

# --- section 5, the transfer rate ----------------------------------------------
check("contact volume", t["volume"], 170)
check("holdup", t["holdup"], 5_933)
check("retention", t["retentionMin"], 14.8, 1)
check("air flow section", t["airSection"], 67.8, 1)
check("mass velocity G", t["massVelocity"], 523)
check("superficial velocity", t["velocity"], 121)
check("Uv correlation", t["uvCorrelation"], 270.8, 1)
check("Uv used", t["uvUsed"], 270.8, 1)
check("UA", t["ua"], 45_894)
check("Cmin", t["cMin"], 8_683)
check("capacity ratio", t["cr"], 0.724, 3)
check("NTU", t["ntu"], 5.29, 2)
check("effectiveness", t["effectiveness"], 0.92, 2)
check("PREDICTED DISCHARGE", t["discharge"], 84)
check("discharge above inlet air", t["aboveAir"], 14)
check("air outlet at effectiveness", t["airOut"], 227)
assert t["meets"], "the workbook's verdict on this case is MEETS the target approach"

# --- psychrometrics -------------------------------------------------------------
check("inlet wet bulb", psy["wetBulb"], 58)
check("inlet humidity ratio", psy["humidityIn"], 0.0081, 4)
check("outlet humidity ratio", psy["humidityOut"], 0.0224, 4)
check("saturation humidity at outlet", psy["saturationOut"], 9.0, 1)
assert psy["exhaustOk"], "the workbook's exhaust moisture check on this case is OK"

# --- the stream table -----------------------------------------------------------
streams = {s["item"]: s for s in r["streams"]}
assert streams["1"]["dry"] == "35,441", streams["1"]["dry"]
assert streams["1"]["water"] == "288", streams["1"]["water"]
assert streams["3"]["water"] == "793", streams["3"]["water"]
assert streams["A"]["dry"] == "22,320", streams["A"]["dry"]
assert streams["B"]["water"] == "1,175", streams["B"]["water"]
assert streams["C"]["water"] == "505", streams["C"]["water"]

# --- the drum, against the method sheet's own 9 x 30 figure ---------------------
# "9 x 30 drum at 22,300 CFM (350 ft/min): predicted ~90 degF with the
#  uncalibrated dryer correlation (Uv ~ 7.7)".
drum = dict(OZARK, coolerType="drum_counter", acfm=22300, drumDia=9.0,
            drumLength=30.0, drumFill=15)
d = cooler_heat.size(drum)
assert not d.get("error"), d.get("error")
dt = d["transfer"]
check("drum superficial velocity", dt["velocity"], 350, -1)
if not 7.0 <= dt["uvCorrelation"] <= 8.0:
    fails.append(f"drum Uv: method sheet ~7.7, port {dt['uvCorrelation']}")
if not 88 <= dt["discharge"] <= 95:
    fails.append(f"drum discharge: method sheet ~90 °F, port {dt['discharge']}")
# The coefficient acts on the whole drum, not the filled fraction — the holdup is
# what the fill sets. Taking the filled volume puts this drum at ~171 °F.
check("drum contact volume", dt["volume"], 1908.5, 1)
check("drum material volume", dt["materialVolume"], 286.3, 1)

# --- co-current cannot beat the common temperature ------------------------------
co = cooler_heat.size(dict(OZARK, coolerType="drum_co", acfm=22300, drumDia=9.0,
                           drumLength=30.0, drumFill=15))
assert co["transfer"]["discharge"] >= co["balance"]["floorCoCurrent"] - 0.5, (
    "co-current discharge cannot go below the common temperature")
assert any("common temperature" in w for w in co["warnings"]), \
    "a co-current run has to say why it cannot reach a counterflow approach"

# --- calibration round-trips ----------------------------------------------------
# Feed the port its own prediction back as a measurement: it must return the
# coefficient it used and a calibration factor of 1.
back = cooler_heat.size(dict(OZARK, measuredDischarge=t["discharge"]))["calibration"]
assert back is not None, "a measured discharge has to produce a calibration block"
check("calibration returns the coefficient", back["uv"], t["uvUsed"], 0)
check("calibration factor round-trips to 1", back["factor"], 1.0, 2)

# A measured discharge that no effectiveness explains is refused, not fitted.
bad = cooler_heat.size(dict(OZARK, measuredDischarge=40))["calibration"]
assert bad["uv"] is None and "outside" in bad["note"], bad

# --- guards ----------------------------------------------------------------------
assert "error" in cooler_heat.size(dict(OZARK, tph=0)), "zero rate has to be refused"
assert "error" in cooler_heat.size(dict(OZARK, tProductIn=60)), \
    "product below the air has to be refused"
assert "error" in cooler_heat.size(dict(OZARK, moistOut=9)), \
    "a cooler does not add water"

# A short airflow is called out rather than quietly sized around.
short = cooler_heat.size(dict(OZARK, acfm=5000))
assert any("below the" in w for w in short["warnings"]), short["warnings"]
assert "short" in short["outputs"][-1]["value"], short["outputs"][-1]

# Over the bed velocity cap.
fast = cooler_heat.size(dict(OZARK, acfm=12000))
assert any("bed cap" in w for w in fast["warnings"]), fast["warnings"]

# A blank override is a blank, not a zero.
assert cooler_heat.size(dict(OZARK, uvOverride="", calFactor=""))["transfer"]["uvUsed"] \
    == t["uvUsed"], "blank override and blank calibration must fall back, not zero"

# The 4×8 soy tumble cooler field point: what the model says about it is
# recorded beside it, so a change to the model shows up here.
fd = cooler_heat.FIELD_DATA["tumble_4x8_soy"]
field = {"coolerType": "drum_counter", "tph": fd["tph"],
         "tProductIn": fd["t_product_in_f"], "cp": 0.45, "bulkDensity": 38,
         "moistIn": 7, "moistOut": 6, "airDryBulb": 70, "airRh": 50,
         "elevation": 1000, "drumDia": 4, "drumLength": 8, "drumFill": 15,
         "calFactor": 1.0}   # what the uncalibrated correlation says
says = fd["model_says"]
for acfm, want in says["discharge_f_at_acfm"].items():
    got = cooler_heat.size(dict(field, acfm=acfm))
    if round(got["transfer"]["discharge"]) != want:
        fails.append("field 4x8 @ %d ACFM: %s vs recorded %s"
                     % (acfm, got["transfer"]["discharge"], want))
got = cooler_heat.size(dict(field, acfm=2500))
if round(got["balance"]["minimumAcfm"]) != says["min_airflow_acfm"]:
    fails.append("field 4x8 min airflow: %s vs recorded %s"
                 % (got["balance"]["minimumAcfm"], says["min_airflow_acfm"]))
cal = cooler_heat.size(dict(field, acfm=2500, measuredDischarge=100))["calibration"]
if round(cal["factor"], 2) != says["cal_factor_if_discharge_100f_at_2500"]:
    fails.append("field 4x8 cal factor: %s" % cal["factor"])

# Insta-Pro ratings: the implied factors are recorded, and the two sizes must
# keep agreeing — that agreement is the finding.
ip = cooler_heat.FIELD_DATA["instapro_ratings"]
for cfm_ton, by_ap in ip["implied_cal_factor"].items():
    for ap, pair in by_ap.items():
        for model, want in zip(("900", "700"), pair):
            m = ip["models"][model]
            tph = m["max_lb_h"] / 2000
            r = cooler_heat.size({
                "coolerType": "drum_counter", "tph": tph, "tProductIn": 250,
                "cp": 0.45, "bulkDensity": 38, "moistIn": 7, "moistOut": 6,
                "airDryBulb": 100, "airRh": 40, "elevation": 1000,
                "drumDia": m["dia_in"] / 12, "drumLength": m["length_in"] / 12,
                "drumFill": 15, "acfm": cfm_ton * tph, "approach": ap,
                "measuredDischarge": 100 + ap})
            if round(r["calibration"]["factor"], 2) != want:
                fails.append("Insta-Pro %s @ %d CFM/ton +%d F: %s vs %s" % (
                    model, cfm_ton, ap, r["calibration"]["factor"], want))
        if abs(pair[0] / pair[1] - 1) > 0.05:
            fails.append("Insta-Pro 900 and 700 imply different factors: %s" % (pair,))

# 2,500 ACFM settles the arrangement: co-current cannot make the 900's rating.
m = ip["models"]["900"]
co = cooler_heat.size({"coolerType": "drum_co", "tph": m["max_lb_h"] / 2000,
                       "tProductIn": 250, "cp": 0.45, "bulkDensity": 38,
                       "moistIn": 7, "moistOut": 6, "airDryBulb": 100,
                       "airRh": 40, "elevation": 1000, "drumDia": m["dia_in"] / 12,
                       "drumLength": m["length_in"] / 12, "drumFill": 15,
                       "acfm": m["fan_acfm"]})
if round(co["balance"]["floorCoCurrent"]) != 153:
    fails.append("Insta-Pro 900 co-current floor: %s" % co["balance"]["floorCoCurrent"])

# Drums carry the Insta-Pro calibration by default (Jason, 2026-10-03); beds
# do not, and a factor typed in still wins.
dflt = cooler_heat.size(dict(OZARK, coolerType="drum_counter", acfm=22300,
                             drumDia=9.0, drumLength=30.0, calFactor=""))
one = cooler_heat.size(dict(OZARK, coolerType="drum_counter", acfm=22300,
                            drumDia=9.0, drumLength=30.0, calFactor=1.0))
if abs(dflt["transfer"]["uvUsed"] / one["transfer"]["uvUsed"]
       - cooler_heat.DRUM_CAL_DEFAULT) > 0.01:
    fails.append("blank calFactor on a drum is not the Insta-Pro default")
if not any("Insta-Pro" in n for n in dflt["notes"]):
    fails.append("drum default calibration is not called out in the notes")
if cooler_heat.size(dict(OZARK, calFactor=""))["transfer"]["uvUsed"] != t["uvUsed"]:
    fails.append("a blank calFactor moved the bed")
ip900 = cooler_heat.size({"coolerType": "drum_counter", "tph": 2, "tProductIn": 250,
                          "cp": 0.45, "bulkDensity": 38, "moistIn": 7, "moistOut": 6,
                          "airDryBulb": 100, "airRh": 40, "elevation": 1000,
                          "drumDia": 46 / 12, "drumLength": 8, "drumFill": 15,
                          "acfm": 2500})
if round(ip900["transfer"]["discharge"]) != 120:
    fails.append("Insta-Pro 900 at its rating with the default calibration: %s"
                 % ip900["transfer"]["discharge"])

# Rotary cooler sizing reproduces the Insta-Pro 900 at its rating: 2 TPH,
# 250 -> 120 F on a 100 F / 40 % day selects a 4 x 8, and the dryer still
# picks from the long grid only.
from calculators import rotary_cooler, dryer
rc_ip = rotary_cooler.size({"preset": "feed", "tph": 2, "tin": 250, "tout": 120,
                            "cp": 0.45, "rho": 38, "mcin": 7, "mcout": 6,
                            "tmax": 100, "humMode": "rh", "humVal": 40})
if rc_ip["model"] != "RC 4×8":
    fails.append("rotary sizing at the Insta-Pro 900 rating picked %s" % rc_ip["model"])
if any(d["L"] / d["d"] < 4 for d in rotary_cooler.DRUMS):
    fails.append("short cooler drums leaked into the dryer's grid")

if fails:
    print("cooler heat balance: %d disagreements with the workbook" % len(fails))
    for f in fails:
        print("  " + f)
    sys.exit(1)
print("cooler heat balance: reference case matches the workbook on %d cells, "
      "drum and calibration behave" % 37)
