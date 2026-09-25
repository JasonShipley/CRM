#!/usr/bin/env python3
"""The JSON fallback path in interpret.py, without touching the API.

This path exists because structured outputs are not reliable for JobRequest's
schema. It has no API-side guarantee, so it is the only thing between a malformed
reply and a wrong quote — these cases are the proof it is strict enough.

    cd renderer && python3 tests/test_json_fallback.py
"""
import json
import pathlib
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import interpret  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}{': ' + detail if detail else ''}")


def reply(*texts, stop_reason="end_turn"):
    """A stand-in for the SDK's Message, with the block shapes it really returns."""
    blocks = [types.SimpleNamespace(type="text", text=t) for t in texts]
    return types.SimpleNamespace(content=blocks, stop_reason=stop_reason)


GOOD = {
    "customer_company": "Fairview Mills", "customer_contact": "Dennis Heideman",
    "mill_model": "XM-4430", "motor_hp": 200, "product_as_written": "grain ration pet food",
    "product_match": "Pet Food (high fat)", "product_confidence": "unsure",
    "capacity_tph": 15, "capacity_pph": None, "screen_64ths": 6,
    "feeder": {"diameter_in": "10", "cup_type": "ss", "rows": None,
               "magnet_clean": "scmaa", "as_written": 'SS round cup 8-4row 10"'},
    "include_plenum": True, "include_screw": True, "include_air_system": True,
    "include_magnet": False, "air_swept": False, "dust_collection": None,
    "other_items": [], "quantity": 1,
    "ambiguities": ['Feeder rows written as "8-4row" — 8-row or 4-row?'],
}


def main():
    # 1. the plain case
    job = interpret._parse_json_reply(reply(json.dumps(GOOD)))
    check("company read", job.customer_company == "Fairview Mills")
    check("nested feeder read", job.feeder.cup_type == "ss")
    check("null stays null", job.capacity_pph is None)
    check("ambiguity survives", len(job.ambiguities) == 1)

    # 2. a code fence, which models add even when told not to
    for fenced in (f"```json\n{json.dumps(GOOD)}\n```", f"```\n{json.dumps(GOOD)}\n```"):
        job = interpret._parse_json_reply(reply(fenced))
        check("fenced JSON parses", job.customer_company == "Fairview Mills", fenced[:20])

    # 3. prose either side of the object
    job = interpret._parse_json_reply(
        reply("Here is the extraction:\n" + json.dumps(GOOD) + "\nLet me know."))
    check("prose around the object is ignored", job.mill_model == "XM-4430")

    # 4. thinking blocks must not be treated as the reply
    r = reply(json.dumps(GOOD))
    r.content.insert(0, types.SimpleNamespace(type="thinking", thinking="hmm {not json}"))
    job = interpret._parse_json_reply(r)
    check("thinking block skipped", job.customer_company == "Fairview Mills")

    # 5. things that must be refused rather than half-read
    for label, body in [
        ("not JSON at all", "I could not work that out, sorry."),
        ("truncated JSON", '{"customer_company": "Fairview'),
        ("empty reply", ""),
        ("wrong enum", json.dumps({**GOOD, "product_confidence": "definitely"})),
        ("wrong type", json.dumps({**GOOD, "quantity": "several"})),
    ]:
        try:
            interpret._parse_json_reply(reply(body))
            FAILS.append(f"{label}: accepted, should have raised")
        except interpret.InterpretError as e:
            check(f"{label} explains itself",
                  "by hand" in str(e), str(e))

    # 6. a thin request must still come back, with the gaps left as nulls
    thin = {"customer_company": None, "mill_model": "XM-4430",
            "product_confidence": "unsure", "feeder": {}}
    job = interpret._parse_json_reply(reply(json.dumps(thin)))
    check("thin request parses", job.mill_model == "XM-4430")
    check("absent fields default", job.quantity == 1 and job.other_items == [])
    check("absent feeder fields stay null", job.feeder.rows is None)

    if FAILS:
        print(f"{len(FAILS)} FAILURE(S):")
        for f in FAILS:
            print("  " + f)
        return 1
    print("OK — the JSON fallback reads a good reply and refuses a bad one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
