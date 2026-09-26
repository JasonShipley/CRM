#!/usr/bin/env python3
"""Combustible dust: the NFPA 660 protection package, priced from real quotes.

Most of what MCE grinds is a combustible dust — feed, grain, wood, pet food, DDGs.
When the rep says so, the proposal gains the protection package MCE actually buys
from High Tech Duct Werks, itemised the way Darryl quotes it and priced at MCE's
buy-out divisor:

  isolation, discharge   a certified explosion-proof rotary valve under the vessel,
                         so a deflagration cannot follow the material out
  the vent               an NFPA 68 panel on the vessel, plus its burst sensor
  isolation, duct        flap valves on the INLET and OUTLET, held open by flow and
                         slammed shut by the pressure front, plus the UL control
                         panel that turns those sensors into a plant shutdown and
                         the level sensors that catch a valve buried in dust
  the adaptor            MCE's own fabricated spool below the bin vent, because a
                         panel needs flat unobstructed wall and a bin vent bolted
                         onto a plenum chamber does not offer one

Two things are still not priced here, on purpose. The panel COUNT is the vent
manufacturer's calculation against a dust hazard analysis, so panels are quoted per
panel with the counts comparable vessels took. And a FLAMELESS vent — what an
indoor vessel with no wall to vent through needs — has never been bought by MCE:
Boss quoted its own distributor three flameless assemblies at $46,623 each against
two domed panels at $2,758, so it is a different conversation, not a line swap.
"""
from . import _vendor
from ._fmt import money

# NFPA 660 consolidated the combustible-dust standards (652/654 and the commodity
# standards) and is what Darryl's own estimate cites. The DHA is still the owner's
# duty, and it is the DHA that sets everything else.
DHA_NOTE = ("Treated as a combustible dust: protection is per NFPA 660, with NFPA 68 "
            "venting and NFPA 69 isolation, and the dust hazard analysis — Kst and Pmax "
            "from a tested sample of the actual product — sets the vent area and the "
            "isolation. MCE has not assumed either.")


def _ref(options):
    """The next option letter, so these slot into a list the caller is building."""
    return chr(ord("A") + len(options))


def kst_reference(material):
    """(name, record) for a dust MCE has actually worked to, or None."""
    return _vendor.dust_on_record(material)


def design_basis(material=None):
    """The design-basis row a combustible-dust job carries."""
    notes = [DHA_NOTE]
    ref = kst_reference(material)
    if ref:
        name, rec = ref
        notes.append(
            f"For reference, MCE has worked to Kst {_vendor._span(rec['kst'])} bar·m/s and "
            f"Pmax {_vendor._span(rec['pmax'])} bar on {name} dust — this product still "
            "needs its own sample.")
    return {"parameter": "Dust classification", "value": "Combustible dust",
            "notes": " ".join(notes), "needsInput": True}


def isolation_option(options, quantity=1, replacing=None):
    """The certified rotary valve on the discharge, priced from Est 7659."""
    item = _vendor.protection_item("rotary")
    if not item:
        return None
    name, sell, cost, qty, date, source, desc = item
    lines = [desc,
             ("Takes the place of the standard drop-through airlock in the scope above"
              if replacing else "Mounts under the collector hopper")]
    found = _vendor.certified_valve_range()
    if found:
        lo, hi, _src = found
        # The quoted valve is a 10", and the standard airlock in MCE's scope is a 12".
        # It would be easy — and wrong — to read this option as a cheap upgrade, so the
        # line says plainly that the size is not settled and the range for the larger
        # certified valves on file is right there next to it.
        lines.append(f'Priced as the 10" valve. This is NOT a size-for-size swap for the '
                     f"standard airlock: larger certified valves on file run {money(lo)} "
                     f"to {money(hi)}, and MCE confirms the size against the actual duty "
                     "before this is firm")
    lines.append("Flame-passage certified, so the deflagration cannot propagate back "
                 "through the discharge the way a standard drop-through valve allows")
    instead = f" in lieu of the standard {replacing}" if replacing else ""
    return {"ref": _ref(options), "quantity": quantity,
            "unitPrice": round(sell, 2), "budgetPrice": True,
            "name": f"NFPA 69 isolation — certified rotary valve{instead}",
            "description": "\n".join(lines)}


