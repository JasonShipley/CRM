# Phase 3 — Migration Dry Run (for sign-off)

**Status:** ⛔ GATE — nothing has been loaded into Twenty. All HubSpot data has been
extracted read-only, transformed to Twenty payloads, and validated locally. The load
runs only after your go-ahead.

## What will be created in Twenty

| Twenty object | To create | Source | Notes |
|---|---|---|---|
| Companies | **824** | 824 HubSpot companies | 100% of source |
| People | **5,663** | 5,663 HubSpot contacts | 100% of source (portal grew from 5,652 during discovery — live system) |
| Opportunities | **271** | 271 HubSpot deals | 100% of source; correct stage + owner on every one |
| Notes | **162** | 61 notes + 101 logged calls | calls become notes titled "Call: …" (Twenty has no call object) |
| Tasks | **158** | 158 HubSpot tasks | status + due date preserved |
| Relations on records | 1,273 | associations | 756 person→company, 258 opp→company, 259 opp→contact |
| Note/task links | 830 | associations | 280 note links + 550 task links to their people/companies/deals |

**Verification already performed:**
- Extraction counts match the portal totals exactly for every object.
- Every association ID cross-checked against extracted records: **zero unresolved IDs**.
- Loader dry-run executed against the live Twenty instance (auth, schema, and querying
  all confirmed working; 0 existing records — clean target).

## Fidelity details

- **Stages:** Appointment Scheduled 249 · Qualified/Presentation Scheduled 1 · First
  Presentation 8 · Closed Won 5 · Closed Lost 8 (Decision Maker Bought-In and Contract
  Sent are configured, currently 0 deals).
- **Deal owners:** Jason Shipley 233 · Jason Bliss 27 · Paula Salazar 8 · Lorand
  Wilkinson 2 · Magda Baptista 1.
- **Field coverage carried over** (people): email 4,024 · job title 2,384 · phone
  1,735 · owner 1,591 · city 580 · lead status 145. (Companies): domain 804 · owner
  135 · city 129 · phone 111 · industry 31.
- **Idempotency:** every record carries its `hubspotId`; re-running the load matches
  and updates instead of duplicating. Twenty's 16 demo seed records are purged first.
- **Nothing fabricated:** blank stays blank. Contacts with no first/last name fall back
  to HubSpot's own display value (email-derived), never an invented name.

## Known deltas (the honest list)

1. **Emails (23,391)** — skipped per your sign-off; connect Gmail sync in Twenty instead.
2. **dealtype** — populated on exactly 1 of 271 deals ("New Business" on one deal);
   not migrated as a field (recorded here instead), per the approved mapping.
3. **~13 secondary company links on contacts** — HubSpot allows a contact to be linked
   to several companies; Twenty's data model has one company per person. The primary
   company migrates (756 links); secondary links have no equivalent field. (A HubSpot
   API daily quota also prevented enumerating them today; they would be unusable in
   Twenty regardless.)
4. **closed_won_reason / closed_lost_reason** — zero values found in the portal;
   nothing to migrate (fields not created, per the approved mapping).
5. **Products (236) and historical quotes (335, with their line items)** — approved for
   import; they load in Phase 4 when the Quote and Product objects exist. Quote→deal/
   company/contact links are already extracted and validated. (Line-item→quote pairing
   hit HubSpot's daily cross-object query cap mid-extraction; the remainder is scheduled
   to finish automatically after the cap resets — it does not affect this Phase 3 load.)

## On your go-ahead

`python3 migration/load.py --purge-demo` — loads in dependency order (companies →
people → opportunities → notes → tasks → links), then produces the final migration
report with created/updated/failed counts per object and spot-check instructions.
