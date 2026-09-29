#!/usr/bin/env python3
"""Dilute phase pneumatic conveying — line size, velocity and system resistance.

duct.py sizes a duct to hold dust in suspension. This sizes a line that carries
PRODUCT: a hammermill discharge blown to a bin, meal to a loadout, pellets across
a plant. The difference is loading — a dust line runs at a solids-to-air ratio
under one, a conveying line at five to fifteen — and loading is what sets the
velocity you must not drop below and most of the pressure drop.

The chain:

  1. air mass       solids loading ratio µ = solids / air, the number the whole
                    design turns on
  2. pickup         the velocity below which particles drop out. Rizk's
                    correlation gives saltation for a horizontal line; MCE's
                    design velocity is that with a margin on it
  3. line size      the diameter that gives the design velocity at the air rate,
                    rounded to a line the pipe schedule actually has
  4. resistance     four terms, each of which a textbook treats separately:
                    acceleration, gas friction (Darcy-Weisbach with Colebrook),
                    solids friction, and lift
  5. air mover      the blower duty at the inlet, and the power

Every correlation here is published and named on the face of the result. Nothing
in it is an MCE number, because MCE has no conveying design standard on file —
which means the velocities and the solids friction factor are the two things to
argue with before a line gets built, and both are inputs.

The honest caveat, stated on every run: dilute phase pressure drop prediction is
good to maybe ±25% even done carefully, because the solids friction factor
depends on particle shape, resilience and the wall it is sliding on. Size the
blower with margin and put a valve on it.
"""
import math

from . import _fmt

G = 32.174                       # ft/s²
R_AIR = 53.35                    # ft·lbf/(lb·°R)
STD_DENSITY = 0.075              # lb/ft³

# Schedule 40 steel pipe inside diameters, inches — what a conveying line is
# actually built from.
PIPE_ID = {2: 2.067, 2.5: 2.469, 3: 3.068, 4: 4.026, 5: 5.047, 6: 6.065,
           8: 7.981, 10: 10.02, 12: 11.938, 14: 13.124, 16: 15.0, 18: 16.876,
           20: 18.812, 24: 22.624}

# Design velocity margin over saltation. Published practice is 1.3–1.5×; below
# about 1.2 a line chokes on any upset.
DEFAULT_VELOCITY_MARGIN = 1.4
MIN_VELOCITY_MARGIN = 1.2

# Solids friction factor. This is the number nobody can give you from first
# principles — it is back-figured from running lines. The band below is the range
# the published correlations sit in for granular products; it is an INPUT.
DEFAULT_SOLIDS_FRICTION = 0.003
SOLIDS_FRICTION_BAND = (0.001, 0.01)

PIPE_ROUGHNESS_FT = 0.00015      # commercial steel

BEND_K_PRESETS = [("2", "Long radius, R/D ≥ 10 — 2 equivalent velocity heads"),
                  ("4", "Standard radius, R/D 6–8 — 4"),
                  ("8", "Short radius or blind tee — 8")]
DEFAULT_BEND_K = 4.0

# What a bend costs the SOLIDS, as a fraction of one full acceleration length.
# They slow against the outer wall and have to be picked back up. Published
# practice runs from about a half to a whole; 1.0 is the conservative end, and on
# a line with many bends it is usually the biggest single term in the total.
DEFAULT_BEND_REACCEL = 1.0

MATERIALS = [
    # label, particle diameter (in), particle density (lb/ft³)
    ("pellet", "Feed or wood pellets, 1/4 in", 0.25, 75),
    ("meal", "Soy meal / ground feed", 0.04, 75),
    ("corn", "Whole corn", 0.33, 80),
    ("flour", "Flour or fines", 0.006, 90),
    ("chip", "Wood chips or hulls", 0.5, 45),
    ("custom", "Custom — enter the particle"),
]
MATERIAL_BY_ID = {m[0]: m for m in MATERIALS}

SOURCES = {
    "saltation": "Rizk (1973) saltation velocity correlation",
    "gas": "Darcy–Weisbach with the Colebrook–White friction factor",
    "solids": "Two-phase additive pressure drop; solids friction factor supplied",
    "accel": "Momentum balance on the acceleration length",
}
ACCURACY_NOTE = (
    "Dilute phase pressure drop is good to about ±25% even done carefully — the "
    "solids friction factor depends on particle shape, resilience and the pipe wall, "
    "and is back-figured from running lines rather than derived. Size the air mover "
    "with margin and put a control valve on it.")


def _num(raw, default=0.0):
    try:
        v = float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def air_density(temp_f, psig, elevation_ft=0):
    """lb/ft³ at the line's own pressure and temperature."""
    p_atm = 14.696 * (1 - 6.8753e-6 * elevation_ft) ** 5.2559
    p_abs = p_atm + psig
    return p_abs * 144 / (R_AIR * (temp_f + 459.67))


