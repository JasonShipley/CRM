#!/usr/bin/env python3
"""Build a full draft proposal from a structured JobRequest.

Nothing in here asks a language model anything. It takes the fields a rep stated
(see interpret.py), runs MCE's calculators, and assembles the proposal in the
shape MCE's own Equipment Proposals use — design basis, scope and pricing,
options, furnished-by-others, schedule, commercial terms.

Anything the rep left open, the calculators could not size, or MCE has no
calculator for yet comes through as an open item and prints orange on the
proposal, matching MCE's "orange items require MCE input before release"
convention on a draft.
"""
import datetime
import re

import calculators
from calculators import _vendor
from calculators._data import PRODUCTS

FALLBACK_PLENUM_VELOCITY = "300"
FALLBACK_TROUGH = "45"

STANDARD_BY_OTHERS = [
    "Motor starters, VFDs and motor control",
    "Controls, PLC programming and instrumentation beyond the switches listed in Section 2",
    "Concrete, foundations, floor openings, anchor bolts and support steel",
    "Infeed to the feeder, and conveyance from the discharge",
    "Installation, millwright, electrical and start-up labor",
]

TERMS = ("Payment: 50% down with order, balance before shipment. Prices are in US dollars "
         "and exclude sales tax, freight and installation. Warranty per MCE standard terms "
         "and conditions.")


# Corporate suffixes MCE leaves out of a proposal reference: their own
# Mid-States Companies quote is MCEQ2609MIDSTATESR1, not ...MIDSTATESCOMPANIESR1.
_SUFFIXES = {"COMPANIES", "COMPANY", "INC", "INCORPORATED", "LLC", "LLP", "LTD",
             "CORP", "CORPORATION", "CO", "GROUP", "HOLDINGS", "INTERNATIONAL"}


def _slug(name, limit=16):
    """Customer part of a proposal reference: whole words only, never cut mid-word."""
    words = [w for w in re.split(r"[^A-Za-z0-9]+", (name or "").upper()) if w]
    words = [w for w in words if w not in _SUFFIXES] or words
    out = ""
    for w in words:
        if len(out) + len(w) > limit:
            break
        out += w
    return out or (words[0][:limit] if words else "CUSTOMER")


def quote_number(company, today=None):
    """MCE's proposal reference: MCEQ + YYMM + CUSTOMER + R1."""
    d = today or datetime.date.today()
    return f"MCEQ{d:%y%m}{_slug(company)}R1"


def _product(job):
    """Resolve the rep's product wording to a row in MCE's index table."""
    if job.product_match:
        for p in PRODUCTS:
            if p["name"] == job.product_match:
                return p
    return None


def _validity(today=None):
    d = today or datetime.date.today()
    year_end = datetime.date(d.year, 12, 31)
    if (year_end - d).days < 30:
        year_end = datetime.date(d.year + 1, 12, 31)
    return year_end


# MCE's grain/feed conveying velocity, the duct calculator's own default.
DUCT_VELOCITY_FPM = 4000


def _hp_number(label):
    """"200 HP" -> 200.0, so a motor named as text still finds its cost."""
    m = re.search(r"([\d.]+)", str(label or ""))
    return float(m.group(1)) if m else None


