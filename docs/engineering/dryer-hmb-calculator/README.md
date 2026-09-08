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
| Dryer Models | One table, three types. Single-pass XD Series rows filled from MCE documents (XD-36 Mk.2, XD-60 Mk.2, XD-72 Mk.2, XD-96 Mk.2). Triple-pass rows are empty, yellow, waiting for MCE drum data. Z8 eight-pass rows carry the ACFM table from the original workbook. Design ACFM for single pass = drum cross-section × 350 fpm. Rated evaporation = min(burner ÷ energy factor, volume × reference loading). |
| Equipment | Smallest model of the chosen type that meets airflow and evaporation with margin; burner with margin, face area at 1,200 Btu/in², burner counts; fan bhp and motor; duct at 5,000 fpm; cyclone inlet area; airlocks and infeed screw from the original DESIGN tables; annual product, fuel and fuel cost. |
| Tables | Standard motor hp, airlock and screw capacity tables (from the original DESIGN sheet). |
| Emissions | Potential to emit with factor inputs marked for confirmation against AP-42. |
| Metric | SI mirror of the key results. |
| Cases | Reference inputs for the original track B case, the Prozus case, the LETEK digestate case and the 2005 6×24 expected-performance file. |

## Default case check (3,000 lb/hr wood shavings, 50% to 10% MC, natural gas, 600 °F in, 180 °F out)

| Quantity | Original workbook | This workbook |
|---|---|---|
| Water evaporated | 1,333 lb/hr | 1,333 lb/hr |
| Fired duty | 15.7 MMBtu/hr (pasted from a 9,000 lb/hr job) | 2.33 MCE method, 2.35 rigorous |
| Btu per lb water | 11,788 | 1,764 |
| Fuel | 1,965 lb/hr | 103 lb/hr natural gas |
| Exhaust | 31,564 ACFM | 5,708 ACFM at 180 °F |
| Dryer | five different models named | XD-60 Mk.2 (XD-36 fails on airflow) |
| Fan | 157 hp | 20 hp at 10 in WC |
| Duct | 36 in | 16 in |

## Still to fill (yellow cells)

- Triple-pass drum models: model name, OD, length, design ACFM, burner. No MCE triple-pass data was found in Drive, QuickBooks or email.
- XD-60 Mk.2 burner rating; XD-72 Mk.2 drum length and burner; Z8 burners; fan hp per model.
- Emission factors for the actual fuel and material.

## Conventions

Imperial throughout, metric on its own sheet. Blue = input, black = formula, green = link to another sheet, yellow = data MCE still has to supply. Moisture contents are wet basis.
