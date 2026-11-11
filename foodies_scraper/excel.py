import json

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from foodies_scraper.config import EXCEL_FILE, OUTPUT_DIR, RECIPES_FILE

COLUMNS = ["Editie", "Pagina", "Titel", "Personen", "Tijd", "Ingrediënten", "Bereiding"]
WIDTHS = [22, 8, 42, 10, 10, 60, 80]
WRAPPED = {"Ingrediënten", "Bereiding"}


def main() -> None:
    if not RECIPES_FILE.exists():
        raise SystemExit(f"Geen {RECIPES_FILE} gevonden. Draai eerst: python -m foodies_scraper.pdf_to_recipes")

    recipes = json.loads(RECIPES_FILE.read_text(encoding="utf-8"))
    if not recipes:
        raise SystemExit("recipes.json bevat geen recepten.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(recipes)
    df.columns = [column.capitalize() for column in df.columns]
    df = df.reindex(columns=COLUMNS).astype(object).fillna("")
    df.to_excel(EXCEL_FILE, index=False)

    from openpyxl import load_workbook

    workbook = load_workbook(EXCEL_FILE)
    sheet = workbook.active
    header_fill = PatternFill("solid", fgColor="2E7D32")
    header_font = Font(bold=True, color="FFFFFF")

    for col_index, column in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=col_index)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(vertical="center")
        sheet.column_dimensions[get_column_letter(col_index)].width = WIDTHS[col_index - 1]

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{sheet.max_row}"

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=sheet.cell(row=1, column=cell.column).value in WRAPPED,
            )

    workbook.save(EXCEL_FILE)
    print(f"{len(recipes)} recepten geschreven naar {EXCEL_FILE}")


if __name__ == "__main__":
    main()
