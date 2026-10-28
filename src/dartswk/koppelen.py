"""Namen koppelen tussen Wikipedia, Oddsportal en Dartsorakel.

Regels (zie docs/review-claude.md, 2.9):
- Oddsportal-namen ("van Gerwen M.", "Zong X. C.") passen alleen als de achternaam én de initialen kloppen.
- Koppelingen zijn één-op-één; een tweede kandidaat of een dubbel gebruikte rij geeft een fout.
- Dartsorakel: exact, alias, omgekeerde naamvolgorde, umlaut-variant, en pas daarna difflib (gelogd,
  alleen bij gelijke eerste letter van de voornaam).
"""
from __future__ import annotations

import difflib
import re
import unicodedata

from . import config

_TRANS_UE = str.maketrans({"ł": "l", "Ł": "L", "ß": "ss", "ø": "o", "Ø": "O", "đ": "d", "Đ": "D",
                           "ü": "ue", "ö": "oe", "ä": "ae", "Ü": "Ue", "Ö": "Oe", "Ä": "Ae"})
_TRANS_U = str.maketrans({"ł": "l", "Ł": "L", "ß": "ss", "ø": "o", "Ø": "O", "đ": "d", "Đ": "D"})


def norm(s: str, umlaut: str = "ue") -> list[str]:
    """Naam -> kleine ascii-tokens. umlaut="ue": ü -> ue (Duitse transcriptie), "u": ü -> u."""
    s = s.translate(_TRANS_UE if umlaut == "ue" else _TRANS_U)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s).split()


def sleutel(s: str, umlaut: str = "ue") -> str:
    return " ".join(norm(s, umlaut))


def _zoek_reeks(sub: list[str], vol: list[str]) -> int:
    """Index waar sub als aaneengesloten reeks in vol staat (achteraan eerst), anders -1."""
    n = len(sub)
    for i in range(len(vol) - n, -1, -1):
        if vol[i:i + n] == sub:
            return i
    return -1


def op_past(opnaam: str, volnaam: str) -> bool:
    """Past een Oddsportal-naam ("Smith M.", "Rodriguez Ru. J.") op een volledige naam?"""
    t = opnaam.split()
    initialen = [x.rstrip(".").lower() for x in t if x.endswith(".")]
    achternaam = [x for x in t if not x.endswith(".")]
    if not achternaam:
        return False
    for umlaut in ("ue", "u"):
        sur, vol = norm(" ".join(achternaam), umlaut), norm(volnaam, umlaut)
        i = _zoek_reeks(sur, vol)
        if i < 0:
            continue
        rest = vol[:i] + vol[i + len(sur):]
        ini = [norm(x, umlaut)[0] if norm(x, umlaut) else "" for x in initialen]
        if all(r.startswith(x) for x, r in zip(ini, rest)):
            return True
    return False


def koppel_odds(wiki: list[dict], odds: list[dict]) -> tuple[dict, list[str]]:
    """Koppel elke gespeelde wiki-wedstrijd aan precies één Oddsportal-rij (namen + setstand).

    Geeft ({wedstrijdnr: (odd1, odd2) | None}, meldingen). Odds staan in de volgorde speler1, speler2.
    """
    gebruikt: dict[int, int] = {}
    uit, meld = {}, []
    for w in wiki:
        if w["walkover"]:
            continue
        kand = []
        for j, x in enumerate(odds):
            if op_past(x["p1"], w["speler1"]) and op_past(x["p2"], w["speler2"]) \
                    and (x["s1"], x["s2"]) == (w["sets1"], w["sets2"]):
                kand.append((j, x["o1"], x["o2"]))
            elif op_past(x["p2"], w["speler1"]) and op_past(x["p1"], w["speler2"]) \
                    and (x["s2"], x["s1"]) == (w["sets1"], w["sets2"]):
                kand.append((j, x["o2"], x["o1"]))
        naam = f"{w['speler1']} - {w['speler2']}"
        if len(kand) > 1:
            raise ValueError(f"WK{w['jaar']} {naam}: {len(kand)} Oddsportal-kandidaten")
        if not kand:
            uit[w["wedstrijd"]] = None
            meld.append(f"geen Oddsportal-rij: {naam}")
            continue
        j, o1, o2 = kand[0]
        if j in gebruikt:
            raise ValueError(f"Oddsportal-rij {odds[j]} gekoppeld aan wedstrijd {gebruikt[j]} én {w['wedstrijd']}")
        gebruikt[j] = w["wedstrijd"]
        if o1 is None or o2 is None:
            uit[w["wedstrijd"]] = None
            meld.append(f"geen odds op Oddsportal: {naam}")
        else:
            uit[w["wedstrijd"]] = (o1, o2)
    return uit, meld


class OrakelIndex:
    """Zoekt Dartsorakel-spelers op naam; elke WK-speler moet op één player_key uitkomen."""

    def __init__(self, orakel: dict):
        self.orakel = orakel
        self.idx: dict[str, set] = {}
        self.idx_u: dict[str, set] = {}
        for key, p in orakel.items():
            self.idx.setdefault(sleutel(p["naam"]), set()).add(key)
            self.idx_u.setdefault(sleutel(p["naam"], "u"), set()).add(key)

    def _uniek(self, keys: set, naam: str):
        if len(keys) > 1:
            raise ValueError(f"'{naam}' is dubbelzinnig bij Dartsorakel: player_keys {sorted(keys)}")
        return next(iter(keys))

    def vind(self, naam: str) -> tuple[object | None, str]:
        """(player_key of None, methode)."""
        k = sleutel(naam)
        if k in config.ALIAS:
            k, methode = config.ALIAS[k], "alias"
        else:
            methode = "exact"
        if k in self.idx:
            return self._uniek(self.idx[k], naam), methode
        om = " ".join(reversed(k.split()))  # Chinese naamvolgorde, bijv. Xiaochen Zong
        if om in self.idx:
            return self._uniek(self.idx[om], naam), "omgekeerd"
        ku = sleutel(naam, "u") if methode == "exact" else k
        if ku in self.idx_u:
            return self._uniek(self.idx_u[ku], naam), "umlaut"
        for c in difflib.get_close_matches(k, list(self.idx), n=3, cutoff=0.85):
            if c.split()[0][0] == k.split()[0][0] and c.split()[-1] == k.split()[-1]:
                return self._uniek(self.idx[c], naam), f"difflib:{c}"
        return None, "geen"

    def koppel(self, namen: list[str]) -> tuple[dict, list[str]]:
        """{naam: player_key | None} met één-op-één-controle, plus meldingen over niet-exacte koppelingen."""
        uit, meld, terug = {}, [], {}
        for n in sorted(set(namen)):
            key, methode = self.vind(n)
            uit[n] = key
            if key is None:
                meld.append(f"geen vormdata: {n}")
                continue
            if key in terug and sleutel(terug[key]) != sleutel(n):  # "Berry van Peer" = "Berry Van Peer"
                raise ValueError(f"'{n}' en '{terug[key]}' wijzen naar dezelfde Dartsorakel-speler {key}")
            terug[key] = n
            if methode != "exact":
                meld.append(f"{n} -> {self.orakel[key]['naam']} ({methode})")
        return uit, meld
