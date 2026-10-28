import pytest

from dartswk.setmodel import hold_kansen, set_kans, wedstrijd_kans


@pytest.mark.parametrize("n", [3, 4, 5, 6, 7])
@pytest.mark.parametrize("ha,hb", [(0.6, 0.6), (0.7, 0.55), (0.52, 0.81), (0.95, 0.4)])
def test_kansen_sommen_tot_1(n, ha, hb):
    # P(A wint) + P(B wint) = 1, en het model is symmetrisch in de spelers
    assert wedstrijd_kans(ha, hb, n) + wedstrijd_kans(hb, ha, n) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("beslissend", [False, True])
def test_set_kansen_sommen_tot_1(beslissend):
    pa, pb = 0.66, 0.31  # A wint leg met 0.66 als A begint, met 0.31 als B begint
    pa_b, pb_b = 1 - pb, 1 - pa  # vanuit B gezien
    for a_begint in (True, False):
        som = set_kans(pa, pb, a_begint, beslissend) + set_kans(pa_b, pb_b, not a_begint, beslissend)
        assert som == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("n", [3, 4, 7])
@pytest.mark.parametrize("h", [0.5, 0.6, 0.75])
def test_gelijke_spelers_half(n, h):
    assert wedstrijd_kans(h, h, n) == pytest.approx(0.5, abs=1e-12)


@pytest.mark.parametrize("n", [3, 5, 7])
def test_monotoon_in_sterkte(n):
    ps = [wedstrijd_kans(*hold_kansen(x, 0.6), n) for x in (-1, -0.5, -0.1, 0, 0.1, 0.5, 1)]
    assert all(a < b for a, b in zip(ps, ps[1:]))
    assert ps[3] == pytest.approx(0.5)


def test_langere_wedstrijd_bevoordeelt_sterkere():
    h1, h2 = hold_kansen(0.3, 0.6)
    assert wedstrijd_kans(h1, h2, 3) < wedstrijd_kans(h1, h2, 7)


def test_sudden_death_bij_5_5():
    # Iedereen wint altijd de eigen leg: zonder sudden death zou de beslissende set nooit eindigen.
    # Met wisselende beginner gooit wie de set begon ook leg 11 (bij 5-5) en wint die dus.
    assert set_kans(1.0, 0.0, True, True) == 1.0
    assert set_kans(1.0, 0.0, False, True) == 0.0
    # Niet-beslissende set: first to 3, de beginner wint 3-2
    assert set_kans(1.0, 0.0, True, False) == 1.0


@pytest.mark.parametrize("p", [0.3, 0.5, 0.6, 0.8])
def test_set_kans_met_handberekening(p):
    # Legkans p onafhankelijk van wie begint: dan is er een gesloten vorm.
    q = 1 - p
    first_to_3 = p**3 * (1 + 3 * q + 6 * q**2)
    assert set_kans(p, p, True, False) == pytest.approx(first_to_3)
    # Beslissende set: 3-0/3-1 wint direct; vanaf 2-2 twee legs verschil, bij 5-5 één sudden-death-leg.
    vanaf_2_2 = p**2 + 2 * p * q * (p**2 + 2 * p * q * (p**2 + 2 * p * q * p))
    beslissend = p**3 + 3 * p**3 * q + 6 * p**2 * q**2 * vanaf_2_2
    assert set_kans(p, p, True, True) == pytest.approx(beslissend)
