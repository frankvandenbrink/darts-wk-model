# Vergelijking modellen: vorm, rating, rating-platt, rating+markt, rating+avg, markt-krimp

Alle cijfers op de testjaren; parameters en drempel afgestemd op train. Log-loss en Brier: lager is beter. Verschil = gemiddelde log-loss model − markt (proportioneel) per wedstrijd, met standaardfout; < 0 = model beter. Helling = c in logit P(winst) = c·logit(p) op de testdata (1 = goed gekalibreerd, < 1 = te stellig, > 1 = te vlak). ROI bij inzet 1 met de stopregel uit de README; interval: bootstrap per (jaar, ronde).

## Data voor de rating (events strikt vóór de WK-start)

| WK | Cutoff (< start) | Events in lijst | Met uitslagen | Paywall | Wedstrijden | Waarvan sets | Laatste event | WK-spelers zonder data |
|---|---|---|---|---|---|---|---|---|
| 2024 | 2023-12-15 | 100 | 60 | 40 | 5874 | 249 | 2023-10-20 | 14 van 98 |
| 2025 | 2024-12-15 | 150 | 71 | 79 | 6868 | 249 | 2024-10-30 | 11 van 98 |
| 2026 | 2025-12-11 | 205 | 72 | 133 | 6995 | 249 | 2025-03-11 | 21 van 128 |

Nulvergelijking blind op de underdog (alle wedstrijden met ongelijke odds): 2024: -4.5% over 92, 2025: +25.0% over 94, 2026: +1.2% over 124.


## Train → test (vaste richting)

### Train 2026 → test 2025

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 94 | 0.6179 | 0.2159 | -0.0164 (0.0169) | 0.92 | 0 | 0 | – | – | beste ROI op train is -6.8% (drempel 1.00) <= 0: niet wedden |
| rating | 94 | 0.6494 | 0.2280 | +0.0152 (0.0276) | 0.77 | 39 | 39 | +32.7% | [-20.0%, +75.2%] | drempel 1.30 heeft de hoogste ROI op train (+19.6%) |
| rating-platt | 94 | 0.6507 | 0.2285 | +0.0165 (0.0275) | 0.74 | 37 | 37 | +15.6% | [-49.7%, +75.2%] | drempel 1.30 heeft de hoogste ROI op train (+21.5%) |
| rating+markt | 94 | 0.6324 | 0.2224 | -0.0019 (0.0037) | 0.70 | 7 | 7 | -100.0% | [-100.0%, -100.0%] | drempel 1.10 heeft de hoogste ROI op train (+40.5%) |
| rating+avg | 94 | 0.6717 | 0.2388 | +0.0374 (0.0292) | 0.56 | 31 | 29 | +7.4% | [-27.5%, +55.5%] | drempel 1.30 heeft de hoogste ROI op train (+27.4%) |
| markt-krimp | 94 | 0.6306 | 0.2220 | -0.0036 (0.0026) | 0.71 | 9 | 9 | +50.0% | [-14.3%, +95.0%] | drempel 1.05 heeft de hoogste ROI op train (+30.8%) |
| markt (prop.) | 94 | 0.6343 | 0.2234 | 0 | 0.68 | – | – | – | – | – |
| markt (Shin) | 94 | 0.6371 | 0.2247 | | | – | – | – | – | – |

Parameters:

- `vorm`: w=0.0, L=12, k=0.04, kc=0.0
- `rating`: halfwaarde=365, lam=0.5, onbekend=0.0, k=0.6, g=0.0
- `rating-platt`: basis=(halfwaarde=365, lam=0.5, onbekend=0.0, k=0.6, g=0.0), c=1.0401, c_se=0.2398
- `rating+markt`: basis=(halfwaarde=365, lam=0.5, onbekend=0.0, k=0.6, g=0.0), a=0.8638, a_se=0.2564, b=0.1543, b_se=0.3281, lr_b_train=0.223
- `rating+avg`: halfwaarde=365, lam=0.5, onbekend=0.0, k=0.5, g=0.08
- `markt-krimp`: a=0.9472, a_se=0.1891

