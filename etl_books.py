#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ETL: Procesa books.txt (titulo;precio;rating;stock) y genera:
- productos.csv
- productos.json

Transformaciones:
- precio -> float
- rating textual (One..Five) -> int
- stock -> stock_qty (int o None) y stock_status (IN_STOCK / OUT_OF_STOCK / UNKNOWN)

Robustez:
- Maneja filas inválidas sin detenerse (logs + skip)
"""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


INPUT_FILE = "books.txt"
OUTPUT_CSV = "productos.csv"
OUTPUT_JSON = "productos.json"
LOG_FILE = "etl_errors.log"

DELIMITER = ";"


RATING_MAP = {
    "Zero": 0,   # por si aparece
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


@dataclass
class Product:
    title: str
    price: Optional[float]
    rating: Optional[int]
    stock_raw: str
    stock_qty: Optional[int]
    stock_status: str


def setup_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_price(price_raw: str) -> Optional[float]:
    """
    Convierte un precio como '£51.77' (o '51.77') a float.
    Retorna None si no se puede convertir.
    """
    if not price_raw:
        return None

    cleaned = price_raw.strip()

    # Quitar símbolo de moneda y espacios (sin asumir solo £)
    cleaned = cleaned.replace("£", "").replace("$", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_rating(rating_raw: str) -> Optional[int]:
    """
    Convierte 'One', 'Two', ... a int.
    Retorna None si no está en el mapa.
    """
    if not rating_raw:
        return None
    return RATING_MAP.get(rating_raw.strip())


def parse_stock(stock_raw: str) -> tuple[Optional[int], str]:
    """
    Normaliza el stock.
    Entrada típica: 'In stock (22 available)' o 'Out of stock'
    Salida:
      - stock_qty: int si se encuentra número, si no None
      - stock_status: 'IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN'
    """
    text = (stock_raw or "").strip()
    if not text:
        return None, "UNKNOWN"

    lower = text.lower()

    if "in stock" in lower:
        # Extraer el número si está presente: (22 available)
        match = re.search(r"\((\d+)\s+available\)", lower)
        qty = int(match.group(1)) if match else None
        return qty, "IN_STOCK"

    if "out of stock" in lower:
        return 0, "OUT_OF_STOCK"

    # Otros casos inesperados
    return None, "UNKNOWN"


def parse_line(line: str, line_no: int) -> Optional[Product]:
    """
    Parsea una línea del archivo books.txt:
      titulo;precio;rating;stock
    Retorna Product o None si la línea es inválida.
    """
    raw = line.rstrip("\n")
    if not raw.strip():
        return None

    parts = raw.split(DELIMITER)

    if len(parts) != 4:
        logging.warning(
            "Linea invalida (esperado 4 columnas) | line=%s | contenido=%r",
            line_no,
            raw,
        )
        return None

    title_raw, price_raw, rating_raw, stock_raw = [p.strip() for p in parts]

    # Título: si viene vacío, lo consideramos inválido (pero podrías cambiar esto)
    if not title_raw:
        logging.warning("Titulo vacío | line=%s | contenido=%r", line_no, raw)
        return None

    price = parse_price(price_raw)
    if price is None and price_raw:
        logging.warning("Precio no convertible | line=%s | valor=%r", line_no, price_raw)

    rating = parse_rating(rating_raw)
    if rating is None and rating_raw:
        logging.warning("Rating desconocido | line=%s | valor=%r", line_no, rating_raw)

    stock_qty, stock_status = parse_stock(stock_raw)

    return Product(
        title=title_raw,
        price=price,
        rating=rating,
        stock_raw=stock_raw,
        stock_qty=stock_qty,
        stock_status=stock_status,
    )


def read_products(input_path: str) -> list[Product]:
    """Lee el archivo de entrada y devuelve la lista de productos válidos."""
    products: list[Product] = []
    path = Path(input_path)

    if not path.exists():
        logging.error("No existe el archivo de entrada: %s", input_path)
        return products

    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            try:
                product = parse_line(line, i)
                if product is not None:
                    products.append(product)
            except Exception as exc:
                logging.error("Error parseando linea %s | %r | %s", i, line, exc)

    return products


def write_csv(products: list[Product], output_path: str) -> None:
    """Escribe productos en CSV."""
    fieldnames = [
        "title",
        "price",
        "rating",
        "stock_raw",
        "stock_qty",
        "stock_status",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames,delimiter=";")
        writer.writeheader()
        for p in products:
            writer.writerow(asdict(p))


def write_json(products: list[Product], output_path: str) -> None:
    """Escribe productos en JSON (lista de objetos)."""
    data = [asdict(p) for p in products]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    setup_logger()

    products = read_products(INPUT_FILE)
    logging.info("Productos válidos: %s", len(products))

    write_csv(products, OUTPUT_CSV)
    write_json(products, OUTPUT_JSON)

    logging.info("Generado: %s y %s", OUTPUT_CSV, OUTPUT_JSON)


if __name__ == "__main__":
    main()