def vent_option(options, quantity=1, vessel=None, indoors=None, size=None):
    """The vent panel: priced per panel where MCE has that panel's quote.

    `indoors` True means a flameless vent, which MCE has never bought — the option
    states the requirement and carries no number rather than the domed price.
    """
    on = f" on the {vessel}" if vessel else ""
    counts = sorted({s["selection"].split(" x ")[0].strip()
                     for s in _vendor.VENT_SELECTIONS})

    if indoors is True:
        flam = _vendor.FLAMELESS_ON_RECORD
        return {"ref": _ref(options), "quantity": quantity, "needsPrice": True,
                "name": "Explosion vent — flameless" + (f", {vessel}" if vessel else ""),
                "description": "\n".join([
                    f"NFPA 68 deflagration venting{on} — the vessel is indoors, so this is "
                    "a FLAMELESS vent: a standard panel cannot discharge inside a building",
                    f'{flam["model"]}, with its breaking-signal sensor included',
                    "Sized and certified by the vent manufacturer against the dust hazard "
                    "analysis (Kst, Pmax, vessel volume and the design reduced pressure)",
                    "A flameless selection also takes more panels than a domed one — on "
                    f'the one MCE job where both were calculated it was '
                    f'{flam["flameless_panels"]} flameless against {flam["domed_panels"]} '
                    "domed",
                    "Price on request — a flameless assembly is an order of magnitude "
                    "above a domed panel, and MCE has never bought one",
                    _vendor.VENT_INSTALL_RULE,
                ])}

    panel = _vendor.vent_panel(size)
    key, model, sell, cost, date, source, size_text, relief = panel
    relief_text = f", {relief:g} ft² relief area" if relief else ""
    menu = _vendor.vent_panel_menu()
    lines = [
        f"NFPA 68 deflagration venting{on} — {size_text} domed vent panel with its "
        f"mounting frame{relief_text}",
    ] + _vendor.VENT_PANEL_SPEC + [
        "PRICED PER PANEL. How many panels comes from the vent manufacturer's "
        "calculation against the dust hazard analysis — comparable MCE vessels have "
        f'taken {" or ".join(counts)} panels',
    ]
    if len(menu) > 1:
        lines.append("Panel sizes MCE has current pricing for: "
                     + "; ".join(f"{text} at {money(price)}" for text, price in menu))
    lines += [
        ("Vents outdoors through an exterior wall, which is what a standard domed "
         "panel requires" if indoors is False else
         "Vents outdoors through the wall — an indoor vessel with no wall to vent "
         "through needs a flameless panel instead, quoted on request"),
        _vendor.VENT_INSTALL_RULE,
    ]
    return {"ref": _ref(options), "quantity": quantity,
            "unitPrice": round(sell, 2), "sku": model, "budgetPrice": True,
            "name": f"Explosion vent panel — {size_text}"
                    + (f", {vessel}" if vessel else ""),
            "description": "\n".join(lines)}


def adaptor_option(options, quantity=1, vessel=None):
    """The fabricated section the panel actually bolts to. MCE steel, unpriced."""
    on = f" under the {vessel}" if vessel else " under the filter"
    return {"ref": _ref(options), "quantity": quantity, "needsPrice": True,
            "name": "Explosion vent adaptor section and vent duct",
            "description": "\n".join(
                [f"MCE-fabricated adaptor section{on}, so the vent panel has the flat "
                 "unobstructed wall it needs"]
                + _vendor.VENT_ADAPTOR_SCOPE[1:]
                + ["Price from the fabrication estimate — sized once the vent panel and "
                   "the wall penetration are fixed"])}


def switch_option(options, quantity=1):
    """Burst indicator sensor, per panel, separate from the vent — as MCE buys it."""
    sell, cost, date, source, spec = _vendor.vent_sensor()
    return {"ref": _ref(options), "quantity": quantity, "unitPrice": round(sell, 2),
            "budgetPrice": True,
            "name": "Explosion vent burst indicator sensor",
            "description": "\n".join([
                spec,
                "Dry contact out for the plant to shut the system down on a vent event",
                "PRICED PER PANEL, and quoted separately from the vent because it is "
                "usually specified by the plant's controls scope rather than with the "
                "vessel",
                "Wiring, interlock and shutdown logic by others",
            ])}


def duct_isolation_option(options, quantity=1):
    """Flap valves, the UL control panel and the level sensors, as one option.

    They are bought together and only work together: the valves carry the shutdown
    sensors, the panel turns those into a plant shutdown, and the level sensors catch
    a valve buried in dust. Splitting them would offer a customer half a system.
    """
    parts = [_vendor.protection_item(k) for k in ("flap", "control", "level")]
    if any(p is None for p in parts):
        return None
    total = sum(sell * qty for _n, sell, _c, qty, *_r in parts)
    lines = []
    for name, sell, _cost, qty, _date, _source, desc in parts:
        lines.append(f"{qty} × {name} — {money(sell)} each")
        lines.append("   " + desc)
    lines.append("Priced as the arrangement MCE has quoted: two flap valves, one "
                 "control panel and two level sensors. The valve size follows the duct")
    lines.append("Wiring and interlock to the plant's own shutdown by others")
    return {"ref": _ref(options), "quantity": quantity, "unitPrice": round(total, 2),
            "budgetPrice": True,
            "name": "NFPA 69 duct isolation and shutdown — flap valves, control panel "
                    "and level sensors",
            "description": "\n".join(lines)}