### Train 2025 → test 2026

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 126 | 0.5680 | 0.1905 | +0.0190 (0.0133) | 1.11 | 68 | 67 | -26.9% | [-56.2%, +7.2%] | drempel 1.10 heeft de hoogste ROI op train (+50.9%) |
| rating | 126 | 0.6369 | 0.2205 | +0.0879 (0.0340) | 0.71 | 105 | 79 | -6.7% | [-55.0%, +7.2%] | drempel 1.05 heeft de hoogste ROI op train (+33.6%) |
| rating-platt | 126 | 0.6377 | 0.2207 | +0.0886 (0.0342) | 0.70 | 105 | 79 | -6.7% | [-55.0%, +7.2%] | drempel 1.05 heeft de hoogste ROI op train (+33.6%) |
| rating+markt | 126 | 0.5806 | 0.1981 | +0.0316 (0.0191) | 1.03 | 71 | 64 | +12.9% | [-55.3%, +31.8%] | drempel 1.15 heeft de hoogste ROI op train (+34.6%) |
| rating+avg | 126 | 0.6194 | 0.2145 | +0.0704 (0.0318) | 0.83 | 104 | 79 | -1.8% | [-47.5%, +9.7%] | drempel 1.05 heeft de hoogste ROI op train (+37.5%) |
| markt-krimp | 126 | 0.5578 | 0.1876 | +0.0088 (0.0139) | 1.40 | 99 | 99 | +2.9% | [-41.5%, +13.4%] | drempel 1.05 heeft de hoogste ROI op train (+29.2%) |
| markt (prop.) | 126 | 0.5490 | 0.1843 | 0 | 0.95 | – | – | – | – | – |
| markt (Shin) | 126 | 0.5498 | 0.1843 | | | – | – | – | – | – |

Parameters:

- `vorm`: w=0.25, L=12, k=0.04, kc=0.0
- `rating`: halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0
- `rating-platt`: basis=(halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0), c=1.0123, c_se=0.3098
- `rating+markt`: basis=(halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0), a=0.3972, a_se=0.3257, b=0.5167, b_se=0.4944, lr_b_train=1.129
- `rating+avg`: halfwaarde=100000, lam=2.0, onbekend=-0.6, k=0.4, g=0.02
- `markt-krimp`: a=0.6764, a_se=0.2007

### Train 2025 → test 2024

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 94 | 0.5985 | 0.2061 | +0.0287 (0.0233) | 1.14 | 63 | 60 | +6.6% | [-19.7%, +50.8%] | drempel 1.10 heeft de hoogste ROI op train (+50.9%) |
| rating | 94 | 0.6048 | 0.2071 | +0.0350 (0.0300) | 1.07 | 73 | 64 | +7.7% | [-18.3%, +47.8%] | drempel 1.05 heeft de hoogste ROI op train (+33.6%) |
| rating-platt | 94 | 0.6047 | 0.2070 | +0.0350 (0.0299) | 1.06 | 73 | 64 | +7.7% | [-18.3%, +47.8%] | drempel 1.05 heeft de hoogste ROI op train (+33.6%) |
| rating+markt | 94 | 0.5798 | 0.1953 | +0.0100 (0.0186) | 1.25 | 48 | 47 | +12.8% | [-22.5%, +71.4%] | drempel 1.15 heeft de hoogste ROI op train (+34.6%) |
| rating+avg | 94 | 0.5970 | 0.2036 | +0.0272 (0.0284) | 1.23 | 71 | 65 | +11.4% | [-19.3%, +52.4%] | drempel 1.05 heeft de hoogste ROI op train (+37.5%) |
| markt-krimp | 94 | 0.5786 | 0.1951 | +0.0089 (0.0164) | 1.42 | 73 | 73 | +8.0% | [-7.1%, +38.5%] | drempel 1.05 heeft de hoogste ROI op train (+29.2%) |
| markt (prop.) | 94 | 0.5698 | 0.1901 | 0 | 0.96 | – | – | – | – | – |
| markt (Shin) | 94 | 0.5722 | 0.1902 | | | – | – | – | – | – |

Parameters:

- `vorm`: w=0.25, L=12, k=0.04, kc=0.0
- `rating`: halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0
- `rating-platt`: basis=(halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0), c=1.0123, c_se=0.3098
- `rating+markt`: basis=(halfwaarde=100000, lam=5.0, onbekend=-0.6, k=0.5, g=0.0), a=0.3972, a_se=0.3257, b=0.5167, b_se=0.4944, lr_b_train=1.129
- `rating+avg`: halfwaarde=100000, lam=2.0, onbekend=-0.6, k=0.4, g=0.02
- `markt-krimp`: a=0.6764, a_se=0.2007

