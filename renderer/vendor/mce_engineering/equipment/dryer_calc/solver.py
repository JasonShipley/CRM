"""Small dependency-free numeric solvers (Brent root finder, damped Newton with a
finite-difference Jacobian). Pure Python so the engine runs anywhere the quote app runs.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence


class SolverError(RuntimeError):
    pass


def brent(f: Callable[[float], float], a: float, b: float, tol: float = 1e-10, maxiter: int = 200) -> float:
    """Brent's method on [a, b]; f(a) and f(b) must bracket a root."""
    fa, fb = f(a), f(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise SolverError(f"root not bracketed on [{a}, {b}]: f={fa:.4g}, {fb:.4g}")
    if abs(fa) < abs(fb):
        a, b, fa, fb = b, a, fb, fa
    c, fc, mflag, d = a, fa, True, 0.0
    for _ in range(maxiter):
        if fa != fc and fb != fc:
            s = (a * fb * fc / ((fa - fb) * (fa - fc)) + b * fa * fc / ((fb - fa) * (fb - fc))
                 + c * fa * fb / ((fc - fa) * (fc - fb)))
        else:
            s = b - fb * (b - a) / (fb - fa)
        cond = (not ((3 * a + b) / 4 < s < b or b < s < (3 * a + b) / 4)
                or (mflag and abs(s - b) >= abs(b - c) / 2)
                or (not mflag and abs(s - b) >= abs(c - d) / 2)
                or (mflag and abs(b - c) < tol) or (not mflag and abs(c - d) < tol))
        if cond:
            s, mflag = (a + b) / 2, True
        else:
            mflag = False
        fs = f(s)
        d, c, fc = c, b, fb
        if fa * fs < 0:
            b, fb = s, fs
        else:
            a, fa = s, fs
        if abs(fa) < abs(fb):
            a, b, fa, fb = b, a, fb, fa
        if fb == 0 or abs(b - a) < tol * max(1.0, abs(b)):
            return b
    raise SolverError("brent: no convergence")


def _solve_linear(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-300:
            raise SolverError("singular Jacobian")
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            fac = m[r][col] / m[col][col]
            for k in range(col, n + 1):
                m[r][k] -= fac * m[col][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][k] * x[k] for k in range(r + 1, n))) / m[r][r]
    return x


def newton(f: Callable[[Sequence[float]], list[float]], x0: Sequence[float], scale: Sequence[float],
           rtol: float = 1e-9, maxiter: int = 60) -> tuple[list[float], int, float]:
    """Damped Newton on a square system. `scale` gives each residual's magnitude, so
    convergence is |r_i| / scale_i < rtol for every equation. Returns (x, iterations, max scaled residual)."""
    x = list(x0)
    n = len(x)
    r = f(x)
    err = max(abs(ri) / si for ri, si in zip(r, scale))
    for it in range(1, maxiter + 1):
        if err < rtol:
            return x, it - 1, err
        jac = [[0.0] * n for _ in range(n)]
        for j in range(n):
            h = 1e-6 * max(abs(x[j]), 1.0)
            xp = list(x)
            xp[j] += h
            rp = f(xp)
            for i in range(n):
                jac[i][j] = (rp[i] - r[i]) / h
        dx = _solve_linear(jac, [-ri for ri in r])
        step = 1.0
        for _ in range(30):
            xn = [xi + step * di for xi, di in zip(x, dx)]
            rn = f(xn)
            errn = max(abs(ri) / si for ri, si in zip(rn, scale))
            if math.isfinite(errn) and errn < err * (1 - 1e-4 * step) or errn < rtol:
                break
            step /= 2
        x, r, err = xn, rn, errn
    if err < rtol:
        return x, maxiter, err
    raise SolverError(f"newton: no convergence (scaled residual {err:.3g})")
