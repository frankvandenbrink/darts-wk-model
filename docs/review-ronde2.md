# Review ronde 2: experimentkader

Een kritische review van de code uit ronde 1 (`src/dartswk/experimenten.py` en wat het aanroept: `rating.py`,
`events.py`, `kalibratie.py`, `evaluatie.py`, `terugtest.laad`). Datum: 2026-10-29.

## 1. Lookahead

| Wat | Gecontroleerd | Oordeel |
|---|---|---|
| Markt | `odd1/odd2` zijn slotodds per wedstrijd, gebruikt als kans en als feature voor díe wedstrijd. | In orde: de slotodd is bekend vóór de wedstrijd. Kanttekening: wie later wedt dan bij de sluiting, krijgt andere odds. |
| Ratings (BT) | `rating.context(jaar)` laadt events met `datum < WK-start` (assert in `events.laad_wedstrijden` en `rating.fit_bt`). Een event heeft de datum van de finaledag, dus ook meerdaagse events zitten er alleen in als ze helemaal vóór de WK-start klaar waren. | In orde. |
| Elo/Glicko | `elo_ratings` gebruikt dezelfde context en assert. Tijdens het WK wordt niet bijgewerkt (conservatief, geen lek). | In orde. |
| Vorm | `parse.load_orakel` assert dat de vormperiode vóór de WK-start eindigt. | In orde. |
| Spelerskoppeling | `keymap` gebruikt de deelnemerslijst van het WK; die is vóór de start bekend. | In orde. |
| Afstemmen/kalibratie | `draai_split` geeft de afstemfunctie alleen de trainrijen. Platt, isotoon, blend (lambda via CV) en de drempel komen uit train. Lambda-CV gebruikt leave-one-year-out of vaste folds binnen train. | In orde. |
| Walk-forward | Assert `max(train) < min(test)`; train en test overlappen niet (assert). | In orde. |
| Vaste richtingen | Afstemmen op een later WK (bijv. 2026 → 2025) is per definitie geen walk-forward. Staat zo in tabel en protocol. | Geen fout, wel alleen ter vergelijking. |

Wel een historisch punt dat al gemeld was: het `RATING_GRID` is verbreed na het zien van resultaten (E007 heeft
`na_test_aangepast: true`). Alle modellen die op `RATING_GRID` steunen (E009, E017, E020, E023, ...) erven dat.
Dat blijft een zwak punt: zie protocol hieronder.

**Geen lookahead gevonden.**

## 2. Geclusterde bootstrap: intervallen van [−100%, +100%]

Voorbeeld E002 (markt-vlak), walk-forward test 2026: 28 bets in 6 clusters (jaar, ronde):

| Ronde | Bets | Winst | ROI |
|---|---|---|---|
| 1 | 15 | +19,0 | +127% |
| 2 | 6 | −6,0 | −100% |
| 3 | 4 | −4,0 | −100% |
| 4, QF, SF | 1 elk | −1,0 elk | −100% |

De bootstrap trekt 6 clusters met teruglegging. Zit ronde 1 niet in de trekking (kans (5/6)^6 ≈ 33%), dan is de
ROI precies −100%. De ondergrens van 5% is dus −100%. De bovengrens van precies +100% is toeval van de discrete
verdeling: drie keer ronde 1, één keer ronde 3 en twee rondes met één bet geeft 51/51 = +100%.

**Geen bug.** De lege resample komt niet voor: er wordt per cluster getrokken en elk cluster heeft ≥ 1 bet, en bij
< 2 clusters geeft de functie geen interval. Het probleem is dat een WK hoogstens 7 rondes en dus 7 clusters per
testjaar heeft. Dan is een clusterbootstrap grof en scheef. **Fix:** het aantal clusters staat nu per
experiment en testjaar in de uitvoer (`clusters`), in `resultaten/experimenten.md` en in de dashboardtabel, met
een uitleg. De ROI-intervallen moeten met dat aantal in gedachten gelezen worden. De cijfers veranderen niet.

## 3. Registerprotocol

| Punt | Bevinding | Gefixt? |
|---|---|---|
| Vingerafdruk tegen de eerste run | `protocolcheck` vergelijkt met de eerste gelogde run, niet de laatste. Een tweede run kan een stille wijziging dus niet witwassen. | Was al goed; test toegevoegd. |
| Vingerafdruk dekt alleen het register | Hypothese, criterium, model, features en grid. Wijzigingen in `config.RATING_GRID`/`GRID`, de drempels, `MIN_BETS_DREMPEL`, `HOLD`, de bootstrap of de splits bleven onzichtbaar, terwijl veel modellen daarop steunen (`"grid": {"bron": "config.RATING_GRID"}`). | **Ja:** een tweede hash (`context`) over splits, config-grids, drempels, hold en bootstrap staat in de log. Verandert die na de eerste run zonder `na_test_aangepast`, dan volgt een waarschuwing. Oude logregels hebben dit veld niet, dus zij worden niet gecontroleerd. |
| `na_test_aangepast: true` zonder toelichting | Werd geaccepteerd en zette de waarschuwing stil uit. | **Ja:** dat geeft nu een fout. |
| Is het vooraf vastleggen aantoonbaar? | Niets legde vast of de registratie vóór de run gecommit was. | **Deels:** de log bevat nu de git-commit en `register_gewijzigd` (of `register.json` niet-gecommitte wijzigingen had tijdens de run). In ronde 2 is het register van E024–E028 eerst apart gecommit, daarna gedraaid. |
| Codewijzigingen | Een bugfix in modelcode verandert cijfers zonder dat de vingerafdruk verandert. | **Deels:** de commit-hash in de log maakt het nagaan mogelijk. Een automatische waarschuwing is er niet. |
| Waarschuwingen zichtbaar | Komen in `resultaten/experimenten.md` (regel *Status*) en in de JSON. | In orde. |
| Runlog is te bewerken | `runlog.jsonl` staat in git, dus geschiedenis blijft na te gaan. Er is geen technische bescherming. | Niet gefixt (bewust: hobbyproject). |

## 4. Wat veranderde er aan de cijfers?

Niets. De fixes voegen alleen velden toe (`clusters`, `context`, `commit`, `register_gewijzigd`). Alle
experimenten zijn opnieuw gedraaid zodat het clustersveld overal staat. De log-loss- en ROI-cijfers van
E001–E023 bleven gelijk, dus `na_test_aangepast` is nergens aangepast.
