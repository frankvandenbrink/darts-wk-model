# Terugtest model `vorm`: train 2025, test 2026

Parameters (afgestemd op train): w=0.25, L=12, k=0.04, kc=0.0

Drempelkeuze: drempel 1.10 heeft de hoogste ROI op train (+50.9%).

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2025 | 94 | 0.6171 | 0.6343 | 0.6371 | 0.2157 | 0.2234 | 0.93 | 0.68 | 1.10 | 50 | 49 | +50.9% | [-10.6%, +73.8%] |
| test | 2026 | 126 | 0.5680 | 0.5490 | 0.5498 | 0.1905 | 0.1843 | 1.11 | 0.95 | 1.10 | 68 | 67 | -26.9% | [-56.2%, +7.2%] |

## Drempeltabel train (basis voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 75 | +38.0% |
| 1.05 | 62 | +45.0% |
| 1.10 | 50 | +50.9% |
| 1.15 | 43 | +40.1% |
| 1.20 | 35 | +45.9% |
| 1.30 | 23 | +24.0% |

## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 101 | -11.4% |
| 1.05 | 81 | -20.3% |
| 1.10 | 68 | -26.9% |
| 1.15 | 58 | -18.3% |
| 1.20 | 45 | -23.7% |
| 1.30 | 34 | -25.4% |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2025 | 94 | 0.6171 | 0.6343 | 0.6371 | 0.2157 | 0.2234 | 0.93 | 0.68 | 1.05 | 62 | 57 | +45.0% | [-7.1%, +65.9%] |
| test | 2026 | 126 | 0.5680 | 0.5490 | 0.5498 | 0.1905 | 0.1843 | 1.11 | 0.95 | 1.05 | 81 | 77 | -20.3% | [-45.1%, +9.3%] |
