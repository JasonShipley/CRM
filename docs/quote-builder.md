# Quote builder — how it works

The quote builder turns a job into a branded Equipment Proposal PDF: the rep
enters the customer, sizes the equipment with MCE's own calculators, and the
sized, priced lines drop straight onto the quote.

It **stands alone**. Quotes are stored by the renderer service itself, not in
Twenty CRM. The CRM tie-in is the next step, not a prerequisite — if Twenty is
down or not configured, the builder, the calculators and the PDF all keep
working.

---

## The two copies of the calculators, and why

| | Where | What it is |
|---|---|---|
| **The originals** | `renderer/tools/*.html` | MCE's calculators, byte for byte. Served at `/tools/<slug>`. The engineering source of truth. |
| **The ports** | `renderer/calculators/*.py` | The same math in Python, so the quote form can size and price server-side. |
| *(hosted, not ported)* | `renderer/tools/rotary-cooler-sizing-calculator.html` | Direct air-swept drum cooler — a different machine from the counterflow cooler, with no quote path yet. Hosted at `/tools/rotary-cooler`; the quote builder cannot size one. |

The originals are **never edited by this project** — with one exception on
record: on 2026-09-23 Jason moved MCE's 44" rotor mills to a 60" screen, and
that is a change to the engineering data itself, not to the port. Editing only
`_data.py` would have left the hosted calculator disagreeing with the quote
builder, which is the exact drift `test_ports.py` exists to catch. So the
calculator's own table was edited, `_data.py` regenerated from it, and the
differential test re-run to prove the two still agree. Any future spec change
follows the same route: change the calculator, regenerate, re-run the test. They are the full
workbenches — index charts, model reference tables, pricing multipliers — and
they are what MCE maintains. Hosting them here just means the team reaches them
behind the login instead of passing files between desktops.

The ports exist because the quote form needs the numbers as data, not as a page
someone reads off. They are kept honest by a differential test, below.

### Keeping them in step

`renderer/calculators/_data.py` is **generated**, not hand-written. It holds every
table the originals use — 32 XM mill models, the Bliss price basis and plenum
weights, feeder and screw-conveyor tables, 51 cooler models with their option
sheets, the baghouse geometry and the Kice comparison table. Hand-copying that
would rot; the extractor reads it out of the HTML.

When MCE changes a calculator:

```bash
cd renderer
python3 tests/extract_data.py     # re-read the tables out of tools/*.html
python3 tests/test_ports.py       # prove the ports still match the originals
```

`tests/test_bliss_areas.py` is a second, separate check: MCE's XM line is built
on the Bliss design and each XM model is priced at its Bliss counterpart's base
price, so their screen areas must agree. The base price is the link, and it is
already in the calculator, so the test needs no judgement — it matches every mill
by price and compares the areas. All 32 agree.

`test_ports.py` runs each original's **own JavaScript** headless (Node, plus a
small DOM shim in `tests/domshim.js`), feeds both sides several hundred
randomized jobs, and asserts they agree — model selection, every displayed
figure, and every price, down to JavaScript's half-up rounding. The cyclone and
hammer-pattern cases go further still: they drive the original's own `compute()`
and read the rendered values back out of the shim, so the wording is diffed too.
It currently covers 527 cases and must stay at zero mismatches.

If the *math* changed and not just the tables, the extractor won't catch it: the
test will fail, and the matching Python function needs the same change.

---

## The free-text intake

A rep types the job as a sentence; a complete draft proposal comes out. Two
stages, deliberately separated:

**1. Extraction (`interpret.py`).** One Claude call reads the sentence and fills
a Pydantic schema — customer, mill model, capacity, screen, feeder, what's
included. It is told, and schema-constrained, to do **extraction only**: never
invent a value, never resolve an ambiguity by picking the likelier option, and
push anything unclear into `ambiguities`. `"8-4row"` comes back as `rows: null`
plus a question, not as an `8`.

**2. Engineering (`quote_from_job.py`).** No model involved. It takes those
fields, runs MCE's calculators, and assembles the proposal. Every number that
reaches the page comes from `calculators/`.

