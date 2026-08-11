#!/usr/bin/env python3
"""Transform extracted HubSpot data (data/*.jsonl + data/assoc/*.tsv) into
Twenty-ready payloads (data/transformed/*.json) and print a dry-run report.

No network access: pure local transform. Nothing is written to Twenty here.
"""
import html
import json
import pathlib
import re
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "transformed"
OUT.mkdir(exist_ok=True)

OWNERS = {
    "49361534": "DEAR_DATA", "78127584": "DEB_CROSS", "81555982": "RON_DOMINGUEZ",
    "82250130": "SAMMY_PATE", "84507451": "MAGDA_BAPTISTA", "86508278": "MIKE_BUCKSKIN",
    "86696556": "LORAND_WILKINSON", "86999308": "JASON_BLISS", "90945055": "PAULA_SALAZAR",
    "94465638": "KAITLYN_ARRINGTON", "365281024": "ROSS_JAMISON",
    "513084931": "JASON_SHIPLEY", "704272141": "TERRY_GESCHWENTNER",
}

STAGES = {
    "appointmentscheduled": "APPOINTMENT_SCHEDULED", "qualifiedtobuy": "QUALIFIED",
    "presentationscheduled": "FIRST_PRESENTATION", "decisionmakerboughtin": "DECISION_MAKER_BOUGHT_IN",
    "contractsent": "CONTRACT_SENT", "closedwon": "CLOSED_WON", "closedlost": "CLOSED_LOST",
}

LIFECYCLE = {
    "subscriber": "SUBSCRIBER", "lead": "LEAD", "marketingqualifiedlead": "MARKETING_QUALIFIED_LEAD",
    "salesqualifiedlead": "SALES_QUALIFIED_LEAD", "opportunity": "OPPORTUNITY",
    "customer": "CUSTOMER", "evangelist": "EVANGELIST", "other": "OTHER",
}

TASK_STATUS = {"COMPLETED": "DONE", "NOT_STARTED": "TODO", "IN_PROGRESS": "IN_PROGRESS",
               "WAITING": "TODO", "DEFERRED": "TODO"}


def rows(name):
    p = DATA / f"{name}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines()]


def tsv(name):
    p = DATA / "assoc" / f"{name}.tsv"
    if not p.exists():
        return []
    lines = p.read_text().splitlines()
    return [ln.split("\t") for ln in lines[1:] if ln.strip()]


def clean_id(v):
    return None if not v or v == "Unassigned" else v


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>|</p>|</div>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace(" ", " ")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def norm_phone(raw):
    """Return (number, callingCode, countryCode) or None if unparseable."""
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", raw)
    plus = digits.startswith("+")
    digits = digits.lstrip("+")
    if len(digits) == 10 and not plus:
        return (digits, "+1", "US")
    if len(digits) == 11 and digits.startswith("1"):
        return (digits[1:], "+1", "US")
    # Anything else (international or malformed): don't guess a calling code.
    return None


def money(v):
    try:
        return {"amountMicros": int(round(float(v) * 1_000_000)), "currencyCode": "USD"}
    except (TypeError, ValueError):
        return None


report = defaultdict(Counter)
unmapped = defaultdict(list)

# ---------------- companies ----------------
companies = {}
for r in rows("company"):
    hid = r["hs_object_id"]
    domain = r.get("domain") or (re.sub(r"^https?://(www\.)?", "", r.get("website", "")).rstrip("/") if r.get("website") else None)
    rec = {
        "name": r.get("name") or domain or f"(unnamed company {hid})",
        "hubspotId": hid,
        "sourceCreatedAt": r.get("createdate_iso"),
    }
    if domain:
        rec["domainName"] = {"primaryLinkUrl": f"https://{domain}"}
    addr = {k: v for k, v in {
        "addressStreet1": r.get("address"), "addressStreet2": r.get("address2"),
        "addressCity": r.get("city"), "addressState": r.get("state"),
        "addressPostcode": r.get("zip"), "addressCountry": r.get("country"),
    }.items() if v}
    if addr:
        rec["address"] = addr
    if r.get("numberofemployees"):
        try:
            rec["employees"] = int(float(r["numberofemployees"]))
        except ValueError:
            pass
    if r.get("linkedin_company_page"):
        rec["linkedinLink"] = {"primaryLinkUrl": r["linkedin_company_page"]}
    if money(r.get("annualrevenue")):
        rec["annualRevenue"] = money(r.get("annualrevenue"))
    ph = norm_phone(r.get("phone"))
    if ph:
        rec["phone"] = {"primaryPhoneNumber": ph[0], "primaryPhoneCallingCode": ph[1]}
    elif r.get("phone"):
        unmapped["company_phone_unparsed"].append({"company": hid, "value": r["phone"]})
    if r.get("description"):
        rec["companyDescription"] = r["description"][:5000]
    if r.get("industry"):
        rec["industry"] = r["industry"]
    if r.get("lifecyclestage") in LIFECYCLE:
        rec["lifecycleStage"] = LIFECYCLE[r["lifecyclestage"]]
    if OWNERS.get(r.get("hubspot_owner_id", "")):
        rec["hubspotOwner"] = OWNERS[r["hubspot_owner_id"]]
    companies[hid] = rec
    for f in ("name", "domain", "phone", "city", "industry", "lifecyclestage", "hubspot_owner_id"):
        if r.get(f):
            report["company_coverage"][f] += 1
