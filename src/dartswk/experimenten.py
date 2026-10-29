"""Systematisch experimentkader: register, vast protocol, controles en uitvoer (zie docs/protocol.md).

- Register: experimenten/register.json. Per experiment id, datum, model, features, grid, hypothese en criterium
  (vóór het draaien geschreven) en `na_test_aangepast` (bool + toelichting).
- Elke run komt in experimenten/runlog.jsonl, ook mislukkingen en experimenten die niet gedraaid konden worden.
  De log bewaart een hash van hypothese, criterium, model, features en grid. Verandert die hash na een eerdere run
  terwijl `na_test_aangepast` false is, dan krijgt het resultaat een protocolwaarschuwing.
- Afstemmen gebeurt alleen op de trainrijen (de afstemfunctie krijgt de testrijen nooit te zien). Walk-forward:
  assert dat elk trainjaar vóór het testjaar ligt. Event-data: assert dat elke wedstrijd vóór de WK-start ligt.
- Per experiment en split: n, log-loss, Brier, verschil met de markt (proportioneel) met se, kalibratiehelling,
  kalibratiebins, bets, ROI met 90%-interval (bootstrap per (jaar, ronde)) en het winstverloop per bet.

Uitvoer: resultaten/experimenten.json en resultaten/experimenten.md. Geen kansen of odds per wedstrijd.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import subprocess
import time
import traceback
from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import config, kalibratie, rating, vorm
from .evaluatie import (MARGE, bets, bootstrap_geclusterd, brier, drempeltabel, kies_drempel, kies_kant,
                        logloss, markt_proportioneel, roi)
from .kalibratie import fit_logit, helling
from .rating import logistic, logit, wedstrijdkans_uit_d
from .setmodel import setstand_verdeling, wedstrijd_kans

SPLITS = [  # (train, test, soort); walk-forward eerst
    ([2024], [2025], "walk-forward"),
    ([2024, 2025], [2026], "walk-forward"),
    ([2026], [2025], "richting"),
    ([2025], [2026], "richting"),
    ([2025], [2024], "richting"),
    ([2025, 2026], [2024], "richting"),
]
N_BINS = 5          # kalibratiebins op de kans van de favoriet volgens het model (0.5-1.0)
RUIS_SE = 2.0       # |verschil| <= 2 se: binnen de ruis


def register_pad() -> Path:
    return config.basis() / "experimenten" / "register.json"


def runlog_pad() -> Path:
    return config.basis() / "experimenten" / "runlog.jsonl"


def _y(rows):
    return [1 if r["winnaar"] == 1 else 0 for r in rows]


def _markt(r):
    return markt_proportioneel(r["odd1"], r["odd2"])


def _sig(x):
    return 1 / (1 + np.exp(-x))


@dataclass(frozen=True)
class P:
    """Generieke parametercontainer (dict met een .dict() voor de uitvoer)."""
    waarden: tuple

    def dict(self) -> dict:
        return {k: (v.dict() if hasattr(v, "dict") else v) for k, v in self.waarden}

    def __getitem__(self, k):
        return dict(self.waarden)[k]


def _p(**kw) -> P:
    return P(tuple(kw.items()))


# ================================================================ controles
def _geen(rows):
    return _p()


def m_markt(grid):
    return _geen, lambda r, prm: _markt(r)


def m_munt(grid):
    return _geen, lambda r, prm: 0.5


def m_markt_vlak(grid):
    return kalibratie.marktkrimp_afstemmen, kalibratie.marktkrimp_kans


# ================================================================ bestaande modellen
def _bestaand(naam):
    from .modellen import MODELLEN

    def f(grid):
        return MODELLEN[naam]
    return f


# ================================================================ Bradley-Terry met vaste halfwaarde (tijdsverval)
def m_bt(grid):
    G = {**config.RATING_GRID, **grid}

    def afstemmen(rows, _g=None):
        rows = [r for r in rows if r["odd1"] is not None]
        y = _y(rows)
        best = None
        for hw, lam, onb in itertools.product(G["halfwaarde"], G["lam"], G["onbekend"]):
            xs = [rating.verschil(r, hw, lam, onb) for r in rows]
            for k in G["k"]:
                ll = np.mean([logloss(wedstrijdkans_uit_d(k * x, r["setsnodig"]), yi) for x, r, yi in zip(xs, rows, y)])
                if best is None or ll < best[1] - 1e-12:
                    best = (rating.RatingParams(hw, lam, onb, k), ll)
        return best[0]
    return afstemmen, rating.kans


# ================================================================ legmodel met vrije hold-kans
@lru_cache(maxsize=None)
def _wk_hold(d: float, n: int, hold: float) -> float:
    ha, hb = rating.hold_uit_legkans(d, hold)
    return wedstrijd_kans(round(ha, 5), round(hb, 5), n)


def m_hold(grid):
    """Ratingparameters zoals `rating` (op train), daarna hold-basis en k samen op train."""
    def afstemmen(rows):
        rows = [r for r in rows if r["odd1"] is not None]
        basis = rating.afstemmen(rows)
        y = _y(rows)
        xs = [rating.verschil(r, basis.halfwaarde, basis.lam, basis.onbekend) for r in rows]
        best = None
        for h, k in itertools.product(grid["hold"], grid["k"]):
            ll = np.mean([logloss(_wk_hold(round(k * x, 4), r["setsnodig"], h), yi) for x, r, yi in zip(xs, rows, y)])
            if best is None or ll < best[1] - 1e-12:
                best = ((h, k), ll)
        return _p(basis=basis, hold=best[0][0], k=best[0][1])

    def kans(r, prm):
        b = prm["basis"]
        x = rating.verschil(r, b.halfwaarde, b.lam, b.onbekend)
        return _wk_hold(round(prm["k"] * x, 4), r["setsnodig"], prm["hold"])
    return afstemmen, kans


# ================================================================ Elo en Glicko-achtig (sequentieel, events vóór de WK-start)
def _chronologisch(wed):
    """Op datum en event; binnen een event staat de finale bovenaan de pagina, dus de volgorde omdraaien."""
    per_event: dict = {}
    for w in wed:
        per_event.setdefault((w.datum, w.event_key), []).append(w)
    return [w for k in sorted(per_event) for w in reversed(per_event[k])]


@lru_cache(maxsize=None)
def elo_ratings(jaar: int, K: float, marge: bool, v0: float = 0.0, q: float = 0.0) -> tuple:
    """({key: rating}, {key: variantie}) op de leg-logitschaal.

    v0 == 0: gewone Elo met vaste K. Met marge: S = aandeel gewonnen legs, verwachting logistic(ra-rb) per leg,
    stap K*legs*(S-E) (genormaliseerd op 11 legs). Zonder marge: alleen de uitslag, E = logistic(s*(ra-rb)).
    v0 > 0: Glicko-achtig. Elke speler heeft een variantie (start v0, groeit met q per jaar inactiviteit); de
    update is een Laplace/Kalman-stap: v' = 1/(1/v + info), r += v'*score. Nieuwe spelers bewegen dus snel en
    hun rating blijft (via de start op 0) gekrompen.
    """
    c = rating.context(jaar)
    voor = c["voor"]
    assert all(w.datum < voor for w in c["wed"]), "event op of na de WK-start: lek"
    s_set = rating.sets_schaal(3)
    r: dict = {}
    v: dict = {}
    laatst: dict = {}
    for w in _chronologisch(c["wed"]):
        a, b = w.winnaar, w.verliezer
        for x in (a, b):
            r.setdefault(x, 0.0)
            v.setdefault(x, v0)
            if v0 > 0 and x in laatst:
                v[x] = min(v0, v[x] + q * (w.datum - laatst[x]).days / 365)
            laatst[x] = w.datum
        d = r[a] - r[b]
        if w.sets or not marge:
            s = s_set if w.sets else 2.0
            e = logistic(s * d)
            score, info = s * (1 - e), s * s * e * (1 - e)
        else:
            e = logistic(d)
            n = w.score_w + w.score_v
            score, info = w.score_w - n * e, n * e * (1 - e)
        if v0 > 0:
            for x, sg in ((a, 1), (b, -1)):
                v[x] = 1 / (1 / v[x] + info)
                r[x] += sg * v[x] * score
        else:
            stap = K * score
            r[a] += stap
            r[b] -= stap
    return r, v


def m_elo(grid):
    glicko = "v0" in grid

    def verschil(r, prm):
        c = rating.context(r["jaar"])
        rt, var = elo_ratings(r["jaar"], prm["K"], prm["marge"], prm.dict().get("v0", 0.0), prm.dict().get("q", 0.0))
        k1, k2 = c["keymap"][r["speler1"]], c["keymap"][r["speler2"]]
        d = rt.get(k1, prm["onbekend"]) - rt.get(k2, prm["onbekend"])
        if glicko:  # Glicko-g: onzekere spelers krijgen een vlakker verschil
            vv = var.get(k1, prm["v0"]) + var.get(k2, prm["v0"])
            d /= math.sqrt(1 + math.pi * vv / 8)
        return d

    def afstemmen(rows):
        rows = [r for r in rows if r["odd1"] is not None]
        y = _y(rows)
        best = None
        sleutels = ["K", "marge", "onbekend"] + (["v0", "q"] if glicko else [])
        for combo in itertools.product(*(grid[s] for s in sleutels)):
            basis = dict(zip(sleutels, combo))
            xs = [verschil(r, _p(**basis)) for r in rows]
            for k in grid["k"]:
                ll = np.mean([logloss(wedstrijdkans_uit_d(k * x, r["setsnodig"]), yi) for x, r, yi in zip(xs, rows, y)])
                if best is None or ll < best[1] - 1e-12:
                    best = (_p(**basis, k=k), ll)
        return best[0]

    def kans(r, prm):
        return wedstrijdkans_uit_d(prm["k"] * verschil(r, prm), r["setsnodig"])
    return afstemmen, kans


# ================================================================ ridge-logistisch (zonder intercept)
def fit_ridge(X: np.ndarray, y: np.ndarray, pen: np.ndarray, max_iter: int = 100) -> np.ndarray:
    """MAP van logit P(y=1) = X @ beta met straf 0.5 * sum(pen * beta^2). Geen intercept (symmetrie)."""
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = _sig(X @ beta)
        grad = X.T @ (y - p) - pen * beta
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(pen)
        stap = np.linalg.solve(H + 1e-9 * np.eye(len(beta)), grad)
        beta += stap
        if np.max(np.abs(stap)) < 1e-9:
            break
    return beta


def _folds(rows, k=5, seed=7):
    """Leave-one-year-out als er meerdere trainjaren zijn, anders k vaste willekeurige folds."""
    jaren = sorted({r["jaar"] for r in rows})
    if len(jaren) > 1:
        return [np.array([r["jaar"] == j for r in rows]) for j in jaren]
    rng = np.random.default_rng(seed)
    f = rng.permutation(len(rows)) % k
    return [f == i for i in range(k)]


def _kies_lambda(X, y, rows, lambdas, pen_masker):
    """Lambda met de laagste kruisgevalideerde log-loss op train."""
    best = None
    for lam in lambdas:
        ll = []
        for te in _folds(rows):
            b = fit_ridge(X[~te], y[~te], lam * pen_masker)
            p = np.clip(_sig(X[te] @ b), 1e-6, 1 - 1e-6)
            ll += list(-(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p)))
        m = float(np.mean(ll))
        if best is None or m < best[1] - 1e-12:
            best = (lam, m)
    return best[0]


FEATURES = {
    "rating": lambda r, b: rating.verschil(r, b.halfwaarde, b.lam, b.onbekend),
    "avg": lambda r, b: vorm.vorm(r, "1", "avg", 0.0, 12) - vorm.vorm(r, "2", "avg", 0.0, 12),
    "co": lambda r, b: vorm.vorm(r, "1", "co", 0.0, 12) - vorm.vorm(r, "2", "co", 0.0, 12),
    "markt": lambda r, b: logit(_markt(r)),
    "markt_x_ronde": lambda r, b: logit(_markt(r)) * (r["setsnodig"] - 3),  # ronde mag alleen als interactie
    "rating_wk": lambda r, b: logit(rating.kans(r, b)),
}


def m_lr(grid):
    """Logistische regressie op features met L2; lambda (= 1/C) via kruisvalidatie op train."""
    feats = grid["features"]
    vrij = set(grid.get("niet_bestraft", []))

    def X_(rows, basis, schaal=None):
        X = np.array([[FEATURES[f](r, basis) for f in feats] for r in rows], dtype=float)
        if schaal is None:
            schaal = np.sqrt((X ** 2).mean(axis=0)) + 1e-12  # geen centreren: features zijn antisymmetrisch
        return X / schaal, schaal

    def afstemmen(rows):
        rows = [r for r in rows if r["odd1"] is not None]
        basis = rating.afstemmen(rows) if any(f in ("rating", "rating_wk") for f in feats) else None
        X, schaal = X_(rows, basis)
        y = np.array(_y(rows), dtype=float)
        masker = np.array([0.0 if f in vrij else 1.0 for f in feats])
        lam = _kies_lambda(X, y, rows, grid["lambda"], masker)
        beta = fit_ridge(X, y, lam * masker)
        return _p(basis=basis, schaal=[round(float(s), 6) for s in schaal], lam=lam,
                  beta=[round(float(b), 4) for b in beta], features=list(feats))

    def kans(r, prm):
        X, _ = X_([r], prm["basis"], np.array(prm["schaal"]))
        return float(_sig(X @ np.array(prm["beta"]))[0])
    return afstemmen, kans


# ================================================================ nabewerking: Platt en isotoon
def m_platt(grid):
    from .modellen import MODELLEN
    af, ka = MODELLEN[grid["basis"]]

    def afstemmen(rows):
        rows = [r for r in rows if r["odd1"] is not None]
        b = af(rows)
        c, se, _ = fit_logit(np.array([[logit(ka(r, b))] for r in rows]), np.array(_y(rows)))
        return _p(basis=b, c=round(float(c[0]), 4), c_se=round(float(se[0]), 4))
    return afstemmen, lambda r, prm: logistic(prm["c"] * logit(ka(r, prm["basis"])))


def pav(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Isotone regressie (pool adjacent violators): (gesorteerde x, monotone fit)."""
    o = np.argsort(x)
    x, y = x[o], y[o].astype(float)
    blok = [[v, 1.0] for v in y]
    grenzen = [[i] for i in range(len(y))]
    i = 0
    while i < len(blok) - 1:
        if blok[i][0] > blok[i + 1][0]:
            w = blok[i][1] + blok[i + 1][1]
            blok[i] = [(blok[i][0] * blok[i][1] + blok[i + 1][0] * blok[i + 1][1]) / w, w]
            grenzen[i] += grenzen.pop(i + 1)
            blok.pop(i + 1)
            i = max(i - 1, 0)
        else:
            i += 1
    fit = np.empty(len(y))
    for (v, _), g in zip(blok, grenzen):
        fit[g] = v
    return x, fit


