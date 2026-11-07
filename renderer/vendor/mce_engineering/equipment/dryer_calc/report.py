"""One-page sizing report (PDF for the quote file, HTML for a phone), built from the API response.

Contents: inputs, mass and energy balance, gas flows, recommended drum, burner, fan, warnings.
MCE facing: no other manufacturer's names or tables appear here.
"""

from __future__ import annotations

import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COMPANY = "Midwest Custom Engineering, Inc."
SEV_LABEL = {"blocked": "BLOCKED", "violation": "VIOLATION", "needs_verification": "VERIFY", "warning": "WARNING",
             "info": "INFO"}


def _v(x, nd=0) -> str:
    if x is None:
        return "-"
    if isinstance(x, dict) and "value" in x:
        val = x["value"]
        si = x.get("si")
        s = _num(val, nd) + (f" {x['unit']}" if x.get("unit") else "")
        if si:
            s += f" ({_num(si[0], nd if abs(si[0]) >= 10 else 2)} {si[1]})"
        return s
    return _num(x, nd) if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


def _num(v, nd=0) -> str:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if v != 0 and abs(v) < 0.1:
        return f"{v:.4g}"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if nd == 0 and abs(v) >= 100:
        return f"{v:,.0f}"
    return f"{v:,.{max(nd, 2) if abs(v) < 10 else 1}f}"


