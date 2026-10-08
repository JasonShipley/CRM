# MCE Quoting — Standing Rules

Rules Jason Shipley has set for every Midwest Custom Engineering quote. Apply them on
every quote, proposal and quote email without being asked.

## Quote emails

- **Hammer mill quotes only** (not coolers, dryers, parts or other equipment):
  - Include this video line just before the sign-off, as a hyperlink (HTML `<a>`; in
    plain text put the URL on its own line):

    > Here is a video on our mills and why they are better than the rest.
    > [What Makes Our Mills Better? (You'll Notice at 2AM)](https://www.youtube.com/watch?v=2HlUqEfD350)

  - Attach `Hammermill Marketing Brochure_compressed.pdf` (Drive file id
    `1mTmHGuEdqG3o0eAoUtiXKE-fnNxJARhz`) along with the proposal PDF.
- All quote emails attach the proposal PDF.
- Layout to follow: the RD Equipment Co quote email of 2026-10-08 (subject
  "RE: RFQ Hammer mill"): greeting, proposal reference, "What's included" bullets,
  total / FOB / delivery / terms, open items, video line, "Let me know if you have
  any questions.", signature.
- Create the email as a Gmail draft; Jason sends it.

## Pricing sources

| Item | Source |
|---|---|
| Baghouse filter and fan | **FILTER LINE — HAND-OFF v7** sheet, Drive file id `1is5j8bL4FMlIzXU1TSBTTbSnSR63Bwyq` (all baghouse pricing lives here). Size with the baghouse calculator (`baghouse-filter-calculator.html`): system CFM = mill screen area × 1.3, MCE 7–7.5:1 air-to-cloth. Fan must be rated at or above the system CFM — step up from the sheet's paired fan if it is not. |
| Hammer mill, feeder + magnet, plenum | Hammermill sizing calculator (`hammermill-sizing-calculator-updated.html`): plenum = Bliss 10-ga weight at the design FPM × 1.35 duty × $15.25/lb. |
| Mill drive motors | TECO/TWMC 2026 price book, "MCE Sell Price" column (cost × 1.30 + $500 freight). |
| Rotary airlocks | Zoho catalog: PAV-10 $10,216 (0.424 cu ft/rev, 16 RPM), PAV-14 $14,750 (1.184 cu ft/rev @ 80%, 15 RPM). No current PAV-12 quote (0.76 cu ft/rev @ 80%, 8–20 RPM): price it at $13,617, the midpoint between the PAV-10/PAV-14 average and the PAV-14 (Jason, 2026-10-08). Size by RPM = ft³/hr ÷ 60 ÷ cu ft/rev; keep it under ~20 RPM. |
| Anything priced from a vendor quote | sell = cost ÷ 0.70. |
| Everything else | QBO / Zoho product catalog; if no real price exists, say so — never invent one. |

## Customer-facing documents

- No vendor or brand names (AirPro, Airlanco, Kice, Prater/PAV, TECO, Bliss, etc.) and
  no pricing-method words ("budgetary", "cost/0.7", "vendor quote") in proposals, PDFs
  or QBO line descriptions. Keep that detail in the private QBO memo.
- Proposal PDF layout: match `MCE_Proposal_Ozark_Organics_Rotary_Tumble_Cooler_ALT_12TPH_Soy_Cake_R2.pdf`
  (white header with logo, dark section bars, design basis, scope table, options,
  furnished by others, freight/delivery, terms, signature block, appendix).
