from __future__ import annotations

from datetime import date
import email.utils as eut
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup

import requests

# Namespaces típicos RSS Arc
ARC_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}


def _txt(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def parse_pubdate_to_date(pubdate: str) -> Optional[date]:
    pubdate = (pubdate or "").strip()
    if not pubdate:
        return None
    try:
        dt = eut.parsedate_to_datetime(pubdate)
        return dt.date()
    except Exception:
        return None


def parse_arc_rss_items(
    s: requests.Session,
    feed_url: str,
    *,
    cutoff_date: date,
    default_categoria: str,
) -> List[Dict]:
    """
    Devuelve una lista de dicts (uno por item) con:
    link, fecha, fecha_raw, titulo, autor, categoria, texto_html
    """
    xml = s.get(feed_url, timeout=(10, 60))
    xml.raise_for_status()

    root = ET.fromstring(xml.text)
    items = root.findall("./channel/item")

    rows: List[Dict] = []
    for it in items:
        titulo = _txt(it.find("title"))
        link = _txt(it.find("link"))
        pubdate_raw = _txt(it.find("pubDate"))
        fecha = parse_pubdate_to_date(pubdate_raw)

        autor = _txt(it.find("dc:creator", ARC_NS))

        # HTML en content:encoded
        texto_html = _txt(it.find("content:encoded", ARC_NS))

        # Categoría: si hay <category>, usa el primero; si no, default_categoria
        cats = [_txt(c) for c in it.findall("category")]
        cats = [c for c in cats if c]
        categoria = cats[0] if cats else default_categoria

        if not link:
            continue
        if fecha is None or fecha < cutoff_date:
            continue

        rows.append({
            "link": link,
            "fecha": fecha,
            "fecha_raw": pubdate_raw,
            "titulo": titulo,
            "autor": autor,
            "categoria": categoria,
            "texto_html": texto_html,
        })

    return rows


def parse_arc_rss_items_v2(
    s: requests.Session,
    feed_url: str,
    *,
    cutoff_date: date,
) -> List[Dict]:
    """
    Devuelve una lista de dicts (uno por item) con:
    link, fecha, fecha_raw, titulo, autor, categoria, texto_html
    """
    xml = s.get(feed_url, timeout=(10, 60))
    xml.raise_for_status()

    root = ET.fromstring(xml.text)
    items = root.findall("./channel/item")

    rows: List[Dict] = []

    for it in items:
        link = _txt(it.find("link"))
        titulo = _txt(it.find("title"))
        pubdate_raw = _txt(it.find("pubDate"))
        fecha = parse_pubdate_to_date(pubdate_raw)

        desc_html = _txt(it.find("description"))

        soup = BeautifulSoup(desc_html, "html.parser")
        primer_p = soup.find("p")

        texto_html = str(primer_p) if primer_p else ""

        if not link:
            continue

        if fecha is None or fecha < cutoff_date:
            continue

        rows.append({
            "link": link,
            "fecha": fecha,
            "fecha_raw": pubdate_raw,
            "titulo": titulo,
            "texto_html": texto_html,
        })

    return rows
