"""Dryer type selector: rule engine skeleton (Phase 2 structure).

ALL RULES AND THRESHOLDS BELOW ARE DRAFT FOR MCE REVIEW. They rank rotary drum, flash,
belt and infrared dryers from the shared process inputs and say which rules decided it.
Only the rotary drum has a calculator today; the others return "calculator not built yet".

Adding a dryer type later: add its key to DRYER_TYPES, its rules to RULES, and register
its calculate(resolved) function in CALCULATORS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

DRAFT = "DRAFT for MCE review"
DRYER_TYPES = ("rotary", "flash", "belt", "infrared")
LABELS = {"rotary": "Rotary drum dryer", "flash": "Flash dryer", "belt": "Belt dryer", "infrared": "Infrared dryer"}

# DRAFT thresholds (MCE to confirm), in one place so they are easy to review
TH = {
    "fine_particle_in": 0.25,  # flash: fine, free flowing below about 1/4 in.
    "coarse_particle_in": 0.25,
    "high_infeed_mc_wb": 45.0,
    "low_temp_product_F": 180.0,  # belt / IR territory
    "small_throughput_dry_lb_hr": 500.0,  # IR: small throughput
    "high_throughput_dry_lb_hr": 4000.0,  # flash: high throughput
    "large_throughput_dry_lb_hr": 20000.0,  # IR / belt get impractical
}


@dataclass
class Rule:
    dryer: str
    points: float
    reason: str
    when: Callable[[dict], bool]
    status: str = DRAFT


def _biomass(c: dict) -> bool:
    return c["material"] in ("wood_shavings", "sawdust", "wood_chips", "ag_residue")


RULES: list[Rule] = [
    # flash
    Rule("flash", 3, "fine, free-flowing particles (under about 1/4 in.)",
         lambda c: c["particle_size_in"] < TH["fine_particle_in"] and not c["sticky"]),
    Rule("flash", 2, "mostly surface moisture", lambda c: c["surface_moisture"]),
    Rule("flash", 2, "short residence time is enough", lambda c: c["residence_need"] == "short"),
    Rule("flash", 1, "high throughput", lambda c: c["dry_lb_hr"] >= TH["high_throughput_dry_lb_hr"]),
    Rule("flash", -3, "coarse particles will not stay suspended",
         lambda c: c["particle_size_in"] >= 2 * TH["fine_particle_in"]),
    Rule("flash", -2, "needs a long residence time", lambda c: c["residence_need"] == "long"),
    Rule("flash", -2, "sticky product fouls the duct", lambda c: c["sticky"]),
    # rotary
    Rule("rotary", 3, "coarse or variable particle size",
         lambda c: c["particle_size_in"] >= TH["coarse_particle_in"]),
    Rule("rotary", 2, "high infeed moisture", lambda c: c["infeed_mc_wb"] >= TH["high_infeed_mc_wb"]),
    Rule("rotary", 2, "robust product (low heat sensitivity)", lambda c: c["heat_sensitivity"] in ("none", "low", "moderate")),
    Rule("rotary", 2, "wood, biomass or ag residue", _biomass),
    Rule("rotary", 2, "direct firing on biomass", lambda c: c["heat_source"] == "biomass"),
    Rule("rotary", 1, "medium or long residence time", lambda c: c["residence_need"] in ("medium", "long")),
    Rule("rotary", -3, "highly heat sensitive product", lambda c: c["heat_sensitivity"] == "high"),
    Rule("rotary", -1, "tight footprint", lambda c: c["footprint"] == "tight"),
    # belt
    Rule("belt", 3, "heat sensitive or fragile product", lambda c: c["heat_sensitivity"] == "high"),
    Rule("belt", 2, "low product temperature limit", lambda c: c["max_product_temp_F"] <= TH["low_temp_product_F"]),
    Rule("belt", 2, "high fire risk (low temperature drying)", lambda c: c["fire_risk"] == "high"),
    Rule("belt", 2, "waste heat available", lambda c: c["heat_source"] == "waste_heat"),
    Rule("belt", 1, "long residence time", lambda c: c["residence_need"] == "long"),
    Rule("belt", -2, "tight footprint", lambda c: c["footprint"] == "tight"),
    Rule("belt", -1, "sticky product sticks to the belt", lambda c: c["sticky"]),
    # infrared
    Rule("infrared", 3, "small throughput", lambda c: c["dry_lb_hr"] <= TH["small_throughput_dry_lb_hr"]),
    Rule("infrared", 2, "high value or specialty product", lambda c: c["product_value"] == "high"),
    Rule("infrared", 2, "precise temperature control needed", lambda c: c["precise_temperature"]),
    Rule("infrared", 1, "electric heat source", lambda c: c["heat_source"] == "electric"),
    Rule("infrared", -4, "throughput too large for infrared", lambda c: c["dry_lb_hr"] >= TH["large_throughput_dry_lb_hr"]),
    Rule("infrared", -2, "deep bed / coarse product", lambda c: c["particle_size_in"] >= 1.0),
]

CALCULATORS: dict[str, Callable | None] = {"rotary": None, "flash": None, "belt": None, "infrared": None}


def register(dryer: str, fn: Callable) -> None:
    CALCULATORS[dryer] = fn


def case_from_resolved(values: dict, dry_lb_hr: float, extra: dict | None = None) -> dict:
    p, f = values["process"], values["fuel"]
    c = {"material": p["material"], "particle_size_in": p["particle_size_in"], "infeed_mc_wb": p["infeed_mc_wb"],
         "sticky": bool(p["sticky"]), "heat_sensitivity": p["heat_sensitivity"],
         "max_product_temp_F": p["max_product_temp_F"], "fire_risk": p["fire_risk"], "dry_lb_hr": dry_lb_hr,
         "residence_need": p["residence_need"], "surface_moisture": p["surface_moisture"],
         "heat_source": f["fuel"] if p["heat_source"] == "fuel" else p["heat_source"], "footprint": p["footprint"],
         "product_value": p["product_value"], "precise_temperature": p["precise_temperature"]}
    c.update(extra or {})
    return c


def rank(case: dict) -> dict:
    scores = {d: 0.0 for d in DRYER_TYPES}
    hits: dict[str, list[dict]] = {d: [] for d in DRYER_TYPES}
    for rule in RULES:
        try:
            ok = rule.when(case)
        except (KeyError, TypeError):
            ok = False
        if ok:
            scores[rule.dryer] += rule.points
            hits[rule.dryer].append({"points": rule.points, "reason": rule.reason})
    order = sorted(DRYER_TYPES, key=lambda d: (-scores[d], DRYER_TYPES.index(d)))
    ranked = []
    for i, d in enumerate(order):
        reasons = sorted(hits[d], key=lambda h: -abs(h["points"]))
        ranked.append({"rank": i + 1, "dryer_type": d, "label": LABELS[d], "score": scores[d],
                       "deciding_reasons": [f"{'+' if h['points'] > 0 else ''}{h['points']:g}: {h['reason']}"
                                            for h in reasons],
                       "calculator": "available" if d == "rotary" else "calculator not built yet"})
    top = ranked[0]
    margin = top["score"] - ranked[1]["score"]
    return {"status": DRAFT, "recommended": top["dryer_type"], "margin": margin,
            "close_call": margin < 2, "ranking": ranked, "case": case,
            "note": "Rules and thresholds are DRAFT for MCE review. Only the rotary drum returns a full calculation."}
