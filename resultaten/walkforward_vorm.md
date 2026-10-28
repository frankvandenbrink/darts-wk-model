# Walk-forward model `vorm` (2024+2025+2026)

Per stap: afstemmen op alle jaren vóór t, ongewijzigd toetsen op t.

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test (train 2024) | 2025 | 94 | 0.6461 | 0.6343 | 0.6371 | 0.2256 | 0.2234 | 1.15 | 34 | 28 | +16.9% | [-24.9%, +43.6%] |
| test (train 2024+2025) | 2026 | 126 | 0.5725 | 0.5490 | 0.5498 | 0.1918 | 0.1843 | 1.30 | 37 | 37 | -43.6% | [-100.0%, +11.7%] |
| totaal test | 2025+2026 | 220 | 0.6039 | 0.5854 | 0.5871 | 0.2062 | 0.2010 | per stap | 71 | 65 | -14.7% | [-48.0%, +22.0%] |

| Stap | Parameters | Drempelkeuze |
|---|---|---|
| test 2025 | w=0.0, L=6, k=0.04, kc=0.02 | drempel 1.15 heeft de hoogste ROI op train (+25.4%) |
| test 2026 | w=0.0, L=6, k=0.04, kc=0.0 | drempel 1.30 heeft de hoogste ROI op train (+28.3%) |

## Ter informatie: vaste drempel 1.05 zonder stopregel (niet het hoofdresultaat)

| Set | Jaren | n | Log-loss model | Log-loss markt (prop.) | Log-loss markt (Shin) | Brier model | Brier markt (prop.) | Drempel | Bets | Underdog | ROI | 90%-int. (geclusterd per ronde) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test (train 2024) | 2025 | 94 | 0.6461 | 0.6343 | 0.6371 | 0.2256 | 0.2234 | 1.05 | 56 | 41 | +7.0% | [-17.1%, +22.9%] |
| test (train 2024+2025) | 2026 | 126 | 0.5725 | 0.5490 | 0.5498 | 0.1918 | 0.1843 | 1.05 | 76 | 73 | -12.3% | [-43.4%, +20.6%] |
| totaal test | 2025+2026 | 220 | 0.6039 | 0.5854 | 0.5871 | 0.2062 | 0.2010 | 1.05 | 132 | 114 | -4.1% | [-22.7%, +14.9%] |
