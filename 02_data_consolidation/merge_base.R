# Consolidate daily Google News Excel files into a dataset for text classification.
# Run this script after the Google News collection stage.

library(readxl)
library(dplyr)
library(purrr)
library(writexl)

# --- Configuration: update these paths for your local environment ---
input_dir <- file.path("01_google_news_collection", "outputs")
output_dir <- file.path("02_data_consolidation", "outputs")
historical_file <- file.path(output_dir, "base_texto_v1.xlsx")
output_file <- file.path(output_dir, "base_texto.xlsx")

if (!dir.exists(input_dir)) {
  stop("Input directory not found: ", input_dir)
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

# Read only Google News batch files; avoid importing unrelated Excel files.
excel_files <- list.files(
  input_dir,
  pattern = "^google_news_[0-9]+_[0-9]{8}\\.xlsx$",
  full.names = TRUE
)
if (length(excel_files) == 0L) {
  stop("No Google News batch files found in: ", input_dir)
}

news <- excel_files |>
  map(read_excel) |>
  bind_rows()

required_columns <- c("link", "titulo", "subtitulo", "cuerpo")
missing_columns <- setdiff(required_columns, names(news))
if (length(missing_columns) > 0L) {
  stop("Missing required columns: ", paste(missing_columns, collapse = ", "))
}

# Retain articles with non-empty bodies and valid links.
news <- news |>
  filter(
    !is.na(link), trimws(as.character(link)) != "",
    !is.na(cuerpo), trimws(as.character(cuerpo)) != ""
  )

# Optionally append a historical dataset from previous collection runs.
if (file.exists(historical_file)) {
  historical <- read_excel(historical_file)
  news <- bind_rows(news, historical)
}

# Prefer records containing article text when duplicate URLs occur.
news <- news |>
  mutate(
    link = trimws(as.character(link)),
    cuerpo = as.character(cuerpo),
    has_text = !is.na(cuerpo) & trimws(cuerpo) != ""
  ) |>
  arrange(link, desc(has_text)) |>
  distinct(link, .keep_all = TRUE) |>
  select(-has_text)

# Construct the text fields used by downstream classification scripts.
clean_text <- function(x) {
  x <- as.character(x)
  x[is.na(x) | trimws(x) == ""] <- NA_character_
  x
}

title <- clean_text(news$titulo)
subtitle <- clean_text(news$subtitulo)
news$titulo_completo <- case_when(
  is.na(title) & is.na(subtitle) ~ NA_character_,
  is.na(title) ~ subtitle,
  is.na(subtitle) ~ title,
  TRUE ~ paste(title, subtitle, sep = "\n")
)

news$texto <- ifelse(
  is.na(news$titulo_completo),
  news$cuerpo,
  paste(news$titulo_completo, news$cuerpo, sep = "\n\n")
)
news$caracteres <- nchar(gsub(" ", "", news$texto, fixed = TRUE))

# Excel cells have a maximum length of 32,767 characters.
news$cuerpo <- substr(news$cuerpo, 1L, 32766L)
news$texto <- substr(news$texto, 1L, 32767L)

write_xlsx(news, path = output_file)
message("Saved ", nrow(news), " unique articles to: ", output_file)
