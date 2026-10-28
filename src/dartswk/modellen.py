"""Register van modellen: naam -> (afstemmen(train_rows) -> params, kans(row, params) -> P(speler1 wint))."""
from __future__ import annotations

from . import kalibratie, rating, vorm

MODELLEN = {
    "vorm": (vorm.afstemmen, vorm.kans),
    "rating": (rating.afstemmen, rating.kans),
    "rating-platt": (kalibratie.platt_afstemmen, kalibratie.platt_kans),
    "rating+markt": (kalibratie.combi_afstemmen, kalibratie.combi_kans),
    "rating+avg": (rating.afstemmen_avg, rating.kans),
    "markt-krimp": (kalibratie.marktkrimp_afstemmen, kalibratie.marktkrimp_kans),  # controle zonder rating
}
