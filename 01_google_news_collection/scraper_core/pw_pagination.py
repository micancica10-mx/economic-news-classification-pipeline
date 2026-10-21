from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from bs4 import BeautifulSoup
from playwright.async_api import Page


async def scrape_paged_listing(
    page: Page,
    *,
    build_page_url: Callable[[int], str],
    parse_cards: Callable[[BeautifulSoup, str], list[dict]],
    cutoff_date: date,
    max_pages: int,
    wait_ms: int,
    card_empty_break_msg: str = "(sin cards) corte por fin de listado/layout",
    should_break_on_page_dates: Optional[Callable[[list[date], date], bool]] = None,
    log_prefix: str = "",
) -> list[dict]:
    """
    Motor genérico:
    - navega paged=1..max_pages
    - obtiene html, soup
    - parsea cards -> lista de items dict con al menos: link, fecha
    - dedupe links
    - aplica cutoff_date
    - regla de corte por fechas de página (opcional)

    Versión robusta (PRO):
    - goto con timeout alto + domcontentloaded
    - espera a que exista al menos un "article" (si aplica)
    - lectura de page.content() con reintentos para evitar:
      "Unable to retrieve content because the page is navigating..."
    """

    rows: list[dict] = []
    seen_links: set[str] = set()

    # Helpers PRO
    async def _safe_goto(url: str) -> None:
        # domcontentloaded suele ser lo más estable para WP con ads/trackers
        await page.goto(url, wait_until="domcontentloaded", timeout=90_000)

    async def _safe_content(tries: int = 6) -> str:
        last_err = None
        for _ in range(tries):
            try:
                # Asegura que terminó la navegación principal
                await page.wait_for_load_state("domcontentloaded")
                # Micro-espera para que el DOM se estabilice
                await page.wait_for_timeout(200)
                return await page.content()
            except Exception as e:
                last_err = e
                # Si está navegando, espera un poquito y reintenta
                await page.wait_for_timeout(350)
        raise last_err  # type: ignore[misc]

    for paged in range(1, max_pages + 1):
        page_url = build_page_url(paged)
        if log_prefix:
            print(f"{log_prefix}→ Página {paged}: {page_url}")
        else:
            print(f"→ Página {paged}: {page_url}")

        # --- Navegación robusta ---
        await _safe_goto(page_url)

        # --- PRO: espera a que haya contenido tipo card ---
        # Tu motor genérico asume "cards"; en tu caso suele ser <article>.
        # Si el sitio no usa article, igual no rompe: cae al except y sigue.
        try:
            await page.wait_for_selector("article", timeout=30_000)
        except Exception:
            # No hacemos break: algunos sitios listan sin article, o cambian layout.
            pass

        await page.wait_for_timeout(wait_ms)

        # --- Lectura robusta del HTML ---
        html = await _safe_content()
        soup = BeautifulSoup(html, "html.parser")

        items = parse_cards(soup, page_url)
        if not items:
            print(f"   {card_empty_break_msg}")
            break

        page_dates: list[date] = []

        for item in items:
            link = (item.get("link") or "").strip()
            f = item.get("fecha")

            if not link or not f:
                continue

            page_dates.append(f)

            if f < cutoff_date:
                continue

            if link in seen_links:
                continue

            seen_links.add(link)
            rows.append(item)

        if should_break_on_page_dates and page_dates:
            if should_break_on_page_dates(page_dates, cutoff_date):
                break

    return rows