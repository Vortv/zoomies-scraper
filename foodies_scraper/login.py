import argparse

from playwright.sync_api import sync_playwright

from foodies_scraper.config import BASE_URL, STATE_FILE


def main() -> None:
    parser = argparse.ArgumentParser(description="Eenmalig inloggen en de sessie opslaan.")
    parser.add_argument("--url", default=f"{BASE_URL}/login")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(args.url)
        print("Log in in het geopende browservenster.")
        input("Als je bent ingelogd: druk hier op Enter om de sessie op te slaan... ")
        context.storage_state(path=str(STATE_FILE))
        browser.close()

    print(f"Sessie opgeslagen in {STATE_FILE}")


if __name__ == "__main__":
    main()
