# Experimenten

Gegenereerd door `dartswk experimenten` (protocol: [docs/protocol.md](../docs/protocol.md)). Verschil = log-loss model − markt (proportioneel) per wedstrijd met standaardfout; < 0 = model beter. 'Binnen de ruis' = |verschil| ≤ 2·se. ROI bij inzet 1, 90%-interval met bootstrap per (jaar, ronde); 'Clusters' = aantal (jaar, ronde)-clusters met bets. Een WK heeft hoogstens 7 rondes, dus hoogstens 7 clusters per testjaar; dan is het interval grof en kan het tot ±100% reiken. Helling = c in logit P(winst) = c·logit(p) (1 = goed, < 1 = te stellig).

## Walk-forward (hoofdresultaat)

| Id | Model | Test | n | Log-loss | Markt | Verschil (se) | Oordeel | Brier | Helling | Bets | ROI [90%] | Clusters |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E001 | markt | 2025 | 94 | 0.6343 | 0.6343 | +0.0000 (0.0000) | binnen de ruis | 0.2234 | 0.68 | 0 | – – | 0 |
| E001 | markt | 2026 | 126 | 0.5490 | 0.5490 | +0.0000 (0.0000) | binnen de ruis | 0.1843 | 0.95 | 0 | – – | 0 |
| E002 | markt-vlak | 2025 | 94 | 0.6316 | 0.6343 | -0.0027 (0.0019) | binnen de ruis | 0.2224 | 0.70 | 28 | +25.9% [-35.0%, +73.9%] | 5 |
| E002 | markt-vlak | 2026 | 126 | 0.5509 | 0.5490 | +0.0019 (0.0082) | binnen de ruis | 0.1852 | 1.17 | 28 | +21.4% [-100.0%, +100.0%] | 6 |
| E003 | blind-underdog | 2025 | 94 | 0.6343 | 0.6343 | +0.0000 (0.0000) | binnen de ruis | 0.2234 | 0.68 | 94 | +25.0% [-21.4%, +47.3%] | 7 |
| E003 | blind-underdog | 2026 | 126 | 0.5490 | 0.5490 | +0.0000 (0.0000) | binnen de ruis | 0.1843 | 0.95 | 124 | +1.2% [-28.4%, +9.4%] | 7 |
| E004 | blind-favoriet | 2025 | 94 | 0.6343 | 0.6343 | +0.0000 (0.0000) | binnen de ruis | 0.2234 | 0.68 | 94 | -17.0% [-26.9%, +5.1%] | 7 |
| E004 | blind-favoriet | 2026 | 126 | 0.5490 | 0.5490 | +0.0000 (0.0000) | binnen de ruis | 0.1843 | 0.95 | 124 | -3.6% [-5.5%, +0.0%] | 7 |
| E005 | munt | 2025 | 94 | 0.6931 | 0.6343 | +0.0589 (0.0508) | binnen de ruis | 0.2500 | – | 0 | – – | 0 |
| E005 | munt | 2026 | 126 | 0.6931 | 0.5490 | +0.1441 (0.0445) | slechter dan de markt | 0.2500 | – | 0 | – – | 0 |
| E006 | vorm | 2025 | 94 | 0.6461 | 0.6343 | +0.0118 (0.0186) | binnen de ruis | 0.2256 | 0.63 | 34 | +16.9% [-24.9%, +43.6%] | 6 |
| E006 | vorm | 2026 | 126 | 0.5725 | 0.5490 | +0.0235 (0.0149) | binnen de ruis | 0.1918 | 1.09 | 37 | -43.6% [-100.0%, +11.7%] | 6 |
| E007 | rating | 2025 | 94 | 0.6888 | 0.6343 | +0.0545 (0.0535) | binnen de ruis | 0.2273 | 0.45 | 47 | +17.5% [-24.8%, +63.0%] | 7 |
| E007 | rating | 2026 | 126 | 0.6236 | 0.5490 | +0.0746 (0.0334) | slechter dan de markt | 0.2168 | 0.73 | 103 | -4.1% [-61.6%, +13.8%] | 7 |
| E008 | rating-platt | 2025 | 94 | 0.6774 | 0.6343 | +0.0431 (0.0482) | binnen de ruis | 0.2257 | 0.49 | 47 | +30.1% [-24.2%, +78.2%] | 7 |
| E008 | rating-platt | 2026 | 126 | 0.6231 | 0.5490 | +0.0741 (0.0332) | slechter dan de markt | 0.2167 | 0.73 | 103 | -4.1% [-61.6%, +13.8%] | 7 |
| E009 | rating+markt | 2025 | 94 | 0.6444 | 0.6343 | +0.0101 (0.0211) | binnen de ruis | 0.2231 | 0.62 | 64 | +14.7% [-22.1%, +54.4%] | 7 |
| E009 | rating+markt | 2026 | 126 | 0.5610 | 0.5490 | +0.0120 (0.0134) | binnen de ruis | 0.1902 | 1.04 | 49 | +35.8% [-39.1%, +55.3%] | 6 |
| E010 | rating+avg | 2025 | 94 | 0.6888 | 0.6343 | +0.0545 (0.0535) | binnen de ruis | 0.2273 | 0.45 | 47 | +17.5% [-24.8%, +63.0%] | 7 |
| E010 | rating+avg | 2026 | 126 | 0.6183 | 0.5490 | +0.0693 (0.0328) | slechter dan de markt | 0.2140 | 0.73 | 61 | +18.1% [-46.5%, +40.1%] | 6 |
| E011 | bt-halfwaarde | 2025 | 94 | 0.6698 | 0.6343 | +0.0355 (0.0302) | binnen de ruis | 0.2342 | 0.57 | 30 | +23.7% [-67.2%, +95.0%] | 7 |
| E011 | bt-halfwaarde | 2026 | 126 | 0.6262 | 0.5490 | +0.0772 (0.0322) | slechter dan de markt | 0.2171 | 0.85 | 105 | -4.6% [-43.5%, +5.6%] | 7 |
| E012 | bt-halfwaarde | 2025 | 94 | 0.6891 | 0.6343 | +0.0548 (0.0434) | binnen de ruis | 0.2334 | 0.47 | 83 | +10.2% [-26.4%, +43.6%] | 7 |
| E012 | bt-halfwaarde | 2026 | 126 | 0.6121 | 0.5490 | +0.0630 (0.0309) | slechter dan de markt | 0.2122 | 0.94 | 73 | +14.5% [-43.9%, +28.7%] | 7 |
| E013 | bt-halfwaarde | 2025 | 94 | 0.6861 | 0.6343 | +0.0519 (0.0478) | binnen de ruis | 0.2296 | 0.47 | 48 | +15.1% [-28.1%, +68.5%] | 7 |
| E013 | bt-halfwaarde | 2026 | 126 | 0.6166 | 0.5490 | +0.0676 (0.0314) | slechter dan de markt | 0.2146 | 0.85 | 77 | +5.8% [-60.6%, +21.4%] | 7 |
| E014 | elo | 2025 | 94 | 0.6535 | 0.6343 | +0.0192 (0.0411) | binnen de ruis | 0.2308 | 0.79 | 45 | +40.7% [-31.4%, +72.1%] | 7 |
| E014 | elo | 2026 | 126 | 0.6409 | 0.5490 | +0.0919 (0.0323) | slechter dan de markt | 0.2246 | 0.84 | 62 | +7.8% [-62.5%, +24.4%] | 7 |
| E015 | glicko | 2025 | 94 | 0.6312 | 0.6343 | -0.0031 (0.0279) | binnen de ruis | 0.2212 | 0.72 | 44 | +2.7% [-48.5%, +55.1%] | 7 |
| E015 | glicko | 2026 | 126 | 0.6337 | 0.5490 | +0.0847 (0.0339) | slechter dan de markt | 0.2199 | 0.71 | 104 | -2.9% [-46.7%, +8.5%] | 7 |
| E016 | hold | 2025 | 94 | 0.6863 | 0.6343 | +0.0521 (0.0523) | binnen de ruis | 0.2270 | 0.46 | 49 | +18.9% [-22.7%, +63.0%] | 7 |
| E016 | hold | 2026 | 126 | 0.6227 | 0.5490 | +0.0737 (0.0331) | slechter dan de markt | 0.2165 | 0.74 | 93 | -1.1% [-63.2%, +17.4%] | 7 |
| E017 | logreg | 2025 | 94 | 0.6327 | 0.6343 | -0.0015 (0.0020) | binnen de ruis | 0.2227 | 0.70 | 27 | +39.1% [-25.3%, +77.8%] | 7 |
| E017 | logreg | 2026 | 126 | 0.5497 | 0.5490 | +0.0007 (0.0087) | binnen de ruis | 0.1848 | 1.18 | 45 | +26.1% [-100.0%, +50.8%] | 5 |
| E018 | logreg | 2025 | 94 | 0.6461 | 0.6343 | +0.0119 (0.0256) | binnen de ruis | 0.2237 | 0.66 | 20 | +38.4% [-30.8%, +90.4%] | 7 |
| E018 | logreg | 2026 | 126 | 0.5833 | 0.5490 | +0.0343 (0.0206) | binnen de ruis | 0.1987 | 0.98 | 46 | +24.9% [-62.5%, +46.5%] | 7 |
| E019 | gbm | – | – | – | – | – | **niet gedraaid**: niet gedraaid: geen sklearn (en geen grote pakketten installeren) | – | – | – | – | – |
| E020 | blend-krimp | 2025 | 94 | 0.6325 | 0.6343 | -0.0017 (0.0056) | binnen de ruis | 0.2221 | 0.69 | 39 | +33.0% [-22.2%, +73.8%] | 7 |
| E020 | blend-krimp | 2026 | 126 | 0.5610 | 0.5490 | +0.0120 (0.0134) | binnen de ruis | 0.1902 | 1.04 | 49 | +35.8% [-39.1%, +55.3%] | 6 |
| E021 | platt | 2025 | 94 | 0.6468 | 0.6343 | +0.0126 (0.0187) | binnen de ruis | 0.2259 | 0.63 | 42 | +8.9% [-26.3%, +32.4%] | 6 |
| E021 | platt | 2026 | 126 | 0.5720 | 0.5490 | +0.0230 (0.0148) | binnen de ruis | 0.1913 | 1.03 | 35 | -40.4% [-100.0%, +16.8%] | 6 |
| E022 | isotoon | 2025 | 94 | 0.6752 | 0.6343 | +0.0409 (0.0347) | binnen de ruis | 0.2315 | 0.48 | 15 | +0.4% [-45.5%, +67.9%] | 6 |
| E022 | isotoon | 2026 | 126 | 0.5896 | 0.5490 | +0.0406 (0.0204) | binnen de ruis | 0.1939 | 0.82 | 38 | -28.8% [-100.0%, +44.3%] | 6 |
| E023 | isotoon | 2025 | 94 | 0.6947 | 0.6343 | +0.0605 (0.0543) | binnen de ruis | 0.2325 | 0.43 | 47 | +29.5% [-13.9%, +57.4%] | 7 |
| E023 | isotoon | 2026 | 126 | 0.6430 | 0.5490 | +0.0940 (0.0485) | binnen de ruis | 0.2191 | 0.54 | 55 | +33.6% [-39.4%, +58.9%] | 6 |
| E024 | blend-krimp | 2025 | 94 | 0.6324 | 0.6343 | -0.0019 (0.0111) | binnen de ruis | 0.2212 | 0.69 | 53 | +24.1% [-22.6%, +65.9%] | 7 |
| E024 | blend-krimp | 2026 | 126 | 0.5600 | 0.5490 | +0.0109 (0.0130) | binnen de ruis | 0.1899 | 1.04 | 49 | +35.8% [-39.1%, +55.3%] | 6 |
| E025 | elo | 2025 | 94 | 0.6535 | 0.6343 | +0.0192 (0.0411) | binnen de ruis | 0.2308 | 0.79 | 45 | +40.7% [-31.4%, +72.1%] | 7 |
| E025 | elo | 2026 | 126 | 0.6426 | 0.5490 | +0.0936 (0.0329) | slechter dan de markt | 0.2238 | 0.73 | 64 | +15.4% [-42.1%, +28.4%] | 7 |
| E026 | glicko | 2025 | 94 | 0.6537 | 0.6343 | +0.0195 (0.0320) | binnen de ruis | 0.2276 | 0.59 | 41 | +23.8% [-28.6%, +79.3%] | 7 |
| E026 | glicko | 2026 | 126 | 0.6247 | 0.5490 | +0.0757 (0.0319) | slechter dan de markt | 0.2174 | 0.75 | 97 | -9.7% [-46.2%, +0.0%] | 7 |

