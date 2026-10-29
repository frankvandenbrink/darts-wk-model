# Correct score (exacte setstand)

Vraag van Frank: kunnen we de exacte setstand van een WK-wedstrijd goed voorspellen, en loont wedden op
'Correct Score' bij TOTO?

## Methode

- Marktkans (marge eraf) → legverschil → holdkansen → exacte setstand-DP met PDC-regels (sets tot 3 legs,
  beslissende set 2 legs verschil, sudden death bij 5-5). Code: `src/dartswk/correctscore.py`.
- Dagvorm: het legverschil per wedstrijd is normaal verdeeld rond d0 met spreiding σ; d0 zo gekozen dat de
  winkans gelijk blijft aan de markt.
- Vooraf vastgelegd in het register: E029 (holdkans), E030 (σ), E031 (strategie 'meest waarschijnlijke stand').

## Resultaten (walk-forward)

| | WK 2025 | WK 2026 |
|---|---|---|
| E029 hold (gekozen 0,50) | −0,0006 ± 0,0005 | −0,0013 ± 0,0004 |
| E030 σ (gekozen 0,3) | −0,0099 ± 0,0174 | −0,0326 ± 0,0151 |
| E031 trefkans (verwacht) | 21,3% (26,0%) | 27,8% (27,8%) |
| E031 ROI eerlijke odds | −12,4% | −2,1% |
| E031 ROI bij 20% marge | −27,0% | −18,4% |

Samen met WK 2024 (314 wedstrijden): trefkans 29,6%, ROI +10% bij eerlijke odds, −4% bij 15% marge, −12% bij
25% marge. De winst komt helemaal uit 2024.

Kalibratie (σ 0, alle jaren): in 'first to 3' eindigt het 44 keer in 3-2 of 2-3, het model verwachtte 69,5.
Whitewashes (3-0/0-3): 86 echt tegen 70,6 verwacht. 'First to 4' klopt goed. Dat is het dagvorm-effect.

## Finetunen (E032–E038)

Alle vooraf vastgelegd in `experimenten/register.json`, gekozen op train, getoetst tegen de standaard (hold 0,60,
σ 0,3). Testsetstanden waren al bekend uit E031 (vlag `test_vooraf_bekend`).

| | WK 2025 | WK 2026 | Oordeel |
|---|---|---|---|
| E032 σ per format (ft3 0,4 / ft≥4 0,2–0,3) | −0,0014 ± 0,0067 | −0,0008 ± 0,0081 | ruis |
| E033 σ per wedstrijd (niveau, vormschommeling)* | +0,0016 ± 0,0115 | −0,0030 ± 0,0095 | ruis |
| E034 holdkans per niveau | +0,0001 ± 0,0002 | +0,0002 ± 0,0001 | niets |
| E035 momentum tussen sets (κ 0 gekozen) | 0 | 0 | niets |
| E036 tie-break 5-5: bull vs wissel | 0,0000 | 0,0000 | niets |

\* E033 na de eerste run gerepareerd (σ per wedstrijd afgekapt op 0,6, bisectiegrenzen); eerste run haalde het
criterium ook niet. Staat als `na_test_aangepast` in het register.

E037 (selectieregel, aangenomen boekmaker, WK 2025+2026, 220 bets): 'hoogste kans' trefkans 29,1%, ROI +0,6% /
−3,6% / −7,5% bij 15/20/25% marge als de boekmaker zonder dagvorm prijst; −10% / −14% / −17% als hij dagvorm
inprijst. 'Hoogste EV' raakt 22–25% en doet het meestal slechter. Intervallen ±30%.

E038 (diagnose): beslissende sets WK 2024–2026: σ 0 verwacht 93, σ 0,3 78, σ 0 + κ 0,3 68, echt 63. Met de
achteraf-averages (WK 2022–2026, n 502) geen systematische afwijking: first to 3 iets minder, first to 4 meer.
Geen regelfout; dagvorm plus toeval.

Niet te toetsen: wie eerst gooit (geen data, bull pas vlak voor de wedstrijd bekend), een marktgeïmpliceerde
setstandverdeling (geen historische CS-odds), hold/break per speler voor 2026 (Dartsorakel-events 2026 achter de
betaalmuur).

Nieuwe standaard: ongewijzigd (hold 0,60, σ 0,3, κ 0, tie-break 'wissel'); keuze per wedstrijd = hoogste kans.
`dartswk cs-odds` heeft nu ook `--kappa` en `--tiebreak`.

## Beperkingen

- Geen historische correct-score-odds; de ROI rekent met eerlijke odds min een aangenomen marge.
  Correct-score-marges liggen bij bookmakers duidelijk hoger dan bij winnaar-markten.
- TOTO-odds mogen we niet scrapen; handmatig noteren is de enige weg.

## Advies

- Geen bewezen voorsprong. Correct score is voor de lol, met kleine inzet (€1–2, hooguit €10 per week binnen
  het weekbudget van €50) en alleen na Franks akkoord per bet.
- Alleen spelen als de TOTO-odd ≥ eerlijke odd (σ 0,3) + 10%: `dartswk cs-odds ODD1 ODD2 --sets 3 --sigma 0.3`.
  In first to 3 vooral whitewashes bekijken; geen 3-2.
- Eerste WK-week: TOTO-odds handmatig loggen (papieren test) om de echte marge te meten.
