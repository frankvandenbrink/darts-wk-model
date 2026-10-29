"""Kalibratie en combinatie met de markt.

- Logistische regressie zonder intercept (Newton). Zonder intercept omdat speler1/speler2 een willekeurige
  volgorde is: een intercept zou speler1 een voordeel geven dat niet bestaat.
- Platt (symmetrisch): logit p = c * logit(p_rating), c gefit op train.
- Combinatie: logit p = a * logit(markt) + b * logit(p_rating), a en b gefit op train. Markt = proportioneel.
- Kalibratiehelling: dezelfde regressie van de uitslag op logit(p) op de testdata; 1 = goed gekalibreerd,
  < 1 = te stellig, > 1 = te vlak.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .evaluatie import markt_proportioneel
from .rating import RatingParams, afstemmen as rating_afstemmen, kans as rating_kans, logit


def fit_logit(X: np.ndarray, y: np.ndarray, max_iter: int = 100) -> tuple[np.ndarray, np.ndarray, float]:
    """(coëfficiënten, standaardfouten, log-likelihood) van logit P(y=1) = X @ beta, zonder intercept."""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if X.shape[0] != len(y):
        X = X.T
    y = np.asarray(y, dtype=float)
    beta = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = 1 / (1 + np.exp(-(X @ beta)))
        grad = X.T @ (y - p)
        H = (X * (p * (1 - p))[:, None]).T @ X
        stap = np.linalg.solve(H, grad)
        beta += stap
        if np.max(np.abs(stap)) < 1e-10:
            break
    p = np.clip(1 / (1 + np.exp(-(X @ beta))), 1e-12, 1 - 1e-12)
    H = (X * (p * (1 - p))[:, None]).T @ X
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return beta, se, ll


def helling(ps: list[float], ys: list[int]) -> float:
    """Kalibratiehelling: c in logit P(y=1) = c * logit(p)."""
    beta, _, _ = fit_logit(np.array([[logit(p)] for p in ps]), np.array(ys))
    return float(beta[0])


def _y(rows):
    return np.array([1 if r["winnaar"] == 1 else 0 for r in rows])


# ---------------------------------------------------------------- Platt
@dataclass(frozen=True)
class PlattParams:
    basis: RatingParams
    c: float
    c_se: float

    def dict(self) -> dict:
        return dict(basis=self.basis.dict(), c=round(self.c, 4), c_se=round(self.c_se, 4))


def platt_afstemmen(rows: list[dict]) -> PlattParams:
    rows = [r for r in rows if r["odd1"] is not None]
    basis = rating_afstemmen(rows)
    X = np.array([[logit(rating_kans(r, basis))] for r in rows])
    beta, se, _ = fit_logit(X, _y(rows))
    return PlattParams(basis, float(beta[0]), float(se[0]))


def platt_kans(r: dict, prm: PlattParams) -> float:
    return 1 / (1 + math.exp(-prm.c * logit(rating_kans(r, prm.basis))))


# ---------------------------------------------------------------- rating + markt
@dataclass(frozen=True)
class CombiParams:
    basis: RatingParams
    a: float
    b: float
    a_se: float
    b_se: float
    lr_b: float = field(default=float("nan"))  # LR-statistiek voor b = 0 (1 vrijheidsgraad), op train

    def dict(self) -> dict:
        return dict(basis=self.basis.dict(), a=round(self.a, 4), a_se=round(self.a_se, 4),
                    b=round(self.b, 4), b_se=round(self.b_se, 4), lr_b_train=round(self.lr_b, 3))


def combi_features(r: dict, basis: RatingParams) -> list[float]:
    return [logit(markt_proportioneel(r["odd1"], r["odd2"])), logit(rating_kans(r, basis))]


def combi_afstemmen(rows: list[dict]) -> CombiParams:
    rows = [r for r in rows if r["odd1"] is not None]
    basis = rating_afstemmen(rows)
    X = np.array([combi_features(r, basis) for r in rows])
    y = _y(rows)
    beta, se, ll = fit_logit(X, y)
    _, _, ll0 = fit_logit(X[:, :1], y)
    return CombiParams(basis, float(beta[0]), float(beta[1]), float(se[0]), float(se[1]), 2 * (ll - ll0))


def combi_kans(r: dict, prm: CombiParams) -> float:
    lm, lr = combi_features(r, prm.basis)
    return 1 / (1 + math.exp(-(prm.a * lm + prm.b * lr)))


# ---------------------------------------------------------------- controle: alleen de markt vlakker/steiler
@dataclass(frozen=True)
class MarktKrimpParams:
    a: float
    a_se: float

    def dict(self) -> dict:
        return dict(a=round(self.a, 4), a_se=round(self.a_se, 4))


def marktkrimp_afstemmen(rows: list[dict]) -> MarktKrimpParams:
    """logit p = a * logit(markt), zonder rating. Controle: zit de winst van rating+markt alleen in de krimp?"""
    rows = [r for r in rows if r["odd1"] is not None]
    X = np.array([[logit(markt_proportioneel(r["odd1"], r["odd2"]))] for r in rows])
    beta, se, _ = fit_logit(X, _y(rows))
    return MarktKrimpParams(float(beta[0]), float(se[0]))


def marktkrimp_kans(r: dict, prm: MarktKrimpParams) -> float:
    return 1 / (1 + math.exp(-prm.a * logit(markt_proportioneel(r["odd1"], r["odd2"]))))
