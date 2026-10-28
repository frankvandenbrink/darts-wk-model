# Ratingmodel op wedstrijdniveau (`--model rating`)

Uitwerking van prioriteit 1 en 3 uit [review-claude.md](review-claude.md), sectie 4: een rating met correctie voor
de tegenstander en krimp, gekoppeld aan het bestaande set/match-model, plus kalibratie en combinatie met de markt.
Alle cijfers hieronder komen uit [`resultaten/vergelijking.md`](../resultaten/vergelijking.md)
(`dartswk vergelijk`).

**Kort:** het ratingmodel voorspelt slechter dan de markt én slechter dan het vormmodel. De combinatie met de markt
komt op log-loss in de buurt van de markt, maar niet eronder. De positieve ROI van `rating+markt` is ook te halen
zonder rating, door de markt alleen wat vlakker te maken (`markt-krimp`). De rating voegt dus niets aantoonbaars toe.
De belangrijkste oorzaak is waarschijnlijk de data: 65% van de resultaatpagina's in de cache is een
abonnementspagina, en vóór WK2026 is het laatste bruikbare event van 11 maart 2025.

## 1. Data

- Evenementenlijst: `https://dartsorakel.com/api/events?year=Y&organCal=All Rankings` voor 2022–2025:
  Players Championships, European Tour, majors en het WK. Gecachet in `data/cache/orakel_events/events_<jaar>.json`.
- Per event de resultaatpagina (`events_result_url`) in `data/cache/orakel_events/pages/<event_key>.html`. Daarin
  staan tabellen Winner | Score | Runner Up met de player_key in de link, de legstand en het average.
- `dartswk fetch-events` haalt dit beleefd op: één verzoek tegelijk, minstens 1,5 s pauze, cache, een eigen
  User-Agent, en wat al gecachet is wordt overgeslagen. Voor deze PR is niets opnieuw opgehaald; alles kwam uit
  de bestaande cache.
- **Paywall.** 133 van de 205 gecachete pagina's zijn geen uitslagen maar de pagina "Subscription – Darts Orakel".
  Die worden herkend (`events.is_paywall`), overgeslagen en geteld. Ik heb niet geprobeerd de paywall te omzeilen.
  Of het om een limiet per bezoeker gaat of om inhoud die alleen voor abonnees is, weet ik niet. Robots.txt staat
  ophalen toe, maar dat zegt niets over de abonnementsvoorwaarden.

| WK | Cutoff (events < WK-start) | Events | Met uitslagen | Paywall | Wedstrijden | Waarvan sets | Laatste bruikbare event | WK-spelers zonder data |
|---|---|---|---|---|---|---|---|---|
| 2024 | 2023-12-15 | 100 | 60 | 40 | 5874 | 249 | 2023-10-20 | 14 van 98 |
| 2025 | 2024-12-15 | 150 | 71 | 79 | 6868 | 249 | 2024-10-30 | 11 van 98 |
| 2026 | 2025-12-11 | 205 | 72 | 133 | 6995 | 249 | 2025-03-11 | 21 van 128 |

Van 2025 is één event bruikbaar (PC, maart 2025), van 2024 elf. De rating voor WK2026 rust daardoor vooral op
2022–2024. Spelers die in 2025 doorbraken, of die hun sterkte in 2025 veranderden, worden slecht ingeschat.
Voorbeelden uit WK2026 (walk-forward-parameters): Littler–Cross 0.56 bij het model tegen 0.90 bij de markt,
Smith–Harrysson 0.36 tegen 0.79.

"WK-spelers" telt de namen in het speelschema (98 bij 96 deelnemers, omdat een paar spelers op Wikipedia onder
twee spellingen voorkomen).

**Cutoff.** Een event heeft één datum; bij het WK is dat de finaledag (2024-01-03 = WK2024). Voor WK j tellen alleen
events met datum strikt vóór de WK-start van j. `laad_wedstrijden` filtert hierop en `fit_bt` controleert het
nog eens met een assert. Een wedstrijd op of na de cutoff geeft dus een fout, en dat staat ook in de tests. Het
WK zelf telt pas mee voor het WK van een jaar later.

