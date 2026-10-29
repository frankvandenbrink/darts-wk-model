# dartswk: terugtest van een dartsmodel voor het PDC WK

> **Hobbyproject. Wedden kan verliesgevend zijn. 18+. Geen advies.**

## Doel

Nagaan of een eenvoudig vormmodel (recente averages en checkout% van vóór het toernooi) de wedstrijden op het
PDC WK beter voorspelt dan de bookmakers, en of wedden op de verschillen met de markt winst had opgeleverd.
De terugtest gebruikt de WK's 2024, 2025 en 2026 (jaar van de finale).

Dit pakket herstructureert het oude script en verwerkt de fixes uit sectie 2 van de review in
[docs/review-claude.md](docs/review-claude.md). Daarnaast is er een **ratingmodel op wedstrijdniveau** (review 4.1 en
4.3): Bradley-Terry op legs met tegenstandercorrectie, tijdsweging en krimp, plus kalibratie en combinatie met de
markt. Zie [docs/model-rating.md](docs/model-rating.md).

## Methode

- **Vorm** (Dartsorakel, alle wedstrijden tot en met de dag vóór het WK; een assert bewaakt dat de periode vóór de
  WK-start eindigt): `vorm = w·waarde(3 mnd) + (1−w)·waarde(L mnd)`, L ∈ {6, 12}, voor average en checkout%.
- **Kans per leg** voor de speler die begint: `logistic(logit(0.60) + k·(avgA−avgB) + kc·(coA−coB))`.
- **Wedstrijdkans exact** uit het WK-format (`setmodel.py`): sets first to 3 legs, beslissende set met twee legs
  verschil en sudden death bij 5-5, wisselende beginner per leg en per set, gemiddeld over wie de bull wint.
  Het aantal benodigde sets volgt uit de ronde (R1/R2 3, R3/R4 4, QF 5, SF 6, F 7), niet uit de uitslag.
- **Markt**: slotodds van Oddsportal (gemiddelde over bookmakers), marge eruit met proportionele normalisatie
  (standaard benchmark) en daarnaast Shin.
- **Afstemmen**: grid search over w, L, k, kc op log-loss (train). Daarna de drempel `eigen kans × odd > drempel`
  met de hoogste ROI op train (min. 10 bets). **Stopregel:** is die ROI ≤ 0, dan wordt er niet gewed.
- **Toetsen**: ongewijzigd op het testjaar. Brier, log-loss, ROI bij vaste inzet 1, en een 90%-interval van de ROI
  met een bootstrap die per ronde (jaar, ronde) resamplet in plaats van per bet.
- **Walk-forward**: voor elk jaar t afstemmen op alle jaren vóór t en toetsen op t.
- **Naamkoppeling**: Oddsportal-namen moeten op achternaam én initialen passen ("Smith M." ≠ Ross Smith);
  elke wedstrijd koppelt aan precies één Oddsportal-rij en elke speler aan precies één Dartsorakel-speler
  (anders een fout). Dubbele Oddsportal-rijen worden ontdubbeld. Niet-exacte koppelingen (alias, omgekeerde
  naamvolgorde, umlaut, difflib) worden gemeld.
- In-wedstrijd-averages van Wikipedia heten `avg*_achteraf` en worden nooit als feature gebruikt.

### Ratingmodel (`--model rating`, details in [docs/model-rating.md](docs/model-rating.md))

- **Data:** de uitslagen per wedstrijd (legstand) van Dartsorakel-events (Pro Tour, European Tour, majors, WK)
  van 2022–2025, alleen events met een datum strikt vóór de WK-start (assert). Bij WK en World Grand Prix staat de
  score in sets; daar telt alleen de uitslag.
- **Rating:** P(a wint een leg van b) = logistic(r_a − r_b). Gewogen maximum likelihood met gewicht
  0.5^(leeftijd/halfwaarde) en een ridge-prior λ die naar het veldgemiddelde krimpt. WK-spelers zonder data
  krijgen de rating `onbekend`.
- **Wedstrijdkans:** k·(r_a − r_b) wordt omgezet in hold-kansen rond 0.60 (de gemiddelde legkans blijft gelijk),
  daarna de exacte set/match-DP.
- **Afstemmen:** halfwaarde, λ, onbekend en k via grid search op log-loss (train). Daarna dezelfde drempel en
  stopregel als hierboven.
- **Varianten:**
  - `rating-platt`: logit p = c·logit(p_rating).
  - `rating+markt`: logit p = a·logit(markt) + b·logit(p_rating), met a en b op train gefit met logistische
    regressie.
  - `rating+avg`: met tegenstander-onafhankelijke averages erbij (ter info).
  - `markt-krimp`: logit p = a·logit(markt), een controle zonder rating.

