"""Parsen van de gecachte bronbestanden."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from . import config

MAANDEN = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


# ---------------------------------------------------------------- Wikipedia
def _speler(cel: str) -> tuple[str | None, float | None, bool]:
    """(naam, in-wedstrijd-average, winnaar-markering) uit een wikitext-cel."""
    winnaar = "b=1" in cel or "'''" in cel
    m = re.search(r"PDCFlag\|([^|}]+)(?:\|[^}]*?avg=([\d.]+))?", cel)
    if not m:
        m = re.search(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]'*\s*([\d.]+)?", cel)
    if not m:
        m = re.match(r"^'*([^'\d{}\[\]|]+?)'*\s*([\d.]+)?$", cel.strip())  # naam zonder link
    if not m:
        return None, None, winnaar
    return m.group(1).strip(), (float(m.group(2)) if m.group(2) else None), winnaar


def _datum(dag: str | None, jaar: int) -> str | None:
    """'Friday, 15 December' -> ISO-datum; december hoort bij het jaar vóór de finale."""
    if not dag:
        return None
    _, d, mnd = dag.replace(",", "").split()
    mnd = MAANDEN[mnd]
    return date(jaar - 1 if mnd >= 7 else jaar, mnd, int(d)).isoformat()


def parse_wiki(tekst: str, jaar: int) -> list[dict]:
    """Alle wedstrijden uit de sectie ==Schedule==, inclusief walkovers (sets leeg, walkover=1).

    De averages zijn de averages ín de wedstrijd zelf: pas achteraf bekend, dus nooit als feature gebruiken.
    """
    sets_nodig = config.JAREN[jaar].sets_per_ronde if jaar in config.JAREN else config.SETS_PER_RONDE
    s = tekst.find("==Schedule==")
    if s < 0:
        raise ValueError(f"geen ==Schedule== in wikitext {jaar}")
    e = tekst.find("\n==", s + 15)
    sectie = tekst[s:e if e > 0 else None]
    rows, ronde, dag = [], None, None
    for line in sectie.split("\n"):
        m = re.search(r"title=(\w+day, \d+ \w+)", line)
        if m:
            dag = m.group(1)
        if not re.match(r"^\|\s*\d+\s*\|\|", line):
            continue
        low = line.lower()
        walkover = "w/o" in low
        if "dart score" not in low and not walkover:
            continue
        c = [x.strip() for x in line.split("||")]
        nr = int(c[0].lstrip("|").strip())
        i = 1
        c1 = re.sub(r"rowspan=\"?\d+\"?\s*\|", "", c[1]).strip()
        if "[[" not in c1 and "{{" not in c1:
            ronde, i = c1, 2
        p1, a1, w1 = _speler(c[i])
        p2, a2, w2 = _speler(c[i + 2])
        if p1 is None or p2 is None:
            raise ValueError(f"WK{jaar} wedstrijd {nr}: speler niet te lezen: {line[:120]}")
        r = dict(jaar=jaar, wedstrijd=nr, datum=_datum(dag, jaar), ronde=ronde,
                 setsnodig=sets_nodig[ronde], speler1=p1, speler2=p2)
        if walkover:
            if w1 == w2:
                raise ValueError(f"WK{jaar} wedstrijd {nr}: winnaar van walkover onduidelijk")
            r.update(sets1=None, sets2=None, winnaar=1 if w1 else 2, walkover=1)
        else:
            sc = re.search(r"dart score\|(\d+)\|(\d+)", c[i + 1], re.I)
            s1, s2 = int(sc.group(1)), int(sc.group(2))
            if s1 == s2:
                raise ValueError(f"WK{jaar} wedstrijd {nr}: gelijke setstand {s1}-{s2}")
            if max(s1, s2) > r["setsnodig"]:
                raise ValueError(f"WK{jaar} wedstrijd {nr}: {s1}-{s2} past niet bij ronde {ronde}")
            r.update(sets1=s1, sets2=s2, winnaar=1 if s1 > s2 else 2, walkover=0)
        r.update(avg1_achteraf=a1, avg2_achteraf=a2)
        rows.append(r)
    return rows


def controleer_wiki(rows: list[dict], jaar: int) -> list[str]:
    """Controles op het speelschema; geeft waarschuwingen terug, gooit bij harde fouten."""
    wk = config.JAREN[jaar]
    if len(rows) != wk.spelers - 1:
        raise ValueError(f"WK{jaar}: {len(rows)} wedstrijden, verwacht {wk.spelers - 1}")
    nrs = [r["wedstrijd"] for r in rows]
    if len(set(nrs)) != len(nrs):
        raise ValueError(f"WK{jaar}: dubbele wedstrijdnummers")
    w = []
    for r in rows:
        if not r["walkover"] and max(r["sets1"], r["sets2"]) != r["setsnodig"]:
            w.append(f"WK{jaar} wedstrijd {r['wedstrijd']}: {r['sets1']}-{r['sets2']} (opgave?)")
    return w


# ---------------------------------------------------------------- Oddsportal
def parse_oddsportal(tekst: str) -> tuple[list[dict], int]:
    """Afgelopen wedstrijden met slotodds. Geeft (rijen, aantal verwijderde dubbele rijen).

    Dubbele rijen (zelfde spelers, uitslag en odds, andere datum door overlap tussen pagina's) worden ontdubbeld.
    Odds '-' (geen odds beschikbaar) wordt None.
    """
    L = [x.strip() for x in tekst.splitlines() if x.strip()]
    rows, gezien, dubbel, dag = [], set(), 0, None
    for i, x in enumerate(L):
        m = re.match(r"^(\d\d \w{3} \d{4})", x)
        if m:
            dag = m.group(1)
        if not x.startswith("Finished") or i + 7 >= len(L):
            continue
        s1, p1, streep, p2, s2, o1, o2 = L[i + 1:i + 8]
        if streep != "-" or not s1.isdigit() or not s2.isdigit():
            continue
        try:
            o1f, o2f = float(o1), float(o2)
        except ValueError:
            o1f = o2f = None
        k = (p1, p2, int(s1), int(s2), o1f, o2f)
        if k in gezien:
            dubbel += 1
            continue
        gezien.add(k)
        rows.append(dict(dag=dag, p1=p1, p2=p2, s1=int(s1), s2=int(s2), o1=o1f, o2=o2f))
    return rows, dubbel


# ---------------------------------------------------------------- Dartsorakel
def load_orakel(jaar: int, cache: Path) -> dict:
    """{player_key: {"naam": str, ("avg"|"co", m): (som, aantal)}}.

    avg: som = punten, aantal = darts; co: som = geraakt, aantal = pogingen.
    """
    start = date.fromisoformat(config.JAREN[jaar].start)
    out: dict = {}
    for m in config.VENSTERS:
        for naam in ("avg", "co"):
            d = json.loads((cache / f"orakel_{jaar}_{naam}_{m}m.json").read_text(encoding="utf-8"))
            assert date.fromisoformat(d["tot"]) < start, \
                f"orakel {jaar} {naam} {m}m: vormperiode tot {d['tot']} eindigt niet vóór WK-start {start}"
            for x in d["data"]:
                p = out.setdefault(x["player_key"], {"naam": x["player_name"]})
                p[(naam, m)] = (x["sumField1"], x["sumField2"])
    return out
