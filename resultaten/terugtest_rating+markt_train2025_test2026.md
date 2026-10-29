# Terugtest model `rating+markt`: train 2025, test 2026

Parameters (afgestemd op train): basis=(halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0), a=0.3972, a_se=0.3257, b=0.5167, b_se=0.4944, lr_b_train=1.129

Drempelkeuze: drempel 1.15 heeft de hoogste ROI op train (+34.6%).

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2025 | 94 | 0.6157 | 0.6343 | 0.6371 | 0.2142 | 0.2234 | 1.00 | 0.68 | 1.15 | 47 | 46 | +34.6% | [-31.4%, +80.9%] |
| test | 2026 | 126 | 0.5806 | 0.5490 | 0.5498 | 0.1981 | 0.1843 | 1.03 | 0.95 | 1.15 | 71 | 64 | +12.9% | [-55.3%, +31.8%] |

## Drempeltabel train (basis voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 77 | +31.4% |
| 1.05 | 68 | +30.8% |
| 1.10 | 59 | +30.7% |
| 1.15 | 47 | +34.6% |
| 1.20 | 41 | +32.3% |
| 1.30 | 31 | +23.8% |

## Drempeltabel test (alleen ter informatie, niet gebruikt voor de keuze)

| Drempel | Bets | ROI |
|---|---|---|
| 1.00 | 109 | -6.8% |
| 1.05 | 94 | -4.4% |
| 1.10 | 82 | +5.6% |
| 1.15 | 71 | +12.9% |
| 1.20 | 62 | +13.6% |
| 1.30 | 48 | +39.2% |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2025 | 94 | 0.6157 | 0.6343 | 0.6371 | 0.2142 | 0.2234 | 1.00 | 0.68 | 1.05 | 68 | 64 | +30.8% | [-35.9%, +70.2%] |
| test | 2026 | 126 | 0.5806 | 0.5490 | 0.5498 | 0.1981 | 0.1843 | 1.03 | 0.95 | 1.05 | 94 | 78 | -4.4% | [-53.0%, +8.1%] |
