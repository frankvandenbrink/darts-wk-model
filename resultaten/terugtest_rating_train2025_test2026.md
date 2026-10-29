# Terugtest model `rating`: train 2025, test 2026

Parameters (afgestemd op train): halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0

Drempelkeuze: drempel 1.05 heeft de hoogste ROI op train (+33.6%).

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2025 | 94 | 0.6238 | 0.6343 | 0.6371 | 0.2174 | 0.2234 | 1.01 | 0.68 | 1.05 | 75 | 67 | +33.6% | [-21.3%, +69.4%] |
| test | 2026 | 126 | 0.6369 | 0.5490 | 0.5498 | 0.2205 | 0.1843 | 0.71 | 0.95 | 1.05 | 105 | 79 | -6.7% | [-55.0%, +7.2%] |

## Drempeltabel train (basis voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 82 | +28.1% |
| 1.05 | 75 | +33.6% |
| 1.10 | 63 | +32.2% |
| 1.15 | 58 | +25.8% |
| 1.20 | 49 | +23.0% |
| 1.30 | 40 | +21.1% |

## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 113 | -5.3% |
| 1.05 | 105 | -6.7% |
| 1.10 | 95 | -2.5% |
| 1.15 | 87 | -0.7% |
| 1.20 | 78 | +6.7% |
| 1.30 | 66 | +21.5% |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2025 | 94 | 0.6238 | 0.6343 | 0.6371 | 0.2174 | 0.2234 | 1.01 | 0.68 | 1.05 | 75 | 67 | +33.6% | [-21.3%, +69.4%] |
| test | 2026 | 126 | 0.6369 | 0.5490 | 0.5498 | 0.2205 | 0.1843 | 0.71 | 0.95 | 1.05 | 105 | 79 | -6.7% | [-55.0%, +7.2%] |
