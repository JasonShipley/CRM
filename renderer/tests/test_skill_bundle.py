#!/usr/bin/env python3
"""The downloadable quote-builder skill must answer exactly as the server does.

Builds the zip, unpacks it, and drives its command line under `python -S` — no
site-packages — which proves the bundle runs on a bare interpreter, the way it
will in a chat sandbox. Then holds every answer to the in-repo code:

  * every calculator, at its defaults, returns what calculators.run returns
  * a full quote from a job equals quote_from_job.build on the same job
  * a misspelt job field is refused rather than silently dropped
  * the pricing basis is the server's /api/pricing payload
  * saving to a server it cannot reach fails with a message, not a traceback

    cd renderer && python3 tests/test_skill_bundle.py
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
RENDERER = HERE.parent
sys.path.insert(0, str(RENDERER))
sys.path.insert(0, str(RENDERER / "skill"))

import build_skill  # noqa: E402
import calculators  # noqa: E402
import quote_from_job as qfj  # noqa: E402
from calculators import _pricing_api  # noqa: E402
from interpret import FeederSpec, JobRequest  # noqa: E402

FAILS = []
TODAY = datetime.date(2026, 10, 5)


def check(name, cond, detail=""):
    if not cond:
        FAILS.append(f"{name}: {detail}"[:600])


def same(obj):
    return json.loads(json.dumps(obj, default=str))


JOBS = {
    "fairview venturi filter receiver": dict(
        customer_company="Fairview Mills", customer_contact="Dennis Heideman",
        mill_model="XM-4430", motor_hp=200, product_as_written="grain ration pet food",
        product_match="Pet Food (high fat)", product_confidence="unsure",
        capacity_tph=15, screen_64ths=6,
        feeder=dict(diameter_in="10", cup_type="ss", rows=8, magnet_clean="scmaa",
                    as_written='SS round cup 8-4row 10" auto selfclean feeder'),
        include_air_system=True, air_swept=True, air_pickup="venturi",
        dust_collection="filter_receiver", airlock_fill=0.9, airlock_rpm=12,
        duct_run_ft=60, duct_elbows=4),
    "cyclone, plenum and screw": dict(
        customer_company="Acme Feed", mill_model="XM-4430", motor_hp=200,
        product_as_written="corn", product_match="Corn / Milo",
        product_confidence="stated", capacity_tph=20, screen_64ths=8,
        include_plenum=True, include_screw=True, include_air_system=True,
        dust_collection="cyclone"),
    "thin request": dict(customer_company="Acme Feed", product_as_written="corn"),
}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        zip_path = tmp / "quote-builder.zip"
        build_skill.build(zip_path)
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            z.extractall(tmp)
        root = tmp / "quote-builder"
        check("SKILL.md at the top", "quote-builder/SKILL.md" in names, names[:5])
        check("version stamped into SKILL.md",
              "{{COMMIT}}" not in (root / "SKILL.md").read_text())

        env = {**os.environ, "MCE_QUOTES_URL": "http://127.0.0.1:9"}

        def cli(*args, ok=True):
            r = subprocess.run([sys.executable, "-S", str(root / "scripts" / "mce.py"),
                                *args], capture_output=True, text=True, cwd=tmp,
                               env=env, timeout=120)
            check(f"no traceback from {args[:2]}", "Traceback" not in r.stderr,
                  r.stderr[-400:])
            check(f"exit status of {args[:2]}", (r.returncode == 0) == ok,
                  f"rc={r.returncode} {r.stdout[-300:]}")
            try:
                return json.loads(r.stdout)
            except ValueError:
                FAILS.append(f"{args[:2]} printed no JSON: {r.stdout[:200]}")
                return {}

        listed = {c["key"] for c in cli("list")}
        check("every calculator listed", listed == set(calculators.CALCULATORS),
              listed ^ set(calculators.CALCULATORS))
        for key in calculators.CALCULATORS:
            got = cli("calc", key, "{}")
            want = same(calculators.run_with_defaults(key, {}))
            check(f"calc {key} runs at its defaults", not got.get("error"), got.get("error"))
            check(f"calc {key} matches the repo", got == want,
                  f"{key}: bundle and repo disagree")

        check("pricing matches /api/pricing", cli("pricing") == same(_pricing_api.payload()))

        for name, data in JOBS.items():
            job_file = tmp / "job.json"
            job_file.write_text(json.dumps(data))
            out = tmp / "quote.json"
            cli("quote", f"@{job_file}", "-o", str(out), "--today", TODAY.isoformat(),
                "--delivery-weeks", "10–12")
            fields = {k: v for k, v in data.items() if k != "feeder"}
            job = JobRequest(**fields, feeder=FeederSpec(**data.get("feeder", {})))
            want = same(qfj.build(job, today=TODAY, delivery_weeks="10–12"))
            got = json.loads(out.read_text()) if out.exists() else {}
            check(f"quote '{name}' matches the repo", got == want,
                  f"lines bundle={[l.get('name') for l in got.get('lines', [])]} "
                  f"repo={[l.get('name') for l in want.get('lines', [])]}")

        refused = cli("quote", '{"mill": "XM-4430"}', ok=False)
        check("misspelt field refused", "mill" in refused.get("error", ""), refused)
        wrong = cli("quote", '{"product_confidence": "certain", '
                    '"feeder": {"cup_type": "round"}}', ok=False)
        check("value outside the schema refused, as pydantic would",
              "certain" in wrong.get("error", "") and "round" in wrong.get("error", ""),
              wrong)

        saved = cli("save", str(tmp / "quote.json"), "--token", "mceq_test", ok=False)
        check("unreachable server explained",
              "Could not reach" in saved.get("error", ""), saved)
        no_token = cli("save", str(tmp / "quote.json"), ok=False)
        check("missing token explained", "token" in no_token.get("error", "").lower(),
              no_token)

        try:
            import jinja2  # noqa: F401
        except ImportError:
            jinja2 = None
        if jinja2:
            r = subprocess.run([sys.executable, str(root / "scripts" / "mce.py"),
                                "render", str(tmp / "quote.json"), "-o",
                                str(tmp / "p.html")], capture_output=True, text=True,
                               timeout=120)
            html = (tmp / "p.html").read_text() if (tmp / "p.html").exists() else ""
            check("proposal page renders", "EQUIPMENT PROPOSAL" in html.upper(),
                  r.stderr[-300:])

    if FAILS:
        print(f"skill bundle: {len(FAILS)} problems")
        for f in FAILS:
            print("  " + f)
        sys.exit(1)
    print(f"skill bundle: {len(calculators.CALCULATORS)} calculators and "
          f"{len(JOBS)} quotes match the repo, stdlib-only")


if __name__ == "__main__":
    main()
