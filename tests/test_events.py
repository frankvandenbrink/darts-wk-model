import json
from datetime import date

import pytest

from dartswk.events import is_paywall, laad_wedstrijden, parse_event_pagina

PAYWALL = "<html><head><title>Subscription - Darts Orakel</title></head><body>abonneer</body></html>"


def test_parse_event_pagina_legs(fixtures):
    rows, namen = parse_event_pagina((fixtures / "orakel_event_fragment.html").read_text(encoding="utf-8"))
    # Smith - Wade 6-0 zonder averages (vermoedelijk walkover) valt af
    assert len(rows) == 2
    f, sf = rows
    assert (f["ronde"], f["winnaar"], f["verliezer"], f["score_w"], f["score_v"]) == ("final", 1, 5, 7, 5)
    assert (f["avg_w"], f["avg_v"]) == (98.34, 99.22)
    assert (sf["ronde"], sf["winnaar"], sf["verliezer"], sf["score_w"], sf["score_v"]) == ("semi-final", 1, 10, 6, 4)
    assert namen == {1: "Peter Wright", 5: "Michael Smith", 10: "Gary Anderson", 7: "James Wade"}


def test_paywall_wordt_herkend():
    assert is_paywall(PAYWALL)
    with pytest.raises(ValueError, match="paywall"):
        parse_event_pagina(PAYWALL)


def _cache(tmp_path, fixtures, events):
    m = tmp_path / "orakel_events"
    (m / "pages").mkdir(parents=True)
    (m / "events_2023.json").write_text(json.dumps(dict(data=events)))
    bron = {"pt": "orakel_event_fragment.html", "wk": "orakel_wk_fragment.html"}
    for e in events:
        html = PAYWALL if e["_pagina"] == "paywall" else (fixtures / bron[e["_pagina"]]).read_text(encoding="utf-8")
        (m / "pages" / f"{e['event_key']}.html").write_text(html, encoding="utf-8")
    return tmp_path


def _ev(key, naam, datum, pagina):
    return dict(event_key=key, tournament_name=naam, event_date=f"{datum} 00:00:00", _pagina=pagina)


def test_laad_wedstrijden_sets_cutoff_en_paywall(tmp_path, fixtures):
    events = [
        _ev(1, "World Championship", "2023-01-03", "wk"),     # WK 2023: score in sets
        _ev(2, "Players Championship", "2023-06-01", "pt"),
        _ev(3, "Players Championship", "2023-06-02", "paywall"),
        _ev(4, "Players Championship", "2023-12-15", "pt"),   # op de WK-start: valt af
        _ev(5, "World Championship", "2024-01-03", "wk"),     # WK 2024 zelf (finaledag): valt af
    ]
    cache = _cache(tmp_path, fixtures, events)
    wed, namen, t = laad_wedstrijden(cache, date(2023, 12, 15))
    assert {w.event_key for w in wed} == {1, 2}
    assert all(w.datum < date(2023, 12, 15) for w in wed)
    assert t["paywall"] == 1 and t["gebruikt"] == 2 and t["events"] == 3
    wk = [w for w in wed if w.event_key == 1]
    assert len(wk) == 1 and wk[0].sets and (wk[0].score_w, wk[0].score_v) == (7, 4)
    assert not any(w.sets for w in wed if w.event_key == 2)
    assert t["sets_wedstrijden"] == 1 and t["laatste_event"] == "2023-06-01"
