# Protocol voor experimenten

Dit protocol geldt voor alles wat via `dartswk experimenten` draait. Het register staat in
[experimenten/register.json](../experimenten/register.json), de log in
[experimenten/runlog.jsonl](../experimenten/runlog.jsonl) en de uitkomsten in
[resultaten/experimenten.md](../resultaten/experimenten.md).

## Regels

1. **Eerst registreren, dan draaien.** Elk experiment krijgt een id (E001, E002, …), een datum, het model, de
   features, het hyperparametergrid, een hypothese en een criterium voor succes. Die worden vóór de eerste run
   geschreven. Zonder hypothese en criterium weigert de code de testjaren te evalueren.
2. **Afstemmen alleen op train.** De afstemfunctie krijgt alleen de trainwedstrijden. Hyperparameters, drempel,
   kalibratie en regularisatie (lambda via kruisvalidatie binnen train) komen allemaal uit train.
3. **Walk-forward is het hoofdresultaat:** test 2025 met train 2024, test 2026 met train 2024+2025. Een assert
   controleert dat elk trainjaar vóór het testjaar ligt.
4. **Vaste richtingen** (2026 → 2025, 2025 → 2026, 2025 → 2024, 2025+2026 → 2024) draaien mee ter vergelijking.
   Ze zijn niet walk-forward: daar worden hyperparameters op een later WK afgestemd.
5. **Geen lookahead.** Vormdata eindigt de dag vóór de WK-start (assert in `parse.load_orakel`). Event-data
   (rating, Elo, Glicko) gebruikt alleen events met datum strikt vóór de WK-start (asserts in `events`,
   `rating.fit_bt` en `experimenten.elo_ratings`). In-wedstrijd-averages worden nooit gebruikt.
6. **Alles wordt gelogd**, ook mislukkingen en experimenten die niet gedraaid konden worden (bijvoorbeeld GBM
   zonder sklearn). De log bewaart een vingerafdruk van hypothese, criterium, model, features en grid. Sinds ronde 2 (zie
   [docs/review-ronde2.md](review-ronde2.md)) ook een hash `context` van splits, config-grids, drempels, hold en
   bootstrap, de git-commit en of `register.json` tijdens de run niet-gecommitte wijzigingen had. Een gewijzigde
   context na de eerste run geeft ook een protocolwaarschuwing; `na_test_aangepast: true` vraagt een toelichting.
7. **Aanpassen na het zien van testcijfers mag, maar moet gemeld worden** in `na_test_aangepast`
   (`waarde: true` en een toelichting). Verandert de vingerafdruk na een eerdere run zonder die melding, dan
   krijgt het resultaat een protocolwaarschuwing.
8. **Controles draaien altijd mee:** `markt` (proportioneel, geen bets), `markt-vlak` (logit·a, a op train),
   `blind-underdog`, `blind-favoriet` (inzet 1) en `munt` (p = 0.5, log-loss ln 2 = 0.6931).

## Wat er per experiment en testjaar wordt gerapporteerd

- n, log-loss, Brier;
- verschil in log-loss met de markt (proportioneel) per wedstrijd, met standaardfout;
- oordeel: *binnen de ruis* als |verschil| ≤ 2 se, anders beter of slechter dan de markt;
- kalibratiehelling: c in logit P(winst) = c·logit(p) (1 = goed, < 1 = te stellig);
- kalibratiebins: 5 bins op de kans van de favoriet volgens het model (0.5–1.0), met gemiddelde kans,
  werkelijke frequentie en aantal;
- aantal bets, ROI bij inzet 1 met 90%-interval (bootstrap die per (jaar, ronde) resamplet, met het aantal
  clusters erbij: een WK heeft hoogstens 7 rondes, dus het interval is grof), en het
  cumulatieve winstverloop per bet (`verloop`).

## Waarom deze keuzes

- **Log-loss tegen de markt als hoofdmaat.** ROI is met ~100 bets per WK vooral ruis (standaardfout ±20–30%).
  Log-loss gebruikt elke wedstrijd en zegt direct of het model informatie heeft die de markt niet heeft.
- **Proportionele margecorrectie** is in deze data de scherpste benchmark (lager dan Shin en power).
- **Criterium "> 1 se in beide testjaren"** is bewust soepel: het is een filter om te zien wat het waard is om
  verder te onderzoeken, geen bewijs. Bewijs vraagt meer toernooien.
- **Bootstrap per (jaar, ronde):** uitslagen binnen een ronde (en een "upsetjaar") zijn gecorreleerd; resamplen
  per bet geeft te smalle intervallen.
- **Geen intercept** in de logistische modellen: speler1/speler2 is een willekeurige volgorde.
- **Ronde alleen als interactie** met de marktlogit: een hoofdeffect van de ronde is symmetrisch en kan niets
  over speler1 zeggen.

## Bekende zwakke plekken

- ~94–126 wedstrijden per WK. Verschillen in log-loss van 0.01 zijn binnen de ruis.
- 65% van de Dartsorakel-resultaatpagina's is een paywall; recente events ontbreken (zie
  [model-rating.md](model-rating.md)).
- Voor de eerder gebouwde modellen (vorm, rating, …) waren de testcijfers al bekend vóór dit register bestond.
  Die staan gemarkeerd met `test_vooraf_bekend: true`.
- Odds zijn gemiddelde slotodds; niet de odds die je zelf krijgt.
