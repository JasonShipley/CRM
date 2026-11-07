"""Combustion: stoichiometric air, excess air, products and flame temperature.

Method (replaces CALC A23:G34 and COMB!A4:L57)
* Solid and liquid fuels: ultimate analysis on a DRY basis (C, H, O, N, S, ash, mass %),
  which must close to 100%, plus fuel moisture (wet basis). Elements are converted to the
  as-fired basis, then an element molar balance gives O2 demand and products. The
  stoichiometric air this produces is identical to the mass formula
      A_st = 11.53 C + 34.34 (H - O/8) + 4.29 S   (lb dry air / lb fuel, mass fractions)
  because those coefficients are just MW ratios divided by 23.14% O2 (by mass) in dry air.
* Gas fuels: volume (= mole) composition, must close to 100%.
* Heating value: LHV as fired is the energy basis. HHV and LHV are cross-checked against
  the analysis: gases from heats of formation (Cengel & Boles Table A-26, 25 C), solids
  and liquids from the Channiwala-Parikh correlation (Fuel 81 (2002) 1051-1063).
  LHV(as fired) = LHV(dry)(1 - M) - 1050 M (BTU/lb), ISO 18125:2017 convention
  (2.443 MJ/kg per kg of moisture).
* Fuel moisture is included in the combustion water (sheet CALC D53 left it out).
* Excess air is always "% excess air": total air = (1 + EA/100) x stoichiometric.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .properties import AIR_MOLE_FRAC, HFG_77F_BTU_LB, HFG_TRIPLE_BTU_LB, MW, MW_AIR, h_mix_btu
from .solver import brent
from .units import KJ_PER_KG_TO_BTU_PER_LB

# heats of formation at 25 C, kJ/kmol (Cengel & Boles Table A-26; H2S and SO2 from NIST-JANAF)
HF298 = {"CH4": -74850.0, "C2H6": -84680.0, "C3H8": -103850.0, "C4H10": -126150.0, "H2": 0.0, "CO": -110530.0,
         "CO2": -393520.0, "H2O": -241820.0, "H2S": -20600.0, "SO2": -296840.0, "N2": 0.0, "O2": 0.0}
HFG25_KJ_KMOL = 44010.0  # H2O(l) -> H2O(g) at 25 C, Cengel Table A-26 (-285830 vs -241820)

# gas fuel stoichiometry per mole of component: (O2 demand, CO2, H2O, SO2)
GAS_STOICH = {
    "CH4": (2.0, 1, 2, 0), "C2H6": (3.5, 2, 3, 0), "C3H8": (5.0, 3, 4, 0), "C4H10": (6.5, 4, 5, 0),
    "H2": (0.5, 0, 1, 0), "CO": (0.5, 1, 0, 0), "H2S": (1.5, 0, 1, 1),
    "CO2": (0.0, 1, 0, 0), "N2": (0.0, 0, 0, 0), "O2": (-1.0, 0, 0, 0),
}
ULTIMATE_KEYS = ("C", "H", "O", "N", "S", "ash")
CLOSURE_TOL_PCT = 0.5


@dataclass
class CombustionResult:
    """Everything per lb of fuel AS FIRED, plus flags raised while checking the fuel."""
    kind: str
    stoich_o2_lbmol: float
    stoich_air_lb: float  # dry air
    stoich_air_mass_formula_lb: float | None  # 11.53C + 34.34(H - O/8) + 4.29S, solids/liquids
    products_lbmol: dict[str, float]  # stoichiometric products from the fuel itself (no air N2/O2)
    water_formed_lb: float  # from H plus fuel moisture
    ash_lb: float
    lhv_computed_btu_lb: float | None  # as fired, from the analysis
    hhv_computed_btu_lb: float | None
    mw_gas: float | None = None
    sg_gas: float | None = None
    notes: list[str] = field(default_factory=list)
    flags: list[tuple[str, str, str]] = field(default_factory=list)  # (severity, code, message)


def check_closure(analysis: dict[str, float], what: str) -> tuple[dict[str, float], list[tuple[str, str, str]]]:
    """Analyses must close to 100% (+/- 0.5). Out of tolerance: violation flag, then normalized."""
    tot = sum(analysis.values())
    flags = []
    if abs(tot - 100.0) > CLOSURE_TOL_PCT:
        flags.append(("violation", "ANALYSIS_NOT_CLOSED",
                      f"{what} sums to {tot:.2f}%, not 100% (tolerance +/-{CLOSURE_TOL_PCT}%). Normalized to 100% "
                      f"for this run; correct the analysis before quoting."))
        return {k: v * 100.0 / tot for k, v in analysis.items()}, flags
    return {k: v * 100.0 / tot for k, v in analysis.items()}, flags


def channiwala_hhv_dry_btu_lb(u: dict[str, float]) -> float:
    """Channiwala & Parikh (2002) unified correlation, dry basis wt%; MJ/kg -> BTU/lb."""
    mj = (0.3491 * u["C"] + 1.1783 * u["H"] + 0.1005 * u["S"] - 0.1034 * u["O"] - 0.0151 * u["N"]
          - 0.0211 * u["ash"])
    return mj * 1000.0 * KJ_PER_KG_TO_BTU_PER_LB


def lhv_dry_from_hhv_dry(hhv_d: float, h_pct_dry: float) -> float:
    return hhv_d - HFG_77F_BTU_LB * MW["H2O"] / MW["H2"] * h_pct_dry / 100.0


def as_fired(value_dry: float, moisture_wb_pct: float, net: bool) -> float:
    m = moisture_wb_pct / 100.0
    return value_dry * (1 - m) - (HFG_77F_BTU_LB * m if net else 0.0)


def to_lhv_as_fired(value: float, basis: str, moisture_wb_pct: float, h_pct_dry: float | None) -> float:
    """Convert an entered heating value to LHV as fired. basis: net_as_fired | net_dry | gross_dry | gross_as_fired."""
    m = moisture_wb_pct / 100.0
    if basis == "net_as_fired":
        return value
    if basis == "net_dry":
        return as_fired(value, moisture_wb_pct, net=True)
    if h_pct_dry is None:
        raise ValueError("gross heating value needs the fuel hydrogen content to convert to net")
    if basis == "gross_dry":
        return as_fired(lhv_dry_from_hhv_dry(value, h_pct_dry), moisture_wb_pct, net=True)
    if basis == "gross_as_fired":
        hhv_d = value / (1 - m) if m < 1 else 0.0
        return as_fired(lhv_dry_from_hhv_dry(hhv_d, h_pct_dry), moisture_wb_pct, net=True)
    raise ValueError(f"unknown heating value basis {basis!r}")


def solid_fuel(ultimate_dry_pct: dict[str, float], moisture_wb_pct: float, is_wood: bool = False) -> CombustionResult:
    u_in = {k: float(ultimate_dry_pct.get(k, 0.0)) for k in ULTIMATE_KEYS}
    u, flags = check_closure(u_in, "Fuel ultimate analysis (dry basis C+H+O+N+S+ash)")
    if is_wood and u["N"] > 1.0:
        flags.append(("warning", "WOOD_N_HIGH", f"Fuel nitrogen {u['N']:.2f}% (dry) is unrealistic for wood "
                                                 f"(typically 0.1 to 0.5%); check the analysis."))
    m = moisture_wb_pct / 100.0
    af = {k: v / 100.0 * (1 - m) for k, v in u.items()}  # as-fired mass fractions
    o2 = af["C"] / MW["C"] + af["H"] / MW["H2"] * 0.5 + af["S"] / MW["S"] - af["O"] / MW["O2"]
    prod = {"CO2": af["C"] / MW["C"], "H2O": af["H"] / MW["H2"] + m / MW["H2O"], "SO2": af["S"] / MW["S"],
            "N2": af["N"] / MW["N2"]}
    air = o2 / AIR_MOLE_FRAC["O2"] * MW_AIR
    formula = 11.53 * af["C"] + 34.34 * (af["H"] - af["O"] / 8) + 4.29 * af["S"]
    hhv_d = channiwala_hhv_dry_btu_lb(u)
    lhv_d = lhv_dry_from_hhv_dry(hhv_d, u["H"])
    return CombustionResult(
        kind="solid", stoich_o2_lbmol=o2, stoich_air_lb=air, stoich_air_mass_formula_lb=formula,
        products_lbmol=prod, water_formed_lb=prod["H2O"] * MW["H2O"], ash_lb=af["ash"],
        lhv_computed_btu_lb=as_fired(lhv_d, moisture_wb_pct, net=True),
        hhv_computed_btu_lb=as_fired(hhv_d, moisture_wb_pct, net=False), flags=flags,
        notes=["HHV/LHV cross-check: Channiwala & Parikh (2002) correlation on the dry ultimate analysis."])


def gas_fuel(composition_mol_pct: dict[str, float]) -> CombustionResult:
    unknown = set(composition_mol_pct) - set(GAS_STOICH)
    if unknown:
        raise ValueError(f"unsupported gas components: {sorted(unknown)}")
    y, flags = check_closure({k: float(v) for k, v in composition_mol_pct.items()}, "Fuel gas composition (mol %)")
    y = {k: v / 100.0 for k, v in y.items()}
    mw = sum(y[k] * MW[k] for k in y)
    o2 = sum(y[k] * GAS_STOICH[k][0] for k in y)
    prod_mol = {"CO2": sum(y[k] * GAS_STOICH[k][1] for k in y), "H2O": sum(y[k] * GAS_STOICH[k][2] for k in y),
                "SO2": sum(y[k] * GAS_STOICH[k][3] for k in y), "N2": y.get("N2", 0.0)}
    # LHV per kmol of fuel from heats of formation (products with water as vapor)
    lhv_kmol = 0.0
    for k, yk in y.items():
        if k in ("CO2", "N2", "O2"):
            continue
        _, c, h2o, so2 = GAS_STOICH[k]
        lhv_kmol += yk * (HF298[k] - c * HF298["CO2"] - h2o * HF298["H2O"] - so2 * HF298["SO2"])
    hhv_kmol = lhv_kmol + prod_mol["H2O"] * HFG25_KJ_KMOL
    per_lb = 1.0 / mw  # lbmol fuel per lb fuel
    return CombustionResult(
        kind="gas", stoich_o2_lbmol=o2 * per_lb, stoich_air_lb=o2 * per_lb / AIR_MOLE_FRAC["O2"] * MW_AIR,
        stoich_air_mass_formula_lb=None, products_lbmol={k: v * per_lb for k, v in prod_mol.items()},
        water_formed_lb=prod_mol["H2O"] * per_lb * MW["H2O"], ash_lb=0.0,
        lhv_computed_btu_lb=lhv_kmol / mw * KJ_PER_KG_TO_BTU_PER_LB,
        hhv_computed_btu_lb=hhv_kmol / mw * KJ_PER_KG_TO_BTU_PER_LB, mw_gas=mw, sg_gas=mw / MW_AIR, flags=flags,
        notes=["LHV/HHV from heats of formation at 25 C (Cengel & Boles Table A-26)."])


def air_moles(dry_air_lb: float, humidity_lb_lb: float) -> dict[str, float]:
    n = dry_air_lb / MW_AIR
    m = {s: n * x for s, x in AIR_MOLE_FRAC.items()}
    m["H2O"] = dry_air_lb * humidity_lb_lb / MW["H2O"]
    return m


def add(*streams: dict[str, float], scale: float = 1.0) -> dict[str, float]:
    out: dict[str, float] = {}
    for st in streams:
        for k, v in st.items():
            out[k] = out.get(k, 0.0) + v * scale
    return out


def flue_gas_per_lb_fuel(c: CombustionResult, excess_air_pct: float, humidity_lb_lb: float) -> dict[str, float]:
    """Products of 1 lb fuel burned with (1 + EA) x stoichiometric humid air, lbmol."""
    air = air_moles(c.stoich_air_lb * (1 + excess_air_pct / 100.0), humidity_lb_lb)
    gas = add(air, c.products_lbmol)
    gas["O2"] = gas.get("O2", 0.0) - c.stoich_o2_lbmol
    return gas


def fuel_energy_on_datum(lhv_btu_lb: float, c: CombustionResult) -> float:
    """BTU per lb fuel entering the balance: LHV + latent heat of the combustion water at 32 F.
    On the package datum, water vapor carries hfg(32 F), so the fuel must carry it too."""
    return lhv_btu_lb + c.water_formed_lb * HFG_TRIPLE_BTU_LB


def adiabatic_flame_temp_f(lhv_btu_lb: float, c: CombustionResult, excess_air_pct: float, humidity_lb_lb: float,
                           t_air_f: float, furnace_eff: float, fuel_sensible_btu_lb: float = 0.0) -> float:
    """Products temperature with the furnace loss (1 - eff) x LHV removed; no dissociation."""
    gas = flue_gas_per_lb_fuel(c, excess_air_pct, humidity_lb_lb)
    air = air_moles(c.stoich_air_lb * (1 + excess_air_pct / 100.0), humidity_lb_lb)
    h_in = fuel_energy_on_datum(lhv_btu_lb, c) - (1 - furnace_eff) * lhv_btu_lb + fuel_sensible_btu_lb \
        + h_mix_btu(air, t_air_f)
    return brent(lambda t: h_mix_btu(gas, t) - h_in, t_air_f, 6000.0)
