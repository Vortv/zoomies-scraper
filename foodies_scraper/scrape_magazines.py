import argparse
import json
import re
import unicodedata
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from foodies_scraper.config import (
    BASE_URL,
    DEBUG_DIR,
    MAGAZINES_INDEX,
    MAGAZINE_PATH_RE,
    PDF_DIR,
    STATE_FILE,
)

PDF_HREF_RE = re.compile(r"\.pdf(\?|$)", re.I)
HOST = urlparse(BASE_URL).netloc


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "editie"


def collect_links(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => ({href: e.href, text: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 150)}))",
    )


def is_internal(url: str) -> bool:
    netloc = urlparse(url).netloc
    return netloc == HOST or netloc.endswith("." + HOST)


def unique_magazine_urls(links: list[dict]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    pattern = re.compile(MAGAZINE_PATH_RE, re.I)
    for link in links:
        href = link.get("href") or ""
        if not is_internal(href):
            continue
        path = urlparse(href).path
        if not pattern.search(path):
            continue
        clean = f"{BASE_URL}{path}" if path else href
        clean = clean.rstrip("/")
        if clean and clean not in seen:
            seen.add(clean)
            urls.append(clean)
    return urls


def save_debug(page, name: str, network_log: list[str]) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    (DEBUG_DIR / f"{name}.html").write_text(page.content(), encoding="utf-8")
    (DEBUG_DIR / f"{name}-network.json").write_text(
        json.dumps(network_log, indent=2), encoding="utf-8"
    )


def download_pdf(context, href: str, dest: str) -> bool:
    try:
        response = context.request.get(href, timeout=120000)
        if response.ok:
            body = response.body()
            if body[:5] == b"%PDF-":
                (PDF_DIR / dest).write_bytes(body)
                return True
    except Exception as exc:
        print(f"    directe download mislukt: {exc}")
    return False


def try_click_download(page, magazine_url: str, index: int) -> str | None:
    candidates = page.locator(
        "a[href*='.pdf' i], [class*='download' i], button:has-text('pdf'), a:has-text('pdf'), "
        "button:has-text('download'), a:has-text('download')"
    )
    count = min(candidates.count(), 5)
    for i in range(count):
        try:
            element = candidates.nth(i)
            if not element.is_visible():
                continue
            with page.expect_download(timeout=60000) as download_info:
                element.click()
            download = download_info.value
            dest = f"{slugify(magazine_url.rsplit('/', 1)[-1]) or f'editie-{index}'}.pdf"
            download.save_as(str(PDF_DIR / dest))
            return dest
        except Exception:
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Magazine-overzicht ophalen en edities als PDF downloaden.")
    parser.add_argument("--limit", type=int, default=0, help="Maximaal aantal edities (0 = alles).")
    parser.add_argument("--discover", action="store_true", help="HTML- en netwerkdebugbestanden opslaan.")
    args = parser.parse_args()

    if not STATE_FILE.exists():
        raise SystemExit("Geen sessie gevonden. Draai eerst: python -m foodies_scraper.login")

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(STATE_FILE))
        page = context.new_page()

        network_log: list[str] = []

        def on_response(response):
            try:
                ctype = response.headers.get("content-type", "")
                if "json" in ctype and is_internal(response.url):
                    network_log.append(response.url)
            except Exception:
                pass

        page.on("response", on_response)

        print(f"Magazine-overzicht openen: {BASE_URL}/magazines")
        page.goto(f"{BASE_URL}/magazines", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        if args.discover:
            save_debug(page, "magazines", network_log)

        links = collect_links(page)
        magazine_urls = unique_magazine_urls(links)
        if not magazine_urls:
            print("Geen magazine-links gevonden. Draai met --discover en bekijk output/debug/.")
            browser.close()
            return
        print(f"{len(magazine_urls)} edities gevonden.")

        if args.limit:
            magazine_urls = magazine_urls[: args.limit]

        for index, url in enumerate(magazine_urls, start=1):
            name = url.rstrip("/").rsplit("/", 1)[-1] or f"editie-{index}"
            print(f"[{index}/{len(magazine_urls)}] {url}")
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
            except Exception as exc:
                print(f"    openen mislukt: {exc}")
                continue

            if args.discover:
                save_debug(page, f"magazine-{slugify(name)}", network_log)

            pdf_links = [
                link["href"]
                for link in collect_links(page)
                if link.get("href") and PDF_HREF_RE.search(link["href"])
            ]
            dest = f"{slugify(name)}.pdf"
            saved = None
            for href in pdf_links[:3]:
                if download_pdf(context, href, dest):
                    saved = dest
                    break
            if not saved:
                saved = try_click_download(page, url, index)
            if saved:
                print(f"    opgeslagen: output/pdfs/{saved}")
                downloaded.append({"url": url, "pdf": saved})
            else:
                print("    geen PDF gevonden; probeer handmatig of met --discover")
                downloaded.append({"url": url, "pdf": None})

        browser.close()

    MAGAZINES_INDEX.parent.mkdir(parents=True, exist_ok=True)
    MAGAZINES_INDEX.write_text(json.dumps(downloaded, indent=2), encoding="utf-8")
    print(f"Index geschreven naar {MAGAZINES_INDEX}")


if __name__ == "__main__":
    main()
