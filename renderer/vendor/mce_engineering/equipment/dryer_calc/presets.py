"""Pull-down presets: materials, fuels and the standard drum list.

Every value carries a source note. "SHEET <cell>" means the value was carried over from
"Coding mass balance for Thermal reactor.xlsm" as an assumption (not as validated math).
"MCE assumption, confirm" means nobody has verified it yet; it is listed in
docs/dryer_calc/assumptions_for_confirmation.md and every run that uses it is flagged.
"""

from __future__ import annotations

MCE_CONFIRM = "MCE assumption, confirm"


def v(value, source: str) -> dict:
    return {"value": value, "source": source}


# ----------------------------------------------------------------------------- materials
# ----------------------------------------------------------------------------- specific heat of dry solids
T_CP_MEAN_C = (130.0 - 32.0) / 1.8  # dry-solids cp evaluated at 130 F, the mean of a 60 F feed and 200 F product
KJKGK_TO_BTULBF = 0.238845897


def cp_wood_dry(t_c: float = T_CP_MEAN_C) -> float:
    """USDA Wood Handbook (FPL-GTR-282) Ch.4: c0 = 0.1031 + 0.003867 T (kJ/kg-K, T in K), oven-dry wood."""
    return (0.1031 + 0.003867 * (t_c + 273.15)) * KJKGK_TO_BTULBF


# Choi & Okos (1986) component equations, kJ/kg-K with t in C (ASHRAE Handbook Refrigeration, Ch.19 Table 1)
CHOI_OKOS = {
    "protein": (2.0082, 1.2089e-3, -1.3129e-6),
    "fat": (1.9842, 1.4733e-3, -4.8008e-6),
    "carbohydrate": (1.5488, 1.9625e-3, -5.9399e-6),
    "fiber": (1.8459, 1.8306e-3, -4.6509e-6),
    "ash": (1.0926, 1.8896e-3, -3.6817e-6),
}


def cp_choi_okos(dry_comp_pct: dict[str, float], t_c: float = T_CP_MEAN_C) -> float:
    """Dry-solids cp (BTU/lb-F) from a dry-basis composition (protein, fat, carbohydrate, fiber, ash; sums to 100)."""
    tot = sum(dry_comp_pct.values())
    cp = sum(dry_comp_pct[k] / tot * (a + b * t_c + c * t_c * t_c) for k, (a, b, c) in CHOI_OKOS.items())
    return cp * KJKGK_TO_BTULBF


def _comp(protein, fat, carbohydrate, fiber, ash):
    return {"protein": protein, "fat": fat, "carbohydrate": carbohydrate, "fiber": fiber, "ash": ash}


WOOD_CP_SOURCE = ("USDA Wood Handbook FPL-GTR-282 Ch.4, oven-dry wood c0 = 0.1031 + 0.003867 T(K) kJ/kg-K at 130 F. "
                  "Replaces the sheet's 0.55, which counts part of the water twice (water is added separately).")


def _food(label, comp, comp_src, **kw):
    return {"label": label, "composition": v(comp, comp_src),
            "cp": v(cp_choi_okos(comp), "Choi & Okos (1986), ASHRAE Refrigeration Handbook Ch.19, from the dry "
                                        "composition at 130 F"), **kw}


def _wood(label, **kw):
    return {"label": label, "composition": v(None, "wood"), "cp": v(cp_wood_dry(), WOOD_CP_SOURCE), "is_wood": True,
            **kw}


