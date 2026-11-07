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
MATERIALS: dict[str, dict] = {
    "wood_shavings": {
        "label": "Wood shavings / planer shavings",
        "cp": v(0.55, "SHEET Input A4 (material specific heat, BTU/lb-F)"),
        "bulk_density_dry": v(8.0, "SHEET Input A6 (dry bulk density; FLOW R26 used 13 and DESIGN B10 used 6)"),
        "particle_size_in": v(0.40, "Volume-equivalent diameter of a 0.09 in. thick shaving (SHEET FLOW C3: 0.080 to "
                                    "0.100 in.) with a 0.5 x 0.75 in. face; face size " + MCE_CONFIRM),
        "particle_density": v(28.0, "USDA Wood Handbook FPL-GTR-282 Ch.5: softwood oven-dry SG about 0.35 to 0.55; "
                                    "0.45 x 62.4 = 28 lb/ft3. " + MCE_CONFIRM),
        "sphericity": v(0.3, "Flake-shaped particle. " + MCE_CONFIRM),
        "ver_range": v([1.5, 4.0], "Volumetric evaporation design range, lb H2O/hr-ft3. " + MCE_CONFIRM),
        "residence_target_min": v(8.0, "Target drum residence time. " + MCE_CONFIRM),
        "max_product_temp_F": v(250.0, "Wood: limit to keep VOC release and scorch down. " + MCE_CONFIRM),
        "heat_sensitivity": v("moderate", MCE_CONFIRM),
        "fire_risk": v("high", "Dry fine wood: high fire and dust deflagration risk. " + MCE_CONFIRM),
        "sticky": v(False, MCE_CONFIRM),
        "is_wood": True,
    },
    "sawdust": {
        "label": "Sawdust",
        "cp": v(0.55, "SHEET Input A4"),
        "bulk_density_dry": v(10.0, MCE_CONFIRM),
        "particle_size_in": v(0.04, "About 1 mm. " + MCE_CONFIRM),
        "particle_density": v(28.0, "USDA Wood Handbook (SG about 0.45). " + MCE_CONFIRM),
        "sphericity": v(0.5, MCE_CONFIRM),
        "ver_range": v([1.5, 4.0], MCE_CONFIRM),
        "residence_target_min": v(8.0, MCE_CONFIRM),
        "max_product_temp_F": v(250.0, MCE_CONFIRM),
        "heat_sensitivity": v("moderate", MCE_CONFIRM),
        "fire_risk": v("high", MCE_CONFIRM),
        "sticky": v(False, MCE_CONFIRM),
        "is_wood": True,
    },
    "wood_chips": {
        "label": "Wood chips / hog fuel",
        "cp": v(0.55, "SHEET Input A4"),
        "bulk_density_dry": v(12.0, MCE_CONFIRM),
        "particle_size_in": v(0.75, MCE_CONFIRM),
        "particle_density": v(28.0, "USDA Wood Handbook (SG about 0.45). " + MCE_CONFIRM),
        "sphericity": v(0.5, MCE_CONFIRM),
        "ver_range": v([1.5, 4.0], MCE_CONFIRM),
        "residence_target_min": v(15.0, MCE_CONFIRM),
        "max_product_temp_F": v(250.0, MCE_CONFIRM),
        "heat_sensitivity": v("low", MCE_CONFIRM),
        "fire_risk": v("moderate", MCE_CONFIRM),
        "sticky": v(False, MCE_CONFIRM),
        "is_wood": True,
    },
    "ag_residue": {
        "label": "Ag residue (chopped straw, stover, hulls)",
        "cp": v(0.50, MCE_CONFIRM),
        "bulk_density_dry": v(6.0, MCE_CONFIRM),
        "particle_size_in": v(0.5, MCE_CONFIRM),
        "particle_density": v(20.0, MCE_CONFIRM),
        "sphericity": v(0.25, MCE_CONFIRM),
        "ver_range": v([1.5, 4.0], MCE_CONFIRM),
        "residence_target_min": v(10.0, MCE_CONFIRM),
        "max_product_temp_F": v(220.0, MCE_CONFIRM),
        "heat_sensitivity": v("moderate", MCE_CONFIRM),
        "fire_risk": v("high", MCE_CONFIRM),
        "sticky": v(False, MCE_CONFIRM),
        "is_wood": False,
    },
    "distillers_grains": {
        "label": "Distillers grains / wet feed co-products",
        "cp": v(0.45, MCE_CONFIRM),
        "bulk_density_dry": v(30.0, MCE_CONFIRM),
        "particle_size_in": v(0.06, MCE_CONFIRM),
        "particle_density": v(70.0, MCE_CONFIRM),
        "sphericity": v(0.7, MCE_CONFIRM),
        "ver_range": v([1.0, 3.0], MCE_CONFIRM),
        "residence_target_min": v(20.0, MCE_CONFIRM),
        "max_product_temp_F": v(200.0, "Protein damage above this. " + MCE_CONFIRM),
        "heat_sensitivity": v("high", MCE_CONFIRM),
        "fire_risk": v("moderate", MCE_CONFIRM),
        "sticky": v(True, "Wet syrup fraction is sticky; backmix normally needed. " + MCE_CONFIRM),
        "is_wood": False,
    },
    "custom": {
        "label": "Custom (enter every property)",
        "cp": v(0.55, "Generic placeholder (SHEET Input A4). Enter the material value."),
        "bulk_density_dry": v(8.0, "Generic placeholder (SHEET Input A6). Enter the material value."),
        "particle_size_in": v(0.25, "Generic placeholder. Enter the material value."),
        "particle_density": v(40.0, "Generic placeholder. Enter the material value."),
        "sphericity": v(0.6, "Generic placeholder."),
        "ver_range": v([1.5, 4.0], "Generic placeholder. " + MCE_CONFIRM),
        "residence_target_min": v(10.0, "Generic placeholder."),
        "max_product_temp_F": v(250.0, "Generic placeholder."),
        "heat_sensitivity": v("moderate", "Generic placeholder."),
        "fire_risk": v("moderate", "Generic placeholder."),
        "sticky": v(False, "Generic placeholder."),
        "is_wood": False,
    },
}

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
        "label": "Propane (HD-5 taken as 100% C3H8)", "kind": "gas",
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
        "label": "Biomass (as-received wood fuel)", "kind": "solid",
        "ultimate": v(WOOD_DRY_ULTIMATE, WOOD_DRY_ULTIMATE_SOURCE),
        "heating_value": v(8500.0, "SHEET Input G7 (net BTU/lb). Taken as DRY basis net. " + MCE_CONFIRM),
        "heating_value_basis": v("net_dry", MCE_CONFIRM),
        "moisture_wb": v(10.0, "Not given in the sheet; same as dry wood (SHEET COMB C10). " + MCE_CONFIRM),
        "density": v(15.0, "SHEET Input H7"),
        "excess_air_pct": v(200.0, "SHEET Input I7 (2 entered; read as 200% excess air)"),
        "cp": v(0.40, "Wood fuel at 10% MC (fuel sensible heat only). " + MCE_CONFIRM),
        "furnace_efficiency": v(0.93, "MCE (Jason 2026-11-07): about 93% for biomass"),
    },
    "dry_wood": {
        "label": "Dry wood (dried product as fuel)", "kind": "solid",
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