**Koppeling.** WK-namen worden via de bestaande `OrakelIndex` gekoppeld aan de player_key. Die index gebruikt de
namen uit de eventpagina's en uit de aggregaatbestanden. Niet-exacte koppelingen worden gemeld, bijvoorbeeld
Bhav Patel → Bhaval Patel (difflib), David Cameron → Dave Cameron, en Zong/Leung via omgekeerde volgorde en alias.

**Sets.** Bij World Championship en World Grand Prix staat de score in sets. Daar telt alleen de uitslag mee, als
één waarneming met kans logistic(s·(r_a − r_b)). Daarbij is s ≈ 3.72: de helling van de exacte wedstrijdkans bij
first to 3 sets. Wedstrijden zonder averages bij beide spelers (vermoedelijk walkovers, 1 in de data) vallen af.

## 2. Model

1. **Leg-Bradley-Terry.** P(a wint een leg van b, gemiddeld over wie begint) = logistic(r_a − r_b). De ratings zijn
   de MAP-schatting van
   `Σ_m w_m [legs_a log σ(r_a−r_b) + legs_b log σ(r_b−r_a)] − λ/2 Σ r_i²`, met `w_m = 0.5^(leeftijd/halfwaarde)`.
   Die wordt gevonden met Newton op de volledige Hessiaan (±300–350 spelers, minder dan 0,1 s per fit). De prior
   krimpt spelers met weinig data naar 0, het tijdsgewogen gemiddelde van het veld. WK-spelers zonder data krijgen
   de rating `onbekend`, die op train wordt afgestemd.
2. **Naar hold-kansen.** Het verschil d = k·(r_a − r_b) wordt omgezet in hold-kansen
   h_a = logistic(H + x) en h_b = logistic(H − x), met H = logit(0.60). Daarbij is x zo gekozen dat
   ½(h_a + 1 − h_b) = logistic(d). Bij k = 1 is de gemiddelde legkans op het WK dus precies die van de rating.
   Daarna volgt de bestaande exacte set/match-DP, met het aantal sets uit de ronde. De hold-basis 0.60 is niet
   geschat: zonder data over wie begon kan dat niet, en volgens de review is de gevoeligheid kleiner dan 0.001 in
   log-loss.
3. **Afstemmen.** Grid search op log-loss over de WK-wedstrijden van de trainjaren (alleen wedstrijden met odds,
   zodat n gelijk is aan de evaluatie):
   halfwaarde ∈ {90, 180, 365, 730, 1460, 2920, 100000} dagen (100000 = in feite geen tijdsweging),
   λ ∈ {0.1, 0.5, 2, 5, 20}, onbekend ∈ {−0.9, −0.6, −0.3, 0, 0.3} en k ∈ {0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5}.
   Daarna volgt de bestaande drempelkeuze op train-ROI (minimaal 10 bets), met de stopregel "ROI ≤ 0 → niet
   wedden".
4. **`rating+markt`.** logit p = a·logit(markt) + b·logit(p_rating). Markt is hier proportioneel. a en b worden met
   logistische regressie op train gefit, op de kansen van het op dezelfde train afgestemde ratingmodel. Er is geen
   intercept, omdat de volgorde speler1/speler2 willekeurig is. Gerapporteerd worden a en b met standaardfout, en de
   LR-statistiek voor b = 0.
5. **`rating-platt`.** logit p = c·logit(p_rating), met c gefit op train en zonder intercept, om dezelfde reden.
   Omdat k al op log-loss is afgestemd, ligt c steeds dicht bij 1 (0.92–1.04) en verandert Platt weinig.
6. **`rating+avg`** (ter informatie): d = k·(Δr + g·Δu). Daarin is u het gekrompen, tijdsgewogen average ten opzichte
   van het eventgemiddelde, met g ∈ {0, 0.02, 0.04, 0.08}. Volgens de opdracht telt dit alleen als het out-of-sample
   helpt. Het helpt een klein beetje ten opzichte van `rating`, maar het blijft ver achter bij de markt en bij het
   vormmodel. Het is dus niet opgenomen in het hoofdmodel.
7. **`markt-krimp`** (controle, geen voorstel): logit p = a·logit(markt), zonder rating. Hiermee is na te gaan of
   winst van `rating+markt` alleen komt doordat de markt vlakker wordt gemaakt.