### Train 2025+2026 → test 2024

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 94 | 0.5973 | 0.2058 | +0.0276 (0.0233) | 1.14 | 65 | 62 | -0.8% | [-27.3%, +42.2%] | drempel 1.10 heeft de hoogste ROI op train (+17.8%) |
| rating | 94 | 0.5997 | 0.2055 | +0.0299 (0.0300) | 1.37 | 45 | 45 | +14.4% | [-29.2%, +118.5%] | drempel 1.30 heeft de hoogste ROI op train (+19.6%) |
| rating-platt | 94 | 0.5999 | 0.2056 | +0.0301 (0.0301) | 1.38 | 45 | 45 | +14.4% | [-29.2%, +118.5%] | drempel 1.30 heeft de hoogste ROI op train (+19.6%) |
| rating+markt | 94 | 0.5703 | 0.1911 | +0.0006 (0.0089) | 1.17 | 19 | 19 | +42.1% | [-30.0%, +220.0%] | drempel 1.20 heeft de hoogste ROI op train (+33.3%) |
| rating+avg | 94 | 0.5929 | 0.2018 | +0.0232 (0.0267) | 1.39 | 44 | 44 | +24.3% | [-22.0%, +122.7%] | drempel 1.30 heeft de hoogste ROI op train (+23.0%) |
| markt-krimp | 94 | 0.5715 | 0.1917 | +0.0017 (0.0087) | 1.16 | 17 | 17 | +58.8% | [-30.0%, +220.0%] | drempel 1.20 heeft de hoogste ROI op train (+24.5%) |
| markt (prop.) | 94 | 0.5698 | 0.1901 | 0 | 0.96 | – | – | – | – | – |
| markt (Shin) | 94 | 0.5722 | 0.1902 | | | – | – | – | – | – |

Parameters:

- `vorm`: w=0.0, L=12, k=0.04, kc=0.0
- `rating`: halfwaarde=1460, lam=2.0, onbekend=0.0, k=0.6, g=0.0
- `rating-platt`: basis=(halfwaarde=1460, lam=2.0, onbekend=0.0, k=0.6, g=0.0), c=0.9953, c_se=0.1889
- `rating+markt`: basis=(halfwaarde=1460, lam=2.0, onbekend=0.0, k=0.6, g=0.0), a=0.7666, a_se=0.2038, b=0.116, b_se=0.284, lr_b_train=0.167
- `rating+avg`: halfwaarde=100000, lam=0.5, onbekend=-0.3, k=0.3, g=0.08
- `markt-krimp`: a=0.8293, a_se=0.1363


## Walk-forward

### Train 2024 → test 2025

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 94 | 0.6461 | 0.2256 | +0.0118 (0.0186) | 0.63 | 34 | 28 | +16.9% | [-24.9%, +43.6%] | drempel 1.15 heeft de hoogste ROI op train (+25.4%) |
| rating | 94 | 0.6888 | 0.2273 | +0.0545 (0.0535) | 0.45 | 47 | 36 | +17.5% | [-24.8%, +63.0%] | drempel 1.15 heeft de hoogste ROI op train (+32.7%) |
| rating-platt | 94 | 0.6774 | 0.2257 | +0.0431 (0.0482) | 0.49 | 47 | 39 | +30.1% | [-24.2%, +78.2%] | drempel 1.15 heeft de hoogste ROI op train (+36.8%) |
| rating+markt | 94 | 0.6444 | 0.2231 | +0.0101 (0.0211) | 0.62 | 64 | 42 | +14.7% | [-22.1%, +54.4%] | drempel 1.00 heeft de hoogste ROI op train (+22.1%) |
| rating+avg | 94 | 0.6888 | 0.2273 | +0.0545 (0.0535) | 0.45 | 47 | 36 | +17.5% | [-24.8%, +63.0%] | drempel 1.15 heeft de hoogste ROI op train (+32.7%) |
| markt-krimp | 94 | 0.6316 | 0.2224 | -0.0027 (0.0019) | 0.70 | 28 | 28 | +25.9% | [-35.0%, +73.9%] | drempel 1.00 heeft de hoogste ROI op train (+58.8%) |
| markt (prop.) | 94 | 0.6343 | 0.2234 | 0 | 0.68 | – | – | – | – | – |
| markt (Shin) | 94 | 0.6371 | 0.2247 | | | – | – | – | – | – |

Parameters:

- `vorm`: w=0.0, L=6, k=0.04, kc=0.02
- `rating`: halfwaarde=100000, lam=0.1, onbekend=0.0, k=0.8, g=0.0
- `rating-platt`: basis=(halfwaarde=100000, lam=0.1, onbekend=0.0, k=0.8, g=0.0), c=0.9152, c_se=0.235
- `rating+markt`: basis=(halfwaarde=100000, lam=0.1, onbekend=0.0, k=0.8, g=0.0), a=0.6227, a_se=0.3487, b=0.3974, b_se=0.3301, lr_b_train=1.771
- `rating+avg`: halfwaarde=100000, lam=0.1, onbekend=0.0, k=0.8, g=0.0
- `markt-krimp`: a=0.9618, a_se=0.2297

