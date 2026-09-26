#!/usr/bin/env python3
"""Combustible dust: what MCE adds to an air system, and what it cannot size.

Most of what MCE grinds is a combustible dust — feed, grain, wood, pet food, DDGs.
When the rep says so, three things have to appear on the proposal, and each one is
priced from what MCE has in writing or not priced at all:

  isolation    NFPA 69 wants the duct back to the process isolated. MCE's certified
               rotary valves do that job (flex-tip rotor, certified to NFPA 69
               12.2.4.3.6) and there are real sell prices on file for two of them —
               but they are different sizes and nothing here sizes a valve, so they
               go out as a priced RANGE with the selection called out.

  venting      NFPA 68 deflagration venting, bought from High Tech Duct Werks. MCE
               has a real price for the domed panel and for the burst switch, so
               those are quoted PER PANEL at real money. How many panels, and what
               size, is the vendor's calculation against a dust hazard analysis —
               three jobs on record took one, two and two panels, and the option
               says so rather than guessing this job's count.

  the adaptor  A vent panel needs flat unobstructed housing wall. A bin vent bolted
               straight onto a plenum chamber does not offer one, so MCE fabricates
               a spool below the bin vent, drilled for the panel, ducted through the
               wall with a rain hood. That is MCE's own steel and there is no cost
               basis for it yet, so it goes out unpriced.

Flameless venting is what an indoor vessel with nowhere to vent needs. On the one
job where both were calculated the flameless selection took three panels against
two domed, MCE did not buy it, and there is no flameless price on file — so an
indoor vessel gets the requirement stated and no number.
"""
from . import _vendor
from ._fmt import money

# NFPA 652 makes the dust hazard analysis the owner's duty, and it is the DHA that
# sets everything else. Every note below leads back to it rather than around it.
DHA_NOTE = ("Treated as a combustible dust: protection is per NFPA 652/654 and NFPA 68/69, "
            "and the dust hazard analysis — Kst and Pmax from a tested sample of the actual "
            "product — sets the vent area and the isolation. MCE has not assumed either.")


def _ref(options):
    """The next option letter, so these slot into a list the caller is building."""
    return chr(ord("A") + len(options))


def kst_reference(material):
    """(name, record) for a dust MCE has actually worked to, or None.

    Reference only — it is what a previous job's figures were, not a value to design
    to. A guessed Kst is a guessed vent area.
    """
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
    """Certified rotary valve, as an unpriced option carrying the real range."""
    found = _vendor.certified_valve_range()
    if not found:
        return None
    lo, hi, _source = found
    instead = f" in lieu of the standard {replacing}" if replacing else ""
    return {
        "ref": _ref(options), "quantity": quantity, "needsPrice": True,
        "name": f"NFPA 69 isolation — ATEX certified rotary valve{instead}",
        "description": "\n".join([
            "Certified rotary valve rated to 40 in WG differential, cast iron with an "
            "8-vane polyurethane flex-tip rotor, flame-passage certified to NFPA 69 "
            "12.2.4.3.6",
            "Isolates the duct back to the process, which a standard drop-through valve "
            "is not certified to do",
            ("Takes the place of the standard drop-through airlock in the scope above"
             if replacing else "Mounts under the collector hopper"),
            f"Indicative {money(lo)} to {money(hi)} depending on the size selected",
            "MCE to confirm the size against the actual duty and firm the price on a "
            "current vendor quote",
        ])}


