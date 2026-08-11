#!/usr/bin/env python3
"""Import HubSpot products, historical quotes, and quote line items into Twenty.

Idempotent via hubspotId. Line items are imported only for pairs present in
data/assoc/line_item_assoc.tsv (the rest arrive when the HubSpot daily quota
allows finishing that extraction; re-running this script picks them up).
"""
import json
import pathlib
import time
from collections import defaultdict

from twenty_client import gql, login, TwentyError

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BATCH = 30

OWNERS = {
    "49361534": "DEAR_DATA", "78127584": "DEB_CROSS", "81555982": "RON_DOMINGUEZ",
    "82250130": "SAMMY_PATE", "84507451": "MAGDA_BAPTISTA", "86508278": "MIKE_BUCKSKIN",
    "86696556": "LORAND_WILKINSON", "86999308": "JASON_BLISS", "90945055": "PAULA_SALAZAR",
    "94465638": "KAITLYN_ARRINGTON", "365281024": "ROSS_JAMISON",
    "513084931": "JASON_SHIPLEY", "704272141": "TERRY_GESCHWENTNER",
}
STATUS = {"DRAFT": "DRAFT", "APPROVAL_NOT_NEEDED": "PUBLISHED", "PENDING_APPROVAL": "PUBLISHED",
          "APPROVED": "PUBLISHED", "REJECTED": "DECLINED"}

report = {"created": defaultdict(int), "updated": defaultdict(int), "failed": defaultdict(list)}


def rows(name):
    p = DATA / f"{name}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def tsv(name):
    p = DATA / "assoc" / f"{name}.tsv"
    if not p.exists():
        return []
    return [ln.split("\t") for ln in p.read_text().splitlines()[1:] if ln.strip()]


def clean(v):
    return None if not v or v == "Unassigned" else v


def money(v):
    try:
        return {"amountMicros": int(round(float(v) * 1_000_000)), "currencyCode": "USD"}
    except (TypeError, ValueError):
        return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_ids(tok, plural):
    out, cursor = {}, None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        d = gql(f"query {{ {plural}(first: 200{after}) {{ edges {{ cursor node {{ id hubspotId }} }} "
                f"pageInfo {{ hasNextPage }} }} }}", token=tok)["data"][plural]
        for e in d["edges"]:
            if e["node"].get("hubspotId"):
                out[e["node"]["hubspotId"]] = e["node"]["id"]
            cursor = e["cursor"]
        if not d["pageInfo"]["hasNextPage"]:
            break
    return out


def upsert(tok, singular, plural, create_name, input_t, update_name, update_t, records):
    existing = fetch_ids(tok, plural)
    to_create = [r for r in records if r["hubspotId"] not in existing]
    to_update = [(existing[r["hubspotId"]], r) for r in records if r["hubspotId"] in existing]
    print(f"{singular}: {len(to_create)} to create, {len(to_update)} to update")
    mut = f"mutation C($data: [{input_t}!]!) {{ {create_name}(data: $data) {{ id hubspotId }} }}"
    for i in range(0, len(to_create), BATCH):
        chunk = to_create[i:i + BATCH]
        try:
            d = gql(mut, {"data": chunk}, token=tok)["data"][create_name]
            for n in d:
                existing[n["hubspotId"]] = n["id"]
                report["created"][singular] += 1
        except TwentyError:
            for rec in chunk:
                try:
                    d = gql(mut, {"data": [rec]}, token=tok)["data"][create_name]
                    existing[d[0]["hubspotId"]] = d[0]["id"]
                    report["created"][singular] += 1
                except TwentyError as e2:
                    report["failed"][singular].append({"hubspotId": rec["hubspotId"], "error": str(e2)[:250]})
        time.sleep(0.05)
    umut = f"mutation U($id: UUID!, $data: {update_t}!) {{ {update_name}(id: $id, data: $data) {{ id }} }}"
    for tid, rec in to_update:
        try:
            gql(umut, {"id": tid, "data": rec}, token=tok)
            report["updated"][singular] += 1
        except TwentyError as e:
            report["failed"][singular].append({"hubspotId": rec["hubspotId"], "error": str(e)[:250]})
    return existing


