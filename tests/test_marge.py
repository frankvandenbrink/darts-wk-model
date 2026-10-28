import pytest

from dartswk.evaluatie import markt_proportioneel, markt_shin, shin_kansen


@pytest.mark.parametrize("o1,o2", [(1.80, 2.00), (1.10, 7.00), (1.01, 21.0), (3.75, 1.29), (1.91, 1.91)])
def test_margecorrectie_somt_tot_1(o1, o2):
    p = markt_proportioneel(o1, o2)
    assert p + markt_proportioneel(o2, o1) == pytest.approx(1.0)
    s = shin_kansen([o1, o2])
    assert sum(s) == pytest.approx(1.0, abs=1e-9)
    assert markt_shin(o1, o2) == pytest.approx(s[0])
    assert 0 < p < 1 and 0 < s[0] < 1


def test_proportioneel_waarde():
    # 1/1.8 = 0.5556, 1/2.0 = 0.5 -> 0.5556 / 1.0556
    assert markt_proportioneel(1.8, 2.0) == pytest.approx(0.526316, abs=1e-6)


def test_shin_drukt_longshot_meer_dan_proportioneel():
    # Shin legt meer van de marge bij de longshot: de favoriet krijgt een hogere kans dan proportioneel
    assert markt_shin(1.10, 7.0) > markt_proportioneel(1.10, 7.0)


def test_gelijke_odds_half():
    assert markt_shin(1.91, 1.91) == pytest.approx(0.5)
    assert markt_proportioneel(1.91, 1.91) == pytest.approx(0.5)


def test_shin_zonder_marge_is_proportioneel():
    assert shin_kansen([2.0, 2.0]) == pytest.approx([0.5, 0.5])
    assert sum(shin_kansen([2.1, 2.1])) == pytest.approx(1.0)
