from dartswk import correctscore as cs
from dartswk.setmodel import setstand_verdeling
from dartswk import rating
from dartswk import experimenten as x


def test_verdeling_som_en_wedstrijdkans():
    for n in (3, 4, 7):
        for sigma in (0.0, 0.4):
            v = cs.verdeling(0.7, n, 0.6, sigma)
            assert abs(sum(v.values()) - 1) < 1e-9
            assert abs(sum(q for (a, _), q in v.items() if a == n) - 0.7) < 2e-3
            assert set(v) == set(cs.standen(n))


def test_gelijk_aan_exacte_dp_zonder_sigma():
    p, n = 0.674, 3
    ha, hb = rating.hold_uit_legkans(round(x._d_uit_kans(p, n), 4), 0.6)
    exact = setstand_verdeling(round(ha, 5), round(hb, 5), n)
    v = cs.verdeling(p, n)
    assert all(abs(v[s] - exact[s]) < 2e-3 for s in exact)


def test_dagvorm_geeft_meer_whitewashes():
    v0, v4 = cs.verdeling(0.7, 3, sigma=0.0), cs.verdeling(0.7, 3, sigma=0.4)
    assert v4[(3, 0)] > v0[(3, 0)] and v4[(0, 3)] > v0[(0, 3)]
    assert v4[(3, 2)] < v0[(3, 2)]


def test_uitslagtype_vanuit_favoriet():
    assert cs.uitslagtype((3, 1), 0.7, 3) == "fav 3-1"
    assert cs.uitslagtype((3, 1), 0.3, 3) == "und 3-1"
    assert cs.uitslagtype((0, 3), 0.3, 3) == "fav 3-0"


def test_eerlijke_odds():
    o = cs.eerlijke_odds(0.5, 3)
    assert o["3-0"] == o["0-3"] and o["3-2"] == o["2-3"]


def test_ext_zonder_momentum_gelijk_aan_setstand_verdeling():
    for ha, hb, n in ((0.71, 0.55, 3), (0.6, 0.6, 4), (0.83, 0.42, 7)):
        exact = setstand_verdeling(ha, hb, n)
        ext = cs._setstand_ext(ha, hb, n, 0.0, "wissel")
        assert all(abs(ext[s] - exact[s]) < 1e-12 for s in exact)


def test_momentum_meer_whitewashes_minder_beslissende_sets():
    v0, vk = cs.verdeling(0.7, 3), cs.verdeling(0.7, 3, kappa=0.3)
    assert abs(sum(q for (a, _), q in vk.items() if a == 3) - 0.7) < 2e-3
    assert vk[(3, 0)] > v0[(3, 0)] and vk[(0, 3)] > v0[(0, 3)]
    assert vk[(3, 2)] < v0[(3, 2)] and vk[(2, 3)] < v0[(2, 3)]
    ext = cs._setstand_ext(0.7, 0.55, 4, 0.3)
    assert abs(sum(ext.values()) - 1) < 1e-9 and ext[(4, 3)] < setstand_verdeling(0.7, 0.55, 4)[(4, 3)]


def test_tiebreak_bull_bijna_gelijk():
    for n in (3, 7):
        w, b = cs.verdeling(0.62, n, sigma=0.3), cs.verdeling(0.62, n, sigma=0.3, tiebreak="bull")
        assert abs(sum(b.values()) - 1) < 1e-9
        assert abs(sum(q for (a, _), q in b.items() if a == n) - 0.62) < 2e-3
        assert max(abs(w[s] - b[s]) for s in w) < 0.01


def test_hold_afgerond_voor_tabel():
    assert cs.verdeling(0.7, 3, hold=0.6012) == cs.verdeling(0.7, 3, hold=0.6)
