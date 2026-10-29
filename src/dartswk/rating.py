"""Ratingmodel: Bradley-Terry op legs met tegenstandercorrectie, tijdsweging en krimp.

- Kans dat speler a een leg wint van b (gemiddeld over wie begint) = logistic(r_a - r_b).
- Fit: gewogen maximum likelihood op legs gewonnen/verloren per wedstrijd (Dartsorakel-uitslagen van alle
  events strikt vóór de WK-start), met gewicht 0.5^(leeftijd / halfwaarde) en een normale prior
  r ~ N(0, 1/lam). De prior krimpt spelers met weinig data naar 0, het tijdsgewogen veldgemiddelde.
- Bij WK en World Grand Prix staat de score in sets; daar telt alleen de uitslag, als één waarneming met
  kans logistic(s * (r_a - r_b)), s = helling van de exacte wedstrijdkans (first to 3 sets) bij k = 1.
- WK-spelers zonder data krijgen rating `onbekend` (afgestemd op train).
- Wedstrijdkans: legverschil d = k * (r_a - r_b) wordt omgezet in hold-kansen h_a = logistic(H + x),
  h_b = logistic(H - x) zodat de gemiddelde legkans logistic(d) is (H = logit(HOLD)); daarna de exacte
  set/match-DP uit setmodel met het aantal sets uit de ronde.
- Variant rating+avg: d = k * (r_a - r_b + g * (u_a - u_b)), u = gekrompen, tijdsgewogen average t.o.v. het
  eventgemiddelde.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache

import numpy as np

from . import config
from .evaluatie import logloss
from .events import Wedstrijd, laad_wedstrijden
from .koppelen import OrakelIndex
from .parse import load_orakel
from .setmodel import wedstrijd_kans


@dataclass(frozen=True)
class RatingParams:
    halfwaarde: int     # dagen
    lam: float          # prior-precisie (krimp)
    onbekend: float     # rating van een speler zonder data
    k: float            # schaal van het ratingverschil op het WK
    g: float = 0.0      # gewicht average-sterkte (alleen rating+avg)

    def dict(self) -> dict:
        return asdict(self)


def logistic(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def logit(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


# ---------------------------------------------------------------- van legkans naar hold-kansen
@lru_cache(maxsize=None)
def hold_uit_legkans(d: float, hold: float = config.HOLD) -> tuple[float, float]:
    """(hold_a, hold_b) met 0.5*(hold_a + 1 - hold_b) = logistic(d) en hold_a/b = logistic(H +/- x)."""
    h = logit(hold)
    doel = logistic(d)
    lo, hi = -20.0, 20.0
    for _ in range(80):
        x = (lo + hi) / 2
        if 0.5 * (logistic(h + x) + logistic(x - h)) < doel:
            lo = x
        else:
            hi = x
    x = (lo + hi) / 2
    return logistic(h + x), logistic(h - x)


def wedstrijdkans_uit_d(d: float, setsnodig: int) -> float:
    ha, hb = hold_uit_legkans(round(d, 4))
    return wedstrijd_kans(round(ha, 5), round(hb, 5), setsnodig)


@lru_cache(maxsize=None)
def sets_schaal(n: int = 3) -> float:
    """Helling s zodat logistic(s*d) de wedstrijdkans first to n sets benadert (kleine d)."""
    d = 0.05
    return logit(wedstrijdkans_uit_d(d, n)) / d


# ---------------------------------------------------------------- Bradley-Terry-fit
def fit_bt(wed: list[Wedstrijd], voor: date, halfwaarde: float, lam: float,
           tol: float = 1e-9, max_iter: int = 50) -> dict[int, float]:
    """{player_key: rating} via Newton op de gewogen log-likelihood plus ridge-prior lam/2 * sum(r^2)."""
    assert all(w.datum < voor for w in wed), f"wedstrijd op of na de cutoff {voor}: lek"
    if not wed:
        return {}
    keys = sorted({w.winnaar for w in wed} | {w.verliezer for w in wed})
    pos = {k: i for i, k in enumerate(keys)}
    a = np.array([pos[w.winnaar] for w in wed])
    b = np.array([pos[w.verliezer] for w in wed])
    leeftijd = np.array([(voor - w.datum).days for w in wed], dtype=float)
    gew = 0.5 ** (leeftijd / halfwaarde)
    s_set = sets_schaal(3)
    s = np.array([s_set if w.sets else 1.0 for w in wed])
    la = np.array([1.0 if w.sets else w.score_w for w in wed])
    lb = np.array([0.0 if w.sets else w.score_v for w in wed])
    n = len(keys)
    r = np.zeros(n)
    for _ in range(max_iter):
        d = s * (r[a] - r[b])
        p = 1 / (1 + np.exp(-d))
        gd = gew * s * (la * (1 - p) - lb * p)             # d loglik / d(r_a - r_b)
        hd = gew * s * s * (la + lb) * p * (1 - p)         # -d2 loglik / d(r_a - r_b)^2
        grad = np.zeros(n)
        np.add.at(grad, a, gd)
        np.add.at(grad, b, -gd)
        grad -= lam * r
        H = np.zeros((n, n))
        np.add.at(H, (a, a), hd)
        np.add.at(H, (b, b), hd)
        np.add.at(H, (a, b), -hd)
        np.add.at(H, (b, a), -hd)
        H[np.diag_indices(n)] += lam
        stap = np.linalg.solve(H, grad)
        r += stap
        if np.max(np.abs(stap)) < tol:
            break
    return {k: float(r[i]) for k, i in pos.items()}


def avg_sterkte(wed: list[Wedstrijd], voor: date, halfwaarde: float, lam_legs: float = 50.0) -> dict[int, float]:
    """Gekrompen, tijdsgewogen average t.o.v. het eventgemiddelde (gewicht = aantal legs, prior 0)."""
    ev: dict[int, list[float]] = {}
    for w in wed:
        for x in (w.avg_w, w.avg_v):
            if x is not None:
                ev.setdefault(w.event_key, []).append(x)
    evgem = {k: float(np.mean(v)) for k, v in ev.items()}
    som: dict[int, float] = {}
    gew: dict[int, float] = {}
    for w in wed:
        g = 0.5 ** ((voor - w.datum).days / halfwaarde) * (3.0 if w.sets else w.score_w + w.score_v)
        for key, x in ((w.winnaar, w.avg_w), (w.verliezer, w.avg_v)):
            if x is None:
                continue
            som[key] = som.get(key, 0.0) + g * (x - evgem[w.event_key])
            gew[key] = gew.get(key, 0.0) + g
    return {k: som[k] / (gew[k] + lam_legs) for k in som}


# ---------------------------------------------------------------- per WK-jaar: data en koppeling
_CONTEXT: dict = {}
_FITS: dict = {}
_AFGESTEMD: dict = {}


def context(jaar: int) -> dict:
    """Wedstrijden vóór de WK-start, koppeling WK-naam -> player_key en tellingen (gecachet)."""
    cache = config.cache_map()
    sleutel = (str(cache), jaar)
    if sleutel not in _CONTEXT:
        voor = date.fromisoformat(config.JAREN[jaar].start)
        wed, namen, telling = laad_wedstrijden(cache, voor)
        orakel = {k: {"naam": v} for k, v in namen.items()}
        try:
            for k, p in load_orakel(jaar, cache).items():
                orakel.setdefault(k, {"naam": p["naam"]})
        except FileNotFoundError:
            pass
        from .dataset import wiki_wedstrijden
        wiki, _ = wiki_wedstrijden(jaar, cache)
        keymap, meld = OrakelIndex(orakel).koppel([r[k] for r in wiki for k in ("speler1", "speler2")])
        spelers_met_data = {w.winnaar for w in wed} | {w.verliezer for w in wed}
        zonder = sorted(n for n, k in keymap.items() if k not in spelers_met_data)
        _CONTEXT[sleutel] = dict(voor=voor, wed=wed, keymap=keymap, telling=telling, koppelmeldingen=meld,
                                 wk_spelers=len(keymap), wk_spelers_zonder_data=zonder)
    return _CONTEXT[sleutel]


def ratings(jaar: int, halfwaarde: float, lam: float) -> tuple[dict, dict]:
    sleutel = (str(config.cache_map()), jaar, halfwaarde, lam)
    if sleutel not in _FITS:
        c = context(jaar)
        _FITS[sleutel] = (fit_bt(c["wed"], c["voor"], halfwaarde, lam), avg_sterkte(c["wed"], c["voor"], halfwaarde))
    return _FITS[sleutel]


def verschil(r: dict, halfwaarde: float, lam: float, onbekend: float, g: float = 0.0) -> float:
    """r_1 - r_2 (+ g * (u_1 - u_2)) voor een WK-wedstrijd."""
    c = context(r["jaar"])
    rt, av = ratings(r["jaar"], halfwaarde, lam)
    k1, k2 = c["keymap"][r["speler1"]], c["keymap"][r["speler2"]]
    r1, r2 = rt.get(k1, onbekend), rt.get(k2, onbekend)
    u1, u2 = av.get(k1, 0.0), av.get(k2, 0.0)
    return r1 - r2 + g * (u1 - u2)


def kans(r: dict, prm: RatingParams) -> float:
    """Kans dat speler1 de wedstrijd wint."""
    x = verschil(r, prm.halfwaarde, prm.lam, prm.onbekend, prm.g)
    return wedstrijdkans_uit_d(prm.k * x, r["setsnodig"])


def _afstemmen(rows: list[dict], grid_g: list[float]) -> RatingParams:
    """Grid search op gemiddelde log-loss (train, alleen wedstrijden met odds)."""
    rows = [r for r in rows if r["odd1"] is not None]
    if not rows:
        raise ValueError("geen trainingswedstrijden met odds")
    sleutel = (str(config.cache_map()), tuple((r["jaar"], r["wedstrijd"]) for r in rows), tuple(grid_g))
    if sleutel in _AFGESTEMD:
        return _AFGESTEMD[sleutel]
    y = [1 if r["winnaar"] == 1 else 0 for r in rows]
    G = config.RATING_GRID
    best = None
    for hw, lam, onb, g in itertools.product(G["halfwaarde"], G["lam"], G["onbekend"], grid_g):
        xs = [verschil(r, hw, lam, onb, g) for r in rows]
        for k in G["k"]:
            ll = sum(logloss(wedstrijdkans_uit_d(k * x, r["setsnodig"]), yi)
                     for x, r, yi in zip(xs, rows, y)) / len(rows)
            if best is None or ll < best[1] - 1e-12:
                best = (RatingParams(hw, lam, onb, k, g), ll)
    _AFGESTEMD[sleutel] = best[0]
    return best[0]


def afstemmen(rows: list[dict]) -> RatingParams:
    return _afstemmen(rows, [0.0])


def afstemmen_avg(rows: list[dict]) -> RatingParams:
    return _afstemmen(rows, config.RATING_GRID["g"])


def beschrijf_data(jaren: list[int]) -> dict:
    """Per WK-jaar: hoeveel events/wedstrijden de rating gebruikt en welke WK-spelers geen data hebben."""
    uit = {}
    for j in jaren:
        c = context(j)
        uit[j] = dict(cutoff_voor=str(c["voor"]), **c["telling"], wk_spelers=c["wk_spelers"],
                      wk_spelers_zonder_data=len(c["wk_spelers_zonder_data"]))
    return uit
