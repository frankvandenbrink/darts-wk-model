# Review: terugtest van het dartsmodel voor het PDC WK (Bull)

## 1. Samenvatting

Het model voorspelt slechter dan de markt, ook op de data waarop het is afgesteld. Op WK2026 (train, 126 wedstrijden) is de log-loss 0.567 tegen 0.549 voor de markt. De testwinst op WK2025 (+52% ROI bij drempel 1.05) komt vooral doordat het model bijna altijd op de underdog bet (53 van de 56 bets) in een jaar waarin favorieten opvallend vaak verloren. Draai je de volgorde om, zodat je afstemt op 2025 en test op het latere 2026, dan is de ROI −27% over 68 bets. Een logistische regressie laat zien dat het model niets toevoegt aan de marktkans (LR-statistiek 0.17 bij 1 vrijheidsgraad). De bouw van de set/match-simulatie is goed. De zwakke plekken zitten in de vormmaat (geen correctie voor tegenstander of niveau, geen krimp bij weinig data) en in de evaluatie. Bulls conclusie "geen aantoonbaar voordeel" klopt, en het bewijs daarvoor is sterker dan hij zelf opschrijft.

## 2. Fouten en risico's in de code/methode

**2.1 Train en test staan in de verkeerde tijdsvolgorde. Ernst: hoog**
- *Bewijs:* `TRAIN = [2026]`, `TEST = [2025]` (r. 34–35). In werkelijkheid stem je nooit af op de toekomst. Ik heb de pijplijn omgekeerd gedraaid met de functies `evalueer` en de grid uit het script. Afstemmen op 2025 kiest w=0.25, L=12, k=0.04, kc=0. De ROI op 2025 is bij alle drempels positief en het hoogst bij 1.10 (+50.9% over 50 bets), dus die drempel wordt gekozen. Op 2026 geeft dat 68 bets met ROI −26.9%. Bij drempel 1.05 is het −20.3% over 81 bets, bij 1.00 −11.4% over 101 bets. De log-loss op 2026 wordt 0.5680, tegen 0.5490 voor de markt.
- Daarbij komt dat het 12-maandenvenster van 2026 (2024-12-10 t/m 2025-12-10) het hele WK2025, het testtoernooi, als vormdata bevat.
- *Fix:* toets alleen walk-forward: afstemmen op jaren tot en met t−1, toetsen op jaar t. Rapporteer beide richtingen zolang er maar twee jaren zijn.

**2.2 De drempelkeuze en de rapportage kloppen niet met elkaar. Ernst: hoog**
- *Bewijs:* alle zes ROI's op train zijn negatief (−6.8% tot −26.8%, `drempels_train`). Toch kiest `max(geldig, key=...)` (r. 299) drempel 1.00. Dat is "het minst slechte", terwijl de juiste beslissing hier "niet wedden" is.
- CONTEXT.md noemt bovendien als hoofdresultaat drempel 1.05 (test +51.7%). De code koos 1.00 (test 75 bets, +34.9%). Daarmee wordt de achteraf gunstigere variant gerapporteerd. De code berekent 1.05 altijd mee (r. 304), en dat nodigt hiertoe uit.
- *Fix:* leg vooraf één drempel en de stopregel vast: alleen wedden als de ROI op train positief is en het betrouwbaarheidsinterval boven 0 ligt. Rapporteer de gekozen drempel als hoofdresultaat.

**2.3 De vormmaat corrigeert niet voor tegenstander of niveau en krimpt niet bij weinig data. Ernst: hoog**
- *Bewijs:* `organStat=All` (r. 79) mengt alle toernooien, en `vorm()` (r. 220–226) controleert alleen het aantal darts in het korte venster. Het lange venster wordt ongefilterd gebruikt.
- Voorbeeld: Cristo Reyes heeft in 2026 een 12-maandengemiddelde van 97.6 over maar 376 darts. Daardoor geeft het model Gian van Veen 0.51 tegen 0.91 bij de markt. Dat is de grootste afwijking van 2026.
- Een gemiddelde uit lagere toernooien telt even zwaar als een gemiddelde tegen de top. Dit leid ik af uit de opzet: de JSON bevat alleen geaggregeerde cijfers, dus per speler kon ik het niet nagaan.
- *Fix:* krimp naar een prior (zie 4.2) en gebruik bij voorkeur ratings op wedstrijdniveau.