def protection(options, quantity=1, material=None, vessel=None, replacing=None,
               indoors=None, size=None):
    """(options added, open items) for a combustible-dust job."""
    added, open_items = [], [
        "Combustible dust was stated. Nothing here sizes a protection package: the dust "
        "hazard analysis sets Kst and Pmax, and those set the vent area, the panel count "
        "and the isolation. Get the DHA figures, or a tested sample, before release.",
    ]

    def add(option):
        if option:
            options.append(option)
            added.append(option)

    iso = isolation_option(options, quantity=quantity, replacing=replacing)
    add(iso)
    if iso and replacing:
        open_items.append(
            f'The certified valve is quoted as a 10" and the {replacing} in the scope '
            f'above is larger, so it prices BELOW the standard airlock. Do not read that '
            "as a credit — settle the valve size against the duty before this goes out.")
    vent = vent_option(options, quantity=quantity, vessel=vessel, indoors=indoors,
                       size=size)
    add(vent)
    add(adaptor_option(options, quantity=quantity, vessel=vessel))
    add(switch_option(options, quantity=quantity))
    add(duct_isolation_option(options, quantity=quantity))

    pkg = _vendor.NFPA_PACKAGE_ON_RECORD
    open_items.append(
        f'Protection priced from {_vendor.EXPLOSION_VENT_VENDOR} estimate '
        f'{pkg["estimate"]} ({pkg["date"]}) — the complete {pkg["standard"]} package for '
        f'a {pkg["job"]}, {money(pkg["subtotal"])} less a '
        f'{pkg["discount"]:.0%} OEM discount = {money(pkg["total"])} cost, marked up at '
        f'MCE\'s buy-out divisor {_vendor.BUYOUT_DIVISOR:g}. {pkg["terms"]}.')

    if indoors is True:
        flam = _vendor.FLAMELESS_ON_RECORD
        open_items.append(
            "Vessel is indoors, so the vent has to be flameless and MCE has never bought "
            f'one. On {flam["quote"]} Boss quoted its own distributor '
            f'{flam["flameless_panels"]} flameless assemblies at '
            f'{money(flam["flameless_each_distributor"])} each — '
            f'{money(flam["flameless_total_distributor"])} against '
            f'{money(flam["domed_total_distributor"])} for {flam["domed_panels"]} domed. '
            "That is distributor pricing, not MCE's cost, so the option carries no "
            "number. Get a quote before it goes out with one.")
    else:
        key, model, sell, cost, date, source, size_text, _relief = _vendor.vent_panel(size)
        open_items.append(
            f"Vent panel priced per panel: {size_text} at {money(cost)} cost "
            f"({source}, {date}) ÷ {_vendor.BUYOUT_DIVISOR:g} = {money(sell)}. Panel "
            "price does not scale with area — each size is priced from its own quote — "
            "and the COUNT is the vent manufacturer's, not MCE's.")
        if indoors is None:
            open_items.append(
                "Nobody said whether the vessel is indoors. Outdoors takes the domed "
                "panel quoted; indoors with no wall to vent through takes a flameless "
                "vent, which is an order of magnitude more and is not on file.")

    open_items.append(
        "Burst sensor and the duct isolation package are optioned out rather than in "
        "scope: MCE has twice been asked to drop the sensor, and the flap valves, "
        "control panel and level sensors belong to the plant's controls scope.")
    open_items.append(
        "Vent adaptor section is unpriced: it is MCE's own fabrication and there is no "
        "cost basis for one yet. " + _vendor.VENT_ADAPTOR_SCOPE[0])
    open_items.append(
        f"Vent basis — {_vendor.EXPLOSION_VENT_VENDOR} "
        f"({_vendor.EXPLOSION_VENT_CONTACT}): "
        + "; ".join(_vendor.vent_selection_lines()) + ".")

    if not kst_reference(material):
        open_items.append(
            f'No dust figures on record for {material or "this product"} — MCE has them '
            f'only for {", ".join(sorted(_vendor.DUST_ON_RECORD))}. The vent supplier '
            "needs a Kst and Pmax from the customer's DHA before it can size anything.")
    return added, open_items
