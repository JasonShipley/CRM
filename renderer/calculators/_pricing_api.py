"""The pricing basis, machine-readable — one function, two callers.

`GET /api/pricing` (builder.py) and the bundled quote-builder skill's
`mce.py pricing` both return this, so a chat working offline and the server
answer the same question with the same numbers.
"""
from . import _pricing, _vendor
from ._book_inputs import MILL_OPTIONS
from ._data import FEEDER_PRICING, MILL_PRICING


def payload():
    return {
        "basis": _pricing.BLISS_BASIS,
        "factors": {k: dict(v) for k, v in _pricing.FACTORS.items()},
        "escalations": _pricing.ESCALATIONS,
        "known_divergence": _pricing.KNOWN_DIVERGENCE,
        "unpriced": _pricing.UNPRICED,
        "rules": {
            "buy_out": f"vendor cost ÷ {_vendor.BUYOUT_DIVISOR:g}",
            "fabrication": f"cost × {1 + _vendor.FAB_CONTINGENCY:g} ÷ "
                           f"{1 - _vendor.FAB_MARGIN:g}",
            "parts": f"cost ÷ {_vendor.PARTS_DIVISOR:g}",
            "fan_with_filter": f"AirPro cost × {_vendor.FAN_MARKUP:g}",
        },
        "models": {"screw": _vendor.SCREW_MODEL},
        "mill_price": {m: _pricing.mill_price(m) for m in sorted(MILL_PRICING)},
        "mill_options": {m: {k: _pricing.mill_option(m, k)
                             for k in sorted(MILL_OPTIONS.get(m, {}))}
                         for m in sorted(MILL_OPTIONS)},
        "feeder_price": {
            f'{d}-{cup}-{rows}': _pricing.feeder_price(d, cup, rows)
            for d in (10, 14) for cup in ("nylon", "ss", "tt")
            for rows in FEEDER_PRICING["rows"]},
    }
