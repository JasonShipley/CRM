"""Dryer emissions estimate (potential to emit) for the sizing record and the workbook's Emissions sheet.

Method
* CO2 and SO2: mass balance on the fuel (all carbon to CO2, all sulfur to SO2). Exact for the stated fuel.
* NOx, CO, VOC and burner PM: EPA AP-42 uncontrolled emission factors, converted to lb/MMBtu of fuel (HHV).
  These are screening values: the burner vendor's guarantee and the state permit govern. Verify the factors
  against the current AP-42 edition before a permit application.
* Stack PM: collector outlet loading (gr/dscf) x stack dry standard flow. Covers product fines and burner ash
  leaving the cyclone or baghouse.
* Product VOC: lb per oven-dry ton (ODT) of product. Wood dryers can emit significant VOC (often the pollutant
  that sets the permit); enter a factor from AP-42 Ch.10.6 or a stack test. 0 means not estimated.
* Tons per year at the operating hours, and potential to emit (PTE) at 8,760 hr/yr. PTE at or above 100 tpy of a
  criteria pollutant is flagged: Title V major-source review is likely (lower thresholds apply in nonattainment
  areas; check the state).
"""

from __future__ import annotations

GR_PER_LB = 7000.0
MAJOR_SOURCE_TPY = 100.0

# lb/MMBtu (HHV). Conversions use AP-42's own heating values.
EMISSION_FACTORS: dict[str, dict] = {
    "natural_gas": {"NOx": 100 / 1020, "CO": 84 / 1020, "PM": 7.6 / 1020, "VOC": 5.5 / 1020,
                    "source": "AP-42 Ch.1.4 Tables 1.4-1 and 1.4-2 (7/98): NOx 100, CO 84, PM (total) 7.6, VOC 5.5 "
                              "lb/10^6 scf, uncontrolled; divided by 1,020 BTU/scf"},
    "propane": {"NOx": 13 / 91.5, "CO": 7.5 / 91.5, "PM": 0.7 / 91.5, "VOC": 1.0 / 91.5,
                "source": "AP-42 Ch.1.5 Table 1.5-1 (7/08): NOx 13, CO 7.5, PM 0.7, VOC 1.0 lb/10^3 gal propane; "
                          "divided by 91.5 MMBtu/10^3 gal"},
    "no2_oil": {"NOx": 20 / 140, "CO": 5 / 140, "PM": 2 / 140, "VOC": 0.34 / 140,
                "source": "AP-42 Ch.1.3 Tables 1.3-1 and 1.3-3 (5/10), distillate oil, commercial boilers: NOx 20, "
                          "CO 5, PM filterable 2, NMTOC 0.34 lb/10^3 gal; divided by 140 MMBtu/10^3 gal"},
    "biomass": {"NOx": 0.22, "CO": 0.60, "PM": 0.40, "VOC": 0.017,
                "source": "AP-42 Ch.1.6 Tables 1.6-1 to 1.6-3 (9/03), dry wood (under 20% MC), uncontrolled: NOx 0.22, "
                          "CO 0.60, PM filterable 0.40, VOC 0.017 lb/MMBtu"},
}
POLLUTANTS = ("NOx", "CO", "SO2", "PM", "VOC", "CO2")


def estimate(fuel: str, fuel_lb_hr: float, hhv_btu_lb: float, co2_lb_per_lb_fuel: float, so2_lb_per_lb_fuel: float,
             stack_dscfm: float, dry_solids_lb_hr: float, hours: float, collector_gr_dscf: float,
             product_voc_lb_odt: float) -> dict:
    ef = EMISSION_FACTORS[fuel]
    mmbtu = fuel_lb_hr * hhv_btu_lb / 1e6
    burner_pm = ef["PM"] * mmbtu
    stack_pm = collector_gr_dscf * stack_dscfm * 60 / GR_PER_LB
    rows = {
        "NOx": (ef["NOx"] * mmbtu, f"AP-42 factor {ef['NOx']:.4f} lb/MMBtu HHV"),
        "CO": (ef["CO"] * mmbtu, f"AP-42 factor {ef['CO']:.4f} lb/MMBtu HHV"),
        "SO2": (so2_lb_per_lb_fuel * fuel_lb_hr, "mass balance: fuel sulfur to SO2"),
        "PM": (stack_pm, f"collector outlet {collector_gr_dscf:g} gr/dscf x {stack_dscfm:,.0f} DSCFM; burner PM before the "
                         f"collector {burner_pm:.3f} lb/hr ({ef['PM']:.4f} lb/MMBtu)"),
        "VOC": (ef["VOC"] * mmbtu + product_voc_lb_odt * dry_solids_lb_hr / 2000,
                f"burner {ef['VOC']:.4f} lb/MMBtu + product {product_voc_lb_odt:g} lb/ODT"),
        "CO2": (co2_lb_per_lb_fuel * fuel_lb_hr, "mass balance: fuel carbon to CO2" +
                (" (biogenic)" if fuel == "biomass" else "")),
    }
    out = {}
    for k in POLLUTANTS:
        lb_hr, basis = rows[k]
        out[k] = {"lb_hr": lb_hr, "tpy": lb_hr * hours / 2000, "pte_tpy": lb_hr * 8760 / 2000, "basis": basis}
    return {"pollutants": out, "fuel_mmbtu_hr_hhv": mmbtu, "burner_pm_lb_hr": burner_pm, "factor_source": ef["source"],
            "product_voc_estimated": product_voc_lb_odt > 0,
            "major_source_flags": [k for k in ("NOx", "CO", "SO2", "PM", "VOC") if out[k]["pte_tpy"] >= MAJOR_SOURCE_TPY],
            "notes": ["Screening estimate. The burner vendor guarantee and the state permit govern; verify factors "
                      "against the current AP-42 edition.",
                      "Standard conditions: SCFM at 70 F, 29.92 in. Hg (EPA uses 68 F; 0.4% difference)."]}
