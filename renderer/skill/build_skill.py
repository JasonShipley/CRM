#!/usr/bin/env python3
"""Build the downloadable quote-builder skill from this repo.

    python renderer/skill/build_skill.py              -> dist/quote-builder.zip
    python renderer/skill/build_skill.py --out x.zip

The zip carries MCE's calculators, quote assembly and pricing basis — the same
files quotes.usemce.com runs, copied, not rewritten — plus a stdlib-only command
line (mce.py) and reference pages generated from the code. Rebuild it whenever a
calculator, the pricing basis or a vendor basis changes, and re-upload it;
VERSION inside says which commit it was built from.

It is MCE-internal: the vendor cost basis is inside. Share it with the org,
never outside it.
"""
import argparse
import datetime
import io
import json
import pathlib
import subprocess
import sys
import zipfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent
RENDERER = SKILL_DIR.parent
REPO = RENDERER.parent
sys.path.insert(0, str(RENDERER))

NAME = "quote-builder"
# Copied verbatim into scripts/mce/. Anything quote_from_job or render_ctx
# imports at use time has to be here; tests/test_skill_bundle.py proves it by
# running the bundle with site-packages switched off.
COPY = ["quote_from_job.py", "render_ctx.py", "quotes_store.py",
        "templates/quote.html", "assets/mce-logo.png",
        "assets/fonts/oswald.woff2", "assets/fonts/inter.woff2"]


def version():
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=REPO, capture_output=True,
                                  text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    commit = git("rev-parse", "--short", "HEAD") or "unknown"
    dirty = bool(git("status", "--porcelain", "--", "renderer"))
    return {"commit": commit + ("+local-changes" if dirty else ""),
            "built": datetime.date.today().isoformat()}


def job_defaults():
    """Every JobRequest field with its default, allowed values and type, so the
    bundled CLI fills and checks a job the way the server's pydantic model does —
    without pydantic in the chat."""
    from typing import List, Literal, get_args, get_origin

    import interpret

    def describe(model):
        defaults, rules = {}, {}
        for name, f in model.model_fields.items():
            if name == "feeder":
                continue
            defaults[name] = f.default_factory() if f.default_factory else f.default
            ann = f.annotation
            optional = type(None) in get_args(ann)
            args = [a for a in get_args(ann) if a is not type(None)]
            inner = args[0] if (optional and len(args) == 1) else ann
            rule = {"optional": optional}
            if get_origin(inner) is Literal:
                rule["allowed"] = list(get_args(inner))
            elif get_origin(inner) in (list, List):
                rule["type"] = "list"
            else:
                rule["type"] = {bool: "bool", int: "int", float: "number",
                                str: "str"}.get(inner, "any")
            rules[name] = rule
        return defaults, rules

    fields, rules = describe(interpret.JobRequest)
    feeder, feeder_rules = describe(interpret.FeederSpec)
    return {"fields": {**fields, "feeder": None}, "rules": rules,
            "feeder": feeder, "feeder_rules": feeder_rules}


def calculators_md():
    import calculators
    out = ["# MCE calculators",
           "",
           "Run any of these with `python scripts/mce.py calc <key> '<json>'`. Leave out "
           "an input to take its default. `python scripts/mce.py fields <key>` prints "
           "the same list as JSON.", ""]
    for key, c in calculators.CALCULATORS.items():
        out += [f"## `{key}` — {c['label']}", "", c.get("blurb", ""), "",
                "Prices: " + ("yes" if c.get("prices") else "sizes only"), "",
                "| Input | Label | Unit | Default | Notes |", "|---|---|---|---|---|"]
        for f in c["fields"]:
            notes = []
            if f.get("options"):
                notes.append("one of " + ", ".join(
                    f"`{o[0]}` ({o[1]})" if isinstance(o, (list, tuple)) else f"`{o}`"
                    for o in f["options"]))
            if f.get("showWhen"):
                notes.append("only when " + ", ".join(
                    f"{k}={v}" for k, v in f["showWhen"].items()))
            if f.get("help"):
                notes.append(f["help"])
            cell = lambda v: str(v if v is not None else "").replace("|", "\\|").replace("\n", " ")
            out.append(f"| `{f['key']}` | {cell(f.get('label'))} | {cell(f.get('unit'))} | "
                       f"{cell(f.get('default'))} | {cell(' — '.join(notes))} |")
        out.append("")
    return "\n".join(out)


def job_request_md():
    import interpret
    return "\n".join([
        "# Job request — what `mce.py quote` takes",
        "",
        "You are doing the extraction step that the server's `/api/interpret` does "
        "with its own Claude call: read the rep's request and fill these fields. "
        "Then run `python scripts/mce.py quote '<json>'`. Fields you leave out take "
        "their defaults; an unknown field is refused.",
        "",
        "## The extraction rules (verbatim from the server)",
        "",
        interpret.SYSTEM,
        "",
        "## The fields",
        "",
        "```",
        interpret.JSON_INSTRUCTION,
        "```",
        ""])


def build(out_path):
    v = version()
    files = {}
    for path in sorted((RENDERER / "calculators").glob("*.py")):
        files[f"scripts/mce/calculators/{path.name}"] = path.read_bytes()
    for rel in COPY:
        files[f"scripts/mce/{rel}"] = (RENDERER / rel).read_bytes()
    files["scripts/mce.py"] = (SKILL_DIR / "mce.py").read_bytes()
    files["scripts/mce/job_defaults.json"] = json.dumps(job_defaults(), indent=1).encode()
    files["reference/calculators.md"] = calculators_md().encode()
    files["reference/job_request.md"] = job_request_md().encode()
    files["VERSION"] = json.dumps(v).encode()
    skill = (SKILL_DIR / "SKILL.template.md").read_text()
    skill = skill.replace("{{COMMIT}}", v["commit"]).replace("{{BUILT}}", v["built"])
    files["SKILL.md"] = skill.encode()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, data in sorted(files.items()):
            info = zipfile.ZipInfo(f"{NAME}/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if rel.endswith("mce.py") else 0o644) << 16
            z.writestr(info, data)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf.getvalue())
    return v, len(files), out_path.stat().st_size


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=str(REPO / "dist" / f"{NAME}.zip"))
    args = p.parse_args()
    v, n, size = build(pathlib.Path(args.out))
    print(f"{args.out}: {n} files, {size / 1024:.0f} KB, commit {v['commit']}, "
          f"built {v['built']}")


if __name__ == "__main__":
    main()
