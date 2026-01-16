#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
books.toscrape.com scraper (1 archivo, con modos):

MODOS:
  --mode urls   : recorre paginación y guarda URLs de productos en URLS_FILE
  --mode scrape : lee URLS_FILE y scrapea detalle de productos a OUTPUT_FILE
  --mode all    : hace urls + scrape en una sola corrida (default)

REQUISITOS:
- Entra a cada producto y obtiene: titulo, precio, rating (palabra), disponibilidad (texto)
- Recorre todas las páginas del catálogo (paginación)
- Polite: pausas con time.sleep()
- Robusto: maneja errores, registra y continúa
- Sin transformación: no convierte valores (precio con £, rating One/Two..., stock tal cual)
- Exporta TXT separado por ';'
"""

import time
import logging
import argparse
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "http://books.toscrape.com/"
START_PAGE = "catalogue/page-1.html"

OUTPUT_FILE = "books.txt"
URLS_FILE = "product_urls.txt"
LOG_FILE = "scraper_errors.log"

SLEEP_BETWEEN_LIST_PAGES = 0.8
SLEEP_BETWEEN_PRODUCT_PAGES = 0.6

TIMEOUT = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; polite-scraper/1.0; +https://example.com)"
}


def setup_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler()
        ],
    )


def fetch(session: requests.Session, url: str) -> str | None:
    """Descarga HTML y retorna texto. Si falla, registra y devuelve None."""
    try:
        response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()

        # FIX: asegurar que se decodifique como UTF-8 (evita Â£, Ã©, etc.)
        response.encoding = "utf-8"

        return response.text
    except requests.RequestException as e:
        logging.error(f"Request failed: {url} | {e}")
        return None

def safe_select_text(soup: BeautifulSoup, css: str) -> str | None:
    """Extrae texto con selector CSS; si no existe, retorna None."""
    element = soup.select_one(css)
    if not element:
        return None
    return element.get_text(strip=True)



def parse_rating_word(soup: BeautifulSoup) -> str | None:
    """
    En books.toscrape la valoración está en:
    <p class="star-rating Three"> ...
    Retornamos "Three" (sin convertir a número).
    """
    elementRating = soup.select_one("p.star-rating")
    if not elementRating:
        return None
    classes = elementRating.get("class", [])
    # classes suele ser ["star-rating", "Three"]
    for c in classes:
        if c != "star-rating":
            return c
    return None


def get_product_links_from_list_page(list_page_html: str, list_page_url: str) -> list[str]:
    """Devuelve lista de URLs absolutas de productos desde una página de catálogo."""
    soup = BeautifulSoup(list_page_html, "html.parser")
    links: list[str] = []

    for a in soup.select("article.product_pod h3 a"):
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(list_page_url, href)
        links.append(abs_url)

    return links


def get_next_page_url(list_page_html: str, list_page_url: str) -> str | None:
    """Detecta el botón next; retorna URL absoluta de la siguiente página o None."""
    soup = BeautifulSoup(list_page_html, "html.parser")
    next_a = soup.select_one("li.next a")
    if not next_a:
        return None
    href = next_a.get("href")
    if not href:
        return None
    return urljoin(list_page_url, href)


def parse_product_detail(product_html: str, product_url: str) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Extrae:
    - titulo: h1
    - precio: p.price_color
    - rating: palabra en class de p.star-rating (One/Two/Three/Four/Five)
    - disponibilidad: p.availability (ej: "In stock (22 available)")
    """
    soup = BeautifulSoup(product_html, "html.parser")

    title = safe_select_text(soup, "div.product_main h1")
    price = safe_select_text(soup, "div.product_main p.price_color")
    rating = parse_rating_word(soup)

    availability_element = soup.select_one("div.product_main p.availability")
    availability = availability_element.get_text(strip=True) if availability_element else None

    # Robustez: registrar missing sin detener
    if title is None:
        logging.warning(f"Missing title | {product_url}")
    if price is None:
        logging.warning(f"Missing price | {product_url}")
    if rating is None:
        logging.warning(f"Missing rating | {product_url}")
    if availability is None:
        logging.warning(f"Missing availability | {product_url}")

    return title, price, rating, availability


