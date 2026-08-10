# Phase 2 — HubSpot → Twenty Field Mapping (for sign-off)

**Status:** ⛔ GATE — nothing imported yet. All data below was discovered live from MCE's
HubSpot portal via the CRM API (read-only) on 2026-08-10. No pipeline stages, fields, or
owners were invented.

## What's in HubSpot today

| Object | Count | Notes |
|---|---|---|
| Companies | **824** | 804 have a domain |
| Contacts | **5,652** | 4,013 have an email; 769 have a company association |
| Deals | **271** | single pipeline ("Sales Pipeline") |
| Notes | 61 | engagement |
| Calls | 101 | engagement |
| Tasks | 158 | engagement |
| Emails | 23,391 | synced inbox copies — see "intentionally not migrated" |
| Meetings | 0 | — |
| Products | 236 | catalog — relevant to Phase 4 quoting |
| Quotes (HubSpot) | 335 | historical quotes — optional import, see questions |

**Owners (13 total, 6 active):** Jason Shipley, Ron Dominguez, Mike Buckskin, Jason Bliss,
Paula Salazar, Kaitlyn Arrington (active); Dear Data, Deb Cross, Sammy Pate, Magda Baptista,
Lorand Wilkinson, Ross Jamison, Terry Geschwentner (deactivated — their records still carry
their names).

**Deal pipeline — mirrored exactly, one pipeline, 7 stages** (current record counts):

| HubSpot stage (internal value) | Deals | Twenty Opportunity stage |
|---|---|---|
| Appointment Scheduled (`appointmentscheduled`) | 249 | Appointment Scheduled |
| Qualified / Presentation Scheduled (`qualifiedtobuy`) | 1 | Qualified / Presentation Scheduled |
| First Presentation (`presentationscheduled`) | 8 | First Presentation |
| Decision Maker Bought-In (`decisionmakerboughtin`) | 0 | Decision Maker Bought-In |
| Contract Sent (`contractsent`) | 0 | Contract Sent |
| Closed Won (`closedwon`) | 5 | Closed Won |
| Closed Lost (`closedlost`) | 8 | Closed Lost |

Twenty's default Opportunity stage options (New/Screening/Meeting/Proposal/Customer) will be
**replaced** with these seven, same order, same labels.

**Custom properties found:** exactly one in the entire portal —
`hydrophos_contact_affiliation` on contacts (enum: Hydrophos / MCE; 6 contacts marked
Hydrophos, remainder unset). It will be carried over. Companies and deals have zero custom
properties.

## Owner handling

Twenty assigns records to workspace *users*, who only exist after accepting an invite. To
keep migration faithful and not block on sign-ups:

- Every migrated Company, Person, and Opportunity gets a **`HubSpot Owner` select field**
  (options = the 13 owner names above) populated from `hubspot_owner_id`.
- After the 6 active users log in to Twenty, Company `accountOwner` can be pointed at the
  real user accounts (10-minute follow-up; the select field keeps the historical truth
  either way, including for the 7 deactivated owners).

## Field mapping

Every migrated record also gets **`hubspotId`** (text, from `hs_object_id`) — the
idempotency key: re-running the import matches on it and updates instead of duplicating —
and **`sourceCreatedAt`** (HubSpot create date; Twenty's own createdAt is system-set and
can't be back-dated).

### Companies → Companies

| HubSpot | Twenty | Type |
|---|---|---|
| `name` | `name` | standard |
| `domain` (fallback `website`) | `domainName` | standard |
| `address`, `address2`, `city`, `state`, `zip`, `country` | `address` (composite) | standard |
| `numberofemployees` | `employees` | standard |
| `linkedin_company_page` | `linkedinLink` | standard |
| `annualrevenue` | `annualRecurringRevenue` | standard (note: HubSpot value is company revenue, not ARR — same money box, label kept as Twenty ships it) |
| `phone` | `phone` | **custom** PHONES |
| `description` | `description` | **custom** TEXT |
| `industry` | `industry` | **custom** TEXT (HubSpot's 150-option enum; stored as text, lossless) |
| `lifecyclestage` | `lifecycleStage` | **custom** SELECT (Lead 699 / Opportunity 121 / Customer 4) |
| `hubspot_owner_id` | `hubspotOwner` | **custom** SELECT (see above) |

### Contacts → People

| HubSpot | Twenty | Type |
|---|---|---|
| `firstname` / `lastname` | `name` | standard |
| `email` | `emails.primaryEmail` | standard |
| `phone` / `mobilephone` | `phones` (primary / additional) | standard |
| `jobtitle` | `jobTitle` | standard |
| `city` | `city` | standard |
| company association | `company` relation | standard (769 contacts) |
| `lifecyclestage` | `lifecycleStage` | **custom** SELECT (Lead 5,312 / Opportunity 281 / Subscriber 41 / Customer 18) |
| `hs_lead_status` | `leadStatus` | **custom** SELECT (New 137, Open 3, Open Deal 3, Connected 2, rest unset) |
| `hydrophos_contact_affiliation` | `affiliation` | **custom** SELECT (Hydrophos / MCE) |
| `hubspot_owner_id` | `hubspotOwner` | **custom** SELECT |

### Deals → Opportunities

| HubSpot | Twenty | Type |
|---|---|---|
| `dealname` | `name` | standard |
| `amount` | `amount` (USD) | standard |
| `closedate` | `closeDate` | standard |
| `dealstage` | `stage` | standard (options replaced, table above) |
| primary company association | `company` relation | standard |
| first contact association | `pointOfContact` relation | standard |
| `description` | `description` | **custom** TEXT |
| `closed_won_reason` / `closed_lost_reason` | **custom** TEXT — created only if the dry run finds any values | |
| `hubspot_owner_id` | `hubspotOwner` | **custom** SELECT |

### Engagements

| HubSpot | Twenty | How |
|---|---|---|
| Notes (61) | Notes | body → note body; linked to the same companies/people/opportunities; original date noted in body header |
| Calls (101) | Notes | titled `Call: <title>`; Twenty has no call object — logged calls preserved as notes |
| Tasks (158) | Tasks | title, body, status, due date; linked to same records |
| Meetings (0) | — | nothing to migrate |

## Intentionally NOT migrated (the honest list)

- **Emails (23,391)** — these are synced inbox copies, not hand-logged records. Importing
  them as notes would bury every record in noise. Recommendation: connect Gmail sync inside
  Twenty (Settings → Accounts) and mail flows in natively going forward. If you want the
  history in the CRM anyway, say so and I'll import them as a separate linked object.
- **HubSpot computed/analytics fields** — traffic sources, page views, intent signals,
  predictive scores, stage-timer fields (`hs_v2_*`), rollup counts (`num_associated_*`,
  `notes_last_*`), enrichment fields (Twitter/Facebook followers, timezone, etc.). These are
  recalculated by the platform, not source data.
- **`dealtype`** — populated on exactly 1 of 271 deals; not worth a field (noted in the
  migration report).
- Contact street address/state/zip — Twenty's Person has only `city` standard; street-level
  contact addresses are rare in this portal. (Company addresses migrate in full.)

Anything above can be promoted to "migrate" before sign-off — nothing is lost until then,
and HubSpot stays untouched either way.

## Open questions at this gate

1. **Approve the mapping** above (including the 7-stage pipeline replacement)?
2. **Emails**: skip + Gmail sync (recommended), or import 23k emails?
3. **Products (236)**: import the catalog into Twenty in Phase 4 so quote line items can
   pick from real parts (recommended)?
4. **Historical HubSpot quotes (335)**: import into the new Quote object in Phase 4 so
   quote history lives on deals (recommended), or start fresh?
