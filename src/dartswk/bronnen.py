"""Ophalen van ruwe brondata naar data/cache/ (wordt niet gecommit).

- Wikipedia: wikitext van het WK-artikel (CC BY-SA 4.0).
- Dartsorakel: geaggregeerde averages en checkout% per speler over 3/6/12 maanden vóór het WK.

Oddsportal wordt niet (meer) opgehaald: de gebruiksvoorwaarden van Oddsportal verbieden scrapen. De ophaalcode is
verwijderd; bestaande lokale bestanden data/cache/oddsportal_<jaar>.txt worden alleen nog geparst (parse.py).
Zie data/BRONNEN.md. Controleer zelf de gebruiksvoorwaarden van Dartsorakel voordat je ophaalt.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import requests

from . import config

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
ORAKEL_KEYS = {"avg": 25, "co": 1053}  # rankKey: 3-dart average, checkout%


def vormperiode(jaar: int, maanden: int) -> tuple[date, date]:
    """(van, tot) voor het vormvenster; tot = dag vóór de WK-start."""
    start = date.fromisoformat(config.JAREN[jaar].start)
    tot = start - timedelta(days=1)
    van = tot - timedelta(days=round(maanden * 30.44))
    assert tot < start, f"vormperiode {jaar} eindigt niet vóór de WK-start"
    return van, tot


def fetch_wiki(jaar: int, cache: Path) -> Path:
    fn = cache / f"wiki_{jaar}.txt"
    if not fn.exists():
        url = "https://en.wikipedia.org/w/index.php"
        r = requests.get(url, params=dict(title=config.JAREN[jaar].wiki, action="raw"),
                         headers={"User-Agent": "dartswk (hobbyproject)"}, timeout=60)
        r.raise_for_status()
        fn.write_text(r.text, encoding="utf-8")
    return fn


def fetch_orakel(jaar: int, cache: Path) -> None:
    for m in config.VENSTERS:
        van, tot = vormperiode(jaar, m)
        for naam, key in ORAKEL_KEYS.items():
            fn = cache / f"orakel_{jaar}_{naam}_{m}m.json"
            if fn.exists():
                continue
            params = dict(dateFrom=str(van), dateTo=str(tot), rankKey=key, organStat="All", minMatches=1,
                          tourCardYear="", showStatsBreakdown=0, excludeWGP=0, length=20000, start=0, draw=1)
            r = requests.get("https://dartsorakel.com/api/stats/player", params=params,
                             headers={"User-Agent": UA}, timeout=120)
            r.raise_for_status()
            d = r.json()
            fn.write_text(json.dumps(dict(van=str(van), tot=str(tot), data=d["data"])), encoding="utf-8")
            print(f"  {jaar} {naam} {m} mnd: {len(d['data'])} spelers")


EVENTS_UA = "dartswk/0.3 (hobbyproject, terugtest PDC WK; beleefde ophaler met pauzes en cache)"
EVENTS_PAUZE = 1.5  # seconden tussen verzoeken (minimaal)


def fetch_orakel_events(kalenderjaren: list[int], cache: Path | None = None, pauze: float = EVENTS_PAUZE) -> None:
    """Evenementenlijst (/api/events, alle rankingtoernooien) en de resultaatpagina per event.

    Beleefd: één verzoek tegelijk, minstens `pauze` seconden ertussen, nette User-Agent, en alles wat al in de
    cache staat wordt niet opnieuw opgehaald. Abonnementspagina's (paywall) worden gemeld; de paywall wordt niet
    omzeild. robots.txt van dartsorakel.com stond bij het schrijven alles toe; controleer zelf de voorwaarden.
    """
    import time

    from .events import is_paywall

    assert pauze >= 1.5, "minstens 1,5 s pauze tussen verzoeken"
    cache = cache or config.cache_map()
    basis = cache / "orakel_events"
    (basis / "pages").mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = EVENTS_UA
    laatst = [0.0]

    def get(url, **kw):
        wacht = laatst[0] + pauze - time.monotonic()
        if wacht > 0:
            time.sleep(wacht)
        r = s.get(url, timeout=60, **kw)
        laatst[0] = time.monotonic()
        r.raise_for_status()
        return r

    for jaar in kalenderjaren:
        fn = basis / f"events_{jaar}.json"
        if not fn.exists():
            r = get("https://dartsorakel.com/api/events", params=dict(year=jaar, organCal="All Rankings"))
            fn.write_text(r.text, encoding="utf-8")
        events = json.loads(fn.read_text(encoding="utf-8"))["data"]
        paywall = 0
        for ev in events:
            pg = basis / "pages" / f"{ev['event_key']}.html"
            if not pg.exists():
                pg.write_text(get(ev["events_result_url"]).text, encoding="utf-8")
            paywall += is_paywall(pg.read_text(encoding="utf-8"))
        print(f"  {jaar}: {len(events)} events, waarvan {paywall} alleen een abonnementspagina (geen uitslagen)")


def fetch(jaren: list[int], cache: Path | None = None) -> None:
    cache = cache or config.cache_map()
    cache.mkdir(parents=True, exist_ok=True)
    for jaar in jaren:
        print(f"WK{jaar}")
        fetch_wiki(jaar, cache)
        fetch_orakel(jaar, cache)
        if not (cache / f"oddsportal_{jaar}.txt").exists():
            print(f"  geen lokale Oddsportal-cache voor {jaar}; die wordt niet opgehaald (gebruiksvoorwaarden)")