def report_rows(resp: dict) -> dict[str, list[list[str]]]:
    o = resp["outputs"]
    mb, cb, gb, res = o["mass_balance"], o["combustion"], o["gas_balance"], o["results"]
    eb, drum, air = o["energy_balance"], o["drum"], o["air_system"]
    inp = {r["field"]: r for r in resp["inputs"]}

    def i(path, label=None, unit_override=None):
        r = inp[path]
        val = r["value"]
        mark = " *" if r["overridden"] else ""
        return [label or path.split(".")[1], f"{_num(val, 2) if isinstance(val, (int, float)) else val} "
                                               f"{unit_override if unit_override is not None else r['unit']}{mark}"]

    inputs = [
        ["Material", resp["outputs"].get("material_label", inp["process.material"]["value"])], i("process.throughput", "Throughput",
                                               f"{inp['process.throughput_unit']['value']} ({inp['process.throughput_basis']['value']})"),
        i("process.infeed_mc_wb", "Infeed MC"), i("process.target_mc_wb", "Product MC"),
        i("process.backmix_ratio", "Backmix"), i("process.material_cp", "Material Cp"),
        i("process.bulk_density_dry", "Bulk density (dry)"), i("process.product_temp_F", "Product temp"),
        i("site.ambient_temp_F", "Ambient"), i("site.humidity_lb_lb", "Humidity"), i("site.elevation_ft", "Elevation"),
        i("fuel.fuel", "Fuel", ""), i("fuel.excess_air_pct", "Excess air"),
        i("fuel.furnace_efficiency", "Furnace efficiency"), i("rotary.gas_mode", "Gas side fixed", ""),
        i("rotary.inlet_temp_F", "Inlet temp (if fixed)"),
        i("rotary.exhaust_temp_F", "Exhaust temp"), i("rotary.recycle_fraction", "Recycle"),
        i("rotary.leakage_pct", "Seal leakage"),
    ]
    balance = [
        ["Wet feed", _v(mb["wet_feed_lb_hr"])], ["Dry solids", _v(mb["solids_lb_hr"])],
        ["Water in / out", f"{_num(mb['water_in_lb_hr']['value'])} / {_num(mb['water_out_lb_hr']['value'])} lb/hr"],
        ["Evaporation", _v(mb["evaporation_lb_hr"])], ["Product", _v(mb["product_lb_hr"])],
        ["MC wet / dry basis", f"{mb['infeed_mc_wb_pct']:g}% / {mb['infeed_mc_db_pct']:.1f}% in, "
                               f"{mb['target_mc_wb_pct']:g}% / {mb['target_mc_db_pct']:.1f}% out"],
        ["Mass closure (overall)", f"{mb['overall_closure_pct']:.2e} %"],
    ]
    energy = [["Fuel input (LHV)", _v(eb["fuel_input_btu_hr"]), "100%", ""]]
    for k, v in eb["uses_btu_hr"].items():
        energy.append([k.replace("_", " ").capitalize(), _v(v), f"{eb['uses_pct'][k]:.1f}%",
                       f"{eb['uses_btu_per_lb_water'][k]:,.0f}"])
    energy.append(["Energy closure", f"{eb['closure_pct']:.2e} %", "", "BTU/lb water"])
    st = gb["streams"]
    gas = []
    for k in ("combustion_air", "dilution_air", "leakage_air", "recycle", "dryer_inlet", "dryer_exhaust", "stack"):
        s = st[k]
        if s["lb_hr"]["value"] <= 0:
            continue
        gas.append([k.replace("_", " "), _num(s["temp_F"]["value"]), _num(s["lb_hr"]["value"]),
                    _num(s["scfm"]["value"]), _num(s["acfm"]["value"]), f"{s['humidity_lb_lb']['value']:.4f}"])
    ex = gb["exhaust"]
    rec = drum["recommended"]
    nxt = drum["next_size_up"]
    drum_rows = []
    if rec:
        drum_rows = [["Recommended", rec["size"]], ["Next size up", nxt["size"] if nxt else "-"],
                     ["VER", f"{rec['ver']['value']:.2f} lb/hr-ft3 (range {rec['ver_design_range'][0]:g} to "
                             f"{rec['ver_design_range'][1]:g})"],
                     ["Gas velocity", f"{rec['gas_velocity_fpm']['value']:.0f} FPM (limit {rec['design_velocity_fpm']['value']:g})"],
                     ["Residence / fill", f"{rec['residence_min']:.1f} min / {rec['fill_pct']:.1f}%"],
                     ["Speed", f"{rec['rpm']:.1f} rpm ({rec['pct_critical']:g}% of {rec['critical_rpm']:.1f} critical)"],
                     ["Slope / L/D", f"{rec['slope_in_per_ft']:.3f} in/ft / {rec['l_over_d']:.1f}"]]
    else:
        drum_rows = [["Recommended", "NONE PASSES (see warnings)"]]
    fan = air["fan"]
    vol = res["fuel_volume"]
    vol_s = ", ".join(_v(v) for k, v in vol.items() if isinstance(v, dict))
    burner = [["Operating (LHV)", _v(res["burner_operating_mmbtu_hr_lhv"], 2)],
              ["Operating (HHV)", _v(res["burner_operating_mmbtu_hr_hhv"], 2)],
              ["Design", f"{_v(res['burner_design_mmbtu_hr_lhv'], 2)} (x{res['burner_design_margin']:g})"],
              ["Fuel", f"{_v(res['fuel_lb_hr'])}; {vol_s}"],
              ["Specific heat", f"{res['btu_per_lb_water_lhv']['value']:,.0f} BTU/lb water LHV "
                                f"({res['btu_per_lb_water_hhv']['value']:,.0f} HHV)"],
              ["Inlet / flame", f"{gb['inlet_temp_F']['value']:,.0f} F / {cb['flame_temp_F']['value']:,.0f} F"],
              ["Exhaust dew point", f"{ex['dew_point_F']['value']:.0f} F (margin {ex['dew_point_margin_F']['value']:.0f} F), "
                                    f"{ex['relative_humidity_pct']:.0f}% RH"],
              ["Annual fuel", _v(res["annual"]["fuel_tons_yr"]) + f", {_num(res['annual']['fuel_mmbtu_yr_lhv']['value'])} MMBtu/yr LHV"]]
    if res.get("self_fueled_balance"):
        sf = res["self_fueled_balance"]
        burner.append(["Net product after fuel", f"{_v(sf['net_product_lb_hr'])} ({sf['fraction_of_product_burned']:.0%} burned)"])
    fan_rows = [["Fan", f"{_num(fan['acfm']['value'])} ACFM at {fan['inlet_temp_F']['value']:g} F, "
                        f"{fan['gas_density_lb_ft3']['value']:.4f} lb/ft3"],
                ["Static pressure", f"{fan['sp_operating_in_wc']['value']:.1f} in. w.c. operating "
                                    f"({fan['sp_standard_air_in_wc']['value']:.1f} at standard air)"],
                ["Fan power", f"{fan['bhp_operating']['value']:.1f} BHP hot, {fan['bhp_cold_start']['value']:.1f} BHP cold; "
                              f"{fan['motor_hp_nema']} HP motor ({fan['motor_basis']})"]]
    for k, d in air["ducts"].items():
        fan_rows.append([f"Duct {k.replace('_', ' ')}", f"{d['diameter_in']['value']:g} in. at {d['velocity_fpm']['value']:,.0f} FPM"])
    warnings = [[SEV_LABEL[f["severity"]], f["message"]] for f in resp["flags"]
                if f["severity"] in ("blocked", "violation", "warning", "needs_verification")]
    return {"inputs": inputs, "balance": balance, "energy": energy, "gas": gas, "drum": drum_rows,
            "burner": burner, "fan": fan_rows, "warnings": warnings}


def _title(resp: dict) -> tuple[str, str]:
    rec = resp.get("record", {})
    job = resp.get("job", {})
    t = f"Rotary Dryer Sizing Report: job {job.get('job_number', '-')}"
    sub = (f"Sizing record {rec.get('index') or 'not saved'}, {rec.get('timestamp', '')}, {rec.get('calculator_version', '')}. "
           f"Customer {job.get('customer') or '-'}. * = overridden input.")
    return t, sub


