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
             Three air cleaners, one sizing: baghouse, filter receiver (the same
             filter with a hopper under it, so it collects and discharges instead
             of sitting on the mill plenum) and cyclone.

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
| Baghouse / filter receiver | $40.20/ft² of cloth ÷ 0.70 | Budget figure; the basis says whether it is an upper bound (plenum-mount) or like-for-like (hopper-bottom) |
| NFPA isolation valve | **not priced** | Offered as an option with the real $10,273–$22,998 range — the size has to be picked against the duty |
| Explosion vent, burst switch | **not priced** | Options; the vent manufacturer sizes and quotes them off the dust hazard analysis |

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
| Explosion vent | **no price on file** — engineering basis only | High Tech Duct Werks Q-26693 (Nix Forest Industries) |
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

### Combustible dust

Set by the rep, never inferred from the material: plenty of combustible products
get ground without anyone asking for protection, and the flag puts three options
in front of a customer. `calculators/nfpa.py` owns what happens when it is set.

- **Isolation** (NFPA 69) is a certified rotary valve — flex-tip rotor, certified
  to NFPA 69 12.2.4.3.6. MCE has sell prices for two of them, but they are
  different **sizes** and nothing here sizes a valve, so the option carries the
  range ($10,273–$22,998) and says the selection has to be made. The smaller one
  prices *below* the standard FT-12, which is exactly why it is never offered as
  a drop-in swap.
- **Deflagration venting** (NFPA 68) is unpriced, on purpose. Vent area comes
  from Kst, Pmax, the vessel volume and the design reduced pressure — a dust
  hazard analysis, not a calculator. MCE buys these sized and quoted by **High
  Tech Duct Werks** (Darryl Lind). The precedent on file is the Nix Forest
  Industries job: wood through a 1/4" screen, Kst 150 bar·m/s, Pmax 8.0 bar,
  design Pred 0.2 bar(g), one EV-VD domed vent with a 23" × 36" panel below the
  hopper of a 25AST-8, vented outdoors through ~40" × 28" duct with a rain hood.
  Quote Q-26693 — **its dollar figure is in an attachment this project has not
  read, and is deliberately not in `_vendor.py`.** A protection package is not a
  number to interpolate.
- **Burst indicator switches** are their own option, off the vent, which is how
  Nix bought it — the plant's controls scope usually specifies them.
- **Kst** is only ever quoted as a reference from a job MCE actually ran
  (`KST_ON_RECORD`, wood 150). For anything else the open items say the vent
  supplier needs a Kst and Pmax from the customer's DHA. A guessed Kst is a
  guessed vent area.

Indoors matters: a standard panel has to discharge outdoors, and an indoor vessel
needs a flameless vent, which prices differently. Unsaid, the option states both
rather than picking one.

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
