# Rep Enumeration Playbook

The step-by-step method for building the CPM/Bliss representative register. Referenced by
`rep-network-builder/SKILL.md`. Sources are ordered by value, not by convenience — work them
in order and stop escalating once a source is exhausted rather than running every pass every time.

## Confirmed background facts

Keep these current; re-verify the dated ones on each refresh pass.

| Fact | Status | Date |
|---|---|---|
| CPM announced acquisition of Jacobs Global, an aftermarket parts supplier for hammermills and pellet mills | Public, confirmed | Dec 2024 |
| Jacobs Global founded 1934; served 4,000+ mills in 80+ countries | Public, per CPM announcement | Dec 2024 |
| CPM's stated rationale: expand aftermarket parts portfolio, market reach, capacity | Public, confirmed | Dec 2024 |
| Rosebank Industries closed acquisition of CPM from American Securities (~$2.1–3.25B) | Public, confirmed | ~May 12, 2026 |
| Bliss Industries publishes a public state-by-state US rep locator | Public, confirmed | Aug 2026 |
| CPM supports customers via a worldwide network of local agents in nearly every country | Public, CPM's own wording | Aug 2026 |
| **CPM moved parts business from legacy CPM/Bliss reps to the Jacobs channel; those reps are unhappy** | **Owner's market intelligence — NOT publicly confirmed** | Aug 2026 |

That last row is the entire premise of the recruiting push, and it is unverified publicly. It is
plausible and consistent with the acquisition, but it must be validated rep by rep. Never assert it
to a rep as fact — ask them what changed and let them characterize it.

## Tier 1 — Jason Bliss

Before any web research. Ask him, by region:

- Which rep firms carried Bliss and Roskamp Champion equipment and parts, and who the principal was at each
- Which of them made most of their money on parts
- Which have already lost the parts line, and which are angry about it
- Which ones he has a personal relationship with, and how warm it actually is
- Which ones are *not* worth approaching, and why — a rep with a reputation problem costs more than the territory is worth
- International agents he knows by name

Capture his answers as **confirmed-firsthand** in the register and cite him as the source. This is the
one source that yields disaffection signal directly, which no directory can give you.

## Tier 2 — published rep locators, brand by brand

Every CPM brand may run its own rep network. A rep who lost Bliss parts may still appear under
Roskamp Champion, or vice versa. Work the full brand family, not just Bliss:

- **Bliss** — `bliss-industries.com/contact-us/sales-representatives/` — state-by-state click-through
  locator covering all 50 states. This is the backbone of the US register. Enumerate every state;
  the same firm will appear across several, which is itself useful (it tells you territory size).
- **Roskamp Champion** — check `cpmroskamp.com` and the Roskamp brand pages on `onecpm.com`
- **CPM core / OneCPM** — `onecpm.com`, including the brands index and the locations and contact pages
- **Remaining CPM brands** — pull the current brand list from `onecpm.com/about-cpm/our-brands` on each
  refresh (the roster changes with acquisitions) and check each for its own rep or distributor locator
- **Jacobs Global** — the channel parts *went to*. Its distributor list is the inverse register: reps
  on it got the business, reps who vanished from a CPM locator without appearing here likely lost it.

**Method note:** these locators are click-per-state or click-per-region, so enumeration means visiting
each state, not fetching one page. Record for each firm: name, principal, phone, email, address, states
covered, and which brand's locator it appeared on.

**Diffing is the highest-value part of this tier.** Snapshot each locator on every refresh pass and
compare against the last. A firm that **disappears** from a CPM brand locator is the strongest public
evidence available that the relationship ended — those go straight to the top of the priority ranking.
Store dated snapshots so the diff is possible; without them this tier only ever gives you a static list.

## Tier 3 — Apollo.io enrichment

Locators give firm names. Apollo gives named humans with contact paths.

- `apollo_mixed_companies_search` — find rep, distributor, and agency firms serving feed, grain, pet
  food, biomass, wood pellet, ethanol/biofuel, and oilseed processing equipment. Filter by geography to
  fill known territory gaps in the register.
- `apollo_mixed_people_api_search` — find the **principal or owner**, not a junior salesperson. At a
  small rep firm the owner is the decision-maker on adding a line. Useful titles: Owner, President,
  Principal, Partner, Manufacturers Representative, Regional Sales Manager, Territory Manager.
- `apollo_people_match` / `apollo_organizations_enrich` — enrich a firm already on the register from a
  locator with emails, phones, and headcount.
- `apollo_contacts_create` / `apollo_labels_*` — stage the recruiting list under a dedicated label so it
  stays separate from the Parts Growth Agent's end-customer prospecting.

