"""Correct score in sets: verdeling over de exacte eindstand, afgeleid van een wedstrijdkans.

De wedstrijdkans p (bijvoorbeeld de marktkans zonder marge) wordt omgezet in een legverschil d (logit-schaal),
daarna in hold-kansen rond `hold` en via een exacte set-DP (zelfde regels als `setmodel.setstand_verdeling`)
in een kans per setstand.

Optioneel `sigma`: dagvorm. Het legverschil van een wedstrijd is d0 + sigma·z met z ~ N(0, 1); d0 wordt zo gekozen
dat de wedstrijdkans gelijk blijft aan p. Daarmee worden legs binnen een wedstrijd gecorreleerd (een goede of slechte
dag), wat vaker tot een 'whitewash' leidt.

Optioneel `kappa`: momentum. Een set wordt gespeeld met legverschil d + kappa als speler 1 de vorige set won en
d − kappa als speler 2 die won (eerste set: d). Optioneel `tiebreak`: bij 5-5 in de beslissende set volgt de
sudden-death-leg de wissel ("wissel", standaard) of wordt opnieuw om de bull gegooid ("bull": 50/50 wie begint).

Voor snelheid wordt per (n, hold, kappa, tiebreak) één tabel over d berekend (gevectoriseerd over d) en lineair
geïnterpoleerd (stap 0,01 op d). hold wordt daarvoor afgerond op 0,005.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .rating import logit

D_MIN, D_MAX, D_STAP = -4.0, 4.0, 0.01
HOLD_STAP = 0.005
_GH_X, _GH_W = np.polynomial.hermite_e.hermegauss(15)   # knopen voor E[f(z)], z ~ N(0, 1)
_GH_W = _GH_W / _GH_W.sum()


def standen(n: int) -> list[tuple[int, int]]:
    """Alle eindstanden first to n sets, vanuit speler 1: (n,0), (n,1), ..., (0,n)."""
    return [(n, k) for k in range(n)] + [(k, n) for k in range(n - 1, -1, -1)]


def _log(x):
    return 1 / (1 + np.exp(-x))


def _holds(d: np.ndarray, hold: float):
    """Gevectoriseerde `rating.hold_uit_legkans`: (hold_a, hold_b) per d, afgerond op 6 decimalen."""
    h, doel = logit(hold), _log(np.asarray(d, dtype=float))
    lo, hi = np.full_like(doel, -20.0), np.full_like(doel, 20.0)
    for _ in range(80):
        x = (lo + hi) / 2
        laag = 0.5 * (_log(h + x) + _log(x - h)) < doel
        lo, hi = np.where(laag, x, lo), np.where(laag, hi, x)
    x = (lo + hi) / 2
    return np.round(_log(h + x), 6), np.round(_log(h - x), 6)


def _set_kans(pa, pb, a_begint: bool, beslissend: bool, tiebreak: str):
    """Kans dat A de set wint (arrays); zie `setmodel.set_kans`. pa/pb = legkans A als A/B begint."""
    memo = {}

    def f(la, lb, a_gooit):
        k = (la, lb, a_gooit)
        if k in memo:
            return memo[k]
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
                return 0.5 * (pa + pb) if tiebreak == "bull" else (pa if a_gooit else pb)
        p = pa if a_gooit else pb
        memo[k] = p * f(la + 1, lb, not a_gooit) + (1 - p) * f(la, lb + 1, not a_gooit)
        return memo[k]

    return f(0, 0, a_begint)


def _dp(holds: dict, n: int, tiebreak: str = "wissel") -> dict:
    """Kans per eindstand (arrays) met momentum: holds[m] = (hold_a, hold_b) na setwinst van A (m=1),
    van B (m=-1) of bij de eerste set (m=0). Gemiddeld over wie de bull wint."""
    sk = {(m, ab, bs): _set_kans(ha, 1 - hb, ab, bs, tiebreak)
          for m, (ha, hb) in holds.items() for ab in (True, False) for bs in (True, False)}
    uit = {}
    for a_eerst in (True, False):
        kans = {(0, 0, 0): 1.0}
        for totaal in range(2 * n - 1):
            nieuw = {}
            for (sa, sb, m), p in kans.items():
                if sa == n or sb == n:
                    nieuw[(sa, sb, m)] = nieuw.get((sa, sb, m), 0.0) + p
                    continue
                a_begint = a_eerst if totaal % 2 == 0 else not a_eerst
                ps = sk[(m, a_begint, sa == n - 1 and sb == n - 1)]
                nieuw[(sa + 1, sb, 1)] = nieuw.get((sa + 1, sb, 1), 0.0) + p * ps
                nieuw[(sa, sb + 1, -1)] = nieuw.get((sa, sb + 1, -1), 0.0) + p * (1 - ps)
            kans = nieuw
        for (sa, sb, _), p in kans.items():
            uit[(sa, sb)] = uit.get((sa, sb), 0.0) + 0.5 * p
    return uit


def _setstand_ext(ha: float, hb: float, n: int, kappa: float = 0.0, tiebreak: str = "wissel") -> dict:
    """Als `setmodel.setstand_verdeling(ha, hb, n)`, met momentum kappa (op de d-schaal) en tie-break-regel."""
    if kappa:
        hold = float(_log((logit(ha) + logit(hb)) / 2))   # ha = logistic(H + x), hb = logistic(H - x)
        d = logit(0.5 * (ha + 1 - hb))
        holds = {m: tuple(float(x[0]) for x in _holds(np.array([d + m * kappa]), hold)) for m in (1, -1)}
        holds[0] = (ha, hb)
    else:
        holds = {0: (ha, hb), 1: (ha, hb), -1: (ha, hb)}
    return {k: float(v) for k, v in _dp(holds, n, tiebreak).items()}


def _rond_hold(hold: float) -> float:
    return round(round(hold / HOLD_STAP) * HOLD_STAP, 4)


@lru_cache(maxsize=None)
def _tabel(n: int, hold: float, kappa: float = 0.0, tiebreak: str = "wissel"):
    ds = np.round(np.arange(D_MIN, D_MAX + D_STAP / 2, D_STAP), 4)
    holds = {m: _holds(ds + m * kappa, hold) for m in (0, 1, -1)}
    v = _dp(holds, n, tiebreak)
    m = np.stack([v[s] for s in standen(n)], axis=1)
    winst = m[:, :n].sum(axis=1)
    return ds, m, winst


def _interp(n: int, hold: float, d: np.ndarray, kappa: float = 0.0, tiebreak: str = "wissel"):
    ds, m, winst = _tabel(n, hold, kappa, tiebreak)
    d = np.clip(d, D_MIN, D_MAX)
    pos = (d - D_MIN) / D_STAP
    i = np.minimum(np.floor(pos).astype(int), len(ds) - 2)
    f = (pos - i)[..., None]
    return m[i] * (1 - f) + m[i + 1] * f


@lru_cache(maxsize=200_000)
def _verdeling(p: float, n: int, hold: float, sigma: float, kappa: float, tiebreak: str) -> tuple:
    ds, _, winst = _tabel(n, hold, kappa, tiebreak)
    lo, hi = D_MIN + 4 * sigma, D_MAX - 4 * sigma
    for _ in range(50):  # bisectie op d0 alleen via de wedstrijdkans (stijgt monotoon in d)
        mid = (lo + hi) / 2
        if (np.interp(np.clip(mid + sigma * _GH_X, D_MIN, D_MAX), ds, winst) * _GH_W).sum() < p:
            lo = mid
        else:
            hi = mid
    v = (_interp(n, hold, (lo + hi) / 2 + sigma * _GH_X, kappa, tiebreak) * _GH_W[:, None]).sum(axis=0)
    return tuple(map(float, v / v.sum()))


def verdeling(p: float, n: int, hold: float = 0.6, sigma: float = 0.0, kappa: float = 0.0,
              tiebreak: str = "wissel") -> dict[tuple[int, int], float]:
    """Kans op elke setstand (vanuit speler 1) bij wedstrijdkans p voor speler 1, first to n sets."""
    return dict(zip(standen(n), _verdeling(float(p), n, _rond_hold(hold), float(sigma), float(kappa), tiebreak)))


def eerlijke_odds(p: float, n: int, hold: float = 0.6, sigma: float = 0.0, kappa: float = 0.0,
                  tiebreak: str = "wissel") -> dict[str, float]:
    """Eerlijke odd (1/kans) per setstand, met de stand als tekst 'a-b' vanuit speler 1."""
    return {f"{a}-{b}": round(1 / q, 2) for (a, b), q in verdeling(p, n, hold, sigma, kappa, tiebreak).items() if q > 0}


def uitslagtype(stand: tuple[int, int], p: float, n: int) -> str:
    """Uitslag vanuit de favoriet (p >= 0.5 is speler 1): 'fav n-0', 'fav n-1', ..., 'und n-0'."""
    a, b = stand if p >= 0.5 else (stand[1], stand[0])
    return f"fav {n}-{b}" if a == n else f"und {n}-{a}"