**2.4 Het model is systematisch vlakker dan de markt. Ernst: hoog (gevolg van 2.3)**
- *Bewijs:* de helling van logit(model) op logit(markt) is 0.70 in 2025 en 0.78 in 2026. De standaardafwijking van logit(p) is 0.66 tegen 0.86 (2025) en 0.84 tegen 0.97 (2026).
- In de kalibratie op train, kansbak 80–90%, wonnen favorieten 94.1% van de wedstrijden. Het model gaf gemiddeld 84.7%, de markt 89.1%.
- Gevolg: bij drempel 1.05 is er in 2026 7 keer tegen Littler gewed en in 2025 6 keer. Van de bets gaan 74/78 (train) en 53/56 (test) naar de underdog, met een gemiddelde odd van 5.90 en 5.38.
- k is goed bepaald: de log-loss heeft in beide jaren een minimum bij k=0.04. De vlakheid komt dus van de ruis in de input, niet van een slecht gekozen k.

**2.5 De ROI rekent met odds die Bull niet kan krijgen. Ernst: middel tot hoog**
- *Bewijs:* volgens CONTEXT.md zijn de odds gemiddelde slotodds van bookmakers op Oddsportal. Bull bet bij TOTO. TOTO-odds staan niet in de data, dus de werkelijke marge en afwijking zijn onbekend.
- Daarnaast rekent de terugtest met slotodds. Die ken je pas vlak voor de wedstrijd, en voor latere rondes zit er informatie uit het lopende toernooi in. Het model gebruikt die informatie niet (dat is geen datalek, maar wel een nadeel).
- *Fix:* sla vanaf nu bij elke bet de TOTO-odd en het tijdstip op. Rapporteer de ROI eventueel met een verslechtering van de odds als gevoeligheidsanalyse.

**2.6 Margecorrectie: proportioneel versus power/Shin. Ernst: laag**
- *Bewijs:* `markt_p` (r. 236–238) normaliseert proportioneel. De mediane overround is 4.5% (2025) en 4.3% (2026), met een maximum van 5.9%.
- Met de power-methode verschuift de kans maximaal 0.032, met Shin maximaal 0.019. De log-loss van de markt per methode:

  | Jaar | Proportioneel | Power | Shin |
  |---|---|---|---|
  | 2025 | 0.6343 | 0.6389 | 0.6371 |
  | 2026 | 0.5490 | 0.5511 | 0.5498 |

- Proportioneel is hier dus de scherpste benchmark, en de conclusie verandert niet. De bets zelf gebruiken de ruwe odds (`p*odd`, r. 253), dus de winst-en-verliesberekening wordt niet door de margecorrectie beïnvloed.
- Favourite-longshot bias raakt vooral de strategie: die bet bijna alleen longshots, en daar zit de bias als die er is. Blind op de underdog wedden gaf in 2026 +1.2% (124 wedstrijden zonder gelijke odds) en in 2025 +25.0%. Met twee jaren is daar dus geen stabiele bias in te zien.
- *Fix:* gebruik Shin of power als benchmark naast proportioneel. Belangrijker is 2.5.

**2.7 Set/match-simulatie. Ernst: laag**
- **Format:** klopt. Sets zijn first-to-3 legs. De beslissende set vraagt twee legs verschil met sudden death bij 5-5 (`set_prob`, r. 197–200). Dat komt overeen met de formatbeschrijving in `wiki_2026.txt`.
- **Aantal sets per ronde:** ik heb per ronde nagegaan dat het aantal benodigde sets overal consistent is: R1/R2 3, R3/R4 4, QF 5, SF 6, F 7.
- **Wie begint:** de beginner wisselt per leg en per set, en de match wordt gemiddeld over wie de bull wint (r. 218). Dat is correct.
- **Sudden-death-leg:** het script laat de wissel doorlopen. Naar mijn weten wordt voor die leg opnieuw om de bull gegooid; de wiki-tekst zegt daar niets over. Ik heb het effect doorgerekend: het verschil in matchkans is maximaal 0.00017, dus te verwaarlozen.
- **`setsnodig`:** wordt afgeleid uit de uitslag (`max(sets1, sets2)`, r. 181). Dat werkt alleen zolang er geen opgaves zijn. Leid het beter af uit de ronde.
- **Vaste hold-kans:** `H = logit(0.60)` hangt niet af van het niveau. Bij hold-kansen van 0.55 tot 0.70 verandert de beste log-loss met hooguit 0.0005. Het throw-deel van het model is dus niet geschat maar wel onschadelijk. Het model is in feite één parameter: k op het verschil in 12-maandengemiddelde, want w=0 en kc=0.
- **Aanname:** legs worden behandeld als onafhankelijke kansexperimenten met een vaste hold-kans per wedstrijd. Ik heb niet gecontroleerd hoe goed die aanname de werkelijke setstanden beschrijft (zie 4.6).

