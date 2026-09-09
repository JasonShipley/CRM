# MCE Dryer Heat and Mass Balance Calculator

`MCE_Dryer_HMB_Calculator.xlsx` replaces the calculation half of Prozus report NT-HMB-2025-001
Rev 0 (the Input / CALC / COMB / FLOW / DESIGN / Burner / Emiss. sheets). Every number recalculates
from the Inputs sheet; nothing is pasted. `build_calculator.py` regenerates it.

## Sheets

| Sheet | Purpose |
|---|---|
| README | How to use, what was wrong in the original, assumptions and sources |
| Inputs | The job: feed, moistures, temperatures, site, dryer type, fuel, air-handling rules, margins, hours. Dryer-type and fuel tables live on the right. |
| HMB | Mass balance; MCE method (theoretical Btu/lb from product inlet temperature, 1,750 with losses); rigorous balance with a closed-form gas-mass calculation from the chosen inlet temperature; combustion; exhaust ACFM/SCFM; energy closure line that must read zero; drum loading and fill for the selected model. |
| Dryer Models | One table, three types. Single-pass standard sizes 3x12, 3x20, 4x20, 5x25, 6x30, 7x35, 8x40, 10x50, 12x60, 13x60 plus a custom row (any size can be built). Triple-pass rows on the same shells with a placeholder airflow factor (yellow) until Baker-Rullman ratings are loaded, plus a custom row. Z8 eight-pass rows carry the ACFM table from the original workbook. Design ACFM for single pass = drum cross-section × 350 fpm. Burners are sized to the heat loading, so rated evaporation = volume × reference loading unless a burner cap is entered. Drum inlet gas limited to 900 °F. |
| Equipment | Smallest model of the chosen type that meets airflow and evaporation with margin; burner with margin, face area at 1,200 Btu/in², burner counts; fan bhp and motor; duct at 5,000 fpm; cyclone inlet area; airlocks and infeed screw from the original DESIGN tables; annual product, fuel and fuel cost. |
| Tables | Standard motor hp, airlock and screw capacity tables (from the original DESIGN sheet). |
| Emissions | Potential to emit with factor inputs marked for confirmation against AP-42. |
| Metric | SI mirror of the key results. |
| Cases | Reference inputs for the original track B case, the Prozus case, the LETEK digestate case and the 2005 6×24 expected-performance file. |

## Default case check (3,000 lb/hr wood shavings, 50% to 10% MC, natural gas, 600 °F in, 180 °F out)

| Quantity | Original workbook | This workbook |
|---|---|---|
| Water evaporated | 1,333 lb/hr | 1,333 lb/hr |
| Fired duty | 15.7 MMBtu/hr (pasted from a 9,000 lb/hr job) | 2.33 MCE method, 2.13 rigorous at 900 °F inlet |
| Btu per lb water | 11,788 | 1,594 rigorous, 1,750 MCE governs |
| Fuel | 1,965 lb/hr | 103 lb/hr natural gas |
| Exhaust | 31,564 ACFM | 3,889 ACFM at 180 °F (900 °F inlet) |
| Dryer | five different models named | XD-60 (5'×25'); the 4'×20' misses the airflow margin by 2% |
| Fan | 157 hp | 15 hp at 10 in WC |
| Duct | 36 in | 12 in |

## Still to fill (yellow cells)

- Triple-pass drum models: model name, OD, length, design ACFM, burner. No MCE triple-pass data was found in Drive, QuickBooks or email.
- XD-60 Mk.2 burner rating; XD-72 Mk.2 drum length and burner; Z8 burners; fan hp per model.
- Emission factors for the actual fuel and material.

## Conventions

Imperial throughout, metric on its own sheet. Blue = input, black = formula, green = link to another sheet, yellow = data MCE still has to supply. Moisture contents are wet basis.
