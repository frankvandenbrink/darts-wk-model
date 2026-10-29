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