**2.8 Lookahead in de vormcijfers. Ernst: laag (geen lek gevonden)**
- *Bewijs:* `tot` is 2024-12-14 en 2025-12-10, precies de dag vóór de WK-start (15-12-2024 en 11-12-2025; de laatste datum staat ook in de wiki). Dat geldt voor alle 12 JSON-bestanden.
- In-toernooidata wordt niet gebruikt: `model_p` gebruikt alleen `vorm()`. De kolommen `avg1_wedstrijd`/`avg2_wedstrijd` (gemiddelde in de wedstrijd zelf) staan wel in de dataset-CSV's. Dat is een valkuil voor later gebruik.
- Ik kan niet nagaan of Dartsorakel `dateTo` filtert op wedstrijddatum of op toernooidatum.
- *Fix:* verwijder de `*_wedstrijd`-kolommen of geef ze een duidelijke naam. Voeg een assert toe dat `tot` kleiner is dan de WK-start.

**2.9 Namen koppelen. Ernst: laag nu, middel voor nieuwe jaren**
- *Bewijs:* `op_match` (r. 131–137) negeert initialen en gebruikt een substring-match op tekens, dus "Smith" past op elke Smith. `vind_speler` gebruikt difflib met cutoff 0.85.
- Ik heb alles nagelopen. Elke wiki-wedstrijd koppelt aan precies één unieke Oddsportal-wedstrijd en er zijn geen initiaal-conflicten. Er zijn vier dubbele Oddsportal-rijen: Dobey–Price in 2025, en Van Veen–Soutar, Wright–Merk en Searle–Clayton in 2026. Die hebben identieke odds maar een andere datum, waarschijnlijk door overlap tussen pagina's. De datums uit Oddsportal zijn dus onbetrouwbaar, maar hier onschadelijk.
- Er zijn drie koppelingen die niet exact zijn, en alle drie kloppen: Xiaochen Zong → zong xiaochen, Man Lok Leung → hugo leung man lok (via de alias), David Cameron → dave cameron (via difflib).
- In de Dartsorakel-data komen dubbele genormaliseerde namen voor: 12 in het 12-maandenbestand van 2025 en 8 in dat van 2026. Bij WK-spelers komt dat niet voor. `load_orakel` zou bij zo'n botsing de ene speler stilletjes overschrijven met de andere.
- Het slug `pdc-world-championship` voor 2026 (r. 31) wijst na de start van WK2027 naar een ander seizoen als je opnieuw ophaalt.
- *Fix:* eis dat de initiaal overeenkomt, dwing een één-op-één-koppeling af met een assert, log alle difflib-matches, koppel op `player_key` en zet het seizoen expliciet in het slug.

**2.10 Bootstrap. Ernst: middel**
- *Bewijs:* `bootstrap_roi` trekt bets onafhankelijk (iid). Daarmee negeert hij de keuze van parameters en drempel en de correlatie binnen een toernooi.
- Een geclusterde bootstrap per ronde geeft voor test bij drempel 1.05 een 90%-interval van [−0.035, 0.780] in plaats van [0.054, 0.997]. Bij drempel 1.00 wordt het [−0.046, 0.584] in plaats van [0.004, 0.713]. Met 7 rondes is ook dat interval nog te optimistisch.
- *Fix:* toets tegen een nulmodel waarin de marktkansen kloppen (zie 3) en bootstrap per toernooi zodra er meer toernooien zijn.

## 3. Statistische valkuilen

- **Steekproefgrootte:** een bet heeft een standaardafwijking van 1.7 tot 2.1 units, omdat het vooral longshots zijn. De standaardfout van de ROI is daardoor ongeveer 0.28 bij 56 bets en 0.19 bij 78 bets. Om een voordeel van 5% ROI op 2 standaardfouten te kunnen aantonen zijn ongeveer 4.400 tot 7.100 bets nodig. Twee WK's leveren er ongeveer 130 op.
- **Gecorreleerde bets:** in 2025 wonnen favorieten 59 van de 94 wedstrijden, terwijl de marktkansen er 67.5 voorspelden (kans op zo weinig of minder ≈ 0.03). In 2026 was dat 91 tegen 91.8 verwacht. Een upsetjaar treft alle underdog-bets tegelijk, en er wordt herhaaldelijk tegen dezelfde speler gewed (Littler 7 en 6 keer). De effectieve steekproef is daarmee eerder "2 toernooien" dan "134 bets".
- **Nulmodel:** als de marktkansen kloppen, is de verwachte ROI van dezelfde bets ongeveer −4%. De kans op +51.7% of meer is dan 0.029, en op +34.9% of meer 0.044. Dat ziet er significant uit, maar deze toets neemt aan dat de uitslagen onafhankelijk zijn, terwijl 2025 als geheel een uitschieter was. Blind op de underdog wedden gaf dat jaar al +25%.
- **Selectie binnen de underdogs is ruis:** de underdog-bets van het model verdienden in 2025 +54.5% (28.89/53), tegen +25% voor alle underdogs. In 2026 was het −13.7% (−10.14/74), tegen +1.2 à 2.7% voor alle underdogs. Het teken draait om.
- **Model tegen markt:** het verschil in log-loss per wedstrijd is −0.016 met standaardfout 0.017 (t=−0.97) in 2025 en +0.018 met standaardfout 0.014 (t=+1.25) in 2026. Dat is in geen van beide jaren significant.
  - Een logistische regressie van de uitslag op logit(model) en logit(markt) over beide jaren geeft b_model = 0.20 (standaardfout 0.50). Het model voegt dus niets toe aan de markt (LR = 0.17).
