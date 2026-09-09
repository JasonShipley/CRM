# LETEK DCG / Bachoco — chicken manure digestate dryer

Engineering review of the dryer proposed to Bernardo Urquiza (LETEK DCG) for the Bachoco
layer farms outside Mérida, Yucatán. Internal document; not for customer issue.
Prepared 8 Sep 2026 against the customer's 20 Aug 2026 requirements.

Files:

| File | What it is |
|---|---|
| `pfd.html` | Process flow diagram, stream table, sizing cases, equipment list, open items (MCE-branded page; open in a browser) |
| `sizing_calc.py` | The mass and energy balance behind every number on the page. `python3 sizing_calc.py` reprints the tables. |

## Design basis (customer statements, 20 Aug 2026)

- 120 to 160 MT/day of biodigester effluent (chicken layer manure digestate) at 85% moisture; design point 140 MT/day.
- Dry to 15% moisture for reuse as bedding, balance to landfill.
- Burner must fire LPG and biogas (55% CH4). Biogas available: 7,455 Nm³/day = 145.77 MMBtu/day at 140 MT/day.
- Biogas conditioning to be included as an allowance; composition unknown.
- pH of two manure samples: 8.23 and 7.21.
- Site is 30 minutes from Puerto Progreso; earlier freight estimates stand.

## Verdict

**XD-96 Mk.2, 8 ft × 40 ft, is the right platform and is confirmed.** It is the same drum as the
Phibro XD-96 Mk.1, which carries a 30 MMBtu/hr burner. The dewatered flowsheet runs it at
2.1 lb water/hr·ft³, one third of the loading MCE used to size the XD-36 for this same customer in
March (6.1). Case B (press cake at 75% MC, 160 MT/day, 20 h) still sits at 3.7. The drum is sized for
the uncertainty in the press, not oversized for the feed.

| | Case A (design) | Case B (press underperforms) | Case C (no press) |
|---|---|---|---|
| Feed | 140 MT/d, 85% MC | 140–160 MT/d | 140 MT/d |
| Press cake | 70% MC | 75% MC | none, back-mix only |
| Hours/day | 24 | 24 / 20 | 24 |
| Water evaporated | 4,161 lb/hr | 5,447 / 7,470 lb/hr | 10,591 lb/hr |
| Thermal duty | 7.28 MMBtu/hr | 9.5 / 13.1 MMBtu/hr | 18.5 MMBtu/hr |
| Biogas covers | 83% | 64% / 56% | 33% |
| Drum loading | 2.07 lb/hr·ft³ | 2.7 / 3.7 | 5.3 |

Energy basis: 1,750 Btu per lb of water removed (MCE standard; theoretical 1,144). This reproduces the
numbers in the draft reply to Bernardo (7.3 and 18.5 MMBtu/hr, 83% coverage, US$420/day make-up LPG,
US$2,500/day all-LPG at US$14.50/MMBtu).

**Specify the burner at 15 MMBtu/hr, dual-fuel, 10:1 turndown, two NFPA 86 gas trains.** The draft
quote did not state a burner size. 15 covers case B worst; normal fire is 7.3. If the press is dropped
later, the drum takes the 30 MMBtu/hr assembly already drawn for the XD-96.

**Exhaust train: design for 14,000 ACFM at 230°F.** Case A is about 10,400 ACFM; 14,000 covers case B at
24 h. Cyclone ≈ 72 in barrel class (or two smaller in parallel) in 304 SS, ID fan ≈ 50 hp at 12 in WC.
Run the cyclone through MCE's calculator before it goes on the quote.

**Materials:** 316L drum shell and flights (digestate carries ammonia and chlorides at pH up to 8.2),
304 SS dropout box, ductwork, cyclone and fan.

## Process flow (see `pfd.html`)

