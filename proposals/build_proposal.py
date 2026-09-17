#!/usr/bin/env python3
"""MCE branded proposal / quote builder.

Renders a proposal JSON file (see 2026-09-mid-states-xm4460/proposal.json) to a
letter-size PDF in MCE brand furniture (black header band with logo, orange rule,
steel-grey section bars, Oswald headings, Inter body) — the same layout as the
LETEK DCG XD-96 budgetary proposal of Sep 2026.

Usage:
  python3 proposals/build_proposal.py proposals/<job>/proposal.json [--html]

Output: PDF next to the JSON (name from "output_basename"), plus the HTML if --html.
Needs: jinja2, playwright (python), and a Chromium (auto-detected under /opt/pw-browsers,
or set CHROMIUM_PATH).

Markup inside any text field:
  [[text]]   -> orange "needs MCE input" flag (only shown while "draft": true; the text
                itself is always printed)
  **text**   -> bold
  lines beginning with "• " render as bullets inside description cells
"""
import base64
import glob
import json
import os
import pathlib
import re
import sys

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"


def b64(path):
    return base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def rich(text, draft=True):
    """Escape, then apply the small inline markup set. Bullets become a <ul>."""
    if text is None:
        return Markup("")
    lines = str(text).split("\n")
    out, in_list = [], False
    for ln in lines:
        s = escape(ln)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", str(s))
        cls = "flag" if draft else "flag-off"
        s = re.sub(r"\[\[(.+?)\]\]", rf'<span class="{cls}">\1</span>', s)
        if ln.startswith("• "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{s[2:]}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if ln.strip() == "":
                out.append('<div class="gap"></div>')
            else:
                out.append(f"<div>{s}</div>")
    if in_list:
        out.append("</ul>")
    return Markup("".join(out))


def money(v):
    if v is None or v == "":
        return ""
    if isinstance(v, str):
        return v
    return "${:,.2f}".format(v)


def compute_pricing(sec):
    """Fill extended prices and totals for a pricing section in place."""
    subtotal = 0.0
    for it in sec.get("items", []):
        if isinstance(it.get("unit_price"), (int, float)):
            it["extended"] = round(it["unit_price"] * it.get("qty", 1), 2)
            subtotal += it["extended"]
        else:  # text-priced line (e.g. "Pending vendor quote") — shown, not totalled
            it["unit_price"] = it.get("price_text", "")
            it["extended"] = it.get("extended_text", "")
    sec["subtotal"] = round(subtotal, 2)
    pct = sec.get("discount_percent") or 0
    sec["discount_amount"] = round(subtotal * pct / 100.0, 2)
    sec["total"] = round(subtotal - sec["discount_amount"], 2)
    for op in sec.get("options", []):
        if isinstance(op.get("unit_price"), (int, float)):
            op["net_unit"] = round(op["unit_price"] * (1 - pct / 100.0), 2)
            op["net_extended"] = round(op["net_unit"] * op.get("qty", 1), 2)
    return sec


def build(json_path, want_html=False):
    json_path = pathlib.Path(json_path)
    doc = json.loads(json_path.read_text())
    draft = bool(doc.get("draft", False))
    for sec in doc.get("sections", []):
        if sec.get("type") == "pricing":
            compute_pricing(sec)

    env = Environment(loader=FileSystemLoader(str(ROOT)), autoescape=True)
    env.filters["rich"] = lambda t: rich(t, draft)
    env.filters["money"] = money
    fonts = {
        "oswald": b64(ASSETS / "fonts" / "Oswald[wght].ttf"),
        "inter": b64(ASSETS / "fonts" / "Inter[opsz,wght].ttf"),
        "inter_italic": b64(ASSETS / "fonts" / "Inter-Italic[opsz,wght].ttf"),
    }
    logo = b64(ASSETS / "mce-logo.png")
    tpl = env.get_template("template.html")
    html = tpl.render(d=doc, fonts=fonts, logo=logo, draft=draft)

    # Header / footer are separate documents in Chromium; give them the same fonts + logo.
    header = env.get_template("header.html").render(d=doc, fonts=fonts, logo=logo, draft=draft)
    footer = env.get_template("footer.html").render(d=doc, fonts=fonts, draft=draft)

    out_pdf = json_path.parent / (doc.get("output_basename", json_path.stem) + ".pdf")
    if want_html:
        (json_path.parent / (doc.get("output_basename", json_path.stem) + ".html")).write_text(html)

    from playwright.sync_api import sync_playwright
    chromium = os.environ.get("CHROMIUM_PATH")
    if not chromium:
        cands = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")
        chromium = cands[0] if cands else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium)
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        page.pdf(path=str(out_pdf), format="Letter", print_background=True,
                 display_header_footer=True, header_template=header, footer_template=footer,
                 margin={"top": "1.42in", "bottom": "0.62in", "left": "0.5in", "right": "0.5in"})
        browser.close()
    print(out_pdf)
    return out_pdf


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    build(args[0], want_html="--html" in sys.argv)
