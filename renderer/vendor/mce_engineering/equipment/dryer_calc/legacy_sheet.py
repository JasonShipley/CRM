"""Replica of the legacy workbook's formulas, FOR THE AUDIT ONLY. The engine never imports this.

"Coding mass balance for Thermal reactor.xlsm" (sheets Input, CALC, FLOW, DESIGN, Burner,
COMB, Thermal Reactor Cal; macro DoCalculate on CALC). Each function names the cells it
reproduces. tests/dryer_calc/test_legacy_sheet.py checks that these replicas return the
workbook's cached values, which proves the audit's reading of every formula; the same
functions evaluated "live" at the current inputs give the numeric impact of each issue.
"""

from __future__ import annotations

# Input sheet as stored (test case)
SHEET_INPUT = {
    "A4_cp": 0.55, "A6_density": 8.0, "D4_ambient": 60.0, "D6_humidity": 0.002, "A10_elev": 1200.0,
    "C8_vapor_density": 0.0465, "H3_comb_eff": 0.9, "D14_feed_T": 60.0, "F14_product_T": 200.0, "F24_exhaust_T": 180.0,
    "F29_recycle_T": 175.0, "G10_wood_nhv": 8000.0, "H10_wood_density": 12.0, "I10_wood_xs": 1.3,
    "C18_wet": 3000.0, "C15_mc_in": 0.5, "F15_mc_out": 0.1,
}
# CALC cells that DoCalculate writes as static values, as stored in the file
SHEET_CALC_STORED = {"F4": 435600.00000000006, "F5": 108000.0, "F6": 1368000.0, "F7": 8732700.0, "F8": -131040.0,
                     "F9": 10513260.0, "F12": 3191031.884649999, "F15": 15725584.682088107, "G17": 1965.6980852610134,
                     "G18": 163.80817377175111, "G25": 16.330241908006816, "G29": 5.242354882255888,
                     "B33": 12.05741622918854, "B34": 23701.239994910982, "F33": 13.05741622918854,
                     "F34": 25666.938080172, "I39": 10513260.0, "I44": 436635.0, "I45": 15717012.186598314,
                     "B47": 1964.6265233247893, "D47": 163.71887694373245, "D48": 1746.3346873998128,
                     "H4": 110799.71821701385, "G67": 588.0202442816465, "C42": 0.1432302405124102}
WOOD_CALC_A23_A27 = {"C": 0.4324, "H": 0.0565, "O": 0.374, "N": 0.0469, "S": 0.0005}
NG_CALC_C23_C29 = {"CH4": 0.952, "C2H6": 0.025, "C3H8": 0.002, "C4H10": 0.0006, "H2": 0.0002, "CO": 0.0, "O2": 0.0002}


def mass_balance_input(wet=3000.0, mc_in=0.5, mc_out=0.1) -> dict:
    """Input C16:F18 (these cells are live formulas and are correct)."""
    solids = wet * (1 - mc_in)
    product = solids / (1 - mc_out)
    water_out = mc_out * product
    return {"solids": solids, "product": product, "water_out": water_out, "evap": wet * mc_in - water_out}


def air_density_sheet(elev_ft: float) -> float:
    """Input A8: ISA density with 2.2 lb/kg and 3.3 ft/m."""
    return ((44.3308 - elev_ft / 3280.83) / 42.2665) ** 4.2558 * 2.2 / 3.3 ** 3


def air_density_isa_exact(elev_ft: float) -> float:
    """Same ISA formula with exact conversions (2.20462 lb/kg, 3.28084 ft/m)."""
    return ((44.3308 - elev_ft * 0.3048 / 1000) / 42.2665) ** 4.2558 * 2.20462262 / 3.28083990 ** 3


def macro_product_heat(cp, solids, water_out, evap, t_feed, t_prod, t_exh) -> dict:
    """DoCalculate -> CALC F4:F9 (written as static values when the macro runs)."""
    f4 = cp * solids * (t_prod - t_feed)
    f5 = water_out * (t_prod - t_feed)
    f6 = evap * (212 - t_feed)
    f7 = evap * 970.3
    f8 = evap * 0.455 * (t_exh - 212)
    return {"F4": f4, "F5": f5, "F6": f6, "F7": f7, "F8": f8, "F9": f4 + f5 + f6 + f7 + f8}


def stale_case_from_stored() -> dict:
    """Back-solve the case the stored CALC values came from (F7 = evap x 970.3)."""
    s = SHEET_CALC_STORED
    evap = s["F7"] / 970.3
    return {"evap": evap, "solids": s["F4"] / (0.55 * 140), "water_out": s["F5"] / 140,
            "check_F6": evap * 152, "check_F8": evap * 0.455 * -32}


def stoich_volumetric_wood(u=WOOD_CALC_A23_A27) -> float:
    """Macro G29: (1.514C + 4.54H + 0.568S - 0.568O) x 100 / 13.334 (S taken from A27 'SULF/H2O')."""
    return (1.514 * u["C"] + 4.54 * u["H"] + 0.568 * u["S"] - 0.568 * u["O"]) * 100 / 13.334


