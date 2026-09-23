#!/usr/bin/env python3
"""Hammer pattern — a faithful port of MCE's own calculator.

Source of truth: renderer/tools/hammer-pattern-calculator.html (served whole at
/tools/hammer-pattern), itself transcribed from "HAMMER PATTERN for MODEL
38-44-40" Rev A, 7/2/26. The reference BOM and the rotor constants are extracted
verbatim into _data.py.

    hammers = motor HP / HP per hammer, rounded DOWN to an even number
    rows    = 8 (high-fat, fibrous, fine) or 4 (inside coarse, outside fine)
    balance = opposite rows carry equal counts; pairs differ by at most one

HP per hammer is only on record for corn — 1.5 standard, 1.75 alternate. The
calculator takes any number, but MCE's note is explicit that other materials come
from engineering rather than a guess, so nothing here supplies one. That is why
this calculator is a shop/parts tool and does not feed quote line items.
"""
import math

from ._data import (HP_COLLAR_W, HP_COLLARS_PER_PIN, HP_REF_BOM, HP_TOTAL_PINS)
from ._fmt import fixed, jsround, num

REFERENCE = "Model 38/44-40 Rev A (7/2/26) — 132 hammers, 8 rows, 17/17/16/16"
CORN_HP_PER_HAMMER = (1.5, 1.75)   # the only values MCE has on record


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def distribute(total, rows):
    """Per-pair hammer counts. Total split over rows/2 opposite pairs as evenly
    as possible, so opposite rows match and pairs differ by at most one."""
    pairs = rows // 2
    half = total // 2
    base, extra = divmod(half, pairs)
    return [base + 1 if i < extra else base for i in range(pairs)]


