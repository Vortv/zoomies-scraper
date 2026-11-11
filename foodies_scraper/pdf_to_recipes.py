import json
import re
import statistics
from pathlib import Path

import pdfplumber

from foodies_scraper.config import (
    INGREDIENT_HEADERS,
    OUTPUT_DIR,
    PDF_DIR,
    RECIPES_FILE,
    STEP_HEADERS,
    TIJD_RE,
)

TITLE_RATIO = 1.22
MIN_TITLE_LEN = 4
MAX_INGREDIENT_LINE_LEN = 90


def normalize(text: str) -> str:
    text = text.lower().strip(" .:;·•-–—")
    return re.sub(r"\s+", " ", text)


def is_header(line: str, headers) -> bool:
    normalized = normalize(line)
    return any(normalized == h or normalized.startswith(h + " ") or normalized.startswith(h + ":") for h in headers)


def page_lines(page) -> list[dict]:
    words = page.extract_words(extra_attrs=["size", "fontname"], keep_blank_chars=False)
    grouped: dict[int, list] = {}
    for word in words:
        key = round(word["top"] / 3.0)
        grouped.setdefault(key, []).append(word)
    lines = []
    for key in sorted(grouped):
        ws = sorted(grouped[key], key=lambda w: w["x0"])
        text = re.sub(r"\s+", " ", " ".join(w["text"] for w in ws)).strip()
        if not text:
            continue
        size = max((w.get("size") or 0.0) for w in ws)
        lines.append({"top": key * 3.0, "text": text, "size": size})
    return lines


def looks_like_title(text: str, size: float, body_size: float) -> bool:
    if size < body_size * TITLE_RATIO:
        return False
    if len(text) < MIN_TITLE_LEN or len(text) > 120:
        return False
    if text.isdigit():
        return False
    return True


def clean_body_line(text: str) -> str:
    stripped = text.strip()
    if re.fullmatch(r"\d{1,4}", stripped):
        return ""
    if re.fullmatch(r"(pagina\s*)?\d{1,4}\s*/\s*\d{1,4}", stripped, re.I):
        return ""
    return stripped


def extract_personen(lines: list[dict]) -> str:
    for line in lines[:14]:
        match = re.search(r"(\d{1,2})\s*(?:personen|persoons|persoonsgerecht)", line["text"], re.I)
        if match:
            return match.group(1)
    return ""


def extract_tijd(lines: list[dict]) -> str:
    for line in lines[:14]:
        match = TIJD_RE.search(line["text"])
        if match:
            return f"{match.group(1)} min"
    return ""


def parse_pdf(pdf_path: Path, editie: str) -> list[dict]:
    recipes: list[dict] = []
    all_lines: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            try:
                for line in page_lines(page):
                    line["page"] = page_number
                    all_lines.append(line)
            except Exception:
                continue

    if not all_lines:
        return recipes

    body_size = statistics.median(line["size"] for line in all_lines)

    segments: list[dict] = []
    for line in all_lines:
        if is_header(line["text"], INGREDIENT_HEADERS) or is_header(line["text"], STEP_HEADERS):
            if not segments:
                segments.append({"title": "", "page": line["page"], "lines": []})
            segments[-1]["lines"].append(line)
        elif looks_like_title(line["text"], line["size"], body_size):
            segments.append({"title": line["text"], "page": line["page"], "lines": []})
        elif segments:
            cleaned = clean_body_line(line["text"])
            if cleaned:
                segments[-1]["lines"].append(line)
        else:
            continue

    for segment in segments:
        has_ingredients = any(is_header(l["text"], INGREDIENT_HEADERS) for l in segment["lines"])
        has_steps = any(is_header(l["text"], STEP_HEADERS) for l in segment["lines"])
        if not (has_ingredients or has_steps):
            continue

        ingredients: list[str] = []
        steps: list[str] = []
        target: list[str] | None = None
        for line in segment["lines"]:
            if is_header(line["text"], INGREDIENT_HEADERS):
                target = ingredients
                continue
            if is_header(line["text"], STEP_HEADERS):
                target = steps
                continue
            if looks_like_title(line["text"], line["size"], body_size):
                target = None
                continue
            if target is not None:
                text = line["text"]
                if target is ingredients and len(text) > MAX_INGREDIENT_LINE_LEN:
                    parts = re.split(r"\s(?=\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|el|tl|st|stuks?|bossje|bosje|takje?s?|blaadje?s?|blik|blikje|pot|pak|rol|scheut|teen|tenen|plak|plakken|snufje|handsje|handvol)\b)", text, flags=re.I)
                    target.extend(p.strip() for p in parts if p.strip())
                else:
                    target.append(text)

        if not ingredients and not steps:
            continue

        recipes.append(
            {
                "editie": editie,
                "pagina": segment["page"],
                "titel": segment["title"],
                "personen": extract_personen(segment["lines"]),
                "tijd": extract_tijd(segment["lines"]),
                "ingrediënten": "\n".join(ingredients),
                "bereiding": "\n".join(steps),
            }
        )

    return recipes


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"Geen PDF's gevonden in {PDF_DIR}. Draai eerst scrape_magazines.py of leg PDF's handmatig in die map.")

    all_recipes: list[dict] = []
    for pdf_path in pdfs:
        editie = pdf_path.stem.replace("-", " ")
        print(f"{pdf_path.name} ...")
        recipes = parse_pdf(pdf_path, editie)
        print(f"  {len(recipes)} recepten gevonden")
        all_recipes.extend(recipes)

    RECIPES_FILE.write_text(json.dumps(all_recipes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Totaal {len(all_recipes)} recepten -> {RECIPES_FILE}")


if __name__ == "__main__":
    main()
