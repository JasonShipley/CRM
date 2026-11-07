"""Rotary drum sizing checks and standard-drum selection (replaces SHEET FLOW Q23:U28).

Checks per candidate drum (D x L, ft):
1. Volumetric evaporation rate VER = evaporation / drum volume, within the material range.
2. Gas velocity through the drum free area at exhaust conditions, against
   (a) the MCE target drum velocity (350 FPM; drums up to the tolerance above it are offered only as a smaller
   alternate, never as the recommendation) and (b) entrainment_fraction x terminal velocity of the
   design particle (Haider & Levenspiel, Powder Technology 58 (1989) 63-70, non-spherical drag).
3. Residence time (at least the target; longer when needed to reach the minimum fill) from Friedman & Marshall, Chem. Eng. Prog. 45 (1949) 482-493 and 573-588,
   as given in Perry's Chemical Engineers' Handbook (Sec. 12, rotary dryers):
       theta = 0.23 L / (S N^0.9 D)  -/+  0.6 B L G / F         (min; - co-current, + counter-current)
       B = 5 Dp^-0.5 (Dp weight-average particle size, microns), G gas and F dry solids mass
       velocity lb/(hr ft2), L and D ft, N rpm, S slope ft/ft.
   The required slope for the target residence time is solved from it at the design speed.
4. Holdup (% fill) = residence x average solids-plus-water mass flow / bulk density / drum volume.
5. Speed as % of critical speed, N_c = (60 / 2 pi) sqrt(2 g / D) = 76.6 / sqrt(D) rpm.
6. Slope within the allowed range; L/D within the allowed range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .properties import air_viscosity_lb_ft_s
from .solver import brent
from .units import G_FT_S2


def critical_speed_rpm(d_ft: float) -> float:
    return 60.0 / (2 * math.pi) * math.sqrt(2 * G_FT_S2 / d_ft)


def haider_levenspiel_cd(re: float, phi: float) -> float:
    a = math.exp(2.3288 - 6.4581 * phi + 2.4486 * phi ** 2)
    b = 0.0964 + 0.5565 * phi
    c = math.exp(4.905 - 13.8944 * phi + 18.4222 * phi ** 2 - 10.2599 * phi ** 3)
    d = math.exp(1.4681 + 12.2584 * phi - 20.7322 * phi ** 2 + 15.8855 * phi ** 3)
    return 24.0 / re * (1 + a * re ** b) + c / (1 + d / re)


def terminal_velocity_ft_s(d_in: float, rho_p: float, rho_g: float, mu_lb_ft_s: float, phi: float) -> float:
    """Terminal settling velocity of the volume-equivalent sphere diameter d (in)."""
    d = d_in / 12.0

    def resid(u: float) -> float:
        re = max(rho_g * u * d / mu_lb_ft_s, 1e-12)
        return u - math.sqrt(4 * G_FT_S2 * d * (rho_p - rho_g) / (3 * haider_levenspiel_cd(re, phi) * rho_g))

    return brent(resid, 1e-6, 500.0)


@dataclass
class DrumDuty:
    evap_lb_hr: float
    exhaust_acfm: float
    gas_in_lb_hr: float
    gas_out_lb_hr: float
    solids_lb_hr: float  # bone dry through the drum (fresh + backmix)
    wet_in_lb_hr: float
    drum_out_lb_hr: float
    rho_bulk_wet: float
    rho_bulk_dry: float
    particle_in: float
    particle_density: float
    sphericity: float
    gas_density_exhaust: float
    exhaust_temp_F: float


@dataclass
class DrumRules:
    ver_range: list[float]
    design_velocity_fpm: float
    entrainment_fraction: float
    residence_min: float
    fill_range_pct: list[float]
    crit_pct: float
    crit_range_pct: list[float]
    slope_range_in_ft: list[float]
    ld_range: list[float]
    co_current: bool = True
    velocity_tolerance_pct: float = 0.0  # drums up to target x (1 + tol) pass, but are only offered as alternates
    entrainment_hard: bool = True  # False when the product is air conveyed out of the drum (carry-over is intended)


def check_drum(d: float, length: float, duty: DrumDuty, rules: DrumRules, ut_ft_s: float) -> dict:
    area = math.pi * d * d / 4
    vol = area * length
    nc = critical_speed_rpm(d)
    n = rules.crit_pct / 100 * nc
    dp_um = duty.particle_in * 25400.0
    b = 5.0 * dp_um ** -0.5
    g = 0.5 * (duty.gas_in_lb_hr + duty.gas_out_lb_hr) / area
    fdry = duty.solids_lb_hr / area
    gas_term = 0.6 * b * length * g / fdry
    flow_avg = 0.5 * (duty.wet_in_lb_hr + duty.drum_out_lb_hr) / 60.0  # lb/min
    rho_avg = 0.5 * (duty.rho_bulk_wet + duty.rho_bulk_dry)
    # residence target is a minimum; a drum larger than the target needs runs longer at the minimum fill
    theta_fill_min = rules.fill_range_pct[0] / 100 * vol * rho_avg / flow_avg
    theta = max(rules.residence_min, theta_fill_min)
    denom = theta + gas_term if rules.co_current else theta - gas_term
    slope = 0.23 * length / (n ** 0.9 * d * denom) if denom > 0 else float("inf")  # ft/ft
    slope_in_ft = slope * 12
    holdup_lb = flow_avg * theta
    fill = holdup_lb / rho_avg / vol * 100
    free_area = area * (1 - min(fill, 50.0) / 100)
    vel_fpm = duty.exhaust_acfm / free_area
    ent_limit_fpm = rules.entrainment_fraction * ut_ft_s * 60
    ver = duty.evap_lb_hr / vol
    ld = length / d
    checks = {
        "ver": {"value": ver, "limit": f"<= {rules.ver_range[1]}", "pass": ver <= rules.ver_range[1] + 1e-9},
        "drum_velocity": {"value": vel_fpm,
                          "limit": f"target {rules.design_velocity_fpm:g} FPM (max "
                                   f"{rules.design_velocity_fpm * (1 + rules.velocity_tolerance_pct / 100):.0f})",
                          "pass": vel_fpm <= rules.design_velocity_fpm * (1 + rules.velocity_tolerance_pct / 100) + 1e-9},
        "entrainment": {"value": vel_fpm, "limit": f"<= {ent_limit_fpm:.0f} FPM", "pass": vel_fpm <= ent_limit_fpm,
                        "hard": rules.entrainment_hard},
        "fill": {"value": fill, "limit": f"{rules.fill_range_pct[0]:g} to {rules.fill_range_pct[1]:g} %",
                 "pass": rules.fill_range_pct[0] - 1e-9 <= fill <= rules.fill_range_pct[1] + 1e-9},
        "slope": {"value": slope_in_ft, "limit": f"{rules.slope_range_in_ft[0]:g} to {rules.slope_range_in_ft[1]:g} in/ft",
                  "pass": rules.slope_range_in_ft[0] - 1e-9 <= slope_in_ft <= rules.slope_range_in_ft[1] + 1e-9},
        "speed": {"value": rules.crit_pct, "limit": f"{rules.crit_range_pct[0]:g} to {rules.crit_range_pct[1]:g} % crit",
                  "pass": rules.crit_range_pct[0] <= rules.crit_pct <= rules.crit_range_pct[1]},
        "l_over_d": {"value": ld, "limit": f"{rules.ld_range[0]:g} to {rules.ld_range[1]:g}",
                     "pass": rules.ld_range[0] - 1e-9 <= ld <= rules.ld_range[1] + 1e-9},
    }
    return {
        "diameter_ft": d, "length_ft": length, "volume_ft3": vol, "area_ft2": area,
        "shell_area_ft2": math.pi * d * length,
        "ver_lb_hr_ft3": ver, "velocity_fpm": vel_fpm, "entrainment_limit_fpm": ent_limit_fpm,
        "residence_min": theta, "residence_target_min": rules.residence_min, "fill_pct": fill, "holdup_lb": holdup_lb,
        "slope_in_per_ft": slope_in_ft, "rpm": n, "critical_rpm": nc, "pct_critical": rules.crit_pct,
        "peripheral_fpm": math.pi * d * n, "l_over_d": ld, "gas_mass_velocity": g, "solids_mass_velocity": fdry,
        "fm_gas_term_min": gas_term, "fm_B": b,
        "under_ver_min": ver < rules.ver_range[0],
        "above_target_velocity": vel_fpm > rules.design_velocity_fpm + 1e-9,
        "checks": checks, "passes": all(c["pass"] or not c.get("hard", True) for c in checks.values()),
        "failed": [k for k, c in checks.items() if not c["pass"] and c.get("hard", True)],
        "advisory_failed": [k for k, c in checks.items() if not c["pass"] and not c.get("hard", True)],
    }


def select_drum(duty: DrumDuty, rules: DrumRules, diameters: list[float], lengths: list[float],
                force: list[float] | None = None, keep: tuple[float, float] | None = None) -> dict:
    """Smallest standard drum that passes every check below the target velocity. keep = a drum to recommend
    anyway (used when the shell loss makes two drums alternate); next size up and alternate are relative to it."""
    mu = air_viscosity_lb_ft_s(duty.exhaust_temp_F)
    ut = terminal_velocity_ft_s(duty.particle_in, duty.particle_density, duty.gas_density_exhaust, mu,
                                duty.sphericity)
    common = {"terminal_velocity_ft_s": ut, "gas_viscosity_lb_ft_s": mu,
              "method": "Friedman & Marshall (1949) residence time; Haider & Levenspiel (1989) terminal velocity"}
    if force:
        c = check_drum(force[0], force[1], duty, rules, ut)
        return {**common, "mode": "forced", "recommended": c, "next_size_up": None, "smaller_alternate": None,
                "candidates_passing": None,
                "smaller_failing": []}
    cands = [check_drum(d, l, duty, rules, ut) for d in sorted(diameters) for l in sorted(lengths)]
    passing_all = sorted([c for c in cands if c["passes"]], key=lambda c: (c["volume_ft3"], c["diameter_ft"]))
    passing = [c for c in passing_all if not c["above_target_velocity"]]
    rec = passing[0] if passing else None
    if keep:
        rec = next(c for c in cands if (c["diameter_ft"], c["length_ft"]) == tuple(keep))
    nxt, alternate = None, None
    if rec:
        bigger = [c for c in passing if c["volume_ft3"] > rec["volume_ft3"] * 1.0001]
        nxt = bigger[0] if bigger else None
    over = [c for c in passing_all if c["above_target_velocity"]
            and (rec is None or c["volume_ft3"] < rec["volume_ft3"] * 0.9999)]
    alternate = over[0] if over else None
    # what governs: the largest failing drums below the recommendation, or (none passing) the closest misses
    if rec:
        smaller = sorted([c for c in cands if not c["passes"] and c["volume_ft3"] < rec["volume_ft3"]],
                         key=lambda c: -c["volume_ft3"])[:3]
    else:
        smaller = sorted(cands, key=lambda c: (len(c["failed"]), c["volume_ft3"]))[:3]
    return {**common, "mode": "kept" if keep else "selected", "recommended": rec, "next_size_up": nxt, "smaller_alternate": alternate,
            "candidates_checked": len(cands), "candidates_passing": len(passing),
            "smaller_failing": [{"size": f"{c['diameter_ft']:g} x {c['length_ft']:g} ft", "failed": c["failed"]}
                                for c in smaller]}

