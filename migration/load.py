#!/usr/bin/env python3
"""Load transformed data (data/transformed/*.json) into Twenty. Idempotent:
records are matched on hubspotId — existing records are updated, never duplicated.

Usage:
  load.py --dry-run     # print what would be created/updated, write nothing
  load.py               # full load
  load.py --purge-demo  # first delete records that have no hubspotId (Twenty seed data)

Order: companies -> people -> opportunities -> notes(+targets) -> tasks(+targets).
"""
import json
import pathlib
import sys
import time
from collections import defaultdict

from twenty_client import gql, login, TwentyError

ROOT = pathlib.Path(__file__).resolve().parent.parent
T = ROOT / "data" / "transformed"
BATCH = 30

PLURAL = {"company": "companies", "person": "people", "opportunity": "opportunities",
          "note": "notes", "task": "tasks", "noteTarget": "noteTargets", "taskTarget": "taskTargets"}
CREATE = {"company": "createCompanies", "person": "createPeople", "opportunity": "createOpportunities",
          "note": "createNotes", "task": "createTasks", "noteTarget": "createNoteTargets",
          "taskTarget": "createTaskTargets"}
UPDATE = {"company": "updateCompany", "person": "updatePerson", "opportunity": "updateOpportunity",
          "note": "updateNote", "task": "updateTask"}
INPUT_T = {"company": "CompanyCreateInput", "person": "PersonCreateInput",
           "opportunity": "OpportunityCreateInput", "note": "NoteCreateInput",
           "task": "TaskCreateInput", "noteTarget": "NoteTargetCreateInput",
           "taskTarget": "TaskTargetCreateInput"}
UPDATE_INPUT_T = {"company": "CompanyUpdateInput", "person": "PersonUpdateInput",
                  "opportunity": "OpportunityUpdateInput", "note": "NoteUpdateInput",
                  "task": "TaskUpdateInput"}

report = {"created": defaultdict(int), "updated": defaultdict(int),
          "failed": defaultdict(list), "skipped": defaultdict(int)}


def fetch_existing(tok, obj, extra_fields="hubspotId"):
    """Return {hubspotId: twentyId} for all records of obj that have hubspotId."""
    plural = PLURAL[obj]
    out, cursor = {}, None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = (f"query {{ {plural}(first: 200{after}) {{ edges {{ cursor node {{ id {extra_fields} }} }} "
             f"pageInfo {{ hasNextPage }} }} }}")
        d = gql(q, token=tok)["data"][plural]
        for e in d["edges"]:
            n = e["node"]
            if n.get("hubspotId"):
                out[n["hubspotId"]] = n["id"]
            cursor = e["cursor"]
        if not d["pageInfo"]["hasNextPage"]:
            break
    return out


def purge_demo(tok):
    """Delete records with empty hubspotId (Twenty's seed data) from core objects."""
    for obj in ("opportunity", "person", "company", "note", "task"):
        plural = PLURAL[obj]
        d = gql(f"query {{ {plural}(first: 200) {{ edges {{ node {{ id hubspotId }} }} }} }}",
                token=tok)["data"][plural]
        ids = [e["node"]["id"] for e in d["edges"] if not e["node"].get("hubspotId")]
        for i in ids:
            gql(f'mutation {{ delete{obj[0].upper() + obj[1:]}(id: "{i}") {{ id }} }}', token=tok)
        if ids:
            print(f"purged {len(ids)} demo {plural}")


def create_batch(tok, obj, records):
    """createMany with per-record fallback; returns {hubspotId: id}."""
    made = {}
    mut = (f"mutation Create($data: [{INPUT_T[obj]}!]!) "
           f"{{ {CREATE[obj]}(data: $data) {{ id hubspotId }} }}")
    for i in range(0, len(records), BATCH):
        chunk = records[i:i + BATCH]
        try:
            d = gql(mut, {"data": chunk}, token=tok)["data"][CREATE[obj]]
            for n in d:
                made[n["hubspotId"]] = n["id"]
                report["created"][obj] += 1
        except TwentyError:
            for rec in chunk:  # isolate failures one by one
                try:
                    d = gql(mut, {"data": [rec]}, token=tok)["data"][CREATE[obj]]
                    made[d[0]["hubspotId"]] = d[0]["id"]
                    report["created"][obj] += 1
                except TwentyError as e2:
                    report["failed"][obj].append({"hubspotId": rec.get("hubspotId"), "error": str(e2)[:300]})
        time.sleep(0.05)
    return made


def update_one(tok, obj, twenty_id, rec):
    mut = (f"mutation Upd($id: UUID!, $data: {UPDATE_INPUT_T[obj]}!) "
           f"{{ {UPDATE[obj]}(id: $id, data: $data) {{ id }} }}")
    try:
        gql(mut, {"id": twenty_id, "data": rec}, token=tok)
        report["updated"][obj] += 1
    except TwentyError as e:
        report["failed"][obj].append({"hubspotId": rec.get("hubspotId"), "error": str(e)[:300]})


def load_object(tok, obj, records, dry):
    existing = fetch_existing(tok, obj)
    to_create = [r for r in records if r["hubspotId"] not in existing]
    to_update = [(existing[r["hubspotId"]], r) for r in records if r["hubspotId"] in existing]
    print(f"{obj}: {len(to_create)} to create, {len(to_update)} existing (will update)")
    if dry:
        return existing
    made = create_batch(tok, obj, to_create)
    for tid, rec in to_update:
        update_one(tok, obj, tid, rec)
    existing.update(made)
    return existing