## Vaste richtingen (ter vergelijking; afstemmen op een later jaar is niet walk-forward)

| Id | Model | Train → test | Log-loss | Verschil (se) | Bets | ROI [90%] |
|---|---|---|---|---|---|---|
| E001 | markt | 2026 → 2025 | 0.6343 | +0.0000 (0.0000) | 0 | – – |
| E001 | markt | 2025 → 2026 | 0.5490 | +0.0000 (0.0000) | 0 | – – |
| E001 | markt | 2025 → 2024 | 0.5698 | +0.0000 (0.0000) | 0 | – – |
| E001 | markt | 2025+2026 → 2024 | 0.5698 | +0.0000 (0.0000) | 0 | – – |
| E002 | markt-vlak | 2026 → 2025 | 0.6306 | -0.0036 (0.0026) | 9 | +50.0% [-14.3%, +95.0%] |
| E002 | markt-vlak | 2025 → 2026 | 0.5578 | +0.0088 (0.0139) | 99 | +2.9% [-41.5%, +13.4%] |
| E002 | markt-vlak | 2025 → 2024 | 0.5786 | +0.0089 (0.0164) | 73 | +8.0% [-7.1%, +38.5%] |
| E002 | markt-vlak | 2025+2026 → 2024 | 0.5715 | +0.0017 (0.0087) | 17 | +58.8% [-30.0%, +220.0%] |
| E003 | blind-underdog | 2026 → 2025 | 0.6343 | +0.0000 (0.0000) | 94 | +25.0% [-21.4%, +47.3%] |
| E003 | blind-underdog | 2025 → 2026 | 0.5490 | +0.0000 (0.0000) | 124 | +1.2% [-28.4%, +9.4%] |
| E003 | blind-underdog | 2025 → 2024 | 0.5698 | +0.0000 (0.0000) | 92 | -4.5% [-18.1%, +21.9%] |
| E003 | blind-underdog | 2025+2026 → 2024 | 0.5698 | +0.0000 (0.0000) | 92 | -4.5% [-18.1%, +21.9%] |
| E004 | blind-favoriet | 2026 → 2025 | 0.6343 | +0.0000 (0.0000) | 94 | -17.0% [-26.9%, +5.1%] |
| E004 | blind-favoriet | 2025 → 2026 | 0.5490 | +0.0000 (0.0000) | 124 | -3.6% [-5.5%, +0.0%] |
| E004 | blind-favoriet | 2025 → 2024 | 0.5698 | +0.0000 (0.0000) | 92 | +1.9% [-2.9%, +7.8%] |
| E004 | blind-favoriet | 2025+2026 → 2024 | 0.5698 | +0.0000 (0.0000) | 92 | +1.9% [-2.9%, +7.8%] |
| E005 | munt | 2026 → 2025 | 0.6931 | +0.0589 (0.0508) | 0 | – – |
| E005 | munt | 2025 → 2026 | 0.6931 | +0.1441 (0.0445) | 0 | – – |
| E005 | munt | 2025 → 2024 | 0.6931 | +0.1234 (0.0506) | 0 | – – |
| E005 | munt | 2025+2026 → 2024 | 0.6931 | +0.1234 (0.0506) | 0 | – – |
| E006 | vorm | 2026 → 2025 | 0.6179 | -0.0164 (0.0169) | 0 | – – |
| E006 | vorm | 2025 → 2026 | 0.5680 | +0.0190 (0.0133) | 68 | -26.9% [-56.2%, +7.2%] |
| E006 | vorm | 2025 → 2024 | 0.5985 | +0.0287 (0.0233) | 63 | +6.6% [-19.7%, +50.8%] |
| E006 | vorm | 2025+2026 → 2024 | 0.5973 | +0.0276 (0.0233) | 65 | -0.8% [-27.3%, +42.2%] |
| E007 | rating | 2026 → 2025 | 0.6494 | +0.0152 (0.0276) | 39 | +32.7% [-20.0%, +75.2%] |
| E007 | rating | 2025 → 2026 | 0.6369 | +0.0879 (0.0340) | 105 | -6.7% [-55.0%, +7.2%] |
| E007 | rating | 2025 → 2024 | 0.6048 | +0.0350 (0.0300) | 73 | +7.7% [-18.3%, +47.8%] |
| E007 | rating | 2025+2026 → 2024 | 0.5997 | +0.0299 (0.0300) | 45 | +14.4% [-29.2%, +118.5%] |
| E008 | rating-platt | 2026 → 2025 | 0.6507 | +0.0165 (0.0275) | 37 | +15.6% [-49.7%, +75.2%] |
| E008 | rating-platt | 2025 → 2026 | 0.6377 | +0.0886 (0.0342) | 105 | -6.7% [-55.0%, +7.2%] |
| E008 | rating-platt | 2025 → 2024 | 0.6047 | +0.0350 (0.0299) | 73 | +7.7% [-18.3%, +47.8%] |
| E008 | rating-platt | 2025+2026 → 2024 | 0.5999 | +0.0301 (0.0301) | 45 | +14.4% [-29.2%, +118.5%] |
| E009 | rating+markt | 2026 → 2025 | 0.6324 | -0.0019 (0.0037) | 7 | -100.0% [-100.0%, -100.0%] |
| E009 | rating+markt | 2025 → 2026 | 0.5806 | +0.0316 (0.0191) | 71 | +12.9% [-55.3%, +31.8%] |
| E009 | rating+markt | 2025 → 2024 | 0.5798 | +0.0100 (0.0186) | 48 | +12.8% [-22.5%, +71.4%] |
| E009 | rating+markt | 2025+2026 → 2024 | 0.5703 | +0.0006 (0.0089) | 19 | +42.1% [-30.0%, +220.0%] |
| E010 | rating+avg | 2026 → 2025 | 0.6717 | +0.0374 (0.0292) | 31 | +7.4% [-27.5%, +55.5%] |
| E010 | rating+avg | 2025 → 2026 | 0.6194 | +0.0704 (0.0318) | 104 | -1.8% [-47.5%, +9.7%] |
| E010 | rating+avg | 2025 → 2024 | 0.5970 | +0.0272 (0.0284) | 71 | +11.4% [-19.3%, +52.4%] |
| E010 | rating+avg | 2025+2026 → 2024 | 0.5929 | +0.0232 (0.0267) | 44 | +24.3% [-22.0%, +122.7%] |
| E011 | bt-halfwaarde | 2026 → 2025 | 0.6765 | +0.0422 (0.0310) | 36 | +27.5% [-28.5%, +73.6%] |
| E011 | bt-halfwaarde | 2025 → 2026 | 0.6375 | +0.0885 (0.0322) | 94 | -0.7% [-49.5%, +10.1%] |
| E011 | bt-halfwaarde | 2025 → 2024 | 0.6210 | +0.0513 (0.0323) | 66 | +0.0% [-19.8%, +38.6%] |
| E011 | bt-halfwaarde | 2025+2026 → 2024 | 0.6070 | +0.0372 (0.0297) | 51 | +10.8% [-35.5%, +85.6%] |
| E012 | bt-halfwaarde | 2026 → 2025 | 0.6494 | +0.0152 (0.0276) | 39 | +32.7% [-20.0%, +75.2%] |
| E012 | bt-halfwaarde | 2025 → 2026 | 0.6319 | +0.0829 (0.0325) | 79 | +9.6% [-43.9%, +21.4%] |
| E012 | bt-halfwaarde | 2025 → 2024 | 0.6089 | +0.0391 (0.0286) | 50 | +8.3% [-29.0%, +72.1%] |
| E012 | bt-halfwaarde | 2025+2026 → 2024 | 0.5976 | +0.0279 (0.0282) | 44 | +17.1% [-25.9%, +118.5%] |
| E013 | bt-halfwaarde | 2026 → 2025 | 0.6408 | +0.0066 (0.0287) | 42 | +23.2% [-21.6%, +52.2%] |
| E013 | bt-halfwaarde | 2025 → 2026 | 0.6347 | +0.0857 (0.0337) | 117 | -5.9% [-50.0%, +8.5%] |
| E013 | bt-halfwaarde | 2025 → 2024 | 0.6033 | +0.0336 (0.0292) | 80 | +8.4% [-13.7%, +46.1%] |
| E013 | bt-halfwaarde | 2025+2026 → 2024 | 0.6038 | +0.0340 (0.0301) | 46 | +18.9% [-26.0%, +122.7%] |
| E014 | elo | 2026 → 2025 | 0.6784 | +0.0441 (0.0376) | 70 | +18.6% [-15.3%, +50.9%] |
| E014 | elo | 2025 → 2026 | 0.6362 | +0.0872 (0.0320) | 65 | +8.6% [-67.9%, +22.5%] |
| E014 | elo | 2025 → 2024 | 0.6318 | +0.0621 (0.0315) | 50 | +3.0% [-28.3%, +60.5%] |
| E014 | elo | 2025+2026 → 2024 | 0.6338 | +0.0640 (0.0314) | 36 | +3.1% [-42.9%, +41.3%] |
| E015 | glicko | 2026 → 2025 | 0.6739 | +0.0396 (0.0335) | 36 | +22.4% [-28.0%, +59.0%] |
| E015 | glicko | 2025 → 2026 | 0.6337 | +0.0847 (0.0339) | 104 | -2.9% [-46.7%, +8.5%] |
| E015 | glicko | 2025 → 2024 | 0.5984 | +0.0286 (0.0289) | 72 | +11.0% [-14.7%, +51.2%] |
| E015 | glicko | 2025+2026 → 2024 | 0.5967 | +0.0269 (0.0288) | 49 | +15.3% [-30.2%, +86.0%] |
| E016 | hold | 2026 → 2025 | 0.6504 | +0.0161 (0.0275) | 39 | +32.7% [-20.0%, +75.2%] |
| E016 | hold | 2025 → 2026 | 0.6369 | +0.0879 (0.0340) | 105 | -6.7% [-55.0%, +7.2%] |
| E016 | hold | 2025 → 2024 | 0.6048 | +0.0350 (0.0300) | 73 | +7.7% [-18.3%, +47.8%] |
| E016 | hold | 2025+2026 → 2024 | 0.5997 | +0.0299 (0.0300) | 45 | +14.4% [-29.2%, +118.5%] |
| E017 | logreg | 2026 → 2025 | 0.6283 | -0.0060 (0.0027) | 4 | -100.0% [-100.0%, -100.0%] |
| E017 | logreg | 2025 → 2026 | 0.5922 | +0.0432 (0.0305) | 72 | +11.1% [-57.4%, +18.0%] |
| E017 | logreg | 2025 → 2024 | 0.6275 | +0.0577 (0.0351) | 45 | +13.6% [-19.5%, +61.2%] |
| E017 | logreg | 2025+2026 → 2024 | 0.5892 | +0.0194 (0.0221) | 19 | +4.0% [-58.3%, +60.0%] |
| E018 | logreg | 2026 → 2025 | 0.6326 | -0.0016 (0.0208) | 37 | +10.5% [-36.0%, +38.5%] |
| E018 | logreg | 2025 → 2026 | 0.5942 | +0.0452 (0.0230) | 59 | +25.1% [-43.6%, +45.8%] |
| E018 | logreg | 2025 → 2024 | 0.6035 | +0.0337 (0.0300) | 46 | +15.4% [-11.4%, +72.4%] |
| E018 | logreg | 2025+2026 → 2024 | 0.5934 | +0.0236 (0.0226) | 54 | +16.4% [-16.5%, +66.7%] |
| E020 | blend-krimp | 2026 → 2025 | 0.6306 | -0.0036 (0.0026) | 9 | +50.0% [-14.3%, +95.0%] |
| E020 | blend-krimp | 2025 → 2026 | 0.5741 | +0.0251 (0.0172) | 67 | +10.4% [-67.9%, +29.2%] |
| E020 | blend-krimp | 2025 → 2024 | 0.5784 | +0.0087 (0.0176) | 49 | +5.1% [-29.2%, +67.5%] |
| E020 | blend-krimp | 2025+2026 → 2024 | 0.5705 | +0.0008 (0.0089) | 19 | +42.1% [-30.0%, +220.0%] |
| E021 | platt | 2026 → 2025 | 0.6198 | -0.0145 (0.0150) | 0 | – – |
| E021 | platt | 2025 → 2026 | 0.5697 | +0.0207 (0.0144) | 79 | -3.2% [-40.5%, +11.4%] |
| E021 | platt | 2025 → 2024 | 0.6000 | +0.0302 (0.0247) | 63 | +3.7% [-21.3%, +46.3%] |
| E021 | platt | 2025+2026 → 2024 | 0.5970 | +0.0272 (0.0229) | 71 | +3.0% [-20.5%, +45.3%] |
| E022 | isotoon | 2026 → 2025 | 0.6402 | +0.0059 (0.0170) | 12 | +52.8% [-27.8%, +116.7%] |
| E022 | isotoon | 2025 → 2026 | 0.6085 | +0.0595 (0.0304) | 45 | -22.3% [-74.6%, +25.3%] |
| E022 | isotoon | 2025 → 2024 | 0.6592 | +0.0894 (0.0339) | 51 | -10.4% [-29.3%, +38.1%] |
| E022 | isotoon | 2025+2026 → 2024 | 0.6289 | +0.0591 (0.0244) | 59 | -19.7% [-35.4%, +23.7%] |
| E023 | isotoon | 2026 → 2025 | 0.6902 | +0.0559 (0.0443) | 41 | +11.9% [-44.5%, +60.6%] |
| E023 | isotoon | 2025 → 2026 | 0.6601 | +0.1111 (0.0478) | 76 | +12.5% [-47.2%, +28.5%] |
| E023 | isotoon | 2025 → 2024 | 0.6177 | +0.0480 (0.0301) | 52 | -4.0% [-36.0%, +69.3%] |
| E023 | isotoon | 2025+2026 → 2024 | 0.6149 | +0.0451 (0.0307) | 47 | +1.6% [-61.0%, +77.6%] |
| E024 | blend-krimp | 2026 → 2025 | 0.6280 | -0.0062 (0.0035) | 7 | +210.7% [+140.0%, +387.5%] |
| E024 | blend-krimp | 2025 → 2026 | 0.5658 | +0.0168 (0.0148) | 46 | +33.1% [-55.0%, +60.8%] |
| E024 | blend-krimp | 2025 → 2024 | 0.5772 | +0.0074 (0.0160) | 28 | +56.2% [+8.8%, +154.5%] |
| E024 | blend-krimp | 2025+2026 → 2024 | 0.5711 | +0.0013 (0.0082) | 13 | +53.8% [-38.9%, +262.5%] |
| E025 | elo | 2026 → 2025 | 0.6865 | +0.0522 (0.0374) | 38 | +38.9% [-39.5%, +107.5%] |
| E025 | elo | 2025 → 2026 | 0.6506 | +0.1016 (0.0338) | 101 | -4.6% [-46.9%, +3.8%] |
| E025 | elo | 2025 → 2024 | 0.6344 | +0.0646 (0.0333) | 70 | -1.5% [-21.3%, +34.1%] |
| E025 | elo | 2025+2026 → 2024 | 0.6361 | +0.0663 (0.0312) | 50 | +6.2% [-31.1%, +77.6%] |
| E026 | glicko | 2026 → 2025 | 0.6739 | +0.0396 (0.0335) | 36 | +22.4% [-28.0%, +59.0%] |
| E026 | glicko | 2025 → 2026 | 0.6454 | +0.0964 (0.0347) | 122 | -2.0% [-48.0%, +9.4%] |
| E026 | glicko | 2025 → 2024 | 0.6002 | +0.0304 (0.0309) | 81 | +8.3% [-15.0%, +44.2%] |
| E026 | glicko | 2025+2026 → 2024 | 0.5967 | +0.0269 (0.0288) | 49 | +15.3% [-30.2%, +86.0%] |

