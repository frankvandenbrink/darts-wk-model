import json

import numpy as np
import pytest

from dartswk import experimenten as x


def _exp(**kw):
    e = dict(id="E900", datum="2026-10-29", model="markt", features=[], grid={}, hypothese="h",
             criterium={"tekst": "c", "regel": "verschil_lt_markt", "factor_se": 1.0},
             na_test_aangepast={"waarde": False, "toelichting": ""})
    e.update(kw)
    return e


def _rij(jaar=2025, odd1=1.5, odd2=2.6, winnaar=1, ronde="1", nr=1):
    return dict(jaar=jaar, ronde=ronde, datum=f"{jaar - 1}-12-15", wedstrijd=nr, setsnodig=3, odd1=odd1,
                odd2=odd2, winnaar=winnaar)


def test_pav_monotoon():
    xs, f = x.pav(np.array([0.5, 0.6, 0.7, 0.8]), np.array([1, 0, 1, 1]))
    assert list(xs) == [0.5, 0.6, 0.7, 0.8]
    assert all(a <= b for a, b in zip(f, f[1:]))
    assert f[0] == f[1] == 0.5


def test_kalibratiebins_symmetrisch():
    b = x.kalibratiebins([0.95, 0.05, 0.55], [1, 0, 0])
    assert sum(k["n"] for k in b) == 3
    assert b[-1]["n"] == 2 and b[-1]["freq"] == 1.0       # beide favorieten wonnen
    assert b[0]["n"] == 1 and b[0]["freq"] == 0.0


def test_blind_bets():
    rows = [_rij(winnaar=1), _rij(winnaar=2, nr=2), _rij(odd1=2.0, odd2=2.0, nr=3)]
    u = x.blind_bets(rows, "underdog")
    f = x.blind_bets(rows, "favoriet")
    assert len(u) == len(f) == 2                         # gelijke odds overgeslagen
    assert [b["resultaat"] for b in u] == [-1.0, pytest.approx(1.6)]
    assert [b["resultaat"] for b in f] == [pytest.approx(0.5), -1.0]


def test_metrics_markt_verschil_nul():
    rows = [_rij(nr=i, winnaar=1 + i % 2) for i in range(6)]
    ps = [x._markt(r) for r in rows]
    m = x.metrics(rows, ps, [])
    assert m["verschil_markt"] == 0 and m["ruis"] == "binnen de ruis" and m["roi"] is None
    assert m["bets"] == 0 and m["verloop"] == []


def test_walk_forward_lek_assert():
    with pytest.raises(AssertionError):
        x.draai_split(_exp(), [2025], [2024], "walk-forward", {})


def test_protocol_eist_hypothese():
    with pytest.raises(ValueError):
        x.protocolcheck(_exp(hypothese=" "), [])


def test_protocol_waarschuwt_bij_stille_wijziging():
    e = _exp()
    eerdere = [dict(id="E900", vingerafdruk="anders")]
    assert x.protocolcheck(e, eerdere) is not None
    e["na_test_aangepast"] = {"waarde": True, "toelichting": "grid verbreed"}
    assert x.protocolcheck(e, eerdere) is None
    assert x.protocolcheck(_exp(), [dict(id="E900", vingerafdruk=x.vingerafdruk(_exp()))]) is None


def test_beoordeel():
    u = [dict(soort="walk-forward", test=[2025], verschil_markt=-0.02, verschil_se=0.01),
         dict(soort="walk-forward", test=[2026], verschil_markt=-0.005, verschil_se=0.01)]
    assert x.beoordeel(_exp(), u)["succes"] is False
    u[1]["verschil_markt"] = -0.03
    assert x.beoordeel(_exp(), u)["succes"] is True
    assert x.beoordeel(_exp(criterium={"tekst": "controle", "regel": None}), u)["succes"] is None


def test_fit_ridge_krimpt_alleen_bestraft():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 2))
    y = (rng.random(400) < 1 / (1 + np.exp(-(X @ [1.0, 1.0])))).astype(float)
    b0 = x.fit_ridge(X, y, np.array([0.0, 0.0]))
    b1 = x.fit_ridge(X, y, np.array([0.0, 1e6]))
    assert abs(b1[1]) < 1e-3 and abs(b0[1]) > 0.5


def test_register_geldig():
    reg = x.laad_register(x.config.basis() / "experimenten" / "register.json") \
        if (x.config.basis() / "experimenten" / "register.json").exists() else None
    if reg is None:
        pytest.skip("geen register in de werkmap")
    for e in reg:
        assert e["model"] in x.MODELTYPES, e["id"]


def test_log_schrijft_jsonl(tmp_path):
    pad = tmp_path / "log.jsonl"
    x.log({"id": "E900", "status": "mislukt"}, pad)
    x.log({"id": "E901", "status": "ok"}, pad)
    assert [r["id"] for r in x.lees_log(pad)] == ["E900", "E901"]
    assert json.loads(pad.read_text().splitlines()[0])["status"] == "mislukt"


def test_protocol_toelichting_verplicht():
    with pytest.raises(ValueError):
        x.protocolcheck(_exp(na_test_aangepast={"waarde": True, "toelichting": " "}), [])


def test_protocol_eerste_run_telt_en_context():
    e = _exp(hypothese="nieuw")
    eerdere = [dict(id="E900", vingerafdruk=x.vingerafdruk(_exp())), dict(id="E900", vingerafdruk=x.vingerafdruk(e))]
    assert x.protocolcheck(e, eerdere) is not None        # tweede run wast de wijziging niet wit
    oud = [dict(id="E900", vingerafdruk=x.vingerafdruk(_exp()), context="andere")]
    assert "config" in x.protocolcheck(_exp(), oud)
    goed = [dict(id="E900", vingerafdruk=x.vingerafdruk(_exp()), context=x.context_vingerafdruk())]
    assert x.protocolcheck(_exp(), goed) is None
