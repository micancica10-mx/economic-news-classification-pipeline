from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List


def parse_wp_sitemap(xml_text: str) -> List[Dict[str, str]]:
    """
    WordPress sitemap típico:
    <urlset><url><loc>...</loc><lastmod>...</lastmod></url>...
    A veces con namespace default.

    Retorna: [{"link": ..., "lastmod_raw": ...}, ...]
    """
    root = ET.fromstring(xml_text)

    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0].strip("{")
        ns = {"sm": ns_uri}
        url_nodes = root.findall("sm:url", ns)
        loc_path = "sm:loc"
        lastmod_path = "sm:lastmod"
    else:
        ns = {}
        url_nodes = root.findall("url")
        loc_path = "loc"
        lastmod_path = "lastmod"

    rows: List[Dict[str, str]] = []
    for u in url_nodes:
        link = (u.findtext(loc_path, default="", namespaces=ns) or "").strip()
        lastmod_raw = (u.findtext(lastmod_path, default="", namespaces=ns) or "").strip()
        if link:
            rows.append({"link": link, "lastmod_raw": lastmod_raw})
    return rows