That split is the point. The model is a parser for the rep's shorthand; it is
never the source of a quoted figure. The rule the quote-builder skill states —
prices from MCE's basis, sizes from MCE's calculators — holds even though the
input is free text.

### What it flags rather than guesses

| Situation | What the proposal does |
|---|---|
| Ambiguous wording (`"8-4row"`) | Sizes the feeder from the mill screen width, asks for the row count |
| Product could match two index rows | Uses the closer one, flags it — the pet food entries grind very differently |
| Stated HP disagrees with the calculation | Quotes the calculated figure; the conflict goes to MCE internally |
| Named mill too small for the motor | Quotes the mill asked for; the shortfall goes to MCE internally, **not** onto the proposal |
| Rep names a cyclone instead of a filter | Sizes the cyclone from the mill's own plenum airflow, quotes no baghouse |
| Rep names a filter receiver | Same cloth, same fan, same price — the line says hopper-bottom and the budget basis becomes like-for-like |
| Rep says indoors | The explosion vent becomes flameless, which MCE has never bought — the option states the requirement instead of carrying the domed price |
| Rep asks for air-swept | The filter becomes a **receiver**, because the product is carried over with the air and has to drop out of it — a bin vent cannot do that |
| Air system, but not air-swept | Offers the air-swept conversion as one option with a real net adder: the pan, plus every step-up the extra airflow forces |
| Rep says the dust is combustible | Adds NFPA isolation, an explosion vent and its burst switch as **options**, sizes none of them, and asks for the dust hazard analysis |
| No calculator exists (fan, duct, airlock) | Lists the item unpriced rather than omitting or guessing it |
| A price is a budget or a model, not a quote | Prices it anyway, marks it budget, and names the source document internally |
| Governing spec missing entirely | Quotes nothing, says what it needs |

Unresolved values print **orange**, matching the convention on MCE's own draft
proposals ("orange items require MCE input before release").

**Pricing provenance never reaches the customer.** A line says what is being
supplied; which vendor quote it was budgeted from, which substitution was made,
and how a basis differs from the job all go to the internal open items — as do
fit findings like an undersized mill or a horsepower conflict. While a quote is
Draft the proposal also carries an internal open-items block listing all of them,
with the original sentence it was built from; that block disappears when the
quote leaves Draft.

**Why this asks for JSON rather than using structured outputs.** The obvious tool
is `messages.parse(output_format=JobRequest)` — the API constrains the model to
the schema so the reply cannot be malformed. It is not usable for this schema:
the API answers *"Schema is too complex"* to `JobRequest`, sometimes rejecting in
under a second and sometimes hanging past a 180s timeout, while plain calls
generating the same tokens return in about fifteen. Flattening the schema did not
clear it. So the contract goes in the prompt instead — `JSON_INSTRUCTION`, which
is **generated from `JobRequest`** so it cannot drift from what will actually
validate — and the reply is validated here against the same model. That trades an
API-side guarantee for a client-side one, which is why `_parse_json_reply`
refuses anything it is unsure of rather than half-reading it, and why
`tests/test_json_fallback.py` covers that parser without needing a key.

`ANTHROPIC_API_KEY` powers this one box. Without it the box says so and the rest
of the builder is unaffected.

`tests/test_intake.py` covers the whole downstream half against the JobRequest
shapes Claude is instructed to produce — including the cases above, which are
the ones that matter.

---

## Sizing chains

The calculators feed each other, which is why they live on one page:

