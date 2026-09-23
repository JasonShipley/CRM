"""Extract JS literal tables from the MCE calculator HTML into Python source.

Run once to generate renderer/calculators/_data.py. Extraction beats hand-copying
32 mill rows, 50 cooler models and four screw-conveyor tables.
"""
import json, pathlib, pprint, re, sys

TOOLS = pathlib.Path("/home/user/CRM/renderer/tools")


def js_body(src, name):
    """Text of the `const <name> = ...;` literal, brackets balanced."""
    m = re.search(r"const\s+" + re.escape(name) + r"\s*=\s*", src)
    if not m:
        raise SystemExit(f"not found: {name}")
    i = m.end()
    open_ch = src[i]
    close_ch = {"[": "]", "{": "}"}[open_ch]
    depth, j, in_str, esc = 0, i, None, False
    while j < len(src):
        c = src[j]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == in_str: in_str = None
        # Comments first: a lone quote inside one (e.g. `15" HMI`) would
        # otherwise put the scanner into string mode and run past the literal.
        elif c == "/" and src[j + 1:j + 2] == "/":
            j = src.find("\n", j)
            if j < 0: break
        elif c == "/" and src[j + 1:j + 2] == "*":
            j = src.find("*/", j) + 1
        elif c in "\"'":
            in_str = c
        elif c == open_ch: depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise SystemExit(f"unbalanced: {name}")


def to_python(text):
    """JS object/array literal -> Python object. Handles // comments, unquoted
    keys, trailing commas, and Math.PI expressions we don't use here."""
    # strip // comments that are not inside a string
    out, in_str, esc, i = [], None, False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == in_str: in_str = None
        elif c in "\"'":
            in_str = c; out.append(c)
        elif c == "/" and i + 1 < len(text) and text[i + 1] == "/":
            while i < len(text) and text[i] != "\n": i += 1
            continue
        elif c == "/" and i + 1 < len(text) and text[i + 1] == "*":
            i = text.find("*/", i) + 2
            continue
        else:
            out.append(c)
        i += 1
    s = "".join(out)
    s = re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:", r'\1"\2":', s)   # quote bare keys
    s = re.sub(r"([{,]\s*)(\d+)\s*:", r'\1"\2":', s)               # quote numeric keys
    s = re.sub(r",(\s*[}\]])", r"\1", s)                             # trailing commas
    # Leave \" alone — JSON already understands it. Only convert single-quoted
    # strings (which never contain escapes in these files) to double-quoted.
    s = re.sub(r"'([^'\\\\]*)'", lambda m: json.dumps(m.group(1)), s)
    s = s.replace("null", "null").replace("true", "true").replace("false", "false")
    return json.loads(s)


def dump(name, obj):
    # pprint, not json.dumps: JSON emits true/false/null, which are not Python.
    return f"{name} = {pprint.pformat(obj, width=96, sort_dicts=False)}\n\n"


hm = (TOOLS / "hammermill-sizing-calculator.html").read_text()
bh = (TOOLS / "baghouse-filter-calculator.html").read_text()
cl = (TOOLS / "counterflow-cooler-sizing-calculator.html").read_text()

parts = ['"""Data tables extracted verbatim from MCE\'s calculators in renderer/tools/.\n\n'
         'Generated, do not hand-edit: change the calculator HTML and re-run the\n'
         'extraction (see docs/quote-builder.md). Every table below is MCE\'s own\n'
         'engineering and pricing data.\n"""\n\n']

for name in ["PRODUCTS", "MCE_XM_MILLS", "FEEDER_10", "FEEDER_14", "SCREW_TABLES",
             "TROUGH_LABELS", "MOTOR_SIZES", "MILL_PRICING", "FEEDER_PRICING",
             "FAMILY_SETS", "ROTOR_INFO", "WIDTH_TO_ROW", "PLENUM_V_IDX", "XM_CHART"]:
    parts.append(dump(name, to_python(js_body(hm, name))))

for name in ["BAG_COUNTS", "BAG_LENGTHS", "KICE_MODELS"]:
    parts.append(dump("BH_" + name, to_python(js_body(bh, name))))

for name in ["PELLETS", "SERIES", "MODELS", "OPTS", "ADDERS", "DUCT_SIZES", "PD_4500",
             "CHECK_DEFS"]:
    parts.append(dump("CL_" + name, to_python(js_body(cl, name))))

pathlib.Path("/home/user/CRM/renderer/calculators/_data.py").write_text("".join(parts))
print("wrote _data.py")