def vent_option(options, quantity=1, vessel=None, indoors=None):
    """Deflagration venting, priced per panel where MCE has a panel price.

    `indoors` None means nobody said. It matters twice over: a standard panel has to
    discharge outdoors, and an indoor vessel with no wall to vent through needs a
    flameless panel, which MCE has no price for. So indoors=True is unpriced and
    says why, while anything else quotes the domed panel MCE actually buys.
    """
    on = f" on the {vessel}" if vessel else ""
    counts = sorted({s["selection"].split(" x ")[0].strip()
                     for s in _vendor.VENT_SELECTIONS})
    panel = _vendor.vent_panel()

    if indoors is True:
        flam = _vendor.FLAMELESS_ON_RECORD
        return {"ref": _ref(options), "quantity": quantity, "needsPrice": True,
                "name": "Explosion vent — flameless" + (f", {vessel}" if vessel else ""),
                "description": "\n".join([
                    f"NFPA 68 deflagration venting{on} — the vessel is indoors, so this is "
                    "a FLAMELESS vent: a standard panel cannot discharge inside a building",
                    "Sized and certified by the vent manufacturer against the dust hazard "
                    "analysis (Kst, Pmax, vessel volume and the design reduced pressure)",
                    f"A flameless selection takes more panels than a domed one — on the "
                    f'one MCE job where both were calculated for the same vessel it was '
                    f'{flam["flameless_panels"]} flameless against {flam["domed_panels"]} '
                    "domed",
                    "Price on request — MCE has no flameless price on file, and it is "
                    "materially more than a domed panel",
                    _vendor.VENT_INSTALL_RULE,
                ])}

    key, model, sell, cost, date, source, size, relief = panel
    lines = [
        f"NFPA 68 deflagration venting{on} — {size} domed vent panel with its mounting "
        f"frame, {relief:g} ft² relief area",
    ] + _vendor.VENT_PANEL_SPEC + [
        f"PRICED PER PANEL. How many panels, and what size, comes from the vent "
        f"manufacturer's calculation against the dust hazard analysis — comparable MCE "
        f'vessels have taken {" or ".join(counts)} panels',
        ("Vents outdoors through an exterior wall, which is what a standard domed "
         "panel requires" if indoors is False else
         "Vents outdoors through the wall — an indoor vessel with no wall to vent "
         "through needs a flameless panel instead, quoted on request"),
        _vendor.VENT_INSTALL_RULE,
    ]
    return {"ref": _ref(options), "quantity": quantity,
            "unitPrice": round(sell, 2), "sku": model, "budgetPrice": True,
            "name": f"Explosion vent panel — {size}" + (f", {vessel}" if vessel else ""),
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
    """Burst indicator switch, per panel, separate from the vent — as Nix bought it."""
    sell, cost, date, source, spec = _vendor.vent_sensor()
    return {"ref": _ref(options), "quantity": quantity, "unitPrice": round(sell, 2),
            "budgetPrice": True,
            "name": "Explosion vent burst indicator switch",
            "description": "\n".join([
                spec,
                "Dry contact out for the plant to shut the system down on a vent event",
                "PRICED PER PANEL, and quoted separately from the vent because it is "
                "usually specified by the plant's controls scope rather than with the "
                "vessel",
                "Wiring, interlock and shutdown logic by others",
            ])}


def protection(options, quantity=1, material=None, vessel=None, replacing=None,
               indoors=None):
    """(options added, open items) for a combustible-dust job.

    `options` is the caller's list — the refs continue from it and the new options
    are appended to it, so one proposal has one A/B/C sequence.
    """
    added, open_items = [], [
        "Combustible dust was stated. Nothing here sizes a protection package: the dust "
        "hazard analysis sets Kst and Pmax, and those set the vent area and the "
        "isolation. Get the DHA figures, or a tested sample, before release.",
    ]

    def add(option):
        if option:
            options.append(option)
            added.append(option)

    isolation = isolation_option(options, quantity=quantity, replacing=replacing)
    if isolation:
        add(isolation)
        lo, hi, source = _vendor.certified_valve_range()
        open_items.append(
            f"Isolation offered as a certified rotary valve at an indicative {money(lo)}–"
            f"{money(hi)} (the two ATEX valves on {source}). Neither was sized against "
            "this duty and there is no airlock calculator, so it is an option with a "
            "range rather than a quoted line — get a firm vendor quote.")

    vent = vent_option(options, quantity=quantity, vessel=vessel, indoors=indoors)
    add(vent)
    add(adaptor_option(options, quantity=quantity, vessel=vessel))
    add(switch_option(options, quantity=quantity))

    if indoors is True:
        open_items.append(
            "Vessel is indoors, so the vent has to be flameless and MCE has no flameless "
            "price on file. On the one job where both were calculated the flameless "
            f'selection took {_vendor.FLAMELESS_ON_RECORD["flameless_panels"]} panels '
            f'against {_vendor.FLAMELESS_ON_RECORD["domed_panels"]} domed, and MCE did '
            "not buy it. Get a current quote before this option goes out with a number.")
    else:
        key, model, sell, cost, date, source, size, relief = _vendor.vent_panel()
        open_items.append(
            f"Vent panel priced per panel: {size} {model} at {money(cost)} cost "
            f"({source}, {date}), marked up at MCE's buy-out divisor "
            f"{_vendor.BUYOUT_DIVISOR:g} to {money(sell)}. The PANEL COUNT is not sized "
            "here — the vent manufacturer sets it off the DHA and the vessel volume.")
        if indoors is None:
            open_items.append(
                "Nobody said whether the vessel is indoors. Outdoors takes the domed "
                "panel quoted; indoors with no wall to vent through takes a flameless "
                "panel, which prices materially higher and is not on file.")

    sell_sw, cost_sw, date_sw, source_sw, _spec = _vendor.vent_sensor()
    open_items.append(
        f"Burst switch priced at {money(cost_sw)} cost per panel ({source_sw}, "
        f"{date_sw}) ÷ {_vendor.BUYOUT_DIVISOR:g}. It is optioned out because MCE has "
        "twice been asked to drop it — it belongs to the plant's controls scope.")
    open_items.append(
        "Vent adaptor section is unpriced: it is MCE's own fabrication and there is no "
        "cost basis for one yet. " + _vendor.VENT_ADAPTOR_SCOPE[0])
    open_items.append(
        f"Vent basis — {_vendor.EXPLOSION_VENT_VENDOR} "
        f"({_vendor.EXPLOSION_VENT_CONTACT}): "
        + "; ".join(_vendor.vent_selection_lines()) + ".")

    ref = kst_reference(material)
    if not ref:
        open_items.append(
            f'No dust figures on record for {material or "this product"} — MCE has them '
            f'only for {", ".join(sorted(_vendor.DUST_ON_RECORD))}. The vent supplier '
            "needs a Kst and Pmax from the customer's DHA before it can size anything.")
    return added, open_items
