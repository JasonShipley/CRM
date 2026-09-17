# MCE branded proposals

Customer-facing quotes/proposals in MCE brand furniture (black header band with logo, orange
rule, steel section bars, Oswald headings, Inter body), matching the LETEK DCG XD-96 proposal
of September 2026.

```
python3 proposals/build_proposal.py proposals/<job>/proposal.json        # writes the PDF next to the JSON
python3 proposals/build_proposal.py proposals/<job>/proposal.json --html # also keeps the HTML
```

Requirements: `pip install jinja2 playwright` and a Chromium under `/opt/pw-browsers`
(or `CHROMIUM_PATH=...`). Fonts (Oswald, Inter — OFL) and the logo live in `assets/`.

Each job folder holds `proposal.json` (the content — edit this, not the PDF) and the rendered
PDF. While `"draft": true`, text wrapped in `[[...]]` prints orange and the header carries the
"DRAFT — INTERNAL REVIEW" banner; set `"draft": false` for the customer copy (the text stays,
the orange goes). `**bold**` and `• ` bullets work in every text field. Pricing sections compute
extended prices, subtotal, discount and total from `qty` × `unit_price`.

`internal_notes` in the JSON is never printed — use it for pricing basis, commissions and
competitive context.

| Job | Customer | Status |
|---|---|---|
| `2026-09-mid-states-xm4460` | Mid-States Companies — 8 × XM-4460 corn ethanol mills | Draft R1 |
