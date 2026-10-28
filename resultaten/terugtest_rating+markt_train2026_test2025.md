# Terugtest model `rating+markt`: train 2026, test 2025

Parameters (afgestemd op train): basis=(halfwaarde=365, lam=0.5, onbekend=0.0, k=0.6, g=0.0), a=0.8638, a_se=0.2564, b=0.1543, b_se=0.3281, lr_b_train=0.223

Drempelkeuze: drempel 1.10 heeft de hoogste ROI op train (+40.5%).

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2026 | 126 | 0.5478 | 0.5490 | 0.5498 | 0.1842 | 0.1843 | 1.00 | 0.95 | 1.10 | 21 | 21 | +40.5% | [-100.0%, +126.9%] |
| test | 2025 | 94 | 0.6324 | 0.6343 | 0.6371 | 0.2224 | 0.2234 | 0.70 | 0.68 | 1.10 | 7 | 7 | -100.0% | [-100.0%, -100.0%] |

## Drempeltabel train (basis voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 69 | +17.5% |
| 1.05 | 43 | +30.7% |
| 1.10 | 21 | +40.5% |
| 1.15 | 7 | +207.1% |
| 1.20 | 3 | +466.7% |
| 1.30 | 0 | – |

## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 36 | +23.8% |
| 1.05 | 17 | +54.7% |
| 1.10 | 7 | -100.0% |
| 1.15 | 4 | -100.0% |
| 1.20 | 1 | -100.0% |
| 1.30 | 0 | – |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2026 | 126 | 0.5478 | 0.5490 | 0.5498 | 0.1842 | 0.1843 | 1.00 | 0.95 | 1.05 | 43 | 41 | +30.7% | [-74.3%, +69.1%] |
| test | 2025 | 94 | 0.6324 | 0.6343 | 0.6371 | 0.2224 | 0.2234 | 0.70 | 0.68 | 1.05 | 17 | 17 | +54.7% | [-8.7%, +109.3%] |