def main():
    tok = login()

    # ---- products ----
    prods = []
    for r in rows("product"):
        rec = {"name": (r.get("name") or f"(product {r['hs_object_id']})")[:255],
               "hubspotId": r["hs_object_id"]}
        if r.get("hs_sku"):
            rec["sku"] = r["hs_sku"]
        if r.get("description"):
            rec["productDescription"] = r["description"][:5000]
        if money(r.get("price")):
            rec["price"] = money(r.get("price"))
        if money(r.get("hs_cost_of_goods_sold")):
            rec["cost"] = money(r.get("hs_cost_of_goods_sold"))
        prods.append(rec)
    prod_ids = upsert(tok, "product", "products", "createProducts", "ProductCreateInput",
                      "updateProduct", "ProductUpdateInput", prods)

    # ---- id maps for relations ----
    opp_ids = fetch_ids(tok, "opportunities")
    comp_ids = fetch_ids(tok, "companies")
    ppl_ids = fetch_ids(tok, "people")

    quote_deal, quote_contact = {}, {}
    for q, d, c in tsv("quote_assoc"):
        q, d, c = clean(q), clean(d), clean(c)
        if q and d and q not in quote_deal:
            quote_deal[q] = d
        if q and c and q not in quote_contact:
            quote_contact[q] = c
    quote_comp = {clean(q): clean(c) for q, c in tsv("quote_company") if clean(q) and clean(c)}

    # ---- quotes ----
    quotes = []
    for r in rows("quote"):
        hid = r["hs_object_id"]
        rec = {"name": (r.get("hs_title") or f"Quote {hid}")[:255], "hubspotId": hid,
               "sourceCreatedAt": r.get("hs_createdate_iso")}
        if r.get("hs_quote_number"):
            rec["quoteNumber"] = r["hs_quote_number"]
        rec["status"] = STATUS.get(r.get("hs_status", ""), "DRAFT")
        if money(r.get("hs_quote_amount")):
            rec["amount"] = money(r.get("hs_quote_amount"))
        if r.get("hs_expiration_date_iso"):
            rec["expirationDate"] = r["hs_expiration_date_iso"]
        if r.get("hs_terms"):
            rec["terms"] = r["hs_terms"][:10000]
        if r.get("hs_comments"):
            rec["comments"] = r["hs_comments"][:10000]
        if OWNERS.get(r.get("hubspot_owner_id", "")):
            rec["preparedBy"] = OWNERS[r["hubspot_owner_id"]]
        oid = opp_ids.get(quote_deal.get(hid, ""))
        cid = comp_ids.get(quote_comp.get(hid, ""))
        pid = ppl_ids.get(quote_contact.get(hid, ""))
        if oid:
            rec["opportunityId"] = oid
        if cid:
            rec["companyId"] = cid
        if pid:
            rec["contactId"] = pid
        quotes.append(rec)
    quote_ids = upsert(tok, "quote", "quotes", "createQuotes", "QuoteCreateInput",
                       "updateQuote", "QuoteUpdateInput", quotes)

    # ---- line items (only pairs we have) ----
    li_quote = {}
    for li, q, d in tsv("line_item_assoc"):
        li, q = clean(li), clean(q)
        if li and q:
            li_quote[li] = q
    li_rows = {r["hs_object_id"]: r for r in rows("line_item")}
    # line order: creation order within each quote
    by_quote = defaultdict(list)
    for li, q in li_quote.items():
        if li in li_rows:
            by_quote[q].append(li)
    items = []
    for q, lis in by_quote.items():
        qid = quote_ids.get(q)
        if not qid:
            continue
        lis.sort(key=lambda x: li_rows[x].get("createdate", ""))
        for n, li in enumerate(lis, 1):
            r = li_rows[li]
            rec = {"name": (r.get("name") or "Item")[:255], "hubspotId": li,
                   "quoteId": qid, "lineNumber": n}
            if r.get("description"):
                rec["itemDescription"] = r["description"][:10000]
            if num(r.get("quantity")) is not None:
                rec["quantity"] = num(r.get("quantity"))
            if money(r.get("price")):
                rec["unitPrice"] = money(r.get("price"))
            if money(r.get("discount")):
                rec["unitDiscount"] = money(r.get("discount"))
            if num(r.get("hs_discount_percentage")) is not None:
                rec["discountPercent"] = num(r.get("hs_discount_percentage"))
            if money(r.get("amount")):
                rec["amount"] = money(r.get("amount"))
            if r.get("hs_sku"):
                rec["sku"] = r["hs_sku"]
            items.append(rec)
    upsert(tok, "quoteLineItem", "quoteLineItems", "createQuoteLineItems", "QuoteLineItemCreateInput",
           "updateQuoteLineItem", "QuoteLineItemUpdateInput", items)

    (DATA / "quote_import_report.json").write_text(json.dumps(
        {k: dict(v) if isinstance(v, defaultdict) else v for k, v in report.items()}, indent=2, default=str))
    print(json.dumps({"created": dict(report["created"]), "updated": dict(report["updated"]),
                      "failed": {k: len(v) for k, v in report["failed"].items()}}, indent=2))


if __name__ == "__main__":
    main()