def build(job, today=None, delivery_weeks=None):
    """JobRequest -> (quote dict, open items). Never raises on a thin request.

    `delivery_weeks` fills the delivery line on the schedule — "10-12", "14", or
    None. MCE's lead time moves with the backlog, so there is no default: left
    unset the line stays a blank for someone to fill, rather than carrying a
    number nobody stood behind.
    """
    open_items = list(job.ambiguities or [])
    design = []
    lines = []
    by_others = list(STANDARD_BY_OTHERS)
    sizing = []

    qty = max(int(job.quantity or 1), 1)
    product = _product(job)
    company = job.customer_company or ""

    # --- what the rep gave us, and what is missing ---------------------------
    pph = job.capacity_pph or (job.capacity_tph * 2000 if job.capacity_tph else None)
    if not pph:
        open_items.append("Throughput was not stated — the mill cannot be sized without it.")
    if not job.screen_64ths:
        open_items.append("Screen size was not stated — the mill cannot be sized without it.")
    if not product:
        open_items.append(
            f"No MCE index-table product matches "
            f"\"{job.product_as_written or 'the product'}\" — engineering to confirm the "
            "grinding index, screen area per HP and bulk density before this is quoted.")
    elif job.product_confidence != "stated":
        open_items.append(
            f"Product read as \"{product['name']}\" ({job.product_confidence}) from "
            f"\"{job.product_as_written}\". The pet food entries grind very differently — "
            "confirm before release.")

    result = None
    if pph and job.screen_64ths and product:
        feeder = job.feeder
        rows = feeder.rows
        if rows is None and feeder.as_written:
            open_items.append(
                f"Feeder rows unclear in \"{feeder.as_written}\" — sized from the mill screen "
                "width instead. Confirm the row count.")
        form = {
            "pph": pph,
            "screen64": job.screen_64ths,
            "index": product["index"],
            "sqInHp": product["sqInHp"],
            "bulkDensity": product["bulkDensity"],
            "family": "grain",
            "millModel": job.mill_model or "",
            "plenumVelocity": FALLBACK_PLENUM_VELOCITY,
            "feederDia": feeder.diameter_in or "10",
            "cupType": feeder.cup_type or "nylon",
            "rowCount": rows if rows is not None else "",
            "magnetClean": feeder.magnet_clean or "sma",
            "trough": FALLBACK_TROUGH,
            "runLength": 0,
        }
        result = calculators.run("hammermill", form)
        if result.get("error"):
            open_items.append(f"Hammermill sizing failed: {result['error']}")
            result = None
        else:
            open_items.extend(result.get("warnings", []))
            sizing.append({"calculator": result["calculator"], "inputs": form,
                           "formula": result.get("formula", ""),
                           "outputs": result.get("outputs", []),
                           "warnings": result.get("warnings", [])})

    out = {o["label"]: o["value"] for o in (result or {}).get("outputs", [])}

    # --- the rep's stated motor vs what the math says ------------------------
    motor = out.get("Motor size")
    if job.motor_hp and motor:
        stated = f"{job.motor_hp:g} HP"
        if stated != motor:
            open_items.append(
                f"The request says a {stated} motor; {pph:,.0f} PPH at index "
                f"{product['index']} through a {job.screen_64ths:g}/64\" screen calculates "
                f"to {motor}. Confirm which governs before release.")
    elif job.motor_hp and not motor:
        open_items.append(f"Motor stated as {job.motor_hp:g} HP but the mill could not be "
                          "sized to check it.")

    # --- design basis ---------------------------------------------------------
    def row(parameter, value, notes="", needs_input=False):
        design.append({"parameter": parameter, "value": value, "notes": notes,
                       "needsInput": needs_input})

    row("Product", product["name"] if product else (job.product_as_written or "TBD"),
        f'As described: "{job.product_as_written}"' if job.product_as_written else "",
        needs_input=not product)
    row("Number of mills", f"{qty} × {out.get('Mill', 'TBD')}",
        "Direct drive, dual grinding chamber" if result else "", needs_input=not result)
    if pph:
        row("Capacity", f"{pph / 2000:g} TPH ({pph:,.0f} PPH) per mill",
            f"At grinding index {product['index']}" if product else "", needs_input=not product)
    else:
        row("Capacity", "TBD", "Not stated in the request", needs_input=True)
    row("Screen size", f'{job.screen_64ths:g}/64"' if job.screen_64ths else "TBD",
        "One set of screens per mill included" if job.screen_64ths else "",
        needs_input=not job.screen_64ths)
    if result:
        row("Mill drive", f"{motor}, {out.get('Rotor', '')}",
            "460 V/3/60 TEFC premium efficiency — motor priced separately")
        # Fit commentary (headroom, undersize) is internal only — it belongs in
        # the open-items list the customer never sees, not on the proposal.
        row("Screen area", f"{out.get('Mill screen area', '')}",
            "Mild steel with AR liners; hammers hard faced and heat treated")
        if job.include_air_system or job.include_plenum:
            row("Air relief through mill", f"{out.get('Plenum airflow', 'TBD')}",
                f"At {FALLBACK_PLENUM_VELOCITY} FPM plenum design velocity")
        row("Feeder", out.get("Rotary feeder", "TBD"),
            f"{out.get('Feeder shaft speed', '')} at 90% cup fill"
            + (f'; {job.feeder.magnet_clean and "magnet adapter included"}'
               if job.feeder.magnet_clean else ""))
    row("Installation", "By others", "MCE start-up assistance available at standard rates")

    # --- scope of supply -------------------------------------------------------
    if result:
        wanted = {"Hammermill": True,
                  "Rotary Feeder": True,
                  "Plenum Chamber": job.include_plenum or job.include_air_system,
                  "Screw Conveyor": job.include_screw}
        for line in result["lines"]:
            keep = next((v for k, v in wanted.items() if k in line["name"]), True)
            if not keep:
                continue
            lines.append({**line, "quantity": qty})

    # --- air system -------------------------------------------------------------
    if job.include_air_system:
        screen_area = result.get("screen_area") if result else None
        # A baghouse unless the rep named a cyclone: MCE's standard air relief is a
        # filter, and with one the fan ducts to atmosphere after it — no cyclone.
        want_cyclone = getattr(job, "dust_collection", None) == "cyclone"
        if screen_area and not want_cyclone:
            bh = calculators.run("baghouse", {"mode": "mill", "screenArea": screen_area,
                                              "ratio": 7, "lenFilter": "any"})
            if not bh.get("error"):
                for line in bh["lines"]:
                    lines.append({**line, "quantity": qty})
                sizing.append({"calculator": bh["calculator"], "inputs": {
                    "mode": "mill", "screenArea": screen_area, "ratio": 7},
                    "formula": bh.get("formula", ""), "outputs": bh.get("outputs", []),
                    "warnings": bh.get("warnings", [])})
                open_items.extend(bh.get("warnings", []))
        # With a baghouse the air is cleaned by the filter and the fan discharges
        # to atmosphere after it — no cyclone, and no fan line of its own: the
        # baghouse calculator already selected and priced the matched AirPro fan.
        have_baghouse = any("Baghouse" in ln["name"] for ln in lines)
        outstanding = ["Ductwork"]
        # The airlock under the filter (or cyclone) hopper is a buy-out. MCE's
        # standard mill-scale unit is the Airlanco FT-12; price it at MCE's own
        # buy-out divisor rather than listing it TBD.
        al = _vendor.airlock()
        if al:
            # Model number and specification only — the vendor's name is internal.
            al_number, al_price, al_date, al_brand, al_source, al_desc = al
            lines.append({
                "name": f"Rotary Airlock — {al_number}", "quantity": qty,
                "unitPrice": round(al_price, 2), "sku": al_number,
                "description": "\n".join([
                    al_desc,
                    "Mounts under the dust filter hopper",
                    "Budgetary price — firm on receipt of a current vendor quote",
                ])})
            open_items.append(
                f"Airlock priced as {al_brand} {al_number} from {al_source} "
                f"({al_date}), marked up at "
                f"MCE's buy-out divisor {_vendor.BUYOUT_DIVISOR:g}. It is the standard "
                "mill-scale drop-through; an ATEX/NFPA 69 certified valve costs "
                "substantially more and should be priced separately if the dust hazard "
                "assessment calls for one.")
        else:
            outstanding.append("Airlock")
        if not have_baghouse:
            # No filter, so the air goes through a cyclone. MCE's cyclone
            # calculator sizes it off the same plenum airflow the mill produces;
            # it carries no price basis, so the line stays needsPrice.
            plenum_cfm = result.get("plenum_cfm") if result else None
            cyc = (calculators.run("cyclone", {"mode": "cfm", "cfm": plenum_cfm,
                                               "series": "mce", "wg": "3"})
                   if plenum_cfm else {"error": "no plenum airflow"})
            if cyc.get("error"):
                outstanding.insert(0, "Cyclone")
            else:
                for line in cyc["lines"]:
                    lines.append({**line, "quantity": qty})
                sizing.append({"calculator": cyc["calculator"], "inputs": {
                    "mode": "cfm", "cfm": plenum_cfm, "series": "mce", "wg": "3"},
                    "formula": cyc.get("formula", ""), "outputs": cyc.get("outputs", []),
                    "warnings": cyc.get("warnings", [])})
                open_items.extend(cyc.get("warnings", []))
                open_items.append(
                    f'Cyclone sized {cyc["matchSize"]} from the mill\'s '
                    f'{cyc["cfm"]:,} CFM plenum airflow at 3" WG. Price basis: '
                    f'{cyc["priceBasis"]}.')
            outstanding.insert(0, "Fan")
        # Ductwork is sized from the same system airflow as everything else, but the
        # run length, the fittings and whether it vents to atmosphere all come out
        # of the site layout, so it is quoted on request rather than guessed at.
        if "Ductwork" in outstanding:
            outstanding.remove("Ductwork")
            plenum_cfm = result.get("plenum_cfm") if result else None
            dk = (calculators.run("duct", {"mode": "dia", "cfm": plenum_cfm,
                                           "velocity": DUCT_VELOCITY_FPM})
                  if plenum_cfm else {"error": "no plenum airflow"})
            if dk.get("error"):
                desc = ["Ductwork for the mill air-relief system.",
                        "Quoted on request once the site layout fixes the run and fittings."]
            else:
                desc = [f'{dk["diameter"]}" dia duct at {DUCT_VELOCITY_FPM:,} FPM conveying '
                        f'velocity on {dk["cfm"]:,.0f} CFM '
                        f'({dk["minDiameter"]:.2f}" minimum, rounded up to the next even inch)',
                        "Straight run, elbows, transitions and supports to suit the layout",
                        "May vent to atmosphere depending on the arrangement"]
                sizing.append({"calculator": dk["calculator"], "inputs": {
                    "mode": "dia", "cfm": plenum_cfm, "velocity": DUCT_VELOCITY_FPM},
                    "formula": dk.get("formula", ""), "outputs": dk.get("outputs", []),
                    "warnings": dk.get("warnings", [])})
            desc.append("Priced upon request once the layout is determined")
            lines.append({
                "name": "Ductwork — priced upon request", "quantity": qty,
                "unitPrice": 0, "needsPrice": True, "description": "\n".join(desc)})
        for item in outstanding:
            lines.append({
                "name": f"{item} — size and price TBD", "quantity": qty,
                "unitPrice": 0, "needsPrice": True,
                "description": (
                    f"{item} for the mill air-relief system. MCE has no calculator for this "
                    "item yet — engineering to size and price, or quote it by others.")})
        if have_baghouse:
            by_others.insert(0, "Stack and weather cap at the fan discharge")
            open_items.append(
                "Air system requested: baghouse sized from the mill screen area with its "
                "matched AirPro fan, discharging to atmosphere after the filter — no cyclone. "
                "Ductwork is sized from the same airflow but priced on request — the run, "
                "the fittings and whether it vents to atmosphere all come out of the site "
                "layout.")
        else:
            open_items.append(
                ("Air system requested with a cyclone rather than a filter, as the rep "
                 "wrote it."
                 if want_cyclone else
                 "Air system requested but no baghouse could be sized, so the quote shows "
                 "a cyclone instead — confirm that is what the customer wants.")
                + " The cyclone is sized above but carries no price; the fan, ductwork and "
                  "airlock are neither sized nor priced — take them to engineering or "
                  "quote the air system by others.")
    else:
        by_others.insert(0, "Air-relief system for the mill — fans, dust filters, ducting, "
                            "airlocks and explosion protection")

    if job.include_magnet or (job.feeder and job.feeder.magnet_clean):
        by_others.append("Compressed air to the magnet adapter (air cylinders)")

    for extra in job.other_items or []:
        lines.append({"name": f"{extra} — price TBD", "quantity": qty, "unitPrice": 0,
                      "needsPrice": True,
                      "description": f'Requested as "{extra}". Not sized or priced by any MCE '
                                     "calculator — engineering to confirm scope and price."})
        open_items.append(f'"{extra}" was requested but has no calculator — priced at zero '
                          "pending engineering.")

    # --- main drive motor, priced net like MCE's own proposals -------------------
    net_items = []
    if motor or job.motor_hp:
        hp = motor or f"{job.motor_hp:g} HP"
        hp_num = job.motor_hp or _hp_number(motor)
        mq = _vendor.motor(hp_num)
        notes = [f"{hp}, 1800 RPM, 460 V/3/60, TEFC premium efficiency, 1.15 SF",
                 "Mounted, aligned and guarded on the mill at MCE",
                 "Priced net"]
        if mq:
            # Model number on the line; the make and the cost basis stay internal.
            m_model, m_price, m_date, m_make, m_source = mq
            notes.insert(1, f"Model {m_model}")
            net_items.append({
                "name": f"Main Drive Motor — {hp}", "quantity": qty,
                "unitPrice": round(m_price, 2), "sku": m_model,
                "description": "\n".join(notes)})
            open_items.append(
                f"Main drive motor priced as {m_make} {m_model} from {m_source} "
                f"({m_date}), marked up at MCE's buy-out divisor "
                f"{_vendor.BUYOUT_DIVISOR:g}."
                + (f" {_vendor.MOTOR_ALTERNATE_PENDING[int(hp_num)]} — compare before "
                   "release." if int(hp_num or 0) in _vendor.MOTOR_ALTERNATE_PENDING else ""))
        else:
            notes.append("Price from the current motor quotation — confirm make and "
                         "availability")
            net_items.append({
                "name": f"Main Drive Motor — {hp}", "quantity": qty, "unitPrice": 0,
                "needsPrice": True, "description": "\n".join(notes)})
            open_items.append(
                f"Main drive motor ({hp}) is unpriced — MCE has no cost on file at that "
                "horsepower. Add the current motor quotation, or the customer may supply "
                "and ship motors to MCE.")

    title_model = out.get("Mill") or job.mill_model or "Hammermill"
    product_label = product["name"] if product else (job.product_as_written or "")
    name = f"{title_model} Grinding System"
    if qty > 1:
        name = f"{title_model} Grinding System ({qty} Mills)"
    if product_label:
        name += f" — {product_label}"

    validity = _validity(today)
    quote = {
        "name": name[:255],
        "quoteNumber": quote_number(company, today),
        "status": "DRAFT",
        "project": f"{product_label} grinding line" if product_label else "",
        "customer": {"company": company, "contact": job.customer_contact or "",
                     "email": "", "phone": "", "street1": "", "street2": "",
                     "city": "", "state": "", "postcode": "", "country": ""},
        "expirationDate": validity.isoformat(),
        "preparedBy": "JASON_SHIPLEY",
        "comments": _cover(job, out, qty, product_label),
        "terms": TERMS,
        "amount": "",
        "lines": lines,
        "netItems": net_items,
        "designBasis": design,
        "byOthers": by_others,
        "schedule": [
            {"item": "Freight", "basis": "FOB MCE plant, Newkirk, OK; freight quoted at time "
                                        "of shipment or shipped freight collect."},
            ({"item": "Delivery",
              "basis": f"{delivery_weeks} weeks after receipt of order and approval "
                       "drawings."}
             if delivery_weeks else
             {"item": "Delivery", "basis": "__ weeks after receipt of order and approval "
                                           "drawings.", "needsInput": True}),
            {"item": "Approval drawings",
             "basis": "General arrangement drawings issued for approval before fabrication."},
            {"item": "Installation",
             "basis": "By others. MCE start-up assistance and operator training available at "
                      "MCE's standard daily rate plus expenses."},
        ],
        "options": [],
        "openItems": open_items,
        "deliveryWeeks": delivery_weeks or "",
        "sizing": sizing,
        "sourceRequest": None,
    }
    return quote


def _cover(job, out, qty, product_label):
    mill = out.get("Mill") or job.mill_model or "hammermill"
    who = job.customer_company or "you"
    bits = [f"Midwest Custom Engineering is pleased to quote "
            f"{'one' if qty == 1 else qty} {mill} extra-heavy-duty hammer mill"
            f"{'' if qty == 1 else 's'}"]
    extras = []
    if job.feeder and (job.feeder.cup_type or job.feeder.rows or job.feeder.diameter_in):
        extras.append("rotary feeder")
    if job.include_plenum:
        extras.append("plenum chamber")
    if job.include_screw:
        extras.append("discharge screw")
    if job.include_air_system:
        extras.append("air system")
    if extras:
        bits.append("with " + ", ".join(extras[:-1]) + (" and " if len(extras) > 1 else "")
                    + extras[-1])
    if product_label:
        bits.append(f"for grinding {product_label.lower()}")
    if out.get("Motor size"):
        bits.append(f"at {out.get('Motor size')}")
    return (" ".join(bits) + f" for {who}. "
            "This proposal is a draft for internal review — items shown in orange need MCE "
            "input before it is released to the customer.")