```
Hammermill:  PPH / index / screen-64ths  ->  next standard motor HP
             motor HP x in²/HP           ->  required screen area
             smallest XM mill in family that carries that area
             mill screen area x 1.3      ->  plenum CFM
             plenum CFM / design velocity->  flange area
             PPH / bulk density          ->  screw conveyor size and length

Baghouse:    the same "screen area x 1.3" gives system CFM
             CFM / air-to-cloth ratio    ->  required cloth area -> MCE model
             the matched AirPro fan comes with the model (_vendor.py)

Duct:        CFM / velocity -> ft2 x 144 -> D = 2 x sqrt(area/pi)
             rounded UP to the next even inch, which is how duct is bought

Air system:  ONE airflow drives the rest. It comes from whichever basis is to
             hand - a CFM figure, a mill screen area, an XM model, or a cooler's
             own requirement - and then the air cleaner, its matched fan, the
             airlock and the duct all follow. calculators/airsystem.py owns that
             chain and calls the same ports the standalone calculators use, so a
             filter sized there and one sized on /tools/baghouse are the same
             filter. tests/test_airsystem.py holds the two to each other.
             Three air cleaners, one sizing: the BIN VENT (MCE's baghouse with no
             hopper, which bolts straight onto the plenum chamber), the FILTER
             RECEIVER (the same filter with a hopper under it, so it collects and
             discharges on its own) and the CYCLONE.

Cyclone:     rated CFM, or inlet ID area / 144 x inlet FPM
             <= 12,600 CFM -> HE series on its rated min/opt/max
             >  12,600 CFM -> H series on its rating at 2" / 3" / 4" WG
             quoted only when there is no baghouse: with a filter the fan
             discharges to atmosphere after it and no cyclone is needed

Hammer
pattern:     motor HP / HP-per-hammer, rounded DOWN to even -> hammer count
             count split over 4 or 8 rows, opposite rows equal (17/16/17/16)
             max per row x thickness + collar <= pin length - end allowance
             HP per hammer is on record for corn only (1.5, 1.75) — the
             calculator takes any number but supplies none, and the quote
             builder does not use it, so no pattern is ever guessed

Cooler:      pellets — volume first:  (TPH x 2000/60) x retention / density
             meal    — airflow first: (TPH x CFM/ton) / face-velocity cap
```

Pick **From mill screen area** on the baghouse tab and give it the screen area
the hammermill just reported, and the two agree by construction.

## What gets priced, and what doesn't

| Line | Priced by | Notes |
|---|---|---|
| Hammermill | Bliss basis x mill multiplier | Warns when CRM list has fallen behind the basis |
| Rotary feeder | Feeder sheet + magnet/cleanout, x multiplier | |
| Plenum | Plenum weight x duty factor x $/lb | Weight varies with design velocity |
| Cooler | MCE list (2016/17 basis escalated), plus options | Price rev shown on the result |
| Screw conveyor | SCC vendor quote x MCE markup | Budget figure; flags when the run length differs from the vendor basis |
| Fan | AirPro OEM lineup cost x 2 | Selected against the baghouse model, not sized separately |
| Bin vent / filter receiver | $40.20/ft² of cloth ÷ 0.70 | Budget figure; the basis says whether it is an upper bound (bin vent) or like-for-like (hopper-bottom receiver) |
| Drop-down air pan with pickup fitting | **$9,204** | A price MCE has sold, not a shop estimate — NEMO Feed proposal 20260428 |
| Certified rotary valve | $6,053 cost ÷ 0.70 = **$8,647** | Est 7659; a 10" valve, so NOT a size-for-size swap for the standard airlock |
| Explosion vent panel | **$1,960** (23"×36") or **$3,964** (36"×44") | Priced per panel from its own quote — price does not scale with area |
| Burst indicator sensor | $378 cost ÷ 0.70 = **$540 per panel** | Optioned out, because it belongs to the plant's controls scope |
| Duct isolation package | $10,993 cost ÷ 0.70 = **$15,704** | 2 flap valves + UL control panel + 2 level sensors; they only work together |
| Flameless vent | **not priced** | Indoors only; ~$46.6k per assembly at the distributor's own cost, and MCE has never bought one |
| Vent adaptor section | **not priced** | MCE's own fabrication — price from the shop estimate |

Unpriced lines land on the quote at $0.00 and are highlighted in the line-item
table, so they can't quietly go out at zero. Fill the price in before sending.

The multipliers and the plenum rate are editable per quote, under **Pricing &
build assumptions**.

## What is saved

One JSON file per quote under `RENDERER_DATA_DIR` (a docker volume in
production): the customer and line items, the proposal sections (design basis,
furnished by others, schedule, options, net-priced items, open items), the
original sentence it was built from, and a `sizing` record of every calculator
run that fed the quote with the exact inputs it ran on. An engineer reviewing a proposal can see
where each number came from without re-deriving it.

