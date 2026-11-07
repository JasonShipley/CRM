"""JSON in / JSON out contract (mce.dryer.v1) for the quote app and the rotary-dryer-build agent.

    from mce_engineering.equipment.dryer_calc.api import run
    response = run({"process": {"throughput": 1.5, "throughput_unit": "TPH"}, "fuel": {"fuel": "biomass"}})

The request is the DryerRequest schema (docs/dryer_calc/input_schema.json); anything left
out takes its documented default. The response always carries the sizing record index,
every resolved input with its source, overrides, flags and outputs. Errors come back as
status "error" with a message, never as a Python exception, so a phone UI can show them.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mce_engineering.core.audit import AuditStore
from mce_engineering.core.provenance import Flag

from . import rotary, selector
from .resolve import resolve
from .schema import DryerRequest

CONTRACT = "mce.dryer.v1"
FAMILY = "rotary_dryer"
AUDIT_PREFIX = "RD"
SEVERITY_ORDER = ["blocked", "violation", "needs_verification", "warning", "info"]
selector.register("rotary", rotary.calculate)


def _summary(out: dict, sel: dict) -> dict:
    mb, res, drum = out["mass_balance"], out["results"], out["drum"]["recommended"]
    fan = out["air_system"]["fan"]
    gb = out["gas_balance"]
    lines = [
        f"Evaporation {mb['evaporation_lb_hr']['value']:,.0f} lb/hr: {mb['wet_feed_lb_hr']['value']:,.0f} lb/hr wet "
        f"at {mb['infeed_mc_wb_pct']:g}% to {mb['product_lb_hr']['value']:,.0f} lb/hr at {mb['target_mc_wb_pct']:g}% MC",
        f"Burner {res['burner_operating_mmbtu_hr_lhv']['value']:.2f} MMBtu/hr operating (LHV), "
        f"{res['burner_design_mmbtu_hr_lhv']['value']:.2f} design; fuel {res['fuel_lb_hr']['value']:,.0f} lb/hr",
        f"{res['btu_per_lb_water_lhv']['value']:,.0f} BTU/lb water (LHV)",
        f"Inlet {gb['inlet_temp_F']['value']:,.0f} F, exhaust {gb['exhaust_temp_F']['value']:g} F, "
        f"{gb['streams']['dryer_exhaust']['acfm']['value']:,.0f} ACFM exhaust",
        f"Drum {drum['size']}" if drum else "Drum: NONE PASSES (see flags)",
        f"Fan {fan['acfm']['value']:,.0f} ACFM, {fan['bhp_operating']['value']:.1f} BHP, {fan['motor_hp_nema']} HP motor",
    ]
    return {"lines": lines, "selector_recommends": sel["recommended"]}


def run(request: dict[str, Any] | DryerRequest, audit_root: str | Path | None = None) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        req = request if isinstance(request, DryerRequest) else DryerRequest.model_validate(request)
    except ValidationError as e:
        return {"contract": CONTRACT, "status": "error", "timestamp": now, "error": "invalid request",
                "details": json.loads(e.json(include_url=False))}
    try:
        R = resolve(req)
        mb_dry = rotary.mass_balance(R["process"], rotary._Ctx())["solids_lb_hr"]
        sel = selector.rank(selector.case_from_resolved(R.values, mb_dry))
        dryer = sel["recommended"] if req.dryer_type == "auto" else req.dryer_type
        calc = selector.CALCULATORS.get(dryer)
        if calc is None:
            return {"contract": CONTRACT, "status": "not_available", "timestamp": now, "dryer_type": dryer,
                    "message": f"{selector.LABELS[dryer]}: calculator not built yet.", "selector": sel,
                    "inputs": R.provenance, "flags": [f.model_dump() for f in R.flags]}
        res = calc(R)
    except ValueError as e:
        return {"contract": CONTRACT, "status": "error", "timestamp": now, "error": str(e)}
    flags: list[Flag] = R.flags + res["flags"]
    flags.sort(key=lambda f: SEVERITY_ORDER.index(f.severity))
    out = res["outputs"]
    record = {"index": None, "timestamp": now, "calculator_version": rotary.CALC_VERSION, "saved": False}
    if req.save_record:
        store = AuditStore(audit_root) if audit_root else AuditStore()
        rec = store.record(prefix=AUDIT_PREFIX, family=FAMILY, job_number=req.job.job_number,
                           calculator_version=rotary.CALC_VERSION,
                           inputs={"request": req.model_dump(mode="json"), "resolved": R.provenance},
                           overrides=R.overrides, results=out, flags=[f.model_dump() for f in flags])
        record = {"index": rec.index, "timestamp": rec.timestamp, "calculator_version": rec.calculator_version,
                  "sha256": rec.sha256, "saved": True, "store": str(store.root)}
    return {
        "contract": CONTRACT, "status": "ok", "dryer_type": dryer, "record": record, "job": req.job.model_dump(),
        "summary": _summary(out, sel), "outputs": out, "inputs": R.provenance, "overrides": R.overrides,
        "flags": [f.model_dump() for f in flags],
        "flag_counts": {s: sum(1 for f in flags if f.severity == s) for s in SEVERITY_ORDER},
        "selector": sel,
    }
