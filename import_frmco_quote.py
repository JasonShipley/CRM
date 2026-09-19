#!/usr/bin/env python3
"""Import Farmers Rice training quote into Twenty CRM.

Run this when the Twenty CRM system is available:
    python3 import_frmco_quote.py

This script will:
1. Find or create the Farmers Rice company
2. Find the Gordon Roberson contact
3. Create the quote with line items
"""
from datetime import datetime, timedelta
from migration.twenty_client import gql, login, TwentyError
import sys

def main():
    try:
        tok = login()
        print("✓ Authenticated with Twenty CRM")
    except Exception as e:
        print(f"✗ Failed to authenticate: {e}")
        print("\nMake sure Twenty CRM is running and credentials are set up.")
        return False

    # Find or create Farmers Rice company
    print("\nLooking for Farmers Rice company...")
    companies = gql("""query {
        companies(filter: {name: {iLike: "%Farmers%"}}, first: 10) {
            edges { node { id name addressCity } }
        }
    }""", token=tok)["data"]["companies"]["edges"]

    company_id = None
    for edge in companies:
        node = edge["node"]
        if "Farmers Rice" in node["name"]:
            company_id = node["id"]
            city = node.get("addressCity", "")
            print(f"  ✓ Found: {node['name']}" + (f" ({city})" if city else ""))
            break

    if not company_id:
        print("  ✗ Farmers Rice not found in CRM")
        print("  Note: Company must be created before importing quote")
        return False

    # Find Gordon Roberson contact
    print("\nLooking for Gordon Roberson contact...")
    people = gql("""query {
        people(filter: {firstName: {eq: "Gordon"}}, first: 20) {
            edges { node { id firstName lastName emails { primaryEmail } } }
        }
    }""", token=tok)["data"]["people"]["edges"]

    contact_id = None
    for edge in people:
        node = edge["node"]
        if node["lastName"] and "Roberson" in node["lastName"]:
            contact_id = node["id"]
            email = (node.get("emails") or {}).get("primaryEmail", "")
            print(f"  ✓ Found: {node['firstName']} {node['lastName']}" + (f" ({email})" if email else ""))
            break

    if not contact_id:
        print("  ✗ Gordon Roberson not found in CRM")
        print("  Note: Contact must be created before importing quote")
        return False

    # Create quote
    print("\nCreating quote...")
    quote_number = f"FRM-{datetime.now().strftime('%Y%m%d')}-JB-TRAIN"
    expiration = (datetime.now() + timedelta(days=30)).isoformat() + "Z"
    total_micros = 7500 * 1_000_000

    quote_mutation = """mutation CreateQuote($input: QuoteCreateInput!) {
        createQuote(input: $input) {
            id quoteNumber status
        }
    }"""

    quote_input = {
        "name": "Farmers Rice - Jason Bliss Training (Lake Charles)",
        "quoteNumber": quote_number,
        "status": "DRAFT",
        "company": {"connect": {"id": company_id}},
        "contact": {"connect": {"id": contact_id}},
        "amount": {"amountMicros": total_micros},
        "expirationDate": expiration,
        "terms": "Net 30",
        "comments": """MCE Field Service Training Trip – Hammer Mill Operations

Location: Farmers Rice Milling Company, Lake Charles, LA

Service Overview:
Jason Bliss will conduct a 2-day training program for the Farmers Rice team on:
- Hammer mill operation and troubleshooting
- Maintenance procedures and safety protocols
- Parts identification and replacement procedures

Duration: 2 business days
Scope: Training only – does not include repair work

Additional Notes:
- Minimum 6 team members recommended for training
- Optional: Additional services for bin feeder replacement available under separate quote
- All training materials will be provided by MCE
- Contact: Jason Shipley (jason@usemce.com) to schedule""",
        "preparedBy": "JASON_SHIPLEY"
    }

    try:
        result = gql(quote_mutation, {"input": quote_input}, token=tok)
        if result.get("errors"):
            print(f"  ✗ Error: {result['errors']}")
            return False

        quote_id = result["data"]["createQuote"]["id"]
        print(f"  ✓ Quote created: {quote_number}")

        # Create line items
        print("\nAdding line items...")
        create_line_items(tok, quote_id)

        print("\n✓ Quote successfully imported into CRM!")
        print(f"  Quote ID: {quote_id}")
        print(f"  Status: DRAFT (ready to review and send)")
        return True

    except TwentyError as e:
        print(f"  ✗ Error creating quote: {e}")
        return False


def create_line_items(tok, quote_id):
    """Create line items for the quote."""

    items = [
        {
            "name": "Training - 2 Days",
            "itemDescription": "On-site training for Farmers Rice team on hammer mill operation, maintenance, and troubleshooting. Instructor: Jason Bliss. Minimum 6 team members recommended.",
            "quantity": 2,
            "unitPrice": {"amountMicros": 2500 * 1_000_000},
            "lineNumber": 1,
            "sku": "TRAIN-2DAY"
        },
        {
            "name": "Travel & Lodging",
            "itemDescription": "Round-trip airfare from Oklahoma to Lake Charles, LA; 2 nights hotel accommodations; meals and ground transportation",
            "quantity": 1,
            "unitPrice": {"amountMicros": 2500 * 1_000_000},
            "lineNumber": 2,
            "sku": "TRAVEL-LC"
        }
    ]

    mutation = """mutation CreateLineItem($input: QuoteLineItemCreateInput!) {
        createQuoteLineItem(input: $input) {
            id name
        }
    }"""

    for item in items:
        item_input = {
            **item,
            "quote": {"connect": {"id": quote_id}}
        }

        try:
            result = gql(mutation, {"input": item_input}, token=tok)
            if result.get("errors"):
                print(f"  ✗ Warning: Could not create '{item['name']}': {result['errors']}")
            else:
                print(f"  ✓ {item['name']}")
        except TwentyError as e:
            print(f"  ✗ Warning: {e}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
