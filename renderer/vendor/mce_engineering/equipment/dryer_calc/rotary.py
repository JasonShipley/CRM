"""Rotary drum dryer engine (direct fired, co-current). Pure calculation: no I/O, no UI.

Order of calculation (task 3a to 3i):
  a mass balance -> b product heat -> c combustion -> d gas-side heat and mass balance
  (numeric solve) -> e losses -> f results -> g drum sizing -> h air system -> i feed and
  discharge handoffs.

Gas side (d). Unknowns: fuel rate m_f, dilution (make-up) air m_dil and, unless fixed,
the dryer inlet temperature T_in. Equations:
  furnace / mixing chamber:
     m_f (LHV + W_f hfg32) - (1 - eta) m_f LHV + m_f cp_f (T_f - 32)
       + H(comb air, T_amb) + H(dilution air, T_amb) + H(recycle, T_rec) = H(inlet gas, T_in)
  drum:
     H(inlet gas, T_in) + H(feed) + H(leak air, T_amb) = H(exhaust gas, T_exh) + H(product) + Q_shell
  plus, when gas_mode is not inlet_temp, inlet gas lb/hr = target or exhaust ACFM = target.
Species are tracked in lbmol/hr (N2, O2, Ar, CO2, H2O, SO2), so humidity, dew point, SCFM and
ACFM all follow from the same stream. Solved with damped Newton to 1e-9 of the product heat
(well inside the 0.1% requirement). Shell loss U A dT depends on the drum, which depends on
the gas flow, so drum selection and the gas solve iterate until the drum stops changing.
"""

from __future__ import annotations

import math
from typing import Any

from mce_engineering.core.provenance import Flag

from . import combustion as cb
from . import emissions as em
from .drum import DrumDuty, DrumRules, select_drum
from .presets import (FUELS, LHV_AS_FIRED_SANE, MATERIALS, NEMA_HP, STANDARD_DRUM_MAX_NORMAL_LENGTH_FT,
                      WOOD_LHV_DRY_SANE)
from .properties import (HFG_77F_BTU_LB, HFG_TRIPLE_BTU_LB, MW, MW_AIR, REFERENCE_STATE, acfm_from_lbmol_hr,
                         adiabatic_saturation_f, barometric_psia, dew_point_f, gas_density_lb_ft3, h_liquid_water_btu_lb,
                         h_mix_btu, h_vapor_btu_lb, psat_psia, scfm_from_lbmol_hr)
from .resolve import Resolved
from .solver import SolverError, newton
from .units import IN_WC_TO_PSI, LB_PER_TON, STD_FT3_PER_LBMOL, q

CALC_VERSION = "dryer_calc rotary 1.0.0"
TYPICAL_SPECIFIC_HEAT = (1400.0, 1900.0)  # BTU/lb water, task statement test-case range
FIRE_RISK_INLET_F = 1000.0  # Jason 2026-11-07: 900 F default, 1,000 F acceptable
AMCA_STD_AIR = 0.075  # lb/ft3, AMCA 210 standard air (70 F, 29.92 in. Hg)


def _mass(m: dict[str, float]) -> float:
    return sum(n * MW[s] for s, n in m.items())


def _mol(m: dict[str, float]) -> float:
    return sum(m.values())


class _Ctx:
    """Collects flags and the calculation trace for one run."""

    def __init__(self) -> None:
        self.flags: list[Flag] = []
        self.trace: list[dict[str, Any]] = []

    def flag(self, sev: str, code: str, msg: str, ref: str = "") -> None:
        self.flags.append(Flag(severity=sev, code=code, message=msg, ref=ref))

    def t(self, step: str, formula: str, value: float, unit: str, ref: str = "") -> float:
        self.trace.append({"step": step, "formula": formula, "value": value, "unit": unit, "ref": ref})
        return value


# ------------------------------------------------------------------------------- a. mass balance
def mass_balance(p: dict, ctx: _Ctx) -> dict:
    t = p["throughput"] * (LB_PER_TON if p["throughput_unit"] == "TPH" else 1.0)
    w_in, w_out, w_bm = p["infeed_mc_wb"] / 100, p["target_mc_wb"] / 100, p["backmix_mc_wb"] / 100
    if w_out >= w_in:
        raise ValueError(f"target MC {p['target_mc_wb']}% must be below infeed MC {p['infeed_mc_wb']}%")
    basis = p["throughput_basis"]
    solids = t * (1 - w_in) if basis == "wet_feed" else t if basis == "dry_solids" else t * (1 - w_out)
    wet = solids / (1 - w_in)
    water_in = wet - solids
    product = solids / (1 - w_out)
    water_out = product - solids
    evap = water_in - water_out
    bm_wet = p["backmix_ratio"] * wet
    bm_solids = bm_wet * (1 - w_bm)
    bm_water = bm_wet - bm_solids
    drum_solids = solids + bm_solids
    drum_water_in = water_in + bm_water
    drum_out = drum_solids / (1 - w_out)
    drum_water_out = drum_out - drum_solids
    drum_evap = drum_water_in - drum_water_out
    mixed_mc = drum_water_in / (drum_solids + drum_water_in) * 100
    if abs(w_bm - w_out) > 1e-9 and bm_wet > 0:
        ctx.flag("info", "BACKMIX_MC", f"Backmix MC {p['backmix_mc_wb']}% differs from product MC "
                                       f"{p['target_mc_wb']}%; drum evaporation uses the backmix MC as entered.")
    closure = (wet + bm_wet) - (drum_out + drum_evap)
    ctx.t("solids", "wet x (1 - MC_in)", solids, "lb/hr")
    ctx.t("product", "solids / (1 - MC_out)", product, "lb/hr")
    ctx.t("evaporation", "water_in - water_out", drum_evap, "lb/hr")
    return {
        "wet_feed_lb_hr": wet, "solids_lb_hr": solids, "water_in_lb_hr": water_in, "product_lb_hr": product,
        "water_out_lb_hr": water_out, "evaporation_lb_hr": drum_evap, "evaporation_fresh_lb_hr": evap,
        "backmix_lb_hr": bm_wet, "backmix_solids_lb_hr": bm_solids, "backmix_water_lb_hr": bm_water,
        "drum_infeed_lb_hr": wet + bm_wet, "drum_solids_lb_hr": drum_solids, "drum_water_in_lb_hr": drum_water_in,
        "drum_discharge_lb_hr": drum_out, "drum_water_out_lb_hr": drum_water_out, "mixed_infeed_mc_wb": mixed_mc,
        "infeed_mc_db": w_in / (1 - w_in) * 100, "target_mc_db": w_out / (1 - w_out) * 100,
        "closure_lb_hr": closure, "closure_pct": closure / (wet + bm_wet) * 100,
    }


# ------------------------------------------------------------------------------- b. product heat
def product_heat(p: dict, mb: dict, t_exh: float, ctx: _Ctx) -> dict:
    cp, tp = p["material_cp"], p["product_temp_F"]
    tf, tb = p["feed_temp_F"], p["backmix_temp_F"]
    q_solids = cp * (mb["solids_lb_hr"] * (tp - tf) + mb["backmix_solids_lb_hr"] * (tp - tb))
    h_w_in = mb["water_in_lb_hr"] * h_liquid_water_btu_lb(tf) + mb["backmix_water_lb_hr"] * h_liquid_water_btu_lb(tb)
    hl_in = h_w_in / mb["drum_water_in_lb_hr"]
    q_resid = mb["drum_water_out_lb_hr"] * (h_liquid_water_btu_lb(tp) - hl_in)
    per_lb = h_vapor_btu_lb(t_exh) - hl_in
    q_evap = mb["evaporation_lb_hr"] * per_lb
    total = q_solids + q_resid + q_evap
    sheet_method = 212 - tf + 970.3 + 0.455 * (t_exh - 212)
    ctx.t("evaporation enthalpy", "h_vapor(T_exh) - h_liquid(T_feed)", per_lb, "BTU/lb",
          "IAPWS-95 liquid, ideal-gas vapor from hfg(32 F)")
    ctx.t("product heat", "solids + residual water + evaporation", total, "BTU/hr")
    h_feed = (cp * (mb["solids_lb_hr"] * (tf - 32) + mb["backmix_solids_lb_hr"] * (tb - 32)) + h_w_in)
    h_prod = cp * mb["drum_solids_lb_hr"] * (tp - 32) + mb["drum_water_out_lb_hr"] * h_liquid_water_btu_lb(tp)
    return {"solids_sensible_btu_hr": q_solids, "residual_water_btu_hr": q_resid, "evaporation_btu_hr": q_evap,
            "total_btu_hr": total, "per_lb_water": total / mb["evaporation_lb_hr"],
            "evaporation_btu_per_lb": per_lb, "evaporation_btu_per_lb_sheet_method": sheet_method,
            "h_feed_btu_hr": h_feed, "h_product_btu_hr": h_prod}


