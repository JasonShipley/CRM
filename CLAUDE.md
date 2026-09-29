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