## E027: inzetbeleid in euro's (bets van de marktblend)

¼-Kelly met start €100; vaste inzet met hoogstens €50 per week (ma–zo, speeldatum). Drawdown = grootste daling vanaf een piek.

| Train → test | Soort | Bets | Inzet 1 (eenheden) | ¼-Kelly eind (drawdown) | €2 vast: winst (drawdown, weken budget op) | €3 vast: winst (drawdown, weken budget op) | €5 vast: winst (drawdown, weken budget op) |
|---|---|---|---|---|---|---|---|
| 2024 → 2025 | walk-forward | 39 | +12.88 | €108.60 (€3.36) | €+25.76 (€12.50, 0; 0 overgeslagen) | €+11.28 (€18.75, 1; 5 overgeslagen) | €-3.70 (€31.25, 1; 11 overgeslagen) |
| 2024+2025 → 2026 | walk-forward | 49 | +17.53 | €129.68 (€35.13) | €+35.06 (€18.60, 0; 0 overgeslagen) | €+41.49 (€27.90, 1; 5 overgeslagen) | €+5.40 (€45.00, 2; 13 overgeslagen) |
| 2026 → 2025 | richting | 9 | +4.50 | €101.92 (€0.57) | €+9.00 (€6.00, 0; 0 overgeslagen) | €+13.50 (€9.00, 0; 0 overgeslagen) | €+22.50 (€15.00, 0; 0 overgeslagen) |
| 2025 → 2026 | richting | 67 | +7.00 | €90.43 (€70.55) | €+8.60 (€33.00, 1; 6 overgeslagen) | €+13.14 (€49.50, 1; 15 overgeslagen) | €-55.00 (€95.00, 3; 27 overgeslagen) |
| 2025 → 2024 | richting | 49 | +2.50 | €97.32 (€36.50) | €+5.00 (€23.60, 0; 0 overgeslagen) | €+4.50 (€38.40, 1; 4 overgeslagen) | €+51.50 (€50.00, 3; 16 overgeslagen) |
| 2025+2026 → 2024 | richting | 19 | +8.00 | €105.57 (€9.26) | €+16.00 (€18.00, 0; 0 overgeslagen) | €+24.00 (€27.00, 0; 0 overgeslagen) | €+40.00 (€45.00, 0; 0 overgeslagen) |