# ------------------------------------------------------------------------------- c. combustion
def fuel_model(fu: dict, fuel_key: str, is_wood_fuel: bool, ctx: _Ctx) -> dict:
    preset = FUELS[fuel_key]
    kind = preset["kind"]
    if kind == "gas":
        c = cb.gas_fuel(fu["gas_composition_pct"])
    else:
        c = cb.solid_fuel(fu["ultimate_dry_pct"], fu["moisture_wb"], is_wood=is_wood_fuel)
    for sev, code, msg in c.flags:
        ctx.flag(sev, code, msg, "fuel")
    h_dry = fu["ultimate_dry_pct"]["H"] if kind != "gas" else None
    lhv_entered = cb.to_lhv_as_fired(fu["heating_value"], fu["heating_value_basis"], fu["moisture_wb"], h_dry) \
        if kind != "gas" else fu["heating_value"]
    if kind == "gas" and fu["heating_value_basis"] not in ("net_as_fired",):
        hhv = fu["heating_value"]
        lhv_entered = hhv * c.lhv_computed_btu_lb / c.hhv_computed_btu_lb
    lhv = c.lhv_computed_btu_lb if fu["heating_value_source"] == "analysis" else lhv_entered
    dev = (lhv_entered - c.lhv_computed_btu_lb) / c.lhv_computed_btu_lb * 100
    if abs(dev) > 5:
        extra = ""
        if kind == "gas" and abs(lhv_entered - c.hhv_computed_btu_lb) / c.hhv_computed_btu_lb < 0.02:
            extra = (f" It is within {abs(lhv_entered / c.hhv_computed_btu_lb - 1) * 100:.1f}% of the computed HHV "
                     f"({c.hhv_computed_btu_lb:,.0f}), so it looks like a gross value labeled net.")
        ctx.flag("warning", "FUEL_HV_MISMATCH",
                 f"Entered heating value gives LHV as fired {lhv_entered:,.0f} BTU/lb, {dev:+.1f}% from the "
                 f"{c.lhv_computed_btu_lb:,.0f} BTU/lb computed from the fuel analysis.{extra} "
                 f"{'Using the entered value' if fu['heating_value_source'] == 'entered' else 'Using the analysis'}; "
                 f"set fuel.heating_value_source to choose.", "fuel.heating_value")
    if fuel_key in LHV_AS_FIRED_SANE:
        lo, hi = LHV_AS_FIRED_SANE[fuel_key]
        if not lo <= lhv <= hi:
            ctx.flag("warning", "FUEL_LHV_RANGE", f"LHV as fired {lhv:,.0f} BTU/lb is outside {lo:,} to {hi:,} "
                                                  f"for {preset['label']}.", "fuel.heating_value")
    if kind == "solid" and is_wood_fuel:
        lhv_dry = (lhv + HFG_77F_BTU_LB * fu["moisture_wb"] / 100) / (1 - fu["moisture_wb"] / 100)
        lo, hi = WOOD_LHV_DRY_SANE
        if not lo <= lhv_dry <= hi:
            ctx.flag("warning", "WOOD_LHV_HIGH" if lhv_dry > hi else "WOOD_LHV_LOW",
                     f"Wood fuel LHV back-calculated to dry basis is {lhv_dry:,.0f} BTU/lb; typical wood is "
                     f"{lo:,.0f} to {hi:,.0f}. At {fu['moisture_wb']:g}% MC a net value of "
                     f"{fu['heating_value']:,.0f} BTU/lb as fired is too high for wood.", "fuel.heating_value")
    hhv = lhv + HFG_77F_BTU_LB * c.water_formed_lb
    vol = {}
    if kind == "gas":
        rho_calc = c.mw_gas / STD_FT3_PER_LBMOL
        vol = {"scf_per_lb": STD_FT3_PER_LBMOL / c.mw_gas, "density_std_lb_ft3": rho_calc}
        if abs(fu["density"] - rho_calc) / rho_calc > 0.10:
            ctx.flag("warning", "FUEL_DENSITY", f"Entered gas density {fu['density']} lb/ft3 differs from "
                                                f"{rho_calc:.4f} lb/ft3 computed from the composition at 70 F, 1 atm "
                                                f"(MW {c.mw_gas:.2f}); the computed value is used for SCFH.",
                     "fuel.density")
        sg_preset = preset.get("sg", {}).get("value")
        if sg_preset and abs(sg_preset - c.sg_gas) / c.sg_gas > 0.01:
            ctx.flag("info", "FUEL_SG", f"Sheet SG {sg_preset} vs {c.sg_gas:.3f} computed from the composition.")
    return {"kind": kind, "c": c, "lhv": lhv, "hhv": hhv, "lhv_entered": lhv_entered, "vol": vol}


