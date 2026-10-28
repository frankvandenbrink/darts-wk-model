# Terugtest model `rating`: train 2026, test 2025

Parameters (afgestemd op train): halfwaarde=365, lam=0.5, onbekend=0.0, k=0.6, g=0.0

Drempelkeuze: drempel 1.30 heeft de hoogste ROI op train (+19.6%).

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2026 | 126 | 0.6000 | 0.5490 | 0.5498 | 0.2074 | 0.1843 | 1.04 | 0.95 | 1.30 | 64 | 61 | +19.6% | [-46.5%, +38.3%] |
| test | 2025 | 94 | 0.6494 | 0.6343 | 0.6371 | 0.2280 | 0.2234 | 0.77 | 0.68 | 1.30 | 39 | 39 | +32.7% | [-20.0%, +75.2%] |

## Drempeltabel train (basis voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 116 | -4.8% |
| 1.05 | 101 | +5.5% |
| 1.10 | 89 | +5.7% |
| 1.15 | 86 | +5.4% |
| 1.20 | 80 | +7.8% |
| 1.30 | 64 | +19.6% |

## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 82 | +16.4% |
| 1.05 | 68 | +23.2% |
| 1.10 | 60 | +15.5% |
| 1.15 | 53 | +15.0% |
| 1.20 | 45 | +25.3% |
| 1.30 | 39 | +32.7% |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2026 | 126 | 0.6000 | 0.5490 | 0.5498 | 0.2074 | 0.1843 | 1.04 | 0.95 | 1.05 | 101 | 83 | +5.5% | [-49.6%, +21.1%] |
| test | 2025 | 94 | 0.6494 | 0.6343 | 0.6371 | 0.2280 | 0.2234 | 0.77 | 0.68 | 1.05 | 68 | 60 | +23.2% | [-12.8%, +53.8%] |
