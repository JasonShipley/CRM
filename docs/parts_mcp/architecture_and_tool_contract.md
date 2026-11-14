# MCE Parts MCP Server: Architecture and Tool Contract

Status: PROPOSAL, awaiting approval from Jason. No code exists yet.
Prepared 14 Nov 2026.

Items marked DECISION FOR JASON are not decided here. The values shown beside them are placeholders that ship as config defaults only after approval.

# Part 1. Architecture

## 1.1 Shape

One new service, `parts_mcp`, added to the existing Docker Compose stack on the MCE server and published by the existing Caddy proxy with automatic HTTPS.

* Transport: remote MCP over streamable HTTP, one endpoint, stateless (no server side session), JSON responses. Stateless keeps retries safe and lets us add a second instance later with no change.
* Language: Python, matching the rest of this repo, using the official MCP Python SDK.
* Address: a new subdomain beside `crm.usemce.com` and `quotes.usemce.com`. Proposed `parts.usemce.com/mcp`. DECISION FOR JASON: the public address.
* No language model sits in the request path. Every tool is deterministic code over the catalog and the customer record. This is deliberate: it is the strongest defense against prompt injection, it cannot invent a price or a fit, and it costs nothing per call.

## 1.2 Request path

1. Caddy terminates TLS and forwards to `parts_mcp`.
2. Auth layer resolves the bearer credential to exactly one `customer_id` and a set of allowed `supplier_id` values. No tool accepts a customer id as an input; identity only ever comes from the credential.
3. Rate limiter checks the per credential budget.
4. Input validator checks types, lengths, enumerations, and character sets. Free text is length capped, stored as data, and never parsed for meaning.
5. Tier engine classifies the call as Tier A, B, or C using config and the customer record.
6. Handler runs inside one database transaction, writes the audit record, and queues any outbound work in an outbox table.
7. Response serializer builds the reply from an explicit allow list of fields. Cost, margin, supplier identity, and any other customer's data are not in the allow list, so they cannot leak by accident.

## 1.3 Auth

Options considered:

* Option A, per customer API keys sent as a bearer token. Simple, works today with agent runtimes that let the operator set a header, easy to rotate and revoke. Weak point: consumer chat apps that only add connectors through an OAuth sign in cannot use it.
* Option B, OAuth 2.1 with client credentials, as the MCP authorization spec describes. Works with the widest set of agent hosts. Costs an authorization server, token endpoints, and more surface to secure before the first order.

Pick: Option A for Phase 1, behind an `Authenticator` interface so Option B is an added class in Phase 2, not a rewrite. Keys are 32 random bytes, shown once at onboarding, stored only as a SHA 256 hash, scoped to one customer, revocable, with an optional expiry. A customer can hold several keys (one per agent) so one can be revoked alone.

## 1.4 Data stores

Options considered: SQLite file, or a new database on the Postgres instance that already runs for the CRM.

Pick: a separate `parts` database on the existing Postgres instance. It gives real transactions and unique constraints for idempotency, it is already operated and backed up nightly (the backup script gains one line), and it keeps parts data out of the CRM schema.

Tables (every row carries `supplier_id`, `customer_id`, or both, and every query filters on them):

* `suppliers`: id, legal name, display policy (whether the name may be shown to buyers, default no), fulfillment adapter name, adapter config, status.
* `customers`: id, legal name, CRM company id, QuickBooks customer id, approved terms code, autonomy flags, ship to addresses on file, owning teammate.
* `credentials`: id, customer id, key hash, label, created, expires, revoked.
* `parts`: MCE part number (primary key), supplier id, supplier part number, category, description for buyers, unit, sold as (each or set), set size, weight, status.
* `part_cross_refs`: MCE part number, reference type (OEM number, customer number, legacy SKU, pattern record), value.
* `fitments`: MCE part number, mill make, mill model, pattern record id, fit status (verified or unverified), verified by, verified date, source document.
* `price_rules`: supplier id, optional category, formula name, divisor, rounding, effective dates, approved by.
* `part_costs`: MCE part number, supplier id, cost, confirmed date, confirmed by, source, lead time text, lead time confirmed date. Internal only.
* `list_prices`: MCE part number, price, approved by, approved date. For parts sold from a published list rather than cost plus.
* `quotes`, `quote_lines`, `orders`, `order_lines`, `fulfillment_legs`, `shipments`.
* `review_items`: the Tier C queue.
* `idempotency_keys`: credential id, tool, key, request hash, stored response.
* `audit_log`: append only, one row per tool call.
* `outbox`: pending deliveries to the CRM, email, and suppliers.

