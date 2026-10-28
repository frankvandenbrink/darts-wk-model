"""Instellingen: jaren, paden en vaste modelkeuzes.

Een jaar toevoegen = één regel in JAREN (jaar van de finale).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Aantal sets nodig om te winnen per ronde (first to n sets). Gelijk voor 2024-2026.
SETS_PER_RONDE = {"1": 3, "2": 3, "3": 4, "4": 4, "QF": 5, "SF": 6, "F": 7}


@dataclass(frozen=True)
class WK:
    start: str          # eerste speeldag (ISO); vormdata loopt tot en met de dag ervoor
    wiki: str           # titel van het Engelstalige Wikipedia-artikel
    oddsportal: str     # seizoen-slug op oddsportal.com/darts/world/<slug>/results/
    spelers: int        # grootte van het speelschema
    sets_per_ronde: dict = field(default_factory=lambda: dict(SETS_PER_RONDE))


JAREN: dict[int, WK] = {
    2024: WK("2023-12-15", "2024_PDC_World_Darts_Championship", "pdc-world-championship-2023-2024", 96),
    2025: WK("2024-12-15", "2025_PDC_World_Darts_Championship", "pdc-world-championship-2024-2025", 96),
    # Opgehaald als "pdc-world-championship" (het lopende seizoen). Het expliciete slug hieronder is
    # het vermoedelijke archiefadres na de start van WK2027 en is nog niet geverifieerd.
    2026: WK("2025-12-11", "2026_PDC_World_Darts_Championship", "pdc-world-championship-2025-2026", 128),
}

VENSTERS = [3, 6, 12]  # maanden vorm die we ophalen bij Dartsorakel

# Naam op Wikipedia (genormaliseerd) -> naam bij Dartsorakel (genormaliseerd)
ALIAS = {
    "man lok leung": "hugo leung man lok",
    "radek szaganski": "radoslaw szaganski",
}

FALLBACK_AVG, FALLBACK_CO = 80.0, 33.0  # speler zonder vormdata
HOLD = 0.60                              # kans dat de beginnende speler een leg wint bij gelijke sterkte
MIN_DARTS_KORT, MIN_CO_KORT = 300, 100   # minimale data in het 3-maandenvenster

GRID = dict(
    w=[0.0, 0.25, 0.5, 0.75],
    L=[6, 12],
    k=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15],
    kc=[0.0, 0.01, 0.02, 0.04],
)
# Ratingmodel (rating.py): grid, afgestemd op log-loss op train. Ratings op de logit-schaal van een leg.
RATING_GRID = dict(
    # Twee keer verbreed omdat het optimum op de rand lag (eerst k=0.6, halfwaarde=730, lam=0.5, onbekend=0;
    # daarna halfwaarde=1460). 100000 dagen = in feite geen tijdsweging.
    halfwaarde=[90, 180, 365, 730, 1460, 2920, 100000],  # dagen
    lam=[0.1, 0.5, 2.0, 5.0, 20.0],            # prior-precisie
    onbekend=[-0.9, -0.6, -0.3, 0.0, 0.3],     # rating van WK-spelers zonder data
    k=[0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5],  # schaal ratingverschil op het WK
    g=[0.0, 0.02, 0.04, 0.08],            # alleen rating+avg: gewicht per averagepunt
)

DREMPELS = [1.00, 1.05, 1.10, 1.15, 1.20, 1.30]
VASTE_DREMPEL = 1.05  # vooraf genoemde regel 'eigen kans x odd > 1,05'; alleen ter informatie
MIN_BETS_DREMPEL = 10   # een drempel telt alleen mee bij minstens zoveel bets op train
BOOTSTRAP_N = 5000


def basis() -> Path:
    """Projectmap: $DARTSWK_HOME of de huidige map."""
    return Path(os.environ.get("DARTSWK_HOME", Path.cwd()))


def cache_map() -> Path:
    return basis() / "data" / "cache"


def data_map() -> Path:
    return basis() / "data"


def resultaten_map() -> Path:
    return basis() / "resultaten"
