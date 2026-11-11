import re
from pathlib import Path

BASE_URL = "https://digitaal.foodiesmagazine.nl"

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
PDF_DIR = OUTPUT_DIR / "pdfs"
DEBUG_DIR = OUTPUT_DIR / "debug"
MAGAZINES_INDEX = OUTPUT_DIR / "magazines.json"
RECIPES_FILE = OUTPUT_DIR / "recipes.json"
EXCEL_FILE = OUTPUT_DIR / "recepten.xlsx"
STATE_FILE = ROOT / "storage_state.json"

MAGAZINE_PATH_RE = r"(magazine|publicatie|edition|editie)"

INGREDIENT_HEADERS = (
    "ingrediënten",
    "ingredienten",
    "benodigdheden",
    "je nodig hebt",
    "je hebt nodig",
    "aanschaf",
)
STEP_HEADERS = (
    "bereiding",
    "bereiden",
    "bereid als volgt",
    "zo maak je",
    "zo maak",
    "aan de slag",
    "instructies",
    "stap voor stap",
    "ga als volgt te werk",
)
TIJD_RE = re.compile(r"(\d{1,3})\s*(?:min|minuten|min\.)")
