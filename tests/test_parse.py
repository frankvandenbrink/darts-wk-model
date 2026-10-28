import pytest

from dartswk.parse import parse_oddsportal, parse_wiki


def test_parse_wiki_fragment_met_walkover(fixtures):
    rows = parse_wiki((fixtures / "wiki_fragment.txt").read_text(encoding="utf-8"), 2025)
    assert [r["wedstrijd"] for r in rows] == [1, 2, 3]  # sectie ==Draw== telt niet mee
    a, wo, f = rows
    assert (a["speler1"], a["speler2"], a["sets1"], a["sets2"], a["winnaar"]) == ("Anna Alfa", "Bert Beta", 3, 1, 1)
    assert a["ronde"] == "1" and a["setsnodig"] == 3 and a["datum"] == "2024-12-15"
    assert (a["avg1_achteraf"], a["avg2_achteraf"]) == (91.79, 88.26)
    # walkover: ronde loopt door (rowspan), geen sets, winnaar via b=1
    assert wo["walkover"] == 1 and wo["ronde"] == "1"
    assert wo["sets1"] is None and wo["sets2"] is None and wo["winnaar"] == 1
    assert wo["avg1_achteraf"] is None
    # finale: link met weergavenaam, average na de naam, setsnodig uit de ronde (niet uit de uitslag)
    assert (f["speler1"], f["speler2"], f["winnaar"], f["setsnodig"]) == ("Anna Alfa", "Eva Epsilon", 2, 7)
    assert f["datum"] == "2025-01-03" and f["avg2_achteraf"] == 99.02


def test_parse_wiki_geen_achteraf_als_feature_naam(fixtures):
    rows = parse_wiki((fixtures / "wiki_fragment.txt").read_text(encoding="utf-8"), 2025)
    assert not any(k.startswith("avg") and not k.endswith("_achteraf") for k in rows[0])


def test_parse_wiki_te_veel_sets_geeft_fout():
    t = "==Schedule==\n| 01 || 1 || [[A B]] || {{dart score|4|1}} || [[C D]]\n"
    with pytest.raises(ValueError):
        parse_wiki(t, 2025)


def test_parse_oddsportal_ontdubbelt(fixtures):
    rows, dubbel = parse_oddsportal((fixtures / "oddsportal_fragment.txt").read_text(encoding="utf-8"))
    assert dubbel == 1
    assert rows[0] == dict(dag="03 Jan 2025", p1="Epsilon E.", p2="Alfa A.", s1=7, s2=5, o1=1.8, o2=2.0)
    assert rows[1]["p1"] == "Smith M." and rows[1]["o1"] is None  # geen odds beschikbaar