# Every product: dry-solids cp, dry bulk density, design particle (volume-equivalent dia, envelope density,
# sphericity), drum design rules (VER range, residence), limits and classes, and typical moisture in/out
# (defaults only: the salesperson types the customer's numbers).
MATERIALS: dict[str, dict] = {
    "wood_shavings": _wood(
        "Wood shavings",
        bulk_density_dry=v(8.0, "SHEET Input A6"),
        particle_size_in=v(0.40, "Volume-equivalent dia of a 0.09 in. shaving (SHEET FLOW C3) with a 0.5 x 0.75 in. "
                                 "face; face size " + MCE_CONFIRM),
        particle_density=v(28.0, "USDA Wood Handbook: oven-dry SG about 0.45"), sphericity=v(0.3, "flakes. " + MCE_CONFIRM),
        ver_range=v([1.5, 4.0], MCE_CONFIRM), residence_target_min=v(8.0, MCE_CONFIRM),
        max_product_temp_F=v(250.0, MCE_CONFIRM), heat_sensitivity=v("moderate", MCE_CONFIRM),
        fire_risk=v("high", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM),
        mc_in=v(50.0, "test case"), product_temp_F=v(180.0, "product leaves at the exhaust temperature (the sheet used 200 F with a 180 F exhaust). " + MCE_CONFIRM), mc_out=v(10.0, "SHEET Input F15")),
    "sawdust": _wood(
        "Sawdust",
        bulk_density_dry=v(12.0, MCE_CONFIRM), particle_size_in=v(0.04, "about 1 mm. " + MCE_CONFIRM),
        particle_density=v(28.0, "USDA Wood Handbook: SG about 0.45"), sphericity=v(0.5, MCE_CONFIRM),
        ver_range=v([1.5, 4.0], MCE_CONFIRM), residence_target_min=v(8.0, MCE_CONFIRM),
        max_product_temp_F=v(250.0, MCE_CONFIRM), heat_sensitivity=v("moderate", MCE_CONFIRM),
        fire_risk=v("high", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM), mc_in=v(50.0, MCE_CONFIRM),
        product_temp_F=v(180.0, "product leaves at the exhaust temperature (the sheet used 200 F with a 180 F exhaust). " + MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "wood_chips": _wood(
        "Wood chips",
        bulk_density_dry=v(12.0, MCE_CONFIRM), particle_size_in=v(0.75, MCE_CONFIRM),
        particle_density=v(28.0, "USDA Wood Handbook: SG about 0.45"), sphericity=v(0.5, MCE_CONFIRM),
        ver_range=v([1.5, 4.0], MCE_CONFIRM), residence_target_min=v(15.0, MCE_CONFIRM),
        max_product_temp_F=v(250.0, MCE_CONFIRM), heat_sensitivity=v("low", MCE_CONFIRM),
        fire_risk=v("moderate", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM), mc_in=v(50.0, MCE_CONFIRM),
        product_temp_F=v(180.0, "product leaves at the exhaust temperature (the sheet used 200 F with a 180 F exhaust). " + MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "bark": _wood(
        "Bark / hog fuel",
        bulk_density_dry=v(15.0, MCE_CONFIRM), particle_size_in=v(1.0, MCE_CONFIRM),
        particle_density=v(30.0, "bark SG about 0.48. " + MCE_CONFIRM), sphericity=v(0.45, MCE_CONFIRM),
        ver_range=v([1.5, 4.0], MCE_CONFIRM), residence_target_min=v(20.0, MCE_CONFIRM),
        max_product_temp_F=v(250.0, MCE_CONFIRM), heat_sensitivity=v("low", MCE_CONFIRM),
        fire_risk=v("moderate", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM), mc_in=v(55.0, MCE_CONFIRM),
        product_temp_F=v(180.0, "product leaves at the exhaust temperature (the sheet used 200 F with a 180 F exhaust). " + MCE_CONFIRM), mc_out=v(15.0, MCE_CONFIRM)),
    "carrots": _food(
        "Carrots (culls / pomace)", _comp(7.9, 2.0, 57.8, 23.9, 8.3),
        "USDA SR Legacy 11124 carrots raw (water 88.3, protein 0.93, fat 0.24, carbohydrate 9.58 incl. fiber 2.8, "
        "ash 0.97 g/100 g) on a dry basis",
        bulk_density_dry=v(22.0, MCE_CONFIRM), particle_size_in=v(0.25, "diced or shredded. " + MCE_CONFIRM),
        particle_density=v(50.0, MCE_CONFIRM), sphericity=v(0.6, MCE_CONFIRM), ver_range=v([1.0, 3.0], MCE_CONFIRM),
        residence_target_min=v(25.0, MCE_CONFIRM), max_product_temp_F=v(180.0, "sugars caramelize. " + MCE_CONFIRM),
        heat_sensitivity=v("high", MCE_CONFIRM), fire_risk=v("low", MCE_CONFIRM),
        sticky=v(True, "sugary when wet. " + MCE_CONFIRM), mc_in=v(85.0, MCE_CONFIRM), product_temp_F=v(160.0, MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "tomato_pomace": _food(
        "Tomato pomace", _comp(20.0, 12.0, 14.0, 50.0, 4.0),
        "Dried tomato pomace, typical feed analyses (CP about 20%, fat 10 to 15%, NDF about 50%, ash 3 to 5%). "
        + MCE_CONFIRM,
        bulk_density_dry=v(18.0, MCE_CONFIRM), particle_size_in=v(0.10, "skins and seeds. " + MCE_CONFIRM),
        particle_density=v(45.0, MCE_CONFIRM), sphericity=v(0.4, MCE_CONFIRM), ver_range=v([1.0, 3.0], MCE_CONFIRM),
        residence_target_min=v(20.0, MCE_CONFIRM), max_product_temp_F=v(180.0, MCE_CONFIRM),
        heat_sensitivity=v("high", MCE_CONFIRM), fire_risk=v("low", MCE_CONFIRM), sticky=v(True, MCE_CONFIRM),
        mc_in=v(75.0, MCE_CONFIRM), product_temp_F=v(160.0, MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "walnut_hulls": _food(
        "Walnut hulls", _comp(6.0, 2.0, 48.0, 35.0, 9.0), "Green walnut hulls, dry basis estimate. " + MCE_CONFIRM,
        bulk_density_dry=v(20.0, MCE_CONFIRM), particle_size_in=v(0.5, MCE_CONFIRM),
        particle_density=v(45.0, MCE_CONFIRM), sphericity=v(0.5, MCE_CONFIRM), ver_range=v([1.0, 3.0], MCE_CONFIRM),
        residence_target_min=v(20.0, MCE_CONFIRM), max_product_temp_F=v(200.0, MCE_CONFIRM),
        heat_sensitivity=v("moderate", MCE_CONFIRM), fire_risk=v("moderate", MCE_CONFIRM),
        sticky=v(False, MCE_CONFIRM), mc_in=v(65.0, MCE_CONFIRM), product_temp_F=v(180.0, MCE_CONFIRM), mc_out=v(12.0, MCE_CONFIRM)),
    "almond_skins": _food(
        "Almond skins", _comp(11.0, 12.0, 32.0, 42.0, 3.0), "Blanched almond skins, dry basis estimate. " + MCE_CONFIRM,
        bulk_density_dry=v(15.0, MCE_CONFIRM), particle_size_in=v(0.08, MCE_CONFIRM),
        particle_density=v(40.0, MCE_CONFIRM), sphericity=v(0.3, "flakes. " + MCE_CONFIRM),
        ver_range=v([1.0, 3.0], MCE_CONFIRM), residence_target_min=v(15.0, MCE_CONFIRM),
        max_product_temp_F=v(180.0, MCE_CONFIRM), heat_sensitivity=v("high", MCE_CONFIRM),
        fire_risk=v("high", "fine, oily dust. " + MCE_CONFIRM), sticky=v(False, MCE_CONFIRM),
        mc_in=v(55.0, MCE_CONFIRM), product_temp_F=v(160.0, MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "ag_residue": _food(
        "Ag residue (straw, stover, hulls)", _comp(4.0, 1.5, 12.5, 75.0, 7.0),
        "Cereal straw / corn stover, typical feed analyses (CP about 4%, NDF about 75%). " + MCE_CONFIRM,
        bulk_density_dry=v(6.0, MCE_CONFIRM), particle_size_in=v(0.5, MCE_CONFIRM),
        particle_density=v(20.0, MCE_CONFIRM), sphericity=v(0.25, MCE_CONFIRM), ver_range=v([1.5, 4.0], MCE_CONFIRM),
        residence_target_min=v(10.0, MCE_CONFIRM), max_product_temp_F=v(220.0, MCE_CONFIRM),
        heat_sensitivity=v("moderate", MCE_CONFIRM), fire_risk=v("high", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM),
        mc_in=v(40.0, MCE_CONFIRM), product_temp_F=v(180.0, MCE_CONFIRM), mc_out=v(12.0, MCE_CONFIRM)),
    "petfood": _food(
        "Pet food ingredients / kibble", _comp(28.0, 15.0, 45.0, 4.0, 8.0),
        "Typical dry dog food guaranteed analysis on a dry basis. " + MCE_CONFIRM,
        bulk_density_dry=v(28.0, MCE_CONFIRM), particle_size_in=v(0.25, "kibble. " + MCE_CONFIRM),
        particle_density=v(60.0, MCE_CONFIRM), sphericity=v(0.8, MCE_CONFIRM), ver_range=v([1.0, 3.0], MCE_CONFIRM),
        residence_target_min=v(15.0, MCE_CONFIRM), max_product_temp_F=v(200.0, MCE_CONFIRM),
        heat_sensitivity=v("high", MCE_CONFIRM), fire_risk=v("moderate", "fat. " + MCE_CONFIRM),
        sticky=v(False, MCE_CONFIRM), mc_in=v(30.0, MCE_CONFIRM), product_temp_F=v(180.0, MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "alfalfa": _food(
        "Alfalfa", _comp(18.0, 2.5, 27.5, 42.0, 10.0),
        "Alfalfa, typical feed analyses (CP 17 to 20%, NDF about 42%, ash about 10%). " + MCE_CONFIRM,
        bulk_density_dry=v(10.0, "chopped. " + MCE_CONFIRM), particle_size_in=v(0.5, "chopped. " + MCE_CONFIRM),
        particle_density=v(25.0, MCE_CONFIRM), sphericity=v(0.25, MCE_CONFIRM), ver_range=v([1.5, 4.0], MCE_CONFIRM),
        residence_target_min=v(10.0, MCE_CONFIRM), max_product_temp_F=v(220.0, MCE_CONFIRM),
        heat_sensitivity=v("moderate", MCE_CONFIRM), fire_risk=v("high", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM),
        mc_in=v(70.0, "fresh chopped alfalfa. " + MCE_CONFIRM), product_temp_F=v(180.0, MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "hay": _food(
        "Hay (grass)", _comp(10.0, 2.5, 19.5, 60.0, 8.0),
        "Grass hay, typical feed analyses (CP about 10%, NDF about 60%). " + MCE_CONFIRM,
        bulk_density_dry=v(6.0, "chopped. " + MCE_CONFIRM), particle_size_in=v(1.0, MCE_CONFIRM),
        particle_density=v(20.0, MCE_CONFIRM), sphericity=v(0.2, MCE_CONFIRM), ver_range=v([1.5, 4.0], MCE_CONFIRM),
        residence_target_min=v(15.0, MCE_CONFIRM), max_product_temp_F=v(200.0, MCE_CONFIRM),
        heat_sensitivity=v("moderate", MCE_CONFIRM), fire_risk=v("high", MCE_CONFIRM), sticky=v(False, MCE_CONFIRM),
        mc_in=v(30.0, MCE_CONFIRM), product_temp_F=v(180.0, MCE_CONFIRM), mc_out=v(12.0, MCE_CONFIRM)),
    "distillers_grains": _food(
        "Distillers grains", _comp(30.0, 10.0, 20.0, 35.0, 5.0),
        "DDGS, typical analyses (CP about 30%, fat about 10%, NDF about 35%, ash about 5%). " + MCE_CONFIRM,
        bulk_density_dry=v(30.0, MCE_CONFIRM), particle_size_in=v(0.06, MCE_CONFIRM),
        particle_density=v(70.0, MCE_CONFIRM), sphericity=v(0.7, MCE_CONFIRM), ver_range=v([1.0, 3.0], MCE_CONFIRM),
        residence_target_min=v(20.0, MCE_CONFIRM), max_product_temp_F=v(200.0, "protein damage above this. "
                                                                        + MCE_CONFIRM),
        heat_sensitivity=v("high", MCE_CONFIRM), fire_risk=v("moderate", MCE_CONFIRM),
        sticky=v(True, "syrup fraction; backmix normally needed. " + MCE_CONFIRM),
        mc_in=v(65.0, "wet cake plus syrup. " + MCE_CONFIRM), product_temp_F=v(180.0, MCE_CONFIRM), mc_out=v(10.0, MCE_CONFIRM)),
    "custom": _wood(
        "Custom (enter the properties)",
        bulk_density_dry=v(8.0, "Generic placeholder. Enter the material value."),
        particle_size_in=v(0.25, "Generic placeholder."), particle_density=v(40.0, "Generic placeholder."),
        sphericity=v(0.6, "Generic placeholder."), ver_range=v([1.5, 4.0], "Generic placeholder."),
        residence_target_min=v(10.0, "Generic placeholder."), max_product_temp_F=v(250.0, "Generic placeholder."),
        heat_sensitivity=v("moderate", "Generic placeholder."), fire_risk=v("moderate", "Generic placeholder."),
        sticky=v(False, "Generic placeholder."), mc_in=v(50.0, "Generic placeholder."),
        product_temp_F=v(200.0, "Generic placeholder."), mc_out=v(10.0, "Generic placeholder.")),
}
MATERIALS["custom"]["is_wood"] = False
MATERIALS["custom"]["cp"] = v(round(cp_wood_dry(), 4), "Generic placeholder (oven-dry wood). Enter the material value.")
for _m in MATERIALS.values():
    _m.setdefault("is_wood", False)

# ----------------------------------------------------------------------------- fuel analyses
# Dry basis mass %, must close to 100 with ash. Moisture is a separate input (wet basis).
WOOD_DRY_ULTIMATE = {"C": 50.0, "H": 6.0, "O": 43.1, "N": 0.2, "S": 0.02, "ash": 0.68}
WOOD_DRY_ULTIMATE_SOURCE = ("Typical softwood, dry basis (C about 50%, H 6%, O 43%, N 0.1 to 0.3%, ash under 1%; "
                            "e.g. Phyllis2 and USDA FPL averages). Replaces SHEET CALC A23:A27, which sums to 91.03% "
                            "with N 4.69%. " + MCE_CONFIRM)
# Kept for the audit trail only: they are NOT used as defaults.
SHEET_CALC_WOOD = {"C": 43.24, "H": 5.65, "O": 37.4, "N": 4.69, "S": 0.05, "ash": 0.0}  # sums to 91.03
SHEET_COMB_WOOD_AS_FIRED = {"C": 47.53, "H": 5.367495792, "N": 0.35, "H2O": 10.0, "ash": 2.0, "S": 0.008,
                            "O": 34.74}  # COMB C7:C13, as fired

NG_COMPOSITION = {"CH4": 95.2, "C2H6": 2.5, "C3H8": 0.2, "C4H10": 0.06, "H2": 0.02, "O2": 0.02, "N2": 2.0}
NG_COMPOSITION_SOURCE = ("SHEET CALC C23:C29 (CH4 95.2, C2H6 2.5, C3H8 0.2, C4H10 0.06, H2 0.02, O2 0.02 = 98.00%). "
                         "The missing 2.00% is assigned to N2 (inert) so the analysis closes. " + MCE_CONFIRM)
NO2_OIL_ULTIMATE = {"C": 87.2, "H": 12.5, "O": 0.04, "N": 0.01, "S": 0.25, "ash": 0.0}

FUELS: dict[str, dict] = {
    "natural_gas": {
        "label": "Natural gas", "kind": "gas",
        "composition": v(NG_COMPOSITION, NG_COMPOSITION_SOURCE),
        "heating_value": v(20700.0, "Net (LHV) computed from the composition: 20,712 BTU/lb. SHEET Input G6 22,800 "
                                    "is the gross (HHV) value labeled net"),
        "heating_value_basis": v("net_as_fired", "SHEET Input G5 label"),
        "moisture_wb": v(0.0, "Dry gas"),
        "density": v(0.044, "SHEET Input H6 (lb/ft3)"),
        "excess_air_pct": v(25.0, "SHEET Input I6 (0.25 entered; read as 25% excess air)"),
        "sg": v(0.587, "SHEET CALC J24"),
        "cp": v(0.53, "Methane gas cp at 60 F (fuel sensible heat only; negligible)."),
        "furnace_efficiency": v(0.98, "MCE (Jason 2026-11-07): about 98% for gas"),
    },
    "propane": {
        "label": "Propane", "kind": "gas",
        "composition": v({"C3H8": 100.0}, "HD-5 is at least 90% propane; pure C3H8 assumed. " + MCE_CONFIRM),
        "heating_value": v(19900.0, "SHEET Input G8"),
        "heating_value_basis": v("net_as_fired", "SHEET Input G5 label"),
        "moisture_wb": v(0.0, "Dry gas"),
        "density": v(0.048, "SHEET Input H8 (lb/ft3). Propane vapor is about 0.114 lb/ft3 at 70 F; flagged."),
        "excess_air_pct": v(30.0, "SHEET Input I8"),
        "sg": v(None, "computed"),
        "cp": v(0.39, "Propane gas cp (fuel sensible heat only)."),
        "furnace_efficiency": v(0.98, "MCE (Jason 2026-11-07): about 98% for gas"),
    },
    "no2_oil": {
        "label": "#2 fuel oil", "kind": "liquid",
        "ultimate": v(NO2_OIL_ULTIMATE, "Typical No. 2 distillate (C 87.2, H 12.5, S 0.25). " + MCE_CONFIRM),
        "heating_value": v(18500.0, "SHEET Input G9"),
        "heating_value_basis": v("net_as_fired", "SHEET Input G5 label"),
        "moisture_wb": v(0.0, "Water-free oil"),
        "density": v(55.6, "SHEET Input H9 (lb/ft3, 7.43 lb/gal)"),
        "excess_air_pct": v(50.0, "SHEET Input I9"),
        "cp": v(0.45, "Fuel oil cp (fuel sensible heat only)."),
        "furnace_efficiency": v(0.98, "Same as gas (98%). " + MCE_CONFIRM),
    },
    "biomass": {
        "label": "Biomass burner (wood fuel)", "kind": "solid",
        "ultimate": v(WOOD_DRY_ULTIMATE, WOOD_DRY_ULTIMATE_SOURCE),
        "heating_value": v(8000.0, "SHEET Input G10; dry basis net (Jason 2026-11-07). Cross-check: Jackson quote "
                                   "260714a-dtm, 6.5 MMBtu/hr at 903 lb/hr dry dust = 7,198 BTU/lb as fired, vs "
                                   "7,095 here at 10% MC"),
        "heating_value_basis": v("net_dry", "Jason 2026-11-07"),
        "moisture_wb": v(10.0, "SHEET COMB C10 (fuel water 10%)"),
        "density": v(12.0, "SHEET Input H10"),
        "excess_air_pct": v(130.0, "SHEET Input I10 (1.3 entered; CALC B33 applies it as (1 + 1.3) x stoich, "
                                   "i.e. 130% excess air)"),
        "cp": v(0.40, "Wood fuel at 10% MC (fuel sensible heat only). " + MCE_CONFIRM),
        "furnace_efficiency": v(0.93, "MCE (Jason 2026-11-07): about 93% for biomass"),
    },
}

# Sane ranges for LHV as fired, BTU/lb, by fuel (outside -> flag). Wood: LHV dry 7,600 to 8,400.
LHV_AS_FIRED_SANE = {"natural_gas": (19500, 21500), "propane": (19500, 20100), "no2_oil": (17800, 18800)}
WOOD_LHV_DRY_SANE = (7400.0, 8600.0)

# ----------------------------------------------------------------------------- standard drums
# Placeholder grid (Jason 2026-11-07): whole-foot diameters up to 13 ft, lengths normally up to 60 ft,
# 65 to 80 ft possible (flagged). Prior MCE builds 3x12, 3x20 and 8x40 are on the grid.
STANDARD_DRUM_DIAMETERS_FT = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
STANDARD_DRUM_LENGTHS_FT = [10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
STANDARD_DRUM_MAX_NORMAL_LENGTH_FT = 60
STANDARD_DRUM_SOURCE = ("MCE (Jason 2026-11-07): whole-foot diameters 3 to 13 ft; lengths to 60 ft normally, 65 to "
                        "80 ft flagged as long. Lengths in 5 ft steps (plus 12 ft) until MCE sets its list.")

# NEMA MG-1 preferred horsepower ratings
NEMA_HP = [1, 1.5, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450,
           500, 600, 700, 800]