### Train 2024+2025 → test 2026

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 126 | 0.5725 | 0.1918 | +0.0235 (0.0149) | 1.09 | 37 | 37 | -43.6% | [-100.0%, +11.7%] | drempel 1.30 heeft de hoogste ROI op train (+28.3%) |
| rating | 126 | 0.6236 | 0.2168 | +0.0746 (0.0334) | 0.73 | 103 | 73 | -4.1% | [-61.6%, +13.8%] | drempel 1.05 heeft de hoogste ROI op train (+22.8%) |
| rating-platt | 126 | 0.6231 | 0.2167 | +0.0741 (0.0332) | 0.73 | 103 | 73 | -4.1% | [-61.6%, +13.8%] | drempel 1.05 heeft de hoogste ROI op train (+22.8%) |
| rating+markt | 126 | 0.5610 | 0.1902 | +0.0120 (0.0134) | 1.04 | 49 | 48 | +35.8% | [-39.1%, +55.3%] | drempel 1.20 heeft de hoogste ROI op train (+46.2%) |
| rating+avg | 126 | 0.6183 | 0.2140 | +0.0693 (0.0328) | 0.73 | 61 | 54 | +18.1% | [-46.5%, +40.1%] | drempel 1.30 heeft de hoogste ROI op train (+24.0%) |
| markt-krimp | 126 | 0.5509 | 0.1852 | +0.0019 (0.0082) | 1.17 | 28 | 28 | +21.4% | [-100.0%, +100.0%] | drempel 1.30 heeft de hoogste ROI op train (+44.7%) |
| markt (prop.) | 126 | 0.5490 | 0.1843 | 0 | 0.95 | – | – | – | – | – |
| markt (Shin) | 126 | 0.5498 | 0.1843 | | | – | – | – | – | – |

Parameters:

- `vorm`: w=0.0, L=6, k=0.04, kc=0.0
- `rating`: halfwaarde=100000, lam=2.0, onbekend=-0.3, k=0.6, g=0.0
- `rating-platt`: basis=(halfwaarde=100000, lam=2.0, onbekend=-0.3, k=0.6, g=0.0), c=0.9907, c_se=0.1936
- `rating+markt`: basis=(halfwaarde=100000, lam=2.0, onbekend=-0.3, k=0.6, g=0.0), a=0.5752, a_se=0.2557, b=0.3633, b_se=0.3283, lr_b_train=1.242
- `rating+avg`: halfwaarde=100000, lam=0.5, onbekend=-0.6, k=0.4, g=0.04
- `markt-krimp`: a=0.8093, a_se=0.151

## Walk-forward totaal (testjaren samen)

| Model | n | Log-loss | Brier | Verschil log-loss vs markt (se) | Helling | Bets | Underdog | ROI | 90%-int. (geclusterd) | Drempelkeuze (train) |
|---|---|---|---|---|---|---|---|---|---|---|
| vorm | 220 | 0.6039 | 0.2062 | +0.0185 (0.0117) | 0.85 | 71 | 65 | -14.7% | [-48.0%, +22.0%] |  |
| rating | 220 | 0.6515 | 0.2213 | +0.0660 (0.0297) | 0.59 | 150 | 109 | +2.7% | [-26.6%, +21.3%] |  |
| rating-platt | 220 | 0.6463 | 0.2205 | +0.0608 (0.0280) | 0.62 | 150 | 112 | +6.6% | [-24.2%, +28.0%] |  |
| rating+markt | 220 | 0.5966 | 0.2043 | +0.0112 (0.0118) | 0.83 | 113 | 90 | +23.8% | [-9.4%, +48.6%] |  |
| rating+avg | 220 | 0.6484 | 0.2197 | +0.0630 (0.0295) | 0.59 | 108 | 90 | +17.9% | [-16.8%, +40.6%] |  |
| markt-krimp | 220 | 0.5854 | 0.2011 | -0.0000 (0.0048) | 0.94 | 56 | 56 | +23.7% | [-50.0%, +71.4%] |  |
| markt (prop.) | 220 | 0.5854 | 0.2010 | 0 | 0.83 | – | – | – | – | – |
| markt (Shin) | 220 | 0.5871 | 0.2016 | | | – | – | – | – | – |
