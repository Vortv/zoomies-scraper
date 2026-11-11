# Foodies Magazine recepten-scraper

Haalt recepten uit de digitale edities van [digitaal.foodiesmagazine.nl](https://digitaal.foodiesmagazine.nl) en zet ze in één doorzoekbaar Excel-bestand.

**Hoe het werkt:** de webreader van Foodies (platform van ePublisher) biedt abonnees per editie een PDF-download aan. Deze toolkit logt in via een echt browservenster (jij typt je wachtwoord zelf, het komt nergens in de code terecht), downloadt de edities als PDF en extraheert daaruit de recepten (titel, personen, tijd, ingrediënten, bereiding) naar `output/recepten.xlsx`.

> Gebruik de resultaten alleen voor persoonlijk gebruik; de recepten zijn auteursrechtelijk beschermd door Foodies.

## Vereisten

- Python 3.10 of nieuwer (<https://www.python.org/downloads/>)

## Installatie

```bash
cd foodies-scraper
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Gebruik

### 1. Eén keer inloggen

```bash
python -m foodies_scraper.login
```

Er opent een browservenster. Log daar in met jouw Foodies-account en druk daarna in de terminal op Enter. De sessie wordt opgeslagen in `storage_state.json` (staat in `.gitignore`, deel dit bestand niet).

### 2. Edities downloaden

```bash
python -m foodies_scraper.scrape_magazines            # alle edities
python -m foodies_scraper.scrape_magazines --limit 3  # eerst 3 edities testen
```

De PDF's komen in `output/pdfs/`. Lukt het niet om de edities automatisch te downloaden, download ze dan handmatig via de downloadknop in de webreader en zet de PDF's zelf in `output/pdfs/` — de rest van de pipeline werkt gewoon.

### 3. Recepten extraheren

```bash
python -m foodies_scraper.pdf_to_recipes
```

Leest alle PDF's in `output/pdfs/` en schrijft `output/recipes.json`.

### 4. Excel-bestand maken

```bash
python -m foodies_scraper.excel
```

Maakt `output/recepten.xlsx` met filterknoppen op elke kolom (editie, pagina, titel, personen, tijd, ingrediënten, bereiding) zodat je makkelijk kunt doorbladeren en filteren.

## Problemen oplossen

- **Geen magazine-links of PDF's gevonden:** draai `python -m foodies_scraper.scrape_magazines --limit 1 --discover`. In `output/debug/` verschijnen dan de HTML van de pagina's en alle JSON-eindpunten die de webreader aanroept. Kijk daar welke URL-structuur de site echt gebruikt en pas zo nodig `MAGAZINE_PATH_RE` in `foodies_scraper/config.py` aan.
- **Sessie verlopen:** gewoon opnieuw `python -m foodies_scraper.login` doen.
- **Recepten onvolledig of versprongen:** de extractie werkt met lettergroottes en kopjes als "Ingrediënten"/"Bereiding". Stel de drempels bij met `TITLE_RATIO` en de koplijsten (`INGREDIENT_HEADERS`, `STEP_HEADERS`) in `foodies_scraper/config.py`.
