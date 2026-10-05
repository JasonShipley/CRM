---
name: quote-builder
description: Sizes, prices and drafts Midwest Custom Engineering equipment quotes with MCE's own calculators and pricing basis, bundled in this skill and run locally — hammer mills and feeders, hammer patterns, counterflow and rotary coolers, cooler heat balance, baghouses and filter receivers, cyclones, fans, airlocks, ductwork, dilute-phase and live-bottom conveying, and dryers. Saves quotes to quotes.usemce.com when it can reach it. Use whenever someone asks to quote, price, size or spec MCE equipment, wants a hammer pattern, cooler, fan or airlock sized, asks what MCE charges for something, or wants a draft proposal — even if they don't name the quote builder.
---

# MCE quote builder

This skill carries MCE's own calculators and pricing basis. They are the same
code that runs at quotes.usemce.com, copied in at commit `{{COMMIT}}` on
{{BUILT}}. Everything sizes and prices **locally**, in this chat's Python, with
no network or login. The server is needed only to save a quote or to get the
house PDF.

All commands are run from this skill's folder:

```
python scripts/mce.py list                     # the calculators
python scripts/mce.py fields <key>             # a calculator's inputs
python scripts/mce.py calc <key> '<json>'      # size / price one thing
python scripts/mce.py pricing                  # the pricing basis
python scripts/mce.py quote '<job json>' -o quote.json   # a full draft proposal
python scripts/mce.py render quote.json -o proposal.html # the proposal page
python scripts/mce.py save quote.json --token mceq_...   # save on quotes.usemce.com
python scripts/mce.py version
```

A JSON argument can be literal JSON, `@file.json`, or `-` for stdin. Everything
prints JSON. If the shell eats the quotes, write the JSON to a file and use `@file`.

## The rules that do not bend

- **Never invent a number.** Every size and price comes from `mce.py`. If it
  can't size or price something, the line says `needsPrice` or the result says
  why. Report that, and never estimate in its place.
- **Drafts only.** A person reviews and sends. Saved quotes stay `DRAFT`.
- **Provenance stays internal.** Vendor names, vendor quote numbers, cost bases
  and fit findings go in the quote's open items, never in customer-facing text.
  This skill holds MCE's vendor cost basis: never quote a cost or a vendor price
  to a customer, and never paste the pricing basis outside MCE.
- **Don't name MCE's customer to a vendor.**
- Boss Products' published pricing is confidential.

## Sizing one thing

Read `reference/calculators.md` for every calculator's inputs, units and
defaults, then run `calc`. Report the `outputs` (label and value pairs), every
`warnings` line, and any priced `lines`. Examples:

- Hammer pattern, Bliss 4442 at 300 HP on corn, 4-row:
  `calc hammer_pattern '{"motorHp":300,"hpPerHammer":1.5,"rows":"4","pinLength":42}'`
- Rotary cooler, 2 TPH of soy meal from 250 °F:
  `calc rotary_cooler '{"tph":2,"tin":250,"tout":120,"cp":0.45,"rho":38,"mcin":7,"mcout":6,"tmax":100,"humMode":"rh","humVal":40}'`
- Fan, airlock or duct on their own: `calc fan`, `calc airlock`, `calc duct`.
  For a whole air system from one airflow, use `calc airsystem`.

## A full draft proposal

1. Read `reference/job_request.md`. It holds the extraction rules the server
   uses, word for word, and every field a job takes.
2. Turn the request into a job JSON under those rules. **Extraction only:** fill
   what was said, leave the rest out, and put every open question in
   `ambiguities`. `8-4row` is MCE shorthand for an 8-row feeder, not an ambiguity.
3. Run `python scripts/mce.py quote '<job json>' -o quote.json --text "<the request as written>"`.
4. Show the user the lines, the totals and **every open item**. Orange items
   need MCE input before release.
5. On request:
   - `render quote.json -o proposal.html` makes the branded proposal page (needs
     Jinja2). Share it as a file.
   - `save quote.json` puts it on quotes.usemce.com, which returns the edit and
     PDF links.

## Saving to quotes.usemce.com

`save` needs the user's own token: `--token mceq_...` or `MCE_QUOTES_TOKEN`.
If they have none, they can issue one against their @usemce.com email:

1. `POST https://quotes.usemce.com/api/tokens/request` with `{"email": ..., "label": ...}`.
   A code is emailed to them.
2. Read the code with Gmail access if you have it, otherwise ask them for it.
3. `POST https://quotes.usemce.com/api/tokens/confirm` with `{"email": ..., "code": ...}`.
   The reply is `{"token": "mceq_..."}`. It is shown once.

The links that come back are browser pages behind the quote-builder login. Hand
them to the user rather than fetching them. If the server can't be reached, the
chat's network is not allowed to reach quotes.usemce.com. Say so: the quote is
still complete locally, and the domain can be added to the allowed list for code
execution.

## When the bundle may be stale

This copy is from {{BUILT}}. Where the server is reachable and disagrees, the
server wins, and the bundle should be rebuilt (`renderer/skill/build_skill.py`
in the CRM repo) and re-uploaded.

## Things the calculators already know, so don't second-guess them

- Hammer pattern: HP per hammer is on file for **corn only** (1.5, or 1.75 as the
  alternate). For any other material, ask engineering rather than picking a number.
- Rotary coolers are calibrated to a running Insta-Pro 900:
  - a 4 × 8 drum carries 2 TPH of soy meal from 250 °F at about 2,500 ACFM;
  - drums turn at 5 rpm (60 ft/min shell speed) and are loaded no more than 43 lb/h per ft³;
  - drum drives are never under 2 HP;
  - the fan motor is sized on hot running, with a damper-closed or VFD start.
- Drum coolers in the cooler heat balance carry a ×2.9 calibration from the same rating.
- Duct is 14 ga standard and 10 ga for abrasive service (application driven). A
  bird screen and rain hood go at the fan discharge. Sweep elbows only when the
  rep turns them on.
- Airlocks are sized on displacement at the stated pocket fill. A `needsPrice`
  line means the vendor price is pending. Say so and don't fill it.
