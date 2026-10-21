# scrapers/google_news.py
from __future__ import annotations

from datetime import date, datetime
import email.utils as eut
import html
import re
import time
import random
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import trafilatura
from bs4 import BeautifulSoup
from googlenewsdecoder import new_decoderv1

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# =========================
# CONFIG
# =========================
HL = "es-419"
GL = "CO"
CEID = "CO:es-419"

# Example search terms. Replace or expand these queries for your research.
# Each query combines an economic keyword with a Colombian news outlet.
KEYWORDS = [
    "inflación larepublica.co",
    "empleo larepublica.co",
    "industria larepublica.co",
]

HEADERS = {
    
"User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.0.0 Safari/537.36"
),
    "Accept-Encoding": "identity",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}

S = requests.Session()
S.headers.update(HEADERS)
S.verify = False

# Trafilatura configuration
_TRAF_CONFIG = trafilatura.settings.use_config()
_TRAF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")

EXTRACT_DELAY: float = 1.0
EXTRACT_DELAY_JITTER: float = 0.5


# =========================
# HELPERS
# =========================
_TAG_RE = re.compile(r"<[^>]+>")


from datetime import timedelta

def generar_periodos(start_date, end_date) -> list[tuple[date, date]]:
    """
    Returns three-day (start, end) date ranges.
    """

    periodos = []
    fecha = start_date

    while fecha <= end_date:

        fin_periodo = min(
            fecha + timedelta(days=2),
            end_date
        )

        periodos.append((fecha, fin_periodo))

        fecha = fin_periodo + timedelta(days=1)

    return periodos




def _strip_html(x: str) -> str:
    x = "" if x is None else str(x)
    x = html.unescape(x)
    x = _TAG_RE.sub(" ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

def _parse_pubdate(pubdate: str) -> datetime | None:
    if not pubdate:
        return None
    try:
        dt = eut.parsedate_to_datetime(pubdate)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return None

def _rss_url_for_query(q: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(q)}&hl={HL}&gl={GL}&ceid={CEID}"
    )

def _parse_rss(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return []
    rows: list[dict] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        rows.append({
            "titulo":    _strip_html(title),
            "link":      link,
            "fecha":     _parse_pubdate(pub),
            "subtitulo": _strip_html(desc),
        })
    return rows


# =========================
# STAGE 1: COLLECT RSS LINKS
# =========================
def run(*, start_date: date,end_date: date, keywords: list[str] | None = None) -> pd.DataFrame:
    kws = keywords or KEYWORDS
    all_rows = []

    periodos = generar_periodos(start_date, end_date)

    for kw in kws:

        for inicio_periodo, fin_periodo in periodos:

            q = (
                f"{kw} "
                f"after:{inicio_periodo:%Y-%m-%d} "
                f"before:{(fin_periodo + timedelta(days=1)):%Y-%m-%d}"
                )

            print(f" Querying: {kw} | "f"{inicio_periodo} -> {fin_periodo}")

            url = _rss_url_for_query(q)

  
            r = S.get(url, timeout=(10, 60))
            r.raise_for_status()
            items = _parse_rss(r.text)

            print(f" {len(items)} items RSS")

            if len(items) >= 95: print(" ⚠️ Possible Google RSS result limit")

            for it in items:
                it["medio"] = "Google News"
                it["query"] = kw
                it["fecha_consulta_ini"] = inicio_periodo
                it["fecha_consulta_fin"] = fin_periodo
                all_rows.append(it)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df

    df = df[df["fecha"].notna()].copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df[(df["fecha"].dt.date >= start_date)&(df["fecha"].dt.date <= end_date)].copy()

    df["link"] = df["link"].astype(str).str.strip()
    df = df[df["link"].ne("") & df["link"].ne("nan")].copy()
    df = df.drop_duplicates(subset=["link"], keep="first")

    cols = ["medio", "fecha", "titulo", "subtitulo", "link", "query", "fecha_consulta_ini",
"fecha_consulta_fin"]
    cols = [c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]
    return df[cols]


# =========================
# STAGE 2: EXTRACTION HELPERS
# =========================
def _fallback_requests(url: str) -> tuple[str, str]:
    """Downloads a page with requests and extracts text using Trafilatura or BeautifulSoup."""
    try:
        r = S.get(url, timeout=30, stream=True)
        raw = r.content
        html_text = raw.decode(r.encoding or "utf-8", errors="ignore")

        result = trafilatura.extract(
            html_text,
            config=_TRAF_CONFIG,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            output_format="txt",
        )
        if result:
            meta = trafilatura.extract_metadata(html_text)
            titulo = (meta.title or "") if meta else ""
            return titulo.strip(), result.strip()

        # Final fallback: BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        parrafos = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        parrafos = [p for p in parrafos if len(p) > 60]
        h1 = soup.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else ""
        return titulo, "\n\n".join(parrafos)

    except Exception as e:
        print(f"   fallback error: {e}")
        return "", ""


def fetch_and_extract(url: str) -> dict[str, str]:
    """
    Decodes the Google News URL, downloads the page, and extracts content.
    Tries Trafilatura first, then falls back to requests/BeautifulSoup.
    """
    url_real = url
    try:
        if "news.google.com" in url:
            decoded = new_decoderv1(url)
            if decoded.get("status"):
                url_real = decoded["decoded_url"]
                print(f"   → {url_real}")
            else:
                print(f"   Could not decode: {url[:60]}")

        downloaded = trafilatura.fetch_url(url_real)
        result = None
        titulo = ""

        if downloaded:
            result = trafilatura.extract(
                downloaded,
                config=_TRAF_CONFIG,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
                output_format="txt",
            )
            meta = trafilatura.extract_metadata(downloaded)
            titulo = (meta.title or "") if meta else ""

        if not result:
            print(f"   Trafilatura returned no text; using requests fallback...")
            titulo, result = _fallback_requests(url_real)

        return {
            "titulo":    titulo.strip(),
            "cuerpo":     (result or "").strip(),
            "url_final": url_real,
            "error":     "" if result else "no content",
        }
    except Exception as e:
        return {"titulo": "", "cuerpo": "", "url_final": url_real, "error": repr(e)}


# =========================
# STAGE 2: FULL EXTRACTION RUN
# =========================
def run_with_content(
    *,
    start_date: date,
    end_date: date,
    keywords: list[str] | None = None,
    extract_delay: float = EXTRACT_DELAY,
) -> pd.DataFrame:
    df = run(start_date=start_date,end_date=end_date, keywords=keywords)
    if df.empty:
        print("No articles found.")
        return df

    print(f"\nExtracting content from {len(df)} artículos...")
    titulos, textos, errores, urls_finales = [], [], [], []

    for i, row in enumerate(df.itertuples(), start=1):
        time.sleep(extract_delay + random.uniform(0, EXTRACT_DELAY_JITTER))
        result = fetch_and_extract(row.link)

        titulos.append(result.get("titulo") or row.titulo)
        textos.append(result.get("cuerpo", ""))
        errores.append(result.get("error", ""))
        urls_finales.append(result.get("url_final", row.link))

        if i % 20 == 0:
            ok = sum(1 for t in textos if t)
            print(f"   Progress: {i}/{len(df)} | ok={ok}")

    df = df.copy()
    df["titulo"]       = titulos
    df["cuerpo"]        = textos
    df["url_final"]    = urls_finales
    df["fetch_error"]  = errores
    df["fetch_status"] = df["cuerpo"].apply(lambda t: "ok" if t else "empty")
    df["text_len"]     = df["cuerpo"].str.len()

    return df