## E028: setstanden (log-loss van de exacte eindstand in sets)

Marktkans (proportioneel) → legverschil → exacte set-DP, tegen een binomiale verdeling met dezelfde wedstrijdkans. Niets afgestemd (hold 0,60).

| Train → test | Soort | n | Set-DP | Binomiaal | Verschil (se) | Log-loss winnaar |
|---|---|---|---|---|---|---|
| 2024 → 2025 | walk-forward | 94 | 1.8514 | 1.8549 | -0.0035 (0.0028) | 0.6343 |
| 2024+2025 → 2026 | walk-forward | 126 | 1.7001 | 1.6942 | +0.0058 (0.0024) | 0.5490 |
| 2026 → 2025 | richting | 94 | 1.8514 | 1.8549 | -0.0035 (0.0028) | 0.6343 |
| 2025 → 2026 | richting | 126 | 1.7001 | 1.6942 | +0.0058 (0.0024) | 0.5490 |
| 2025 → 2024 | richting | 94 | 1.7169 | 1.7124 | +0.0045 (0.0027) | 0.5698 |
| 2025+2026 → 2024 | richting | 94 | 1.7169 | 1.7124 | +0.0045 (0.0027) | 0.5698 |

## Hypothesen, criteria en beoordeling

### E001: Markt (proportioneel)

