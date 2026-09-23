#!/usr/bin/env python3
"""Re-fit the screw conveyor cost model from MCE's SCC quotations.

MCE never buys the same screw twice, so there is no price list to look up. This
fits cost = BASE + PER_IN x dia + PER_IN_FT x dia x length over every carbon-steel
quote on file, after escalating each to a common date, and prints the
coefficients to paste into calculators/_vendor.py.

    cd renderer && python3 tests/fit_screw_model.py

Run it whenever a new SCC quote lands: add the quote to SCREW_QUOTES in
_vendor.py first, then re-fit and paste the result back.
"""
import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from calculators import _vendor as v  # noqa: E402


def escalate(cost, date, to, rate):
    years = (to - datetime.date.fromisoformat(date)).days / 365.25
    return cost * (1 + rate) ** years


def lstsq(rows):
    """cost = c0 + c1*dia + c2*dia*length, by normal equations."""
    X = [[1.0, d, d * f] for d, f, _ in rows]
    y = [c for _, _, c in rows]
    n = 3
    A = [[sum(X[k][i] * X[k][j] for k in range(len(X))) for j in range(n)] for i in range(n)]
    b = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(n)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[piv] = A[piv], A[i]
        b[i], b[piv] = b[piv], b[i]
        for r in range(i + 1, n):
            f = A[r][i] / A[i][i]
            for c in range(i, n):
                A[r][c] -= f * A[i][c]
            b[r] -= f * b[i]
    out = [0.0] * n
    for i in reversed(range(n)):
        out[i] = (b[i] - sum(A[i][j] * out[j] for j in range(i + 1, n))) / A[i][i]
    return out


def main():
    ref = v.SCREW_MODEL_DATE
    rate = v.SCREW_ESCALATION
    carbon = [(dia, ft, escalate(cost, date, ref, rate))
              for q, date, dia, ft, mat, cost, note in v.SCREW_QUOTES if mat == "CS"]
    if len(carbon) < 4:
        print(f"Only {len(carbon)} carbon quotes — too few to fit three coefficients.")
        return 1

    base, per_in, per_in_ft = lstsq(carbon)
    print(f"Fitted on {len(carbon)} carbon-steel quotes, escalated to {ref} "
          f"at {rate:.1%}/yr:\n")
    print(f'    SCREW_MODEL = {{"base": {base:.1f}, "per_in": {per_in:.1f}, '
          f'"per_in_ft": {per_in_ft:.2f}}}\n')

    def model(d, f):
        return base + per_in * d + per_in_ft * d * f

    errs = []
    print(f"    {'quote':14} {'size':>12} {'model':>10} {'quoted':>10}  error")
    for q, date, dia, ft, mat, cost, note in v.SCREW_QUOTES:
        esc = escalate(cost, date, ref, rate)
        pred = model(dia, ft)
        err = (pred / esc - 1) * 100
        if mat == "CS":
            errs.append(abs(err))
        tag = "" if mat == "CS" else f"  ({mat}, excluded from the fit)"
        size = '%d" x %g ft' % (dia, ft)
        print(f"    {q:14} {size:>12} ${pred:>9,.0f} ${esc:>9,.0f}  "
              f"{err:+5.1f}%{tag}")
    print(f"\n    mean absolute error {sum(errs)/len(errs):.1f}%, worst {max(errs):.1f}%")

    live = [v.SCREW_MODEL["base"], v.SCREW_MODEL["per_in"], v.SCREW_MODEL["per_in_ft"]]
    drift = max(abs(a - b) for a, b in zip([base, per_in, per_in_ft], live))
    if drift > 1.0:
        print(f"\n    _vendor.py is out of date by up to {drift:,.1f} — paste the "
              "coefficients above into SCREW_MODEL.")
        return 1
    print("\n    _vendor.py matches this fit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
