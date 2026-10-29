# Onderzoek: TOTO-odds loggen en open bronnen voor darts-odds en -statistieken

Stand: 29-10-2026. Geen juridisch advies; samenvatting van de voorwaarden zoals die nu online staan.

## 1. Mogen we TOTO-odds lezen en loggen?

**Bronnen**

- [Deelnemersreglement TOTO Sport & TOTO Casino & Winnitt, geldig vanaf 1 oktober 2026](https://portal-spa-api.toto.nl/assets/3bd23cbf-f81e-4345-9f1e-091f124da687)
- [Vorige versie, geldig vanaf 27 augustus 2024](https://portal-spa-api.toto.nl/assets/61bcd3d9-04ca-4945-b214-f840dfe2e0c3)
- [Disclaimer Nederlandse Loterij](https://www.nederlandseloterij.nl/disclaimer) (TOTO Online B.V. valt onder Nederlandse Loterij)
- [robots.txt van toto.nl](https://www.toto.nl/robots.txt)

**Wat erin staat**

- Het reglement bevat **geen expliciet verbod op scrapen of geautomatiseerd gebruik**. Gezocht op o.a. "geautomatiseerd",
  "scrapen", "robot", "crawl", "bot".
- Art. 10: alle intellectuele-eigendomsrechten, *uitdrukkelijk ook databankrechten*, op de website, apps en "elk materiaal dat
  daarin wordt weergegeven" zijn van TOTO of haar licentiegevers.
- Disclaimer Nederlandse Loterij, kopje *Auteursrechten*: "Gebruik van informatie van (delen van) de webpagina's zonder
  voorafgaande schriftelijke toestemming van Nederlandse Loterij [...] is niet toegestaan."
- Art. 13 lid 3 en art. 17 onder f en g: het account is persoonlijk, "mag dus niet door anderen gebruikt worden", en de
  deelnemer houdt wachtwoorden en inlogcodes geheim. Art. 15 lid 1a: niet professioneel of bedrijfsmatig gebruiken.
- Art. 37 (Live Streaming & Scorebord): alleen voor particuliere doeleinden; reproduceren of tonen in een publieke omgeving
  is verboden.
- robots.txt sluit alleen PDF's uit voor crawlers.

**Conclusie**

| Gebruik | Oordeel |
|---|---|
| Frank of Bull leest handmatig de odd van een wedstrijd waarop we willen wedden en noteert die in het eigen logboek | Prima: normaal, particulier gebruik |
| Op de publieke pagina tonen tegen welke odd **wij** een bet hebben geplaatst (onze eigen inzet en uitkomst) | Verdedigbaar: dit is een feit over onze eigen bet, geen overname van TOTO's oddsoverzicht. Klein houden en de bron noemen |
| Automatisch alle TOTO-odds ophalen (scraper of bot) | Niet doen. Geen expliciet verbod, maar het raakt TOTO's databankrecht en de disclaimer vraagt toestemming vooraf |
| Een volledige TOTO-oddstabel publiceren | Niet doen zonder schriftelijke toestemming |
| Live Stream of Scorebord-gegevens van TOTO gebruiken | Niet doen (art. 37) |

**Let op, apart van de odds:** art. 17 onder f en g zegt dat het account niet door anderen gebruikt mag worden en dat de
inloggegevens geheim blijven. Bull die met Franks login bets plaatst, staat daarmee op gespannen voet, ook al keurt Frank elke
bet goed. Het veiligste is dat Frank de goedgekeurde bets zelf plaatst en Bull alleen voorbereidt en logt. Frank beslist.

## 2. Open of betaalbare bronnen voor darts-odds en -statistieken

| Bron | Wat | Kosten | Darts/PDC | Bruikbaar in NL | Voorwaarden / opmerking | Oordeel |
|---|---|---|---|---|---|---|
| [The Odds API](https://the-odds-api.com/sports-odds-data/sports-apis.html) | Odds van veel bookmakers | Gratis 500 credits/mnd, vanaf $30/mnd | **Nee**, geen darts in de lijst | Ja | Duidelijke API-voorwaarden | Niet bruikbaar voor darts |
| [Betfair Exchange API](https://developer.betfair.com/) | Exchange-prijzen, historische data | n.v.t. | Ja | **Nee**: Betfair is sinds 30-9-2021 weg uit NL ([bron](https://www.gamblingnews.com/news/betfair-leaves-the-netherlands-prior-to-official-market-launch/)); volgens [bfgateway](https://www.bfgateway.com/betfair-access/betfair-exchange-not-available) staat NL ook op Betfairs lijst geblokkeerde API-regio's | Niet omzeilen met een VPN | Niet bruikbaar |
| [OpticOdds](https://developer.opticodds.com/docs/odds-api-getting-started-guide) | Odds van 100+ bookmakers, ook darts | Op aanvraag (zakelijk) | Ja | Ja (data) | Zakelijke licentie | Te duur voor een hobby |
| [Sportradar Darts API](https://developer.sportradar.com/darts/reference/darts-overview) | Officiële PDC-data: schema, uitslagen, stats, winkansen | Proefperiode, daarna zakelijk | Ja, officiële PDC-partner | Ja | Zakelijke licentie | Mooi voor een proef, te duur voor structureel |
| [BSD / Bzzoiro Darts API](https://sports.bzzoiro.com/docs/darts/) | PDC-wedstrijden, legs, h2h, Elo, odds per bookmaker (15 boeken) | Odds-API $5/mnd, sport-add-on $7/mnd | Ja | Ja | [Voorwaarden](https://sports.bzzoiro.com/terms/): geen ruwe data doorverkopen; data "compiled from public sources, third party providers" (herkomst onduidelijk). TOTO zit er niet in | **Beste goedkope kandidaat**; eerst een maand testen en de licentie op publiceren lezen |
| [API-Sports](https://api-sports.io/) | Veel sporten | Gratis tier | **Nee**, geen darts | Ja | – | Niet bruikbaar |
| [sportsdata-mcp](https://github.com/DanielTomaro13/sportsdata-mcp) (MIT) | Open-source MCP-server, 64 providers | Gratis | Geen darts genoemd | Ja | Per provider eigen voorwaarden | Niet nodig voor darts |
| [Wikipedia](https://en.wikipedia.org/wiki/2026_PDC_World_Darts_Championship) | WK-schema, uitslagen, in-match averages | Gratis, CC BY-SA 4.0 | Ja | Ja | Naamsvermelding | Gebruiken we al |
| [Dartsorakel](https://dartsorakel.com/) | Averages, checkout%, uitslagen | Deels gratis, deels paywall | Ja | Ja | Paywall niet omzeilen | Gebruiken we al (alleen gratis deel, niet herverspreid) |
| Oddsportal | Slotodds | Gratis te bekijken | Ja | Ja | **Voorwaarden verbieden scrapen** | Ophaalscript verwijderd |

**Advies:** voor het WK de TOTO-odd per voorgestelde bet handmatig loggen (dat is ook de odd die echt telt), en eventueel
één maand BSD ($5) proberen om historische slotodds van andere PDC-toernooien te krijgen, na het lezen van hun
licentie op publiceren. Geen scrapers.