- Hypothese (2026-10-29): Referentie. De proportioneel genormaliseerde slotodds zijn de benchmark.
- Criterium: controle: geen criterium; dient als referentie → n.v.t. (geen toetsbaar criterium (controle))
- Na test aangepast: nee
- Status: ok

### E002: Markt vlakker (logit·a, a op train)

- Hypothese (2026-10-29): Controle: als dit wint van de markt, komt winst van modellen die de markt 'vlakker' maken uit de favourite-longshot-kanteling en niet uit informatie.
- Criterium: controle: geen criterium; dient als referentie → n.v.t. (geen toetsbaar criterium (controle))
- Na test aangepast: nee
- Status: ok

### E003: Blind op de underdog

- Hypothese (2026-10-29): Controle: altijd de underdog, inzet 1. Laat zien hoeveel ROI een jaar met veel upsets 'gratis' geeft.
- Criterium: controle: geen criterium; dient als referentie → n.v.t. (geen toetsbaar criterium (controle))
- Na test aangepast: nee
- Status: ok

### E004: Blind op de favoriet

- Hypothese (2026-10-29): Controle: altijd de favoriet, inzet 1. Verwacht ongeveer −marge.
- Criterium: controle: geen criterium; dient als referentie → n.v.t. (geen toetsbaar criterium (controle))
- Na test aangepast: nee
- Status: ok

