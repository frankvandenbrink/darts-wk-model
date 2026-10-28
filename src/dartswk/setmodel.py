"""Exacte set- en wedstrijdkansen voor het WK-format.

- Een set is first to 3 legs. De beslissende set (bij n-1 tegen n-1 sets) vraagt twee legs verschil,
  met een sudden-death-leg bij 5-5.
- De beginnende speler wisselt per leg en per set; de wedstrijdkans is het gemiddelde over wie de bull wint.
- In de sudden-death-leg loopt de wissel door (in werkelijkheid wordt opnieuw om de bull gegooid; het verschil
  in wedstrijdkans is volgens de review maximaal 0.00017).
"""
from __future__ import annotations

import math
from functools import lru_cache


@lru_cache(maxsize=None)
def set_kans(pa: float, pb: float, a_begint: bool, beslissend: bool) -> float:
    """Kans dat A de set wint. pa = kans dat A een leg wint als A begint, pb = idem als B begint."""

    @lru_cache(maxsize=None)
    def f(la: int, lb: int, a_gooit: bool) -> float:
        if not beslissend:
            if la == 3:
                return 1.0
            if lb == 3:
                return 0.0
        else:
            if la >= 3 and la - lb >= 2:
                return 1.0
            if lb >= 3 and lb - la >= 2:
                return 0.0
            if la == 5 and lb == 5:  # sudden-death-leg
                return pa if a_gooit else pb
        p = pa if a_gooit else pb
        return p * f(la + 1, lb, not a_gooit) + (1 - p) * f(la, lb + 1, not a_gooit)

    return f(0, 0, a_begint)


def wedstrijd_kans(hold_a: float, hold_b: float, n: int) -> float:
    """Kans dat A wint in een wedstrijd first to n sets.

    hold_a = kans dat A een leg wint waarin A begint; hold_b = idem voor B.
    """
    pa, pb = hold_a, 1 - hold_b

    def g(a_eerst: bool) -> float:
        @lru_cache(maxsize=None)
        def f(sa: int, sb: int) -> float:
            if sa == n:
                return 1.0
            if sb == n:
                return 0.0
            a_begint = a_eerst if (sa + sb) % 2 == 0 else not a_eerst
            ps = set_kans(pa, pb, a_begint, sa == n - 1 and sb == n - 1)
            return ps * f(sa + 1, sb) + (1 - ps) * f(sa, sb + 1)

        return f(0, 0)

    return 0.5 * (g(True) + g(False))


def hold_kansen(x: float, hold: float) -> tuple[float, float]:
    """Hold-kansen van A en B bij sterkteverschil x (logit-schaal) en basis-holdkans `hold`."""
    h = math.log(hold / (1 - hold))
    return 1 / (1 + math.exp(-(h + x))), 1 / (1 + math.exp(-(h - x)))