def stoich_mass_formula(u=WOOD_CALC_A23_A27) -> float:
    return 11.53 * u["C"] + 34.34 * (u["H"] - u["O"] / 8) + 4.29 * u["S"]


def stoich_ng_sheet(y=NG_CALC_C23_C29, sg=0.587) -> float:
    """Macro G25 (ft3 air/ft3 gas divided by SG = lb air / lb gas)."""
    return (0.0956 * y["CH4"] + 0.1675 * y["C2H6"] + 0.239 * y["C3H8"] + 0.311 * y["C4H10"] + 0.0239 * y["H2"]
            + 0.0239 * y["CO"] - 0.0478 * y["O2"]) * 100 / sg


def calc_heat_total_live(h4: float, comb_eff: float, ph: dict, comb_products_lb_hr: float, humidity=0.002,
                         t_amb=60.0, t_exh=180.0, shell_frac_latent=0.05) -> dict:
    """CALC F10:F15 / I39:I45 evaluated live (macro + sheet formulas) for a FIXED total gas flow H4."""
    d40 = h4 - comb_products_lb_hr  # make-up air incl. humidity (A41 recycle = 0)
    d39 = humidity / (1 + humidity) * d40
    i42 = (d40 - d39 + comb_products_lb_hr) * 0.24 * (t_exh - t_amb)
    i43 = d39 * 0.455 * (t_exh - t_amb)
    i44 = shell_frac_latent * ph["F7"]
    i45 = (ph["F9"] + i42 + i43 + i44) / comb_eff
    return {"I42": i42, "I43": i43, "I44": i44, "I45": i45}


def solve_sheet_fuel_live(h4: float, ph: dict, nhv=8000.0, eff=0.9, xs=1.3, stoich=None) -> dict:
    """The sheet's chain (I45 -> B47 -> F34 -> D40 -> I42) iterated to a fixed point at the current inputs."""
    stoich = stoich or stoich_volumetric_wood()
    fuel = 1000.0
    for _ in range(200):
        prods = (1 + (1 + xs) * stoich) * fuel
        h = calc_heat_total_live(h4, eff, ph, prods)
        new = h["I45"] / nhv
        if abs(new - fuel) < 1e-9:
            break
        fuel = new
    return {"fuel_lb_hr": fuel, "I45": h["I45"], **h}


def enthalpy_check(t_exh=180.0, t_in=588.0202442816465, d58=2550.630582014884, d59=112119.05972013055,
                   a58=1217.2972486815509, a59=110785.72638679722, evap=1333.3333333333333) -> float:
    """CALC A68:F74 (absolute-datum air polynomial, ideal-gas vapor polynomial, + 970.3 latent)."""
    air = lambda t: -0.0000000009 * t ** 3 + 0.00002 * t ** 2 + 0.2322 * t + 110.82
    vap = lambda t: 0.000000002 * t ** 3 + 0.00004 * t ** 2 + 0.4322 * t + 203.75
    d72 = (d59 - d58) * air(t_exh) + d58 * vap(t_exh) + evap * 970.3
    i71 = (a59 - a58) * air(t_in) + a58 * vap(t_in)
    return i71 / d72


def scfm_sheet(h2o_lb_hr: float, total_lb_hr: float, air_density: float, vapor_density=0.0465) -> float:
    """CALC A55/A60/D60 pattern."""
    return h2o_lb_hr / 60 / vapor_density + (total_lb_hr - h2o_lb_hr) / 60 / air_density


def fan_hp_sheet(acfm: float, sp=18.0) -> float:
    """DESIGN B29."""
    return acfm * sp * 5.2 / 33000 * 1.75


def flow_drum_check(product_lb_hr=1666.6666666666665, d_ft=8.0, l_ft=60.0) -> dict:
    """FLOW R25:R28 (1.5 min, 13 lb/ft3, 0.785 D^2 L)."""
    load = product_lb_hr / 60 * 1.5
    vol = load / 13
    drum = 0.785 * d_ft ** 2 * l_ft
    return {"R25": load, "R26": vol, "R27": drum, "R28": vol / drum}


def burner_temps(q_btu_hr=15717012.186598314, products=25652.946249955363, makeup=85132.78013684186, t_amb=60.0):
    """Burner F7 (hot gas) and F8 (dryer inlet)."""
    return {"F7": q_btu_hr / 0.25 / products + t_amb, "F8": q_btu_hr / 0.24 / (products + makeup) + t_amb}


# ------------------------------------------------------------- Thermal Reactor Cal (appendix only)
def thermal_reactor(feed=680.5807622504536, mc_in=0.10, mc_out=0.03, cp=1.7, t_in=20.0, t_out=101.0) -> dict:
    d14 = feed * (mc_in - mc_out)
    d14_correct = feed * (1 - (1 - mc_in) / (1 - mc_out))
    d19 = feed * (t_out - t_in)
    d19_with_cp = feed * cp * (t_out - t_in)
    return {"D14": d14, "D14_correct": d14_correct, "D19": d19, "D19_with_cp": d19_with_cp}
