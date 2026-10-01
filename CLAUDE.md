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

- **10"/14" dia rotary feeder + magnetic adapter combo pricing** (a 2017 rotary-feeder-and-magnet OEM price
  book, the same one MCE's own "manual clean/manual self-clean/auto self-clean" magnet-adapter option
  structure was modeled from — original file kept locally, not Drive, per Jason): each diameter's page
  gives a base nylon-cup (or stainless-cup) feeder price by row count, plus three magnetic-adapter add-on
  tiers: **manual clean** (least cost, hinged clamps), **manual self-clean** (mid), **automatic self-clean**
  (highest, air-cylinder/solenoid actuated). MCE's sell price for a given row size/tier = (base feeder price
  + adapter tier add-on) &times; 2 — confirmed against real current MCE sell figures for the 10" 3-row combo
  (manual clean $8,816; manual self-clean $11,990; auto self-clean $13,658), which match this formula
  exactly off the source book's 10" DIA page. **Standing practice: only ever offer the manual-clean tier
  (base-quoted) or the automatic self-clean tier (offered as an upgrade option) — skip the manual
  self-clean middle tier entirely** unless a customer specifically asks for it. Never disclose the source
  book, the tier model codes, or the &times;2 formula in a customer-facing document — write the combo as a
  plain "nylon cup feeder with built-in [manual-clean / auto self-clean] magnetic separator" spec, per the
  no-disclosure rule below.

- **10" rotary airlock pricing** (real current vendor quote via email, Prairie States Industrial Supply /
  Prater Industries, rep Jeff Mahurin, Aug 2026 — "10\" PAV Series" airlock, revised quote total $6,810.91
  for the bare 10" airlock, confirmed current): applies to **every** rotary airlock on a job, not just one —
  on the Ballard job this meant upsizing the pre-crack discharge airlock from 8" to 10" to match the
  final-grind and cooler-cyclone airlocks, so all three price and spec identically. Use this real vendor
  cost, not the stale Zoho catalog
  Unit_Price, whenever quoting a 10" airlock — Zoho's $6,496 listed price is now **below** this real current
  vendor cost and would sell at a loss. Apply the same `cost / 0.7` margin rule used for screw
  conveyors/ductwork: $6,810.91 / 0.7 = **$9,729.87** sell price per 10" airlock. Check Jason's email for
  the latest Jeff Mahurin quote before relying on Zoho's airlock catalog price in any future quote — Zoho
  has not kept pace with this vendor's current pricing. Never name the vendor, rep, or model line in a
  customer-facing document — write it as a generic "cast-iron rotary airlock" spec per the no-disclosure
  rule below.

- **575V vs 230/460V mill drive motor pricing (Teco/TWMC MAX-E1 EP-series)**: verified against real Teco
  portal catalog pages for EP0202 (20 HP, 3600 RPM, 254/256T) — the 230/460V version and the 575V version
  (catalog #EP02025) carry the *identical* List Price ($3,106.00) and Net/Your Price ($1,009.45); Teco does
  not charge more for this line at 575V. Standing practice: **still charge the customer 1% more for a
  575V-specced mill drive motor** than the 230/460V sell price (net cost &times; 1.30 + $500 flat freight,
  per standing MCE pricing policy) — a margin cushion, not a real vendor cost difference. Apply this same
  1% adder to every EP-series mill drive motor frame in a job (20 HP and up), not just the verified 20 HP
  point, since Teco's flat 32.5%-of-list net pricing and blanket percentage escalation apply uniformly
  across the whole catalog. Never disclose in a customer-facing document that this is a margin adder rather
  than a real vendor cost — write the motor line as a normal 575V spec at the marked-up price, per the
  no-disclosure rule below.
  - **Control panels (e.g. cooler control system) specced at 575V use a lighter 0.75% adder** instead of the
    1% mill-drive-motor adder — same margin-cushion logic, just a smaller cushion for a panel vs. a bare
    motor. Apply to the panel's full sell price, same no-disclosure treatment.

## Customer-Facing Quote/Proposal Rules (apply to every quote, every item)

- **MANDATORY final check, every time any customer-facing document (proposal, quote PDF) is edited, not
  just when an item you touched might be affected:** before treating the edit as done or sending the file,
  run a literal search of the *entire* document for this exact term list and confirm zero hits. Do not
  rely on memory of what you meant to remove — grep the whole file:
  `MAC|Nolin|Airlanco|AirPro|Kice|AVS|TECO|IDEC|Nix Forest|Zoho|Eaton|Baldor|Dodge|Coperion|Cincinnati Fan|
  Bliss|Carlane|Ponca City|SMA|SCMA-M|SCMA-A|Prairie States|Mahurin|PAV Series|Prater|
  modeled from|data sheet|catalog sheet|source catalog|sourced from|per MCE's own|vendor quote|outside
  vendor|comparable quote|budgetary|scaled by|midpoint|divide by|cost/0\.7|non-stock|isn't a stocked|needs?
  to be engineered|confirm .* once|pending (fabrication|final)|the next smaller|the next size`.
  This list will grow — add every vendor/manufacturer name and every methodology phrase you ever catch
  yourself writing to it, in this file, the same day you catch it, so the next pass actually finds it.
  A partial fix (removing one flagged sentence from an item but leaving a second one in the same bullet
  list, or fixing one item but not sweeping the rest of the document) is the same failure as no fix. Read
  and re-verify the *entire* item block you touched, not just the sentence you were told about.
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
  outlet transitions, and a weatherproof rain hood at the fan discharge — same scope every time.
  Price it from the real **Nolin Milling 2026 catalog** (MCE's preferred ductwork/transitions/elbows
  vendor), not by estimating: two reference transcriptions live in the same Drive folder as the MAC
  cyclone catalog — "Nolin Milling 2026 Price List — Ductwork, Elbows, Transitions (reference)" and
  "Nolin Milling 2026 Ductwork & Elbow Price List (reference)" — plus the full "Nolin Milling 2026 Online
  Catalog.pdf". These give real $/10-ft-length duct pricing by diameter and gauge, elbow pricing by
  diameter/gore/gauge, square-to-round and round-to-round transition pricing, and 150# flange adapter
  plates (use these for fan inlet/outlet connections — the catalog says they're made for exactly that).
  Build cost from these real prices (100 ft = ten 10-ft lengths at the job's diameter/14ga; transitions
  and flange adapters at the nearest listed size when the exact custom size isn't tabulated, same as
  Nolin's own worked examples do), then apply `cost / 0.7` per the screw-conveyor-style margin rule below.
  The catalog has no rain hood/weather cap listing (it says that comes with the fan or is MCE-fabricated)
  — use **$350 cost** as the baseline for this small fan (XF-29, 25 HP class); it scales up with fan size,
  so bump it for a larger exhaust fan on a bigger job. Fold it into the same cost basis before dividing
  by 0.7. Add roughly $1,500–$2,000 for freight on top of the whole ductwork line's sell price (baked into
  the total, never called out as freight on the customer document, consistent with never stating an item
  includes freight).
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
