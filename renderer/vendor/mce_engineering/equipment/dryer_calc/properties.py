"""Steam, gas and psychrometric properties on ONE reference state.

Reference state for the whole dryer balance (stated in every output):
    32 F (273.15 K), liquid water h = 0, every ideal gas species h = 0 at 32 F,
    except water vapor, whose enthalpy is measured from liquid water at 32 F
    (h_vapor(32 F) = hfg at the triple point = 2500.9 kJ/kg = 1075.2 BTU/lb).
    Solids h = Cp x (T - 32 F).

Sources
* Saturation pressure / temperature: IAPWS-IF97 Region 4 equations (IAPWS R7-97(2012)),
  verified against the IF97 check values in tests.
* Saturated liquid water enthalpy: quartic fit to IAPWS-95 table values
  (Cengel & Boles, Thermodynamics, Table A-4, 0.01 to 150 C), max fit error 0.04 kJ/kg.
* Ideal gas heat capacities: cp = a + bT + cT^2 + dT^3 (T in K, kJ/kmol-K),
  Cengel & Boles Table A-2(c), valid 273 to 1800 K, quoted error < 1%. Argon is
  monatomic: cp = 5/2 R = 20.786 kJ/kmol-K.
* Water vapor is treated as an ideal gas. At dryer partial pressures (< 5 psia) the
  real-gas departure is under 0.4 BTU/lb per psia of partial pressure (< 0.15%).
* Barometric pressure vs elevation: ASHRAE Handbook Fundamentals (2017) Ch. 1, Eq. 3.
"""

from __future__ import annotations

import math

from .units import (KJ_PER_KG_TO_BTU_PER_LB, P_STD_PSIA, PSI_TO_KPA, R_PSIA_FT3, STD_FT3_PER_LBMOL, f_to_c,
                    f_to_k, f_to_r)

REFERENCE_STATE = ("32 F (0 C) and 14.696 psia: liquid water h = 0; dry air and all other ideal-gas species "
                   "h = 0 at 32 F; water vapor h measured from liquid water at 32 F (includes hfg = 1075.2 BTU/lb "
                   "at the triple point); solids h = Cp x (T - 32 F). Fuel energy enters as LHV (as fired) plus the "
                   "latent heat of its combustion water at 32 F, so the latent heat in every water vapor stream is "
                   "on the same basis.")

# molecular weights, lb/lbmol (IUPAC 2013 standard atomic weights)
MW = {
    "N2": 28.0134, "O2": 31.9988, "Ar": 39.948, "CO2": 44.0095, "H2O": 18.01528, "SO2": 64.064,
    "C": 12.0107, "H": 1.00794, "H2": 2.01588, "S": 32.065, "N": 14.0067, "O": 15.9994,
    "CH4": 16.04246, "C2H6": 30.06904, "C3H8": 44.09562, "C4H10": 58.1222, "CO": 28.0101, "H2S": 34.08088,
}
GAS_SPECIES = ("N2", "O2", "Ar", "CO2", "H2O", "SO2")

# dry air, mole fraction (U.S. Standard Atmosphere 1976, CO2 rounded to 360 ppm)
AIR_MOLE_FRAC = {"N2": 0.78084, "O2": 0.20946, "Ar": 0.00934, "CO2": 0.00036}
MW_AIR = sum(AIR_MOLE_FRAC[s] * MW[s] for s in AIR_MOLE_FRAC)  # 28.965
O2_MASS_FRAC_AIR = AIR_MOLE_FRAC["O2"] * MW["O2"] / MW_AIR  # 0.2314