### E005: Munt (p = 0.5)

- Hypothese (2026-10-29): Controle: log-loss ln 2 = 0.6931. Elk model moet hier ruim onder zitten.
- Criterium: controle: geen criterium; dient als referentie → n.v.t. (geen toetsbaar criterium (controle))
- Na test aangepast: nee
- Status: ok

### E006: Vormmodel

- Hypothese (2026-10-29): Het vormmodel voorspelt niet beter dan de markt (verwachting op basis van eerdere runs).
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0118 (se 0.0186); WK2026: +0.0235 (se 0.0149))
- Na test aangepast: nee (De testcijfers van dit model waren al bekend uit resultaten/vergelijking.md vóór het register bestond; dit is een herregistratie, geen vooraf vastgelegde toets.)
- Status: ok

### E007: Ratingmodel (BT op legs)

- Hypothese (2026-10-29): Bradley-Terry op legs voorspelt niet beter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0545 (se 0.0535); WK2026: +0.0746 (se 0.0334))
- Na test aangepast: ja (Grid is twee keer verbreed na het zien van train- en testresultaten (docs/model-rating.md). De testcijfers van dit model waren al bekend uit resultaten/vergelijking.md vóór het register bestond; dit is een herregistratie, geen vooraf vastgelegde toets.)
- Status: ok