- **Multiple testing:** de grid heeft 320 combinaties, er zijn 6 drempels en 2 jaren, er is een extra drempel (1.05) gerapporteerd naast de gekozen, en er zijn blind-underdog-varianten bekeken. Bovendien liggen de modelkeuzes in de code vast (h=0.60, minimumaantallen 300/100 darts, fallback 80/33). Uit de bestanden is niet te zien of die keuzes vóór of na het bekijken van de resultaten zijn gemaakt.
- **Conclusies:** dat de test beter is dan de train komt hier door het testjaar, niet door het model. Ook in-sample verliest het model van de markt. Dat is het sterkste signaal in de hele terugtest.

## 4. Voorstellen voor een beter model (geprioriteerd)

1. **Ratings op wedstrijdniveau met correctie voor tegenstandersterkte, gecombineerd met de markt.** Dit zou ik als eerste bouwen.
   - *Opzet:* Elo/Glicko of Bradley-Terry, bij voorkeur op legs (legs gewonnen tegen legs verloren per wedstrijd), over alle PDC-wedstrijden vóór elk WK (Pro Tour, European Tour, majors).
   - *Waarom eerst:* dit pakt de hoofdoorzaak aan (2.3/2.4: ruwe gemiddelden zonder tegenstanderscorrectie maken het model vlak). Bovendien kun je het dan toetsen op alle PDC-toernooien met odds, en niet alleen op twee WK's. Dat laatste is nodig vanwege de steekproefgrootte in sectie 3.
   - *Data:* wedstrijduitslagen met legstanden. Dartsorakel toont uitslagen per toernooi en speler, maar de huidige API-call levert alleen aggregaten. Naar mijn weten is daar scrapen voor nodig (controleer de gebruiksvoorwaarden). Voor majors staan uitslagen ook op Wikipedia.
   - *Combineren met de markt:* combineer niet blind, maar via logit p = a·logit(markt) + b·logit(rating), geschat walk-forward. Alleen als b consistent groter is dan 0 is er een reden om te wedden.

2. **Bayesiaans krimpen naar het gemiddelde.** Dit is een snelle winst binnen het huidige model.
   - *Opzet:* gem_krimp = (n·gem + n0·μ)/(n + n0), met n het aantal darts (staat al in `n_avg*_12m`), μ het veldgemiddelde of een tourgemiddelde, en n0 afgestemd op log-loss.
   - *Effect:* dit lost gevallen als Reyes (376 darts) direct op.
   - *Data:* al aanwezig. Kosten: een uur werk.

3. **Kalibratie en combinatie met de markt.**
   - *Platt-schaling:* een logistische fit op logit(p) heeft maar twee parameters en past bij deze kleine n.
   - *Isotonic regressie:* vraagt honderden tot duizenden wedstrijden, dus pas zinvol na voorstel 1.
   - *Data:* aanwezig.

4. **Leg-model met throw.**
   - *Opzet:* schat per speler een hold- en break-kans (of leg-ratings met een throw-term) in plaats van de vaste h=0.60.
   - *Effect:* het directe winsteffect is klein, want de gevoeligheid voor h was minder dan 0.001 in log-loss. Het is wel nodig voor de markten onder 6.
   - *Data:* legs met wie begon. Controleer of Dartsorakel een hold/break-statistiek heeft onder een andere `rankKey`; dat weet ik niet zeker. Zo niet, dan schat je het uit leguitslagen per wedstrijd.

