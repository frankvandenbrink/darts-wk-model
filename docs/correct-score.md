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
