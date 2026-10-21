"""Collect Google News RSS results and extract article text into Excel batches.

Requires scrapers/google.py, which implements the Google News RSS collection.
The Excel files are inputs to the separate R consolidation stage.
"""
from __future__ import annotations

import argparse
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout, as_completed
from datetime import date, datetime

import pandas as pd
import requests
import trafilatura
from bs4 import BeautifulSoup
from googlenewsdecoder import new_decoderv1
from scrapers.google import run as run_google

_TRAF_CONFIG = trafilatura.settings.use_config()
_TRAF_CONFIG.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")
_TRAF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "15")
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ResearchNewsCollector/1.0)",
    "Accept-Language": "es-CO,es;q=0.9",
}

def run_with_timeout(func, args=(), kwargs=None, timeout=30):
    """
    Waits for a function result with a timeout.
    Returns a timeout result if the wait expires; the worker may continue running.
    """
    kwargs = kwargs or {}
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FutureTimeout:
            return {
                "titulo": "",
                "cuerpo": "",
                "error": f"timeout_{timeout}s",
                "url_final": args[0] if args else ""
            }


def _fallback_requests(url: str) -> tuple[str, str]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30, verify=False)
        r.encoding = r.apparent_encoding
        html = r.text

        result = trafilatura.extract(
            html,
            config=_TRAF_CONFIG,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            output_format="txt",
        )
        if result:
            meta = trafilatura.extract_metadata(html)
            titulo = (meta.title or "") if meta else ""
            return titulo.strip(), result.strip()

        # BeautifulSoup fallback
        soup = BeautifulSoup(html, "html.parser")
        parrafos = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        parrafos = [p for p in parrafos if len(p) > 60]
        h1 = soup.find("h1")
        titulo = h1.get_text(" ", strip=True) if h1 else ""
        return titulo, "\n\n".join(parrafos)

    except Exception as e:
        print(f"   fallback error: {e}")
        return "", ""


def _fetch_and_extract_google(url_google: str) -> dict[str, str]:
    url_real = url_google
    try:
        # Decode the Google News URL
        if "news.google.com" in url_google:
            decoded = new_decoderv1(url_google)
            if decoded.get("status"):
                url_real = decoded["decoded_url"]
            else:
                print(f"   Could not decode: {url_google[:60]}")

        # 🔥 Fetch HTML with requests
        try:
            resp = requests.get(
                url_real,
                headers=_HEADERS,
                timeout=15,
                verify=False
            )
            html = resp.text
        except Exception as e:
            return {
                "titulo": "",
                "cuerpo": "",
                "url_final": url_real,
                "error": f"requests_error: {e}",
            }

        result = None
        titulo = ""

        # 🔥 Use Trafilatura for text extraction only
        if html:
            result = trafilatura.extract(
                html,
                config=_TRAF_CONFIG,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
                output_format="txt",
            )

            meta = trafilatura.extract_metadata(html)
            titulo = (meta.title or "") if meta else ""

        # 🔥 Fallback if no text was extracted
        if not result:
            titulo, result = _fallback_requests(url_real)

        return {
            "titulo": titulo.strip(),
            "cuerpo": (result or "").strip(),
            "url_final": url_real,
            "error": "" if result else "no content",
        }

    except Exception as e:
        return {
            "titulo": "",
            "cuerpo": "",
            "url_final": url_real,
            "error": repr(e),
        }


