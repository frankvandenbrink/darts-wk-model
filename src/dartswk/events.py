"""Wedstrijduitslagen per toernooi van Dartsorakel (evenementenlijst + resultaatpagina's).

- Evenementenlijst: data/cache/orakel_events/events_<kalenderjaar>.json (/api/events, organCal=All Rankings).
- Resultaatpagina's: data/cache/orakel_events/pages/<event_key>.html, tabellen Winner | Score | Runner Up met
  cellen als 'Peter Wright (98.34)' en '7 - 5'. Spelers worden herkend aan de player_key in de link.
- Bij World Championship en World Grand Prix is de score in sets; daar wordt alleen de uitslag gebruikt.
- Een deel van de pagina's is een abonnementspagina (paywall) in plaats van uitslagen; die worden overgeslagen
  en geteld. De paywall wordt niet omzeild.
- Een event heeft één datum (bij het WK de finaledag). Voor het voorspellen van WK j tellen alleen events met
  datum strikt vóór de WK-start; `laad_wedstrijden` controleert dat met een assert.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

SETS_TOERNOOIEN = {"World Championship", "World Grand Prix"}
_KEY = re.compile(r"/player/details/(\d+)/")
_SCORE = re.compile(r"^(\d+)\s*-\s*(\d+)$")
_AVG = re.compile(r"\(([\d.]+)\)")


@dataclass(frozen=True)
class Wedstrijd:
    datum: date
    event_key: int
    toernooi: str
    ronde: str
    winnaar: int        # player_key
    verliezer: int
    score_w: int        # legs, of sets als sets=True
    score_v: int
    avg_w: float | None
    avg_v: float | None
    sets: bool          # score in sets: alleen de uitslag gebruiken


def is_paywall(html: str) -> bool:
    m = re.search(r"<title>([^<]*)</title>", html)
    return bool(m) and m.group(1).strip().startswith("Subscription")


def _speler(td) -> tuple[int, str, float | None]:
    a = td.find("a", href=_KEY)
    if a is None:
        raise ValueError(f"geen spelerlink in cel: {td.get_text(' ', strip=True)[:80]}")
    m = _AVG.search(td.get_text(" ", strip=True))
    return int(_KEY.search(a["href"]).group(1)), a.get_text(strip=True), float(m.group(1)) if m else None


def parse_event_pagina(html: str) -> tuple[list[dict], dict[int, str]]:
    """(wedstrijden, {player_key: naam}) uit een resultaatpagina. Paywall-pagina: ValueError.

    Wedstrijd zonder averages bij beide spelers (vermoedelijk walkover) wordt overgeslagen.
    """
    if is_paywall(html):
        raise ValueError("abonnementspagina (paywall), geen uitslagen")
    soup = BeautifulSoup(html, "html.parser")
    rows, namen = [], {}
    for tabel in soup.select("table.v3-event-results-table"):
        ronde = (tabel.get("id") or "").removeprefix("round-")
        for tr in tabel.select("tbody tr"):
            td = tr.find_all("td")
            if len(td) < 3:
                continue
            kw, nw, aw = _speler(td[0])
            kv, nv, av = _speler(td[2])
            m = _SCORE.match(td[1].get_text(strip=True))
            if not m:
                raise ValueError(f"onleesbare score: {td[1].get_text(strip=True)!r}")
            sw, sv = int(m.group(1)), int(m.group(2))
            if sw <= sv:
                raise ValueError(f"winnaar heeft niet de hoogste score: {nw} {sw}-{sv} {nv}")
            namen[kw], namen[kv] = nw, nv
            if aw is None and av is None:
                continue
            rows.append(dict(ronde=ronde, winnaar=kw, verliezer=kv, score_w=sw, score_v=sv, avg_w=aw, avg_v=av))
    if not rows:
        raise ValueError("geen uitslagentabellen gevonden")
    return rows, namen


def event_map(cache: Path) -> Path:
    return cache / "orakel_events"


def laad_eventlijst(cache: Path) -> list[dict]:
    uit = []
    for fn in sorted(event_map(cache).glob("events_*.json")):
        uit += json.loads(fn.read_text(encoding="utf-8"))["data"]
    return uit


def laad_wedstrijden(cache: Path, voor: date) -> tuple[list[Wedstrijd], dict[int, str], dict]:
    """Alle wedstrijden uit events met datum strikt vóór `voor`, plus spelersnamen en tellingen.

    Pagina's die ontbreken of een paywall zijn, worden overgeslagen en geteld in de meldingen.
    """
    wed, namen = [], {}
    telling = dict(events=0, gebruikt=0, paywall=0, ontbreekt=0, wedstrijden=0, sets_wedstrijden=0)
    for ev in laad_eventlijst(cache):
        d = date.fromisoformat(ev["event_date"][:10])
        if d >= voor:
            continue
        telling["events"] += 1
        fn = event_map(cache) / "pages" / f"{ev['event_key']}.html"
        if not fn.exists():
            telling["ontbreekt"] += 1
            continue
        html = fn.read_text(encoding="utf-8")
        if is_paywall(html):
            telling["paywall"] += 1
            continue
        rows, nm = parse_event_pagina(html)
        namen.update(nm)
        sets = ev["tournament_name"] in SETS_TOERNOOIEN
        telling["gebruikt"] += 1
        for r in rows:
            wed.append(Wedstrijd(datum=d, event_key=ev["event_key"], toernooi=ev["tournament_name"], sets=sets, **r))
    assert all(w.datum < voor for w in wed), f"event op of na de cutoff {voor}"
    telling["wedstrijden"] = len(wed)
    telling["sets_wedstrijden"] = sum(w.sets for w in wed)
    telling["laatste_event"] = str(max(w.datum for w in wed)) if wed else None
    return wed, namen, telling