The record shape is deliberately tool-agnostic — customer, lines, sizing — so
writing these into Twenty later is a mapping job, not a rewrite.

---

## Vendor cost bases

### Where each price comes from

| Item | Basis | Source |
|---|---|---|
| Mill, feeder, plenum | MCE's own calculator multipliers | `hammermill-sizing-calculator.html` |
| Screw conveyor | least-squares fit over 9 SCC quotations | `SCREW_QUOTES` |
| Fan (with a baghouse) | AirPro OEM lineup cost × 2.0 | AirPro Q117935R1 |
| Cyclone | sold price where MCE has sold that model, else $/lb of shipping weight | NEMO Feed 20260428, LETEK MCE-Q-2609-LETEK-R2 |
| Airlock | FT-12 vendor cost ÷ 0.70 | Airlanco quote 024350 |
| Main drive motor | vendor cost ÷ 0.70, by horsepower | `MOTOR_QUOTES` |
| Baghouse | $40.20/ft² of cloth ÷ 0.70 — **budget only, upper bound** | Airlanco quote 024350 vs NEMO Feed sell |
| Filter receiver | the same $40.20/ft² ÷ 0.70 — **budget, like-for-like** | as above; the reference unit *is* a hopper-bottom receiver |
| NFPA 69 isolation valve | sell prices on file for two certified valves, quoted as a range | NEMO Feed 20260428 |
| Explosion vent panel | each size from its own quote ÷ 0.70 | High Tech Duct Werks estimate 7659, EV calc ref 0609-RCRI |
| Certified rotary valve, flap valves, control panel, level sensors | rate less the 15% OEM discount ÷ 0.70 | High Tech Duct Werks estimate 7659 |
| Flameless vent, vent adaptor | **no price on file** | flameless never bought at MCE level; the adaptor is MCE's own fabrication |
| Ductwork | sized from the system CFM; **priced on request** — run, fittings and whether it vents to atmosphere come from the layout | duct calculator |

Buy-out lines print the **model number and the specification** — airflow, static,
RPM, HP, frame. The vendor's name never reaches a customer line; it lives in the
internal open items with the quote that set the price.

MCE's own markup rules, transcribed rather than inferred, are in `_vendor.py`:
buy-out `cost / 0.70`, fabrication `cost × 1.10 / 0.75`, parts `cost / 0.77`. The
fabrication rule reproduces the "1D3D-60 CYCLONE — BUDGET PRICE MODEL" sheet's
sell price to the cent, and the buy-out rule reproduces the NEMO Feed baghouse
sell price from the Airlanco cost exactly — both are checked in code.

`renderer/calculators/_vendor.py` holds the figures MCE buys at, each with its
source quote and expiry:

- **AirPro fans** — MCE's OEM lineup pairs one fan with each baghouse model
  (arrangement 4V, direct-mounted, CS outlet damper, 12 in.wg). The fan is
  therefore *selected against the filter*, never sized independently. Sell price
  is cost x 2. When a baghouse is in the scope the air is cleaned by the filter
  and the fan discharges to atmosphere after it, so **no cyclone is quoted**.
- **SCC screw conveyors** — MCE never buys the same screw twice, so there is no
  list to look up. `SCREW_QUOTES` holds every SCC quotation on file (diameter,
  length, material, date, cost) and `SCREW_MODEL` is a least-squares fit over the
  carbon-steel ones:

  ```
  cost = BASE + PER_IN x diameter + PER_IN_FT x diameter x length
  ```

  Each quote is escalated to a common date first, at a rate derived from the one
  like-for-like pair across time (11.5%/yr). Mean absolute error 6.6%, worst 16%
  across nine quotes spanning 6" to 18" and 8 to 25 ft. Outside that envelope the
  model extrapolates and says so on the open items.

  Because it is a model rather than a quote, the screw markup carries extra
  cover: MCE's usual "divide by 0.8" plus 10%, i.e. 1.375. Every screw line
  raises an open item saying it is modelled and that SCC should price the real
  configuration.

  `tests/fit_screw_model.py` re-fits from the quote list and tells you if
  `_vendor.py` has drifted. Add a new quote to `SCREW_QUOTES`, re-run it, paste
  the coefficients back.

  One open question it surfaced: the single T304 stainless quote lands within 1%
  of what the model predicts for carbon at that size, so no material premium is
  applied. That is one data point against a model that may simply over-predict at
  12" — worth confirming with SCC before leaning on it for a sanitary job.

