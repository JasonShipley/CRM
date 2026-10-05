---
name: quote-builder
description: Builds and sizes Midwest Custom Engineering equipment quotes through MCE's own quote builder at quotes.usemce.com — hammer mills, feeders, coolers, baghouses and filter receivers, cyclones, fans, airlocks, ductwork, dryers and conveying. Use whenever someone asks to quote, price, size or spec MCE equipment, wants a hammer pattern, cooler, fan or airlock sized, asks what MCE charges for something, or wants a draft proposal PDF — even if they don't name the quote builder.
---

# MCE quote builder

MCE's quoting runs on one service: **https://quotes.usemce.com**. It holds the
ports of MCE's own calculators and MCE's single pricing basis. Every chat,
Cowork session and agent quotes through it, so two quotes for the same job
agree.

## The rules that do not bend

- **Never invent a number.** Sizes come from `/api/calc` or `/api/interpret`,
  prices from the same responses or `/api/pricing`. If the service cannot size or
  price something, say so and leave it unpriced — never estimate it yourself.
- **Drafts only.** Anything you save stays `DRAFT`. A person reviews and sends.
- **Provenance stays internal.** Vendor names, vendor quote numbers, which basis a
  price came from and fit findings belong in the quote's open items, never in
  customer-facing text.
- **Don't name MCE's customer to a vendor.**
- Boss Products' published pricing is confidential.

## Access

All calls go to `https://quotes.usemce.com/api/...` with
`Authorization: Bearer mceq_...`. Each person has their own token.

- If the user has given you their token, use it.
- If not, issue one against their **@usemce.com** work email:
  1. `POST /api/tokens/request` with `{"email": "<their email>", "label": "<which assistant>"}`.
     A six-digit code is emailed to them. It is good for 15 minutes and five tries.
  2. Read the code from their inbox if you have Gmail access. Otherwise ask them for it.
  3. `POST /api/tokens/confirm` with `{"email": ..., "code": "123456"}`.
     The reply is `{"token": "mceq_..."}`. It is shown **once**, so tell them to keep it.
- `GET /api/tokens` lists their tokens. `POST /api/tokens/<id>/revoke` revokes one.

If the request cannot reach `quotes.usemce.com` at all, the problem is this
environment's network allowlist, not the service. Tell the user that the domain
needs adding to the allowed domains for code execution.

## What to call

| Need | Call |
|---|---|
| The pricing basis (factors, rules, mill and feeder prices, what is unpriced) | `GET /api/pricing` |
| Size one piece of equipment | `POST /api/calc/<key>` with a JSON object of its inputs |
| A whole draft proposal from a sentence | `POST /api/interpret` with `{"text": "..."}` |
| Save that draft as a quote | `POST /api/quotes` with the `quote` object from interpret |
| Change a saved quote | `POST /api/quotes/<id>` with the full quote |

Calculator keys: `hammermill`, `hammer_pattern`, `cooler` (counterflow),
`cooler_heat` (heat balance check), `rotary_cooler`, `baghouse`, `cyclone`,
`airsystem` (filter, fan, airlock and duct from one airflow), `fan`, `xf_fan`,
`airlock`, `duct`, `dilute_phase`, `live_bottom`, `dryer`.

Omit any input you don't have; the calculator uses MCE's default and reports the
basis. Every result has `outputs` (label/value pairs), `warnings`, and usually
`lines` with prices, or `needsPrice` where no price is on file.

### The usual flow

1. Take the job as the rep or customer described it. Keep their wording.
2. `POST /api/interpret` with that text. You get back `quote`, `openItems` and
   `job` (what was extracted). **Nothing is saved yet.**
3. Show the user the lines, the total and every open item. Open items in orange
   need MCE input before release.
4. Once they're happy, `POST /api/quotes` with the `quote` object. The reply
   gives `url`, `pdfUrl` and `editUrl`. These are browser pages behind the
   quote-builder login, so hand the links to the user rather than fetching them.

For a single sizing question, such as "hammer pattern for a Bliss 4442 at 300 HP"
or "what cooler for 2 TPH of soy meal", call the calculator directly and report
the outputs. Don't build a quote unless asked.

## Things the service already knows, so don't second-guess them

- Hammer pattern: HP per hammer is on file for **corn only** (1.5, 1.75 alternate).
  For anything else, ask engineering rather than picking a number.
- Rotary coolers are calibrated to a running Insta-Pro 900: 4 × 8 drum, 2 TPH of
  soy meal from 250 °F, about 2,500 ACFM, 5 rpm. The drum drive is never under
  2 HP, and the fan motor is sized on hot running with a damper-closed or VFD start.
- Duct is 14 ga standard, 10 ga for abrasive service (application driven), with a
  bird screen and rain hood at the fan discharge. Sweep elbows only when the rep
  turns them on.
- Airlocks are sized on displacement at the stated pocket fill. If a line comes
  back `needsPrice`, the price is pending from the vendor. Say so; don't fill it.