Keuzes die vooraf vastlagen: hold-basis 0.60, de prior met gemiddelde 0 voor iedereen, en λ voor averages
(50 legs). **Na het bekijken van de eerste resultaten** (train én test) is het grid twee keer verbreed, omdat het
optimum op de rand lag: eerst k = 0.6, halfwaarde = 730, λ = 0.5 en onbekend = 0, daarna halfwaarde = 1460. De
testcijfers zijn daarna niet meer gebruikt voor keuzes. Wel zijn ze toen al gezien, dus dit is een vrijheidsgraad
van de onderzoeker. De verbreding maakte het model op test niet duidelijk beter of slechter.

## 3. Resultaten

Log-loss op het testjaar (lager is beter). n: 94 (2024), 94 (2025) en 126 (2026). "Helling" is c in
logit P(winst) = c·logit(p) op test: kleiner dan 1 betekent te stellig.

| Train → test | Rating | Rating-Platt | Rating+markt | Markt-krimp | Vorm | Markt prop. | Markt Shin | Helling rating |
|---|---|---|---|---|---|---|---|---|
| 2026 → 2025 | 0.6494 | 0.6507 | 0.6324 | 0.6306 | 0.6179 | 0.6343 | 0.6371 | 0.77 |
| 2025 → 2026 | 0.6369 | 0.6377 | 0.5806 | 0.5578 | 0.5680 | 0.5490 | 0.5498 | 0.71 |
| 2025 → 2024 | 0.6048 | 0.6047 | 0.5798 | 0.5786 | 0.5985 | 0.5698 | 0.5722 | 1.07 |
| 2025+2026 → 2024 | 0.5997 | 0.5999 | 0.5703 | 0.5715 | 0.5973 | 0.5698 | 0.5722 | 1.37 |
| WF 2024 → 2025 | 0.6888 | 0.6774 | 0.6444 | 0.6316 | 0.6461 | 0.6343 | 0.6371 | 0.45 |
| WF 2024+2025 → 2026 | 0.6236 | 0.6231 | 0.5610 | 0.5509 | 0.5725 | 0.5490 | 0.5498 | 0.73 |
| **WF totaal (220)** | **0.6515** | 0.6463 | **0.5966** | 0.5854 | **0.6039** | **0.5854** | 0.5871 | 0.59 |

Brier, walk-forward totaal: rating 0.2213, rating+markt 0.2043, markt-krimp 0.2011, vorm 0.2062, markt 0.2010.
Verschil in log-loss met de markt per wedstrijd (walk-forward totaal, standaardfout): rating +0.066 (0.030),
rating+markt +0.011 (0.012), vorm +0.019 (0.012).

**Coëfficiënten van `rating+markt`** (op train; se tussen haakjes; LR voor b = 0, kritieke waarde 3.84):

| Train | a (markt) | b (rating) | LR |
|---|---|---|---|
| 2026 | 0.86 (0.26) | 0.15 (0.33) | 0.22 |
| 2025 | 0.40 (0.33) | 0.52 (0.49) | 1.13 |
| 2025+2026 | 0.77 (0.20) | 0.12 (0.28) | 0.17 |
| 2024 (WF) | 0.62 (0.35) | 0.40 (0.33) | 1.77 |
| 2024+2025 (WF) | 0.58 (0.26) | 0.36 (0.33) | 1.24 |

b is steeds positief, maar nergens significant. Dat a < 1 is, betekent dat de combinatie de markt vlakker maakt.

**Wedden** (drempel en stopregel op train; 90%-interval met bootstrap per ronde):

| Train → test | Rating: bets, ROI [90%] | Rating+markt: bets, ROI [90%] | Markt-krimp: bets, ROI | Vorm: bets, ROI |
|---|---|---|---|---|
| 2026 → 2025 | 39, +32.7% [−20.0, +75.2] | 7, −100.0% | 9, +50.0% | 0 (stopregel) |
| 2025 → 2026 | 105, −6.7% [−55.0, +7.2] | 71, +12.9% [−55.3, +31.8] | 99, +2.9% | 68, −26.9% |
| 2025 → 2024 | 73, +7.7% [−18.3, +47.8] | 48, +12.8% [−22.5, +71.4] | 73, +8.0% | 63, +6.6% |
| 2025+2026 → 2024 | 45, +14.4% [−29.2, +118.5] | 19, +42.1% [−30.0, +220.0] | 17, +58.8% | 65, −0.8% |
| WF 2024 → 2025 | 47, +17.5% [−24.8, +63.0] | 64, +14.7% [−22.1, +54.4] | 28, +25.9% | 34, +16.9% |
| WF 2024+2025 → 2026 | 103, −4.1% [−61.6, +13.8] | 49, +35.8% [−39.1, +55.3] | 28, +21.4% | 37, −43.6% |
| **WF totaal** | 150, +2.7% [−26.6, +21.3] | 113, **+23.8%** [−9.4, +48.6] | 56, +23.7% [−50.0, +71.4] | 71, −14.7% [−48.0, +22.0] |

