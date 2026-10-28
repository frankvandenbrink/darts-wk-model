import math

import pytest

from dartswk.evaluatie import (bets, bootstrap_geclusterd, brier, drempeltabel, gemiddeld, kies_drempel,
                               kies_kant, logloss, roi)


def test_brier_en_logloss_mini():
    ps, ys = [0.8, 0.3, 0.5], [1, 0, 1]
    assert gemiddeld(brier, ps, ys) == pytest.approx((0.04 + 0.09 + 0.25) / 3)
    assert gemiddeld(logloss, ps, ys) == pytest.approx(-(math.log(0.8) + math.log(0.7) + math.log(0.5)) / 3)
    assert logloss(0.0, 1) < 20  # afgekapt, geen oneindig


def _r(jaar, ronde, o1, o2, winnaar):
    return dict(jaar=jaar, ronde=ronde, odd1=o1, odd2=o2, winnaar=winnaar)


ROWS = [_r(2025, "1", 2.0, 2.0, 1),   # p=0.6: ev1=1.2 -> bet 1, wint +1
        _r(2025, "1", 1.5, 3.0, 1),   # p=0.4: ev2=1.8 -> bet 2, verliest -1
        _r(2025, "2", 1.2, 5.0, 2),   # p=0.7: ev1=0.84, ev2=1.5 -> bet 2, wint +4
        _r(2025, "2", 1.5, 2.5, 1)]   # p=0.62: ev1=0.93, ev2=0.95 -> geen bet bij 1.0
PS = [0.6, 0.4, 0.7, 0.62]


def test_bets_en_roi():
    bl = bets(ROWS, PS, 1.0)
    assert [b["resultaat"] for b in bl] == [1.0, -1.0, 4.0]
    assert [b["underdog"] for b in bl] == [False, True, True]
    assert roi(bl) == pytest.approx(4 / 3)
    assert len(bets(ROWS, PS, 1.6)) == 1  # alleen ev 1.8
    assert bets(ROWS, PS, None) == []    # niet wedden
    assert roi([]) is None


def test_kies_kant():
    assert kies_kant(0.5, 2.2, 1.7, 1.05) == 1
    assert kies_kant(0.5, 2.0, 2.0, 1.05) is None   # ev precies 1.0
    assert kies_kant(0.5, 2.2, 2.4, 1.05) == 2      # hoogste verwachting


def test_bootstrap_geclusterd():
    bl = bets(ROWS, PS, 1.0)
    lo, hi = bootstrap_geclusterd(bl, n=2000, seed=3)
    # twee clusters: ronde 1 (0 winst / 2 bets) en ronde 2 (+4 / 1 bet) -> ROI tussen 0 en 4
    assert 0.0 <= lo <= roi(bl) <= hi <= 4.0
    assert bootstrap_geclusterd(bl[:1]) == (None, None)  # één cluster
    assert bootstrap_geclusterd([]) == (None, None)


def test_drempeltabel():
    tab = drempeltabel(ROWS, PS, [1.0, 1.6, 2.0])
    assert tab == [dict(drempel=1.0, bets=3, roi=round(4 / 3, 4)), dict(drempel=1.6, bets=1, roi=-1.0),
                   dict(drempel=2.0, bets=0, roi=None)]


def test_stopregel_niet_wedden_bij_roi_niet_positief():
    tab = [dict(drempel=1.00, bets=100, roi=-0.068), dict(drempel=1.05, bets=78, roi=-0.116)]
    assert kies_drempel(tab, 10)[0] is None
    tab = [dict(drempel=1.00, bets=50, roi=0.0)]
    assert kies_drempel(tab, 10)[0] is None  # ROI precies 0: ook niet wedden


def test_stopregel_kiest_beste_positieve_drempel_met_genoeg_bets():
    tab = [dict(drempel=1.00, bets=75, roi=0.38), dict(drempel=1.10, bets=50, roi=0.509),
           dict(drempel=1.30, bets=5, roi=0.9)]  # te weinig bets
    assert kies_drempel(tab, 10)[0] == 1.10
    assert kies_drempel([dict(drempel=1.3, bets=5, roi=0.9)], 10)[0] is None
