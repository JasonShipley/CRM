#!/usr/bin/env python3
"""Render a quote JSON in the HubSpot quote layout MCE used before Twenty
(logo, slate header band, comments box, Products & Services table, totals,
signature block, contact card). Same JSON shape as render_local.py.

    python renderer/render_hubspot_style.py docs/quotes/my-quote.json out/my-quote.pdf
"""
import base64
import json
import pathlib
import sys
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

import render_local as rl

ROOT = pathlib.Path(__file__).resolve().parent

# Chromium snaps line boxes to whole CSS pixels, so a 16.3pt line pitch cannot be
# expressed directly. The page is authored with 22px lines and printed at this
# scale (16.3 / 16.5) so the output lands on the original 16.3pt pitch exactly.
PRINT_SCALE = 16.3 / 16.5

# Layout geometry in real points, measured off the original HubSpot PDF (A4).
GEOMETRY = dict(
    page_top=30, page_right=28.3, page_bottom=36, page_left=27.7,   # text column starts 10.2pt in
    logo_top=3.2, band_top=5.8, band_pad_top=22.0, band_pad_bottom=37.1, title_gap=17.7,
    comments_top=21.75, comments_pad_top=17.25, comments_pad_bottom=15.45, comments_gap=8.1,
    products_top=19.15, table_top=9.5, th_pad_top=8.4, th_pad_bottom=10.4,
    td_pad_top=10.6, td_pad_bottom=9.35, desc_gap=-0.7, totals_top=11.3, sub_pad_bottom=10.2,
    grand_top=9.75, terms_top=20.05, terms_gap=8.2, sig_top=41.0, sig_line_top=53.3,
    sig_cap_top=2.6, sig2_top=44.8, contact_top=65.5, avatar_top=15.0, contact_lines_top=4.7,
)


def long_date(iso):
    return datetime.fromisoformat(iso).strftime("%B %-d, %Y")


def build(q, geometry=GEOMETRY):
    ctx = rl.build_context(q)
    for it in ctx["items"]:  # keep blank lines: the HubSpot layout renders them as empty rows
        it["_desc_lines"] = [ln.rstrip() for ln in (it.get("itemDescription") or "").split("\n")]
    ctx["issue_date"] = long_date(q["issueDate"])
    ctx["expires"] = long_date(q["expirationDate"])
    ctx["a"] = (q.get("company") or {}).get("address") or {}
    ctx["c"] = q.get("contact") or {}
    ctx["g"] = geometry
    fonts = ROOT / "assets" / "fonts"
    ctx["font400"] = base64.b64encode((fonts / "Montserrat-Regular.ttf").read_bytes()).decode()
    ctx["font700"] = base64.b64encode((fonts / "Montserrat-Bold.ttf").read_bytes()).decode()
    ctx["avatar_b64"] = base64.b64encode((ROOT / "assets" / "jason-avatar.png").read_bytes()).decode()
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.filters["s"] = lambda v: round(float(v) / PRINT_SCALE, 3)
    return env.get_template("quote_hubspot.html").render(**ctx)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, out_pdf = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    html = build(json.loads(src.read_text()))
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.with_suffix(".html").write_text(html)
    rl.html_to_pdf(html, out_pdf, scale=PRINT_SCALE, prefer_css_page_size=True)
    print(f"wrote {out_pdf}")


if __name__ == "__main__":
    main()