def m_isotoon(grid):
    """Isotoon op de kans van de favoriet (symmetrisch gevouwen), geklemd op [0.5, 0.98]."""
    from .modellen import MODELLEN
    af, ka = MODELLEN[grid["basis"]]

    def afstemmen(rows):
        rows = [r for r in rows if r["odd1"] is not None]
        b = af(rows)
        p = np.array([ka(r, b) for r in rows])
        y = np.array(_y(rows))
        q = np.maximum(p, 1 - p)
        yf = np.where(p >= 0.5, y, 1 - y)
        x, f = pav(q, yf)
        return _p(basis=b, x=[round(float(v), 4) for v in x], f=[round(float(v), 4) for v in f])

    def kans(r, prm):
        p = ka(r, prm["basis"])
        q = max(p, 1 - p)
        f = float(np.interp(q, prm["x"], prm["f"]))
        f = min(max(f, 0.5), 0.98)
        return f if p >= 0.5 else 1 - f
    return afstemmen, kans


# ================================================================ marktblend met krimp op b
def m_blend(grid):
    """logit p = a*logit(markt) + b*logit(p_rating); alleen b krijgt een ridge-straf (naar 0), lambda via CV.

    grid["marge"] kiest de margecorrectie van de marktinput (standaard proportioneel, E024: Shin).
    """
    marge = MARGE[grid.get("marge", "proportioneel")]

    def feats(r, basis):
        return [logit(marge(r["odd1"], r["odd2"])), logit(rating.kans(r, basis))]

    def afstemmen(rows):
        rows = [r for r in rows if r["odd1"] is not None]
        basis = rating.afstemmen(rows)
        X = np.array([feats(r, basis) for r in rows])
        y = np.array(_y(rows), dtype=float)
        masker = np.array([0.0, 1.0])
        lam = _kies_lambda(X, y, rows, grid["lambda"], masker)
        a, b = fit_ridge(X, y, lam * masker)
        return _p(basis=basis, lam=lam, a=round(float(a), 4), b=round(float(b), 4))

    def kans(r, prm):
        lm, lr = feats(r, prm["basis"])
        return logistic(prm["a"] * lm + prm["b"] * lr)
    return afstemmen, kans


def m_niet(grid):
    raise RuntimeError("niet gedraaid")


MODELTYPES = {
    "markt": m_markt, "munt": m_munt, "markt-vlak": m_markt_vlak,
    "blind-underdog": m_markt, "blind-favoriet": m_markt,
    "vorm": _bestaand("vorm"), "rating": _bestaand("rating"), "rating-platt": _bestaand("rating-platt"),
    "rating+markt": _bestaand("rating+markt"), "rating+avg": _bestaand("rating+avg"),
    "bt-halfwaarde": m_bt, "hold": m_hold, "elo": m_elo, "glicko": m_elo, "logreg": m_lr,
    "platt": m_platt, "isotoon": m_isotoon, "blend-krimp": m_blend, "gbm": m_niet,
}
WEDREGEL = {"markt": "geen", "munt": "geen", "blind-underdog": "underdog", "blind-favoriet": "favoriet"}


