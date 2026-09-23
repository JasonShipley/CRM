"""Number formatting that matches the calculators' JavaScript.

JS `Number.toLocaleString` and `Math.round` round half away from zero; Python's
`format` and `round` round half to even. On a value like 562.5 that is a visible
one-unit difference between the hosted calculator and the quote builder, so all
displayed numbers go through here.
"""
import math
from decimal import ROUND_HALF_UP, Decimal


def jsround(x):
    """JS Math.round: half up."""
    return math.floor(x + 0.5)


def num(value, places=0):
    """JS toLocaleString(en-US) with fixed fraction digits."""
    q = Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return f"{q:,.{places}f}"


def fixed(value, places=0):
    """JS Number.toFixed: half away from zero, no thousands separator."""
    q = Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return f"{q:.{places}f}"


def locale(value):
    """Bare JS `Number.toLocaleString("en-US")` — grouped, and up to three
    fraction digits with trailing zeros dropped. `num()` fixes the digit count;
    this one matches a calculator that passes no options at all."""
    q = Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    q = q.normalize()
    if -1 < q < 1 and q != 0:
        out = f"{q:,f}"
    else:
        out = f"{q:,f}" if q == q.to_integral_value() else f"{q:,f}"
    if "." in out:
        out = out.rstrip("0").rstrip(".")
    return out or "0"


def money(value, places=0):
    v = Decimal(str(value))
    return ("−$" if v < 0 else "$") + num(abs(v), places)
