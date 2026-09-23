# MCE CRM — Twenty + Quoting

This is Midwest Custom Engineering's self-hosted CRM: [Twenty](https://twenty.com)
(open source) with all HubSpot data migrated in, plus a quote builder that sizes
equipment with MCE's own calculators and produces MCE-branded quote PDFs. This
README is the runbook — written so a non-developer can operate everything.

## What's running

| Piece | What it is | Where |
|---|---|---|
| Twenty CRM | the CRM itself (app, worker, PostgreSQL, Redis) | `https://crm.usemce.com` |
| Quote builder | the sales team's quote form, the sizing calculators, and the branded PDF | `https://quotes.usemce.com` |

**Where credentials live:** `deploy/credentials.local` on the server (never in git).
It holds the admin login for Twenty. Keep a copy in your password manager.

**Who can reach the quote builder:** nobody without the login. `quotes.usemce.com`
sits behind Caddy basic auth (user `mce`), and the service itself is bound to
localhost, so it is only reachable through Caddy — never straight off the
internet. That matters more than it used to: the builder now carries MCE's
sizing calculators, the XM model tables and the pricing basis. To add a second,
app-level password on top, set `RENDERER_PASSWORD` and `RENDERER_SECRET_KEY` in
`deploy/.env` and restart. To change the Caddy password, generate a new hash with
`docker compose exec caddy caddy hash-password` and paste it into
`deploy/Caddyfile`.

---

## Daily use

### Log in
Open `http://<server>:3000` and sign in with the email/password from
`deploy/credentials.local` (or your own account once invited: Settings → Members).

### Build a quote

Open `https://quotes.usemce.com` and click **+ New quote**. The form runs top to
bottom:

1. **Customer** — company, contact, email, phone, address. These print on the
   proposal.
2. **Quote details** — name, quote # (filled in for you as `YYYYMMDD-N`),
   project, valid-until date, purchase terms and the cover paragraph
   (**Comments to buyer**). Leave **Contract value** blank and the total comes
   from the lines.
3. **Size the equipment** — pick a tab, enter the job, press **Size it**:
   - **Hammermill + Plenum** — capacity, screen size, product. Returns the XM
     model, motor HP, screen area, rotary feeder, plenum and discharge screw,
     with package pricing. Choosing a product fills in its index, screen area
     per HP and bulk density; all three stay editable.
   - **Counterflow Cooler** — production rate and product. Returns the cooler
     model, air system and option pricing.
   - **Baghouse Filter** — system CFM, or the mill screen area the hammermill
     just reported, and it sizes off the same airflow the mill does.

   Check the result, then **Add to quote** to drop the priced lines into the
   line items below. Size as many as the job needs — they all land on one quote.
4. **Line items** — everything is editable: name, the spec lines that print as
   bullets, qty, unit price, discount. **+ Add line** for anything the
   calculators don't cover. Leave **Line total** blank to compute
   qty × (price − discount).
5. **Save** or **Save & open PDF** at the bottom. The PDF is the Equipment
   Proposal you email.

Lines the calculators size but don't price — screw conveyors and baghouses —
come in at **$0.00 and are highlighted**. Put a price on them before the quote
goes out.

### The calculators on their own

**Calculators** in the top bar opens MCE's full sizing workbenches — the same
files that were on Jason's desktop, now hosted behind the same login. Use these
when you want the whole reference: index chart, model tables, feeder and screw
tables, pricing multipliers. The quote form runs the same math; these show all
the working.

### Quotes already in the CRM

**CRM** in the top bar lists the quotes held in Twenty (everything migrated from
HubSpot) and renders them with the same branded layout. Quotes built in the
builder are stored separately for now — tying the two together is the next step.

### When a customer accepts
1. Change the quote's **Status** to **Accepted**.
2. The QuickBooks sync (below) creates a matching **QBO Estimate** so accounting can
   raise the down-payment invoice without re-keying. The estimate's ID appears on the
   quote in the **QBO Estimate ID** field once synced.

---

## Server operations (copy-paste)

All commands run on the server, from the repo folder (e.g. `/opt/mce-crm`).

| Task | Command |
|---|---|
| Start everything | `cd deploy && docker compose -f docker-compose.yml -f docker-compose.renderer.yml -f docker-compose.caddy.yml up -d` |
| Stop everything | `cd deploy && docker compose -f docker-compose.yml -f docker-compose.renderer.yml -f docker-compose.caddy.yml down` |
| See status | `docker compose ps` |
| View app logs | `docker compose logs --tail 100 server` |
| Restart after a reboot | nothing — containers auto-start (`restart: always`) |
| Update Twenty | edit `deploy/.env`, change `TAG=` to the new version, then `docker compose pull && docker compose up -d` |
| Back up now | `sudo deploy/backup.sh` |
| Restore a backup | `gunzip -c /var/backups/mce-crm/twenty-db-<stamp>.sql.gz \| docker compose exec -T db psql -U postgres -d default` |

Nightly backups: `deploy/backup.sh` is installed in root's crontab (2:15 AM, keeps 30
days, database + uploaded files) during production setup.

## Accepted quote → QuickBooks estimate

The sync is operated by MCE's Claude workspace (which holds the QuickBooks connection):

- A scheduled task lists quotes with Status = Accepted and no QBO Estimate ID
  (`python3 migration/accepted_quotes.py --list`), creates the matching estimate in
  QuickBooks Online (same line items, quantities, prices, discounts), and writes the
  estimate ID back (`--mark`).
- To trigger it manually, ask Claude: *"sync accepted quotes to QuickBooks."*

## If something looks wrong

1. `docker compose ps` — anything not "healthy"? `docker compose up -d` fixes most states.
2. App up but login failing → check `deploy/credentials.local` wasn't changed.
3. PDF button erroring → `docker compose -f docker-compose.yml -f docker-compose.renderer.yml restart quote-renderer`.
3b. Quote builder says the CRM is unreachable → only the **CRM** tab needs Twenty.
   Building quotes, sizing and PDFs keep working; check Twenty with
   `docker compose ps`.
4. Disk full → old backups: `du -sh /var/backups/mce-crm`, prune with `find ... -delete`
   (see `backup.sh`), or grow the server volume in the Hetzner console.

## Project history

- `docs/phase0-decision-memo.md` — hosting/quoting decisions (signed off)
- `docs/phase2-field-mapping.md` — HubSpot → Twenty field mapping (signed off)
- `docs/phase3-migration-report.md` — migration results: all counts match, idempotent
- `docs/examples/` — MCE's example quotes (the renderer's source of truth) + a rendered sample
- `docs/quote-builder.md` — how the builder and the calculator ports fit together
- `docs/hetzner-checklist.md` — production server provisioning steps
- `migration/` — all migration/import scripts (safe to re-run; never duplicate)
- `renderer/` — the quote builder + renderer service
  - `renderer/tools/` — MCE's own calculators, hosted unmodified
  - `renderer/calculators/` — the Python ports the quote form sizes with
  - `renderer/tests/` — proves the ports still match the originals