## 1.5 How it uses the existing parts agent and pipeline

Finding that shapes this: the hammer mill parts agent is a Claude skill that a person or a scheduled session runs. It has no API, so the server cannot call it during a request. The server therefore splits the work:

* What the pipeline does by rule, the server does in code: match a part, check fit against verified records, apply the price rule to a confirmed cost, build the quote, record the PO, route the order.
* What the pipeline does by judgment, the server hands to the agent and its humans through the review queue: unknown patterns, reverse engineer jobs, unconfirmed cost, new customers, anything over a cap. Each review item is written so the parts agent can pick it up at the matching step of its eight step pipeline.

Reuse of existing assets:

* Price rule: `price = cost / divisor`, rounded to cents, per line, exactly as the pipeline states. The divisor lives in `price_rules` per supplier and optional category, never in code.
* Quotes: each server quote is also written to the Twenty CRM as a Quote with Quote Line Items, using the schema and client already in `migration/`. The branded PDF comes from the existing renderer.
* Accounting: when an order is placed the CRM quote moves to Accepted. The existing scheduled sync (`migration/accepted_quotes.py`) then creates the QuickBooks estimate, and accounting raises the invoice as it does today. The server never touches invoices, payments, or credit terms.
* PO routing: an order summary (customer, quote number, PO number, lines, totals, ship to, terms) goes to Mike and Accounting, the same content the pipeline sends at step 8.
* Purchasing: the server never issues a supplier PO. It queues a purchase request for Mike, who submits, as the purchasing rules require.
* Part numbers: the 9 digit scheme (category, series, component) is the internal key. Buyers see the customer facing twin (same digits, leading 2).

Outbound delivery uses a transactional outbox: the order commits first, then workers deliver to the CRM, email, and supplier, with retries. A failed email can never lose or duplicate an order.

## 1.6 Where supplier fulfillment plugs in

A `FulfillmentAdapter` interface with four methods: `submit(leg)`, `status(leg)`, `tracking(leg)`, `cancel(leg)`. An order is split into one fulfillment leg per `supplier_id`.

* Phase 1 ships one adapter, `mce_internal`: email to Mike and Accounting plus a purchasing queue entry. Status and tracking are entered by MCE staff through a small admin command.
* Phase 3 adds `supplier_webhook`: signed POST to the OEM, acceptance and ship confirmation callbacks, SLA timers. Adding an OEM is a `suppliers` row, an adapter config, a catalog load, and price rules.

## 1.7 Autonomy tiers

* Tier A, autonomous: `search_parts`, `get_part`, `get_compatibility`, `get_quote_status`, `get_order_status`, `get_tracking`.
* Tier B, autonomous within limits: `request_quote` when every line is a catalog part with verified fit for the stated mill and a price that is either an approved list price or a rule applied to a confirmed, fresh cost. `place_order` when the customer has approved terms on record, has no past due balance, ships to an address on file, and the order is inside both caps.
* Tier C, human first: new customers, custom or non catalog parts, unconfirmed or stale cost, unverified fit, over cap orders, credit exceptions, new ship to address, disputes, and every `request_human` call. Nothing is priced or promised. A review item is created and the buyer agent is told a human will respond and by when.

Config, all DECISION FOR JASON, defaults intentionally low:

* `per_order_cap_usd`: 1000
* `per_customer_daily_cap_usd`: 2500
* `cost_freshness_days`: 90 (older confirmed cost counts as unconfirmed)
* `quote_valid_days`: 30
* `review_response_business_days`: 1
* `rate_limit_per_minute`: 60 reads, 10 writes, per credential

## 1.8 Tradeoffs accepted

* Deterministic search is less forgiving than a language model. An odd description returns no match and escalates. That is the right failure for rotating equipment.
* API keys first means some chat apps cannot connect until OAuth lands in Phase 2.
* Sharing the CRM Postgres instance ties uptime to that host. Acceptable at Phase 1 volume.
* Status and tracking are entered by MCE staff in Phase 1. Carrier integration is deferred.

## 1.9 Deferred, not built in Phase 1

OAuth 2.1, payment capture, returns and warranty tools, live inventory counts, carrier APIs, buyer webhooks, automated Drive filing, language model assisted search, supplier portal, settlement.

