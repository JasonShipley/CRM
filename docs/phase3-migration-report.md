# Phase 3 — Migration Report (final)

**Status: ✅ Complete.** All HubSpot CRM data is loaded into Twenty. HubSpot was never
modified — every operation against it was read-only.

## Record counts — HubSpot vs Twenty

| Object | HubSpot | Twenty | Match |
|---|---|---|---|
| Companies | 824 | **824** | ✅ |
| Contacts → People | 5,663 | **5,663** | ✅ |
| Deals → Opportunities | 271 | **271** | ✅ (stage + owner on every record) |
| Notes + Calls → Notes | 61 + 101 | **162** | ✅ |
| Tasks | 158 | **158** | ✅ |
| Note links | — | 280 | all extracted associations |
| Task links | — | 550 | all extracted associations |
| Person → company relations | 756 | 756 | primary association |
| Opportunity → company / contact | 258 / 259 | 258 / 259 | ✅ |

**Idempotency verified:** immediately after the load, the migration was re-run in full —
`0 to create` on every object, counts unchanged. Re-running never duplicates.

**Spot-check (deal `47831627158`):** "Water Treatment Plant" — $29,920,000, stage
Appointment Scheduled, owner Magda Baptista, company I-Town Rail and Commerce
(itownrc.com), point of contact Gary Hendry (gary@itownrc.com). Matches HubSpot exactly.

## Deltas and data notes (complete list)

1. **Emails (23,391)** — intentionally skipped per sign-off. Connect Gmail sync inside
   Twenty (Settings → Accounts) for email going forward.
2. **Duplicate company domains (193)** — Twenty enforces unique domains; HubSpot doesn't.
   Where several HubSpot companies shared a domain, the first keeps it and the rest are
   listed (with values) in `data/transformed/unmapped.json`. One additional case (Kice
   Industries) had its domain held by a sibling record and was dropped+logged the same way.
   All companies themselves migrated.
3. **Unparseable phone numbers (203: 193 people, 10 companies)** — non-US/Canada formats
   and malformed strings that Twenty's phone validation rejects. Not guessed; the original
   strings are preserved in `data/transformed/unmapped.json`.
4. **`dealtype`** — populated on exactly 1 of 271 deals; recorded here, not migrated as a field.
5. **Secondary company links on contacts (~13)** — Twenty's model is one company per
   person; each contact's primary company migrated.
6. **closed won/lost reasons** — no values exist in the portal; nothing to migrate.
7. **Products (236) & historical quotes (335)** — load in Phase 4 with the Quote/Product
   objects. Quote↔deal/company/contact links already extracted and validated; line-item
   pairing resumes automatically when HubSpot's daily query quota resets.

## Where things live

- Migration tooling: `migration/` (schema setup, ingest, transform, idempotent loader)
- Extracted data + logs: `data/` (gitignored — contains customer data)
- Field mapping (as approved): `docs/phase2-field-mapping.md`
- Instance (build env): http://localhost:3000 — login in `deploy/credentials.local`
- Production deployment: pending Hetzner server (`docs/hetzner-checklist.md`)