# Cengel & Boles Table A-2(c): cp = a + b T + c T^2 + d T^3, kJ/(kmol K), T in K
_CP = {
    "N2": (28.90, -0.1571e-2, 0.8081e-5, -2.873e-9),
    "O2": (25.48, 1.520e-2, -0.7155e-5, 1.312e-9),
    "CO2": (22.26, 5.981e-2, -3.501e-5, 7.469e-9),
    "H2O": (32.24, 0.1923e-2, 1.055e-5, -3.595e-9),
    "SO2": (25.78, 5.795e-2, -3.812e-5, 8.612e-9),
    "Ar": (20.786, 0.0, 0.0, 0.0),
    "AIR": (28.11, 0.1967e-2, 0.4802e-5, -1.966e-9),  # used only to cross-check the species mix
}
CP_VALID_K = (273.0, 1800.0)
T0_K = 273.15
HFG_TRIPLE_KJ_KG = 2500.9  # IAPWS-95 h_g at 0.01 C (h_f = 0.000611)
HFG_TRIPLE_BTU_LB = HFG_TRIPLE_KJ_KG * KJ_PER_KG_TO_BTU_PER_LB  # 1075.2
HFG_77F_BTU_LB = 2442.3 * KJ_PER_KG_TO_BTU_PER_LB  # 1050.0, used only for HHV <-> LHV conversion (ISO 18125)
KJ_KMOL_TO_BTU_LBMOL = KJ_PER_KG_TO_BTU_PER_LB  # same ratio


def cp_molar(species: str, t_k: float) -> float:
    a, b, c, d = _CP[species]
    return a + b * t_k + c * t_k ** 2 + d * t_k ** 3


def _int_cp(species: str, t1: float, t2: float) -> float:
    a, b, c, d = _CP[species]
    f = lambda t: a * t + b * t ** 2 / 2 + c * t ** 3 / 3 + d * t ** 4 / 4
    return f(t2) - f(t1)


def h_species_btu_lbmol(species: str, t_f: float) -> float:
    """Enthalpy of one ideal-gas species, BTU/lbmol, on the package reference state."""
    dh = _int_cp(species, T0_K, f_to_k(t_f)) * KJ_KMOL_TO_BTU_LBMOL
    if species == "H2O":
        dh += HFG_TRIPLE_BTU_LB * MW["H2O"]
    return dh


def h_mix_btu(moles: dict[str, float], t_f: float) -> float:
    """Total enthalpy (BTU or BTU/hr) of a gas mixture given lbmol (or lbmol/hr) of each species."""
    return sum(n * h_species_btu_lbmol(s, t_f) for s, n in moles.items() if n)


def h_vapor_btu_lb(t_f: float) -> float:
    """Water vapor (ideal gas, low partial pressure), BTU/lb from liquid water at 32 F."""
    return h_species_btu_lbmol("H2O", t_f) / MW["H2O"]


def h_dry_air_btu_lb(t_f: float) -> float:
    return h_mix_btu({s: x / MW_AIR for s, x in AIR_MOLE_FRAC.items()}, t_f)


def cp_dry_air_btu_lb_f(t_f: float) -> float:
    t = f_to_k(t_f)
    return sum(x * cp_molar(s, t) for s, x in AIR_MOLE_FRAC.items()) / MW_AIR * 0.238846


# saturated liquid water, quartic fit to IAPWS-95 (kJ/kg vs C), see module docstring
_HF_FIT = (-2.1313466381417214e-09, 4.394598995903351e-06, -0.0005402996963053674, 4.20380665371623,
           -0.007289928357669179)
HF_VALID_F = (32.0, 302.0)


def h_liquid_water_btu_lb(t_f: float) -> float:
    t = f_to_c(t_f)
    a, b, c, d, e = _HF_FIT
    _ = e  # fit intercept (-0.007 kJ/kg) dropped so h_f(32 F) = 0 exactly on the reference state
    return (((a * t + b) * t + c) * t + d) * t * KJ_PER_KG_TO_BTU_PER_LB


# ---------------------------------------------------------------- IAPWS-IF97 Region 4
_N = (0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5,
      -0.32325550322333e7, 0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6,
      -0.23855557567849, 0.65017534844798e3)


