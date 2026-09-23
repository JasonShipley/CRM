#!/usr/bin/env python3
"""MCE sizing calculators — the engine behind the quote form builder.

Each module here is a faithful Python port of one of MCE's own calculators,
which are served whole and unmodified from renderer/tools/. The ports let the
quote builder size and price equipment server-side; the originals stay the
engineering source of truth and the thing MCE edits.

`renderer/tests/` diffs every port against its original by running the original's
own JavaScript headless — run it after touching either side.

This module is the registry: it declares each calculator's inputs so the form UI
and the JSON API are generated from one description, and dispatches `run()`.
"""
from . import baghouse, cooler, cyclone, duct, hammer_pattern, hammermill
from ._data import CL_CHECK_DEFS, CL_PELLETS, MCE_XM_MILLS, PRODUCTS, XM_CHART

# --------------------------------------------------------------- input specs --
# type: number | select | checkbox | hidden. `advanced` fields are collapsed in
# the UI behind "Pricing & build assumptions".

HAMMERMILL_FIELDS = [
    {"key": "product", "label": "Product", "type": "select", "default": "0",
     "options": [(str(i), p["name"]) for i, p in enumerate(PRODUCTS)],
     "help": "Sets the starting index, screen area per HP and bulk density — all three stay editable."},
    {"key": "pph", "label": "Capacity", "type": "number", "unit": "PPH",
     "default": 24000, "step": 100, "min": 0},
    {"key": "screen64", "label": "Screen size", "type": "number", "unit": "/64\"",
     "default": 8, "step": 1, "min": 1},
    {"key": "index", "label": "Grinding index", "type": "number", "default": 40,
     "step": 1, "min": 1},
    {"key": "sqInHp", "label": "Screen area per HP", "type": "number", "unit": "in²/HP",
     "default": 15, "step": 0.5, "min": 1},
    {"key": "bulkDensity", "label": "Bulk density", "type": "number", "unit": "lb/ft³",
     "default": 45, "step": 1, "min": 1},
    {"key": "family", "label": "Rotor family", "type": "select", "default": "grain",
     "options": [("grain", '22" / 44" rotor — grain & biomass, 60 Hz'),
                 ("render", '19" / 38" rotor — rendering or 380 V 50 Hz')]},
    {"key": "millModel", "label": "Mill model", "type": "select", "default": "",
     "options": [("", "Auto — best fit for the required screen area")]
                + [(m["model"], f'{m["model"]} — {m["screenSize"]}, {m["area"]:,} in², '
                                f'{m["hpMin"]}–{m["hpMax"]} HP') for m in MCE_XM_MILLS],
     "help": "Override the auto match when the plant has a reason to."},
    {"key": "plenumVelocity", "label": "Plenum design velocity", "type": "select",
     "default": "300",
     "options": [("200", "200 FPM — light/fluffy or fibrous"),
                 ("250", "250 FPM — general feed"),
                 ("300", "300 FPM — heavy/dense (corn)"),
                 ("350", "350 FPM — heavy/dense (corn)"),
                 ("400", "400 FPM — space-constrained"),
                 ("450", "450 FPM — space-constrained")]},
    {"key": "feederDia", "label": "Rotary feeder", "type": "select", "default": "10",
     "options": [("10", '10" dia'), ("14", '14" dia')]},
    {"key": "cupType", "label": "Feeder cups", "type": "select", "default": "nylon",
     "options": [("nylon", "Nylon cup"), ("ss", "Stainless round cup"),
                 ("tt", 'Tight-tolerance SS (10" only)')]},
    {"key": "rowCount", "label": "Feeder rows", "type": "select", "default": "",
     "options": [("", "Auto — matched to the mill screen width")]
                + [(str(n), f"{n}-row") for n in
                   [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]]},
    {"key": "magnetClean", "label": "Magnet cleanout", "type": "select", "default": "sma",
     "options": [("sma", "Manual clean (SMA)"),
                 ("scmam", "Manual self-clean (SCMA-M)"),
                 ("scmaa", "Auto self-clean (SCMA-A)")]},
    {"key": "trough", "label": "Screw trough loading", "type": "select", "default": "45",
     "options": [("45", "45%"), ("30a", "30% A"), ("30b", "30% B"), ("15", "15%")]},
    {"key": "runLength", "label": "Extra screw run", "type": "number", "unit": "ft",
     "default": 2, "step": 1, "min": 0,
     "help": "Beyond the plenum discharge flange, to the actual discharge point."},
    {"key": "millMult", "label": "Mill multiplier", "type": "number", "default": 1.73,
     "step": 0.01, "min": 0.5, "advanced": True},
    {"key": "feederMult", "label": "Feeder multiplier", "type": "number", "default": 2.00,
     "step": 0.01, "min": 0.5, "advanced": True},
    {"key": "plenumDuty", "label": "Plenum duty factor", "type": "number", "default": 1.35,
     "step": 0.05, "min": 1, "advanced": True},
    {"key": "plenumRate", "label": "Plenum rate", "type": "number", "unit": "$/lb",
     "default": 15.25, "step": 0.25, "min": 1, "advanced": True},
]

