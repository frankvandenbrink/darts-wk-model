"""Correct score in sets: verdeling over de exacte eindstand, afgeleid van een wedstrijdkans.

De wedstrijdkans p (bijvoorbeeld de marktkans zonder marge) wordt omgezet in een legverschil d (logit-schaal),
daarna in hold-kansen rond `hold` en via de exacte set-DP (`setmodel.setstand_verdeling`) in een kans per setstand.

Optioneel `sigma`: dagvorm. Het legverschil van een wedstrijd is d0 + sigma·z met z ~ N(0, 1); d0 wordt zo gekozen
dat de wedstrijdkans gelijk blijft aan p. Daarmee worden legs binnen een wedstrijd gecorreleerd (een goede of slechte
dag), wat vaker tot een 'whitewash' leidt.

Voor snelheid wordt per (n, hold) één tabel over d berekend en lineair geïnterpoleerd (stap 0,01 op d).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .rating import hold_uit_legkans
from .setmodel import setstand_verdeling

D_MIN, D_MAX, D_STAP = -4.0, 4.0, 0.01
_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(15)   # knopen voor E[f(z)], z ~ N(0, 1)
_GH_W = _GH_W / _GH_W.sum()


def standen(n: int) -> list[tuple[int, int]]:
    """Alle eindstanden first to n sets, vanuit speler 1: (n,0), (n,1), ..., (0,n)."""
    return [(n, k) for k in range(n)] + [(k, n) for k in range(n - 1, -1, -1)]


@lru_cache(maxsize=None)
def _tabel(n: int, hold: float):
    ds = np.round(np.arange(D_MIN, D_MAX + D_STAP / 2, D_STAP), 4)
    st = standen(n)
    m = np.empty((len(ds), len(st)))
    for i, d in enumerate(ds):
        ha, hb = hold_uit_legkans(float(d), hold)
        v = setstand_verdeling(round(ha, 6), round(hb, 6), n)
        m[i] = [v[s] for s in st]
    winst = m[:, :n].sum(axis=1)
    return ds, m, winst


def _interp(n: int, hold: float, d: np.ndarray):
    ds, m, winst = _tabel(n, hold)
    d = np.clip(d, D_MIN, D_MAX)
    pos = (d - D_MIN) / D_STAP
    i = np.minimum(np.floor(pos).astype(int), len(ds) - 2)
    f = (pos - i)[..., None]
    return m[i] * (1 - f) + m[i + 1] * f


def verdeling(p: float, n: int, hold: float = 0.6, sigma: float = 0.0) -> dict[tuple[int, int], float]:
    """Kans op elke setstand (vanuit speler 1) bij wedstrijdkans p voor speler 1, first to n sets."""
    def mix(d0):
        return (_interp(n, hold, d0 + sigma * _GH_X) * _GH_W[:, None]).sum(axis=0)

    lo, hi = D_MIN + 4 * sigma, D_MAX - 4 * sigma
    for _ in range(50):
        mid = (lo + hi) / 2
        if mix(np.float64(mid))[:n].sum() < p:
            lo = mid
        else:
            hi = mid
    v = mix(np.float64((lo + hi) / 2))
    v = v / v.sum()
    return dict(zip(standen(n), map(float, v)))


def eerlijke_odds(p: float, n: int, hold: float = 0.6, sigma: float = 0.0) -> dict[str, float]:
    """Eerlijke odd (1/kans) per setstand, met de stand als tekst 'a-b' vanuit speler 1."""
    return {f"{a}-{b}": round(1 / q, 2) for (a, b), q in verdeling(p, n, hold, sigma).items() if q > 0}


def uitslagtype(stand: tuple[int, int], p: float, n: int) -> str:
    """Uitslag vanuit de favoriet (p >= 0.5 is speler 1): 'fav n-0', 'fav n-1', ..., 'und n-0'."""
    a, b = stand if p >= 0.5 else (stand[1], stand[0])
    return f"fav {n}-{b}" if a == n else f"und {n}-{a}"