# Part 2. Tool contract

## 2.1 Conventions for every tool

Identity: the caller is the customer bound to the credential. No tool takes a customer identifier.

Result envelope, returned by every tool:

```
{
  "status": "ok" | "needs_human_confirmation" | "error",
  "data": { ... } | null,
  "review": { "review_id", "reason_code", "respond_by", "contact" } | null,
  "error": { "code", "message", "retryable" } | null
}
```

* `ok`: the answer is complete and comes from confirmed data.
* `needs_human_confirmation`: MCE will not answer or act automatically. A review item exists. `review.respond_by` is an ISO 8601 UTC timestamp. `review.contact` is always: Midwest Custom Engineering parts desk, parts@usemce.com, 772 300 9035, midwestcustomengineering.com. The caller should not retry; it should wait or use `get_quote_status` or `get_order_status`.
* `error`: the call was rejected. Nothing was created unless the code says so.

Part numbers shown to buyers are the 9 digit MCE customer facing numbers. Money is a decimal string in USD. Prices never include freight or tax unless a field says so.

Free text fields (`notes`, `description`, `message`) are stored and shown to MCE staff as untrusted customer text. They never change price, fit, terms, limits, or routing, whatever they say.

Idempotency: every write tool requires `idempotency_key`, a caller generated string of 16 to 64 characters from letters, digits, and underscore. Keys are scoped to the credential and the tool and kept 30 days. Same key with the same arguments returns the original result and creates nothing. Same key with different arguments returns `idempotency_conflict`.

Error codes shared by all tools:

* `unauthenticated`: missing, unknown, expired, or revoked credential. Not retryable.
* `forbidden`: the credential may not use this tool or see this record. Also returned for records that belong to another customer, so existence is not revealed. Not retryable.
* `invalid_input`: an argument failed validation. `message` names the field. Not retryable until fixed.
* `not_found`: no such part, quote, or order for this customer. Not retryable.
* `rate_limited`: too many calls. Retryable after the number of seconds in `message`.
* `idempotency_conflict`: key reused with different arguments. Not retryable with that key.
* `internal_error`: MCE side fault. Retryable with the same idempotency key.

## 2.2 search_parts (Tier A, read)

Description shown to agents: Search the Midwest Custom Engineering parts catalog for hammer mill wear parts: hammers, screens, rods and pins, spacers and collars, rotors, and wear liners. Search by MCE part number, by your own or an OEM part number, by mill make and model, or by category and dimensions. Returns catalog parts only. A part appearing in results does not confirm it fits your mill; call get_compatibility before quoting. If nothing matches, do not guess a substitute; call request_human with the mill model and pattern details.

Inputs:

* `query` (string, optional, max 120): part number, cross reference number, or keywords.
* `category` (enum, optional): `hammer`, `screen`, `rod_pin`, `spacer_collar`, `rotor`, `wear_liner`.
* `mill_make` (string, optional, max 40) and `mill_model` (string, optional, max 40).
* `limit` (integer, optional, 1 to 25, default 10) and `cursor` (string, optional).
* At least one of `query`, `category`, or `mill_model` is required.

Output `data`: `parts` (array of `part_number`, `name`, `category`, `summary`, `unit`, `sold_as`, `set_size`, `match_reason`), `next_cursor`.

Errors: shared codes only. An empty result is `ok` with an empty array.

## 2.3 get_part (Tier A, read)

Description shown to agents: Get the full catalog record for one MCE part number: description, dimensions, material and hardfacing, unit of sale, set size for parts sold as balanced sets, known cross references, and the mill models with verified fit. Availability and lead time are returned only when MCE has confirmed them recently; otherwise the field reads needs_human_confirmation. This tool does not return a price; call request_quote.

Inputs: `part_number` (string, required, exactly 9 digits).

Output `data`: `part_number`, `name`, `category`, `description`, `dimensions` (object), `material`, `hardfacing`, `unit`, `sold_as`, `set_size`, `weight_lb`, `cross_references` (array of `type`, `value`), `verified_fitments` (array of `mill_make`, `mill_model`), `availability` (`confirmed` with `lead_time` text and `as_of` date, or `needs_human_confirmation`).

Errors: `not_found`, plus shared codes.

## 2.4 get_compatibility (Tier A, read)

