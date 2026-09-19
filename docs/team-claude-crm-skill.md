# MCE CRM (Twenty) — Quoting Skill for Team Claude

(Copy-paste block for team Claude; replace PASTE-API-KEY-HERE with a key from
Twenty Settings → APIs. Full version delivered in chat 2026-09-25; keep in sync.)

- API: http://62.238.116.55:3000/graphql, Authorization: Bearer <key>
- Objects: quotes (status DRAFT/PUBLISHED/ACCEPTED/DECLINED/EXPIRED, qboEstimateId),
  quoteLineItems (lineNumber print order, amountMicros = $ x 1e6), products (236 catalog),
  companies/people/opportunities (hubspotId on all).
- Rules: Claude-created quotes stay DRAFT; prices from catalog or flagged, never invented;
  QBO estimate only for human-ACCEPTED quotes without qboEstimateId, then write id back.
- PDF renderer: http://62.238.116.55:8090
