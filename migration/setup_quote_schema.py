#!/usr/bin/env python3
"""Create the Phase 4 quoting schema in Twenty: Product, Quote, Quote Line Item.

Modeled on MCE's example quotes (docs/examples/) and the HubSpot quote data.
Idempotent: existing objects/fields are left alone.
"""
from setup_schema import OWNERS, opts
from twenty_client import gql, login

STATUS = [
    ("DRAFT", "Draft", "gray"),
    ("PUBLISHED", "Published", "blue"),
    ("ACCEPTED", "Accepted", "green"),
    ("DECLINED", "Declined", "red"),
    ("EXPIRED", "Expired", "orange"),
]

OBJECTS = [
    {"nameSingular": "product", "namePlural": "products",
     "labelSingular": "Product", "labelPlural": "Products",
     "icon": "IconPackage",
     "description": "MCE part/equipment catalog (imported from HubSpot products)"},
    {"nameSingular": "quote", "namePlural": "quotes",
     "labelSingular": "Quote", "labelPlural": "Quotes",
     "icon": "IconFileDollar",
     "description": "Customer quotes with line items; renders to branded PDF"},
    {"nameSingular": "quoteLineItem", "namePlural": "quoteLineItems",
     "labelSingular": "Quote Line Item", "labelPlural": "Quote Line Items",
     "icon": "IconListDetails",
     "description": "Line items belonging to a quote"},
]

FIELDS = {
    "product": [
        {"name": "sku", "label": "SKU", "type": "TEXT"},
        {"name": "productDescription", "label": "Description", "type": "TEXT"},
        {"name": "price", "label": "Price", "type": "CURRENCY"},
        {"name": "cost", "label": "Cost", "type": "CURRENCY"},
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT"},
    ],
    "quote": [
        {"name": "quoteNumber", "label": "Quote #", "type": "TEXT"},
        {"name": "status", "label": "Status", "type": "SELECT", "options": opts(STATUS)},
        {"name": "amount", "label": "Amount", "type": "CURRENCY"},
        {"name": "expirationDate", "label": "Valid Until", "type": "DATE_TIME"},
        {"name": "terms", "label": "Purchase Terms", "type": "TEXT"},
        {"name": "comments", "label": "Comments to Buyer", "type": "TEXT"},
        {"name": "preparedBy", "label": "Prepared By", "type": "SELECT", "options": opts(OWNERS)},
        {"name": "qboEstimateId", "label": "QBO Estimate ID", "type": "TEXT",
         "description": "QuickBooks Online estimate id (set automatically on acceptance)"},
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT"},
        {"name": "sourceCreatedAt", "label": "HubSpot Created", "type": "DATE_TIME"},
    ],
    "quoteLineItem": [
        {"name": "itemDescription", "label": "Description", "type": "TEXT"},
        {"name": "quantity", "label": "Quantity", "type": "NUMBER"},
        {"name": "unitPrice", "label": "Unit Price", "type": "CURRENCY"},
        {"name": "unitDiscount", "label": "Unit Discount", "type": "CURRENCY"},
        {"name": "discountPercent", "label": "Discount %", "type": "NUMBER"},
        {"name": "amount", "label": "Line Total", "type": "CURRENCY"},
        {"name": "sku", "label": "SKU", "type": "TEXT"},
        {"name": "position", "label": "Position", "type": "NUMBER"},
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT"},
    ],
}

# (source object, field name, target object, label on target side, icon)
RELATIONS = [
    ("quote", "opportunity", "opportunity", "Quotes", "IconFileDollar"),
    ("quote", "company", "company", "Quotes", "IconFileDollar"),
    ("quote", "contact", "person", "Quotes", "IconFileDollar"),
    ("quoteLineItem", "quote", "quote", "Line Items", "IconListDetails"),
    ("quoteLineItem", "product", "product", "Line Items", "IconListDetails"),
]


def main():
    tok = login()

    def objects_by_name():
        d = gql("query { objects(paging: {first: 200}) { edges { node { id nameSingular "
                "fieldsList { name } } } } }", token=tok, endpoint="/metadata")["data"]
        return {e["node"]["nameSingular"]: e["node"] for e in d["objects"]["edges"]}

    objs = objects_by_name()
    for spec in OBJECTS:
        if spec["nameSingular"] in objs:
            print(f"object {spec['nameSingular']} exists")
            continue
        gql("mutation C($input: CreateOneObjectInput!) { createOneObject(input: $input) { id } }",
            {"input": {"object": spec}}, token=tok, endpoint="/metadata")
        print(f"created object {spec['nameSingular']}")
    objs = objects_by_name()

    for obj_name, fields in FIELDS.items():
        existing = {f["name"] for f in objs[obj_name]["fieldsList"]}
        for spec in fields:
            if spec["name"] in existing:
                continue
            fi = {"objectMetadataId": objs[obj_name]["id"], **spec}
            gql("mutation C($input: CreateOneFieldMetadataInput!) { createOneField(input: $input) { id } }",
                {"input": {"field": fi}}, token=tok, endpoint="/metadata")
            print(f"created {obj_name}.{spec['name']}")

    objs = objects_by_name()
    for src, fname, target, tlabel, ticon in RELATIONS:
        if fname in {f["name"] for f in objs[src]["fieldsList"]}:
            print(f"relation {src}.{fname} exists")
            continue
        fi = {"objectMetadataId": objs[src]["id"], "name": fname,
              "label": fname[0].upper() + fname[1:], "type": "RELATION",
              "relationCreationPayload": {
                  "targetObjectMetadataId": objs[target]["id"],
                  "targetFieldLabel": tlabel, "targetFieldIcon": ticon,
                  "type": "MANY_TO_ONE"}}
        gql("mutation C($input: CreateOneFieldMetadataInput!) { createOneField(input: $input) { id } }",
            {"input": {"field": fi}}, token=tok, endpoint="/metadata")
        print(f"created relation {src}.{fname} -> {target}")

    print("quote schema complete")


if __name__ == "__main__":
    main()
