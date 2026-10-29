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
    # geen externe requests: alleen inline scripts, geen stylesheets, afbeeldingen of url()
    assert not re.search(r"<(link|img|iframe)\b", tekst)
    assert not re.search(r"<script\b[^>]*\bsrc", tekst)
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


def _experimenten():
    u = {"train": [2024], "test": [2025], "soort": "walk-forward", "n": 94, "logloss": 0.64, "brier": 0.22,
         "logloss_markt": 0.63, "brier_markt": 0.21, "verschil_markt": 0.01, "verschil_se": 0.02,
         "ruis": "binnen de ruis", "helling": 0.8, "bets": 3, "underdog_bets": 2, "winst": 1.0, "roi": 0.33,
         "roi_90": [-0.5, 0.9], "verloop": [-1.0, 1.5, 1.0], "drempel": 1.1, "drempel_reden": "x",
         "kalibratie": [{"van": 0.5, "tot": 0.6, "n": 10, "kans": 0.55, "freq": 0.5},
                        {"van": 0.6, "tot": 0.7, "n": 0, "kans": None, "freq": None}]}
    reg = [{"id": "E006", "naam": "Vorm <x>", "model": "vorm", "hypothese": "h", "soort": "model",
            "na_test_aangepast": {"waarde": True, "toelichting": "t"}},
           {"id": "E019", "naam": "GBM", "model": "gbm", "hypothese": "h2", "soort": "model",
            "na_test_aangepast": {"waarde": False}}]
    return {"register": reg, "resultaten": [
        {"id": "E006", "model": "vorm", "status": "ok", "uitkomsten": [u, dict(u, soort="richting")],
         "beoordeling": {"succes": False}},
        {"id": "E019", "model": "gbm", "status": "niet gedraaid", "fout": "geen sklearn", "uitkomsten": []}]}


def test_experimenten_en_inhoud(bd, resultaten, tmp_path):
    _schrijf(resultaten / "experimenten.json", _experimenten())
    inhoud = tmp_path / "inhoud"
    inhoud.mkdir()
    _schrijf(inhoud / "aanbeveling.json", {"titel": "Advies", "punten": ["niet wedden <nu>"]})
    _schrijf(inhoud / "onderzoek.json", {"items": [{"naam": "Bron", "url": "https://voorbeeld.nl", "kosten": "0"}]})
    proto = tmp_path / "protocol.md"
    proto.write_text("# Protocol\n\nTekst met [link](model-rating.md) en **vet**.\n\n- een\n- twee\n1. eerst\n",
                     encoding="utf-8")
    uit = tmp_path / "site"
    bd.main(["--resultaten", str(resultaten), "--uit", str(uit), "--inhoud", str(inhoud), "--protocol", str(proto)])
    pagina = (uit / "index.html").read_text(encoding="utf-8")
    _controleer_html(pagina)
    assert "niet wedden &lt;nu&gt;" in pagina
    assert "Vorm &lt;x&gt;" in pagina and 'class="mislukt"' in pagina and "geen sklearn" in pagina
    assert "table class=\"sorteerbaar\"" in pagina and "<script>" in pagina
    assert "dl-titel" in pagina and "svg role=\"img\" class=\"klein\"" not in pagina
    assert 'class="klein"' in pagina and "rc-titel" in pagina
    assert "<li>een</li>" in pagina and "<ol><li>eerst</li></ol>" in pagina
    assert "blob/main/docs/model-rating.md" in pagina
    assert 'href="https://voorbeeld.nl"' in pagina and "vrienden.html" in pagina
    assert (uit / "vrienden.html").exists()
    # experimenten.json is geen run-bestand
    assert len(bd.verzamel(resultaten)["runs"]) == 3


def test_markdown_html(bd):
    h = bd.markdown_html("## Kop\n\nRegel een\nregel twee\n\n- a\n  vervolg\n- `b`\n")
    assert "<h4>Kop</h4>" in h and "<p>Regel een regel twee</p>" in h
    assert "<li>a vervolg</li>" in h and "<code>b</code>" in h


def test_inzet_setstand_werkwijze(bd, resultaten, tmp_path):
    exp = _experimenten()
    week = lambda w, x, op: {"week": w, "ingezet": 10.0, "winst": x, "budget_op": op}
    wb = {"inzet": 5, "budget": 50, "bets": 3, "overgeslagen": 1, "ingezet": 15.0, "eind": 4.0,
          "max_drawdown": 5.0, "weken_budget_op": 1, "weken": [week("2024-12-16", -5.0, True), week("2024-12-23", 9.0, False)]}
    kelly = {"start": 100, "eind": 103.0, "winst": 3.0, "ingezet": 12.0, "max_drawdown": 2.0, "verloop": [103.0]}
    exp["register"] += [{"id": "E027", "naam": "Inzet", "model": "inzet", "hypothese": "h", "grid": {"weekbudget": 50},
                         "na_test_aangepast": {"waarde": False}},
                        {"id": "E028", "naam": "Setstanden", "model": "setstand", "hypothese": "h",
                         "na_test_aangepast": {"waarde": False}}]
    exp["resultaten"] += [
        {"id": "E027", "model": "inzet", "status": "ok", "uitkomsten": [
            {"train": [2024], "test": [2025], "soort": "walk-forward", "bets": 3, "vast_1": 1.0, "kelly": kelly,
             "weekbudget": [wb]}]},
        {"id": "E028", "model": "setstand", "status": "ok", "beoordeling": {"succes": False}, "uitkomsten": [
            {"train": [2024], "test": [2025], "soort": "walk-forward", "n": 94, "logloss_dp": 1.85,
             "logloss_naief": 1.855, "logloss_winnaar": 0.63, "verschil_naief": -0.0035, "verschil_se": 0.0028}]}]
    _schrijf(resultaten / "experimenten.json", exp)
    uit = tmp_path / "site"
    bd.main(["--resultaten", str(resultaten), "--uit", str(uit)])
    pagina = (uit / "index.html").read_text(encoding="utf-8")
    _controleer_html(pagina)
    assert "iw-titel" in pagina and "€5 vast" in pagina and "(vs naïef)" in pagina
    assert "blob/main/docs/review-ronde2.md" in pagina and "blob/main/docs/onderzoek-odds-en-toto.md" in pagina
    assert 'id="werkwijze"' in pagina and "Laatst bijgewerkt" in pagina