def saltation_velocity(diameter_in, particle_in, particle_density, air_density_,
                       loading):
    """Rizk (1973), the correlation most often used for a first pass.

    Fr_s = (1 / 10^d) * mu^(1/b) with d = 1440*dp + 1.96 and b = 1100*dp + 2.5,
    dp in metres, and the saltation velocity follows from the Froude number on the
    pipe diameter. Returns ft/s.
    """
    dp_m = particle_in * 0.0254
    d_exp = 1440 * dp_m + 1.96
    b_exp = 1100 * dp_m + 2.5
    d_pipe_m = diameter_in * 0.0254
    # Rizk: mu = (1/10^d) * Fr^b  ->  Fr = (mu * 10^d)^(1/b)
    fr = (loading * 10 ** d_exp) ** (1.0 / b_exp)
    v_ms = fr * math.sqrt(9.80665 * d_pipe_m)
    return v_ms * 3.28084


def colebrook(reynolds, rel_roughness):
    """Colebrook–White, solved by iteration. Laminar below 2300."""
    if reynolds < 2300:
        return 64 / reynolds if reynolds > 0 else 0.0
    f = 0.02
    for _ in range(60):
        rhs = -2 * math.log10(rel_roughness / 3.7 + 2.51 / (reynolds * math.sqrt(f)))
        f_new = 1 / rhs ** 2
        if abs(f_new - f) < 1e-12:
            return f_new
        f = f_new
    return f