### E008: Rating + Platt

- Hypothese (2026-10-29): Platt verandert weinig omdat k al op log-loss is afgestemd.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0431 (se 0.0482); WK2026: +0.0741 (se 0.0332))
- Na test aangepast: nee (De testcijfers van dit model waren al bekend uit resultaten/vergelijking.md vóór het register bestond; dit is een herregistratie, geen vooraf vastgelegde toets.)
- Status: ok

### E009: Rating + markt (logistisch)

- Hypothese (2026-10-29): De combinatie komt dicht bij de markt maar niet eronder.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0101 (se 0.0211); WK2026: +0.0120 (se 0.0134))
- Na test aangepast: nee (De testcijfers van dit model waren al bekend uit resultaten/vergelijking.md vóór het register bestond; dit is een herregistratie, geen vooraf vastgelegde toets.)
- Status: ok

### E010: Rating + averages

- Hypothese (2026-10-29): Averages bovenop de rating helpen een beetje, niet genoeg om de markt te verslaan.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0545 (se 0.0535); WK2026: +0.0693 (se 0.0328))
- Na test aangepast: nee (De testcijfers van dit model waren al bekend uit resultaten/vergelijking.md vóór het register bestond; dit is een herregistratie, geen vooraf vastgelegde toets.)
- Status: ok

### E011: BT, halfwaarde vast 180 d

- Hypothese (2026-10-29): Sterk tijdsverval (180 d) is slechter dan geen verval, omdat recente data grotendeels ontbreekt (paywall).
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0355 (se 0.0302); WK2026: +0.0772 (se 0.0322))
- Na test aangepast: nee
- Status: ok

### E012: BT, halfwaarde vast 365 d

- Hypothese (2026-10-29): Halfwaarde 365 d zit tussen 180 d en geen verval in; niet beter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0548 (se 0.0434); WK2026: +0.0630 (se 0.0309))
- Na test aangepast: nee
- Status: ok

### E013: BT, halfwaarde vast 730 d

- Hypothese (2026-10-29): Halfwaarde 730 d is ongeveer gelijk aan geen verval; niet beter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0519 (se 0.0478); WK2026: +0.0676 (se 0.0314))
- Na test aangepast: nee
- Status: ok

### E014: Elo op legs/uitslag

- Hypothese (2026-10-29): Elo (sequentieel, recente wedstrijden tellen vanzelf zwaarder) is vergelijkbaar met BT en niet beter dan de markt; de marge-variant (legs) wordt op train gekozen boven alleen de uitslag.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0192 (se 0.0411); WK2026: +0.0919 (se 0.0323))
- Na test aangepast: nee
- Status: ok