def interleave(pair_counts):
    """Order the pairs the way the drawing lays them out — 17, 16, 17, 16 —
    so equal counts sit opposite each other in the display."""
    desc = sorted(pair_counts, reverse=True)
    n = len(desc)
    return [desc[i // 2 if i % 2 == 0 else n - 1 - i // 2] for i in range(n)]


def size(f):
    hp = _num(f.get("motorHp"))
    hph = _num(f.get("hpPerHammer"), 1.5)
    rows = 4 if str(f.get("rows")) == "4" else 8
    pin_len = _num(f.get("pinLength"), 40)
    thickness = _num(f.get("thickness"), 0.25)
    allowance = max(0.0, _num(f.get("pinAllowance"), 7.5))
    override_raw = f.get("countOverride")
    override = _num(override_raw) if str(override_raw or "").strip() else 0.0

    valid = hp > 0 and hph > 0
    if not valid and override <= 0:
        return {"error": "Motor HP and HP per hammer are required."}
    if thickness <= 0:
        return {"error": "Hammer thickness must be greater than zero."}

    warnings, outputs = [], []

    # Rounded DOWN to even — the 38/44-40 drawing's own convention
    # (200 HP / 1.5 = 133.3 -> 132). Balance requires an even total.
    raw = hp / hph if valid else None
    odd = False
    if override > 0:
        total = max(2, jsround(override))
        manual = True
        odd = total % 2 != 0
        adjusted = override if total != override else None
    else:
        total = math.floor(raw / 2) * 2
        total = max(total, rows)       # at least one hammer per loaded row
        manual, adjusted = False, None

    if valid:
        formula = (f"{num(hp)} HP ÷ {hph:g} HP/hammer = {fixed(raw, 1)} → {total} hammers"
                   + (f" (override — adjusted from {adjusted:g})" if adjusted is not None
                      else " (override)" if manual
                      else " (rounded down to even for balance)"))
    else:
        formula = (f"{total} hammers (override"
                   + (f" — adjusted from {adjusted:g}" if adjusted is not None else "")
                   + " — enter motor HP to check loading)")

    # An odd override cannot balance; lay out the nearest even count.
    dist_total = total - 1 if odd else total
    per_pair = interleave(distribute(dist_total, rows))
    labels = (["Rows 1 & 5", "Rows 2 & 6", "Rows 3 & 7", "Rows 4 & 8"] if rows == 8
              else ["Rows A & C (opposite)", "Rows B & D (opposite)"])

    # The original's own three note lines, verbatim — the differential test diffs
    # them against the hosted calculator, so they stay worded exactly as MCE wrote
    # them. The rep-facing `warnings` list is derived from them below.
    balance_notes = []
    if odd:
        balance_notes.append(f"\u26a0 {total} hammers can't balance (odd count) — layout "
                             f"shown for {dist_total}; add or drop one hammer.")
    if manual and dist_total < rows:
        balance_notes.append("\u26a0 Fewer hammers than loaded rows — some rows run empty; "
                             "consider a " + ("4-row pattern." if rows == 8 else
                                              "smaller frame."))
    balance_note = " ".join(balance_notes)

    count_notes = []
    if valid:
        actual = hp / total
        if actual > 1.8 and hph in CORN_HP_PER_HAMMER:
            count_notes.append(f"{fixed(actual, 2)} HP/hammer runs hot for corn — consider more "
                               "hammers.")
        if total == 132 and rows == 8:
            count_notes.append("Matches the 38/44-40 reference pattern (132 hammers).")
    count_note = " ".join(count_notes)

    dist_detail = (f"{rows}-row pattern · {rows} loaded pins of {HP_TOTAL_PINS} · "
                   "opposite rows equal for balance")

    warnings += [n.lstrip("\u26a0 ") for n in balance_notes]
    if valid and hph not in CORN_HP_PER_HAMMER:
        warnings.append(f"{hph:g} HP/hammer is not one of MCE's recorded corn values "
                        "(1.5 standard, 1.75 alternate). Confirm the basis with "
                        "engineering before this pattern is cut.")
    if count_notes and count_notes[0].endswith("consider more hammers."):
        warnings.append(count_notes[0])

    # Pin stack check — against USABLE length (pin minus the ends in the rotor plates).
    usable = pin_len - allowance
    max_per_row = max(per_pair)
    stack = max_per_row * thickness + HP_COLLARS_PER_PIN * HP_COLLAR_W
    spacer_len = usable - stack
    spacer_total = sum(2 * max(0.0, usable - (c * thickness + HP_COLLARS_PER_PIN * HP_COLLAR_W))
                       for c in per_pair)

    if spacer_len < 0:
        stack_note = (
            f'\u26a0 {max_per_row} hammers × {thickness:g}" + collars = {fixed(stack, 2)}" exceeds '
            f'the {fixed(usable, 1)}" usable stack length ({pin_len:g}" pin − {allowance:g}" end '
            "allowance) — this pattern physically won't fit. Fewer hammers per row (more "
            "rows / bigger frame) needed.")
        stack_ok = False
    elif spacer_len < max_per_row * 0.25:
        stack_note = (
            f'Tight: only {fixed(spacer_len, 2)}" of spacer room around {max_per_row} hammers in '
            f'the {fixed(usable, 1)}" usable stack — verify the stagger layout fits before '
            "committing.")
        stack_ok = False
    else:
        stack_note = ("Spacer widths per row come from the stagger layout (see the 38/44-40 "
                      "drawing) so hammer paths wash the full screen width — this tool sizes "
                      "the totals, engineering picks the widths.")
        stack_ok = True
    if not stack_ok:
        warnings.append(stack_note.lstrip("\u26a0 "))

    outputs = [
        {"label": "Hammers", "value": f"{num(total)}", "headline": True},
        {"label": "Balance", "value": ("Override · Odd Count" if odd else
                                       "Override" if manual else "Balanced")},
        {"label": "Actual HP / hammer",
         "value": f"{fixed(hp / total, 2)} HP" if valid else "—"},
        {"label": "Pattern capacity @ 1.5–1.75",
         "value": f"{num(jsround(total * 1.5))}–{num(jsround(total * 1.75))} HP"},
        {"label": "Pattern", "value": dist_detail},
    ]
    outputs += [{"label": labels[i], "value": f"{c} per row"} for i, c in enumerate(per_pair)]
    outputs += [
        {"label": "Hammers / loaded pin (max)", "value": f'{max_per_row} × {thickness:g}"'},
        {"label": "Hammer + collar stack", "value": f'{fixed(stack, 2)}"'},
        {"label": "Left for spacers", "value": f'{fixed(spacer_len, 2)}" / pin'},
        {"label": "Spacer fill (all loaded pins)", "value": f'{fixed(spacer_total, 1)}"'},
    ]
    if count_note:
        outputs.append({"label": "Loading", "value": count_note})
    outputs.append({"label": "Stack", "value": stack_note})

    bom = [
        (f'1/4" × 2-1/2" × 8-1/4" swing hammer'
         + (f' (thickness {thickness:g}")' if thickness != 0.25 else ""),
         f"{dist_total} (balanced from {total})" if odd else str(dist_total)),
        (f'Hammer pin × {pin_len:g}" long', str(HP_TOTAL_PINS)),
        ('Squeeze collar (1/2" wide)', str(rows * HP_COLLARS_PER_PIN)),
        ('Spacer stock, 1-9/32" tall (total width to cut per stagger drawing)',
         f'≈{fixed(spacer_total, 0)}"'),
    ]

    return {"calculator": "Hammer Pattern", "outputs": outputs, "warnings": warnings,
            "lines": [], "total": 0.0, "formula": formula,
            "hammers": total, "rows": rows, "perPair": per_pair,
            "distTotal": dist_total, "maxPerRow": max_per_row,
            "stack": stack, "spacerLen": spacer_len, "spacerTotal": spacer_total,
            "pill": ("Override · Odd Count" if odd else "Override" if manual
                     else "Balanced"),
            "actualHph": f"{fixed(hp / total, 2)} HP" if valid else "—",
            "capacityRange": f"{num(jsround(total * 1.5))}–{num(jsround(total * 1.75))} HP",
            "countNote": count_note, "balanceNote": balance_note,
            "stackNote": stack_note, "distDetail": dist_detail,
            "bom": [{"item": i, "qty": q} for i, q in bom],
            "referenceBom": [{"item": i, "qty": q} for i, q in HP_REF_BOM]}