Digester effluent → T-101 agitated tank → P-101 PC pump → SP-101 screw press (pressate back to
digester/lagoon, by others) → H-101 live-bottom hopper → FS-101 metering screw → B-101 dual-fuel burner /
D-101 XD-96 Mk.2 drum → dropout box → RV-101 airlock → CV-101 cooling conveyor → dried product.
Exhaust: dropout box → CY-101 cyclone (fines rejoin product via RV-102) → SC-101 acid scrubber
(optional, likely permit-driven) → FN-101 ID fan → stack.
Fuel: biogas → GC-101 conditioning (H2S removal, moisture knockout, booster blower, flame arrester) →
gas train; LPG tank and vaporizer (by others) → gas train; both to B-101 with automatic changeover.

## Open items that change the answer

1. **Press cake moisture** (70% vs 75% MC = 31% swing in duty). Bench-test the 5-gal sample with a press vendor.
2. **Solids capture / pressate.** Balance assumes 100% capture; real digestate presses capture 60–80% without polymer. The rest returns in ~70 MT/day of pressate and is not dried. LETEK must own that stream.
3. **Ammonia in the exhaust.** Heated pH-8 digestate strips ammonia. Expect a scrubber to be a permit condition; it is not in the quote.
4. **Biogas H2S and supply pressure.** Sets the conditioning skid and whether the gas train survives. Allowance stands until an analysis arrives.
5. **Operating hours.** 24 h assumed. At 20 h everything downstream of the press grows 20%.
6. **Effluent total solids.** If the digestate is really 10% TS rather than 15%, the tank, pump and press double; dryer duty is unchanged.
7. **Product cooling.** Dried manure at 180°F self-heats in a pile; cool below 120°F before storage.

## Confidence

High on the drum and the thermal duty for a given cake moisture. Medium on exhaust volume and cyclone
size (first-principles, pending MCE calculator). Low on anything downstream of the press until a sample
is tested. No prices or lead times in this document; those belong to the quote.

## Calculator run and quote (9 Sep 2026)

`case_letek_140tpd.json` is the case file for the MCE Dryer HMB Calculator (`../dryer-hmb-calculator/run_case.py`).
`LETEK_140tpd_caseA.xlsx` is the run and `LETEK_140tpd_caseA_Flow.pdf` the customer Flow page. The calculator
selected the XD-96 8 ft x 40 ft on airflow (12,934 ACFM at 230 F, 74% utilization), 7.28 MMBtu/hr on the MCE
basis (6.61 rigorous), 50 hp fan at 12 in WC, 22 in duct, 366 lb/hr propane before biogas credit.

QBO draft estimate 20260909-LETEK-A (customer LETEK DCG, created 9 Sep 2026): catalog-priced lines total
$147,818.58; the XD-96 system, dual-fuel burner, screw press, biogas skid and XF-36 fan are $0 placeholders
until priced. Not sent.

## Calculator run and quote (9 Sep 2026)

- `case_letek_140tpd.json` + `../dryer-hmb-calculator/run_case.py` → `LETEK_140tpd_caseA.xlsx` and `LETEK_140tpd_caseA_Flow.pdf` (the PFD). The calculator selected the XD-96 8×40 on its own; burner oversized to 10 MMBtu/hr per Jason.
- `make_quote.py <hubspot products csv>` → `MCE_Quote_20260909-LETEK-A_Chicken_Manure_Dryer.pdf`, rendered with the repo's branded quote template and priced from the HubSpot product export of 24 Aug 2026 (not committed). Priced subtotal $718,822; burner, stainless option, screw press and biogas skid are TBD lines.
- QBO draft estimate 20260909-LETEK-A exists on customer LETEK DCG (created 8 Sep 2026); not sent.

## Pricing basis for the open lines (9 Sep 2026, afternoon)

### 316L stainless option: priced from the Phibro Animate North Dryer

