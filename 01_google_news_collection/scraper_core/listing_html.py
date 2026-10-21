from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import requests
from bs4 import BeautifulSoup


def get_soup(session: requests.Session, url: str, *, timeout: int = 30) -> Optional[BeautifulSoup]:
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None


def scrape_paged_listing_bs(
    session: requests.Session,
    *,
    base_url: str,
    start_page: int = 1,
    build_url: Optional[Callable[[str, int], str]] = None,
    get_cards: Callable[[BeautifulSoup], list],
    extract_rows: Callable[[list, str], list[dict]],
    should_stop_after_page: Callable[[list, datetime], bool],
    categoria: str,
    cutoff_dt: datetime,
    log_prefix: str = "",
) -> list[dict]:
    """
    Recorre páginas (1,2,3...) y extrae filas.
    - build_url: por defecto base_url + page
    - get_cards: cómo obtener tarjetas
    - extract_rows: cómo transformar tarjetas → dicts
    - should_stop_after_page: regla de corte por cutoff (usa tarjetas de esa página)
    """
    rows: list[dict] = []
    page = start_page

    if build_url is None:
        build_url = lambda b, p: f"{b}{p}"

    while True:
        url = build_url(base_url, page)
        if log_prefix:
            print(f"{log_prefix}→ Página {page}: {url}")
        else:
            print(f"→ Página {page}: {url}")

        soup = get_soup(session, url)
        if not soup:
            break

        cards = get_cards(soup)
        if not cards:
            break

        # 1) decidir si se corta después de esta página
        stop = should_stop_after_page(cards, cutoff_dt)

        # 2) extraer todas las tarjetas
        rows.extend(extract_rows(cards, categoria))

        if stop:
            break

        page += 1

    return rows