Description shown to agents: Check whether a specific MCE part fits a specific hammer mill, or list the MCE parts with verified fit for a mill. Fit is answered only from records MCE has verified against a drawing, a sample, or a prior order. The answer is one of verified_fit, no_verified_fit, or needs_human_confirmation. There is no partial or probable fit. A wrong part on a hammer mill is a safety and downtime risk, so if the answer is anything other than verified_fit, do not order the part; call request_human.

Inputs:

* `mill_make` (string, required, max 40) and `mill_model` (string, required, max 40).
* `part_number` (string, optional, 9 digits). If omitted, the tool lists parts with verified fit.
* `pattern_id` (string, optional, max 20): an MCE hammer pattern record on file for this customer.
* `category` (enum, optional, same values as search_parts).

Output `data`: `mill_make`, `mill_model`, `results` (array of `part_number`, `name`, `fit` as `verified_fit` or `no_verified_fit`, `verified_on` date, `set_size`, `notes`).

Returns `needs_human_confirmation` when the mill model is unknown to MCE, when the model maps to more than one configuration, or when a pattern on file conflicts with the catalog. A review item is opened in those cases.

Errors: `not_found` (unknown part number), plus shared codes.

## 2.5 request_quote (Tier B, or Tier C by rule; write)

Description shown to agents: Request a price quote for one or more MCE catalog parts for a stated mill. If every line is a catalog part with verified fit for that mill and confirmed pricing, and your account allows it, a firm quote is returned immediately with unit prices, extended prices, lead time, payment terms, and an expiry date. In every other case (new customer, custom or pattern built parts, unconfirmed pricing, unverified fit, partial hammer sets) no price is returned; the request goes to the MCE parts desk and the response tells you when a person will reply. Hammers are quoted in complete balanced sets only. Prices exclude freight and tax unless stated. Requires an idempotency_key; repeating a call with the same key returns the same quote.

Inputs:

* `idempotency_key` (string, required).
* `mill_make`, `mill_model` (strings, required, max 40 each).
* `lines` (array, required, 1 to 50) of `part_number` (9 digits, required) and `quantity` (integer, 1 to 10000, required).
* `custom_request` (object, optional): `description` (string, max 1000), `pattern_id` (string, max 20). Presence of this field always routes to Tier C.
* `need_by` (date, optional). Informational; never changes price or lead time.
* `customer_reference` (string, optional, max 60).
* `notes` (string, optional, max 1000). Untrusted text for MCE staff.

Output `data` when `ok`: `quote_id`, `quote_number`, `state` (`firm`), `lines` (array of `part_number`, `name`, `quantity`, `unit_price`, `extended_price`, `lead_time`), `subtotal`, `freight` (`not_included`), `terms`, `expires_at`, `document_url`.

Output when `needs_human_confirmation`: `data.quote_id`, `data.state` (`under_review`), and `review` with `reason_code` from: `new_customer`, `non_catalog_part`, `cost_unconfirmed`, `fit_unverified`, `partial_set`, `account_review`.

Errors: `invalid_input`, `not_found` (unknown part number), `idempotency_conflict`, plus shared codes.

Idempotency: by key. A repeat returns the stored quote and does not reprice.

## 2.6 get_quote_status (Tier A, read)

Description shown to agents: Get the current state of a quote you requested: under_review, firm, expired, declined, or ordered. For a firm quote, returns the same priced lines as request_quote. For a quote under review, returns when MCE expects to respond. Only quotes that belong to your account are visible.

Inputs: `quote_id` (string, required).

Output `data`: `quote_id`, `quote_number`, `state`, `lines` (priced only when `firm` or `ordered`), `subtotal`, `terms`, `expires_at`, `respond_by` (when `under_review`), `order_id` (when `ordered`).

Errors: `not_found`, plus shared codes.

## 2.7 place_order (Tier B, or Tier C by rule; write)

Description shown to agents: Place an order against a firm, unexpired MCE quote, using your purchase order number. The order covers the whole quote exactly as priced; to change lines or quantities, request a new quote. If your account has approved terms, the order is within your account limits, and the ship to address is one MCE has on file, the order is accepted immediately and routed to MCE purchasing and accounting. Otherwise the order is held for review by a person and the response tells you when to expect an answer; a held order is not yet accepted. This tool does not take payment; MCE invoices under the terms on the quote. Requires an idempotency_key; repeating a call with the same key, or ordering the same quote twice, returns the existing order and never creates a second one.

Inputs:

