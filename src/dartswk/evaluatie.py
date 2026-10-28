"""Evaluatie: marktkansen (margecorrectie), Brier, log-loss, bets, ROI, stopregel en geclusterde bootstrap."""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

EPS = 1e-6


# ---------------------------------------------------------------- marktkansen
def markt_proportioneel(odd1: float, odd2: float) -> float:
    """Kans op speler1: impliciete kansen naar verhouding geschaald tot som 1."""
    i1, i2 = 1 / odd1, 1 / odd2
    return i1 / (i1 + i2)


def shin_kansen(odds: list[float], tol: float = 1e-12) -> list[float]:
    """Shin (1993): kansen gecorrigeerd voor insiders; z via bisectie zodat de kansen optellen tot 1."""
    pi = [1 / o for o in odds]
    B = sum(pi)
    if B <= 1:  # geen marge: proportioneel
        return [x / B for x in pi]

    def kansen(z):
        return [(math.sqrt(z * z + 4 * (1 - z) * x * x / B) - z) / (2 * (1 - z)) for x in pi]

    lo, hi = 0.0, 0.999
    while hi - lo > tol:
        z = (lo + hi) / 2
        if sum(kansen(z)) > 1:
            lo = z
        else:
            hi = z
    p = kansen((lo + hi) / 2)
    s = sum(p)
    return [x / s for x in p]


def markt_shin(odd1: float, odd2: float) -> float:
    return shin_kansen([odd1, odd2])[0]


MARGE = {"proportioneel": markt_proportioneel, "shin": markt_shin}


# ---------------------------------------------------------------- metrics
def logloss(p: float, y: int) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def gemiddeld(f, ps, ys) -> float:
    return float(np.mean([f(p, y) for p, y in zip(ps, ys)])) if len(ps) else float("nan")


# ---------------------------------------------------------------- bets
def kies_kant(p: float, odd1: float, odd2: float, drempel: float | None) -> int | None:
    """1 of 2 als eigen kans x odd > drempel (hoogste verwachting), anders None. drempel None = niet wedden."""
    if drempel is None:
        return None
    ev1, ev2 = p * odd1, (1 - p) * odd2
    if max(ev1, ev2) <= drempel:
        return None
    return 1 if ev1 >= ev2 else 2


def bets(rows: list[dict], ps: list[float], drempel: float | None) -> list[dict]:
    """Vaste inzet 1 per bet, hoogstens één kant per wedstrijd."""
    uit = []
    for r, p in zip(rows, ps):
        kant = kies_kant(p, r["odd1"], r["odd2"], drempel)
        if kant is None:
            continue
        odd = r["odd1"] if kant == 1 else r["odd2"]
        won = r["winnaar"] == kant
        andere = r["odd2"] if kant == 1 else r["odd1"]
        uit.append(dict(jaar=r["jaar"], ronde=r["ronde"], odd=odd, underdog=odd > andere,
                        gewonnen=won, resultaat=(odd - 1) if won else -1.0))
    return uit


def roi(bl: list[dict]) -> float | None:
    return sum(b["resultaat"] for b in bl) / len(bl) if bl else None


def bootstrap_geclusterd(bl: list[dict], n: int = 5000, seed: int = 1, alpha: float = 0.10):
    """90%-interval van de ROI met resampling van clusters (jaar, ronde) in plaats van losse bets."""
    if not bl:
        return None, None
    cl = defaultdict(lambda: [0.0, 0])
    for b in bl:
        c = cl[(b["jaar"], b["ronde"])]
        c[0] += b["resultaat"]
        c[1] += 1
    som = np.array([v[0] for v in cl.values()])
    aantal = np.array([v[1] for v in cl.values()])
    if len(som) < 2:
        return None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(som), size=(n, len(som)))
    rois = som[idx].sum(axis=1) / aantal[idx].sum(axis=1)
    return float(np.quantile(rois, alpha / 2)), float(np.quantile(rois, 1 - alpha / 2))


def drempeltabel(rows, ps, drempels) -> list[dict]:
    out = []
    for d in drempels:
        bl = bets(rows, ps, d)
        r = roi(bl)
        out.append(dict(drempel=d, bets=len(bl), roi=None if r is None else round(r, 4)))
    return out


def kies_drempel(tabel: list[dict], min_bets: int) -> tuple[float | None, str]:
    """Drempel met de hoogste ROI op train (min. `min_bets` bets). Stopregel: ROI <= 0 -> niet wedden."""
    geldig = [x for x in tabel if x["bets"] >= min_bets and x["roi"] is not None]
    if not geldig:
        return None, f"geen drempel met minstens {min_bets} bets op train: niet wedden"
    best = max(geldig, key=lambda x: x["roi"])
    if best["roi"] <= 0:
        return None, f"beste ROI op train is {best['roi']:+.1%} (drempel {best['drempel']:.2f}) <= 0: niet wedden"
    return best["drempel"], f"drempel {best['drempel']:.2f} heeft de hoogste ROI op train ({best['roi']:+.1%})"
