"""Resolve a DryerRequest into concrete values with provenance.

For every input field the sizing record keeps: value, unit, source, the default it
replaced (if any), whether it is an override, and the override reason. Values outside
the field's sane range raise an OUT_OF_RANGE flag with the reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mce_engineering.core.provenance import Flag

from .presets import FUELS, MATERIALS, MCE_CONFIRM, STANDARD_DRUM_DIAMETERS_FT, STANDARD_DRUM_LENGTHS_FT, \
    STANDARD_DRUM_SOURCE
from .schema import BLOCKS, DryerRequest, field_meta


@dataclass
class Resolved:
    values: dict[str, dict[str, Any]]  # block -> name -> value
    provenance: list[dict[str, Any]]
    flags: list[Flag]
    overrides: list[dict[str, Any]]
    mce_assumptions_used: list[str] = field(default_factory=list)

    def __getitem__(self, block: str) -> dict[str, Any]:
        return self.values[block]


def _in_range(value, lo, hi) -> bool:
    vals = value if isinstance(value, list) else [value]
    for x in vals:
        if not isinstance(x, (int, float)) or isinstance(x, bool):
            continue
        if lo is not None and x < lo or hi is not None and x > hi:
            return False
    return True


def resolve(req: DryerRequest) -> Resolved:
    mat = MATERIALS[req.process.material]
    fuel = FUELS[req.fuel.fuel]
    values: dict[str, dict[str, Any]] = {}
    prov: list[dict[str, Any]] = []
    flags: list[Flag] = []
    overrides: list[dict[str, Any]] = []
    assumptions: list[str] = []

    for block in BLOCKS:
        model = getattr(req, block)
        values[block] = {}
        for name in type(model).model_fields:
            meta = field_meta(type(model), name)
            raw = getattr(model, name)
            user_set = name in model.model_fields_set
            path = f"{block}.{name}"
            preset_key = meta.get("preset")
            default, default_src = meta["default"], meta.get("source", "") or "calculator default"
            if preset_key:
                pre = (mat if block == "process" or (block == "rotary" and preset_key in mat) else fuel).get(preset_key)
                if pre is not None:
                    default, default_src = pre["value"], pre["source"]
                    if block == "process" or block == "rotary":
                        default_src = f"material preset '{req.process.material}': {default_src}"
                    else:
                        default_src = f"fuel preset '{req.fuel.fuel}': {default_src}"
            value = default if raw is None else raw
            overridden = bool(user_set and raw is not None and raw != default)
            reason = req.override_reasons.get(path, "")
            source = (f"user override{': ' + reason if reason else ''}" if overridden else default_src)
            if not overridden and MCE_CONFIRM in str(default_src) and value is not None:
                assumptions.append(path)
            values[block][name] = value
            rec = {"field": path, "value": value, "unit": meta.get("unit", ""), "source": source,
                   "overridden": overridden}
            if overridden:
                rec["default"] = default
                rec["default_source"] = default_src
                overrides.append({"field": path, "value": value, "default": default, "default_source": default_src,
                                  "reason": reason or "not given"})
                flags.append(Flag(severity="info", code="OVERRIDE",
                                  message=f"{path} set to {value} (default {default}; {default_src})"
                                          + (f". Reason: {reason}" if reason else ". No reason given."),
                                  ref=path))
            lo, hi = (meta.get("sane_range") or [None, None])
            if value is not None and not _in_range(value, lo, hi):
                why = meta.get("range_reason") or "outside the range MCE treats as normal for this input"
                flags.append(Flag(severity="warning", code="OUT_OF_RANGE",
                                  message=f"{path} = {value} {meta.get('unit', '')} is outside {lo} to {hi}: {why}. "
                                          f"Used as entered; confirm.", ref=path))
            prov.append(rec)

    # second pass: defaults that depend on other inputs
    p, s, f, r, a = (values[b] for b in BLOCKS)

    def derive(block: str, name: str, value: Any, source: str) -> None:
        values[block][name] = value
        for rec in prov:
            if rec["field"] == f"{block}.{name}":
                rec["value"], rec["source"] = value, source

    if p["backmix_mc_wb"] is None:
        derive("process", "backmix_mc_wb", p["target_mc_wb"], "= product MC (SHEET Input A15)")
    if p["backmix_temp_F"] is None:
        derive("process", "backmix_temp_F", s["ambient_temp_F"], "= ambient. " + MCE_CONFIRM)
    if p["feed_temp_F"] is None:
        derive("process", "feed_temp_F", s["ambient_temp_F"], "= ambient (SHEET Input D14)")
    if f["fuel_temp_F"] is None:
        derive("fuel", "fuel_temp_F", s["ambient_temp_F"], "= ambient")
    if p["bulk_density_wet"] is None:
        x_in = p["infeed_mc_wb"] / (100 - p["infeed_mc_wb"])
        derive("process", "bulk_density_wet", p["bulk_density_dry"] * (1 + x_in),
               "= dry bulk density x (1 + infeed dry-basis MC), no shrink or swell. " + MCE_CONFIRM)
        assumptions.append("process.bulk_density_wet")
    if r["recycle_temp_F"] is None:
        derive("rotary", "recycle_temp_F", r["exhaust_temp_F"] - 5.0, "= exhaust - 5 F (SHEET Input F29)")
    if r["shell_U"] is None:
        derive("rotary", "shell_U", 0.5 if r["insulated"] else 1.5,
               ("jacketed" if r["insulated"] else "bare") + " shell, combined convection + radiation. " + MCE_CONFIRM)
        assumptions.append("rotary.shell_U")
    if a["duct_velocity_fpm"] is None:
        dv = 5200.0 if p["bulk_density_dry"] > 12 else 4500.0
        derive("air", "duct_velocity_fpm", dv, "SHEET Input A23 rule (4,500 FPM; 5,200 if bulk density > 12)")
    if r["standard_diameters_ft"] is None:
        derive("rotary", "standard_diameters_ft", list(STANDARD_DRUM_DIAMETERS_FT), STANDARD_DRUM_SOURCE)
        assumptions.append("rotary.standard_diameters_ft")
    if r["standard_lengths_ft"] is None:
        derive("rotary", "standard_lengths_ft", list(STANDARD_DRUM_LENGTHS_FT), STANDARD_DRUM_SOURCE)

    # list-valued ranges must be [low, high]
    for blk, name in (("rotary", "ver_range"), ("rotary", "fill_range_pct"), ("rotary", "critical_speed_range_pct"),
                      ("rotary", "slope_range_in_per_ft"), ("rotary", "ld_range")):
        vv = values[blk][name]
        if not (isinstance(vv, list) and len(vv) == 2 and vv[0] <= vv[1]):
            raise ValueError(f"{blk}.{name} must be [low, high], got {vv!r}")

    assumptions = sorted(set(assumptions))
    if assumptions:
        flags.append(Flag(severity="needs_verification", code="MCE_ASSUMPTIONS",
                          message=f"{len(assumptions)} default values in this run are MCE assumptions awaiting "
                                  f"confirmation: {', '.join(assumptions)}. See docs/dryer_calc/"
                                  f"assumptions_for_confirmation.md.", ref="assumptions"))
    return Resolved(values=values, provenance=prov, flags=flags, overrides=overrides, mce_assumptions_used=assumptions)
