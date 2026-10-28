import math

import numpy as np

from dartswk import kalibratie
from dartswk.rating import RatingParams, logit


def _synthetisch(n, a, b, seed=3):
    rng = np.random.default_rng(seed)
    lm = rng.normal(0, 1.2, n)                 # logit markt
    lr = 0.6 * lm + rng.normal(0, 0.8, n)      # logit rating, gecorreleerd met de markt
    p = 1 / (1 + np.exp(-(a * lm + b * lr)))
    y = (rng.random(n) < p).astype(int)
    return lm, lr, y


def test_fit_logit_vindt_a_en_b_terug():
    lm, lr, y = _synthetisch(40000, 0.8, 0.4)
    beta, se, _ = kalibratie.fit_logit(np.column_stack([lm, lr]), y)
    assert abs(beta[0] - 0.8) < 3 * se[0] + 0.01
    assert abs(beta[1] - 0.4) < 3 * se[1] + 0.01
    assert se[0] < 0.05 and se[1] < 0.05


def test_fit_logit_b_nul_als_rating_niets_toevoegt():
    lm, lr, y = _synthetisch(40000, 1.0, 0.0)
    beta, se, _ = kalibratie.fit_logit(np.column_stack([lm, lr]), y)
    assert abs(beta[1]) < 3 * se[1]


def test_helling_van_goed_gekalibreerde_kansen_is_een():
    rng = np.random.default_rng(5)
    p = rng.uniform(0.05, 0.95, 40000)
    y = (rng.random(len(p)) < p).astype(int)
    assert abs(kalibratie.helling(list(p), list(y)) - 1.0) < 0.05
    # te stellige kansen (logit x 2) geven helling ~0.5
    p2 = 1 / (1 + np.exp(-2 * np.log(p / (1 - p))))
    assert abs(kalibratie.helling(list(p2), list(y)) - 0.5) < 0.03


def test_combi_kans_volgt_de_formule(monkeypatch):
    monkeypatch.setattr(kalibratie, "rating_kans", lambda r, prm: 0.7)
    prm = kalibratie.CombiParams(RatingParams(365, 1.0, -0.3, 1.0), a=0.6, b=0.5, a_se=0.1, b_se=0.1)
    r = dict(odd1=1.5, odd2=2.8)
    q = (1 / 1.5) / (1 / 1.5 + 1 / 2.8)
    verwacht = 1 / (1 + math.exp(-(0.6 * logit(q) + 0.5 * logit(0.7))))
    assert math.isclose(kalibratie.combi_kans(r, prm), verwacht, rel_tol=1e-12)
    # symmetrie: spelers omdraaien geeft 1 - p
    monkeypatch.setattr(kalibratie, "rating_kans", lambda r, prm: 0.3)
    assert math.isclose(kalibratie.combi_kans(dict(odd1=2.8, odd2=1.5), prm), 1 - verwacht, rel_tol=1e-12)


def test_combi_afstemmen_rapporteert_a_en_b(monkeypatch):
    lm, lr, y = _synthetisch(3000, 0.9, 0.3)
    rows = []
    for x_m, x_r, yi in zip(lm, lr, y):
        q = 1 / (1 + math.exp(-x_m))
        rows.append(dict(odd1=1 / q, odd2=1 / (1 - q), winnaar=1 if yi else 2, p_rating=1 / (1 + math.exp(-x_r))))
    monkeypatch.setattr(kalibratie, "rating_afstemmen", lambda rows: RatingParams(365, 1.0, -0.3, 1.0))
    monkeypatch.setattr(kalibratie, "rating_kans", lambda r, prm: r["p_rating"])
    prm = kalibratie.combi_afstemmen(rows)
    assert abs(prm.a - 0.9) < 3 * prm.a_se and abs(prm.b - 0.3) < 3 * prm.b_se
    assert prm.lr_b > 0
    assert set(prm.dict()) == {"basis", "a", "a_se", "b", "b_se", "lr_b_train"}
