# Walk-forward model `rating+markt` (2024+2025+2026)

Per stap: afstemmen op alle jaren vóór t, ongewijzigd toetsen op t.

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test (train 2024) | 2025 | 94 | 0.6444 | 0.6343 | 0.6371 | 0.2231 | 0.2234 | 0.62 | 0.68 | 1.00 | 64 | 42 | +14.7% | [-22.1%, +54.4%] |
| test (train 2024+2025) | 2026 | 126 | 0.5610 | 0.5490 | 0.5498 | 0.1902 | 0.1843 | 1.04 | 0.95 | 1.20 | 49 | 48 | +35.8% | [-39.1%, +55.3%] |
| totaal test | 2025+2026 | 220 | 0.5966 | 0.5854 | 0.5871 | 0.2043 | 0.2010 | 0.83 | 0.83 | per stap | 113 | 90 | +23.8% | [-9.4%, +48.6%] |

| Stap | Parameters | Drempelkeuze |
|---|---|---|
| test 2025 | basis=(halfwaarde=100000, lam=0.1, onbekend=0.0, k=0.8, g=0.0), a=0.6227, a_se=0.3487, b=0.3974, b_se=0.3301, lr_b_train=1.771 | drempel 1.00 heeft de hoogste ROI op train (+22.1%) |
| test 2026 | basis=(halfwaarde=100000, lam=2.0, onbekend=-0.3, k=0.6, g=0.0), a=0.5752, a_se=0.2557, b=0.3633, b_se=0.3283, lr_b_train=1.242 | drempel 1.20 heeft de hoogste ROI op train (+46.2%) |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test (train 2024) | 2025 | 94 | 0.6444 | 0.6343 | 0.6371 | 0.2231 | 0.2234 | 0.62 | 0.68 | 1.05 | 42 | 31 | +31.6% | [-14.1%, +66.5%] |
| test (train 2024+2025) | 2026 | 126 | 0.5610 | 0.5490 | 0.5498 | 0.1902 | 0.1843 | 1.04 | 0.95 | 1.05 | 87 | 72 | -0.9% | [-59.5%, +17.4%] |
| totaal test | 2025+2026 | 220 | 0.5966 | 0.5854 | 0.5871 | 0.2043 | 0.2010 | 0.83 | 0.83 | 1.05 | 129 | 103 | +9.6% | [-19.2%, +27.3%] |
