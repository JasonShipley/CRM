#!/usr/bin/env python3
"""Ingest a persisted HubSpot MCP query result file into data/<object>.jsonl.

Usage: ingest_page.py <object> <result-file> [--tsv]

Plain SELECT results contain {"results": [{"content": "<json-record>"}, ...]};
cross-object (association) queries return one TSV dataset instead (--tsv).
Dedupes by hs_object_id (or full row for TSV), so re-ingesting is safe.
HubSpot HTML-entity-encodes text values; we decode them here.
"""
import html
import json
import pathlib
import re
import sys

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)


def decode(v):
    return html.unescape(v) if isinstance(v, str) else v


def main():
    obj, path = sys.argv[1], sys.argv[2]
    is_tsv = "--tsv" in sys.argv
    raw = pathlib.Path(path).read_text()

    # Persisted MCP files may wrap payload as [{"type":"text","text":"..."}]
    try:
        outer = json.loads(raw)
    except json.JSONDecodeError:
        outer = None
    if isinstance(outer, list) and outer and "text" in outer[0]:
        payload = json.loads(outer[0]["text"])
    elif isinstance(outer, dict):
        payload = outer
    else:
        payload = json.loads(raw)

    out = DATA / f"{obj}.jsonl"
    seen = set()
    if out.exists():
        for line in out.read_text().splitlines():
            rec = json.loads(line)
            seen.add(rec.get("hs_object_id") or json.dumps(rec, sort_keys=True))

    added = dup = 0
    with out.open("a") as fh:
        if is_tsv:
            content = payload["results"][0]["content"]
            m = re.search(r"Dataset TSV:\n(.*)", content, re.S)
            body = m.group(1) if m else content
            lines = [ln for ln in body.splitlines() if ln.strip()]
            header = lines[0].split("\t")
            for ln in lines[1:]:
                if ln.startswith("Showing "):
                    continue
                cells = ln.split("\t")
                rec = {"_tsv_header": header, "_cells": cells}
                key = json.dumps(rec, sort_keys=True)
                if key in seen:
                    dup += 1
                    continue
                seen.add(key)
                fh.write(json.dumps(rec) + "\n")
                added += 1
        else:
            for item in payload["results"]:
                rec = json.loads(item["content"])["properties"]
                rec = {k: decode(v) for k, v in rec.items()}
                key = rec.get("hs_object_id")
                if key in seen:
                    dup += 1
                    continue
                seen.add(key)
                fh.write(json.dumps(rec) + "\n")
                added += 1

    total = sum(1 for _ in out.open())
    inst = payload.get("instructions", "")
    m = re.search(r"of (\d+) total", inst)
    print(f"{obj}: +{added} ({dup} dup) -> {total} rows"
          + (f" (source total {m.group(1)})" if m else ""))


if __name__ == "__main__":
    main()
