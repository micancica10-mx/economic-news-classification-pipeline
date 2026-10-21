from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Dict


def _strip_ns(tag: str) -> str:
    # "{namespace}loc" -> "loc"
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_urlset_sitemap(xml: str) -> List[Dict[str, str]]:
    """
    Parsea sitemaps estándar tipo:
      <url><loc>...</loc><lastmod>...</lastmod></url>
    Devuelve: [{"link": ..., "lastmod_raw": ...}, ...]
    """
    root = ET.fromstring(xml)
    rows: List[Dict[str, str]] = []

    # busca todos los <url> ignorando namespaces
    for url_node in root.iter():
        if _strip_ns(url_node.tag) != "url":
            continue

        link = ""
        lastmod_raw = ""

        for child in list(url_node):
            t = _strip_ns(child.tag)
            if t == "loc":
                link = (child.text or "").strip()
            elif t == "lastmod":
                lastmod_raw = (child.text or "").strip()

        if link:
            rows.append({"link": link, "lastmod_raw": lastmod_raw})

    return rows