def collect_product_urls(session: requests.Session) -> list[str]:
    """
    Recorre TODA la paginación del catálogo y devuelve una lista de URLs de productos.
    Polite: pausa entre páginas del catálogo.
    """
    urls: list[str] = []
    current_url = urljoin(BASE_URL, START_PAGE)

    while current_url:
        logging.info(f"[urls] Catalog page: {current_url}")
        html = fetch(session, current_url)
        if html is None:
            logging.error(f"[urls] Stopping due to fetch error: {current_url}")
            break

        page_links = get_product_links_from_list_page(html, current_url)
        logging.info(f"[urls] Found products: {len(page_links)}")
        urls.extend(page_links)

        time.sleep(SLEEP_BETWEEN_LIST_PAGES)
        current_url = get_next_page_url(html, current_url)

    # Deduplicación conservadora (por si acaso) sin alterar el contenido de los campos scrapeados
    # (Las URLs duplicadas solo causarían repetición de filas, esto lo evita.)
    urls = list(dict.fromkeys(urls))
    logging.info(f"[urls] Total unique product URLs collected: {len(urls)}")
    return urls


def save_urls(urls: list[str], path: str) -> None:
    """Guarda 1 URL por línea."""
    with open(path, "w", encoding="utf-8") as f:
        for u in urls:
            f.write(u + "\n")


def load_urls(path: str) -> list[str]:
    """Carga 1 URL por línea, ignorando líneas vacías."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"URLs file not found: {path}")
        return []


def scrape_from_urls(session: requests.Session, urls: list[str], output_path: str) -> tuple[int, int]:
    """
    Visita cada URL de producto y escribe OUTPUT en formato:
      titulo;precio;rating;disponibilidad
    Retorna: (productos_procesados_ok, lineas_escritas)
    """
    total_products = 0
    total_lines_written = 0

    with open(output_path, "w", encoding="utf-8") as f_out:
        for product_url in urls:
            time.sleep(SLEEP_BETWEEN_PRODUCT_PAGES)

            product_html = fetch(session, product_url)
            if product_html is None:
                logging.error(f"[scrape] Skipping product due to fetch error: {product_url}")
                continue

            try:
                title, price, rating, availability = parse_product_detail(product_html, product_url)

                # se guarda sin transformación; si falta de deja vacío
                line = f"{title or ''};{price or ''};{rating or ''};{availability or ''}\n"
                f_out.write(line)

                total_lines_written += 1
                total_products += 1
            except Exception as e:
                logging.error(f"[scrape] Parse failed: {product_url} | {e}")
                continue

    return total_products, total_lines_written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="books.toscrape.com scraper")
    parser.add_argument(
        "--mode",
        choices=["urls", "scrape", "all"],
        default="all",
        help="urls=solo recolecta URLs | scrape=solo scrapea usando URLS_FILE | all=ambos (default)"
    )
    parser.add_argument("--urls-file", default=URLS_FILE, help="Archivo para guardar/leer URLs (1 por línea).")
    parser.add_argument("--output-file", default=OUTPUT_FILE, help="Archivo TXT de salida (separado por ';').")
    return parser.parse_args()


def main():
    setup_logger()
    args = parse_args()
    session = requests.Session()

    if args.mode == "urls":
        urls = collect_product_urls(session)
        save_urls(urls, args.urls_file)
        logging.info(f"[urls] Saved: {len(urls)} URLs -> {args.urls_file}")
        return

    if args.mode == "scrape":
        urls = load_urls(args.urls_file)
        if not urls:
            logging.error("[scrape] No URLs to process. Run with --mode urls first (or use --mode all).")
            return
        processed, lines = scrape_from_urls(session, urls, args.output_file)
        logging.info(f"[scrape] Done. Products processed: {processed}. Lines written: {lines}. Output: {args.output_file}")
        return

    # mode == "all"
    urls = collect_product_urls(session)
    save_urls(urls, args.urls_file)
    logging.info(f"[all] Saved: {len(urls)} URLs -> {args.urls_file}")

    processed, lines = scrape_from_urls(session, urls, args.output_file)
    logging.info(f"[all] Done. Products processed: {processed}. Lines written: {lines}. Output: {args.output_file}")


if __name__ == "__main__":
    main()
