#!/usr/bin/env python3
"""Add optional detail fields to the Quote object, for complex engineered
proposals (design basis, furnished-by-others, freight/delivery, options &
adders, a narrative totals breakdown, and a custom draft-banner note).

All fields are plain TEXT, entered by pipe-delimited rows (one row per line,
columns separated by " | "). Blank on a quote means the renderer skips that
section entirely — simple catalog quotes are unaffected.

Standalone (no import of twenty_client, so it runs even on a host where
migration/ wasn't copied) — reads deploy/credentials.local, talks to
http://localhost:3000. Idempotent: safe to re-run.

Run from the deploy checkout root, e.g.:
    cd /opt/mce-crm && python3 add_quote_detail_fields.py
"""
import json
import pathlib
import urllib.error
import urllib.request

BASE = "http://localhost:3000"
REPO = pathlib.Path(__file__).resolve().parent.parent
CREDS = REPO / "deploy" / "credentials.local"

FIELDS = [
    {"name": "designBasis", "label": "Design Basis", "type": "TEXT",
     "description": 'Optional "1. Design Basis" table. One row per line: '
                    "Parameter | Design Value | Notes"},
    {"name": "furnishedByOthers", "label": "Furnished by Others", "type": "TEXT",
     "description": 'Optional "Furnished by Others" bullet list. One item per line.'},
    {"name": "freightDelivery", "label": "Freight, Delivery and Schedule", "type": "TEXT",
     "description": 'Optional table. One row per line: Item | Basis'},
    {"name": "optionsAdders", "label": "Options and Adders", "type": "TEXT",
     "description": 'Optional alternates table (shown after the totals, unnumbered). '
                    "One row per line: Option | Description | Qty | Unit Price | Net Adder"},
    {"name": "totalsBreakdown", "label": "Totals Breakdown", "type": "TEXT",
     "description": "Optional narrative totals (overrides the plain Subtotal/Total block). "
                    "One row per line: Label | Amount. Last row renders as the bold grand total."},
    {"name": "draftNote", "label": "Draft Banner Note", "type": "TEXT",
     "description": 'Optional override for the orange draft banner text on DRAFT quotes '
                    '(default: "Draft — Internal Review").'},
]


def creds():
    d = {}
    for line in CREDS.read_text().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            d[k.strip().lower()] = v.strip()
    return d["email"], d["password"]


def post(endpoint, payload, token=None):
    req = urllib.request.Request(
        BASE + endpoint, data=json.dumps(payload).encode(),
        headers={"content-type": "application/json",
                 **({"authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:800]}")


def gql(query, variables=None, token=None, endpoint="/graphql"):
    out = post(endpoint, {"query": query, "variables": variables or {}}, token)
    if out.get("errors"):
        raise RuntimeError(json.dumps(out["errors"])[:1500])
    return out["data"]


def login():
    email, password = creds()
    d = gql(f'mutation {{ getLoginTokenFromCredentials(email: "{email}", '
            f'password: "{password}", origin: "{BASE}") {{ loginToken {{ token }} }} }}',
            endpoint="/metadata")
    lt = d["getLoginTokenFromCredentials"]["loginToken"]["token"]
    d = gql(f'mutation {{ getAuthTokensFromLoginToken(loginToken: "{lt}", origin: "{BASE}") '
            "{ tokens { accessOrWorkspaceAgnosticToken { token } } } }", endpoint="/metadata")
    return d["getAuthTokensFromLoginToken"]["tokens"]["accessOrWorkspaceAgnosticToken"]["token"]


def main():
    tok = login()
    d = gql('query { objects(paging: {first: 200}) { edges { node { id nameSingular '
            "fieldsList { name } } } } }", token=tok, endpoint="/metadata")
    quote = next(e["node"] for e in d["objects"]["edges"] if e["node"]["nameSingular"] == "quote")
    existing = {f["name"] for f in quote["fieldsList"]}

    for spec in FIELDS:
        if spec["name"] in existing:
            print(f"quote.{spec['name']} exists, skipping")
            continue
        gql("mutation C($input: CreateOneFieldMetadataInput!) "
            "{ createOneField(input: $input) { id name } }",
            {"input": {"field": {"objectMetadataId": quote["id"], **spec}}},
            token=tok, endpoint="/metadata")
        print(f"created quote.{spec['name']} (TEXT)")

    print("done")


if __name__ == "__main__":
    main()