seen_domains = {}
for hid, rec in companies.items():
    url = rec.get("domainName", {}).get("primaryLinkUrl")
    if not url:
        continue
    url = url.lower()
    rec["domainName"]["primaryLinkUrl"] = url
    if url in seen_domains:
        del rec["domainName"]
        unmapped["duplicate_domain_dropped"].append({"company": hid, "domain": url,
                                                     "kept_on": seen_domains[url]})
    else:
        seen_domains[url] = hid
report["counts"]["companies"] = len(companies)

# ---------------- people ----------------
contact_company = {c: comp for c, comp in ((clean_id(a), clean_id(b)) for a, b in tsv("contact_company")) if c and comp}
people = {}
for r in rows("contact"):
    hid = r["hs_object_id"]
    first, last = r.get("firstname", ""), r.get("lastname", "")
    if not first and not last:
        # fall back to the email/local part HubSpot displays, never invent a name
        full = r.get("hs_full_name_or_email", "")
        first = full or f"(no name {hid})"
    rec = {
        "name": {"firstName": first[:255], "lastName": last[:255]},
        "hubspotId": hid,
        "sourceCreatedAt": r.get("createdate_iso"),
    }
    if r.get("email"):
        rec["emails"] = {"primaryEmail": r["email"]}
    phones = {}
    for raw in (r.get("phone"), r.get("mobilephone")):
        ph = norm_phone(raw)
        if ph is None:
            if raw:
                unmapped["person_phone_unparsed"].append({"person": hid, "value": raw})
            continue
        if "primaryPhoneNumber" not in phones:
            phones.update({"primaryPhoneNumber": ph[0], "primaryPhoneCallingCode": ph[1]})
        else:
            phones["additionalPhones"] = [{"number": ph[0], "callingCode": ph[1]}]
    if phones:
        rec["phones"] = phones
    if r.get("jobtitle"):
        rec["jobTitle"] = r["jobtitle"][:255]
    if r.get("city"):
        rec["city"] = r["city"][:255]
    if r.get("lifecyclestage") in LIFECYCLE:
        rec["lifecycleStage"] = LIFECYCLE[r["lifecyclestage"]]
    if r.get("hs_lead_status"):
        rec["leadStatus"] = r["hs_lead_status"]
    if r.get("hydrophos_contact_affiliation"):
        rec["affiliation"] = r["hydrophos_contact_affiliation"].upper()
    if OWNERS.get(r.get("hubspot_owner_id", "")):
        rec["hubspotOwner"] = OWNERS[r["hubspot_owner_id"]]
    if contact_company.get(hid):
        rec["_companyHubspotId"] = contact_company[hid]
    people[hid] = rec
    for f in ("email", "phone", "jobtitle", "city", "lifecyclestage", "hs_lead_status", "hubspot_owner_id"):
        if r.get(f):
            report["person_coverage"][f] += 1
report["counts"]["people"] = len(people)
report["counts"]["people_with_company"] = sum(1 for p in people.values() if "_companyHubspotId" in p)

# ---------------- opportunities ----------------
deal_company, deal_contacts = {}, defaultdict(list)
for d, comp, cont in tsv("deal_assoc"):
    d, comp, cont = clean_id(d), clean_id(comp), clean_id(cont)
    if d and comp and d not in deal_company:
        deal_company[d] = comp
    if d and cont and cont not in deal_contacts[d]:
        deal_contacts[d].append(cont)

