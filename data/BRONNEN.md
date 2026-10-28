# Bronvermelding data/

De bestanden `wedstrijden_WK<jaar>.csv` zijn afgeleid van de Engelstalige Wikipedia-artikelen hieronder
(sectie *Schedule*), opgehaald als wikitext via `action=raw` en omgezet met `dartswk dataset`.
Ze vallen onder de licentie [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
hergebruik mag onder dezelfde licentie en met naamsvermelding van de Wikipedia-bijdragers.

| Bestand | Bron |
|---|---|
| `wedstrijden_WK2024.csv` | [2024 PDC World Darts Championship](https://en.wikipedia.org/wiki/2024_PDC_World_Darts_Championship) |
| `wedstrijden_WK2025.csv` | [2025 PDC World Darts Championship](https://en.wikipedia.org/wiki/2025_PDC_World_Darts_Championship) |
| `wedstrijden_WK2026.csv` | [2026 PDC World Darts Championship](https://en.wikipedia.org/wiki/2026_PDC_World_Darts_Championship) |

Auteurs: de bijdragers aan deze artikelen (zie de versiegeschiedenis op Wikipedia).
Wijzigingen: alleen de speelschema-tabel is overgenomen, omgezet naar CSV en aangevuld met `setsnodig`
(afgeleid uit de ronde) en `winnaar`.

## Kolommen

| Kolom | Betekenis |
|---|---|
| `jaar` | jaar van de finale |
| `wedstrijd` | wedstrijdnummer op Wikipedia |
| `datum` | speeldag (ISO) |
| `ronde` | 1, 2, 3, 4, QF, SF, F |
| `setsnodig` | first to n sets, volgt uit de ronde |
| `speler1`, `speler2` | naam zoals op Wikipedia |
| `sets1`, `sets2` | setstand (leeg bij walkover) |
| `winnaar` | 1 of 2 |
| `walkover` | 1 als de wedstrijd niet gespeeld is |
| `avg1_achteraf`, `avg2_achteraf` | three-dart average **in de wedstrijd zelf**. Pas achteraf bekend: nooit als feature gebruiken |

`data/cache/` (ruwe Wikipedia-, Oddsportal- en Dartsorakel-bestanden) wordt niet gecommit.