# ================================================================ bets en metrics
def blind_bets(rows, kant: str) -> list[dict]:
    """Inzet 1 op de underdog of favoriet volgens de odds; gelijke odds overgeslagen."""
    uit = []
    for r in rows:
        if r["odd1"] == r["odd2"]:
            continue
        fav = 1 if r["odd1"] < r["odd2"] else 2
        k = fav if kant == "favoriet" else 3 - fav
        odd = r[f"odd{k}"]
        won = r["winnaar"] == k
        uit.append(dict(jaar=r["jaar"], ronde=r["ronde"], odd=odd, underdog=k != fav, gewonnen=won,
                        resultaat=(odd - 1) if won else -1.0))
    return uit


def kalibratiebins(ps, ys, n=N_BINS) -> list[dict]:
    """Kans van de favoriet (volgens het model) in n bins op [0.5, 1]: gemiddelde kans, frequentie, aantal."""
    q = [max(p, 1 - p) for p in ps]
    yf = [y if p >= 0.5 else 1 - y for p, y in zip(ps, ys)]
    uit = []
    for i in range(n):
        lo, hi = 0.5 + i * 0.5 / n, 0.5 + (i + 1) * 0.5 / n
        sel = [(a, b) for a, b in zip(q, yf) if lo <= a < hi or (i == n - 1 and a == 1.0)]
        uit.append(dict(van=round(lo, 2), tot=round(hi, 2), n=len(sel),
                        kans=round(float(np.mean([a for a, _ in sel])), 4) if sel else None,
                        freq=round(float(np.mean([b for _, b in sel])), 4) if sel else None))
    return uit


def metrics(rows, ps, bl) -> dict:
    ys = _y(rows)
    q = [_markt(r) for r in rows]
    dl = np.array([logloss(p, y) - logloss(x, y) for p, x, y in zip(ps, q, ys)])
    d, se = float(dl.mean()), float(dl.std(ddof=1) / math.sqrt(len(dl)))
    try:
        h = round(helling(ps, ys), 3)
    except (np.linalg.LinAlgError, ValueError):
        h = None  # bijv. munt: alle logits 0
    r = roi(bl)
    lo, hi = bootstrap_geclusterd(bl, n=config.BOOTSTRAP_N)
    clusters = len({(b["jaar"], b["ronde"]) for b in bl})
    verloop, som = [], 0.0
    for b in bl:
        som += b["resultaat"]
        verloop.append(round(som, 2))
    if abs(d) <= RUIS_SE * se or se == 0:
        ruis = "binnen de ruis"
    else:
        ruis = "beter dan de markt" if d < 0 else "slechter dan de markt"
    return dict(
        n=len(rows), logloss=round(float(np.mean([logloss(p, y) for p, y in zip(ps, ys)])), 4),
        brier=round(float(np.mean([brier(p, y) for p, y in zip(ps, ys)])), 4),
        logloss_markt=round(float(np.mean([logloss(p, y) for p, y in zip(q, ys)])), 4),
        brier_markt=round(float(np.mean([brier(p, y) for p, y in zip(q, ys)])), 4),
        verschil_markt=round(d, 4), verschil_se=round(se, 4), ruis=ruis,
        helling=h, kalibratie=kalibratiebins(ps, ys),
        bets=len(bl), underdog_bets=sum(b["underdog"] for b in bl),
        winst=round(sum(b["resultaat"] for b in bl), 2),
        roi=None if r is None else round(r, 4),
        roi_90=[None if lo is None else round(lo, 3), None if hi is None else round(hi, 3)],
        clusters=clusters,
        verloop=verloop,
    )


def _sorteer(rows):
    return sorted(rows, key=lambda r: (r["jaar"], r["datum"] or "", r["wedstrijd"]))


