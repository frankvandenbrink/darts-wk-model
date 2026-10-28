import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "bouw_dashboard.py"


@pytest.fixture(scope="module")
def bd():
    spec = importlib.util.spec_from_file_location("bouw_dashboard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _test_resultaat(**extra):
    basis = {"n": 94, "brier_model": 0.22, "logloss_model": 0.64, "brier_markt_proportioneel": 0.21,
             "logloss_markt_proportioneel": 0.63, "brier_markt_shin": 0.212, "logloss_markt_shin": 0.632,
             "bets": 30, "underdog_bets": 25, "roi": 0.12, "roi_90_geclusterd": [-0.2, 0.4], "drempel": 1.1}
    basis.update(extra)
    return basis


def _run(train, test, **extra):
    run = {"model": "vorm", "train": train, "test": test, "parameters": {"w": 0.0, "L": 6},
           "drempel": 1.1, "drempel_reden": "hoogste ROI op train", "train_resultaat": _test_resultaat(),
           "test_resultaat": _test_resultaat()}
    run.update(extra)
    return run


def _schrijf(pad: Path, obj):
    pad.write_text(json.dumps(obj), encoding="utf-8")


class _Controle(HTMLParser):
    LEEG = {"meta", "br", "hr", "img", "input", "link", "circle", "line", "polyline", "path", "rect"}

    def __init__(self):
        super().__init__()
        self.stapel, self.fouten = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.LEEG:
            self.stapel.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.LEEG:
            if tag in self.stapel and self.stapel[-1] == tag:
                self.stapel.pop()
            return
        if not self.stapel or self.stapel[-1] != tag:
            self.fouten.append(f"onverwachte </{tag}>, open: {self.stapel[-3:]}")
        else:
            self.stapel.pop()


def _controleer_html(tekst: str):
    p = _Controle()
    p.feed(tekst)
    assert not p.fouten
    assert p.stapel == []
    # geen externe requests: geen scripts, stylesheets, afbeeldingen of url()
    assert not re.search(r"<(script|link|img|iframe)\b", tekst)
    assert "url(" not in tekst
    assert not re.search(r'\ssrc=', tekst)


@pytest.fixture
def resultaten(tmp_path):
    r = tmp_path / "resultaten"
    r.mkdir()
    # los run-object, met stopregel: geen bets, geen ROI
    stop = _run([2026], [2025], drempel=None, drempel_reden="niet wedden")
    stop["test_resultaat"] = _test_resultaat(bets=0, underdog_bets=0, roi=None, roi_90_geclusterd=[None, None],
                                             drempel=None)
    _schrijf(r / "terugtest_vorm_train2026_test2025.json", stop)
    # los run-object met ontbrekende keys
    kaal = _run([2025], [2026])
    kaal["test_resultaat"] = {"n": 126, "logloss_model": 0.57, "logloss_markt_proportioneel": 0.55}
    del kaal["drempel_reden"]
    _schrijf(r / "terugtest_vorm_train2025_test2026.json", kaal)
    # walk-forward
    _schrijf(r / "walkforward_vorm.json", {"model": "vorm", "stappen": [_run([2024], [2025])],
                                           "totaal_test": _test_resultaat(n=220, drempel="per stap")})
    return r


def test_verzamel_alle_formaten_en_ontdubbelen(bd, resultaten):
    rijk = _run([2024], [2025], soort="walk-forward", verloop=[1.5, 0.5, -0.5, 2.0])
    _schrijf(resultaten / "vergelijking.json", {
        "runs": [rijk, _run([2023], [2024], soort="richting", model="rating")],
        "data": {"2025": {"n": 94, "favoriet_won": "59/94"}},
        "blind_underdog": {"2025": {"bets": 94, "roi": 0.05}},
        "meldingen": {"2025": "1 walkover"},
    })
    v = bd.verzamel(resultaten)
    sleutels = [bd.run_sleutel(r) for r in v["runs"]]
    assert len(sleutels) == len(set(sleutels)) == 4
    wf = next(r for r in v["runs"] if bd.run_sleutel(r) == ("vorm", (2024,), (2025,)))
    assert wf["_bron"] == "vergelijking.json" and wf["verloop"]
    assert {r["soort"] for r in v["runs"]} == {"richting", "walk-forward"}
    assert "vorm" in v["totalen"]
    assert set(v["extra"]) == {"data", "blind_underdog", "meldingen"}

    pagina = bd.bouw_html(v, None, sha="abcdef1234567")
    _controleer_html(pagina)
    assert "<polyline" in pagina
    assert "rating" in pagina
    assert "blind op de underdog" in pagina
    assert "abcdef1" in pagina


def test_ontbrekende_keys_en_geen_live(bd, resultaten, tmp_path):
    uit = tmp_path / "site"
    assert bd.main(["--resultaten", str(resultaten), "--uit", str(uit)]) == 0
    pagina = (uit / "index.html").read_text(encoding="utf-8")
    _controleer_html(pagina)
    assert "Darts-WK-model: tussenstanden" in pagina
    assert "Hobbyproject. Wedden kan verliesgevend zijn. 18+. Geen advies." in pagina
    assert bd.LIVE_LEEG in pagina
    assert "niet wedden" in pagina
    assert "geen bets (stopregel)" in pagina
    assert "Geen winstverloop beschikbaar" in pagina
    assert "–" in pagina
    assert "markt wint" in pagina
    assert "commit onbekend" in pagina
    data = json.loads((uit / "data.json").read_text(encoding="utf-8"))
    assert len(data["runs"]) == 3 and data["live"] is None


def test_live_bestand(bd, resultaten, tmp_path):
    _schrijf(resultaten / "live_2027.json", {
        "model": "vorm", "bijgewerkt": "2026-12-12",
        "wedstrijden": [
            {"datum": "2026-12-11", "ronde": "1", "speler1": "A <b>", "speler2": "B", "kans_model": 0.6,
             "kans_markt": 0.55, "odd1": 1.7, "odd2": 2.2, "bet": 1, "winnaar": 1, "sets1": 3, "sets2": 1},
            {"datum": "2026-12-12", "ronde": "1", "speler1": "C", "speler2": "D", "kans_model": 0.4,
             "bet": None, "winnaar": None},
        ],
    })
    uit = tmp_path / "site"
    bd.main(["--resultaten", str(resultaten), "--uit", str(uit)])
    pagina = (uit / "index.html").read_text(encoding="utf-8")
    _controleer_html(pagina)
    assert bd.LIVE_LEEG not in pagina
    assert "1 van 2 wedstrijden gespeeld" in pagina
    assert "A &lt;b&gt;" in pagina
    assert "+0.70 units" in pagina
    # het live-bestand is geen run
    assert len(bd.verzamel(resultaten)["runs"]) == 3


def test_github_sha_in_voettekst(bd, resultaten, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "0123456789abcdef")
    uit = tmp_path / "site"
    bd.main(["--resultaten", str(resultaten), "--uit", str(uit)])
    assert "/commit/0123456789abcdef" in (uit / "index.html").read_text(encoding="utf-8")


def test_echte_resultaten(bd, tmp_path):
    echte = SCRIPT.parent.parent / "resultaten"
    v = bd.verzamel(echte)
    assert v["runs"]
    _controleer_html(bd.bouw_html(v, bd.lees_live(echte)))
