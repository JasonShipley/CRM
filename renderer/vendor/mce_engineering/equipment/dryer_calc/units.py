"""Unit constants, conversions and the dual-unit output helper.

Imperial (US customary) is primary everywhere; metric is shown alongside.
Standard conditions for every SCFM / SCFH in this package: 70 F and 29.92 in. Hg
(14.696 psia), dry or wet as labeled. ACFM is at the actual temperature and the site
barometric pressure (plus any local gauge pressure the caller passes).
"""

from __future__ import annotations

import math

# exact or defined conversions
LB_TO_KG = 0.45359237
FT_TO_M = 0.3048
IN_TO_M = 0.0254
FT3_TO_M3 = FT_TO_M ** 3
BTU_TO_KJ = 1.05505585262  # International Table BTU
KJ_PER_KG_TO_BTU_PER_LB = 1.0 / (BTU_TO_KJ / LB_TO_KG)  # 0.429923
BTU_HR_TO_KW = BTU_TO_KJ / 3600.0
PSI_TO_KPA = 6.894757293168
IN_WC_TO_PSI = 0.0361273  # inch of water at 60 F (ASHRAE)
IN_WC_TO_PA = IN_WC_TO_PSI * PSI_TO_KPA * 1000.0
LB_PER_TON = 2000.0  # US short ton
G_FT_S2 = 32.174

# gas constant and the single standard state used for SCFM
R_PSIA_FT3 = 10.73159  # psia ft3 / (lbmol R)
T_STD_R = 70.0 + 459.67
P_STD_PSIA = 14.696
STD_FT3_PER_LBMOL = R_PSIA_FT3 * T_STD_R / P_STD_PSIA  # 386.8 ft3/lbmol at 70 F, 29.92 in. Hg


def f_to_c(t_f: float) -> float:
    return (t_f - 32.0) / 1.8


def c_to_f(t_c: float) -> float:
    return t_c * 1.8 + 32.0


def f_to_r(t_f: float) -> float:
    return t_f + 459.67


def f_to_k(t_f: float) -> float:
    return (t_f + 459.67) / 1.8


def k_to_f(t_k: float) -> float:
    return t_k * 1.8 - 459.67


def delta_f_to_c(dt_f: float) -> float:
    return dt_f / 1.8


# unit -> (metric unit, converter). Used by q() so every output carries both systems.
_METRIC = {
    "lb/hr": ("kg/h", lambda v: v * LB_TO_KG),
    "lb": ("kg", lambda v: v * LB_TO_KG),
    "TPH": ("t/h", lambda v: v * LB_PER_TON * LB_TO_KG / 1000.0),
    "tons/yr": ("t/yr", lambda v: v * LB_PER_TON * LB_TO_KG / 1000.0),
    "F": ("C", f_to_c),
    "dF": ("dC", delta_f_to_c),
    "BTU/hr": ("kW", lambda v: v * BTU_HR_TO_KW),
    "MMBtu/hr": ("MW", lambda v: v * 1e6 * BTU_HR_TO_KW / 1000.0),
    "MMBtu/yr": ("GJ/yr", lambda v: v * 1e6 * BTU_TO_KJ / 1e6),
    "BTU/lb": ("kJ/kg", lambda v: v / KJ_PER_KG_TO_BTU_PER_LB),
    "BTU/lb-F": ("kJ/kg-K", lambda v: v * 4.1868),
    "BTU/hr-ft2-F": ("W/m2-K", lambda v: v * 5.678263),
    "lb/ft3": ("kg/m3", lambda v: v * LB_TO_KG / FT3_TO_M3),
    "ft3/hr": ("m3/h", lambda v: v * FT3_TO_M3),
    "ft3": ("m3", lambda v: v * FT3_TO_M3),
    "ft2": ("m2", lambda v: v * FT_TO_M ** 2),
    "ACFM": ("Am3/h", lambda v: v * FT3_TO_M3 * 60.0),
    "SCFM": ("Sm3/h", lambda v: v * FT3_TO_M3 * 60.0),  # same 70 F / 1 atm basis
    "SCFH": ("Sm3/h", lambda v: v * FT3_TO_M3),
    "FPM": ("m/s", lambda v: v * FT_TO_M / 60.0),
    "ft/s": ("m/s", lambda v: v * FT_TO_M),
    "ft": ("m", lambda v: v * FT_TO_M),
    "in": ("mm", lambda v: v * 25.4),
    "psia": ("kPa", lambda v: v * PSI_TO_KPA),
    "in. w.c.": ("Pa", lambda v: v * IN_WC_TO_PA),
    "HP": ("kW", lambda v: v * 0.745699872),
    "lb H2O/hr-ft3": ("kg H2O/h-m3", lambda v: v * LB_TO_KG / FT3_TO_M3),
    "lb/hr-ft2": ("kg/s-m2", lambda v: v * LB_TO_KG / FT_TO_M ** 2 / 3600.0),
    "BTU/lb water": ("kJ/kg water", lambda v: v / KJ_PER_KG_TO_BTU_PER_LB),
    "lb/lb": ("kg/kg", lambda v: v),
    "gal/hr": ("L/h", lambda v: v * 3.785411784),
}


def _round(v: float, sig: int = 5) -> float:
    if v == 0 or not math.isfinite(v):
        return v
    return round(v, max(0, sig - 1 - int(math.floor(math.log10(abs(v))))))


def q(value, unit: str, note: str = "") -> dict:
    """Output quantity with the metric equivalent alongside: {"value", "unit", "si": [v, unit]}."""
    out: dict = {"value": value, "unit": unit}  # full precision; display layers round
    conv = _METRIC.get(unit)
    if conv and isinstance(value, (int, float)) and not isinstance(value, bool):
        out["si"] = [_round(float(conv[1](value))), conv[0]]
    if note:
        out["note"] = note
    return out