### Bin vent, filter receiver, cyclone

Three ways to clean the air, one sizing. The cloth area, the grid, the bags and the
matched fan are identical; what differs is how the unit is built and what the line
says:

- **Bin vent** — MCE's baghouse with **no hopper**, bolted straight onto the plenum
  chamber. This is the standard mill arrangement, and the vent vendor's own term for
  it ("which object is the bin vent?").
- **Filter receiver** — the same filter with a **hopper** under it, free-standing on
  legs, so it collects and discharges on its own rather than sitting on a plenum
  that already has a discharge.
- **Cyclone** — no filter, so the fan ducts to atmosphere.

The budget rate is the same $40.20/ft² either way, because one data point supports
one rate. What changes is the honesty of the comparison: the Airlanco reference unit
*is* a hopper-bottom receiver, so for a receiver the scale is like-for-like, and for
a bin vent it is an upper bound. `baghouse_budget(hopper=...)` says which.

### Air-swept, and why it changes the filter

A plain-plenum mill relieves air through the plenum and discharges its product down a
screw. An **air-swept** mill takes the product out through the air instead, on a
drop-down pan with an air pickup fitting. Three things follow, and the builder does
all three rather than just raising the CFM:

1. **Airflow** rises by the pan factor — screen area × 1.25 × 1.3 CFM/in².
2. **The filter gains a hopper.** The ground product is carried over with the air and
   has to drop out of the filter, which a plenum-mount bin vent cannot do. So
   air-swept quotes a **filter receiver**, whatever the rep named, and says so on the
   open items.
3. **The pan is a line**, priced at $9,204 from the one MCE has sold.

On a quote that is *not* air-swept, the same arithmetic runs in reverse as an option:
"Air-swept conversion — air pickup fitting and filter receiver" carries a real net
adder of the pan plus every step-up the higher airflow forces (a bigger filter, and
the fan too if the selection changes). For Fairview Mills that is $9,204 + $10,464 =
**$19,668**, with the fan unchanged.

### Combustible dust

Set by the rep, never inferred from the material: plenty of combustible products
get ground without anyone asking for protection, and the flag puts five options in
front of a customer. `calculators/nfpa.py` owns what happens when it is set, and it
prices exactly what MCE has in writing — nothing more.

MCE buys its protection through High Tech Duct Werks (Darryl Lind), the Florida rep
for Boss Products. Four documents are on record, and `estimate 7659` (2026-08-28) is
the complete NFPA 660 package for a lumber cyclone — vent panel, burst sensor,
certified rotary valve, two flap isolation valves, the UL control panel and the dust
level sensors, less a 15% OEM discount, $18,796.05. Every option below is built from
its line items, and `tests/test_airsystem.py` adds the parts back up and checks they
come to that total to the cent.

