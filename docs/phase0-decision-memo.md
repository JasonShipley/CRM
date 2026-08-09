# Phase 0 Decision Memo — MCE CRM Migration (HubSpot → Twenty)

**To:** Jason Shipley, Midwest Custom Engineering
**Date:** 2026-08-09
**Status:** ⛔ GATE — awaiting sign-off. Nothing has been provisioned and nothing in HubSpot has been touched (HubSpot is read-only throughout this project).

This memo covers the two decisions left open: **where Twenty runs** and **how quoting works**. My recommendation on each is listed first. No money is spent until you sign off.

---

## Decision 1 — Hosting

### Option A (recommended): Self-host with Docker Compose on a small VPS

Twenty is open source and free to self-host. The stack is four containers (Twenty server, background worker, PostgreSQL, Redis) managed by one `docker-compose.yml`, which fits comfortably on a ~2 vCPU / 4 GB RAM VPS.

| Cost item | Amount |
|---|---|
| Twenty license | $0 (open source) |
| VPS (e.g. Hetzner ~$9/mo, DigitalOcean ~$24/mo for 4 GB) | **~$10–24/mo flat**, regardless of user count |
| Domain/TLS | ~$12/yr if MCE doesn't already own a domain; TLS is free (Let's Encrypt) |

**Why I recommend it:**
- **Full data ownership.** Your CRM data sits in a Postgres database you control, with nightly dump backups you can copy anywhere.
- **The quote renderer needs API/infra access.** The companion quote-PDF service (Decision 2) runs as one more container on the same box — simplest possible topology, no second host to pay for.
- **Flat cost.** At $9/user/mo, Twenty Cloud costs more than the VPS as soon as ~2 people use the CRM. MCE's sales/ops group is well past that.

**The honest downside:** someone has to own a server. Mitigations, all included in this project: containers auto-restart on reboot, nightly automated Postgres backups, and a Phase 6 runbook written so a non-developer can start/stop/update the app and restore a backup. Realistic ongoing effort is minutes per month.

An always-on machine at MCE's shop is a $0/mo variant, but I'd advise against it: office machines get rebooted/unplugged, and remote access for the sales team requires network setup a VPS gives you for free.

### Option B (fallback): Twenty Cloud (managed)

$9/user/mo (Pro) or $19/user/mo (Organization w/ SSO), per twenty.com/pricing as of Aug 2026. For 5–8 seats that's **$45–160/mo**. Zero server maintenance and the same core product. Two real drawbacks for MCE:

1. **Cost scales with seats** and exceeds the VPS immediately.
2. **The quote renderer still needs somewhere to run.** Cloud gives API access but no box, so we'd rent a small host anyway — at which point it can just run all of Twenty.

Choose B only if MCE firmly does not want any server, even one wrapped in a runbook.

> **Practical note:** the build environment I'm working in is ephemeral, so Phase 1 means: I build and validate the full compose stack here, and the production instance goes onto the VPS you approve (or a machine you designate). I will not provision any paid VPS myself — after sign-off you either hand me access to one, or I hand you a 5-minute provisioning checklist and take it from there. Also noted: my environment's proxy blocks twenty.com directly, so I'll verify all setup commands against the official docs inside the github.com/twentyhq/twenty repository (which is reachable) rather than from memory.

---

## Decision 2 — Quoting

### Option A (recommended): Quote object in Twenty + companion renderer (+ optional QBO Estimate push)

- **Quote lives in the CRM** as a native Twenty custom object linked to the Opportunity, Company, and Contact — quote #, status, line items (part / description / qty / unit price / discount / line total), subtotal, tax, freight, total, valid-until, terms, prepared-by. Sales never leaves the CRM to quote, and every deal shows its quote history.
- **A small renderer service** (runs beside Twenty in the same compose file) pulls a quote by ID via Twenty's GraphQL API and produces a **branded PDF plus a shareable web view** matching MCE's example quotes exactly — the HubSpot-quality output you have today.
- **Optional (Phase 5): on "Accepted," auto-create a matching QuickBooks Online Estimate** and write the QBO id back onto the quote, so Kaitlyn never re-keys line items. I verified this environment already has a **connected QuickBooks connector that supports estimate creation**, so this costs nothing extra and needs no OAuth build. I recommend turning Phase 5 **on**.

### Option B: Quote directly in QuickBooks Online

QBO Estimates work, but: sales leaves the CRM for every quote (and MCE's deal/quote linkage lives nowhere), QBO's estimate templates give far less design control than a custom renderer (you'd lose the branded look of your current quotes), and deal-stage automation can't see quote status. Reasonable only if minimizing custom software outweighs all of that.

### Option C: QBO-only (no quote in CRM at all)

Cheapest to build, weakest result — the CRM can't answer "what did we quote this customer, when, at what margin," which is the heart of the parts-reorder business. Not recommended.

**Trade-off summary**

| | A: Twenty object + renderer | B: Quote in QBO | C: QBO-only |
|---|---|---|---|
| Sales stays in CRM | ✅ | ❌ | ❌ |
| Branded doc matches current quotes | ✅ (pixel control) | ⚠️ template-limited | ⚠️ |
| Accounting re-keying | ✅ none (w/ Phase 5) | ✅ none | ✅ none |
| Quote history on the deal | ✅ | ❌ | ❌ |
| Build effort | Moderate (the one custom piece of this project) | Low | Lowest |

---

## What I need from you to proceed

1. **Hosting:** Option A (self-host VPS, ~$10–24/mo) — approve, or choose B.
2. **Quoting:** Option A (Twenty quote object + renderer) — approve, or choose B/C.
3. **Phase 5 (QBO Estimate push on accept):** recommend **yes** — approve or defer.
4. **Example quote PDFs:** none were attached yet. Please attach 1–2 recent MCE quotes — they are the source of truth for the renderer's layout and branding. Without them I'll build the quote object and a draft layout, but won't finalize branding.
5. **VPS specifics** (only if 1A approved): provider preference and billing owner, or tell me to send you the provisioning checklist.

Nothing is built, provisioned, or spent until this gate clears. HubSpot remains untouched and read-only at every phase.
