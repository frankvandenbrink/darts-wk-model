"""Dataset opbouwen: Wikipedia-uitslagen + Oddsportal-odds + Dartsorakel-vorm."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .koppelen import OrakelIndex, koppel_odds
from .parse import controleer_wiki, load_orakel, parse_oddsportal, parse_wiki

WIKI_KOLOMMEN = ["jaar", "wedstrijd", "datum", "ronde", "setsnodig", "speler1", "speler2",
                 "sets1", "sets2", "winnaar", "walkover", "avg1_achteraf", "avg2_achteraf"]


def wiki_wedstrijden(jaar: int, cache: Path | None = None) -> tuple[list[dict], list[str]]:
    cache = cache or config.cache_map()
    rows = parse_wiki((cache / f"wiki_{jaar}.txt").read_text(encoding="utf-8"), jaar)
    return rows, controleer_wiki(rows, jaar)


def schrijf_wiki_csv(jaar: int, cache: Path | None = None, map_: Path | None = None) -> tuple[Path, list[str]]:
    """data/wedstrijden_WK<jaar>.csv met alleen Wikipedia-gegevens (CC BY-SA 4.0)."""
    rows, meld = wiki_wedstrijden(jaar, cache)
    df = pd.DataFrame(rows, columns=WIKI_KOLOMMEN)
    for k in ("sets1", "sets2"):
        df[k] = df[k].astype("Int64")
    fn = (map_ or config.data_map()) / f"wedstrijden_WK{jaar}.csv"
    fn.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(fn, index=False, encoding="utf-8")
    return fn, meld


def _vorm_kolommen(p: dict | None, kant: str) -> dict:
    """Vorm uit Dartsorakel-aggregaten: avg = punten/darts*3, co = geraakt/pogingen*100."""
    r = {}
    for m in config.VENSTERS:
        for naam in ("avg", "co"):
            v = p.get((naam, m)) if p else None
            if v and v[1] > 0:
                val = v[0] / v[1] * 3 if naam == "avg" else v[0] / v[1] * 100
                r[f"{naam}{kant}_{m}m"], r[f"n_{naam}{kant}_{m}m"] = round(val, 2), v[1]
            else:
                r[f"{naam}{kant}_{m}m"], r[f"n_{naam}{kant}_{m}m"] = None, 0
    return r


def bouw(jaar: int, cache: Path | None = None) -> tuple[list[dict], list[str]]:
    """Gespeelde wedstrijden (geen walkovers) met odds (of None) en vormfeatures van vóór het WK.

    De kolommen avg*_achteraf blijven erin ter controle maar worden door geen enkel model gebruikt.
    """
    cache = cache or config.cache_map()
    wiki, meld = wiki_wedstrijden(jaar, cache)
    odds, dubbel = parse_oddsportal((cache / f"oddsportal_{jaar}.txt").read_text(encoding="utf-8"))
    if dubbel:
        meld.append(f"{dubbel} dubbele Oddsportal-rij(en) verwijderd")
    gekoppeld, m = koppel_odds(wiki, odds)
    meld += m
    orakel = load_orakel(jaar, cache)
    idx = OrakelIndex(orakel)
    spelers, m = idx.koppel([r[k] for r in wiki for k in ("speler1", "speler2")])
    meld += m
    rows = []
    for w in wiki:
        if w["walkover"]:
            meld.append(f"walkover overgeslagen: {w['speler1']} - {w['speler2']}")
            continue
        r = dict(w)
        o = gekoppeld.get(w["wedstrijd"])
        r["odd1"], r["odd2"] = o if o else (None, None)
        for kant in ("1", "2"):
            key = spelers[w["speler" + kant]]
            r.update(_vorm_kolommen(orakel.get(key) if key is not None else None, kant))
        rows.append(r)
    return rows, meld
