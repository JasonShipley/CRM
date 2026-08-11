#!/usr/bin/env python3
"""Set up the approved MCE schema in Twenty (Phase 2 mapping, signed off).

- Replaces Opportunity.stage options with MCE's 7 HubSpot pipeline stages.
- Creates custom fields on company/person/opportunity/note/task.

Idempotent: safe to re-run; existing fields are left alone.
"""
import json

from twenty_client import gql, login

# The 13 HubSpot owners, discovered live (Phase 2). value -> label
OWNERS = [
    ("JASON_SHIPLEY", "Jason Shipley"),
    ("RON_DOMINGUEZ", "Ron Dominguez"),
    ("MIKE_BUCKSKIN", "Mike Buckskin"),
    ("JASON_BLISS", "Jason Bliss"),
    ("PAULA_SALAZAR", "Paula Salazar"),
    ("KAITLYN_ARRINGTON", "Kaitlyn Arrington"),
    ("DEAR_DATA", "Dear Data"),
    ("DEB_CROSS", "Deb Cross"),
    ("SAMMY_PATE", "Sammy Pate"),
    ("MAGDA_BAPTISTA", "Magda Baptista"),
    ("LORAND_WILKINSON", "Lorand Wilkinson"),
    ("ROSS_JAMISON", "Ross Jamison"),
    ("TERRY_GESCHWENTNER", "Terry Geschwentner"),
]

# HubSpot's actual dealstage enum -> Twenty stage options (order preserved)
STAGES = [
    ("APPOINTMENT_SCHEDULED", "Appointment Scheduled", "blue"),
    ("QUALIFIED", "Qualified / Presentation Scheduled", "purple"),
    ("FIRST_PRESENTATION", "First Presentation", "sky"),
    ("DECISION_MAKER_BOUGHT_IN", "Decision Maker Bought-In", "turquoise"),
    ("CONTRACT_SENT", "Contract Sent", "yellow"),
    ("CLOSED_WON", "Closed Won", "green"),
    ("CLOSED_LOST", "Closed Lost", "red"),
]

# HubSpot lifecyclestage enum (standard, discovered via get_properties)
LIFECYCLE = [
    ("SUBSCRIBER", "Subscriber", "gray"),
    ("LEAD", "Lead", "blue"),
    ("MARKETING_QUALIFIED_LEAD", "Marketing Qualified Lead", "sky"),
    ("SALES_QUALIFIED_LEAD", "Sales Qualified Lead", "turquoise"),
    ("OPPORTUNITY", "Opportunity", "purple"),
    ("CUSTOMER", "Customer", "green"),
    ("EVANGELIST", "Evangelist", "pink"),
    ("OTHER", "Other", "yellow"),
]

# HubSpot hs_lead_status enum (standard, discovered via get_properties)
LEAD_STATUS = [
    ("NEW", "New", "blue"),
    ("OPEN", "Open", "sky"),
    ("IN_PROGRESS", "In Progress", "turquoise"),
    ("OPEN_DEAL", "Open Deal", "purple"),
    ("UNQUALIFIED", "Unqualified", "gray"),
    ("ATTEMPTED_TO_CONTACT", "Attempted to Contact", "yellow"),
    ("CONNECTED", "Connected", "green"),
    ("BAD_TIMING", "Bad Timing", "orange"),
]

AFFILIATION = [("HYDROPHOS", "Hydrophos", "sky"), ("MCE", "MCE", "orange")]

COLORS = ["green", "turquoise", "sky", "blue", "purple", "pink", "red", "orange", "yellow", "gray"]


def opts(pairs):
    return [
        {"value": v, "label": l, "color": (c if c else COLORS[i % len(COLORS)]), "position": i}
        for i, (v, l, *cx) in enumerate(pairs)
        for c in [cx[0] if cx else None]
    ]


