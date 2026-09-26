#!/usr/bin/env python3
"""Combustible dust: what MCE adds to an air system, and what it cannot size.

Most of what MCE grinds is a combustible dust — feed, grain, wood, pet food, DDGs.
When the rep says so, two things have to appear on the proposal and neither is a
number this project can invent:

  isolation    NFPA 69 wants the duct back to the process isolated. MCE's certified
               rotary valves do that job (flex-tip rotor, certified to NFPA 69
               12.2.4.3.6) and there are real sell prices on file for two of them —
               but they are different sizes and nothing here sizes a valve, so they
               go out as a priced RANGE with the selection called out.

  deflagration NFPA 68 venting. Vent area comes from Kst, Pmax, the vessel volume
               and the design Pred — a dust hazard analysis, not a calculator. MCE
               buys these sized and quoted by High Tech Duct Werks, so the option
               carries the engineering basis from the job they did it on (Nix Forest
               Industries) and no price at all. Burst indicator switches come off
               that as their own option, which is how Nix bought it.

Nothing in here prices a protection package. It states the basis, offers the
options, and puts the missing quotes on the open-items list where a rep will see
them before the proposal goes out.
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
    """A Kst MCE has actually worked to for this material, or None.

    Reference only — it is what a previous job's tested sample came back at, not a
    value to design to. A guessed Kst is a guessed vent area.
    """
    want = str(material or "").lower()
    for name, kst in _vendor.KST_ON_RECORD.items():
        if name in want:
            return name, kst
    return None


def design_basis(material=None):
    """The design-basis row a combustible-dust job carries."""
    notes = [DHA_NOTE]
    ref = kst_reference(material)
    if ref:
        name, kst = ref
        p = _vendor.EXPLOSION_VENT_PRECEDENT
        notes.append(f'For reference, MCE\'s {name} dust on the {p["job"]} job tested at '
                     f'Kst {kst} bar·m/s, Pmax {p["pmax"]} bar — this product still needs '
                     "its own sample.")
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
            (f"Takes the place of the standard drop-through airlock in the scope above"
             if replacing else "Mounts under the collector hopper"),
            f"Indicative {money(lo)} to {money(hi)} depending on the size selected",
            "MCE to confirm the size against the actual duty and firm the price on a "
            "current vendor quote",
        ])}


def vent_option(options, quantity=1, vessel=None, indoors=None):
    """Deflagration venting, unpriced — the vendor sizes and quotes it.

    `indoors` None means nobody said. It matters: a standard panel has to discharge
    outdoors, and an indoor vessel needs a flameless vent instead, which is a
    different price. Left unsaid, the option says both rather than picking one.
    """
    on = f" on the {vessel}" if vessel else ""
    lines = [
        f"NFPA 68 deflagration venting{on} — vent panel, mounting frame and the vent "
        "duct through to atmosphere with a rain hood",
        "Sized and certified by the vent manufacturer against the dust hazard analysis "
        "(Kst, Pmax, vessel volume and the design reduced pressure)",
    ]
    if indoors is True:
        lines.append("Vessel is indoors, so this is a FLAMELESS vent — a standard panel "
                     "cannot discharge inside a building")
    elif indoors is False:
        lines.append("Vessel vents outdoors through an exterior wall — a standard panel, "
                     "not a flameless vent")
    else:
        lines.append("A vessel that vents outdoors takes a standard panel; one that has to "
                     "vent inside a building takes a flameless vent, which prices "
                     "differently — confirm which before this is firmed")
    lines.append("Price on request — quoted by the vent manufacturer once the DHA figures "
                 "and the vessel arrangement are fixed")
    return {"ref": _ref(options), "quantity": quantity, "needsPrice": True,
            "name": "Explosion vent" + (f" — {vessel}" if vessel else ""),
            "description": "\n".join(lines)}


def switch_option(options, quantity=1):
    """Burst indicator switches, separate from the vent — the way Nix bought it."""
    return {"ref": _ref(options), "quantity": quantity, "needsPrice": True,
            "name": "Explosion vent burst indicator switch",
            "description": "\n".join([
                "Tether-mounted burst sensor on the vent panel, dry contact out for the "
                "plant to shut the system down on a vent event",
                "Optional on the vent above — quoted separately because it is usually "
                "specified by the plant's controls scope, not with the vessel",
                "Wiring, interlock and shutdown logic by others",
                "Price on request",
            ])}


def protection(options, quantity=1, material=None, vessel=None, replacing=None,
               indoors=None):
    """(options added, open items) for a combustible-dust job.

    `options` is the caller's list — the refs continue from it and the new options
    are appended to it, so one proposal has one A/B/C sequence.
    """
    added, open_items = [], [
        "Combustible dust was stated. Nothing in this proposal sizes a protection "
        "package: the dust hazard analysis sets Kst and Pmax, and those set the vent "
        "area and the isolation. Get the DHA figures, or a tested sample, before "
        "release.",
    ]

    isolation = isolation_option(options, quantity=quantity, replacing=replacing)
    if isolation:
        options.append(isolation)
        added.append(isolation)
        lo, hi, source = _vendor.certified_valve_range()
        open_items.append(
            f"Isolation offered as a certified rotary valve at an indicative {money(lo)}–"
            f"{money(hi)} (the two ATEX valves on {source}). Neither was sized against "
            "this duty and there is no airlock calculator, so it is an option with a "
            "range rather than a quoted line — get a firm vendor quote.")

    vent = vent_option(options, quantity=quantity, vessel=vessel, indoors=indoors)
    options.append(vent)
    added.append(vent)
    switches = switch_option(options, quantity=quantity)
    options.append(switches)
    added.append(switches)

    p = _vendor.EXPLOSION_VENT_PRECEDENT
    open_items.append(
        f"Explosion vent and burst switch are unpriced. MCE buys these from "
        f'{_vendor.EXPLOSION_VENT_VENDOR} ({_vendor.EXPLOSION_VENT_CONTACT}) — get a '
        f'quote the way {p["quote"]} was done for {p["job"]}. That basis: '
        + "; ".join(_vendor.explosion_vent_basis()[2:]) + ".")
    ref = kst_reference(material)
    if not ref:
        open_items.append(
            f'No Kst on record for {material or "this product"} — MCE has tested figures '
            f'only for {", ".join(sorted(_vendor.KST_ON_RECORD))}. The vent supplier needs '
            "a Kst and Pmax from the customer's DHA before it can size anything.")
    return added, open_items