def write_pdf(resp: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = report_rows(resp)
    fs = 6.4
    body = ParagraphStyle("b", fontName="Helvetica", fontSize=fs, leading=fs + 1.3)
    head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=fs + 1.4, leading=fs + 3, spaceBefore=3, spaceAfter=1)
    title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=11, leading=13)

    def P(t):
        return Paragraph(html.escape(str(t)), body)

    def tbl(data, widths, header=None):
        d = ([[P(h) for h in header]] if header else []) + [[P(c) for c in r] for r in data]
        t = Table(d, colWidths=[w * inch for w in widths])
        style = [("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("TOPPADDING", (0, 0), (-1, -1), 0.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
                 ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")))
        t.setStyle(TableStyle(style))
        return t

    def section(name, flow):
        return [Paragraph(name, head), flow]

    t, sub = _title(resp)
    left = (section("Inputs", tbl(rows["inputs"], [1.15, 2.4]))
            + section("Mass balance", tbl(rows["balance"], [1.15, 2.4]))
            + section("Drum", tbl(rows["drum"], [1.15, 2.4])))
    right = (section("Energy balance", tbl(rows["energy"], [1.2, 1.25, 0.45, 0.65], ["Item", "BTU/hr", "%", "BTU/lb"]))
             + section("Burner and fuel", tbl(rows["burner"], [1.1, 2.45]))
             + section("Fan and ducts", tbl(rows["fan"], [1.1, 2.45])))
    two = Table([[left, right]], colWidths=[3.6 * inch, 3.65 * inch])
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    o = resp["outputs"]
    story = [Paragraph(COMPANY, head), Paragraph(t, title), P(sub), P("Reference state: " + o["reference_state"]),
             P(o["site"]["standard_conditions"] + f"; site pressure {o['site']['barometric_psia']['value']:.3f} psia."),
             Spacer(1, 2), two,
             Paragraph("Gas flows", head),
             tbl(rows["gas"], [1.3, 0.6, 1.0, 1.0, 1.0, 1.0], ["Stream", "F", "lb/hr", "SCFM", "ACFM", "lb H2O/lb dry"]),
             Paragraph(f"Warnings ({len(rows['warnings'])})", head),
             tbl(rows["warnings"][:14] or [["-", "None"]], [0.75, 6.5])]
    if len(rows["warnings"]) > 14:
        story.append(P(f"{len(rows['warnings']) - 14} more in the sizing record."))
    doc = SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.45 * inch, rightMargin=0.45 * inch,
                            topMargin=0.35 * inch, bottomMargin=0.35 * inch, title=t, author=COMPANY)
    doc.build(story)
    return path


def to_html(resp: dict) -> str:
    rows = report_rows(resp)
    t, sub = _title(resp)
    o = resp["outputs"]

    def table(data, header=None):
        h = "".join(f"<th>{html.escape(x)}</th>" for x in header) if header else ""
        body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in data)
        return f"<table>{'<thead><tr>' + h + '</tr></thead>' if h else ''}<tbody>{body}</tbody></table>"

    parts = [f"<h1>{html.escape(t)}</h1><p class=sub>{html.escape(sub)}</p>",
             "<h2>Summary</h2><ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in resp["summary"]["lines"]) + "</ul>",
             "<h2>Warnings</h2>" + table(rows["warnings"] or [["-", "None"]]),
             "<h2>Inputs</h2>" + table(rows["inputs"]), "<h2>Mass balance</h2>" + table(rows["balance"]),
             "<h2>Energy balance</h2>" + table(rows["energy"], ["Item", "BTU/hr", "%", "BTU/lb"]),
             "<h2>Gas flows</h2><div class=scroll>" + table(rows["gas"], ["Stream", "F", "lb/hr", "SCFM", "ACFM", "lb H2O/lb dry"]) + "</div>",
             "<h2>Drum</h2>" + table(rows["drum"]), "<h2>Burner and fuel</h2>" + table(rows["burner"]),
             "<h2>Fan and ducts</h2>" + table(rows["fan"]),
             f"<p class=sub>Reference state: {html.escape(o['reference_state'])}</p>"]
    css = ("body{font-family:system-ui,sans-serif;margin:0 auto;max-width:860px;padding:0 16px;color:#111;background:#fff}"
           "h1{font-size:1.25rem}h2{font-size:1rem;margin:1.1em 0 .3em;border-bottom:2px solid #e8731a}"
           "table{border-collapse:collapse;width:100%;font-size:.85rem}td,th{border:1px solid #ccc;padding:4px 6px;"
           "text-align:left;vertical-align:top}th{background:#f2f2f2}.sub{color:#555;font-size:.8rem}"
           ".scroll{overflow-x:auto}")
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport "
            f"content='width=device-width,initial-scale=1'><title>Rotary Dryer Sizing</title><style>{css}</style>"
            f"</head><body><p class=sub>{COMPANY}</p>{''.join(parts)}</body></html>")