**Credits:** these tools consume Apollo credits. Surface the estimated cost before any bulk enrichment,
and the credits used plus the new balance after it settles — unprompted, every time.

## Tier 4 — trade and open sources

- **Trade show exhibitor and attendee lists** — IPPE is the big one for feed and pet food; also the
  biomass and pellet fuel shows. Rep firms exhibit alongside or in place of the OEMs they carry.
- **Supplier directories** — Feed & Grain, FeedMachinery, Pet Food Processing buyers' guides. These list
  brands *and* often the regional representation behind them.
- **AFIA** membership, especially the equipment manufacturer side.
- **LinkedIn** — search the brand names against rep-style titles. Watch for the signals a locator can't
  show: a headline that dropped a brand, a new line announced, a job change, or a post complaining about
  a principal. These are public and often more current than any directory.
- **Trade press** — Feed & Grain, Milling and Grain, Bioenergy International, Pet Food Processing,
  Processing Magazine all cover rep appointments and channel changes. A "Company X appoints Y as rep for
  Z territory" item is a dated, citable channel fact.

## Tier 5 — international

Sequence this **after** the US register is real and after Jason has answered the international-readiness
question in SKILL.md. Approaching an overseas agent MCE can't actually supply wastes the introduction.

- Jacobs Global's 80+ country footprint is the best available proxy for where Bliss-type hammer-mill
  parts demand already exists. Where Jacobs served mills, mills exist.
- CPM's own international presence spans North America, South America, Europe, the Middle East, and
  Asia, supported by local agents — that agent layer is the recruiting target.
- Regional CPM sites (e.g. the `.cn` domain) sometimes list local contacts the `.com` site does not.
  Check region-specific domains separately.
- Prioritize English-language markets with established feed and biomass industries first — Canada,
  Australia, New Zealand, UK, Ireland — then Latin America where CPM's presence is heavy.
- For each international agent, record the practical blockers alongside the contact: freight route and
  cost, import duties on wear parts, lead time, payment terms and currency, and whether MCE can
  realistically support them. An agent with no supply path is not a lead.

## Register schema

Maintain one row per rep firm. Suggested columns:

`firm_name` · `principal_name` · `title` · `email` · `phone` · `city_state` · `territory_states` ·
`country` · `cpm_brands_carried` · `other_lines_carried` · `est_hammermill_accounts` ·
`parts_share_of_business` · `lost_parts_line` (yes/no/unknown) · `disaffection_signal` ·
`source` · `source_confidence` (confirmed-firsthand / confirmed-public / inferred) ·
`jason_bliss_relationship` · `contract_constraints_known` · `priority_tier` · `status` · `last_touch` ·
`next_action`

`source_confidence` is not optional. A register that silently mixes Jason Bliss's firsthand knowledge
with a guess off a directory listing will get someone called who shouldn't be, and will make the whole
register untrustworthy the first time that happens.

`contract_constraints_known` exists so the non-solicitation boundary in SKILL.md is enforceable rather
than aspirational. If a rep tells you they're bound by an exclusivity or non-compete clause, it gets
recorded here and the row stops advancing until Jason and counsel clear it.

## Qualification scoring

Rank on these, in rough order of weight:

1. **Hammer-mill density in territory** — how many Bliss-type mills are actually in their book. Nothing
   else compensates for a thin territory.
2. **Parts share of their historical revenue** — the higher it was, the more the Jacobs consolidation
   hurt, and the more motivated they are.
3. **Jason Bliss relationship** — a warm personal intro converts at a completely different rate than a
   cold call, and costs less of everyone's time.
4. **MCE territory gap** — a rep covering a region where MCE has no presence is worth more than one
   overlapping the direct team's existing accounts.
5. **Line compatibility** — complementary non-competing lines are good (they're already calling on the
   right plants); a competing parts line is disqualifying until it's resolved.
6. **Contract freedom** — a rep who is free to add a line today outranks a better-positioned rep who is
   locked up for a year.

## Anti-patterns

- Asserting "CPM took your parts business away" to a rep as established fact. Ask; don't tell.
- Treating a directory listing as proof a rep still represents that brand. Locators go stale.
- Filling gaps in the register with plausible-looking guesses instead of leaving them blank or `unknown`.
- Substituting web-search snippets for a locator page that couldn't be fetched, and not saying so.
- Approaching international agents before MCE can actually supply them.
- Drafting anything that helps a rep get around a contract they've told you they're bound by.
- Letting this register drift into an end-customer prospect list — that's the Parts Growth Agent's job,
  and duplicating it here means two skills maintaining the same accounts differently.