COOLER_FIELDS = [
    {"key": "pellet", "label": "Product", "type": "select", "default": "p6",
     "options": [(p["id"], p["label"]) for p in CL_PELLETS],
     "help": "Items marked * are meal/flake products — they size on airflow, not volume."},
    {"key": "tph", "label": "Production rate", "type": "number", "unit": "TPH",
     "default": 20, "step": 0.5, "min": 0.5},
    {"key": "density", "label": "Bulk density", "type": "number", "unit": "lb/ft³",
     "default": 40, "step": 1, "min": 10, "max": 80},
    {"key": "margin", "label": "Design margin", "type": "number", "unit": "%",
     "default": 0, "step": 5, "min": 0, "max": 50},
    {"key": "upsize", "label": "Upsize", "type": "select", "default": "0",
     "options": [("0", "Smallest model that fits"), ("1", "One size up"),
                 ("2", "Two sizes up")]},
    {"key": "mealHeight", "label": "Meal cooler height", "type": "select", "default": "std4",
     "options": cooler.MEAL_HEIGHTS,
     "help": "Only applies to meal and cake products."},
    {"key": "panel", "label": "Control panel", "type": "select", "default": "mce",
     "options": [("mce", "MCE Cooler Control System"), ("none", "By others")]},
    {"key": "xp", "label": "XP electrics", "type": "select", "default": "none",
     "options": [("none", "Standard"), ("air", "XP — air floor"),
                 ("elec", "XP — electric floor")]},
    {"key": "sensors", "label": "Extra level sensors", "type": "number", "default": 0,
     "step": 1, "min": 0, "max": 8},
]

BAGHOUSE_FIELDS = [
    {"key": "mode", "label": "Airflow basis", "type": "select", "default": "cfm",
     "options": [("cfm", "Enter system CFM"),
                 ("mill", "From mill screen area (× 1.3)")]},
    {"key": "cfm", "label": "System airflow", "type": "number", "unit": "CFM",
     "default": 3000, "step": 50, "min": 0, "showWhen": {"mode": "cfm"}},
    {"key": "screenArea", "label": "Mill screen area", "type": "number", "unit": "in²",
     "default": 2400, "step": 10, "min": 0, "showWhen": {"mode": "mill"}},
    {"key": "ratio", "label": "Air-to-cloth ratio", "type": "number", "default": 7,
     "step": 0.25, "min": 1, "max": 15,
     "help": "MCE standard is 7:1. 6.25:1 is conservative, 7.5:1 aggressive."},
    {"key": "lenFilter", "label": "Bag length", "type": "select", "default": "any",
     "options": [("any", "Any"), ("4", "4 ft"), ("6", "6 ft"), ("8", "8 ft"),
                 ("10", "10 ft")]},
]