# ------------------------------------------------------------------------------- d. gas solve
class GasModel:
    def __init__(self, R: Resolved, mb: dict, ph: dict, fm: dict, p_site: float):
        self.s, self.f, self.r = R["site"], R["fuel"], R["rotary"]
        self.mb, self.ph, self.fm, self.p_site = mb, ph, fm, p_site
        self.c: cb.CombustionResult = fm["c"]
        self.ea = self.f["excess_air_pct"]
        self.w = self.s["humidity_lb_lb"]
        self.ta = self.s["ambient_temp_F"]
        self.t_exh = self.r["exhaust_temp_F"]
        self.t_rec = self.r["recycle_temp_F"]
        self.rf = self.r["recycle_fraction"]
        self.lam = self.r["leakage_pct"] / 100
        self.flue_per_lb = cb.flue_gas_per_lb_fuel(self.c, self.ea, self.w)
        self.v_evap = {"H2O": mb["evaporation_lb_hr"] / MW["H2O"]}
        self.shell_ua = 0.0  # BTU/hr-F, set from the drum
        self.fuel_cp = FUELS[self.f["fuel"]]["cp"]["value"]

    def shell_loss(self, m_f: float, t_in: float) -> float:
        if self.r["shell_loss_method"] == "percent":
            return self.r["shell_loss_pct"] / 100 * m_f * self.fm["lhv"]
        return self.shell_ua * ((t_in + self.t_exh) / 2 - self.ta)

    def streams(self, m_f: float, m_dil: float) -> dict[str, dict[str, float]]:
        fuel_gas = {k: v * m_f for k, v in self.flue_per_lb.items()}
        comb_air = cb.air_moles(m_f * self.c.stoich_air_lb * (1 + self.ea / 100), self.w)
        dil = cb.air_moles(m_dil, self.w)
        x = cb.add(fuel_gas, dil)
        mx, mv = _mass(x), _mass(self.v_evap)
        e_mass = ((1 + self.lam) * mx + mv) / (1 - self.rf * (1 + self.lam))
        m_mass = mx + self.rf * e_mass
        leak = cb.air_moles(self.lam * m_mass / (1 + self.w), self.w)
        e = cb.add(x, leak, self.v_evap, scale=1.0 / (1 - self.rf))
        rec = {k: v * self.rf for k, v in e.items()}
        m = cb.add(x, rec)
        stack = {k: v * (1 - self.rf) for k, v in e.items()}
        return {"fuel_gas": fuel_gas, "combustion_air": comb_air, "dilution_air": dil, "leakage_air": leak,
                "dryer_inlet": m, "dryer_exhaust": e, "recycle": rec, "stack": stack}

    def fuel_in(self, m_f: float) -> float:
        lhv = self.fm["lhv"]
        return m_f * (lhv + self.c.water_formed_lb * HFG_TRIPLE_BTU_LB - (1 - self.f["furnace_efficiency"]) * lhv
                      + self.fuel_cp * (self.f["fuel_temp_F"] - 32))

    def residuals(self, m_f: float, m_dil: float, t_in: float) -> tuple[float, float, dict]:
        st = self.streams(m_f, m_dil)
        h_inlet = h_mix_btu(st["dryer_inlet"], t_in)
        furnace = (self.fuel_in(m_f) + h_mix_btu(st["combustion_air"], self.ta) + h_mix_btu(st["dilution_air"], self.ta)
                   + h_mix_btu(st["recycle"], self.t_rec) - h_inlet)
        drum = (h_inlet + self.ph["h_feed_btu_hr"] + h_mix_btu(st["leakage_air"], self.ta)
                - h_mix_btu(st["dryer_exhaust"], self.t_exh) - self.ph["h_product_btu_hr"] - self.shell_loss(m_f, t_in))
        return furnace, drum, st

    def solve(self) -> dict:
        mode = self.r["gas_mode"]
        scale_e = self.ph["total_btu_hr"]
        m_f0 = 1.6 * scale_e / self.fm["lhv"]
        if mode == "inlet_temp":
            t_in = self.r["inlet_temp_F"]
            fn = lambda x: list(self.residuals(x[0], x[1], t_in)[:2])
            x, it, err = newton(fn, [m_f0, 10 * self.mb["evaporation_lb_hr"]], [scale_e, scale_e])
            m_f, m_dil = x
        else:
            target = self.r["inlet_gas_lb_hr"] if mode == "inlet_gas_flow" else self.r["exhaust_acfm_target"]
            if target is None:
                raise ValueError(f"gas_mode {mode} needs rotary.{'inlet_gas_lb_hr' if mode == 'inlet_gas_flow' else 'exhaust_acfm_target'}")

            def fn(x):
                fu, dr, st = self.residuals(x[0], x[1], x[2])
                if mode == "inlet_gas_flow":
                    g = _mass(st["dryer_inlet"]) - target
                else:
                    g = acfm_from_lbmol_hr(_mol(st["dryer_exhaust"]), self.t_exh, self.p_site) - target
                return [fu, dr, g]

            x, it, err = newton(fn, [m_f0, 10 * self.mb["evaporation_lb_hr"], 700.0], [scale_e, scale_e, target])
            m_f, m_dil, t_in = x
        fu, dr, st = self.residuals(m_f, m_dil, t_in)
        return {"m_fuel": m_f, "m_dilution": m_dil, "t_in": t_in, "streams": st, "iterations": it,
                "residual_furnace_btu_hr": fu, "residual_drum_btu_hr": dr, "max_scaled_residual": err}


def stream_summary(name: str, mol: dict[str, float], t_f: float, p_site: float, gauge_in_wc: float = 0.0) -> dict:
    n = _mol(mol)
    if n <= 0:
        return {"name": name, "lb_hr": q(0.0, "lb/hr")}
    mass = _mass(mol)
    h2o = mol.get("H2O", 0.0)
    dry_mass = mass - h2o * MW["H2O"]
    dry_mw = dry_mass / (n - h2o) if n > h2o else MW_AIR
    p = p_site + gauge_in_wc * IN_WC_TO_PSI
    mw = mass / n
    pw = h2o / n * p
    o2_wet = mol.get("O2", 0.0) / n * 100
    o2_dry = mol.get("O2", 0.0) / (n - h2o) * 100 if n > h2o else 0.0
    return {
        "name": name, "temp_F": q(t_f, "F"), "lb_hr": q(mass, "lb/hr"), "dry_gas_lb_hr": q(dry_mass, "lb/hr"),
        "h2o_lb_hr": q(h2o * MW["H2O"], "lb/hr"), "humidity_lb_lb": q(h2o * MW["H2O"] / dry_mass, "lb/lb"),
        "scfm": q(scfm_from_lbmol_hr(n), "SCFM"), "acfm": q(acfm_from_lbmol_hr(n, t_f, p), "ACFM"),
        "density_lb_ft3": q(gas_density_lb_ft3(mw, t_f, p), "lb/ft3"), "mw": round(mw, 3), "dry_mw": round(dry_mw, 3),
        "h2o_vol_pct": round(h2o / n * 100, 3), "o2_vol_pct_wet": round(o2_wet, 3), "o2_vol_pct_dry": round(o2_dry, 3),
        "co2_vol_pct_dry": round(mol.get("CO2", 0.0) / (n - h2o) * 100, 3) if n > h2o else 0.0,
        "dew_point_F": q(dew_point_f(pw), "F") if pw > 0 else None,
        "_lbmol_hr": {k: round(v, 6) for k, v in mol.items()},
    }


def _std_duct(acfm: float, v_target: float, inc_in: float, min_v: float | None = None) -> dict:
    d_exact = math.sqrt(4 * acfm / (math.pi * v_target)) * 12
    d = max(inc_in, round(d_exact / inc_in) * inc_in)
    v = acfm / (math.pi * (d / 12) ** 2 / 4)
    while min_v and v < min_v and d > inc_in:
        d -= inc_in
        v = acfm / (math.pi * (d / 12) ** 2 / 4)
    return {"acfm": q(acfm, "ACFM"), "diameter_exact_in": q(d_exact, "in"), "diameter_in": q(d, "in"),
            "velocity_fpm": q(v, "FPM")}


def _nema(hp: float) -> float | None:
    return next((h for h in NEMA_HP if h >= hp - 1e-9), None)


