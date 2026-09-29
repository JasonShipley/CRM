# MCE CRM — rules for any Claude session working here

## Quote-to-cash procedure (never skip steps)

The customer-facing document is always a **Twenty CRM quote rendered to
branded PDF**. A QuickBooks Online estimate is an internal accounting
artifact created only *after* a human has accepted that quote — never a
substitute for it, and never created speculatively.

1. **Price main equipment** from Twenty's `product` catalog (QBO's catalog
   mirrors the same numbers and can be used to cross-check, but Twenty's
   `quote` / `quoteLineItem` objects are the record of what's being offered).
   Never invent a price.
2. **Size ancillary equipment** (motors, feeders, air-balancing components,
   etc.) only via MCE's real sizing calculators. Never estimate or guess a
   size, model, or capacity.
3. **Create the quote in Twenty CRM**: a `quote` record, `Status = DRAFT`,
   linked to the Company/Contact/Opportunity, with one `quoteLineItem` per
   priced item. Anything not yet fully priced or sourced (e.g. a motor whose
   frame isn't confirmed, a feeder still needing a vendor quote) stays out of
   the line items and gets called out in Comments/Terms instead — never a
   placeholder price.
4. **Render the PDF** via the renderer app (`http://<server>:8090/quote/<id>/pdf`)
   and hand it to Jason for review. Do not send it to the customer directly.
5. Jason reviews and sends it (himself, or asks Claude to send via Gmail once
   he's confirmed the content), then sets the quote's `Status = PUBLISHED` in
   Twenty.
6. **Only after the customer accepts** and the quote's `Status` is set to
   `ACCEPTED` in Twenty does the QuickBooks sync run: `migration/accepted_quotes.py
   --list` finds accepted quotes with no `qboEstimateId`, a matching QBO
   estimate is created with the same line items, and the id is written back
   with `migration/accepted_quotes.py --mark <quoteId> <qboEstimateId>`.
7. **Never create, send, or edit a QBO estimate/invoice ahead of that** —
   not as a placeholder, not to "get a number to show," not because Twenty
   is unreachable. If asked to "put together a quote," the deliverable is a
   Twenty quote + PDF. If Twenty CRM can't be reached (see below), say so and
   produce the PDF from the confirmed data directly rather than reaching for
   QuickBooks as a workaround.

See `README.md` for the full operator runbook and `docs/team-claude-crm-skill.md`
for the API/object reference.

## Known gap: Twenty CRM access from this environment

This container has no `TWENTY_EMAIL` / `TWENTY_PASSWORD` (or
`deploy/credentials.local`) and outbound requests to the Twenty CRM host
(`3000`) and renderer (`8090`) time out — so a session here can render a quote
PDF locally from `renderer/templates/quote.html` (same template, same fonts/
logo in `renderer/assets/`) but cannot yet write the Quote record back into
Twenty. Until that's fixed (add the credentials and allow the host in this
environment's network settings), flag any quote you produce as **not yet
recorded in Twenty CRM** and say so explicitly, rather than silently treating
a locally-rendered PDF as the system of record.
