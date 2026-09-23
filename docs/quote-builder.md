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

The originals are **never edited by this project**. They are the full
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

`test_ports.py` runs each original's **own JavaScript** headless (Node, plus a
small DOM shim in `tests/domshim.js`), feeds both sides several hundred
randomized jobs, and asserts they agree — model selection, every displayed
figure, and every price, down to JavaScript's half-up rounding. It currently
covers 273 cases and must stay at zero mismatches.

If the *math* changed and not just the tables, the extractor won't catch it: the
test will fail, and the matching Python function needs the same change.

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
| Screw conveyor | **not priced** | Sized only — price from the screw catalog |
| Baghouse | **not priced** | Sized only — price from the fabrication estimate |

Unpriced lines land on the quote at $0.00 and are highlighted in the line-item
table, so they can't quietly go out at zero. Fill the price in before sending.

The multipliers and the plenum rate are editable per quote, under **Pricing &
build assumptions**.

## What is saved

One JSON file per quote under `RENDERER_DATA_DIR` (a docker volume in
production), including a `sizing` record of every calculator run that fed the
quote and the exact inputs it ran on. An engineer reviewing a proposal can see
where each number came from without re-deriving it.

The record shape is deliberately tool-agnostic — customer, lines, sizing — so
writing these into Twenty later is a mapping job, not a rewrite.

---

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