CYCLONE_FIELDS = [
    {"key": "series", "label": "Cyclone line", "type": "select", "default": "mce",
     "options": [("mce", "MCE — HE and H series"),
                 ("budget", "Budget — primed gray")],
     "help": "The MCE line matches HE up to 12,600 CFM and H above that."},
    {"key": "mode", "label": "Airflow basis", "type": "select", "default": "cfm",
     "options": [("cfm", "Enter rated CFM"),
                 ("measure", "From inlet dimensions and velocity")]},
    {"key": "cfm", "label": "Rated airflow", "type": "number", "unit": "CFM",
     "default": 3500, "step": 50, "min": 0, "showWhen": {"mode": "cfm"}},
    {"key": "inletShape", "label": "Inlet shape", "type": "select", "default": "round",
     "options": [("round", "Round"), ("rect", "Rectangular")],
     "showWhen": {"mode": "measure"}},
    {"key": "inletId", "label": "Inlet ID", "type": "number", "unit": "in",
     "default": 12, "step": 1, "min": 0,
     "showWhen": {"mode": "measure", "inletShape": "round"}},
    {"key": "inletW", "label": "Inlet width (ID)", "type": "number", "unit": "in",
     "default": 10, "step": 1, "min": 0,
     "showWhen": {"mode": "measure", "inletShape": "rect"}},
    {"key": "inletH", "label": "Inlet height (ID)", "type": "number", "unit": "in",
     "default": 18, "step": 1, "min": 0,
     "showWhen": {"mode": "measure", "inletShape": "rect"}},
    {"key": "fpm", "label": "Inlet velocity", "type": "select", "default": "3500",
     "options": cyclone.FPM_PRESETS, "showWhen": {"mode": "measure"}},
    {"key": "wg", "label": "Static pressure", "type": "select", "default": "3",
     "options": cyclone.WG_OPTIONS,
     "help": "H-series rating basis. Ignored below 12,600 CFM, where HE applies."},
]

HAMMER_PATTERN_FIELDS = [
    {"key": "motorHp", "label": "Motor HP", "type": "number", "unit": "HP",
     "default": 200, "step": 5, "min": 0},
    {"key": "hpPerHammer", "label": "HP per hammer", "type": "number", "unit": "HP",
     "default": 1.5, "step": 0.05, "min": 0.1,
     "help": "Corn is 1.5 standard, 1.75 alternate. MCE has no other material on "
             "record — get the number from engineering rather than guessing."},
    {"key": "rows", "label": "Pattern", "type": "select", "default": "8",
     "options": [("8", "8-row — high-fat / fibrous / fine"),
                 ("4", "4-row — inside coarse, outside fine")]},
    {"key": "pinLength", "label": "Pin length", "type": "number", "unit": "in",
     "default": 40, "step": 1, "min": 6,
     "help": "Usually the chamber width."},
    {"key": "thickness", "label": "Hammer thickness", "type": "number", "unit": "in",
     "default": 0.25, "step": 0.0625, "min": 0.125},
    {"key": "pinAllowance", "label": "Pin end allowance", "type": "number", "unit": "in",
     "default": 7.5, "step": 0.25, "min": 0,
     "help": "Pin length taken up by the rotor plates — 7.5\" on the 38/44-40 drawing."},
    {"key": "countOverride", "label": "Count override", "type": "number",
     "unit": "hammers", "default": "", "step": 1, "min": 1, "advanced": True,
     "help": "Lay out a count engineering has already set."},
]

DUCT_FIELDS = [
    {"key": "mode", "label": "Solve for", "type": "select", "default": "dia",
     "options": [("dia", "Duct diameter from an airflow"),
                 ("cfm", "Airflow from a duct diameter")]},
    {"key": "cfm", "label": "Airflow", "type": "number", "unit": "CFM",
     "default": 1400, "step": 10, "min": 0, "showWhen": {"mode": "dia"}},
    {"key": "diameter", "label": "Duct diameter", "type": "number", "unit": "in",
     "default": 8, "step": 0.5, "min": 0, "showWhen": {"mode": "cfm"}},
    {"key": "velocity", "label": "Minimum conveying velocity", "type": "select",
     "default": "4000", "options": duct.VELOCITY_PRESETS,
     "help": "Below this the material drops out of the airstream."},
]