Nulvergelijking, blind op de underdog: 2024 −4.5% (92), 2025 +25.0% (94), 2026 +1.2% (124).

## 4. Kritische lezing

- **Kansen.** Het ratingmodel is in elke split slechter dan de markt en ook slechter dan het vormmodel. Het
  verschil met het vormmodel is het kleinst met 2024 als testjaar (0.6048 tegen 0.5985 en 0.5997 tegen 0.5973),
  het jaar met de minst onvolledige data. Out-of-sample is het te stellig (helling 0.45–0.77 in 2025/2026), ook al kiest de grid een
  k van maar 0.5–0.8. De ratings zijn dus ruisig of verouderd ten opzichte van de vorm op het WK.
- **De +23.8% van `rating+markt` is geen bewijs voor de rating.**
  - De log-loss van de combinatie is slechter dan die van de markt (+0.011 per wedstrijd).
  - b is nergens significant.
  - `markt-krimp`, dezelfde markt zonder rating maar vlakker gemaakt, geeft dezelfde ROI (+23.7%).
  - De bets zijn vooral underdogs (90 van 113), en in 2025 leverde blind op de underdog al +25% op.

  De winst zit dus in de kanteling naar underdogs in deze steekproef, niet in informatie uit de rating. Alle
  intervallen bevatten 0.
- **Lekken.** Ik heb er niet een gevonden.
  - Ratings gebruiken alleen events vóór de WK-start (assert).
  - Odds en uitslagen van het testjaar worden niet gebruikt bij het afstemmen.
  - De slotodds die de combinatie als input gebruikt, zijn dezelfde odds waartegen gewed wordt. Dat is
    consistent, maar het blijft de kanttekening uit de review (2.5): slotodds van Oddsportal zijn niet de odds die
    je zelf krijgt.
  - In de richtingen 2026 → 2025 en 2025(+2026) → 2024 zijn de hyperparameters op latere jaren afgestemd. De
    ratings zelf bevatten geen informatie uit de toekomst.
- **Waarom zo zwak?** De meest waarschijnlijke oorzaak is de data:
  - Van de laatste 12 maanden vóór elk WK ontbreekt het grootste deel. Vóór WK2026 is er na maart 2025 niets.
  - Er zijn geen majors uit 2024–2025.
  - De Premier League en andere toernooien buiten de ranking ontbreken.
  - Tijdsweging helpt dan niet. De grid kiest bijna altijd halfwaarde 100000, dus geen weging: met de beschikbare
    data is "meer data" belangrijker dan "recente data".

  Of het model met volledige data beter zou zijn, kan ik met deze cache niet zeggen.
- **Steekproef.** 314 WK-wedstrijden in drie toernooien. Zie review sectie 3: voor een betrouwbaar oordeel over ROI
  zijn duizenden bets nodig. De rating maakt het wel mogelijk om op alle Pro Tour-wedstrijden te toetsen, zodra er
  odds voor die wedstrijden zijn.

## 5. Gebruik

```bash
dartswk fetch-events --kalenderjaren 2022 2023 2024 2025   # alleen als de cache ontbreekt; beleefd, met pauzes
dartswk terugtest --model rating --walk-forward --jaren 2024 2025 2026
dartswk terugtest --model rating+markt --train 2025 --test 2026
dartswk vergelijk                                          # alles -> resultaten/vergelijking.{md,json}
```

Modellen: `vorm`, `rating`, `rating-platt`, `rating+markt`, `rating+avg`, `markt-krimp` (zie `modellen.py`).
Code: `events.py` (parser en lader, cutoff), `rating.py` (BT-fit, hold-omzetting, afstemmen) en `kalibratie.py`
(Platt, combinatie, kalibratiehelling).
