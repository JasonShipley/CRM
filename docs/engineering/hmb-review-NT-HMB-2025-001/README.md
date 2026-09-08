# Review of NT-HMB-2025-001 Rev 0 (Prozus biomass heat and mass balance)

Internal engineering review, 8 Sep 2026. Full findings with cell references: `review.html`.
Source file reviewed: `Biomass_HMB_Report_Doc._no._NTHMB2025001_REV_0.xlsm` (not committed; MCE-confidential).

## Bottom line

The workbook holds two unrelated calculations and neither closes.

- **Track A, the Prozus report** (Assumption, Combustion, Rotary dryer Cal, Thermal Reactor Cal):
  fuel is overstated 1.9× because flue-gas mass is divided by a 30%-excess-air yield (8.95 kg/kg,
  ~1,750°C gas) while the same gas is valued at 1,100°C. 47% of the fuel energy vanishes.
  The dryer heats solids to 375°C with gas leaving at 82°C. The reactor ignores devolatilization,
  so "912 kg/h product, 67% of feed" should be about 640–690 kg/h. The imperial mirror columns are
  a different calculation from the metric ones (evaporation term missing).
- **Track B, the MCE dryer calculator** (Input, CALC, COMB, FLOW, DESIGN, Burner, Emiss.):
  CALC F4:F15, H4, I39:I45, B47, D48 are pasted values from a 9,000 lb/hr-evaporation job, while
  Input says 1,333 lb/hr. Burner 15.7 MMBtu/hr, fan 31,564 ACFM, 36 in duct, 157 hp and all
  emissions tonnages inherit a 6.5× error. Input!A28 already reads "INLET TEMP IS NOT CORRECT".
- **Orphaned**: the coal/char boiler blend at the top of Combustion (negative oxygen), Cost Sheet,
  Est. Cost Analysis (#DIV/0!, #VALUE!), Sheet1, hidden Module1.

What is right: combustion stoichiometry in both tracks, the metric water-removed formula, the
enthalpy-balance method for mixed gas, the Input mass balance, emission factors, airlock and screw
capacity tables, and unit conversions.

## Corrected figures

| Quantity | Report | Corrected |
|---|---|---|
| Dryer heat demand (track A) | 1.67 GJ/h | 1.14 GJ/h |
| Dryer mixed gas 309→82°C | 6,956 kg/h | 4,790 kg/h |
| Dryer fuel | 210.7 kg/h | ~76 kg/h (110 if only the flue-gas error is fixed) |
| Reactor fuel | 79.5 kg/h | ~42 kg/h (reactor demand still needs rework) |
| Total fuel, % of feed | 290 kg/h, 21% | ~120 kg/h, 9% |
| Product at 3% MC | 912 kg/h, 67% | ~685 kg/h, 50% (25% devolatilization) |
| Track B dryer duty | 15.7 MMBtu/hr | ~2.3 MMBtu/hr |
| Track B fuel | 1,965 lb/hr | ~290 lb/hr |
| Track B exhaust | 31,564 ACFM | ~5,000 ACFM |
| Track B dryer from Input size table | 10'×40' | 6'×24' |

## Actions

1. Return to Prozus with findings 1, 3, 4, 5, 6, 8, 11 (numbering per `review.html`). Ask for one
   metric calculation with an energy-closure line per sheet and a stated reactor heating mode.
2. Rebuild CALC on formulas from Input before the MCE calculator is used on another quote; add a
   "Btu per lb water evaporated" sanity flag (1,400–2,200).
3. Quote nothing from this file for burner, fan, duct or emissions until both are done.