CALCULATORS = {
    "hammermill": {
        "key": "hammermill", "label": "Hammermill + Plenum",
        "blurb": "Mill model, motor HP, screen area, rotary feeder, plenum and "
                 "discharge screw — with package pricing.",
        "fields": HAMMERMILL_FIELDS, "run": hammermill.size, "prices": True,
        "tool": "hammermill-sizing-calculator.html",
    },
    "cooler": {
        "key": "cooler", "label": "Counterflow Cooler",
        "blurb": "Cooler model from throughput and product — volume-first for "
                 "pellets, airflow-first for meal — with option pricing.",
        "fields": COOLER_FIELDS, "run": cooler.size, "prices": True,
        "tool": "counterflow-cooler-sizing-calculator.html",
    },
    "cyclone": {
        "key": "cyclone", "label": "Cyclone",
        "blurb": "Rated CFM — entered, or from the inlet and its velocity — to an "
                 "MCE HE/H or budget cyclone, with the full dimension set.",
        "fields": CYCLONE_FIELDS, "run": cyclone.size, "prices": False,
        "tool": "cyclone-cfm-calculator.html",
    },
    "hammer_pattern": {
        "key": "hammer_pattern", "label": "Hammer Pattern",
        "blurb": "Motor HP to hammer count, the balanced row split and the pin "
                 "stack check — a shop and parts tool, not a quote line.",
        "fields": HAMMER_PATTERN_FIELDS, "run": hammer_pattern.size, "prices": False,
        "tool": "hammer-pattern-calculator.html",
    },
    "duct": {
        "key": "duct", "label": "Duct Sizing",
        "blurb": "Airflow to duct diameter at the conveying velocity, rounded up "
                 "to the next even inch — or the airflow a given duct carries.",
        "fields": DUCT_FIELDS, "run": duct.size, "prices": False,
        "tool": "duct-sizing-calculator.html",
    },
    "baghouse": {
        "key": "baghouse", "label": "Baghouse Filter",
        "blurb": "Cloth area and MCE filter model from system airflow or a mill "
                 "screen area, with the Kice equivalent.",
        "fields": BAGHOUSE_FIELDS, "run": baghouse.size, "prices": False,
        "tool": "baghouse-filter-calculator.html",
    },
}

# Calculators MCE has said are coming. They show as greyed-out cards so the sales
# team can see what is and is not available yet.
PLANNED = [
    ("Dryer", "Dryer sizing from moisture removal duty."),
    ("Fan", "CFM and static pressure to fan size, model and HP."),
    ("Airlock", "Airflow and material to rotary airlock size and drive."),
]

# Hosted calculators the quote builder cannot yet size with, because no Python
# port exists. The tools page labels them so nobody goes looking for the field.
NOT_PORTED = {
    "rotary-cooler": "Hosted only — no quote-builder port yet",
}

PRODUCT_DEFAULTS = [
    {"index": p["index"], "sqInHp": p["sqInHp"], "bulkDensity": p["bulkDensity"],
     "chart": XM_CHART.get(p["name"])}
    for p in PRODUCTS
]

COOLER_OPTION_DEFS = CL_CHECK_DEFS


def run(key, form):
    """Run a calculator against a raw form dict. Always returns a dict; a failed
    run carries an `error` string rather than raising."""
    calc = CALCULATORS.get(key)
    if not calc:
        return {"error": f"Unknown calculator: {key}"}
    try:
        result = calc["run"](form or {})
    except Exception as e:                       # noqa: BLE001 - surface, don't 500
        return {"error": f"{calc['label']} could not run: {e}"}
    if not result.get("error"):
        result.setdefault("calculator", calc["label"])
        result["key"] = key
    return result
