from __future__ import annotations
from bs4 import BeautifulSoup


def parse_sitemap_table_html(text: str) -> list[dict]:
    """
    Para casos raros donde la respuesta no es XML sino una tabla HTML
    con columnas loc/lastmod (como algunos visores o proxies).
    """
    soup = BeautifulSoup(text or "", "html.parser")
    rows = []
    for tr in soup.select("tr"):
        a = tr.select_one("td.loc a")
        lm = tr.select_one("td.lastmod")
        if not a:
            continue
        link = (a.get("href") or a.get_text(strip=True) or "").strip()
        lastmod_raw = (lm.get_text(strip=True) if lm else "").strip()
        if link:
            rows.append({"link": link, "lastmod_raw": lastmod_raw})
    return rows
