# Terugtest model `vorm`: train 2026, test 2025

Parameters (afgestemd op log-loss, train): w=0.0, L=12, k=0.04, kc=0.0

Drempelkeuze: beste ROI op train is -6.8% (drempel 1.00) <= 0: niet wedden.

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2026 | 126 | 0.5669 | 0.5490 | 0.5498 | 0.1898 | 0.1843 | niet wedden | 0 | 0 | – | – |
| test | 2025 | 94 | 0.6179 | 0.6343 | 0.6371 | 0.2159 | 0.2234 | niet wedden | 0 | 0 | – | – |

## Drempeltabel train (basis voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 100 | -6.8% |
| 1.05 | 78 | -11.6% |
| 1.10 | 65 | -13.2% |
| 1.15 | 52 | -23.8% |
| 1.20 | 48 | -26.8% |
| 1.30 | 34 | -22.8% |

## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 75 | +34.8% |
| 1.05 | 56 | +51.7% |
| 1.10 | 51 | +57.4% |
| 1.15 | 41 | +41.5% |
| 1.20 | 36 | +47.7% |
| 1.30 | 24 | +18.9% |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2026 | 126 | 0.5669 | 0.5490 | 0.5498 | 0.1898 | 0.1843 | 1.05 | 78 | 74 | -11.6% | [-38.8%, +11.3%] |
| test | 2025 | 94 | 0.6179 | 0.6343 | 0.6371 | 0.2159 | 0.2234 | 1.05 | 56 | 53 | +51.7% | [-7.0%, +77.5%] |
