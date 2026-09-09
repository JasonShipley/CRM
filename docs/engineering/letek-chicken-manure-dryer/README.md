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

- `case_letek_140tpd.json` + `../dryer-hmb-calculator/run_case.py` → `LETEK_140tpd_caseA.xlsx` and `LETEK_140tpd_caseA_Flow.pdf` (the PFD). The calculator selected the XD-96 8×40 on its own; burner oversized to 15 MMBtu/hr per Jason.
- `make_quote.py <hubspot products csv>` → `MCE_Quote_20260909-LETEK-A_Chicken_Manure_Dryer.pdf`, rendered with the repo's branded quote template and priced from the HubSpot product export of 24 Aug 2026 (not committed). Priced subtotal $718,822; burner, stainless option, screw press and biogas skid are TBD lines.
- QBO draft estimate 20260909-LETEK-A exists on customer LETEK DCG (created 8 Sep 2026); not sent.