def psat_mpa(t_k: float) -> float:
    n = _N
    th = t_k + n[8] / (t_k - n[9])
    a = th * th + n[0] * th + n[1]
    b = n[2] * th * th + n[3] * th + n[4]
    c = n[5] * th * th + n[6] * th + n[7]
    return (2 * c / (-b + math.sqrt(b * b - 4 * a * c))) ** 4


def tsat_k(p_mpa: float) -> float:
    n = _N
    be = p_mpa ** 0.25
    e = be * be + n[2] * be + n[5]
    f = n[0] * be * be + n[3] * be + n[6]
    g = n[1] * be * be + n[4] * be + n[7]
    d = 2 * g / (-f - math.sqrt(f * f - 4 * e * g))
    return (n[9] + d - math.sqrt((n[9] + d) ** 2 - 4 * (n[8] + n[9] * d))) / 2


def psat_psia(t_f: float) -> float:
    return psat_mpa(f_to_k(t_f)) * 1000.0 / PSI_TO_KPA


def dew_point_f(pw_psia: float) -> float:
    """Dew point (F) for a water vapor partial pressure (psia). IF97 Region 4 is valid above 611.2 Pa."""
    p = pw_psia * PSI_TO_KPA / 1000.0
    if p < 611.213e-6:
        return float("nan")  # below the triple point (frost point regime)
    return tsat_k(p) * 1.8 - 459.67


# ---------------------------------------------------------------- site and gas state
def barometric_psia(elevation_ft: float) -> float:
    """ASHRAE Fundamentals 2017 Ch.1 Eq.3: p = 14.696 (1 - 6.8754e-6 Z)^5.2559."""
    return P_STD_PSIA * (1.0 - 6.8754e-6 * elevation_ft) ** 5.2559


def gas_density_lb_ft3(mw: float, t_f: float, p_psia: float) -> float:
    return p_psia * mw / (R_PSIA_FT3 * f_to_r(t_f))


def scfm_from_lbmol_hr(lbmol_hr: float) -> float:
    return lbmol_hr * STD_FT3_PER_LBMOL / 60.0


def acfm_from_lbmol_hr(lbmol_hr: float, t_f: float, p_psia: float) -> float:
    return lbmol_hr * R_PSIA_FT3 * f_to_r(t_f) / p_psia / 60.0


def humidity_ratio_from_pw(pw_psia: float, p_psia: float, mw_dry: float = MW_AIR) -> float:
    return MW["H2O"] / mw_dry * pw_psia / (p_psia - pw_psia)


def air_viscosity_lb_ft_s(t_f: float) -> float:
    """Sutherland's law for air (mu0 1.716e-5 Pa s at 273.15 K, S = 110.4 K), returned in lb/(ft s)."""
    t = f_to_k(t_f)
    mu = 1.716e-5 * (t / 273.15) ** 1.5 * (273.15 + 110.4) / (t + 110.4)
    return mu * 0.67196897514


def adiabatic_saturation_f(moles: dict[str, float], t_f: float, p_psia: float) -> float:
    """Adiabatic saturation temperature of a gas stream (wet bulb proxy for drying gas).

    Solves h(gas, T) + m_w h_l(Ts) = h(gas + m_w vapor, Ts) with the gas saturated at Ts.
    """
    n_dry = sum(n for s, n in moles.items() if s != "H2O")
    h_in = h_mix_btu(moles, t_f)

    def resid(ts: float) -> float:
        pw = psat_psia(ts)
        n_w_sat = n_dry * pw / (p_psia - pw)
        added = n_w_sat - moles.get("H2O", 0.0)
        m = dict(moles)
        m["H2O"] = n_w_sat
        return h_in + added * MW["H2O"] * h_liquid_water_btu_lb(ts) - h_mix_btu(m, ts)

    from .solver import brent
    t_boil = tsat_k(p_psia * PSI_TO_KPA / 1000.0) * 1.8 - 459.67
    return brent(resid, 33.0, min(t_f, t_boil - 0.5))
