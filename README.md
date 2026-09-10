# MCE CRM — Twenty + Quoting

This is Midwest Custom Engineering's self-hosted CRM: [Twenty](https://twenty.com)
(open source) with all HubSpot data migrated in, plus a quoting system that produces
MCE-branded quote PDFs. This README is the runbook — written so a non-developer can
operate everything.

## What's running

| Piece | What it is | Where |
|---|---|---|
| Twenty CRM | the CRM itself (app, worker, PostgreSQL, Redis) | `http://<server>:3000` |
| Quote renderer | turns a Quote into a branded web page + PDF | `http://<server>:8090` |

**Where credentials live:** `deploy/credentials.local` on the server (never in git).
It holds the admin login for Twenty. Keep a copy in your password manager.

---

## Daily use

### Log in
Open `http://<server>:3000` and sign in with the email/password from
`deploy/credentials.local` (or your own account once invited: Settings → Members).

### Create a quote
1. Open the **Opportunity** (deal) the quote belongs to — or skip this and start from
   the Quotes tab.
2. In the left sidebar choose **Quotes → + New**. Fill in:
   - **Name** — e.g. "Dryer for 2 TPH Wood Chips — Acme Forest".
   - **Quote #** — your reference (e.g. `20260812-1`).
   - **Status** — Draft while you work; Published when sent.
   - **Company / Contact / Opportunity** — link them (start typing the name).
   - **Valid Until**, **Purchase Terms** (e.g. "50% down, balance before shipment"),
     **Comments to Buyer** (the cover-letter paragraph), **Prepared By**.
3. Add line items: on the quote, use **Line Items → + New** for each row:
   - **Name** (e.g. "XM-4415 Hammer Mill"), **Description** (the long spec text — every
     line shows on the PDF), **Quantity**, **Unit Price**, optional **Unit Discount** or
     **Discount %**, **Line Total** (leave blank to auto-compute qty × (price − discount)),
     **Line #** (print order), optional **SKU** and **Product** (pick from the imported
     catalog to prefill pricing conventions).
4. Set the quote's **Amount** to the total contract value (the renderer also computes a
   subtotal from the lines; keeping Amount authoritative matches how HubSpot worked).

### Generate the PDF / share a quote
1. Open `http://<server>:8090` — you'll see the list of all quotes.
2. Click the quote to preview the branded web view.
3. Click **PDF** to download the print-ready document (this is what you email).

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
| Start everything | `cd deploy && docker compose -f docker-compose.yml -f docker-compose.renderer.yml up -d` |
| Stop everything | `cd deploy && docker compose -f docker-compose.yml -f docker-compose.renderer.yml down` |
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
4. Disk full → old backups: `du -sh /var/backups/mce-crm`, prune with `find ... -delete`
   (see `backup.sh`), or grow the server volume in the Hetzner console.

## Project history

- `docs/phase0-decision-memo.md` — hosting/quoting decisions (signed off)
- `docs/phase2-field-mapping.md` — HubSpot → Twenty field mapping (signed off)
- `docs/phase3-migration-report.md` — migration results: all counts match, idempotent
- `docs/examples/` — MCE's example quotes (the renderer's source of truth) + a rendered sample
- `docs/hetzner-checklist.md` — production server provisioning steps
- `migration/` — all migration/import scripts (safe to re-run; never duplicate)
- `renderer/` — the quote renderer service

---

## Re-issue a quote offline (no Twenty needed)

When you need a revised copy of a quote that lives in HubSpot/Twenty but only a few
lines change, describe the quote in a JSON file (see `docs/quotes/` for an example)
and render it with the same branded template the server uses:

```bash
python renderer/render_local.py docs/quotes/my-quote.json out/my-quote.pdf
```

This writes the PDF plus a `.html` preview next to it. Dollar amounts in the JSON are
plain dollars; the line total is `quantity × (unit price − discount)`.