def fase2_google_news(
    df_google: pd.DataFrame,
    *,
    extract_delay: float = 1.0,
    max_workers: int = 3,
    batch_size: int = 100,
    output_dir: str = "outputs",
    fecha_archivo: str | None = None,
    resume: bool = True,
) -> pd.DataFrame:
    """
    Process Google News articles in batches and save each batch to Excel.

    - Creates files such as: google_news_1_24032026.xlsx, google_news_2_24032026.xlsx, ...
    - When resume=True, skip batch files already saved for the same run date.
    - Does not combine batches; the R stage consolidates these Excel files.
    """
    if df_google.empty:
        return pd.DataFrame(columns=df_google.columns)

    output_dir = os.path.abspath(output_dir)

    os.makedirs(output_dir, exist_ok=True)


    if fecha_archivo is None:
        fecha_archivo = datetime.now().strftime("%d%m%Y")

    total = len(df_google)
    n_batches = (total + batch_size - 1) // batch_size

    # Detect previously saved batches
    existing_batches: set[int] = set()
    if resume:
        pattern = re.compile(rf"^google_news_(\d+)_{re.escape(fecha_archivo)}\.xlsx$")
        for fname in os.listdir(output_dir):
            m = pattern.match(fname)
            if m:
                existing_batches.add(int(m.group(1)))

    if existing_batches:
        print(f"   Resuming; previously saved batches: {sorted(existing_batches)}")

    def _process_batch(df_batch: pd.DataFrame, batch_num: int) -> pd.DataFrame:
        rows_input = list(df_batch.itertuples())
        total_batch = len(rows_input)

        results: dict[int, dict] = {}

        def _worker(idx: int, row) -> tuple[int, dict]:
            time.sleep(extract_delay + random.uniform(0, 0.5))

            print(f"   → Processing: {row.link[:80]}")

            result = run_with_timeout(
                    _fetch_and_extract_google,
                    args=(row.link,),
                    timeout=17  # adjust as needed
            )
            if result.get("error"):
                print(f"   ⚠️ Error for: {row.link[:80]} | {result['error']}")
            return idx, {
                "titulo": result.get("titulo") or getattr(row, "titulo", ""),
                "cuerpo": result.get("cuerpo", ""),
                "error": result.get("error", ""),
                "url_final": result.get("url_final", row.link),
            }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_worker, i, row): i
                for i, row in enumerate(rows_input)
            }
            for done, future in enumerate(as_completed(futures), start=1):
                idx, res = future.result()
                results[idx] = res
                if done % 20 == 0 or done == total_batch:
                    ok = sum(1 for r in results.values() if r["cuerpo"])
                    print(f"   Google batch {batch_num}: {done}/{total_batch} | ok={ok}")

        titulos = [results[i]["titulo"] for i in range(total_batch)]
        textos = [results[i]["cuerpo"] for i in range(total_batch)]
        errores = [results[i]["error"] for i in range(total_batch)]
        urls_finales = [results[i]["url_final"] for i in range(total_batch)]

        out = df_batch.copy()
        out["titulo"] = titulos
        out["cuerpo"] = textos
        out["url_final"] = urls_finales
        out["fetch_error"] = errores
        out["fetch_status"] = out["cuerpo"].apply(lambda t: "ok" if t else "empty")
        out["text_len"] = out["cuerpo"].fillna("").str.len()
        out["fecha_scrape"] = datetime.now().replace(microsecond=0)
        return out

    for batch_num in range(1, n_batches + 1):
        if batch_num in existing_batches:
            print(f"   ⏭️ Skipping batch {batch_num}/{n_batches}: already exists")
            continue

        start = (batch_num - 1) * batch_size
        end = min(start + batch_size, total)

        print(f"\n   ▶ Processing batch {batch_num}/{n_batches} | rows {start + 1}-{end} of {total}")
        df_batch = df_google.iloc[start:end].copy().reset_index(drop=True)

        df_batch_full = _process_batch(df_batch, batch_num)

        preferred_cols_g = [
            "medio", "fecha", "titulo", "subtitulo", "link", "url_final", "cuerpo",
            "fetch_status", "fetch_error", "text_len", "fecha_scrape", "query",
            "fecha_raw", "feed", "categoria", "autor",  "section_url", "resumen",
            "etiqueta", "meta_roja", "page"
            
        ]
        cols_g = [c for c in preferred_cols_g if c in df_batch_full.columns] + \
                 [c for c in df_batch_full.columns if c not in preferred_cols_g]
        df_batch_full = df_batch_full[cols_g]

        path_batch = os.path.join(output_dir, f"google_news_{batch_num}_{fecha_archivo}.xlsx")
        df_batch_full.to_excel(path_batch, index=False)
        print(f"   💾 Saved batch {batch_num}: {path_batch} ({len(df_batch_full)} rows)")

    print("\n   ✅ Google News extraction completed in batches.")
    return pd.DataFrame(columns=df_google.columns)


def main():
    parser = argparse.ArgumentParser(description="Collect Colombian economic news via Google News RSS")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD")
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--processed-links", default="", help="Optional Excel file containing a 'link' column")
    args = parser.parse_args()

    if args.start_date > args.end_date:
        parser.error("--start-date must not be later than --end-date")

    # Stage 1: Retrieve Google News RSS entries through the companion module.
    news = run_google(start_date=args.start_date, end_date=args.end_date)
    if "url" in news.columns and "link" not in news.columns:
        news = news.rename(columns={"url": "link"})
    if "link" not in news.columns:
        raise ValueError("The Google News collector must return a 'link' or 'url' column")

    news = news.copy()
    news["link"] = news["link"].astype(str).str.strip()
    news = news[news["link"].ne("") & news["link"].ne("nan")]
    news = news.drop_duplicates(subset=["link"]).reset_index(drop=True)

    # Exclude institutional sources using the same title-based rules as the original script.
    excluded_sources = {
        "cali.gov.co", "valledelcauca.gov.co", "pasto.gov.co",
        "popayan.gov.co", "narino.gov.co", "cauca.gov.co",
        " - Gobernacion Cauca", "policia.gov.co", " - Gobernación del valle",
    }
    if "titulo" in news.columns:
        pattern = "|".join(re.escape(source) for source in excluded_sources)
        news = news[~news["titulo"].astype(str).str.contains(pattern, case=False, na=False)]

    # Optionally remove links already collected on previous runs.
    if args.processed_links:
        previous = pd.read_excel(args.processed_links)
        if "link" not in previous.columns:
            raise ValueError("The processed-links workbook must contain a 'link' column")
        seen = set(previous["link"].dropna().astype(str).str.strip())
        news = news[~news["link"].isin(seen)]

    news = news.reset_index(drop=True)
    print(f"Google News articles to process: {len(news)}")

    # Stage 2: Extract article text and save separate Excel files by batch.
    fase2_google_news(
        news,
        extract_delay=args.delay,
        max_workers=args.workers,
        batch_size=args.batch_size,
        output_dir=args.output_dir,
    )
    print("Next step: consolidate the Excel batches using the R script in 02_data_consolidation.")


if __name__ == "__main__":
    main()