### E015: Glicko-achtig (variantie per speler)

- Hypothese (2026-10-29): Onzekerheid per speler maakt voorspellingen voor spelers met weinig data vlakker; daardoor betere kalibratie (helling dichter bij 1) dan Elo, maar nog steeds niet beter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: -0.0031 (se 0.0279); WK2026: +0.0847 (se 0.0339))
- Na test aangepast: nee
- Status: ok

### E016: Legmodel met vrije hold-kans

- Hypothese (2026-10-29): De hold-basis maakt nauwelijks uit (< 0.002 log-loss); geen verbetering t.o.v. rating met hold 0.60.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0521 (se 0.0523); WK2026: +0.0737 (se 0.0331))
- Na test aangepast: nee
- Status: ok

### E017: Logistische regressie met markt (L2)

- Hypothese (2026-10-29): Met de markt onbestraft en de andere features gekrompen (lambda via CV op train) komt het model op of iets boven de markt, niet significant eronder.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: -0.0015 (se 0.0020); WK2026: +0.0007 (se 0.0087))
- Na test aangepast: nee
- Status: ok

### E018: Logistische regressie zonder markt (L2)

- Hypothese (2026-10-29): Een lineaire combinatie van rating en vorm is beter dan elk afzonderlijk, maar slechter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0119 (se 0.0256); WK2026: +0.0343 (se 0.0206))
- Na test aangepast: nee
- Status: ok

### E019: Kleine GBM

- Hypothese (2026-10-29): Niet gedraaid.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → n.v.t. (niet gedraaid: geen sklearn (en geen grote pakketten installeren))
- Na test aangepast: nee
- Status: niet gedraaid

### E020: Marktblend met krimp op b

- Hypothese (2026-10-29): Krimp van b naar 0 (lambda via CV op train) brengt de blend dichter bij de markt dan rating+markt, maar niet significant eronder.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: -0.0017 (se 0.0056); WK2026: +0.0120 (se 0.0134))
- Na test aangepast: nee
- Status: ok

### E021: Vorm + Platt

- Hypothese (2026-10-29): Platt op het vormmodel verandert weinig (k is al op log-loss afgestemd).
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0126 (se 0.0187); WK2026: +0.0230 (se 0.0148))
- Na test aangepast: nee
- Status: ok

### E022: Vorm + isotoon

- Hypothese (2026-10-29): Isotone kalibratie overfit bij ~100 wedstrijden; slechter dan Platt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0409 (se 0.0347); WK2026: +0.0406 (se 0.0204))
- Na test aangepast: nee
- Status: ok

### E023: Rating + isotoon

- Hypothese (2026-10-29): Isotone kalibratie op de rating overfit; slechter dan rating-platt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0605 (se 0.0543); WK2026: +0.0940 (se 0.0485))
- Na test aangepast: nee
- Status: ok

### E024: Marktblend met Shin als marktinput

- Hypothese (2026-10-29): Shin als marktinput in de blend verandert de log-loss nauwelijks t.o.v. E020 (proportioneel), omdat a op train de schaal toch al bijstelt; het verschil met E020 is < 0,002 per wedstrijd.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: -0.0019 (se 0.0111); WK2026: +0.0109 (se 0.0130))
- Na test aangepast: nee
- Status: ok

### E025: Elo met breder K-grid

- Hypothese (2026-10-29): In E014 lag het optimum op de rand (K=0,005, k=0,5). Met een breder grid verbetert Elo iets op train, maar blijft het op test slechter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0192 (se 0.0411); WK2026: +0.0936 (se 0.0329))
- Na test aangepast: nee
- Status: ok

### E026: Glicko met breder v0-grid

- Hypothese (2026-10-29): In E015 lag het optimum op de rand (v0=0,4). Een grotere v0 helpt op train, maar Glicko blijft op test slechter dan de markt.
- Criterium: walk-forward log-loss lager dan de markt (proportioneel) in beide testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: +0.0195 (se 0.0320); WK2026: +0.0757 (se 0.0319))
- Na test aangepast: nee
- Status: ok

### E027: Inzetbeleid op de bets van E020 (euro)

- Hypothese (2026-10-29): Met dezelfde bets als E020 geeft ¼-Kelly (start €100) een kleinere maximale drawdown dan vaste inzet, maar de ROI-cijfers zijn met 2 testjaren ruis. Bij €2–5 vaste inzet raakt het weekbudget van €50 in de eerste WK-week op.
- Criterium: beschrijvend: eindstand, maximale drawdown en aantal weken met een uitgeput budget in euro's (geen toets) → n.v.t. (geen toetsbaar criterium (controle of beschrijvend))
- Na test aangepast: nee
- Status: ok

### E028: Setstanden: exacte set-DP tegen een naïeve verdeling

- Hypothese (2026-10-29): De exacte set-DP (wisselende beginner, beslissende set) geeft een lagere log-loss op de exacte setstand dan een binomiale setverdeling met dezelfde wedstrijdkans, maar het verschil is klein.
- Criterium: log-loss van de setstand (DP) lager dan naïef in beide walk-forward-testjaren (2025 en 2026), verschil > 1 se → niet gehaald (WK2025: -0.0035 (se 0.0028); WK2026: +0.0058 (se 0.0024))
- Na test aangepast: nee
- Status: ok