opportunities = {}
for r in rows("deal"):
    hid = r["hs_object_id"]
    stage_raw = r.get("dealstage", "")
    if stage_raw not in STAGES:
        unmapped["deals_bad_stage"].append(hid)
        continue
    rec = {
        "name": r.get("dealname") or f"(unnamed deal {hid})",
        "stage": STAGES[stage_raw],
        "hubspotId": hid,
        "sourceCreatedAt": r.get("createdate_iso"),
    }
    if money(r.get("amount")):
        rec["amount"] = money(r.get("amount"))
    if r.get("closedate_iso"):
        rec["closeDate"] = r["closedate_iso"]
    elif r.get("closedate"):
        rec["closeDate"] = r["closedate"]
    if r.get("description"):
        rec["oppDescription"] = r["description"][:5000]
    if OWNERS.get(r.get("hubspot_owner_id", "")):
        rec["hubspotOwner"] = OWNERS[r["hubspot_owner_id"]]
    if deal_company.get(hid):
        rec["_companyHubspotId"] = deal_company[hid]
    if deal_contacts.get(hid):
        rec["_contactHubspotId"] = deal_contacts[hid][0]
    for f in ("closed_won_reason", "closed_lost_reason", "dealtype"):
        if r.get(f):
            unmapped[f].append({"deal": hid, "value": r[f]})
    opportunities[hid] = rec
    report["deal_stages"][STAGES[stage_raw]] += 1
    if r.get("hubspot_owner_id") in OWNERS:
        report["deal_owners"][OWNERS[r["hubspot_owner_id"]]] += 1
    else:
        report["deal_owners"]["(no owner)"] += 1
report["counts"]["opportunities"] = len(opportunities)
report["counts"]["opps_with_company"] = sum(1 for o in opportunities.values() if "_companyHubspotId" in o)
report["counts"]["opps_with_contact"] = sum(1 for o in opportunities.values() if "_contactHubspotId" in o)

# ---------------- notes (incl. calls) ----------------
def collect_targets(assoc_name, deal_name):
    out = defaultdict(lambda: {"person": [], "company": [], "opportunity": []})
    for eng, cont, comp in tsv(assoc_name):
        t = out[eng]
        c1, c2 = clean_id(cont), clean_id(comp)
        if c1 and c1 not in t["person"]:
            t["person"].append(c1)
        if c2 and c2 not in t["company"]:
            t["company"].append(c2)
    for eng, d in tsv(deal_name):
        d = clean_id(d)
        if d and d not in out[eng]["opportunity"]:
            out[eng]["opportunity"].append(d)
    return out

note_targets = collect_targets("note_assoc", "note_deal")
call_targets = collect_targets("call_assoc", "call_deal")

notes = {}
for r in rows("note"):
    hid = r["hs_object_id"]
    body = strip_html(r.get("hs_note_body", ""))
    date = (r.get("hs_timestamp_iso") or r.get("hs_createdate_iso") or "")[:10]
    title = (body.splitlines()[0][:60] if body else "Note") or "Note"
    notes[hid] = {
        "title": title,
        "bodyV2": {"markdown": f"*(HubSpot note, {date})*\n\n{body}"},
        "hubspotId": hid,
        "_targets": note_targets.get(hid, {}),
    }
for r in rows("call"):
    hid = r["hs_object_id"]
    body = strip_html(r.get("hs_call_body", ""))
    date = (r.get("hs_timestamp_iso") or r.get("hs_createdate_iso") or "")[:10]
    title = r.get("hs_call_title") or "Call"
    parts = [f"*(HubSpot logged call, {date}"]
    if r.get("hs_call_direction"):
        parts.append(f", {r['hs_call_direction'].lower()}")
    header = "".join(parts) + ")*"
    notes[hid] = {
        "title": f"Call: {title}"[:255] if not title.lower().startswith("call") else title[:255],
        "bodyV2": {"markdown": f"{header}\n\n{body}" if body else header},
        "hubspotId": hid,
        "_targets": call_targets.get(hid, {}),
    }
report["counts"]["notes_from_notes"] = len(rows("note"))
report["counts"]["notes_from_calls"] = len(rows("call"))

# ---------------- tasks ----------------
task_targets = collect_targets("task_assoc", "task_deal")

tasks = {}
for r in rows("task"):
    hid = r["hs_object_id"]
    body = strip_html(r.get("hs_task_body", ""))
    rec = {
        "title": (r.get("hs_task_subject") or "Task")[:255],
        "hubspotId": hid,
        "_targets": task_targets.get(hid, {}),
    }
    if body:
        rec["bodyV2"] = {"markdown": body}
    if r.get("hs_task_status"):
        rec["status"] = TASK_STATUS.get(r["hs_task_status"], "TODO")
    if r.get("hs_timestamp_iso"):
        rec["dueAt"] = r["hs_timestamp_iso"]
    tasks[hid] = rec
    report["task_status"][rec.get("status", "(none)")] += 1
report["counts"]["tasks"] = len(tasks)

# ---------------- write ----------------
for name, obj in [("companies", companies), ("people", people), ("opportunities", opportunities),
                  ("notes", notes), ("tasks", tasks)]:
    (OUT / f"{name}.json").write_text(json.dumps(obj, indent=1))

(OUT / "unmapped.json").write_text(json.dumps(unmapped, indent=1))

print(json.dumps({k: dict(v) for k, v in report.items()}, indent=2))
print("\nunmapped/special:", {k: len(v) for k, v in unmapped.items()})