MCE's only built 8' x 40' 316L system is the Phibro Animal Health (Quincy, IL) "Animate North Dryer",
quote ref 20220510-162131559 of 10 May 2022, accepted on Phibro PO 479135 (16 May 2022) and invoiced in full
(invoices 1332-1, 1335-1, 2022-16-2). Same drum size as the XD-96, so it is the right precedent.

| Phibro line (May 2022)                                             | Price        |
|--------------------------------------------------------------------|-------------:|
| XC Series 316L drum system, 8' x 40', 1/2" shell, sub-arc, X-ray; 316L live bottom, drop-out box, airlock; R-15 with 304 cladding | $1,529,000 |
| Burner: Honeywell / Access RA2500, 25 MMBtu/hr, valve train, BMS, 316 SS NYB blower, inlet plate, muffler | $279,895 |
| 2 x HE-47 cyclone, 10 ga 316L                                       | $43,900      |
| 2 x VBS 14x10x10 airlock, 304L                                      | $31,930      |
| FC41W42 fan, 316L, 200 hp, 25,000 CFM at 22 in WC                  | $114,521     |
| **Total (PO value)**                                               | **$1,999,246** |
| Not taken: 5/8" shell adder $59,855; enlarged drop-out box $56,000; 316L wet scrubber $241,500 | |

Comparison of the three stainless bases MCE has used on this job:

| Basis                                          | 316L dryer system | Adder over XD-96 Mk.2 A36 ($589,500) |
|------------------------------------------------|------------------:|-------------------------------------:|
| Phibro 2022 actual (same 8' x 40' drum)        | $1,529,000        | $939,500                             |
| "316 doubles the price" (J. Shipley, Mar 2026) | $1,179,000        | $589,500                             |
| L. Wilkinson quote to LETEK, 27 Mar 2026 (XD-72 basis, $489,000): 304 +$358,000, 316L +$422,500 | $911,500 (scaled) | $422,500 |

The Phibro number is the only one backed by a built job and it is 2022 pricing, so it is a floor, not a
ceiling. The quote (line 3) and QBO estimate 6476 now carry the 316L drum system as an **option at the
Phibro basis: $1,529,000 for the system, a $939,500 adder over line 1, not in the total.** Fan, ducting and
cyclone in 316L are "on request" (the 304 cyclone adder of $21,000 stays on line 7). A full 316L system on
the Phibro basis with the smaller 10 MMBtu burner and 60 hp fan would land near $1.7-1.8M before the press
and biogas skid; Phibro's $2.0M included a 25 MMBtu burner and a 200 hp 316L fan.

### Burner, press and biogas skid: vendor RFQs drafted (not sent)

No usable vendor pricing on file. Three Gmail drafts are in the Drafts folder for Jason to review and send:

- **Vincent Corporation (Tampa), fred@vincentcorp.com** - screw press, 12,900 lb/hr digestate at 15% TS to
  30% TS cake, 316 SS, options for tank, PC pump, polymer, spares; net dealer pricing FOB Tampa. Jason's
  last contact with Fred was the May 2026 "Press for grain" inquiry (no reply on file).
- **BDC (Hazelwood, MO), Joe Kovacs, joek@gobdc.com** - 10 MMBtu/hr dual-fuel LPG + biogas combustion system,
  two NFPA 86 trains with changeover, parallel-positioning control like the 2024 Animate proposal (BDC
  proposal 323581, 12 Jun 2024; BDC quoted the 2022 30 MMBtu Animate system at $115,170 on 0622-06 Rev-1,
  which MCE sold at $279,895). The 323581 PDF is only in Gmail; its price was not extracted.
- **Biogas conditioning skid** - recipient left blank (no vendor on file); 195 scfm, H2S 5,000 to under
  200 ppm, moisture knockout, booster to 2 psig.

MCE convention for these lines once vendor net pricing arrives: sell = vendor net / 0.8 (Jan 2026
Roastamatic thread), then update lines 2, 10 and 11 in `make_quote.py` and QBO estimate 6476.
