#!/usr/bin/env python3
"""MCE quote builder, bundled — every calculator and the pricing basis, offline.

This is the command line the quote-builder skill runs inside a chat. It is the
same code quotes.usemce.com runs (copied in by renderer/skill/build_skill.py),
so a quote sized here and one sized on the server agree. Standard library only;
`render` additionally uses Jinja2 when it is installed.

    python mce.py list                         calculators and what they do
    python mce.py fields rotary_cooler         a calculator's inputs
    python mce.py calc rotary_cooler '{"tph": 2, "tin": 250}'
    python mce.py pricing                      the pricing basis
    python mce.py quote @job.json -o quote.json    a draft proposal from a job
    python mce.py render quote.json -o proposal.html
    python mce.py save quote.json              save it on quotes.usemce.com
    python mce.py version

JSON arguments may be literal JSON, @path to a file, or - for stdin.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import types
import urllib.error
import urllib.request

sys.dont_write_bytecode = True      # the skill folder may be read-only
HERE = pathlib.Path(__file__).resolve().parent
LIB = HERE / "mce"
sys.path.insert(0, str(LIB))

SERVER = os.environ.get("MCE_QUOTES_URL", "https://quotes.usemce.com").rstrip("/")


def emit(obj):
    print(json.dumps(obj, indent=1, default=str, ensure_ascii=False))


def fail(message, **extra):
    emit({"error": message, **extra})
    sys.exit(1)


def read_json(arg):
    if arg is None:
        return {}
    try:
        if arg == "-":
            return json.load(sys.stdin)
        if arg.startswith("@"):
            return json.loads(pathlib.Path(arg[1:]).read_text())
        return json.loads(arg)
    except (OSError, ValueError) as e:
        fail(f"Could not read JSON from {arg[:60]!r}: {e}")


def version_info():
    path = HERE.parent / "VERSION"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"commit": "unknown", "built": "unknown"}


# ------------------------------------------------------------- calculators ---

def cmd_list(_):
    import calculators
    emit([{"key": k, "label": c["label"], "what": c.get("blurb", ""),
           "prices": bool(c.get("prices"))}
          for k, c in calculators.CALCULATORS.items()])


def cmd_fields(args):
    import calculators
    calc = calculators.CALCULATORS.get(args.key)
    if not calc:
        fail(f"Unknown calculator {args.key!r}.", known=sorted(calculators.CALCULATORS))
    emit([{k: f.get(k) for k in ("key", "label", "type", "unit", "default", "help",
                                 "options", "showWhen", "advanced") if k in f}
          for f in calc["fields"]])


def cmd_calc(args):
    import calculators
    if args.key not in calculators.CALCULATORS:
        fail(f"Unknown calculator {args.key!r}.", known=sorted(calculators.CALCULATORS))
    result = calculators.run_with_defaults(args.key, read_json(args.inputs))
    emit(result)
    if result.get("error"):
        sys.exit(1)


def cmd_pricing(_):
    from calculators import _pricing_api
    emit(_pricing_api.payload())


# ------------------------------------------------------------------ quotes ---

def job_from(data):
    """A plain dict -> the object quote_from_job.build reads, with every field the
    server's JobRequest has. Unknown keys are refused, not ignored: a misspelt
    field would otherwise silently quote without it."""
    spec = json.loads((LIB / "job_defaults.json").read_text())
    fields, feeder_defaults = spec["fields"], spec["feeder"]
    unknown = sorted(set(data) - set(fields))
    if unknown:
        fail(f"Unknown job field(s): {', '.join(unknown)}.", allowed=sorted(fields))
    feeder_in = data.get("feeder") or {}
    bad = sorted(set(feeder_in) - set(feeder_defaults))
    if bad:
        fail(f"Unknown feeder field(s): {', '.join(bad)}.", allowed=sorted(feeder_defaults))
    problems = (_check(data, spec.get("rules", {}), "")
                + _check(feeder_in, spec.get("feeder_rules", {}), "feeder."))
    if problems:
        fail("The job does not fit the schema: " + " ".join(problems))
    merged = {**fields, **{k: v for k, v in data.items() if k != "feeder"}}
    merged["feeder"] = types.SimpleNamespace(**{**feeder_defaults, **feeder_in})
    return types.SimpleNamespace(**merged)


def _check(values, rules, prefix):
    """The checks pydantic makes on the server: listed values only, and the
    right kind of value. A wrong one is refused, never coerced or guessed."""
    out = []
    for name, v in values.items():
        rule = rules.get(name) or {}
        if v is None:
            if not rule.get("optional", True):
                out.append(f"{prefix}{name} cannot be null.")
            continue
        if "allowed" in rule:
            if v not in rule["allowed"]:
                out.append(f"{prefix}{name} must be one of "
                           f"{', '.join(json.dumps(a) for a in rule['allowed'])}, "
                           f"not {json.dumps(v)}.")
            continue
        kind = rule.get("type")
        good = {"bool": lambda x: isinstance(x, bool),
                "int": lambda x: isinstance(x, int) and not isinstance(x, bool),
                "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
                "str": lambda x: isinstance(x, str),
                "list": lambda x: isinstance(x, list)}.get(kind, lambda x: True)
        if not good(v):
            out.append(f"{prefix}{name} must be a {kind}, not {json.dumps(v)}.")
    return out


def summary(quote):
    import quotes_store
    t = quotes_store.totals(quote)
    return {"lines": [{"name": l.get("name"), "quantity": l.get("quantity"),
                       "unitPrice": l.get("unitPrice"),
                       "needsPrice": bool(l.get("needsPrice"))}
                      for l in quote.get("lines") or []],
            "totals": t}


def cmd_quote(args):
    import quote_from_job
    data = read_json(args.job)
    job = job_from(data)
    today = None
    if args.today:
        try:
            today = datetime.date.fromisoformat(args.today)
        except ValueError:
            fail("--today must be YYYY-MM-DD.")
    quote = quote_from_job.build(job, today=today, delivery_weeks=args.delivery_weeks)
    if args.text:
        quote["sourceRequest"] = args.text
    if args.output:
        pathlib.Path(args.output).write_text(json.dumps(quote, indent=1, default=str))
    emit({"saved_to": args.output, "summary": summary(quote),
          "openItems": quote.get("openItems"), "quote": None if args.output else quote})


def load_quote(path):
    data = read_json("@" + path if not path.startswith("@") else path)
    return data.get("quote", data) if isinstance(data, dict) else data


def cmd_render(args):
    try:
        import jinja2
    except ImportError:
        fail("Jinja2 is not installed here, so the proposal page cannot be drawn. "
             "pip install jinja2, or save the quote to quotes.usemce.com for its PDF.")
    import render_ctx
    quote = load_quote(args.quote)
    if not quote.get("quoteNumber"):
        quote["quoteNumber"] = datetime.date.today().strftime("%Y%m%d") + "-LOCAL"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(LIB / "templates")),
                             autoescape=jinja2.select_autoescape(["html"]))
    html = env.get_template("quote.html").render(**render_ctx.from_store(quote))
    pathlib.Path(args.output).write_text(html)
    emit({"written": args.output, "bytes": len(html),
          "note": "Draft proposal page. Open it in a browser and print to PDF, or "
                  "save the quote to quotes.usemce.com for the house PDF."})


def cmd_save(args):
    token = args.token or os.environ.get("MCE_QUOTES_TOKEN")
    if not token:
        fail("No token. Pass --token mceq_... or set MCE_QUOTES_TOKEN. Each person "
             "issues their own: POST /api/tokens/request with their @usemce.com "
             "email, then /api/tokens/confirm with the code they are emailed.")
    quote = load_quote(args.quote)
    url = f"{SERVER}/api/quotes" + (f"/{args.id}" if args.id else "")
    req = urllib.request.Request(
        url, data=json.dumps(quote, default=str).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            reply = json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        fail(f"quotes.usemce.com refused the save (HTTP {e.code}).", detail=body)
    except (urllib.error.URLError, OSError) as e:
        fail(f"Could not reach {SERVER}: {getattr(e, 'reason', e)}. This chat's "
             "network may not allow it — the domain has to be on the allowed list "
             "for code execution. The quote is still good locally.")
    for k in ("url", "pdfUrl", "editUrl"):
        if reply.get(k, "").startswith("/"):
            reply[k] = SERVER + reply[k]
    emit(reply)


def cmd_version(_):
    emit({**version_info(), "server": SERVER})


def main(argv=None):
    p = argparse.ArgumentParser(prog="mce.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("fields"); s.add_argument("key"); s.set_defaults(fn=cmd_fields)
    s = sub.add_parser("calc"); s.add_argument("key"); s.add_argument("inputs", nargs="?")
    s.set_defaults(fn=cmd_calc)
    sub.add_parser("pricing").set_defaults(fn=cmd_pricing)
    s = sub.add_parser("quote"); s.add_argument("job")
    s.add_argument("-o", "--output"); s.add_argument("--today")
    s.add_argument("--delivery-weeks"); s.add_argument("--text",
                                                       help="the request as written")
    s.set_defaults(fn=cmd_quote)
    s = sub.add_parser("render"); s.add_argument("quote")
    s.add_argument("-o", "--output", default="proposal.html"); s.set_defaults(fn=cmd_render)
    s = sub.add_parser("save"); s.add_argument("quote")
    s.add_argument("--token"); s.add_argument("--id", help="update this saved quote")
    s.set_defaults(fn=cmd_save)
    sub.add_parser("version").set_defaults(fn=cmd_version)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
