# Data Consolidation (R)

This script consolidates the Excel batches produced by the **Google News RSS collection** stage into a single dataset for downstream news classification.

## Processing steps

1. Read `google_news_<batch>_<DDMMYYYY>.xlsx` files from the collection output directory.
2. Keep records with valid article links and non-empty article bodies.
3. Optionally append an existing historical dataset (`base_texto_v1.xlsx`).
4. Remove duplicate article URLs, retaining records with article text.
5. Combine titles, subtitles, and article bodies into the `texto` field, and calculate `caracteres`.
6. Export `base_texto.xlsx` for the **Python classification** stage.

## Requirements

R packages: `readxl`, `dplyr`, `purrr`, and `writexl`.

```r
install.packages(c("readxl", "dplyr", "purrr", "writexl"))
```

## Running the script

Run `merge_base_clean.R` from the repository root, or adjust `input_dir`, `output_dir`, and `historical_file` at the top of the script to match your directory structure. The historical dataset is optional. The script creates the output directory if needed.

**Input:** Daily Google News Excel batches in `01_google_news_collection/outputs/`.

**Output:** `02_data_consolidation/outputs/base_texto.xlsx`, which serves as an input to the subsequent classification models in Python.

The repository does not need to include the collected news datasets. The project is under ongoing development, and the exact data schema may evolve.