## Data en licenties

| Bron | Wat | In de repo? |
|---|---|---|
| Wikipedia (CC BY-SA 4.0) | uitslagen, rondes, in-wedstrijd-averages | **Ja**: `data/wedstrijden_WK<jaar>.csv`, bronvermelding in [data/BRONNEN.md](data/BRONNEN.md) |
| Oddsportal | slotodds | **Nee**. Alleen de bestaande lokale cache; ophalen is verwijderd (zie hieronder) |
| Dartsorakel | geaggregeerde averages en checkout% | **Nee**. Alleen ophalen via `dartswk fetch` |
| Dartsorakel | evenementenlijst en resultaatpagina's (legstanden) | **Nee**. Alleen ophalen via `dartswk fetch-events` (≥ 1,5 s pauze, cache) |

Ruwe bestanden komen in `data/cache/` (staat in `.gitignore`). Wie Oddsportal of Dartsorakel ophaalt, is zelf
verantwoordelijk voor het naleven van hun gebruiksvoorwaarden. In `resultaten/` staan alleen samengevatte cijfers,
geen odds per wedstrijd.

**Oddsportal:** de gebruiksvoorwaarden van Oddsportal verbieden scrapen. De ophaalcode is daarom verwijderd en er
wordt vanaf nu geen nieuwe Oddsportal-data opgehaald. De terugtest gebruikt alleen de odds die al lokaal in
`data/cache/` stonden. Zie [data/BRONNEN.md](data/BRONNEN.md).