* `idempotency_key` (string, required).
* `quote_id` (string, required).
* `po_number` (string, required, 1 to 40, letters, digits, space, period, slash, underscore).
* `ship_to_id` (string, required): an address id on file for the account, as returned at onboarding.
* `confirm_total` (decimal string, required): must equal the quote subtotal. Guards against ordering a quote the caller has not read.
* `requested_ship_date` (date, optional). Informational.
* `notes` (string, optional, max 1000). Untrusted text for MCE staff.

Output `data` when `ok`: `order_id`, `order_number`, `state` (`accepted`), `quote_number`, `po_number`, `lines`, `subtotal`, `terms`, `ship_to` (label only), `estimated_ship` (text from quote lead time), `placed_at`.

Output when `needs_human_confirmation`: `data.order_id`, `data.state` (`held_for_review`), and `review` with `reason_code` from: `over_order_cap`, `over_daily_cap`, `terms_not_approved`, `credit_review`, `ship_to_not_on_file`.

Errors:

* `quote_not_firm`: the quote is under review or declined.
* `quote_expired`: request a new quote.
* `total_mismatch`: `confirm_total` does not equal the quote subtotal.
* `duplicate_po_number`: this PO number is already on a different order for the account. Nothing created.
* `invalid_input`, `not_found`, `idempotency_conflict`, plus shared codes.

Idempotency: by key, and by a unique constraint of one order per quote. A second call for an already ordered quote, with any key, returns the existing order with `ok` and a `duplicate_of_existing` flag set true.

## 2.8 get_order_status (Tier A, read)

Description shown to agents: Get the current state of an order on your account by order id or by your purchase order number: held_for_review, accepted, in_production, shipped, delivered, or cancelled, with the dates MCE has recorded. Dates are reported only when recorded by MCE; this tool does not estimate.

Inputs: exactly one of `order_id` (string) or `po_number` (string).

Output `data`: `order_id`, `order_number`, `po_number`, `state`, `lines` (with `quantity_ordered`, `quantity_shipped`), `placed_at`, `accepted_at`, `estimated_ship`, `shipped_at`, `respond_by` (when held).

Errors: `not_found`, plus shared codes.

## 2.9 get_tracking (Tier A, read)

Description shown to agents: Get shipment tracking for an order on your account: carrier, tracking number, ship date, and the lines in each shipment. Returns an empty list if nothing has shipped yet. An order may ship in more than one shipment.

Inputs: `order_id` (string, required).

Output `data`: `order_id`, `shipments` (array of `carrier`, `tracking_number`, `shipped_at`, `lines` with `part_number` and `quantity`).

Errors: `not_found`, plus shared codes.

## 2.10 request_human (Tier C always; write)

Description shown to agents: Ask a person at the Midwest Custom Engineering parts desk to help. Use this for parts not in the catalog, hammers built to a pattern, reverse engineered or obsolete parts, any doubt about fit, changes or cancellations to an order, delivery problems, damaged or incorrect parts, warranty questions, and billing or credit questions. Describe the need in plain text and include the mill make and model if known. The response gives a reference id and the time by which MCE will reply by email or phone. This tool does not change any quote or order by itself. Requires an idempotency_key.

Inputs:

* `idempotency_key` (string, required).
* `topic` (enum, required): `part_identification`, `custom_part`, `fit_question`, `order_change`, `delivery_issue`, `damaged_or_incorrect`, `warranty`, `billing_or_credit`, `other`.
* `message` (string, required, 10 to 2000). Untrusted text for MCE staff.
* `related_quote_id`, `related_order_id` (strings, optional).
* `mill_make`, `mill_model` (strings, optional, max 40).
* `contact_name` (string, optional, max 80), `contact_email` (email, optional), `contact_phone` (string, optional, max 30).

Output: always `needs_human_confirmation` on success, with `review.review_id`, `review.respond_by`, `review.contact`.

Errors: `invalid_input`, `not_found` (related record not on the account), `idempotency_conflict`, plus shared codes.

## 2.11 What a review item contains

So that Jason or the owning teammate can act in one read, each review item holds: reason code and tier rule that fired, customer name and account state (terms, open balance flag, last order), the full request as structured fields, any free text in a clearly marked untrusted block, mill and pattern on file, the matching catalog rows with internal cost state (confirmed date or missing), the pipeline step to resume at, the response deadline, and the owner. Delivered to the parts inbox and stored in `review_items`.