def create_targets(tok, kind, parent_field, rows_, dry):
    """kind: noteTarget/taskTarget; rows_: list of {parent_field: id, personId/companyId/opportunityId: id}"""
    if dry:
        print(f"{kind}: {len(rows_)} links would be created")
        return
    mut = (f"mutation Create($data: [{INPUT_T[kind]}!]!) "
           f"{{ {CREATE[kind]}(data: $data) {{ id }} }}")
    for i in range(0, len(rows_), BATCH):
        chunk = rows_[i:i + BATCH]
        try:
            gql(mut, {"data": chunk}, token=tok)
            report["created"][kind] += len(chunk)
        except TwentyError:
            for rec in chunk:
                try:
                    gql(mut, {"data": [rec]}, token=tok)
                    report["created"][kind] += 1
                except TwentyError as e2:
                    report["failed"][kind].append({"rec": rec, "error": str(e2)[:300]})
        time.sleep(0.05)


def main():
    dry = "--dry-run" in sys.argv
    tok = login()
    if "--purge-demo" in sys.argv and not dry:
        purge_demo(tok)

    data = {n: json.loads((T / f"{n}.json").read_text())
            for n in ("companies", "people", "opportunities", "notes", "tasks")}

    def strip_private(rec):
        return {k: v for k, v in rec.items() if not k.startswith("_")}

    comp_ids = load_object(tok, "company", [strip_private(r) for r in data["companies"].values()], dry)

    ppl = []
    for r in data["people"].values():
        rec = strip_private(r)
        cid = comp_ids.get(r.get("_companyHubspotId", ""))
        if cid:
            rec["companyId"] = cid
        ppl.append(rec)
    ppl_ids = load_object(tok, "person", ppl, dry)

    opps = []
    for r in data["opportunities"].values():
        rec = strip_private(r)
        cid = comp_ids.get(r.get("_companyHubspotId", ""))
        pid = ppl_ids.get(r.get("_contactHubspotId", ""))
        if cid:
            rec["companyId"] = cid
        if pid:
            rec["pointOfContactId"] = pid
        opps.append(rec)
    opp_ids = load_object(tok, "opportunity", opps, dry)

    # notes + targets
    note_ids = load_object(tok, "note", [strip_private(r) for r in data["notes"].values()], dry)
    existing_nt = set() if dry else {
        (e["noteId"], e.get("personId"), e.get("companyId"), e.get("opportunityId"))
        for e in fetch_targets(tok, "noteTarget", "noteId")}
    nt = []
    for hid, r in data["notes"].items():
        nid = note_ids.get(hid)
        t = r.get("_targets", {})
        if not nid:
            continue
        for key, idmap, field in (("person", ppl_ids, "personId"), ("company", comp_ids, "companyId"),
                                  ("opportunity", opp_ids, "opportunityId")):
            target = idmap.get(t.get(key) or "")
            if target:
                row = {"noteId": nid, field: target}
                sig = (nid, row.get("personId"), row.get("companyId"), row.get("opportunityId"))
                if sig not in existing_nt:
                    nt.append(row)
    create_targets(tok, "noteTarget", "noteId", nt, dry)

    task_ids = load_object(tok, "task", [strip_private(r) for r in data["tasks"].values()], dry)
    existing_tt = set() if dry else {
        (e["taskId"], e.get("personId"), e.get("companyId"), e.get("opportunityId"))
        for e in fetch_targets(tok, "taskTarget", "taskId")}
    tt = []
    for hid, r in data["tasks"].items():
        tid = task_ids.get(hid)
        t = r.get("_targets", {})
        if not tid:
            continue
        for key, idmap, field in (("person", ppl_ids, "personId"), ("company", comp_ids, "companyId"),
                                  ("opportunity", opp_ids, "opportunityId")):
            target = idmap.get(t.get(key) or "")
            if target:
                row = {"taskId": tid, field: target}
                sig = (tid, row.get("personId"), row.get("companyId"), row.get("opportunityId"))
                if sig not in existing_tt:
                    tt.append(row)
    create_targets(tok, "taskTarget", "taskId", tt, dry)

    out = {k: dict(v) if isinstance(v, defaultdict) else v for k, v in report.items()}
    out["failed"] = {k: v for k, v in report["failed"].items()}
    (ROOT / "data" / "load_report.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"created": out["created"], "updated": out["updated"],
                      "failed": {k: len(v) for k, v in out["failed"].items()}}, indent=2))


def fetch_targets(tok, kind, parent_field):
    plural = PLURAL[kind]
    out, cursor = [], None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = (f"query {{ {plural}(first: 200{after}) {{ edges {{ cursor node "
             f"{{ id {parent_field} personId companyId opportunityId }} }} pageInfo {{ hasNextPage }} }} }}")
        d = gql(q, token=tok)["data"][plural]
        for e in d["edges"]:
            out.append(e["node"])
            cursor = e["cursor"]
        if not d["pageInfo"]["hasNextPage"]:
            break
    return out


if __name__ == "__main__":
    main()