5. **Inzetgrootte.**
   - Vaste inzet op longshots geeft veel variantie: een standaardafwijking van ongeveer 2 units per bet.
   - Kelly met een fractie (¼ à ½) op de gecombineerde kans zet automatisch weinig in als model en markt nauwelijks verschillen, en bij een afwezig voordeel nul.
   - Binnen €50 per week: stel een maximum per bet in en houd een logboek bij.

6. **Andere markten: sethandicap, totaal sets, correct score.**
   - De set/leg-recursie levert de hele verdeling over setstanden al. Die kun je nu al zonder odds toetsen op de wiki-setstanden (`sets1`/`sets2`): voorspelde tegen werkelijke frequentie van 3-0, 3-1, 3-2, enzovoort.
   - Om deze markten te betten zijn historische odds nodig. Of Oddsportal die voor darts per toernooi heeft, weet ik niet zeker. TOTO-historie is voor zover ik weet niet vrij beschikbaar, dus zelf loggen.
   - Deze markten hebben vaak een hogere marge. Pas zinvol als het model op de winnaarsmarkt (moneyline) minstens gelijk speelt met de markt.

Voorbereidend en goedkoop: maak de evaluatie walk-forward, voeg meer jaren en toernooien toe en log vanaf nu je eigen TOTO-odds. Zonder die stap is geen enkel modelvoorstel te beoordelen.

## 5. Oordeel over de conclusie van Bull

"Geen aantoonbaar voordeel" klopt, en is eerder te voorzichtig dan te streng geformuleerd:
- Het model verliest in-sample van de markt.
- In de juiste tijdsvolgorde (afstemmen op 2025, toetsen op 2026) is de ROI −27%.
- Het model voegt statistisch niets toe aan de marktkans (b_model 0.20, standaardfout 0.50).

Zijn deelconclusies kloppen ook:
- **Upsetjaar 2025:** favorieten wonnen 59 van de 94 tegen 67.5 verwacht (kans ≈ 0.03), en blind op de underdog wedden gaf +25%.
- **Model vlakker dan de markt:** de helling is 0.70 à 0.78.
- **Vooral underdogs:** 53 van de 56 en 74 van de 78 bets.

Twee correcties:
- **Gerapporteerde drempel:** het hoofdresultaat in CONTEXT.md gebruikt drempel 1.05, terwijl de code 1.00 koos. Bij 1.00 is de test 75 bets met +34.9%.
- **Blind op de underdog, 2026:** de −0.4% kan ik niet reproduceren. Ik kom op +2.7% (alle 126 wedstrijden), +1.2% (zonder de 2 wedstrijden met gelijke odds) of −1.5% (underdog volgens het model in plaats van de markt).

Praktisch advies: wed niet met dit model bij TOTO. Als het experiment doorgaat, eerst krimp en kalibratie toevoegen en walk-forward evalueren, daarna ratings op wedstrijdniveau, en alleen wedden waar de combinatie met de markt walk-forward over meerdere toernooien iets oplevert.

---

## Naschrift van Bull: kritiek op deze review

De review is geschreven door Claude Code met `claude -p` op een kopie van de onderzoeksmap (28-10-2026). Ik heb de punten gecontroleerd:

- **2.1 Tijdsvolgorde:** gedeeltelijk mee eens. Frank koos bewust voor afstemmen op 2026 en toetsen op 2025. Het echte probleem is subtieler: het 12-maandenvenster van 2026 bevat WK2025 zelf. De toetsuitslagen zitten dus in de features waarop is afgestemd. De omgekeerde run (−27% op 2026) is de eerlijkste toets en wordt vanaf nu altijd gerapporteerd (walk-forward).
- **2.2 Drempel:** terecht dat 'niet wedden' de juiste uitkomst was. Maar 1.05 was de vooraf in de opdracht genoemde regel ('eigen kans × odd > 1,05'), geen achteraf gekozen variant. Op de Page stonden beide drempels.
- **5 Blind op de underdog in 2026:** de correctie klopt. Mijn −0,4% telde wedstrijden met gelijke odds verkeerd. Het juiste getal is +1,2% (zonder gelijke odds) of +2,7%. De conclusie verandert niet.
- **4.1 Data:** de review zegt dat leg-uitslagen per wedstrijd lastig te krijgen zijn. Dartsorakel heeft echter een openbare evenementenlijst (`/api/events`) en resultaatpagina's per toernooi met legstanden en averages. Daarmee is een rating op wedstrijdniveau haalbaar. Dat is het vervolg in de PR.
- **Niet gecontroleerd door de review:** de juistheid van de Oddsportal-slotodds zelf (bijv. tegen een tweede bron) en of Dartsorakel `dateTo` op wedstrijddatum filtert. Beide blijven open punten.
