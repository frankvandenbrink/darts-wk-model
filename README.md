# dartswk: terugtest van een dartsmodel voor het PDC WK

> **Hobbyproject. Wedden kan verliesgevend zijn. 18+. Geen advies.**

## Doel

Nagaan of een eenvoudig vormmodel (recente averages en checkout% van vóór het toernooi) de wedstrijden op het
PDC WK beter voorspelt dan de bookmakers, en of wedden op de verschillen met de markt winst had opgeleverd.
De terugtest gebruikt de WK's 2024, 2025 en 2026 (jaar van de finale).

Dit pakket herstructureert het oude script en verwerkt de fixes uit sectie 2 van de review in
[docs/review-claude.md](docs/review-claude.md).

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

## Data en licenties

| Bron | Wat | In de repo? |
|---|---|---|
| Wikipedia (CC BY-SA 4.0) | uitslagen, rondes, in-wedstrijd-averages | **Ja**: `data/wedstrijden_WK<jaar>.csv`, bronvermelding in [data/BRONNEN.md](data/BRONNEN.md) |
| Oddsportal | slotodds | **Nee**. Alleen ophalen via `dartswk fetch` |
| Dartsorakel | geaggregeerde averages en checkout% | **Nee**. Alleen ophalen via `dartswk fetch` |

Ruwe bestanden komen in `data/cache/` (staat in `.gitignore`). Wie Oddsportal of Dartsorakel ophaalt, is zelf
verantwoordelijk voor het naleven van hun gebruiksvoorwaarden. In `resultaten/` staan alleen samengevatte cijfers,
geen odds per wedstrijd.

## Installatie

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'          # met tests
.venv/bin/pip install -e '.[odds]'         # alleen nodig om Oddsportal op te halen (playwright)
.venv/bin/playwright install chromium      # of: export DARTSWK_CHROME=/usr/bin/google-chrome
```

## Commando's

```bash
dartswk fetch --jaren 2024 2025 2026                     # ruwe data naar data/cache/ (slaat bestaande over)
dartswk dataset                                          # data/wedstrijden_WK<jaar>.csv (alleen Wikipedia)
dartswk terugtest --model vorm --train 2026 --test 2025  # afstemmen op 2026, toetsen op 2025
dartswk terugtest --model vorm --train 2025 --test 2026
dartswk terugtest --model vorm --walk-forward --jaren 2024 2025 2026
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

## Beperkingen

- Drie toernooien, ~300 wedstrijden; de effectieve steekproef is eerder "drie toernooien". Om 5% ROI aan te tonen
  zijn duizenden bets nodig (review, sectie 3).
- De stopregel kijkt alleen naar het teken van de ROI op train. Met een strengere regel (90%-interval op train
  boven 0) was alleen in de stap 2024 → 2025 gewed (train [+3.0%, +77.1%]); bij 2024+2025 → 2026
  ([−9.1%, +85.9%]) en 2025 → 2026 ([−10.6%, +73.8%]) niet.
- Odds zijn gemiddelde slotodds van Oddsportal, niet de odds die je bij je eigen bookmaker krijgt. De juistheid
  ervan is niet tegen een tweede bron gecontroleerd.
- De vorm is niet gecorrigeerd voor tegenstander of niveau en krimpt niet bij weinig data (review 2.3).
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
