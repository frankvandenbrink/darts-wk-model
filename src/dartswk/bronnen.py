"""Ophalen van ruwe brondata naar data/cache/ (wordt niet gecommit).

- Wikipedia: wikitext van het WK-artikel (CC BY-SA 4.0).
- Dartsorakel: geaggregeerde averages en checkout% per speler over 3/6/12 maanden vóór het WK.
- Oddsportal: resultatenpagina's met slotodds; alleen leesbaar met een echte browser (playwright).

Controleer zelf de gebruiksvoorwaarden van Oddsportal en Dartsorakel voordat je ophaalt.
"""
from __future__ import annotations

import json
import os
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


def fetch_oddsportal(jaar: int, cache: Path) -> None:
    fn = cache / f"oddsportal_{jaar}.txt"
    if fn.exists():
        return
    import asyncio

    try:
        from playwright.async_api import async_playwright
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("playwright ontbreekt: pip install -e '.[odds]' && playwright install chromium") from e

    base = f"https://www.oddsportal.com/darts/world/{config.JAREN[jaar].oddsportal}/results/"
    chrome = os.environ.get("DARTSWK_CHROME")  # bijv. /usr/bin/google-chrome; leeg = playwright-chromium

    async def main():
        out = []
        async with async_playwright() as p:
            kw = dict(headless=True, args=["--no-sandbox"])
            if chrome:
                kw["executable_path"] = chrome
            b = await p.chromium.launch(**kw)
            ctx = await b.new_context(user_agent=UA)
            for n in range(1, 8):
                pg = await ctx.new_page()
                await pg.goto(base + (f"#/page/{n}/" if n > 1 else ""), wait_until="domcontentloaded", timeout=60000)
                await pg.wait_for_timeout(4000)
                for _ in range(12):
                    await pg.mouse.wheel(0, 4000)
                    await pg.wait_for_timeout(700)
                t = await pg.inner_text("body")
                await pg.close()
                if t.count("Finished") == 0:
                    break
                out.append(f"=====PAGE {n}\n" + t)
            await b.close()
        fn.write_text("\n".join(out), encoding="utf-8")

    asyncio.run(main())


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
        try:
            fetch_oddsportal(jaar, cache)
        except Exception as e:  # noqa: BLE001 - odds zijn optioneel; meld en ga door
            print(f"  oddsportal mislukt voor {jaar}: {e}")