def draai_split(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    if soort == "walk-forward":
        assert max(train) < min(test), f"walk-forward met train {train} niet vóór test {test}: lek"
    assert not set(train) & set(test), "train en test overlappen"
    tr = _sorteer([r for j in train for r in data[j] if r["odd1"] is not None])
    te = _sorteer([r for j in test for r in data[j] if r["odd1"] is not None])
    afstemmen, kans = MODELTYPES[exp["model"]](exp.get("grid", {}))
    prm = afstemmen(tr)          # alleen train
    p_te = [kans(r, prm) for r in te]
    regel = WEDREGEL.get(exp["model"], "drempel")
    if regel == "geen":
        drempel, reden, bl = None, "controle: geen bets", []
    elif regel in ("underdog", "favoriet"):
        drempel, reden, bl = None, f"controle: altijd {regel}, inzet 1", blind_bets(te, regel)
    else:
        p_tr = [kans(r, prm) for r in tr]
        drempel, reden = kies_drempel(drempeltabel(tr, p_tr, config.DREMPELS), config.MIN_BETS_DREMPEL)
        bl = bets(te, p_te, drempel)
    return dict(train=train, test=test, soort=soort, parameters=prm.dict(), drempel=drempel,
                drempel_reden=reden, **metrics(te, p_te, bl))


# ================================================================ E027: inzetbeleid in euro's
def _maxdrawdown(saldi: list[float]) -> float:
    piek, dd = saldi[0] if saldi else 0.0, 0.0
    for x in saldi:
        piek = max(piek, x)
        dd = max(dd, piek - x)
    return round(dd, 2)


def _week(datum: str) -> str:
    """Maandag van de speelweek (ma–zo) als ISO-datum."""
    d = date.fromisoformat(datum)
    return str(date.fromordinal(d.toordinal() - d.weekday()))


def simuleer_kelly(bl: list[dict], start: float, fractie: float) -> dict:
    """Fractionele Kelly: inzet = fractie * (p*o - 1)/(o - 1) * kapitaal, op volgorde van speeldatum."""
    kap, saldi, inzet_tot = start, [start], 0.0
    for b in bl:
        f = max(0.0, fractie * (b["p"] * b["odd"] - 1) / (b["odd"] - 1))
        inzet = round(f * kap, 2)
        inzet_tot += inzet
        kap += inzet * (b["odd"] - 1) if b["gewonnen"] else -inzet
        saldi.append(round(kap, 2))
    return dict(start=start, eind=round(kap, 2), winst=round(kap - start, 2), ingezet=round(inzet_tot, 2),
                max_drawdown=_maxdrawdown(saldi), verloop=saldi[1:])


def simuleer_weekbudget(bl: list[dict], inzet: float, budget: float) -> dict:
    """Vaste inzet; per week (ma–zo) hoogstens `budget` inzetten. Bets die niet meer passen vallen af."""
    winst, saldi, per_week, overgeslagen, geplaatst = 0.0, [0.0], {}, 0, 0
    for b in bl:
        w = per_week.setdefault(_week(b["datum"]), dict(ingezet=0.0, winst=0.0, op=False))
        if w["ingezet"] + inzet > budget + 1e-9:
            w["op"] = True
            overgeslagen += 1
            continue
        w["ingezet"] += inzet
        r = inzet * (b["odd"] - 1) if b["gewonnen"] else -inzet
        w["winst"] += r
        winst += r
        geplaatst += 1
        saldi.append(round(winst, 2))
    weken = [dict(week=k, ingezet=round(v["ingezet"], 2), winst=round(v["winst"], 2), budget_op=v["op"])
             for k, v in sorted(per_week.items())]
    return dict(inzet=inzet, budget=budget, bets=geplaatst, overgeslagen=overgeslagen,
                ingezet=round(sum(w["ingezet"] for w in weken), 2), eind=round(winst, 2),
                max_drawdown=_maxdrawdown(saldi), weken_budget_op=sum(w["budget_op"] for w in weken),
                weken=weken)


def draai_inzet(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """Dezelfde bets als de basis (drempel op train), daarna ¼-Kelly en vaste inzet met weekbudget."""
    g = exp["grid"]
    tr = _sorteer([r for j in train for r in data[j] if r["odd1"] is not None])
    te = _sorteer([r for j in test for r in data[j] if r["odd1"] is not None])
    afstemmen, kans = MODELTYPES[g["basis"]](g)
    prm = afstemmen(tr)
    drempel, reden = kies_drempel(drempeltabel(tr, [kans(r, prm) for r in tr], config.DREMPELS),
                                  config.MIN_BETS_DREMPEL)
    bl = []
    for r in te:
        p = kans(r, prm)
        k = kies_kant(p, r["odd1"], r["odd2"], drempel)
        if k is None:
            continue
        bl.append(dict(datum=r["datum"], odd=r[f"odd{k}"], p=p if k == 1 else 1 - p, gewonnen=r["winnaar"] == k))
    return dict(train=train, test=test, soort=soort, drempel=drempel, drempel_reden=reden, bets=len(bl),
                vast_1=round(sum((b["odd"] - 1) if b["gewonnen"] else -1 for b in bl), 2),
                kelly=simuleer_kelly(bl, g["startkapitaal"], g["kelly_fractie"]),
                weekbudget=[simuleer_weekbudget(bl, i, g["weekbudget"]) for i in g["vaste_inzet"]])


# ================================================================ E028: setstanden
def _d_uit_kans(p: float, n: int) -> float:
    """Legverschil d (logit-schaal) zodat de exacte wedstrijdkans first to n sets gelijk is aan p."""
    lo, hi = -6.0, 6.0
    for _ in range(40):
        m = (lo + hi) / 2
        if wedstrijdkans_uit_d(m, n) < p:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def binomiale_setstanden(p: float, n: int) -> dict:
    """Naïef: elke set onafhankelijk met vaste setkans q, q zo gekozen dat P(wedstrijd) = p."""
    def verdeling(q):
        uit = {}
        for k in range(n):  # verliezer heeft k sets
            c = math.comb(n - 1 + k, k)
            uit[(n, k)] = c * q ** n * (1 - q) ** k
            uit[(k, n)] = c * (1 - q) ** n * q ** k
        return uit
    lo, hi = 0.0, 1.0
    for _ in range(60):
        q = (lo + hi) / 2
        if sum(v for (a, b), v in verdeling(q).items() if a == n) < p:
            lo = q
        else:
            hi = q
    return verdeling((lo + hi) / 2)


def draai_setstand(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """Log-loss van de exacte setstand: set-DP vs binomiaal, beide met de marktkans als wedstrijdkans.

    Er wordt niets afgestemd (hold vast 0.60), dus train wordt niet gebruikt."""
    hold = exp["grid"].get("hold", config.HOLD)
    te = [r for j in test for r in data[j] if r["odd1"] is not None and not r.get("walkover")
          and r.get("sets1") is not None and max(r["sets1"], r["sets2"]) == r["setsnodig"]]
    dp, nf, ll_w = [], [], []
    for r in te:
        p, n = _markt(r), r["setsnodig"]
        ha, hb = rating.hold_uit_legkans(round(_d_uit_kans(p, n), 4), hold)
        v_dp = setstand_verdeling(round(ha, 5), round(hb, 5), n)
        v_nf = binomiale_setstanden(p, n)
        s = (int(r["sets1"]), int(r["sets2"]))
        dp.append(-math.log(max(v_dp.get(s, 0.0), 1e-12)))
        nf.append(-math.log(max(v_nf.get(s, 0.0), 1e-12)))
        ll_w.append(logloss(p, 1 if r["winnaar"] == 1 else 0))
    d = np.array(dp) - np.array(nf)
    return dict(train=train, test=test, soort=soort, n=len(te), logloss_dp=round(float(np.mean(dp)), 4),
                logloss_naief=round(float(np.mean(nf)), 4), logloss_winnaar=round(float(np.mean(ll_w)), 4),
                verschil_naief=round(float(d.mean()), 4),
                verschil_se=round(float(d.std(ddof=1) / math.sqrt(len(d))), 4))


# ================================================================ E029-E031: correct score (zie correctscore.py)
def _cs_rijen(data: dict, jaren: list[int]) -> list[dict]:
    return [r for j in jaren for r in data[j] if r["odd1"] is not None and not r.get("walkover")
            and r.get("sets1") is not None and max(r["sets1"], r["sets2"]) == r["setsnodig"]]


def _cs_ll(rows: list[dict], hold: float, sigma: float) -> np.ndarray:
    from .correctscore import verdeling
    return np.array([-math.log(max(verdeling(_markt(r), r["setsnodig"], hold, sigma)
                                   .get((int(r["sets1"]), int(r["sets2"])), 0.0), 1e-12)) for r in rows])


def draai_cs_param(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """E029/E030: hold of sigma afstemmen op train (log-loss van de setstand), toetsen tegen hold 0,60 en sigma 0."""
    g = exp["grid"]
    holds = g["hold"] if isinstance(g["hold"], list) else [g["hold"]]
    sigmas = g["sigma"] if isinstance(g["sigma"], list) else [g["sigma"]]
    tr, te = _cs_rijen(data, train), _cs_rijen(data, test)
    train_ll = {(h, s): float(_cs_ll(tr, h, s).mean()) for h in holds for s in sigmas}
    h, s = min(train_ll, key=train_ll.get)
    ll, basis = _cs_ll(te, h, s), _cs_ll(te, config.HOLD, 0.0)
    d = ll - basis
    return dict(train=train, test=test, soort=soort, n=len(te), gekozen=dict(hold=h, sigma=s),
                train_logloss={f"hold={a},sigma={b}": round(v, 4) for (a, b), v in train_ll.items()},
                logloss_dp=round(float(ll.mean()), 4), logloss_naief=round(float(basis.mean()), 4),
                basis="set-DP, hold 0,60, σ 0", verschil_naief=round(float(d.mean()), 4),
                verschil_se=round(float(d.std(ddof=1) / math.sqrt(len(d))), 4))


def draai_cs_strategie(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """E031: kies per wedstrijd de meest waarschijnlijke setstand; trefkans, ROI en kalibratie per uitslagtype.

    Niets afgestemd (hold en sigma vast), dus train wordt niet gebruikt. ROI bij inzet 1 tegen odds
    1/(kans·(1+marge)): marge 0 = eerlijke odds."""
    from .correctscore import standen, uitslagtype, verdeling
    g = exp["grid"]
    te = _cs_rijen(data, test)
    picks, typen = [], {}
    for r in te:
        p, n = _markt(r), r["setsnodig"]
        v = verdeling(p, n, g["hold"], g["sigma"])
        echt = (int(r["sets1"]), int(r["sets2"]))
        best = max(v, key=v.get)
        picks.append(dict(n=n, q=v[best], raak=best == echt, type=uitslagtype(best, p, n), cluster=(r["jaar"], r["ronde"])))
        for st in standen(n):
            t = typen.setdefault(uitslagtype(st, p, n), dict(verwacht=0.0, echt=0))
            t["verwacht"] += v[st]
            t["echt"] += st == echt
    for t in typen.values():
        t["verwacht"] = round(t["verwacht"], 2)

    def roi(ps, marge):
        return None if not ps else round(sum((1 / (q["q"] * (1 + marge)) if q["raak"] else 0) for q in ps) / len(ps) - 1, 4)

    def blok(ps):
        if not ps:
            return None
        return dict(n=len(ps), raak=sum(q["raak"] for q in ps), trefkans=round(sum(q["raak"] for q in ps) / len(ps), 4),
                    verwachte_trefkans=round(sum(q["q"] for q in ps) / len(ps), 4),
                    gem_eerlijke_odd=round(sum(1 / q["q"] for q in ps) / len(ps), 2),
                    roi={f"{m:g}": roi(ps, m) for m in g["marges"]},
                    keuzes={k: sum(q["type"] == k for q in ps) for k in sorted({q["type"] for q in ps})})
    # 90%-interval van de ROI bij eerlijke odds: bootstrap per (jaar, ronde)
    rng = np.random.default_rng(1)
    cl = {}
    for q in picks:
        cl.setdefault(q["cluster"], []).append(q)
    sleutels = list(cl)
    boots = []
    for _ in range(config.BOOTSTRAP_N):
        ps = [q for k in rng.choice(len(sleutels), len(sleutels)) for q in cl[sleutels[k]]]
        boots.append(roi(ps, 0.0))
    return dict(train=train, test=test, soort=soort, n=len(te), totaal=blok(picks),
                roi_90_eerlijk=[round(float(np.percentile(boots, 5)), 3), round(float(np.percentile(boots, 95)), 3)],
                clusters=len(sleutels),
                per_format={str(n): blok([q for q in picks if q["n"] == n]) for n in sorted({q["n"] for q in picks})},
                uitslagtypen=dict(sorted(typen.items())))


# ================================================================ E032-E038: correct score finetunen
_CS_STANDAARD = dict(hold=config.HOLD, sigma=0.0, sigma3=None, sigma4=None, sigma0=None, beta_niveau=0.0,
                     beta_vol=0.0, gamma=0.0, kappa=0.0, tiebreak="wissel")


def _cs_profiel(train_rows: list[dict]):
    """Functie r -> (z_niveau, z_vol), gestandaardiseerd met gemiddelde en sd van de train-rijen (ontbreekt: 0)."""
    def niveau(r):
        a, b = r.get("avg1_12m"), r.get("avg2_12m")
        return None if a is None or b is None else (a + b) / 2

    def vol(r):
        w = [r.get(f"avg{k}_3m") for k in (1, 2)] + [r.get(f"avg{k}_12m") for k in (1, 2)]
        return None if None in w else (abs(w[0] - w[2]) + abs(w[1] - w[3])) / 2
    schaal = []
    for f in (niveau, vol):
        w = [x for x in map(f, train_rows) if x is not None]
        mu, sd = (float(np.mean(w)), float(np.std(w, ddof=1))) if len(w) > 1 else (0.0, 1.0)
        schaal.append((f, mu, sd or 1.0))
    return lambda r: tuple(0.0 if f(r) is None else (f(r) - mu) / sd for f, mu, sd in schaal)


def _cs_rij_param(r: dict, c: dict, z: tuple) -> tuple:
    """(hold, sigma, kappa, tiebreak) voor wedstrijd r bij parametercombinatie c."""
    zn, zv = z
    if c["sigma3"] is not None or c["sigma4"] is not None:
        s = c["sigma3" if r["setsnodig"] == 3 else "sigma4"]
        s = c["sigma"] if s is None else s
    elif c["sigma0"] is not None:
        # z afgekapt op ±2 en σ op ≤ 0,6 (na test toegevoegd, zie register E033)
        zn_, zv_ = (max(-2.0, min(2.0, x)) for x in (zn, zv))
        s = min(0.6, c["sigma0"] * math.exp(c["beta_niveau"] * zn_ + c["beta_vol"] * zv_))
    else:
        s = c["sigma"]
    return logistic(logit(c["hold"]) + c["gamma"] * zn), round(s, 4), c["kappa"], c["tiebreak"]


def _cs_ll_c(rows: list[dict], c: dict, prof) -> np.ndarray:
    from .correctscore import verdeling
    return np.array([-math.log(max(verdeling(_markt(r), r["setsnodig"], *_cs_rij_param(r, c, prof(r)))
                                   [(int(r["sets1"]), int(r["sets2"]))], 1e-12)) for r in rows])


def draai_cs_tune(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """E032-E036: combinatie van hold, σ (per format of per wedstrijd), γ, κ en tie-break kiezen op train
    (log-loss van de setstand), toetsen tegen de basis uit grid['basis'].

    `correctscore.verdeling` cachet per (p, n, hold, σ, κ, tie-break), dus combinaties die per wedstrijd dezelfde
    parameters geven, worden één keer gerekend."""
    g = exp["grid"]
    sleutels = [k for k in _CS_STANDAARD if k in g]
    lijsten = [g[k] if isinstance(g[k], list) else [g[k]] for k in sleutels]
    combis = [dict(_CS_STANDAARD, **dict(zip(sleutels, w))) for w in itertools.product(*lijsten)]
    label = [",".join(f"{k}={c[k]}" for k in sleutels) for c in combis]
    tr, te = _cs_rijen(data, train), _cs_rijen(data, test)
    prof = _cs_profiel(tr)
    train_ll = [float(_cs_ll_c(tr, c, prof).mean()) for c in combis]
    top = sorted(range(len(combis)), key=lambda i: train_ll[i])[:10]
    c, basis = combis[top[0]], dict(_CS_STANDAARD, **g["basis"])
    ll, ll_b = _cs_ll_c(te, c, prof), _cs_ll_c(te, basis, prof)
    d = ll - ll_b
    ns = np.array([r["setsnodig"] for r in te])
    return dict(train=train, test=test, soort=soort, n=len(te), gekozen={k: c[k] for k in sleutels},
                n_combinaties=len(combis), train_logloss={label[i]: round(train_ll[i], 4) for i in top},
                test_logloss={label[i]: round(float(_cs_ll_c(te, combis[i], prof).mean()), 4) for i in top},
                logloss_dp=round(float(ll.mean()), 4), logloss_naief=round(float(ll_b.mean()), 4),
                basis=f"hold {basis['hold']:.2f}, σ {basis['sigma']:g}".replace(".", ","),
                verschil_naief=round(float(d.mean()), 4),
                verschil_se=round(float(d.std(ddof=1) / math.sqrt(len(d))), 4) if len(d) > 1 else None,
                per_format={str(n): dict(n_wedstrijden=int((ns == n).sum()), logloss_dp=round(float(ll[ns == n].mean()), 4),
                                         logloss_basis=round(float(ll_b[ns == n].mean()), 4))
                            for n in sorted(set(ns.tolist()))})


def _macht_odds(q: np.ndarray, marge: float) -> np.ndarray:
    """Odds 1/q**k met k < 1 zo dat sum(q**k) = 1 + marge: longshots krijgen relatief meer marge."""
    q = np.maximum(q, 1e-12)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        k = (lo + hi) / 2
        if (q ** k).sum() > 1 + marge:   # sum(q**k) daalt in k
            lo = k
        else:
            hi = k
    return 1 / q ** ((lo + hi) / 2)


def _roi_90(cl: list) -> list:
    """90%-interval van de ROI (inzet 1) met bootstrap per cluster; cl = [[opbrengst, bets], ...] per cluster."""
    a = np.array([v for v in cl if v[1]], dtype=float)
    if not len(a):
        return [None, None]
    idx = np.random.default_rng(1).choice(len(a), size=(config.BOOTSTRAP_N, len(a)))
    r = a[idx, 0].sum(axis=1) / a[idx, 1].sum(axis=1) - 1
    return [round(float(np.percentile(r, 5)), 3), round(float(np.percentile(r, 95)), 3)]


def draai_cs_selectie(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """E037: selectieregel per wedstrijd ('kans', 'ev', 'ev110') tegen een aangenomen boekmakermodel.

    Boekodds: set-DP met σ_boek plus marge, proportioneel (1/(q·(1+m))) of 'macht' (zie `_macht_odds`).
    Niets afgestemd, dus train wordt niet gebruikt."""
    from .correctscore import standen, uitslagtype, verdeling
    g = exp["grid"]
    te = _cs_rijen(data, test)
    picks = {}
    for r in te:
        p, n = _markt(r), r["setsnodig"]
        st = standen(n)
        echt = st.index((int(r["sets1"]), int(r["sets2"])))
        v = np.array([verdeling(p, n, g["hold"], g["sigma"])[s] for s in st])
        for sb in g["sigma_boek"]:
            qb = np.array([verdeling(p, n, g["hold"], sb)[s] for s in st])
            for methode, marge in itertools.product(g["marge_methode"], g["marges"]):
                odd = 1 / (qb * (1 + marge)) if methode == "proportioneel" else _macht_odds(qb, marge)
                ev = v * odd
                for regel in g["regels"]:
                    # bij gelijke EV (afgerond) wint de hoogste eigen kans
                    i = int(np.argmax(v)) if regel == "kans" else max(range(len(st)), key=lambda j: (round(ev[j], 9), v[j]))
                    if regel == "ev110" and ev[i] < 1.10:
                        i = None
                    picks.setdefault((sb, methode, marge, regel), []).append(
                        None if i is None else dict(raak=i == echt, odd=float(odd[i]), type=uitslagtype(st[i], p, n),
                                                    cluster=f"{r['jaar']}-{r['ronde']}"))
    uit = []
    for (sb, methode, marge, regel), ps in picks.items():
        ps = [q for q in ps if q]
        cl = {}
        for q in ps:
            c = cl.setdefault(q["cluster"], [0.0, 0])
            c[0] += q["odd"] if q["raak"] else 0.0
            c[1] += 1
        opbr = sum(c[0] for c in cl.values())
        uit.append(dict(sigma_boek=sb, methode=methode, marge=marge, regel=regel, bets=len(ps),
                        raak=sum(q["raak"] for q in ps), trefkans=round(sum(q["raak"] for q in ps) / len(ps), 4) if ps else None,
                        roi=round(opbr / len(ps) - 1, 4) if ps else None,
                        gem_odd=round(sum(q["odd"] for q in ps) / len(ps), 2) if ps else None,
                        keuzes={k: sum(q["type"] == k for q in ps) for k in sorted({q["type"] for q in ps})},
                        roi_90=_roi_90(list(cl.values())), clusters=[[round(a, 3), b] for a, b in cl.values()]))
    return dict(train=train, test=test, soort=soort, n=len(te), combinaties=uit)


_FAV_BUCKETS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.0)]


def _beslissend_blok(items: list[tuple[float, bool]]) -> dict:
    """items = (kans op de beslissende set, gehaald); verwacht vs echt met z = (echt − verwacht)/se."""
    verw = sum(q for q, _ in items)
    var = sum(q * (1 - q) for q, _ in items)
    echt = sum(b for _, b in items)
    return dict(n=len(items), verwacht=round(verw, 2), echt=int(echt),
                z=round((echt - verw) / math.sqrt(var), 2) if var > 0 else None)


def _per_format_blok(items: list[tuple[int, float, bool]]) -> dict:
    return {str(n): _beslissend_blok([(q, b) for m, q, b in items if m == n]) for n in sorted({m for m, _, _ in items})}


def _achteraf_rijen(data: dict) -> list[tuple[int, int, int, int, float]] | None:
    """(jaar, n, sets winnaar/speler 1, sets speler 2, avg1 − avg2) met de averages ín de wedstrijd zelf:
    WK's uit de csv's plus WK 2022/2023 uit de gecachte Dartsorakel-pagina's. None als die cache ontbreekt."""
    from .events import event_map, laad_wedstrijden
    if not (event_map(config.cache_map()) / "pages").exists():
        return None
    uit = [(j, r["setsnodig"], int(r["sets1"]), int(r["sets2"]), r["avg1_achteraf"] - r["avg2_achteraf"])
           for j in sorted(data) for r in data[j]
           if not r.get("walkover") and r.get("sets1") is not None and r.get("avg1_achteraf") is not None
           and r.get("avg2_achteraf") is not None and max(r["sets1"], r["sets2"]) == r["setsnodig"]]
    wed, _, _ = laad_wedstrijden(config.cache_map(), date(2027, 1, 1))
    wk = [w for w in wed if w.toernooi == "World Championship" and w.sets and w.datum.year in (2022, 2023)
          and w.datum.year not in data and w.avg_w is not None and w.avg_v is not None]
    nodig = {}
    for w in wk:
        nodig[(w.event_key, w.ronde)] = max(nodig.get((w.event_key, w.ronde), 0), w.score_w)
    uit += [(w.datum.year, nodig[(w.event_key, w.ronde)], w.score_w, w.score_v, w.avg_w - w.avg_v)
            for w in wk if w.score_w == nodig[(w.event_key, w.ronde)]]
    return uit


def _achteraf_diagnose(data: dict, hold: float) -> dict | None:
    """Beschrijvend (nooit als feature): legverschil d = c·(avg1 − avg2) met de averages van de wedstrijd zelf,
    c met maximale likelihood op de setstand (σ 0), over alle achteraf-rijen samen."""
    from .correctscore import _interp, standen
    rijen = _achteraf_rijen(data)
    if not rijen:
        return None
    groepen = {}
    for j, n, a, b, x in rijen:
        groepen.setdefault(n, []).append((j, standen(n).index((a, b)), x))

    def kansen(c):
        return {n: _interp(n, hold, c * np.array([x for _, _, x in g])) for n, g in groepen.items()}

    def ll(c):
        k = kansen(c)
        return -sum(np.log(np.maximum(k[n][np.arange(len(g)), [i for _, i, _ in g]], 1e-12)).sum()
                    for n, g in groepen.items()) / len(rijen)
    cs = np.arange(0.0, 1.0001, 0.0025)
    c = float(cs[int(np.argmin([ll(c) for c in cs]))])
    k = kansen(c)
    items = [(j, n, float(k[n][t, n - 1] + k[n][t, n]), standen(n)[i][0] + standen(n)[i][1] == 2 * n - 1)
             for n, g in groepen.items() for t, (j, i, _) in enumerate(g)]
    return dict(c=c, n=len(rijen), logloss=round(float(ll(c)), 4), jaren=sorted({j for j, *_ in rijen}),
                per_format=_per_format_blok([(n, q, b) for _, n, q, b in items]),
                per_jaar={str(j): _beslissend_blok([(q, b) for jj, _, q, b in items if jj == j])
                          for j in sorted({j for j, *_ in items})})


def draai_cs_diagnose(exp: dict, train: list[int], test: list[int], soort: str, data: dict) -> dict:
    """E038: verwacht vs echt aantal beslissende sets (stand n−1 : n−1 bereikt) per model, format en favorietkans.

    De achteraf-diagnose (averages in de wedstrijd zelf) hangt niet van de split af en wordt alleen bij de
    walk-forward-split met test [2025] berekend; anders None."""
    from .correctscore import verdeling
    g = exp["grid"]
    te = _cs_rijen(data, test)
    uit = []
    for c in g["configs"]:
        items = []
        for r in te:
            p, n = _markt(r), r["setsnodig"]
            v = verdeling(p, n, c.get("hold", g["hold"]), c.get("sigma", 0.0), c.get("kappa", 0.0),
                          c.get("tiebreak", "wissel"))
            items.append((n, max(p, 1 - p), v[(n, n - 1)] + v[(n - 1, n)], r["sets1"] + r["sets2"] == 2 * n - 1))
        uit.append(dict(config=c, totaal=_beslissend_blok([(q, b) for _, _, q, b in items]),
                        per_format=_per_format_blok([(n, q, b) for n, _, q, b in items]),
                        per_favoriet={f"{lo:g}-{hi:g}": _beslissend_blok([(q, b) for _, f, q, b in items
                                                                          if lo <= f < hi or (hi == 1.0 and f == 1.0)])
                                      for lo, hi in _FAV_BUCKETS}))
    achteraf = (_achteraf_diagnose(data, g["hold"]) if soort == "walk-forward" and test == [2025] else None)
    return dict(train=train, test=test, soort=soort, n=len(te), configs=uit, achteraf=achteraf)


SPECIAAL = {"inzet": draai_inzet, "setstand": draai_setstand, "cs-hold": draai_cs_param,
            "cs-dagvorm": draai_cs_param, "cs-strategie": draai_cs_strategie, "cs-tune": draai_cs_tune,
            "cs-selectie": draai_cs_selectie, "cs-diagnose": draai_cs_diagnose}


# ================================================================ register, log, criterium
def laad_register(pad: Path | None = None) -> list[dict]:
    reg = json.loads((pad or register_pad()).read_text(encoding="utf-8"))
    ids = [e["id"] for e in reg["experimenten"]]
    assert len(ids) == len(set(ids)), "dubbele experiment-id's"
    for e in reg["experimenten"]:
        for veld in ("id", "datum", "model", "hypothese", "criterium", "na_test_aangepast"):
            if veld not in e:
                raise ValueError(f"{e.get('id')}: veld '{veld}' ontbreekt in het register")
    return reg["experimenten"]


def vingerafdruk(exp: dict) -> str:
    kern = {k: exp.get(k) for k in ("model", "features", "grid", "hypothese", "criterium")}
    return hashlib.sha256(json.dumps(kern, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def context_vingerafdruk() -> str:
    """Hash van wat buiten het register de uitkomst bepaalt: splits, config-grids, drempels en bootstrap."""
    kern = dict(splits=SPLITS, grid=config.GRID, rating_grid=config.RATING_GRID, drempels=config.DREMPELS,
                min_bets=config.MIN_BETS_DREMPEL, hold=config.HOLD, bootstrap=config.BOOTSTRAP_N)
    return hashlib.sha256(json.dumps(kern, sort_keys=True).encode()).hexdigest()[:12]


def git_staat() -> dict:
    """Commit en of het register niet-gecommitte wijzigingen heeft (dan is 'vooraf vastgelegd' niet aantoonbaar)."""
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=config.basis(), capture_output=True, text=True,
                                  timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    return dict(commit=git("rev-parse", "--short", "HEAD") or None,
                register_gewijzigd=bool(git("status", "--porcelain", "--", "experimenten/register.json")))


def lees_log(pad: Path | None = None) -> list[dict]:
    pad = pad or runlog_pad()
    if not pad.exists():
        return []
    return [json.loads(x) for x in pad.read_text(encoding="utf-8").splitlines() if x.strip()]


def log(regel: dict, pad: Path | None = None) -> None:
    pad = pad or runlog_pad()
    pad.parent.mkdir(parents=True, exist_ok=True)
    with pad.open("a", encoding="utf-8") as f:
        f.write(json.dumps(regel, ensure_ascii=False) + "\n")


def protocolcheck(exp: dict, eerdere: list[dict]) -> str | None:
    """Waarschuwing als hypothese/criterium/grid gewijzigd zijn na een eerdere run zonder dat te melden."""
    if not exp["hypothese"].strip() or not exp["criterium"].get("tekst", "").strip():
        raise ValueError(f"{exp['id']}: eerst hypothese en criterium vastleggen, dan pas testjaren evalueren")
    nta = exp["na_test_aangepast"]
    if nta["waarde"] and not nta.get("toelichting", "").strip():
        raise ValueError(f"{exp['id']}: na_test_aangepast is true maar zonder toelichting")
    eigen = [x for x in eerdere if x["id"] == exp["id"]]
    # Vergelijk met de eerste run: anders zou een tweede run een stille wijziging 'witwassen'.
    vorige = [x["vingerafdruk"] for x in eigen if x.get("vingerafdruk")]
    w = []
    if vorige and vorige[0] != vingerafdruk(exp) and not nta["waarde"]:
        w.append("hypothese, criterium of grid is gewijzigd na een eerdere run, maar na_test_aangepast staat op false")
    ctx = [x["context"] for x in eigen if x.get("context")]
    if ctx and ctx[0] != context_vingerafdruk() and not nta["waarde"]:
        w.append("splits, config-grid, drempels of bootstrap zijn gewijzigd sinds de eerste run, maar "
                 "na_test_aangepast staat op false")
    return "; ".join(w) or None


def beoordeel(exp: dict, uitkomsten: list[dict]) -> dict:
    """Criterium op de walk-forward-stappen: succes als in elk testjaar verschil < -factor*se."""
    c = exp["criterium"]
    if c.get("regel") == "verschil_lt_naief":
        f = c.get("factor_se", 1.0)
        wf = [u for u in uitkomsten if u["soort"] == "walk-forward"]
        return dict(succes=bool(wf) and all(u["verschil_naief"] < -f * u["verschil_se"] for u in wf),
                    toelichting="; ".join(f"WK{u['test'][0]}: {u['verschil_naief']:+.4f} (se {u['verschil_se']:.4f})"
                                          for u in wf))
    if c.get("regel") != "verschil_lt_markt":
        return dict(succes=None, toelichting="geen toetsbaar criterium (controle of beschrijvend)")
    f = c.get("factor_se", 1.0)
    wf = [u for u in uitkomsten if u["soort"] == "walk-forward"]
    ok = [u["verschil_markt"] < -f * u["verschil_se"] for u in wf]
    return dict(succes=bool(wf) and all(ok),
                toelichting="; ".join(f"WK{u['test'][0]}: {u['verschil_markt']:+.4f} (se {u['verschil_se']:.4f})"
                                      for u in wf))


def draai(ids: list[str] | None = None, splits=None) -> dict:
    from .terugtest import laad
    reg = laad_register()
    if ids:
        onbekend = set(ids) - {e["id"] for e in reg}
        if onbekend:
            raise ValueError(f"onbekende experimenten: {sorted(onbekend)}")
        reg = [e for e in reg if e["id"] in ids]
    splits = splits or SPLITS
    data, _ = laad(sorted({j for tr, te, _ in splits for j in tr + te}))
    eerdere = lees_log()
    staat = git_staat()
    uit = []
    for exp in reg:
        t0 = time.time()
        res = dict(id=exp["id"], model=exp["model"], vingerafdruk=vingerafdruk(exp))
        try:
            res["protocolwaarschuwing"] = protocolcheck(exp, eerdere)
            if exp.get("status") == "niet_gedraaid":
                res.update(status="niet gedraaid", fout=exp.get("reden_niet_gedraaid", ""), uitkomsten=[])
            else:
                f = SPECIAAL.get(exp["model"], draai_split)
                res["uitkomsten"] = [f(exp, tr, te, s, data) for tr, te, s in splits]
                res["status"] = "ok"
                res["beoordeling"] = beoordeel(exp, res["uitkomsten"])
        except Exception as fout:  # noqa: BLE001 - mislukkingen worden gelogd en gerapporteerd
            res.update(status="mislukt", fout=f"{type(fout).__name__}: {fout}", uitkomsten=[],
                       traceback=traceback.format_exc(limit=3))
        res["duur_s"] = round(time.time() - t0, 1)
        log(dict(tijd=datetime.now(timezone.utc).isoformat(timespec="seconds"), id=exp["id"], status=res["status"],
                 vingerafdruk=res["vingerafdruk"], context=context_vingerafdruk(), **staat,
                 fout=res.get("fout"), duur_s=res["duur_s"],
                 samenvatting={f"{'+'.join(map(str, u['train']))}->{u['test'][0]}":
                               u.get("verschil_markt", u.get("verschil_naief", u.get("vast_1")))
                               for u in res["uitkomsten"]}))
        print(f"{exp['id']} {exp['model']}: {res['status']} ({res['duur_s']} s)")
        uit.append(res)
    return dict(gegenereerd=str(date.today()), splits=[dict(train=tr, test=te, soort=s) for tr, te, s in splits],
                register=reg, resultaten=uit)


def samenvoegen(nieuw: dict, pad: Path) -> dict:
    """Bij een deelrun: vervang alleen de gedraaide experimenten in een bestaand resultatenbestand."""
    if not pad.exists():
        return nieuw
    oud = json.loads(pad.read_text(encoding="utf-8"))
    ids = {r["id"] for r in nieuw["resultaten"]}
    res = [r for r in oud.get("resultaten", []) if r["id"] not in ids] + nieuw["resultaten"]
    reg = laad_register()
    volgorde = {e["id"]: i for i, e in enumerate(reg)}
    res.sort(key=lambda r: volgorde.get(r["id"], 999))
    return dict(nieuw, register=reg, resultaten=res)


# ================================================================ markdown
def _pct(x):
    return "–" if x is None else f"{x:+.1%}"


def _ci(c):
    return "–" if not c or c[0] is None else f"[{c[0]:+.1%}, {c[1]:+.1%}]"


def markdown(v: dict) -> str:
    reg = {e["id"]: e for e in v["register"]}
    L = ["# Experimenten", "",
         "Gegenereerd door `dartswk experimenten` (protocol: [docs/protocol.md](../docs/protocol.md)). "
         "Verschil = log-loss model − markt (proportioneel) per wedstrijd met standaardfout; < 0 = model beter. "
         f"'Binnen de ruis' = |verschil| ≤ {RUIS_SE:g}·se. ROI bij inzet 1, 90%-interval met bootstrap per (jaar, "
         "ronde); 'Clusters' = aantal (jaar, ronde)-clusters met bets. Een WK heeft hoogstens 7 rondes, dus hoogstens 7 clusters per testjaar; dan is het "
         "interval grof en kan het tot ±100% reiken. Helling = c in logit P(winst) = c·logit(p) (1 = goed, < 1 = te stellig).", "",
         "## Walk-forward (hoofdresultaat)", "",
         "| Id | Model | Test | n | Log-loss | Markt | Verschil (se) | Oordeel | Brier | Helling | Bets | ROI [90%] | Clusters |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    gewoon = [r for r in v["resultaten"] if r["model"] not in SPECIAAL]
    for r in gewoon:
        if r["status"] != "ok":
            L.append(f"| {r['id']} | {r['model']} | – | – | – | – | – | **{r['status']}**: {r.get('fout', '')} | – | – | – | – | – |")
            continue
        for u in r["uitkomsten"]:
            if u["soort"] != "walk-forward":
                continue
            h = "–" if u["helling"] is None else f"{u['helling']:.2f}"
            L.append(f"| {r['id']} | {r['model']} | {u['test'][0]} | {u['n']} | {u['logloss']:.4f} | "
                     f"{u['logloss_markt']:.4f} | {u['verschil_markt']:+.4f} ({u['verschil_se']:.4f}) | {u['ruis']} | "
                     f"{u['brier']:.4f} | {h} | {u['bets']} | {_pct(u['roi'])} {_ci(u['roi_90'])} | {u.get('clusters', '–')} |")
    L += ["", "## Vaste richtingen (ter vergelijking; afstemmen op een later jaar is niet walk-forward)", "",
          "| Id | Model | Train → test | Log-loss | Verschil (se) | Bets | ROI [90%] |", "|---|---|---|---|---|---|---|"]
    for r in gewoon:
        for u in r.get("uitkomsten", []):
            if u["soort"] == "richting":
                L.append(f"| {r['id']} | {r['model']} | {'+'.join(map(str, u['train']))} → {u['test'][0]} | "
                         f"{u['logloss']:.4f} | {u['verschil_markt']:+.4f} ({u['verschil_se']:.4f}) | {u['bets']} | "
                         f"{_pct(u['roi'])} {_ci(u['roi_90'])} |")
    for r in v["resultaten"]:
        if r["model"] == "setstand" and r["status"] == "ok":
            L += ["", f"## {r['id']}: setstanden (log-loss van de exacte eindstand in sets)", "",
                  "Marktkans (proportioneel) → legverschil → exacte set-DP, tegen een binomiale verdeling met dezelfde "
                  "wedstrijdkans. Niets afgestemd (hold 0,60).", "",
                  "| Train → test | Soort | n | Set-DP | Binomiaal | Verschil (se) | Log-loss winnaar |",
                  "|---|---|---|---|---|---|---|"]
            for u in r["uitkomsten"]:
                L.append(f"| {'+'.join(map(str, u['train']))} → {u['test'][0]} | {u['soort']} | {u['n']} | "
                         f"{u['logloss_dp']:.4f} | {u['logloss_naief']:.4f} | {u['verschil_naief']:+.4f} "
                         f"({u['verschil_se']:.4f}) | {u['logloss_winnaar']:.4f} |")
        if r["model"] in ("cs-hold", "cs-dagvorm") and r["status"] == "ok":
            L += ["", f"## {r['id']}: correct score, {reg[r['id']].get('naam', '')}", "",
                  "Parameter gekozen op train (log-loss van de setstand); getoetst tegen de basis (set-DP, hold 0,60, σ 0).", "",
                  "| Train → test | Soort | n | Gekozen | Log-loss | Basis | Verschil (se) |", "|---|---|---|---|---|---|---|"]
            for u in r["uitkomsten"]:
                k = u["gekozen"]
                L.append(f"| {'+'.join(map(str, u['train']))} → {u['test'][0]} | {u['soort']} | {u['n']} | "
                         f"hold {k['hold']}, σ {k['sigma']} | {u['logloss_dp']:.4f} | {u['logloss_naief']:.4f} | "
                         f"{u['verschil_naief']:+.4f} ({u['verschil_se']:.4f}) |")
        if r["model"] == "cs-strategie" and r["status"] == "ok":
            marges = reg[r["id"]]["grid"]["marges"]
            L += ["", f"## {r['id']}: correct score, meest waarschijnlijke setstand", "",
                  "ROI bij inzet 1 tegen odds 1/(kans·(1+marge)). Niets afgestemd, dus train speelt geen rol.", "",
                  "| Test | n | Raak | Trefkans (verwacht) | Gem. eerlijke odd | "
                  + " | ".join(f"ROI marge {m:.0%}" for m in marges) + " | 90%-int. ROI eerlijk |",
                  "|---|---|---|---|---|" + "---|" * (len(marges) + 1)]
            gezien = set()
            for u in r["uitkomsten"]:
                if u["test"][0] in gezien:
                    continue
                gezien.add(u["test"][0])
                t = u["totaal"]
                L.append(f"| {u['test'][0]} | {t['n']} | {t['raak']} | {t['trefkans']:.1%} ({t['verwachte_trefkans']:.1%}) | "
                         f"{t['gem_eerlijke_odd']:.2f} | " + " | ".join(_pct(t['roi'][f'{m:g}']) for m in marges)
                         + f" | {_ci(u['roi_90_eerlijk'])} |")
            sl = sorted(set().union(*(u["uitslagtypen"] for u in r["uitkomsten"])))
            L += ["", "Uitslagtypen (verwacht volgens het model / werkelijk), per testjaar:", "",
                  "| Test | " + " | ".join(sl) + " |", "|---|" + "---|" * len(sl)]
            gezien = set()
            for u in r["uitkomsten"]:
                if u["test"][0] in gezien:
                    continue
                gezien.add(u["test"][0])
                ty = u["uitslagtypen"]
                L.append(f"| {u['test'][0]} | " + " | ".join(
                    f"{ty[k]['verwacht']:.1f} / {ty[k]['echt']}" if k in ty else "–"
                    for k in sl) + " |")
        if r["model"] == "cs-tune" and r["status"] == "ok":
            L += ["", f"## {r['id']}: correct score, {reg[r['id']].get('naam', '')}", "",
                  f"Combinatie gekozen op train (log-loss van de setstand, {r['uitkomsten'][0]['n_combinaties']} "
                  f"combinaties); getoetst tegen de basis (set-DP, {r['uitkomsten'][0]['basis']}).", "",
                  "| Train → test | Soort | n | Gekozen | Log-loss | Basis | Verschil (se) |", "|---|---|---|---|---|---|---|"]
            for u in r["uitkomsten"]:
                se = "–" if u["verschil_se"] is None else f"{u['verschil_se']:.4f}"
                L.append(f"| {'+'.join(map(str, u['train']))} → {u['test'][0]} | {u['soort']} | {u['n']} | "
                         + ", ".join(f"{k} {v}" for k, v in u["gekozen"].items())
                         + f" | {u['logloss_dp']:.4f} | {u['logloss_naief']:.4f} | {u['verschil_naief']:+.4f} ({se}) |")
        if r["model"] == "cs-selectie" and r["status"] == "ok":
            uniek = {}
            for u in r["uitkomsten"]:
                uniek.setdefault(u["test"][0], u)
            wf = sorted({u["test"][0] for u in r["uitkomsten"] if u["soort"] == "walk-forward"})

            def cel(c):
                if not c["bets"]:
                    return "0"
                return f"{c['bets']} / {c['trefkans']:.1%} / {_pct(c['roi'])} {_ci(c['roi_90'])}"
            L += ["", f"## {r['id']}: correct score, selectieregel tegen een boekmakermodel", "",
                  "Eigen model tegen aangenomen boekodds (set-DP met σ_boek plus marge; geen echte CS-odds). Per cel: "
                  "bets / trefkans / ROI bij inzet 1 [90%-interval, bootstrap per (jaar, ronde)]. Totaal over de "
                  f"unieke testjaren ({', '.join(map(str, sorted(uniek)))}). Niets afgestemd.", "",
                  "| σ_boek | Marge | Regel | " + " | ".join(f"WK{j}" for j in wf) + " | Totaal |",
                  "|---|---|---|" + "---|" * (len(wf) + 1)]
            for i, c in enumerate(uniek[wf[0]]["combinaties"] if wf else []):
                alle = [u["combinaties"][i] for u in uniek.values()]
                bets, raak = sum(a["bets"] for a in alle), sum(a["raak"] for a in alle)
                cl = [k for a in alle for k in a["clusters"]]
                tot = dict(bets=bets, trefkans=raak / bets if bets else None, roi_90=_roi_90(cl),
                           roi=sum(k[0] for k in cl) / bets - 1 if bets else None)
                L.append(f"| {c['sigma_boek']:g} | {c['marge']:.0%} {c['methode']} | {c['regel']} | "
                         + " | ".join(cel(uniek[j]["combinaties"][i]) for j in wf) + f" | {cel(tot)} |")
        if r["model"] == "cs-diagnose" and r["status"] == "ok":
            uniek = {}
            for u in r["uitkomsten"]:
                uniek.setdefault(u["test"][0], u)
            fm = sorted({n for u in uniek.values() for c in u["configs"] for n in c["per_format"]}, key=int)

            def blk(b):
                if not b:
                    return "–"
                z = "–" if b["z"] is None else f"{b['z']:+.1f}"
                return f"{b['verwacht']:.1f} / {b['echt']} ({z})"
            L += ["", f"## {r['id']}: correct score, beslissende sets (n−1 : n−1) verwacht vs echt", "",
                  "Per cel: verwacht / echt (z = (echt − verwacht)/se). Wedstrijdkans = marktkans.", "",
                  "| Test | Model | Totaal | " + " | ".join(f"first to {n}" for n in fm) + " |",
                  "|---|---|---|" + "---|" * len(fm)]
            for j, u in sorted(uniek.items()):
                for c in u["configs"]:
                    L.append(f"| {j} | " + ", ".join(f"{k} {v}" for k, v in c["config"].items()) + f" | {blk(c['totaal'])} | "
                             + " | ".join(blk(c["per_format"].get(n)) for n in fm) + " |")
            a = next((u["achteraf"] for u in r["uitkomsten"] if u.get("achteraf")), None)
            if a:
                L += ["", f"Achteraf (beschrijvend, nooit als feature): legverschil d = c·(avg1 − avg2) met de averages "
                      f"van de wedstrijd zelf, σ 0; c = {a['c']:g} (max. likelihood op WK {', '.join(map(str, a['jaren']))}, "
                      f"n = {a['n']}).", "",
                      "| Groep | n | Verwacht / echt (z) |", "|---|---|---|"]
                L += [f"| first to {n} | {b['n']} | {blk(b)} |" for n, b in a["per_format"].items()]
                L += [f"| WK{j} | {b['n']} | {blk(b)} |" for j, b in a["per_jaar"].items()]
        if r["model"] == "inzet" and r["status"] == "ok":
            g = reg[r["id"]]["grid"]
            L += ["", f"## {r['id']}: inzetbeleid in euro's (bets van de marktblend)", "",
                  f"¼-Kelly met start €{g['startkapitaal']}; vaste inzet met hoogstens €{g['weekbudget']} per week "
                  "(ma–zo, speeldatum). Drawdown = grootste daling vanaf een piek.", "",
                  "| Train → test | Soort | Bets | Inzet 1 (eenheden) | ¼-Kelly eind (drawdown) | "
                  + " | ".join(f"€{i} vast: winst (drawdown, weken budget op)" for i in g["vaste_inzet"]) + " |",
                  "|---|---|---|---|---|" + "---|" * len(g["vaste_inzet"])]
            for u in r["uitkomsten"]:
                k = u["kelly"]
                L.append(f"| {'+'.join(map(str, u['train']))} → {u['test'][0]} | {u['soort']} | {u['bets']} | "
                         f"{u['vast_1']:+.2f} | €{k['eind']:.2f} (€{k['max_drawdown']:.2f}) | "
                         + " | ".join(f"€{w['eind']:+.2f} (€{w['max_drawdown']:.2f}, {w['weken_budget_op']}; "
                                      f"{w['overgeslagen']} overgeslagen)" for w in u["weekbudget"]) + " |")
    L += ["", "## Hypothesen, criteria en beoordeling", ""]
    for r in v["resultaten"]:
        e = reg[r["id"]]
        b = r.get("beoordeling") or {}
        succ = {True: "**gehaald**", False: "niet gehaald", None: "n.v.t."}[b.get("succes")]
        L += [f"### {r['id']}: {e.get('naam', e['model'])}", "",
              f"- Hypothese ({e['datum']}): {e['hypothese']}",
              f"- Criterium: {e['criterium'].get('tekst', '')} → {succ} ({b.get('toelichting', r.get('fout', ''))})",
              f"- Na test aangepast: {'ja' if e['na_test_aangepast']['waarde'] else 'nee'}"
              + (f" ({e['na_test_aangepast']['toelichting']})" if e['na_test_aangepast'].get('toelichting') else ""),
              f"- Status: {r['status']}" + (f"; waarschuwing: {r['protocolwaarschuwing']}" if r.get("protocolwaarschuwing") else ""),
              ""]
    return "\n".join(L) + "\n"