FIELDS = {
    "company": [
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT",
         "description": "Source record ID from HubSpot (migration idempotency key)"},
        {"name": "sourceCreatedAt", "label": "HubSpot Created", "type": "DATE_TIME",
         "description": "Original create date in HubSpot"},
        {"name": "hubspotOwner", "label": "HubSpot Owner", "type": "SELECT", "options": opts(OWNERS)},
        {"name": "phone", "label": "Phone", "type": "PHONES"},
        {"name": "companyDescription", "label": "Description", "type": "TEXT"},
        {"name": "industry", "label": "Industry", "type": "TEXT"},
        {"name": "lifecycleStage", "label": "Lifecycle Stage", "type": "SELECT", "options": opts(LIFECYCLE)},
        {"name": "employees", "label": "Employees", "type": "NUMBER"},
    ],
    "person": [
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT",
         "description": "Source record ID from HubSpot (migration idempotency key)"},
        {"name": "sourceCreatedAt", "label": "HubSpot Created", "type": "DATE_TIME",
         "description": "Original create date in HubSpot"},
        {"name": "hubspotOwner", "label": "HubSpot Owner", "type": "SELECT", "options": opts(OWNERS)},
        {"name": "lifecycleStage", "label": "Lifecycle Stage", "type": "SELECT", "options": opts(LIFECYCLE)},
        {"name": "leadStatus", "label": "Lead Status", "type": "SELECT", "options": opts(LEAD_STATUS)},
        {"name": "affiliation", "label": "Affiliation", "type": "SELECT", "options": opts(AFFILIATION)},
        {"name": "city", "label": "City", "type": "TEXT"},
    ],
    "opportunity": [
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT",
         "description": "Source record ID from HubSpot (migration idempotency key)"},
        {"name": "sourceCreatedAt", "label": "HubSpot Created", "type": "DATE_TIME",
         "description": "Original create date in HubSpot"},
        {"name": "hubspotOwner", "label": "HubSpot Owner", "type": "SELECT", "options": opts(OWNERS)},
        {"name": "oppDescription", "label": "Description", "type": "TEXT"},
    ],
    "note": [
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT"},
    ],
    "task": [
        {"name": "hubspotId", "label": "HubSpot ID", "type": "TEXT"},
    ],
}


def main():
    tok = login()

    d = gql(
        "query { objects(paging: {first: 100}) { edges { node { id nameSingular "
        "fieldsList { id name type options } } } } }",
        token=tok, endpoint="/metadata",
    )["data"]
    objects = {e["node"]["nameSingular"]: e["node"] for e in d["objects"]["edges"]}

    # 1) Replace Opportunity stage options (only if not already MCE's stages)
    opp = objects["opportunity"]
    stage = next(f for f in opp["fieldsList"] if f["name"] == "stage")
    current_values = [o["value"] for o in (stage["options"] or [])]
    wanted_values = [v for v, _, _ in STAGES]
    if current_values != wanted_values:
        gql(
            "mutation UpdateStage($id: UUID!, $update: UpdateFieldInput!) "
            "{ updateOneField(input: {id: $id, update: $update}) { id options } }",
            {"id": stage["id"],
             "update": {"options": opts(STAGES), "defaultValue": "'APPOINTMENT_SCHEDULED'"}},
            token=tok, endpoint="/metadata",
        )
        print("stage options replaced:", ", ".join(l for _, l, _ in STAGES))
    else:
        print("stage options already set")

    # 2) Create custom fields (skip existing)
    for obj_name, fields in FIELDS.items():
        obj = objects[obj_name]
        existing = {f["name"] for f in obj["fieldsList"]}
        for spec in fields:
            if spec["name"] in existing:
                print(f"{obj_name}.{spec['name']} exists, skipping")
                continue
            field_input = {
                "objectMetadataId": obj["id"],
                "name": spec["name"],
                "label": spec["label"],
                "type": spec["type"],
            }
            if "options" in spec:
                field_input["options"] = spec["options"]
            if "description" in spec:
                field_input["description"] = spec["description"]
            gql(
                "mutation CreateField($input: CreateOneFieldMetadataInput!) "
                "{ createOneField(input: $input) { id name } }",
                {"input": {"field": field_input}},
                token=tok, endpoint="/metadata",
            )
            print(f"created {obj_name}.{spec['name']} ({spec['type']})")

    print("schema setup complete")


if __name__ == "__main__":
    main()
