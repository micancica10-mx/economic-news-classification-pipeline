# Google News RSS Collection

This folder contains the first stage of a research-oriented pipeline for collecting and classifying Colombian economic news.

## What it does

1. Queries Google News RSS for articles matching economic keywords and selected Colombian news outlets, using the companion `scrapers/google.py` module.
2. Filters duplicate URLs and selected non-news sources. An optional previously processed links workbook can be used to avoid recollecting articles.
3. Resolves Google News links and attempts to extract article titles and text using Trafilatura, with a BeautifulSoup fallback.
4. Saves results as **Excel files in batches** under `outputs/`, e.g., `google_news_1_21102026.xlsx`. Batch files are not combined at this stage.

## Configure search keywords and news outlets

Edit the `KEYWORDS` list near the top of `scrapers/google.py` before running the collector. The public example contains **three illustrative queries**:

```python
KEYWORDS = [
    "inflación larepublica.co",
    "empleo larepublica.co",
    "industria larepublica.co",
]
```

Replace or extend these entries with your preferred economic search terms and Colombian news outlets. Each string is submitted as a Google News RSS search query; the outlet name is part of the query text, not a guaranteed website-only filter. The three examples are not intended to represent the full set of terms used in the broader research project.

## Next stage: consolidation in R

The daily Excel outputs are inputs to the script in `02_data_consolidation/`, which combines files across batches and collection dates. The resulting unified dataset is subsequently processed by the Python classification scripts in `03_news_classification/`.

## Files and setup

- `main.py`: orchestrates RSS collection, article extraction, and Excel export.
- `scrapers/google.py`: implements the Google News RSS query and collection logic (**required**; add this file to the repository).

Run from this folder after installing dependencies and supplying `scrapers/google.py`:

```bash
python main.py --start-date 2026-10-21 --end-date 2026-10-21
```

Optional parameters: `--output-dir`, `--batch-size`, `--workers`, `--delay`, and `--processed-links` (an Excel workbook with a `link` column).

## Notes and limitations

- Google News RSS provides discovery links; full-text availability depends on the publisher and may be limited or unavailable.
- Respect publishers' access restrictions, robots policies, terms, and copyright. This project does not grant permission to reproduce copyrighted content.
- Existing Excel batches with the same run date are skipped when resuming; review outputs before rerunning a partially completed collection.
- This public repository covers the Google News component only. Other website-specific collectors used in the broader research workflow are not published here.
- The broader pipeline and its final AI-based classification prompt remain under development.
- Generative AI assisted code development and debugging; that assistance is separate from the downstream AI classification stage.