## Installatie

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'          # met tests
```

## Commando's

```bash
dartswk fetch --jaren 2024 2025 2026                     # Wikipedia + Dartsorakel naar data/cache/ (geen Oddsportal)
dartswk dataset                                          # data/wedstrijden_WK<jaar>.csv (alleen Wikipedia)
dartswk terugtest --model vorm --train 2026 --test 2025  # afstemmen op 2026, toetsen op 2025
dartswk terugtest --model vorm --train 2025 --test 2026
dartswk terugtest --model vorm --walk-forward --jaren 2024 2025 2026
dartswk fetch-events                                     # Dartsorakel-events 2022-2025 (beleefd, gecachet)
dartswk terugtest --model rating --walk-forward --jaren 2024 2025 2026
dartswk vergelijk                                        # alle modellen, alle splits -> resultaten/vergelijking.*
pytest                                                   # draait zonder netwerk en zonder data/cache
```

Uitvoer: `resultaten/<naam>.json` en `resultaten/<naam>.md`. Een jaar toevoegen = één regel in
`JAREN` in `src/dartswk/config.py`.

## Resultaten

Alle cijfers komen uit `resultaten/` (gedraaid met de cache van 2024–2026). n = wedstrijden met odds:
2024 94 van 95 (Smith–Dobey heeft geen odds op Oddsportal), 2025 94 (+1 walkover), 2026 126 (+1 walkover).
Log-loss: lager is beter.

### Train/test (beide richtingen)

| Train → test | Parameters | Log-loss model (test) | Markt prop. | Markt Shin | Drempel (train) | Bets test | ROI test | 90%-int. |
|---|---|---|---|---|---|---|---|---|
| 2026 → 2025 | w=0, L=12, k=0.04, kc=0 | 0.6179 | 0.6343 | 0.6371 | niet wedden (beste train-ROI −6.8%) | 0 | – | – |
| 2025 → 2026 | w=0.25, L=12, k=0.04, kc=0 | 0.5680 | 0.5490 | 0.5498 | 1.10 (train +50.9%, 50 bets) | 68 (67 underdog) | −26.9% | [−56.2%, +7.2%] |

Op de traindata zelf: 2026 model 0.5669 tegen markt 0.5490; 2025 model 0.6171 tegen markt 0.6343.

### Walk-forward (2024 → 2025, 2024+2025 → 2026)

| Testjaar | Train | Parameters | Log-loss model | Markt prop. | Markt Shin | Drempel | Bets | ROI | 90%-int. |
|---|---|---|---|---|---|---|---|---|---|
| 2025 | 2024 | w=0, L=6, k=0.04, kc=0.02 | 0.6461 | 0.6343 | 0.6371 | 1.15 | 34 (28 underdog) | +16.9% | [−24.9%, +43.6%] |
| 2026 | 2024+2025 | w=0, L=6, k=0.04, kc=0 | 0.5725 | 0.5490 | 0.5498 | 1.30 | 37 (37 underdog) | −43.6% | [−100.0%, +11.7%] |
| **Totaal** | | | **0.6039** | **0.5854** | 0.5871 | per stap | 71 | **−14.7%** (−10.41 units) | [−48.0%, +22.0%] |

### Ratingmodel tegen vorm en markt

Volledige tabellen (Brier, parameters, drempelkeuze, alle varianten): [resultaten/vergelijking.md](resultaten/vergelijking.md).
Log-loss op het testjaar; ROI met de stopregel en een 90%-interval (bootstrap per ronde).

| Train → test | n | Rating | Rating+markt | Vorm | Markt prop. | Markt Shin | Helling rating | Bets rating, ROI | Bets rating+markt, ROI |
|---|---|---|---|---|---|---|---|---|---|
| 2026 → 2025 | 94 | 0.6494 | 0.6324 | 0.6179 | 0.6343 | 0.6371 | 0.77 | 39, +32.7% [−20.0, +75.2] | 7, −100.0% |
| 2025 → 2026 | 126 | 0.6369 | 0.5806 | 0.5680 | 0.5490 | 0.5498 | 0.71 | 105, −6.7% [−55.0, +7.2] | 71, +12.9% [−55.3, +31.8] |
| 2025 → 2024 | 94 | 0.6048 | 0.5798 | 0.5985 | 0.5698 | 0.5722 | 1.07 | 73, +7.7% [−18.3, +47.8] | 48, +12.8% [−22.5, +71.4] |
| 2025+2026 → 2024 | 94 | 0.5997 | 0.5703 | 0.5973 | 0.5698 | 0.5722 | 1.37 | 45, +14.4% [−29.2, +118.5] | 19, +42.1% [−30.0, +220.0] |
| WF 2024 → 2025 | 94 | 0.6888 | 0.6444 | 0.6461 | 0.6343 | 0.6371 | 0.45 | 47, +17.5% [−24.8, +63.0] | 64, +14.7% [−22.1, +54.4] |
| WF 2024+2025 → 2026 | 126 | 0.6236 | 0.5610 | 0.5725 | 0.5490 | 0.5498 | 0.73 | 103, −4.1% [−61.6, +13.8] | 49, +35.8% [−39.1, +55.3] |
| **WF totaal** | 220 | **0.6515** | **0.5966** | 0.6039 | **0.5854** | 0.5871 | 0.59 | 150, +2.7% [−26.6, +21.3] | 113, +23.8% [−9.4, +48.6] |

- Brier, walk-forward totaal: rating 0.2213, rating+markt 0.2043, vorm 0.2062, markt 0.2010.
- Helling: c in logit P(winst) = c·logit(p) op test; kleiner dan 1 betekent te stellig.
- `rating+markt` gefit op train:
  - b (rating) ligt tussen 0.12 en 0.52, met standaardfouten van 0.28–0.49;
  - de LR-statistiek voor b = 0 is hoogstens 1.77 (kritieke waarde 3.84);
  - a (markt) ligt tussen 0.40 en 0.86.
- Controle `markt-krimp` (alleen de markt vlakker maken, zonder rating): walk-forward totaal log-loss 0.5854 en
  56 bets met **+23.7%** ROI.
- Blind op de underdog: 2024 −4.5%, 2025 +25.0%, 2026 +1.2%.

### Ter informatie: vaste drempel 1.05, zonder stopregel

Niet het hoofdresultaat; opgenomen omdat 1.05 vooraf als regel genoemd was.

| Variant | Bets | ROI | 90%-int. |
|---|---|---|---|
| 2026 → 2025 | 56 | +51.7% | [−7.0%, +77.5%] |
| 2025 → 2026 | 81 | −20.3% | [−45.1%, +9.3%] |
| Walk-forward totaal (2025+2026) | 132 | −4.1% | [−22.7%, +14.9%] |

## Dashboard

De tussenstanden staan op <https://frankvandenbrink.github.io/darts-wk-model/>. De pagina is statisch en wordt
gebouwd door `scripts/bouw_dashboard.py` (alleen standaardbibliotheek) uit `resultaten/*.json`. De workflow
`.github/workflows/pages.yml` bouwt en publiceert hem bij elke push naar `main` die `resultaten/`, het script,
deze README of de workflow wijzigt, en handmatig via *Run workflow*. Lokaal: `python scripts/bouw_dashboard.py`,
daarna `site/index.html` openen. Tijdens het WK 2026/27 komen voorspellingen en uitslagen in
`resultaten/live_2027.json`; het schema staat bovenin het script.

## Conclusie

Het vormmodel voorspelt slechter dan de markt. In de walk-forward verliest het in beide testjaren op log-loss
(totaal 0.6039 tegen 0.5854) en ook in-sample op 2024 (0.5814 tegen 0.5698) en 2026. Alleen in 2025, het
upsetjaar (favorieten wonnen 59 van de 94), scoort het model beter dan de markt, omdat het vlakker is.

Het wedresultaat in de walk-forward is −14.7% over 71 bets, bijna allemaal underdogs. Met de stopregel wordt bij
afstemmen op 2026 niet gewed; de +51.7% op 2025 bij drempel 1.05 is dus geen resultaat van de regel zoals die vooraf
vastligt. Alle betrouwbaarheidsintervallen bevatten 0. **Er is geen aantoonbaar voordeel; wed niet met dit model.**
Proportionele margecorrectie geeft de scherpste marktbenchmark; met Shin verandert de conclusie niet.

**Ratingmodel:** geen verbetering. Het voorspelt in alle splits slechter dan de markt én dan het vormmodel
(walk-forward 0.6515 tegen 0.6039 en 0.5854), en het is out-of-sample te stellig.

- Gecombineerd met de markt komt het dichtbij (0.5966), maar niet onder de markt.
- Het gewicht b van de rating is nergens significant.
- De +23.8% ROI van `rating+markt` is geen aanwijzing voor voordeel. De controle zonder rating (`markt-krimp`)
  haalt hetzelfde (+23.7%). De winst komt dus van een kanteling naar underdogs (90 van de 113 bets) in een
  steekproef met het upsetjaar 2025, niet van de rating.
- Er is geen lek gevonden. Het interval bevat 0.

De waarschijnlijke hoofdoorzaak is de data: 133 van de 205 resultaatpagina's zijn een abonnementspagina. Vóór
WK2026 is het laatste bruikbare event van maart 2025, en 21 van de 128 WK2026-spelers hebben geen data. Of een
rating met volledige data wél iets toevoegt, is met deze cache niet te zeggen. **Wed ook niet met het ratingmodel.**

## Beperkingen

- Drie toernooien, ~300 wedstrijden; de effectieve steekproef is eerder "drie toernooien". Om 5% ROI aan te tonen
  zijn duizenden bets nodig (review, sectie 3).
- De stopregel kijkt alleen naar het teken van de ROI op train. Met een strengere regel (90%-interval op train
  boven 0) was alleen in de stap 2024 → 2025 gewed (train [+3.0%, +77.1%]); bij 2024+2025 → 2026
  ([−9.1%, +85.9%]) en 2025 → 2026 ([−10.6%, +73.8%]) niet.
- Odds zijn gemiddelde slotodds van Oddsportal, niet de odds die je bij je eigen bookmaker krijgt. De juistheid
  ervan is niet tegen een tweede bron gecontroleerd.
- De vorm is niet gecorrigeerd voor tegenstander of niveau en krimpt niet bij weinig data (review 2.3). Het
  ratingmodel doet dat wel, maar heeft te weinig recente data.
- Rating, dekking van de data: 65% van de Dartsorakel-resultaatpagina's is een paywall. Die wordt niet omzeild.
  Bruikbare events: 2022 43/50, 2023 17/50, 2024 11/50, 2025 1/55. De dekking is dus scheef in de tijd, en
  tijdsweging helpt daardoor niet: de grid kiest meestal "geen weging".
- Het grid van het ratingmodel is twee keer verbreed na het bekijken van de eerste resultaten (op train én test),
  omdat het optimum op de rand lag. Zie [docs/model-rating.md](docs/model-rating.md).
- Bij train 2026 → test 2025 bevat het 12-maandenvenster van 2026 het WK 2025 zelf; die richting is daarom de
  minst eerlijke. Walk-forward heeft dat probleem niet.
- Onbekend is of Dartsorakel `dateTo` op wedstrijd- of toernooidatum filtert.
- De sudden-death-leg laat de wissel van beginner doorlopen (effect ≤ 0.00017 op de wedstrijdkans).
- Het Oddsportal-slug voor 2026 in `config.py` is niet geverifieerd (de cache is opgehaald met het slug van het
  toen lopende seizoen).

Zie [docs/review-claude.md](docs/review-claude.md) voor de volledige review en voorstellen voor een beter model.

## Licentie

Code: MIT, zie [LICENSE](LICENSE). Data in `data/wedstrijden_WK*.csv`: CC BY-SA 4.0 (Wikipedia).

> **Hobbyproject. Wedden kan verliesgevend zijn. 18+. Geen advies.**
