import pytest

from dartswk.koppelen import OrakelIndex, koppel_odds, norm, op_past


def orakel(*namen):
    return {i: {"naam": n} for i, n in enumerate(namen, start=1)}


# ---------------------------------------------------------------- Oddsportal-namen
@pytest.mark.parametrize("op,vol", [
    ("van Gerwen M.", "Michael van Gerwen"),
    ("Zong X. C.", "Xiaochen Zong"),
    ("Leung M. L.", "Man Lok Leung"),
    ("Rodriguez Ru. J.", "Rusty-Jake Rodriguez"),
    ("Van den Bergh D.", "Dimitri Van den Bergh"),
    ("Gruellich D.", "Dominik Grüllich"),
    ("Grullich D.", "Dominik Grüllich"),
])
def test_op_past(op, vol):
    assert op_past(op, vol)


def test_initiaal_conflict_smith():
    assert op_past("Smith M.", "Michael Smith")
    assert not op_past("Smith M.", "Ross Smith")
    assert op_past("Smith R.", "Ross Smith")
    assert not op_past("Smith R.", "Michael Smith")
    assert not op_past("Smith M.", "Michael Smithson")


def _w(nr, s1, s2, n1, n2):
    return dict(jaar=2025, wedstrijd=nr, speler1=s1, speler2=s2, sets1=n1, sets2=n2, walkover=0)


def test_koppel_odds_een_op_een_en_omgedraaid():
    wiki = [_w(1, "Michael Smith", "Chris Dobey", 3, 1), _w(2, "Ross Smith", "Luke Littler", 0, 3)]
    odds = [dict(p1="Littler L.", p2="Smith R.", s1=3, s2=0, o1=1.2, o2=4.5),
            dict(p1="Smith M.", p2="Dobey C.", s1=3, s2=1, o1=1.8, o2=2.0)]
    uit, meld = koppel_odds(wiki, odds)
    assert uit == {1: (1.8, 2.0), 2: (4.5, 1.2)}  # in volgorde speler1, speler2
    assert meld == []


def test_koppel_odds_dubbel_gebruik_geeft_fout():
    wiki = [_w(1, "Michael Smith", "Chris Dobey", 3, 1), _w(2, "Mark Smith", "Chris Dobey", 3, 1)]
    odds = [dict(p1="Smith M.", p2="Dobey C.", s1=3, s2=1, o1=1.8, o2=2.0)]
    with pytest.raises(ValueError):
        koppel_odds(wiki, odds)


def test_koppel_odds_meerdere_kandidaten_geeft_fout():
    wiki = [_w(1, "Michael Smith", "Chris Dobey", 3, 1)]
    odds = [dict(p1="Smith M.", p2="Dobey C.", s1=3, s2=1, o1=1.8, o2=2.0),
            dict(p1="Smith M.", p2="Dobey C.", s1=3, s2=1, o1=1.7, o2=2.1)]
    with pytest.raises(ValueError):
        koppel_odds(wiki, odds)


# ---------------------------------------------------------------- Dartsorakel
def test_umlaut_norm():
    assert norm("Dominik Grüllich") == norm("Dominik Gruellich") == ["dominik", "gruellich"]
    assert norm("Dominik Grüllich", "u") == ["dominik", "grullich"]


def test_orakel_zong_omgekeerd():
    idx = OrakelIndex(orakel("Zong Xiaochen", "Zongqi Lu"))
    assert idx.vind("Xiaochen Zong") == (1, "omgekeerd")


def test_orakel_umlaut():
    idx = OrakelIndex(orakel("Dominik Gruellich"))
    assert idx.vind("Dominik Grüllich")[0] == 1
    idx = OrakelIndex(orakel("Dominik Grullich"))
    assert idx.vind("Dominik Grüllich") == (1, "umlaut")


def test_orakel_alias_szaganski():
    idx = OrakelIndex(orakel("Radoslaw Szaganski", "Hugo Leung Man Lok"))
    assert idx.vind("Radek Szaganski") == (1, "alias")
    assert idx.vind("Man Lok Leung") == (2, "alias")


def test_orakel_difflib_vereist_zelfde_initiaal():
    idx = OrakelIndex(orakel("Dave Cameron", "Cameron Menzies"))
    assert idx.vind("David Cameron")[0] == 1
    assert idx.vind("Mavid Cameron") == (None, "geen")


def test_orakel_dubbelzinnig_en_een_op_een():
    idx = OrakelIndex(orakel("Ryan Joyce", "Ryan Joyce"))
    with pytest.raises(ValueError):
        idx.vind("Ryan Joyce")
    idx = OrakelIndex(orakel("Berry van Peer", "Dave Cameron"))
    uit, _ = idx.koppel(["Berry van Peer", "Berry Van Peer"])  # alleen hoofdletterverschil: zelfde speler
    assert uit == {"Berry van Peer": 1, "Berry Van Peer": 1}
    with pytest.raises(ValueError):
        idx.koppel(["Dave Cameron", "David Cameron"])  # twee WK-namen naar één Dartsorakel-speler