# ------------------------------------------------------------------------------- main entry
def calculate(R: Resolved) -> dict:
    ctx = _Ctx()
    p, s, f, r, a = R["process"], R["site"], R["fuel"], R["rotary"], R["air"]
    mat = MATERIALS[p["material"]]
    p_site = barometric_psia(s["elevation_ft"])
    ctx.t("site pressure", "14.696 (1 - 6.8754e-6 Z)^5.2559", p_site, "psia", "ASHRAE Fundamentals 2017 Ch.1 Eq.3")

    mb = mass_balance(p, ctx)
    ph = product_heat(p, mb, r["exhaust_temp_F"], ctx)
    is_wood_fuel = f["fuel"] == "biomass"
    self_fueled = is_wood_fuel and bool(mat.get("is_wood"))  # the burner can fire the dried product itself
    fm = fuel_model(f, f["fuel"], is_wood_fuel, ctx)
    c: cb.CombustionResult = fm["c"]

    t_flame = cb.adiabatic_flame_temp_f(fm["lhv"], c, f["excess_air_pct"], s["humidity_lb_lb"], s["ambient_temp_F"],
                                        f["furnace_efficiency"], FUELS[f["fuel"]]["cp"]["value"] * (f["fuel_temp_F"] - 32))
    if t_flame > 2780:
        ctx.flag("warning", "FLAME_T_EXTRAPOLATED", f"Flame temperature {t_flame:,.0f} F is above the 1,800 K limit of "
                                                    f"the cp fit and ignores dissociation; the true value is lower.")

    gm = GasModel(R, mb, ph, fm, p_site)
    rules = DrumRules(ver_range=r["ver_range"], design_velocity_fpm=r["drum_design_velocity_fpm"],
                      entrainment_fraction=r["entrainment_fraction"], residence_min=r["residence_target_min"],
                      fill_range_pct=r["fill_range_pct"], crit_pct=r["critical_speed_pct"],
                      crit_range_pct=r["critical_speed_range_pct"], slope_range_in_ft=r["slope_range_in_per_ft"],
                      ld_range=r["ld_range"], velocity_tolerance_pct=r["drum_velocity_tolerance_pct"],
                      entrainment_hard=not a["product_air_conveyed"])
    drum_sel, sol, outer = None, None, []

    def _duty(sol):
        st = sol["streams"]
        ex = st["dryer_exhaust"]
        return DrumDuty(
            evap_lb_hr=mb["evaporation_lb_hr"], exhaust_acfm=acfm_from_lbmol_hr(_mol(ex), r["exhaust_temp_F"], p_site),
            gas_in_lb_hr=_mass(st["dryer_inlet"]), gas_out_lb_hr=_mass(ex), solids_lb_hr=mb["drum_solids_lb_hr"],
            wet_in_lb_hr=mb["drum_infeed_lb_hr"], drum_out_lb_hr=mb["drum_discharge_lb_hr"],
            rho_bulk_wet=p["bulk_density_wet"], rho_bulk_dry=p["bulk_density_dry"], particle_in=p["particle_size_in"],
            particle_density=p["particle_density"], sphericity=p["sphericity"],
            gas_density_exhaust=gas_density_lb_ft3(_mass(ex) / _mol(ex), r["exhaust_temp_F"], p_site),
            exhaust_temp_F=r["exhaust_temp_F"])

    def _solve():
        try:
            return gm.solve()
        except SolverError as e:
            raise ValueError(f"gas-side balance did not converge: {e}") from e

    prev_key, seen = None, []
    for k in range(12):
        sol = _solve()
        duty = _duty(sol)
        drum_sel = select_drum(duty, rules, r["standard_diameters_ft"], r["standard_lengths_ft"], r["force_drum"])
        rec = drum_sel["recommended"]
        key = (rec["diameter_ft"], rec["length_ft"]) if rec else None
        outer.append({"iteration": k + 1, "fuel_lb_hr": sol["m_fuel"], "drum": key,
                      "shell_loss_btu_hr": gm.shell_loss(sol["m_fuel"], sol["t_in"])})
        if r["shell_loss_method"] == "percent" or rec is None:
            break
        new_ua = r["shell_U"] * rec["shell_area_ft2"]
        if key == prev_key and abs(new_ua - gm.shell_ua) < 1e-6 * max(new_ua, 1):
            break
        if k >= 2 and key != prev_key and r["force_drum"] is None:
            # The shell loss of one drum selects the other: take the larger diameter (it carries the higher gas
            # flow), solve with its own shell loss and keep it. The workbook does the same after its pass B and C.
            cand = max(key, prev_key)
            gm.shell_ua = r["shell_U"] * math.pi * cand[0] * cand[1]
            sol = _solve()
            duty = _duty(sol)
            drum_sel = select_drum(duty, rules, r["standard_diameters_ft"], r["standard_lengths_ft"], None, keep=cand)
            outer.append({"iteration": k + 2, "fuel_lb_hr": sol["m_fuel"], "drum": cand,
                          "shell_loss_btu_hr": gm.shell_loss(sol["m_fuel"], sol["t_in"]), "note": "drum alternated"})
            ctx.flag("info", "DRUM_SHELL_LOSS_ALTERNATES",
                     f"The shell loss of the {prev_key[0]:g} x {prev_key[1]:g} ft drum selects the {key[0]:g} x "
                     f"{key[1]:g} ft drum and back. The larger diameter is kept, with its own shell loss.", "drum")
            if not drum_sel["recommended"]["passes"]:
                ctx.flag("warning", "DRUM_ALTERNATE_FAILS", f"The kept {cand[0]:g} x {cand[1]:g} ft drum fails "
                         + ", ".join(drum_sel["recommended"]["failed"]) + " at its own gas flow.", "drum")
            break
        prev_key, gm.shell_ua = key, new_ua
    if drum_sel["recommended"] is None:
        need_area = duty.exhaust_acfm / r["drum_design_velocity_fpm"] / (1 - r["fill_range_pct"][0] / 100)
        need_d = math.sqrt(4 * need_area / math.pi)
        hint = ""
        if need_d > max(r["standard_diameters_ft"]):
            hint = (f" Exhaust {duty.exhaust_acfm:,.0f} ACFM at {r['drum_design_velocity_fpm']:g} FPM needs about "
                    f"{need_d:.1f} ft diameter, above the largest standard {max(r['standard_diameters_ft']):g} ft: raise "
                    f"the inlet temperature (less gas per lb of water), add recycle, or split into two dryers.")
        ctx.flag("violation", "NO_DRUM_PASSES", "No standard drum passes every check. Closest: "
                 + "; ".join(f"{x['size']} fails {', '.join(x['failed'])}" for x in drum_sel["smaller_failing"])
                 + "." + hint, "drum")
        shell_note = "no drum selected: shell loss excluded"
        ctx.flag("warning", "SHELL_LOSS_EXCLUDED", "Shell loss could not be computed without a drum; energy results "
                                                   "exclude it.")
    else:
        shell_note = (f"U {r['shell_U']} x A {drum_sel['recommended']['shell_area_ft2']:.0f} ft2 x (T avg - T amb)"
                      if r["shell_loss_method"] == "UA" else f"{r['shell_loss_pct']}% of burner LHV input")

    m_f, m_dil, t_in, st = sol["m_fuel"], sol["m_dilution"], sol["t_in"], sol["streams"]
    if m_dil < 0:
        ctx.flag("violation", "INLET_TEMP_INFEASIBLE",
                 f"Solved dilution air is negative ({m_dil:,.0f} lb/hr): an inlet temperature of {t_in:,.0f} F needs "
                 f"less air than the {f['excess_air_pct']:g}% excess combustion air already supplies (flame "
                 f"{t_flame:,.0f} F). Lower excess air, raise inlet temperature limit or add recycle.", "rotary")
    if t_in > t_flame:
        ctx.flag("violation", "INLET_ABOVE_FLAME", f"Inlet temperature {t_in:,.0f} F is above the flame temperature "
                                                   f"{t_flame:,.0f} F.")

    # ------------------------------------------------------------ e. losses and energy balance
    lhv = fm["lhv"]
    q_fuel = m_f * lhv
    q_shell = gm.shell_loss(m_f, t_in)
    q_furnace = (1 - f["furnace_efficiency"]) * q_fuel
    q_rec_duct = h_mix_btu(st["recycle"], r["exhaust_temp_F"]) - h_mix_btu(st["recycle"], r["recycle_temp_F"])
    h_air_in = sum(h_mix_btu(st[k], s["ambient_temp_F"]) for k in ("combustion_air", "dilution_air", "leakage_air"))
    fuel_datum_terms = m_f * (c.water_formed_lb * HFG_TRIPLE_BTU_LB
                              + gm.fuel_cp * (f["fuel_temp_F"] - 32))
    evap_vapor_h = mb["evaporation_lb_hr"] * h_vapor_btu_lb(r["exhaust_temp_F"])
    q_stack = h_mix_btu(st["stack"], r["exhaust_temp_F"]) - evap_vapor_h - h_air_in - fuel_datum_terms
    q_leak = h_mix_btu(st["leakage_air"], r["exhaust_temp_F"]) - h_mix_btu(st["leakage_air"], s["ambient_temp_F"])
    uses = {"evaporation": ph["evaporation_btu_hr"], "solids_sensible": ph["solids_sensible_btu_hr"],
            "residual_water_sensible": ph["residual_water_btu_hr"], "stack_loss": q_stack, "shell_loss": q_shell,
            "furnace_loss": q_furnace, "recycle_duct_loss": q_rec_duct}
    uses_total = sum(uses.values())
    # independent closure on the reference state (all streams, both control volumes combined)
    e_in = gm.fuel_in(m_f) + h_air_in + ph["h_feed_btu_hr"] + q_furnace  # gross fuel datum energy
    e_out = h_mix_btu(st["stack"], r["exhaust_temp_F"]) + ph["h_product_btu_hr"] + q_shell + q_rec_duct + q_furnace
    e_closure = (e_in - e_out) / e_in * 100
    breakdown_closure = (q_fuel - uses_total) / q_fuel * 100
    # overall mass closure: fresh feed + fuel + all air = product + stack + ash
    air_mass = sum(_mass(st[k]) for k in ("combustion_air", "dilution_air", "leakage_air"))
    m_in = mb["wet_feed_lb_hr"] + m_f + air_mass
    m_out = mb["product_lb_hr"] + _mass(st["stack"]) + m_f * c.ash_lb
    m_closure = (m_in - m_out) / m_in * 100

    # ------------------------------------------------------------ exhaust psychrometrics
    ex = st["dryer_exhaust"]
    n_ex = _mol(ex)
    pw = ex["H2O"] / n_ex * p_site
    t_dew = dew_point_f(pw)
    ps = psat_psia(r["exhaust_temp_F"])
    w_ex = ex["H2O"] * MW["H2O"] / (_mass(ex) - ex["H2O"] * MW["H2O"])
    dry_mw = (_mass(ex) - ex["H2O"] * MW["H2O"]) / (n_ex - ex["H2O"])
    w_sat = MW["H2O"] / dry_mw * ps / (p_site - ps) if ps < p_site else float("inf")
    margin = r["exhaust_temp_F"] - t_dew
    t_wb_inlet = adiabatic_saturation_f(st["dryer_inlet"], t_in, p_site)
    if margin < 0:
        ctx.flag("violation", "EXHAUST_BELOW_DEW_POINT", f"Exhaust {r['exhaust_temp_F']:g} F is below its dew point "
                                                         f"{t_dew:.0f} F: condensation in the drum and collector.")
    elif margin < r["min_dew_point_margin_F"]:
        ctx.flag("warning", "DEW_POINT_MARGIN", f"Exhaust is only {margin:.0f} F above its dew point {t_dew:.0f} F "
                                                f"(minimum {r['min_dew_point_margin_F']:g} F); risk of condensation "
                                                f"in the cyclone, baghouse and stack.")

    # ------------------------------------------------------------ f. results
    btu_lb = q_fuel / mb["evaporation_lb_hr"]
    lo, hi = TYPICAL_SPECIFIC_HEAT
    if not lo <= btu_lb <= hi:
        drivers = sorted(((k, v) for k, v in uses.items()), key=lambda kv: -kv[1])[:3]
        ctx.flag("warning" if btu_lb > hi else "info", "SPECIFIC_HEAT_RANGE",
                 f"{btu_lb:,.0f} BTU/lb water is outside the typical rotary range {lo:,.0f} to {hi:,.0f}. Largest heat "
                 f"uses: " + ", ".join(f"{k.replace('_', ' ')} {v / mb['evaporation_lb_hr']:,.0f} BTU/lb" for k, v in
                                       drivers) + f". Inlet {t_in:,.0f} F, exhaust {r['exhaust_temp_F']:g} F, furnace "
                 f"efficiency {f['furnace_efficiency']:.0%}.")
    if p["product_temp_F"] > p["max_product_temp_F"]:
        ctx.flag("violation", "PRODUCT_TEMP", f"Product temperature {p['product_temp_F']:g} F exceeds the material "
                                              f"limit {p['max_product_temp_F']:g} F.", "process.product_temp_F")
    if p["product_temp_F"] > r["exhaust_temp_F"]:
        ctx.flag("warning", "PRODUCT_ABOVE_EXHAUST",
                 f"Product {p['product_temp_F']:g} F is hotter than the exhaust gas {r['exhaust_temp_F']:g} F. In a "
                 f"co-current drum the product leaves near the outlet gas temperature; this is only consistent if "
                 f"the exhaust temperature is measured downstream after duct and collector cooling. Confirm the "
                 f"measuring point.", "process.product_temp_F")
    if p["fire_risk"] == "high" and t_in > FIRE_RISK_INLET_F:
        ctx.flag("warning", "FIRE_RISK_INLET", f"High fire risk material with a {t_in:,.0f} F inlet, above the "
                                               f"{FIRE_RISK_INLET_F:,.0f} F MCE limit (Jason 2026-11-07: 900 to 1,000 F "
                                               f"is fine): confirm spark detection, fire bypass and explosion venting.")
    if f["furnace_efficiency"] < 0.95 and fm["kind"] == "gas":
        ctx.flag("info", "FURNACE_EFF_GAS", f"Furnace efficiency {f['furnace_efficiency']:.0%} now covers only "
                                            f"unburned fuel and radiation (stack loss is computed). For gas firing "
                                            f"that is conservative; 97 to 99% is more usual. MCE to confirm.")

    burner_op = q_fuel / 1e6
    burner_hhv = m_f * fm["hhv"] / 1e6
    design = burner_op * r["burner_design_margin"]
    fuel_vol = {}
    if fm["kind"] == "gas":
        scfh = m_f * fm["vol"]["scf_per_lb"]
        fuel_vol = {"scfh": q(scfh, "SCFH"), "basis": "70 F, 29.92 in. Hg"}
    elif fm["kind"] == "liquid":
        fuel_vol = {"gal_hr": q(m_f / f["density"] * 7.48052, "gal/hr"), "ft3_hr": q(m_f / f["density"], "ft3/hr")}
    else:
        fuel_vol = {"ft3_hr": q(m_f / f["density"], "ft3/hr")}
    hours = p["annual_hours"]
    annual = {"hours": hours, "fuel_tons_yr": q(m_f * hours / LB_PER_TON, "tons/yr"),
              "fuel_mmbtu_yr_lhv": q(burner_op * hours, "MMBtu/yr"),
              "fuel_mmbtu_yr_hhv": q(burner_hhv * hours, "MMBtu/yr"),
              "product_tons_yr": q(mb["product_lb_hr"] * hours / LB_PER_TON, "tons/yr")}
    if fm["kind"] == "gas":
        annual["fuel_mmscf_yr"] = round(m_f * fm["vol"]["scf_per_lb"] * hours / 1e6, 3)
    self_fuel = None
    if self_fueled:
        net = mb["product_lb_hr"] - m_f
        self_fuel = {"product_lb_hr": q(mb["product_lb_hr"], "lb/hr"), "fuel_lb_hr": q(m_f, "lb/hr"),
                     "net_product_lb_hr": q(net, "lb/hr"), "fraction_of_product_burned": round(m_f / mb["product_lb_hr"], 4),
                     "net_product_tons_yr": q(net * hours / LB_PER_TON, "tons/yr"),
                     "note": "Net = dried product minus the fuel burned, when the burner fires the dried product."}
        if net < 0:
            ctx.flag("warning", "NOT_SELF_FUELING", f"The dryer burns more fuel ({m_f:,.0f} lb/hr) than it produces "
                                                    f"({mb['product_lb_hr']:,.0f} lb/hr).")

    # ------------------------------------------------------------ emissions (potential to emit)
    stack = st["stack"]
    stack_dscfm = scfm_from_lbmol_hr(_mol(stack) - stack.get("H2O", 0.0))
    emis = em.estimate(f["fuel"], m_f, fm["hhv"], c.products_lbmol.get("CO2", 0.0) * MW["CO2"],
                       c.products_lbmol.get("SO2", 0.0) * MW["SO2"], stack_dscfm, mb["solids_lb_hr"],
                       p["annual_hours"], a["collector_outlet_gr_dscf"], p["product_voc_lb_odt"])
    for k in emis["major_source_flags"]:
        ctx.flag("warning", "PTE_MAJOR_SOURCE", f"{k} potential to emit {emis['pollutants'][k]['pte_tpy']:,.0f} tpy is at "
                                                f"or above {em.MAJOR_SOURCE_TPY:g} tpy: Title V major-source review is "
                                                f"likely. Check state and nonattainment thresholds.", "emissions")
    if not emis["product_voc_estimated"]:
        ctx.flag("info", "VOC_PRODUCT_NOT_ESTIMATED", "VOC released by the product is not included (factor 0 lb/ODT). "
                                                      "For wood it can set the permit; enter a factor from AP-42 "
                                                      "Ch.10.6 or a stack test.", "emissions")
    emis_out = {"stack_dscfm": q(stack_dscfm, "SCFM"), "fuel_mmbtu_hr_hhv": q(emis["fuel_mmbtu_hr_hhv"], "MMBtu/hr"),
                "burner_pm_lb_hr": q(emis["burner_pm_lb_hr"], "lb/hr"), "factor_source": emis["factor_source"],
                "pollutants": {k: {"lb_hr": q(r["lb_hr"], "lb/hr"), "tpy": q(r["tpy"], "tons/yr"),
                                   "pte_tpy": q(r["pte_tpy"], "tons/yr"), "basis": r["basis"]}
                               for k, r in emis["pollutants"].items()},
                "major_source_flags": emis["major_source_flags"], "notes": emis["notes"]}

    # ------------------------------------------------------------ h. air system
    dv = a["duct_velocity_fpm"]
    inc = a["duct_size_increment_in"]
    rho_b = p["bulk_density_dry"]
    v_convey = a["convey_velocity_coeff"] * math.sqrt(rho_b) * a["convey_velocity_factor"]
    acfm_in = acfm_from_lbmol_hr(_mol(st["dryer_inlet"]), t_in, p_site)
    acfm_ex = acfm_from_lbmol_hr(n_ex, r["exhaust_temp_F"], p_site)
    acfm_stack = acfm_from_lbmol_hr(_mol(st["stack"]), r["exhaust_temp_F"], p_site)
    ducts = {"furnace_to_drum": _std_duct(acfm_in, dv, inc),
             "drum_to_cyclone": _std_duct(acfm_ex, dv, inc, v_convey if a["product_air_conveyed"] else None),
             "stack": _std_duct(acfm_stack, dv, inc)}
    if r["recycle_fraction"] > 0:
        ducts["recycle"] = _std_duct(acfm_from_lbmol_hr(_mol(st["recycle"]), r["recycle_temp_F"], p_site), dv, inc)
    gas_ratio = _mass(ex) / mb["product_lb_hr"]
    convey_ok = gas_ratio >= a["min_gas_to_product"]
    v_dc = ducts["drum_to_cyclone"]["velocity_fpm"]["value"]
    if a["product_air_conveyed"]:
        if not convey_ok:
            ctx.flag("warning", "CONVEY_GAS_RATIO", f"Only {gas_ratio:.1f} lb gas per lb product; at least "
                                                    f"{a['min_gas_to_product']:g} is needed to air convey the product.")
        if v_dc < v_convey:
            ctx.flag("warning", "CONVEY_VELOCITY", f"Drum-to-cyclone duct velocity {v_dc:,.0f} FPM is below the "
                                                   f"{v_convey:,.0f} FPM minimum conveying velocity.")
    p_fan = p_site + a["fan_inlet_static_in_wc"] * IN_WC_TO_PSI
    fan_acfm = acfm_from_lbmol_hr(n_ex, r["exhaust_temp_F"], p_fan)
    rho_op = _mass(ex) / 60.0 / fan_acfm
    rho_cold = gas_density_lb_ft3(MW_AIR * (1 + s["humidity_lb_lb"]) / (1 + s["humidity_lb_lb"] * MW_AIR / MW["H2O"]),
                                  s["ambient_temp_F"], p_site)
    sp = a["fan_sp_in_wc"]
    sp_op = sp * rho_op / AMCA_STD_AIR if a["fan_sp_basis"] == "standard_air" else sp
    sp_std = sp_op * AMCA_STD_AIR / rho_op
    sp_cold = sp_std * rho_cold / AMCA_STD_AIR
    eta = a["fan_efficiency"]
    bhp_op = fan_acfm * sp_op / (6356 * eta)
    bhp_cold = fan_acfm * sp_cold / (6356 * eta)
    motor_basis = bhp_op if a["fan_vfd_or_damper"] else max(bhp_op, bhp_cold)
    motor = _nema(motor_basis)
    sheet_hp = fan_acfm * 18 * 5.2 / 33000 * 1.75
    if not a["fan_vfd_or_damper"]:
        ctx.flag("info", "FAN_COLD_START", f"No VFD or damper: motor sized for cold start ({bhp_cold:,.0f} BHP at "
                                           f"{rho_cold:.4f} lb/ft3) not hot operation ({bhp_op:,.0f} BHP).")
    fan = {"acfm": q(fan_acfm, "ACFM"), "inlet_temp_F": q(r["exhaust_temp_F"], "F"),
           "gas_density_lb_ft3": q(rho_op, "lb/ft3"), "sp_operating_in_wc": q(sp_op, "in. w.c."),
           "sp_standard_air_in_wc": q(sp_std, "in. w.c."), "sp_basis_entered": a["fan_sp_basis"],
           "efficiency": eta, "bhp_operating": q(bhp_op, "HP"), "bhp_cold_start": q(bhp_cold, "HP"),
           "cold_air_density_lb_ft3": q(rho_cold, "lb/ft3"), "motor_hp_nema": motor,
           "motor_basis": "hot operation (VFD or damper)" if a["fan_vfd_or_damper"] else "cold start",
           "sheet_method_hp_for_comparison": q(sheet_hp, "HP"),
           "formula": "BHP = ACFM x SP / (6356 x efficiency); SP corrected by gas density / 0.075 (AMCA 210 "
                      "standard air)"}

    # ------------------------------------------------------------ i. feed and discharge handoffs
    dtf = r["design_throughput_factor"]
    infeed_ft3 = mb["drum_infeed_lb_hr"] / p["bulk_density_wet"]
    disch_ft3 = mb["drum_discharge_lb_hr"] / p["bulk_density_dry"]
    handoffs = {
        "cyclone": {"calculator": "cyclone", "inlet_acfm": q(acfm_ex, "ACFM"), "inlet_temp_F": q(r["exhaust_temp_F"], "F"),
                    "gas_lb_hr": q(_mass(ex), "lb/hr"), "gas_density_lb_ft3": q(rho_op, "lb/ft3"),
                    "dew_point_F": q(t_dew, "F"), "solids_load_lb_hr": q(mb["drum_discharge_lb_hr"] if a["product_air_conveyed"] else 0.0, "lb/hr"),
                    "particle_size_in": q(p["particle_size_in"], "in"), "bulk_density_lb_ft3": q(rho_b, "lb/ft3")},
        "baghouse": {"calculator": "baghouse", "inlet_acfm": q(acfm_ex, "ACFM"), "inlet_temp_F": q(r["exhaust_temp_F"], "F"),
                     "dew_point_F": q(t_dew, "F"), "dew_point_margin_F": q(margin, "dF"),
                     "h2o_vol_pct": round(ex["H2O"] / n_ex * 100, 2), "note": "Dust load = cyclone carry-over (from the cyclone calculator)."},
        "fan": {"calculator": "fan", "acfm": q(fan_acfm, "ACFM"), "temp_F": q(r["exhaust_temp_F"], "F"),
                "density_lb_ft3": q(rho_op, "lb/ft3"), "sp_in_wc": q(sp_op, "in. w.c."), "elevation_ft": s["elevation_ft"]},
        "infeed_airlock": {"calculator": "airlock", "lb_hr_design": q(mb["drum_infeed_lb_hr"] * dtf, "lb/hr"),
                           "ft3_hr_design": q(infeed_ft3 * dtf, "ft3/hr"), "bulk_density_lb_ft3": q(p["bulk_density_wet"], "lb/ft3"),
                           "mc_wb_pct": round(mb["mixed_infeed_mc_wb"], 2), "temp_F": q(p["feed_temp_F"], "F")},
        "infeed_screw": {"calculator": "screw_conveyor", "lb_hr_design": q(mb["drum_infeed_lb_hr"] * dtf, "lb/hr"),
                         "tph_design": round(mb["drum_infeed_lb_hr"] * dtf / LB_PER_TON, 3),
                         "ft3_hr_design": q(infeed_ft3 * dtf, "ft3/hr"), "bulk_density_lb_ft3": q(p["bulk_density_wet"], "lb/ft3")},
        "discharge_airlock": {"calculator": "airlock", "lb_hr_design": q(mb["drum_discharge_lb_hr"] * dtf, "lb/hr"),
                              "ft3_hr_design": q(disch_ft3 * dtf, "ft3/hr"), "bulk_density_lb_ft3": q(rho_b, "lb/ft3"),
                              "temp_F": q(p["product_temp_F"], "F"), "location": "under the product cyclone" if a["product_air_conveyed"] else "drum discharge"},
        "discharge_screw": {"calculator": "screw_conveyor", "lb_hr_design": q(mb["drum_discharge_lb_hr"] * dtf, "lb/hr"),
                            "tph_design": round(mb["drum_discharge_lb_hr"] * dtf / LB_PER_TON, 3),
                            "ft3_hr_design": q(disch_ft3 * dtf, "ft3/hr"), "bulk_density_lb_ft3": q(rho_b, "lb/ft3"),
                            "temp_F": q(p["product_temp_F"], "F")},
        "design_throughput_factor": dtf,
    }
    if fm["kind"] == "solid":
        handoffs["fuel_feed"] = {"calculator": "screw_conveyor / airlock", "lb_hr_design": q(m_f * dtf, "lb/hr"),
                                 "ft3_hr_design": q(m_f * dtf / f["density"], "ft3/hr"),
                                 "bulk_density_lb_ft3": q(f["density"], "lb/ft3")}

    # ------------------------------------------------------------ assemble output
    st_out = {k: stream_summary(k, v, {"combustion_air": s["ambient_temp_F"], "dilution_air": s["ambient_temp_F"],
                                       "leakage_air": s["ambient_temp_F"], "fuel_gas": t_flame,
                                       "dryer_inlet": t_in, "dryer_exhaust": r["exhaust_temp_F"],
                                       "recycle": r["recycle_temp_F"], "stack": r["exhaust_temp_F"]}[k], p_site)
              for k, v in st.items()}
    rec = drum_sel["recommended"]

    def drum_out(d: dict | None) -> dict | None:
        if d is None:
            return None
        return {"size": f"{d['diameter_ft']:g} ft dia x {d['length_ft']:g} ft long",
                "diameter_ft": q(d["diameter_ft"], "ft"), "length_ft": q(d["length_ft"], "ft"),
                "volume_ft3": q(d["volume_ft3"], "ft3"), "shell_area_ft2": q(d["shell_area_ft2"], "ft2"),
                "ver": q(d["ver_lb_hr_ft3"], "lb H2O/hr-ft3"), "ver_design_range": r["ver_range"],
                "gas_velocity_fpm": q(d["velocity_fpm"], "FPM"), "entrainment_limit_fpm": q(d["entrainment_limit_fpm"], "FPM"),
                "design_velocity_fpm": q(r["drum_design_velocity_fpm"], "FPM"),
                "residence_min": round(d["residence_min"], 2), "residence_target_min": d["residence_target_min"],
                "fill_pct": round(d["fill_pct"], 2),
                "holdup_lb": q(d["holdup_lb"], "lb"), "slope_in_per_ft": round(d["slope_in_per_ft"], 4),
                "rpm": round(d["rpm"], 2), "critical_rpm": round(d["critical_rpm"], 2),
                "pct_critical": d["pct_critical"], "peripheral_fpm": q(d["peripheral_fpm"], "FPM"),
                "l_over_d": round(d["l_over_d"], 2), "fm_gas_drag_term_min": round(d["fm_gas_term_min"], 3),
                "under_ver_min": d["under_ver_min"],
                "checks": {k: {"value": round(v["value"], 4), "limit": v["limit"], "pass": v["pass"],
                               "hard": v.get("hard", True)}
                           for k, v in d["checks"].items()},
                "passes_all_checks": d["passes"], "failed_checks": d["failed"],
                "advisory_checks_exceeded": d["advisory_failed"]}

    drum_block = {"recommended": drum_out(rec), "next_size_up": drum_out(drum_sel["next_size_up"]),
                  "smaller_alternate": drum_out(drum_sel.get("smaller_alternate")),
                  "mode": drum_sel["mode"], "candidates_checked": drum_sel.get("candidates_checked"),
                  "candidates_passing": drum_sel.get("candidates_passing"),
                  "smaller_failing": drum_sel["smaller_failing"],
                  "terminal_velocity_ft_s": q(drum_sel["terminal_velocity_ft_s"], "ft/s"),
                  "method": drum_sel["method"], "standard_sizes_source": "presets.STANDARD_DRUM_* (placeholder grid)",
                  "outer_iterations": outer}
    if rec and rec["fm_gas_term_min"] > rec["residence_min"]:
        ctx.flag("needs_verification", "FM_GAS_DRAG", f"Friedman-Marshall gas drag term ({rec['fm_gas_term_min']:.1f} "
                                                      f"min) exceeds the target residence time: the drum is "
                                                      f"partly air conveying, which is outside the correlation's data. "
                                                      f"Confirm residence time and slope with MCE test data.", "drum")
    if rec and rec["advisory_failed"]:
        ctx.flag("info", "DRUM_CARRYOVER", f"Drum gas velocity {rec['velocity_fpm']:.0f} FPM is above "
                                           f"{r['entrainment_fraction']:g} x the design particle terminal velocity "
                                           f"({rec['entrainment_limit_fpm']:.0f} FPM). The product is air conveyed out of "
                                           f"the drum, so carry-over is the intended discharge path; the MCE design "
                                           f"velocity governs. Entrainment is a hard check when product_air_conveyed is "
                                           f"false.", "drum")
    if rec and rec["length_ft"] > STANDARD_DRUM_MAX_NORMAL_LENGTH_FT:
        ctx.flag("warning", "DRUM_LONG", f"Drum length {rec['length_ft']:g} ft is over the normal "
                                         f"{STANDARD_DRUM_MAX_NORMAL_LENGTH_FT} ft maximum (up to 80 ft is possible).",
                 "drum")
    if rec and rec["above_target_velocity"]:
        ctx.flag("warning", "DRUM_VELOCITY_OVER_TARGET", f"Drum gas velocity {rec['velocity_fpm']:.0f} FPM is above the "
                                                         f"{r['drum_design_velocity_fpm']:g} FPM target: wet material "
                                                         f"may start air conveying.", "drum")
    alt = drum_sel.get("smaller_alternate")
    if alt:
        ctx.flag("info", "DRUM_SMALLER_ALTERNATE", f"A smaller drum, {alt['diameter_ft']:g} x {alt['length_ft']:g} ft, "
                                                   f"passes at {alt['velocity_fpm']:.0f} FPM, slightly above the "
                                                   f"{r['drum_design_velocity_fpm']:g} FPM target.", "drum")
    if rec and rec["under_ver_min"]:
        ctx.flag("info", "VER_BELOW_RANGE", f"VER {rec['ver_lb_hr_ft3']:.2f} is below the design range "
                                            f"{r['ver_range'][0]:g}: another check (velocity, fill or L/D) governs "
                                            f"the drum size.", "drum")
    if rec and r["force_drum"] and not rec["passes"]:
        ctx.flag("violation", "FORCED_DRUM_FAILS", f"Forced drum fails: {', '.join(rec['failed'])}.", "drum")

    out = {
        "calculator": CALC_VERSION, "dryer_type": "rotary", "material_label": mat["label"],
        "reference_state": REFERENCE_STATE,
        "site": {"barometric_psia": q(p_site, "psia"), "elevation_ft": q(s["elevation_ft"], "ft"),
                 "standard_conditions": "SCFM at 70 F, 29.92 in. Hg; ACFM at actual T and site pressure"},
        "mass_balance": {
            "wet_feed_lb_hr": q(mb["wet_feed_lb_hr"], "lb/hr"), "wet_feed_tph": round(mb["wet_feed_lb_hr"] / LB_PER_TON, 4),
            "solids_lb_hr": q(mb["solids_lb_hr"], "lb/hr"), "water_in_lb_hr": q(mb["water_in_lb_hr"], "lb/hr"),
            "product_lb_hr": q(mb["product_lb_hr"], "lb/hr"), "product_tph": round(mb["product_lb_hr"] / LB_PER_TON, 4),
            "water_out_lb_hr": q(mb["water_out_lb_hr"], "lb/hr"), "evaporation_lb_hr": q(mb["evaporation_lb_hr"], "lb/hr"),
            "backmix_lb_hr": q(mb["backmix_lb_hr"], "lb/hr"), "drum_infeed_lb_hr": q(mb["drum_infeed_lb_hr"], "lb/hr"),
            "drum_discharge_lb_hr": q(mb["drum_discharge_lb_hr"], "lb/hr"),
            "mixed_infeed_mc_wb_pct": round(mb["mixed_infeed_mc_wb"], 3),
            "infeed_mc_wb_pct": p["infeed_mc_wb"], "infeed_mc_db_pct": round(mb["infeed_mc_db"], 3),
            "target_mc_wb_pct": p["target_mc_wb"], "target_mc_db_pct": round(mb["target_mc_db"], 3),
            "drum_closure_pct": mb["closure_pct"], "overall_closure_pct": m_closure,
        },
        "product_heat": {
            "solids_sensible_btu_hr": q(ph["solids_sensible_btu_hr"], "BTU/hr"),
            "residual_water_btu_hr": q(ph["residual_water_btu_hr"], "BTU/hr"),
            "evaporation_btu_hr": q(ph["evaporation_btu_hr"], "BTU/hr"),
            "total_mmbtu_hr": q(ph["total_btu_hr"] / 1e6, "MMBtu/hr"),
            "per_lb_water": q(ph["per_lb_water"], "BTU/lb water"),
            "evaporation_btu_per_lb": q(ph["evaporation_btu_per_lb"], "BTU/lb"),
            "evaporation_btu_per_lb_sheet_method": q(ph["evaporation_btu_per_lb_sheet_method"], "BTU/lb",
                                                     "212 - T_feed + 970.3 + 0.455 (T_exh - 212), for comparison"),
        },
        "combustion": {
            "fuel": f["fuel"], "fuel_label": FUELS[f["fuel"]]["label"],
            "lhv_as_fired_btu_lb": q(fm["lhv"], "BTU/lb"), "hhv_as_fired_btu_lb": q(fm["hhv"], "BTU/lb"),
            "lhv_from_analysis_btu_lb": q(c.lhv_computed_btu_lb, "BTU/lb"),
            "hhv_from_analysis_btu_lb": q(c.hhv_computed_btu_lb, "BTU/lb"),
            "lhv_basis_used": f["heating_value_source"],
            "stoich_air_lb_per_lb_fuel": round(c.stoich_air_lb, 4),
            "stoich_air_mass_formula_lb_per_lb": round(c.stoich_air_mass_formula_lb, 4) if c.stoich_air_mass_formula_lb else None,
            "excess_air_pct": f["excess_air_pct"], "air_to_stoich_ratio": round(1 + f["excess_air_pct"] / 100, 4),
            "combustion_air_lb_per_lb_fuel": round(c.stoich_air_lb * (1 + f["excess_air_pct"] / 100), 4),
            "products_lb_per_lb_fuel": round(_mass(gm.flue_per_lb), 4),
            "water_formed_lb_per_lb_fuel": round(c.water_formed_lb, 4),
            "ash_lb_per_lb_fuel": round(c.ash_lb, 5),
            "products_lb_hr": {k: q(v * m_f * MW[k], "lb/hr") for k, v in gm.flue_per_lb.items() if v},
            "flame_temp_F": q(t_flame, "F"), "furnace_efficiency": f["furnace_efficiency"],
            "furnace_efficiency_covers": "unburned fuel and furnace/burner radiation only (stack loss is computed)",
            "notes": c.notes,
        },
        "gas_balance": {
            "mode": r["gas_mode"], "inlet_temp_F": q(t_in, "F"), "exhaust_temp_F": q(r["exhaust_temp_F"], "F"),
            "dilution_air_lb_hr": q(m_dil, "lb/hr"),
            "solver": {"method": "damped Newton, finite-difference Jacobian", "iterations": sol["iterations"],
                       "max_scaled_residual": sol["max_scaled_residual"],
                       "residual_furnace_btu_hr": sol["residual_furnace_btu_hr"],
                       "residual_drum_btu_hr": sol["residual_drum_btu_hr"], "tolerance": "1e-9 of product heat"},
            "streams": st_out,
            "exhaust": {"humidity_lb_lb_dry_gas": round(w_ex, 5), "dew_point_F": q(t_dew, "F"),
                        "dew_point_margin_F": q(margin, "dF"), "h2o_partial_pressure_psia": q(pw, "psia"),
                        "relative_humidity_pct": round(pw / ps * 100, 3),
                        "pct_saturation": round(w_ex / w_sat * 100, 3) if math.isfinite(w_sat) else 0.0,
                        "inlet_gas_adiabatic_saturation_F": q(t_wb_inlet, "F"),
                        "gas_to_product_lb_lb": round(gas_ratio, 3)},
        },
        "losses": {"shell_btu_hr": q(q_shell, "BTU/hr"), "shell_method": shell_note,
                   "leakage_air_lb_hr": q(_mass(st["leakage_air"]), "lb/hr"),
                   "leakage_heat_btu_hr": q(q_leak, "BTU/hr", "heating leak air from ambient to exhaust (part of stack loss)"),
                   "furnace_btu_hr": q(q_furnace, "BTU/hr"), "recycle_duct_btu_hr": q(q_rec_duct, "BTU/hr"),
                   "stack_btu_hr": q(q_stack, "BTU/hr")},
        "energy_balance": {
            "basis": "LHV as fired; uses relative to feed and ambient air",
            "fuel_input_btu_hr": q(q_fuel, "BTU/hr"),
            "uses_btu_hr": {k: q(v, "BTU/hr") for k, v in uses.items()},
            "uses_pct": {k: round(v / q_fuel * 100, 3) for k, v in uses.items()},
            "uses_btu_per_lb_water": {k: round(v / mb["evaporation_lb_hr"], 1) for k, v in uses.items()},
            "breakdown_closure_pct": breakdown_closure,
            "reference_state_in_btu_hr": q(e_in, "BTU/hr"), "reference_state_out_btu_hr": q(e_out, "BTU/hr"),
            "closure_pct": e_closure,
        },
        "results": {
            "burner_operating_mmbtu_hr_lhv": q(burner_op, "MMBtu/hr"),
            "burner_operating_mmbtu_hr_hhv": q(burner_hhv, "MMBtu/hr"),
            "burner_design_mmbtu_hr_lhv": q(design, "MMBtu/hr"), "burner_design_margin": r["burner_design_margin"],
            "fuel_lb_hr": q(m_f, "lb/hr"), "fuel_volume": fuel_vol,
            "btu_per_lb_water_lhv": q(btu_lb, "BTU/lb water"),
            "btu_per_lb_water_hhv": q(m_f * fm["hhv"] / mb["evaporation_lb_hr"], "BTU/lb water"),
            "typical_range_btu_per_lb": list(TYPICAL_SPECIFIC_HEAT),
            "annual": annual, "self_fueled_balance": self_fuel,
        },
        "drum": drum_block,
        "air_system": {"ducts": ducts, "duct_target_velocity_fpm": dv,
                       "conveying": {"product_air_conveyed": a["product_air_conveyed"],
                                     "gas_to_product_lb_lb": round(gas_ratio, 3), "min_required": a["min_gas_to_product"],
                                     "min_convey_velocity_fpm": q(v_convey, "FPM"),
                                     "formula": f"{a['convey_velocity_coeff']:g} x sqrt(bulk density) x "
                                                f"{a['convey_velocity_factor']:g}",
                                     "pass": bool(convey_ok and v_dc >= v_convey) if a["product_air_conveyed"] else None},
                       "fan": fan},
        "handoffs": handoffs,
        "emissions": emis_out,
        "trace": ctx.trace,
    }
    return {"outputs": out, "flags": ctx.flags}
