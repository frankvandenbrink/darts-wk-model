"""Vormmodel: kans per leg uit het verschil in recente average en checkout% (Dartsorakel).

vorm = w * waarde(3 mnd) + (1-w) * waarde(L mnd), L in {6, 12}
kans dat de beginner een leg wint = logistic(logit(HOLD) + k*(avgA-avgB) + kc*(coA-coB))
De wedstrijdkans volgt exact uit setmodel. In-wedstrijd-averages (*_achteraf) worden nooit gebruikt.
"""
from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass

from . import config
from .evaluatie import logloss
from .setmodel import hold_kansen, wedstrijd_kans


@dataclass(frozen=True)
class VormParams:
    w: float
    L: int
    k: float
    kc: float

    def dict(self) -> dict:
        return asdict(self)


def vorm(r: dict, kant: str, naam: str, w: float, L: int) -> float:
    kort, lang = r[f"{naam}{kant}_3m"], r[f"{naam}{kant}_{L}m"]
    nk = r[f"n_{naam}{kant}_3m"]
    minn = config.MIN_DARTS_KORT if naam == "avg" else config.MIN_CO_KORT
    if lang is None:
        return config.FALLBACK_AVG if naam == "avg" else config.FALLBACK_CO
    if kort is None or nk < minn:
        return lang
    return w * kort + (1 - w) * lang


def kans(r: dict, prm: VormParams) -> float:
    """Kans dat speler1 de wedstrijd wint."""
    a1, a2 = vorm(r, "1", "avg", prm.w, prm.L), vorm(r, "2", "avg", prm.w, prm.L)
    c1, c2 = vorm(r, "1", "co", prm.w, prm.L), vorm(r, "2", "co", prm.w, prm.L)
    h1, h2 = hold_kansen(prm.k * (a1 - a2) + prm.kc * (c1 - c2), config.HOLD)
    return wedstrijd_kans(round(h1, 4), round(h2, 4), r["setsnodig"])


def afstemmen(rows: list[dict]) -> VormParams:
    """Grid search op gemiddelde log-loss (alleen wedstrijden met odds, zodat n gelijk is aan de evaluatie)."""
    rows = [r for r in rows if r["odd1"] is not None]
    if not rows:
        raise ValueError("geen trainingswedstrijden met odds")
    y = [1 if r["winnaar"] == 1 else 0 for r in rows]
    best = None
    for w, L, k, kc in itertools.product(*config.GRID.values()):
        prm = VormParams(w, L, k, kc)
        ll = sum(logloss(kans(r, prm), yi) for r, yi in zip(rows, y)) / len(rows)
        if best is None or ll < best[1]:
            best = (prm, ll)
    return best[0]
