# Walk-forward model `rating` (2024+2025+2026)

Per stap: afstemmen op alle jaren vóór t, ongewijzigd toetsen op t.

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test (train 2024) | 2025 | 94 | 0.6888 | 0.6343 | 0.6371 | 0.2273 | 0.2234 | 0.45 | 0.68 | 1.15 | 47 | 36 | +17.5% | [-24.8%, +63.0%] |
| test (train 2024+2025) | 2026 | 126 | 0.6236 | 0.5490 | 0.5498 | 0.2168 | 0.1843 | 0.73 | 0.95 | 1.05 | 103 | 73 | -4.1% | [-61.6%, +13.8%] |
| totaal test | 2025+2026 | 220 | 0.6515 | 0.5854 | 0.5871 | 0.2213 | 0.2010 | 0.59 | 0.83 | per stap | 150 | 109 | +2.7% | [-26.6%, +21.3%] |

| Stap | Parameters | Drempelkeuze |
|---|---|---|
| test 2025 | halfwaarde=100000, lam=0.1, onbekend=0.0, k=0.8, g=0.0 | drempel 1.15 heeft de hoogste ROI op train (+32.7%) |
| test 2026 | halfwaarde=100000, lam=2.0, onbekend=-0.3, k=0.6, g=0.0 | drempel 1.05 heeft de hoogste ROI op train (+22.8%) |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Helling model | Helling markt | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test (train 2024) | 2025 | 94 | 0.6888 | 0.6343 | 0.6371 | 0.2273 | 0.2234 | 0.45 | 0.68 | 1.05 | 65 | 44 | +16.0% | [-23.6%, +56.9%] |
| test (train 2024+2025) | 2026 | 126 | 0.6236 | 0.5490 | 0.5498 | 0.2168 | 0.1843 | 0.73 | 0.95 | 1.05 | 103 | 73 | -4.1% | [-61.6%, +13.8%] |
| totaal test | 2025+2026 | 220 | 0.6515 | 0.5854 | 0.5871 | 0.2213 | 0.2010 | 0.59 | 0.83 | 1.05 | 168 | 117 | +3.7% | [-24.5%, +23.3%] |
