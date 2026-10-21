from __future__ import annotations

from bs4 import BeautifulSoup


def extract_title(html: str) -> str:
    """
    Prioridad:
    1) og:title
    2) twitter:title
    3) h1
    4) <title>
    """
    soup = BeautifulSoup(html or "", "html.parser")

    og = soup.select_one('meta[property="og:title"]')
    if og and og.get("content"):
        return og["content"].strip()

    tw = soup.select_one('meta[name="twitter:title"]')
    if tw and tw.get("content"):
        return tw["content"].strip()

    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(" ", strip=True)
        if t:
            return t

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    return ""
