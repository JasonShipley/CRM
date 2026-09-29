# CLAUDE.md

## Engineering & Quoting Reference Documents

- **MAC cyclone catalog** (MAC Equipment, Sabetha, KS — "H.E. Collector" data sheet, effective 11-1-86):
  https://drive.google.com/file/d/1XFFyBLFCypgEWivt2x9HU1XLIMHVcuUg/view
  This is the original manufacturer catalog MCE modeled its own HE-series cyclone line from (dimensions,
  flange standards, construction gauges, and the #21 through #47 size range with min/opt/max CFM ratings
  per size). MCE's own `cyclone-cfm-calculator.html` sizing table traces back to this source.

  Key implication: sizes exist in this source catalog (e.g. **HE-27**, ~27" dia, ~3,524-4,028 CFM range)
  that are **not** currently in MCE's Zoho CRM product catalog as priced, sellable SKUs. MCE's real Zoho
  cyclone catalog jumps directly from HE-24 (up to 3,250 CFM, $6,950) to HE-30 (up to 4,900 CFM, $9,950) —
  it skips HE-27 and likely other intermediate sizes. A size missing from Zoho is still buildable per this
  MAC source data, but has no established sell price and would need to be engineered/costed from scratch
  rather than looked up.

  When sizing a cyclone for a quote: check the real Zoho `Products` module first for an existing priced
  SKU (search by "HE-" model number). Only fall back to the MAC catalog's dimensional data if a
  custom/intermediate size is genuinely needed and worth costing out.

## Customer-Facing Quote/Proposal Rules (apply to every quote, every item)

- **Always check the real Zoho CRM `Products` module first, for every item, before writing a description
  or price.** MCE has actual catalog records (name, full description, current `Unit_Price`) for most of
  its standard equipment — cyclones, cooler control panels, ductwork allowances, coolers, fans, dryers,
  etc. Search Products by keyword/model number before inventing or estimating a description or price. Use
  the real description as the basis for the item's copy (condensed if very long — e.g. a full PLC I/O
  signal list can be summarized to its functional bullets), just with any vendor/brand names in it (IDEC,
  Eaton, etc.) genericized per the rule below. Only fall back to engineering/estimating from scratch when
  no catalog record exists for that item or size.
- **Standard cooler-system ductwork allowance**: price as 100 ft of duct at the size the air system
  calculator recommends, plus a transition from the equipment's exhaust to round duct, fan inlet and
  outlet transitions, and a weatherproof rain hood at the fan discharge — same scope every time. MCE's
  real "Est Ductwork" catalog SKU ($9,995) covers 17" dia/50 ft straight duct + 4 elbows; scale to the
  actual job's diameter and 100 ft length by duct surface area ratio (circumference × length) since no
  catalog SKU exists at every diameter.
- **Never disclose internal pricing methodology or sourcing in a customer-facing document.** Item
  descriptions must read like a normal, confident vendor/catalog spec sheet — a feature and construction
  list — never a note explaining how MCE arrived at the number. Specifically, never write into an item
  description, footnote, or commercial terms section: the word "budgetary" applied to a price, a vendor
  name or "outside vendor quote" used as a cost basis, a formula or scaling method (e.g. "scaled by cloth
  area," "midpoint between two catalog sizes," "divide by 0.7"), or a statement that a size/part "isn't a
  stocked SKU and would need to be engineered/costed from scratch." If a component's price needed real
  engineering work to derive, that's expected and fine — the customer only ever sees the finished number
  and a normal spec description, exactly as if it came straight out of a catalog.
- **Screw conveyor pricing formula**: when a real vendor quote is available for a comparable screw
  conveyor (same or larger diameter, similar or longer length), treat its total price as **cost** and set
  the quoted sell price as `cost / 0.7` (i.e. a 30% margin). Use this same formula every time a screw
  conveyor needs pricing from a comparable quote. Sanity-check the result against any competitor pricing
  on file for the same duty (it should come in under) before using it.
- These rules don't change internal recordkeeping — track the real basis (vendor quotes, formulas,
  non-stock sizes) wherever MCE keeps its own working notes. They only govern what ends up in a document
  the customer will read.
