import math
from datetime import date, timedelta

import numpy as np
import pytest

from dartswk.events import Wedstrijd
from dartswk.rating import fit_bt, hold_uit_legkans, logistic, sets_schaal, wedstrijdkans_uit_d

VOOR = date(2024, 1, 1)


def _w(a, b, la, lb, dagen=10, sets=False):
    """Wedstrijd tussen a en b met la-lb legs, `dagen` vóór VOOR (winnaar eerst)."""
    w, v, sw, sv = (a, b, la, lb) if la > lb else (b, a, lb, la)
    return Wedstrijd(datum=VOOR - timedelta(days=dagen), event_key=1, toernooi="PC", ronde="x", winnaar=w,
                     verliezer=v, score_w=sw, score_v=sv, avg_w=None, avg_v=None, sets=sets)


def _simuleer(r, n_wed, rng, eerst_tot=6):
    """Wedstrijden first to `eerst_tot` legs met legkans logistic(r_a - r_b)."""
    wed = []
    for _ in range(n_wed):
        a, b = rng.choice(len(r), size=2, replace=False)
        p = logistic(r[a] - r[b])
        la = lb = 0
        while la < eerst_tot and lb < eerst_tot:
            if rng.random() < p:
                la += 1
            else:
                lb += 1
        wed.append(_w(int(a), int(b), la, lb, dagen=int(rng.integers(1, 300))))
    return wed


def test_bt_vindt_bekende_sterktes_terug():
    rng = np.random.default_rng(7)
    echt = np.linspace(-0.8, 0.8, 12)
    wed = _simuleer(echt, 4000, rng)
    r = fit_bt(wed, VOOR, halfwaarde=1e9, lam=1e-3)
    schat = np.array([r[i] for i in range(12)])
    schat -= schat.mean()
    assert np.max(np.abs(schat - (echt - echt.mean()))) < 0.08
    assert np.corrcoef(schat, echt)[0, 1] > 0.99


def test_krimp_naar_nul_bij_weinig_data_en_sterkere_prior():
    # speler 0 wint 1 wedstrijd 6-2, speler 1 wint 20 wedstrijden 6-2 (tegen dezelfde middenmoter 9)
    wed = [_w(0, 9, 6, 2)] + [_w(1, 9, 6, 2) for _ in range(20)] + [_w(9, 8, 6, 6 - 1) for _ in range(5)]
    zwak = fit_bt(wed, VOOR, halfwaarde=1e9, lam=0.5)
    sterk = fit_bt(wed, VOOR, halfwaarde=1e9, lam=5.0)
    assert 0 < zwak[0] < zwak[1]                      # weinig data: dichter bij 0
    assert abs(sterk[0]) < abs(zwak[0]) and abs(sterk[1]) < abs(zwak[1])
    assert abs(sum(sterk.values())) < 1e-6            # prior rond 0: gemiddelde blijft 0 (ridge, gelijke prior)


def test_tijdsweging_telt_recente_wedstrijden_zwaarder():
    # speler 0 won lang geleden ruim van 1, verloor recent ruim van 1
    wed = [_w(0, 1, 6, 1, dagen=700) for _ in range(10)] + [_w(0, 1, 1, 6, dagen=10) for _ in range(10)]
    kort = fit_bt(wed, VOOR, halfwaarde=60, lam=0.1)
    lang = fit_bt(wed, VOOR, halfwaarde=1e9, lam=0.1)
    assert kort[0] - kort[1] < -1.0
    assert abs(lang[0] - lang[1]) < 1e-6


def test_cutoff_assert_weigert_wedstrijd_op_of_na_de_wk_start():
    wed = [_w(0, 1, 6, 3, dagen=5), _w(0, 1, 6, 3, dagen=0)]  # dagen=0: op de WK-start
    with pytest.raises(AssertionError, match="cutoff"):
        fit_bt(wed, VOOR, halfwaarde=365, lam=1.0)


def test_sets_wedstrijd_telt_alleen_de_uitslag():
    # 7-4 in sets mag niet als 7-4 in legs tellen: één gewonnen wedstrijd met schaal s
    legs = fit_bt([_w(0, 1, 7, 4)], VOOR, halfwaarde=1e9, lam=1.0)
    sets = fit_bt([_w(0, 1, 7, 4, sets=True)], VOOR, halfwaarde=1e9, lam=1.0)
    s = sets_schaal(3)
    d = sets[0] - sets[1]
    # stationair punt voor r_0 = d/2 = -r_1: s * (1 - logistic(s*d)) = lam * d/2
    assert math.isclose(s * (1 - logistic(s * d)), 1.0 * d / 2, rel_tol=1e-6)
    assert not math.isclose(d, legs[0] - legs[1], rel_tol=1e-3)
    assert 2 < s < 8


@pytest.mark.parametrize("d", [-1.0, -0.2, 0.0, 0.3, 1.2])
def test_hold_kansen_geven_de_bt_legkans(d):
    ha, hb = hold_uit_legkans(d)
    assert math.isclose(0.5 * (ha + 1 - hb), logistic(d), abs_tol=1e-9)
    if d == 0.0:
        assert math.isclose(ha, 0.6, abs_tol=1e-9) and math.isclose(hb, 0.6, abs_tol=1e-9)


def test_wedstrijdkans_monotoon_en_symmetrisch():
    assert math.isclose(wedstrijdkans_uit_d(0.0, 3), 0.5, abs_tol=1e-9)
    ps = [wedstrijdkans_uit_d(d, 4) for d in (-0.5, -0.1, 0.1, 0.5)]
    assert ps == sorted(ps)
    assert math.isclose(wedstrijdkans_uit_d(0.3, 5) + wedstrijdkans_uit_d(-0.3, 5), 1.0, abs_tol=1e-4)
    # langere wedstrijd: favoriet wint vaker
    assert wedstrijdkans_uit_d(0.2, 7) > wedstrijdkans_uit_d(0.2, 3)