| Option | Priced from | MCE cost | Sell |
|---|---|---|---|
| Certified rotary valve (10" VDL HT250) | Est 7659 | $6,052.85 | **$8,646.93** |
| Explosion vent panel, 23" × 36" | Est 7659 | $1,371.90 | **$1,959.86** |
| Explosion vent panel, 36" × 44" | ref 0609-RCRI | $2,775.00 | **$3,964.29** |
| Burst indicator sensor, per panel | Est 7659 | $378.25 | **$540.36** |
| Duct isolation: 2 flap valves + UL panel + 2 level sensors | Est 7659 | $10,993.05 | **$15,704.36** |
| Vent adaptor section | — | — | MCE fabrication, unpriced |
| Flameless vent | — | — | never bought, on request |

Things that matter and are easy to get wrong:

- **Panel price does not scale with area.** The 23" × 36" is $1,614 and the 36" × 44"
  is $2,775 — not the 1.9× their areas would imply. So a panel is priced from its own
  quote and never interpolated from another size. A size MCE has no quote for is
  quoted on request.
- **The panel COUNT is not sized here.** It is the vent manufacturer's calculation
  against the DHA. Panels are quoted per panel, with the counts comparable MCE
  vessels actually took.
- **Two different isolation devices, and the lumber job bought both.** A certified
  rotary valve isolates the material discharge; **flap valves** isolate the duct, one
  on the inlet and one on the outlet, held open by flow and slammed shut by the
  pressure front. The flap valves, the UL control panel and the level sensors are one
  option because they only work together.
- **The certified valve prices BELOW the standard airlock**, because the quoted valve
  is a 10" and the FT-12 in MCE's scope is larger. That is a size mismatch, not a
  credit: the option says so on its face ("NOT a size-for-size swap"), carries the
  $10,273–$22,998 range for the larger certified valves on file, and the internal
  notes say it outright.
- **Flameless is a different conversation, not a line swap.** On Q-25602 Boss quoted
  its own distributor three flameless assemblies at $46,623 each — $139,869 — against
  two domed panels at $5,516 for the same vessel. That is *distributor* pricing, so it
  never reaches a proposal; `indoors` true produces the requirement and no number.
- **Whose discount is whose.** Boss quotes its distributors at list less 25%; Darryl's
  estimate to MCE carried a 15% OEM discount. A Boss-to-Ductwerks figure is not a cost
  MCE can buy at, and `BOSS_LIST_PRICES` is kept separate from `ISOLATION_ITEMS` so the
  two never get mixed.
- **The adaptor section** is why a vent is not just a purchase. A panel needs flat,
  unobstructed housing wall — "areas near structural supports, motors, ducts,
  platforms, corners or hopper sections have to be avoided" — and a bin vent bolted
  onto a plenum chamber does not offer one. MCE fabricates a spool below the bin vent,
  drilled and flanged for the panel, panel sideways, rain hood outside (Nix took
  roughly a 40" × 28" duct about 5 ft through the wall). MCE's own steel, no cost
  basis yet, so it goes out unpriced.
- **Dust figures** are only ever quoted as a reference from a job MCE actually ran
  (`DUST_ON_RECORD`: wood Kst 150 / Pmax 8, corn Kst 130–150 / Pmax 8–9), with the
  range intact where the vendor was given a range. For anything else the open items
  say the vent supplier needs a Kst and Pmax from the customer's DHA. A guessed Kst is
  a guessed vent area.

The four selections on record are in `VENT_SELECTIONS` and reach every
combustible-dust quote's internal notes:

| Job | Dust | Vessel | Selection |
|---|---|---|---|
| Nix Forest Industries (Q-26693) | wood, 1/4" screen, Kst 150 | 25AST-8, below the hopper | 1 × EV-VD 23" × 36" |
| lumber cyclone (Est 7659) | wood / lumber, Kst 150 | cyclone with 10" valves, NFPA 660 | 1 × 23" × 36", + rotary valve + 2 flap valves |
| corn mill air system (ref 0609-RCRI) | ground corn, Kst 130–150 | below the baghouse extension | 2 × EV-VD 36" × 44" |
| XM-4460 plenum bin vent (Q-25602) | corn to 500 micron, Kst 150 | bin vent on the plenum, indoors | 2 × domed 44" × 44", or 3 × flameless |

A quote past its expiry still prices, but says so on the line and raises an open
item — a stale basis is visible rather than silent. Update the numbers here when
a new vendor quote lands.

## Adding a calculator

1. Put MCE's HTML in `renderer/tools/`, and register it in `TOOLS` in `app.py`.
2. Add its tables to the extractor's list in `tests/extract_data.py`, re-run it.
3. Write `renderer/calculators/<name>.py` with a `size(form)` that returns
   `{outputs, warnings, lines, total, formula}`. Displayed numbers go through
   `_fmt.num()` so they round the way the original does.
4. Register it in `calculators/__init__.py` with its input fields — the form UI
   and the JSON API are both generated from that declaration.
5. Add a reference script under `tests/` and a case block in `test_ports.py`.

Nothing in the form template needs touching: the tab, the inputs and the results
panel all come from the registry.