def size(f):
    rate_tph = _num(f.get("tph"), 10)
    rate = _num(f.get("rate")) or rate_tph * 2000        # lb/h solids
    loading = _num(f.get("loading"), 8)     # the MAXIMUM loading to design to
    material = str(f.get("material") or "meal")
    spec = MATERIAL_BY_ID.get(material, MATERIAL_BY_ID["meal"])
    particle = _num(f.get("particleSize"), spec[2] if len(spec) > 2 else 0.04)
    particle_density = _num(f.get("particleDensity"),
                            spec[3] if len(spec) > 3 else 75)
    bulk = _num(f.get("bulkDensity"), 35)

    horiz = _num(f.get("horizontal"), 150)
    vert = _num(f.get("vertical"), 40)
    bends = int(_num(f.get("bends"), 4))
    bend_k = _num(f.get("bendK"), DEFAULT_BEND_K)
    margin = _num(f.get("velocityMargin"), DEFAULT_VELOCITY_MARGIN)
    solids_friction = _num(f.get("solidsFriction"), DEFAULT_SOLIDS_FRICTION)
    temp = _num(f.get("temp"), 70)
    elevation = _num(f.get("elevation"), 0)
    blower_psig = _num(f.get("blowerPressure"), 8)
    blower_eff = _num(f.get("blowerEff"), 0.65)
    bend_reaccel = _num(f.get("bendReaccel"), DEFAULT_BEND_REACCEL)

    if rate <= 0:
        return {"error": "A conveying rate is required — either lb/h or TPH."}
    if loading <= 0:
        return {"error": "A solids loading ratio is required."}
    if bulk <= 0 or particle_density <= 0:
        return {"error": "A bulk density and a particle density are required."}

    warnings, notes = [], []
    if loading > 15:
        warnings.append(
            f"A maximum loading of {_fmt.locale(loading)} is past dilute phase. Above "
            "about 15 a line runs dense or strand phase, which this does not model — "
            "the velocity and the pressure drop both behave differently.")
    elif loading > 10:
        notes.append(
            f"Designing up to a loading of {_fmt.locale(loading)} puts the line at the "
            "top of dilute phase. Lines this loaded are less forgiving of an upset — "
            "a surge chokes them.")
    if margin < MIN_VELOCITY_MARGIN:
        warnings.append(
            f"A velocity margin of {_fmt.locale(margin)} over saltation is under the "
            f"{MIN_VELOCITY_MARGIN} nobody should design below. The line will plug on "
            "the first upset.")

    # --- line size and air rate --------------------------------------------------
    # The design fixes the VELOCITY, not the air rate: every line has to run above
    # its own saltation velocity, and saltation grows with the pipe. So a bigger
    # line needs more air, which at a fixed solids rate means a lower loading and
    # a bigger blower. The smallest line that keeps the loading inside dilute phase
    # is therefore the cheapest to run, and that is the one picked.
    #
    # Rizk's saltation depends on the loading and the loading depends on the air,
    # so each line is solved by iteration rather than in one pass.
    rho_line = air_density(temp, blower_psig, elevation)
    rho_inlet = air_density(temp, 0, elevation)
    max_loading = loading

    trials = []
    for nominal, id_in in sorted(PIPE_ID.items()):
        area = math.pi * (id_in / 12) ** 2 / 4
        mu = max_loading
        v_salt = v_design = air_lb_s = 0.0
        for _ in range(80):
            v_salt = saltation_velocity(id_in, particle, particle_density,
                                        rho_line, max(mu, 0.1))
            v_design = v_salt * margin
            air_lb_s = rho_line * area * v_design
            mu_new = (rate / 3600) / air_lb_s if air_lb_s > 0 else float("inf")
            if abs(mu_new - mu) < 1e-9:
                mu = mu_new
                break
            mu = mu_new
        trials.append({"nominal": nominal, "idIn": id_in,
                       "saltationFps": round(v_salt, 3),
                       "designFps": round(v_design, 3),
                       "loading": round(mu, 4),
                       "scfm": round(air_lb_s * 3600 / STD_DENSITY / 60, 2),
                       "ok": mu <= max_loading})

    feasible = [t for t in trials if t["ok"]]
    chosen = feasible[0] if feasible else None
    if not chosen:
        return {"error": "No schedule 40 line from 2 in to 24 in carries this rate "
                         f"at a loading of {_fmt.locale(max_loading)} or below. "
                         "Allow a higher loading, or split the rate across two lines."}

    id_in = chosen["idIn"]
    area = math.pi * (id_in / 12) ** 2 / 4
    velocity = chosen["designFps"]
    loading = chosen["loading"]
    air_lb_s = rho_line * area * velocity
    air_lb_h = air_lb_s * 3600
    acfm_line = air_lb_s * 60 / rho_line
    scfm = air_lb_h / STD_DENSITY / 60
    acfm_inlet = air_lb_s * 60 / rho_inlet

    if loading < 1:
        notes.append(
            f"At {_fmt.fixed(loading, 1)} the line is barely loaded — this is closer "
            "to a dust pick-up than a conveying line, and the air is doing most of "
            "the work. A smaller line is not available, so the blower is what it is.")

    # --- pressure drop -----------------------------------------------------------
    viscosity = 1.2e-5 * (temp + 459.67) / 530      # lb/(ft·s), near enough over the band
    reynolds = rho_line * velocity * (id_in / 12) / viscosity
    rel_rough = PIPE_ROUGHNESS_FT / (id_in / 12)
    f_darcy = colebrook(reynolds, rel_rough)

    total_length = horiz + vert
    vel_head = rho_line * velocity ** 2 / (2 * G)          # lb/ft²

    dp_gas = f_darcy * (total_length / (id_in / 12)) * vel_head
    dp_solids = solids_friction * loading * (total_length / (id_in / 12)) * vel_head
    # acceleration: bringing the solids from rest to their conveying velocity.
    # Particles run slower than the air; 0.8 is the usual first-pass slip.
    slip = _num(f.get("slip"), 0.8)
    dp_accel = rate / 3600 / area * (slip * velocity) / G
    dp_lift = (rate / 3600) / (area * slip * velocity) * vert
    # A bend costs the gas its K times the velocity head, and costs the solids a
    # fresh acceleration: they slow against the outer wall and have to be picked
    # back up. One acceleration length per bend is the usual allowance.
    dp_bends_gas = bends * bend_k * vel_head
    dp_bends_solids = bends * dp_accel * bend_reaccel
    dp_bends = dp_bends_gas + dp_bends_solids

    dp_psf = dp_gas + dp_solids + dp_accel + dp_lift + dp_bends
    dp_psi = dp_psf / 144
    dp_inwg = dp_psf / 5.202

    if dp_psi > blower_psig:
        warnings.append(
            f"The line wants {_fmt.fixed(dp_psi, 2)} psi and the blower is set at "
            f"{_fmt.locale(blower_psig)} psig. Either a bigger machine, a shorter "
            "route, or less loading.")
    elif dp_psi > blower_psig * 0.85:
        notes.append(
            f"At {_fmt.fixed(dp_psi, 2)} psi the line uses "
            f"{_fmt.fixed(dp_psi / blower_psig * 100, 0)}% of the blower's rating, "
            "with nothing left for a dirty filter or a wet day.")

    # --- air mover ----------------------------------------------------------------
    p_atm = 14.696 * (1 - 6.8753e-6 * elevation) ** 5.2559
    ratio = (p_atm + max(dp_psi, 0)) / p_atm
    # adiabatic blower power
    k = 1.395
    bhp = (air_lb_s * R_AIR * (temp + 459.67) * k / (k - 1)
           * (ratio ** ((k - 1) / k) - 1)) / 550 / blower_eff

    if bends and dp_bends > dp_psf * 0.4:
        notes.append(
            f"Bends are {_fmt.fixed(dp_bends / dp_psf * 100, 0)}% of the total "
            "resistance. Picking the solids back up after each one is what costs — "
            "fewer, longer-radius bends is the cheapest change available on this line.")
    notes.append(ACCURACY_NOTE)
    notes.append(
        f'Saltation at {_fmt.fixed(chosen["saltationFps"], 1)} ft/s from '
        f'{SOURCES["saltation"]}, on a {_fmt.locale(particle)} in particle at '
        f"{_fmt.locale(particle_density)} lb/ft³. If the product is finer or lighter "
        "than that, the number moves.")

    outputs = [
        {"label": "Line size", "headline": True,
         "value": f'{_fmt.locale(chosen["nominal"])}" sch 40',
         "note": f'{_fmt.locale(id_in)}" ID'},
        {"label": "Conveying velocity", "value": f"{_fmt.fixed(velocity, 1)} ft/s",
         "note": f'{_fmt.fixed(velocity * 60, 0)} ft/min — saltation is '
                 f'{_fmt.fixed(chosen["saltationFps"], 1)} ft/s'},
        {"label": "Air required", "value": f"{_fmt.num(scfm)} SCFM",
         "note": f"{_fmt.num(air_lb_h)} lb/h — a solids loading of "
                 f"{_fmt.fixed(loading, 1)}"},
        {"label": "System resistance", "value": f"{_fmt.fixed(dp_psi, 2)} psi",
         "note": f'{_fmt.num(dp_inwg)}" WG over {_fmt.locale(total_length)} ft '
                 f"and {bends} bend{'s' if bends != 1 else ''}"},
        {"label": "Blower", "value": f"{_fmt.fixed(bhp, 1)} BHP",
         "note": f"{_fmt.num(acfm_inlet)} ACFM at the inlet, "
                 f"{_fmt.fixed(blower_eff * 100, 0)}% efficient"},
    ]

    breakdown = [
        ("Gas friction", dp_gas, SOURCES["gas"]),
        ("Solids friction", dp_solids, SOURCES["solids"]),
        ("Acceleration", dp_accel, SOURCES["accel"]),
        ("Lift", dp_lift, f"{_fmt.locale(vert)} ft of vertical rise"),
        ("Bends", dp_bends, f"{bends} × K {_fmt.locale(bend_k)} on the gas, plus "
                            f"{_fmt.locale(bend_reaccel)} of an acceleration "
                            "each for the solids"),
    ]
    resistance = [{"label": name, "value": f"{_fmt.fixed(v / 144, 3)} psi",
                   "note": note} for name, v, note in breakdown]

    line = {"name": f'Dilute Phase Conveying Line — {_fmt.locale(chosen["nominal"])}" sch 40',
            "quantity": 1, "unitPrice": 0, "needsPrice": True,
            "description": "\n".join([
                f"{_fmt.num(rate)} lb/h at a solids loading of {_fmt.locale(loading)}",
                f'{_fmt.locale(chosen["nominal"])}" schedule 40 line, '
                f"{_fmt.locale(horiz)} ft horizontal and {_fmt.locale(vert)} ft "
                f"vertical, {bends} bends",
                f"{_fmt.num(scfm)} SCFM at {_fmt.fixed(dp_psi, 2)} psi — "
                f"{_fmt.fixed(bhp, 1)} BHP at the blower shaft",
                "Line, bends, supports, air mover and receiver priced separately"])}

    return {
        "calculator": "Dilute Phase Conveying", "outputs": outputs,
        "resistance": resistance, "warnings": warnings, "notes": notes,
        "lines": [line], "options": [], "total": 0.0, "needsPrice": True,
        "sources": SOURCES,
        "air": {"lbPerHour": round(air_lb_h, 3), "scfm": round(scfm, 3),
                "acfmLine": round(acfm_line, 3), "acfmInlet": round(acfm_inlet, 3),
                "densityLine": round(rho_line, 6), "densityInlet": round(rho_inlet, 6),
                "loading": loading},
        "line": {"nominal": chosen["nominal"], "idIn": id_in,
                 "areaFt2": round(area, 6), "velocityFps": round(velocity, 4),
                 "saltationFps": chosen["saltationFps"],
                 "designFps": chosen["designFps"], "margin": margin,
                 "reynolds": round(reynolds, 1), "darcyF": round(f_darcy, 6)},
        "pressure": {"gasPsi": round(dp_gas / 144, 6),
                     "solidsPsi": round(dp_solids / 144, 6),
                     "accelPsi": round(dp_accel / 144, 6),
                     "liftPsi": round(dp_lift / 144, 6),
                     "bendsPsi": round(dp_bends / 144, 6),
                     "bendsGasPsi": round(dp_bends_gas / 144, 6),
                     "bendsSolidsPsi": round(dp_bends_solids / 144, 6),
                     "totalPsi": round(dp_psi, 6),
                     "totalInWg": round(dp_inwg, 4)},
        "blower": {"bhp": round(bhp, 4), "ratio": round(ratio, 5),
                   "efficiency": blower_eff},
        "trials": trials,
    }
