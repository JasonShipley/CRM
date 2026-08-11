#!/usr/bin/env python3
"""Phase 5 helper: sync accepted quotes to QuickBooks Online estimates.

Usage:
  accepted_quotes.py --list                 JSON of quotes with status ACCEPTED
                                            and no qboEstimateId yet (incl. line items)
  accepted_quotes.py --mark <quoteId> <qboEstimateId>
                                            write the QBO estimate id back to the quote

The QBO estimate itself is created through the QuickBooks connector by the
operator agent (see README runbook, "Accepted quote -> QuickBooks estimate").
"""
import json
import sys

from twenty_client import gql, login


def main():
    tok = login()
    if "--list" in sys.argv:
        d = gql("""query { quotes(filter: {status: {eq: "ACCEPTED"}}, first: 100) { edges { node {
            id name quoteNumber qboEstimateId amount { amountMicros }
            company { name } contact { name { firstName lastName } emails { primaryEmail } }
            lineItems { edges { node { name itemDescription quantity lineNumber sku
              unitPrice { amountMicros } unitDiscount { amountMicros } discountPercent
              amount { amountMicros } } } }
        } } } }""", token=tok)["data"]
        out = []
        for e in d["quotes"]["edges"]:
            n = e["node"]
            if n.get("qboEstimateId"):
                continue
            items = [i["node"] for i in n["lineItems"]["edges"]]
            items.sort(key=lambda x: x.get("lineNumber") or 9999)
            n["lineItems"] = items
            out.append(n)
        print(json.dumps(out, indent=1))
    elif "--mark" in sys.argv:
        i = sys.argv.index("--mark")
        quote_id, qbo_id = sys.argv[i + 1], sys.argv[i + 2]
        gql('mutation M($id: UUID!, $data: QuoteUpdateInput!) { updateQuote(id: $id, data: $data) { id qboEstimateId } }',
            {"id": quote_id, "data": {"qboEstimateId": qbo_id}}, token=tok)
        print(f"marked {quote_id} -> QBO estimate {qbo_id}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
