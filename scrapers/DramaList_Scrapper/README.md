# DramaList Scrapper

Scrapes drama data and posters from [MyDramaList](https://mydramalist.com). The pipeline is ten
numbered steps, each in its own script, plus `run_pipeline.py` which runs all of them in order
with one command.

## Folder layout

- All step scripts live in `steps/`: `steps/step0a_download_listing_pages.py`, ...,
  `steps/step3_download_images.py`. `run_pipeline.py` and `README.md` stay at the top level as
  the single entry point.
- Scraped/downloaded data lives under `output/`: `output/html_pages/`, `output/dramas_html/`,
  `output/drama_image_by_id/`, `output/extra/`, `output/dramalist_all_dramas.csv`
- `mydramalist_data.csv` and `dramalist_kdramas.xlsx` stay next to `run_pipeline.py`

## Quick start

```bash
python run_pipeline.py                                        # run all ten steps, in order
python run_pipeline.py --skip-listing --skip-urls --skip-html  # already have output/dramas_html/, just extract + get images
python run_pipeline.py --only images                           # run just one step
```

Each step skips work it's already done (existing HTML files, CSV rows, downloaded images), so
re-running `run_pipeline.py` after a partial or failed run just resumes.

Each step script can still be run on its own if you want to run just that step manually, e.g.
`python steps/step1_download_html.py` (run from the `DramaList_Scrapper/` folder).

## Pipeline

### Step 0a — `steps/step0a_download_listing_pages.py` (listing downloader)
Uses Playwright to fetch MyDramaList's listing pages from **two sources**, defined in
the `SOURCES` dict:
- `popular` — `mydramalist.com/shows/popular?page=1..250`
- `newest` — `mydramalist.com/shows/newest?page=1..250`

- **Input:** none (hits the live site)
- **Output:** each source gets its own subfolder under `output/html_pages/`, so both can
  reuse the same `page_N.html` naming without colliding:
  - `output/html_pages/popular/page_1.html` ... `page_250.html`
  - `output/html_pages/newest/page_1.html` ... `page_250.html`
- **Run:** `python steps/step0a_download_listing_pages.py`
- Each source's `last_page` is **hardcoded on purpose**, not auto-detected. `popular`'s
  250 is confirmed as MyDramaList's actual last page. `newest`'s 250 is **unverified** —
  check the run's output for repeated fetch errors/empty pages near the end and adjust
  `SOURCES["newest"]["last_page"]` in the script accordingly.
- To add another listing source later, add an entry to `SOURCES` with its own
  `url_template` and `last_page` — it'll get its own subfolder named after the source key.
- Skips pages already saved. Safe to re-run/resume.

### Step 0b — `steps/step0b_extract_drama_urls.py` (URL extractor)
Parses every listing page under `output/html_pages/` (recursively, across all source
subfolders) with BeautifulSoup and pulls out one row per drama box: `Ranking, Title,
Media_Info, Rating, Description, Title_URL, Image_URL`. `Title_URL` is what Step 1 needs.
Since `popular` and `newest` can list the same drama, `mydramalist_data.csv` may contain
duplicate `Title_URL` rows — harmless, Step 1 skips a drama it's already downloaded
regardless of which CSV row triggered it.

- **Input:** `output/html_pages/**/*.html`
- **Output:** `mydramalist_data.csv`
- **Run:** `python steps/step0b_extract_drama_urls.py`
- Rewrites the whole CSV each run (not incremental) — re-run after Step 0a fetches new pages.

### Step 1 — `steps/step1_download_html.py` (drama page downloader)
Reads drama URLs from `mydramalist_data.csv` (column `Title_URL`) and uses Playwright to visit
each drama's own page and save the raw HTML.

- **Input:** `mydramalist_data.csv`
- **Output:** `output/dramas_html/*.html`
- **Run:** `python steps/step1_download_html.py`
- Skips URLs already saved (`output/dramas_html/<drama_id>.html` exists). Safe to re-run/resume.
- Hits the live site — be mindful of rate limiting before re-running on the full URL list.

### Step 2 — `steps/step2_extract_data.py` (data extractor)
Parses every HTML file in `output/dramas_html/` (JSON-LD + XPath) and extracts structured fields:
title, media type, alternate names, description, genres, rating, actors, directors, screenwriters,
episodes, aired dates, duration, ranking, watchers, content rating, popularity.

The `media_type` field contains the title's displayed MyDramaList type, such as `Drama`, `Movie`,
`Special`, or `TV Show`. Extraction first reads the labeled `Type:` entry in the page's Details
section. If that entry is unavailable, it falls back to the middle segment of the subtitle (for
example, `ごくせん 3 ‧ Drama ‧ 2008` produces `Drama`).

- **Input:** `output/dramas_html/*.html`
- **Output:** `output/dramalist_all_dramas.csv`
- **Run:** `python steps/step2_extract_data.py`
- Skips titles already present in the output CSV (`skip_existing=True`). Safe to re-run/resume.
- Multithreaded (auto-detects CPU cores), uses `lxml` for speed.
- If the output CSV was created before `media_type` was added, rebuild it instead of appending;
  the existing CSV header does not contain the new column.

### Step 2b — `steps/step2b_dedupe_data.py` (dedup)
Removes duplicate rows from `output/dramalist_all_dramas.csv`, keeping the first occurrence.
Duplicates are identified by `url` (the true unique per-drama identifier), since Step 0b's
`popular` and `newest` listing sources can list the same drama.

- **Input:** `output/dramalist_all_dramas.csv`
- **Output:** `output/dramalist_all_dramas.deduped.csv` — a **separate file**, does not overwrite
  the original. Once you've checked the deduped result looks right, you can manually replace the
  original with it.
- **Run:** `python steps/step2b_dedupe_data.py`

### Step 2c — `steps/step2c_clean_titles.py` (title cleanup)
Reads `output/dramalist_all_dramas.deduped.csv` and cleans up the dataset:
1. Fixes HTML entities in the `title` column (e.g. `&amp;` -> `&`, `&quot;` -> `"`).
2. Drops rows where the title contains "Special" or "BTS" (case-insensitive) —
   bonus/behind-the-scenes entries, not real dramas.
3. Drops rows where `media_type` is "TV Program" (case-insensitive) — not a drama.

- **Input:** `output/dramalist_all_dramas.deduped.csv`
- **Output:** `output/dramalist_all_dramas.deduped.cleantitle.csv` — a **separate file**, does not
  overwrite the input.
- **Run:** `python steps/step2c_clean_titles.py`

### Step 2d — `steps/step2d_split_by_country.py` (country split)
Reads the `country` column from `output/dramalist_all_dramas.deduped.cleantitle.csv` and splits
it into one CSV per country, using the industry-standard shorthand for that country's dramas (e.g.
South Korea's rows go to `kdrama_dataset.csv`). Countries with no established shorthand fall back
to their first letter, printing a warning so it can be added to `COUNTRY_PREFIXES` if wrong.

Current mapping (8 countries found in the dataset):

| Country | Prefix | Output file |
| --- | --- | --- |
| South Korea | `k` | `kdrama_dataset.csv` |
| China | `c` | `cdrama_dataset.csv` |
| Thailand | `t` | `tdrama_dataset.csv` |
| Japan | `j` | `jdrama_dataset.csv` |
| Taiwan | `tw` | `twdrama_dataset.csv` |
| Philippines | `p` (fallback) | `pdrama_dataset.csv` |
| Hong Kong | `hk` | `hkdrama_dataset.csv` |
| Singapore | `s` (fallback) | `sdrama_dataset.csv` |

- **Input:** `output/dramalist_all_dramas.deduped.cleantitle.csv`
- **Output:** `output/by_country/<prefix>drama_dataset.csv` (one file per country)
- **Run:** `python steps/step2d_split_by_country.py`
- Any new country not in `COUNTRY_PREFIXES` still gets a file (first-letter fallback), it just
  logs a warning instead of failing.

### Step 2e — `steps/step2e_clean_country_datasets.py` (per-country cleanup)
Applies the same cleanup developed for `data/final/kdrama_dataset.csv` to **every** file in
`output/by_country/`:
- Drops low-value/redundant columns: `url`, `country` (constant within a single-country file),
  `media_type`, `date_published`, `content_rating`, `ranked`, `score`, `popularity`. Unlike
  `data/final`'s copy, `image` is **kept** here — Step 3 reads it from this file's output.
- Cleans `description`: strips MyDramaList's "Edit Translation" UI text, strips
  `(Source: ...)`/`(Sources: ...)` attribution tags (case-insensitive, handles missing colons and
  malformed brackets), collapses repeated whitespace. Drops rows with an empty/missing description.
- `watchers`: strips comma thousands-separators, converts to a real integer.
- `rating_count`: converted to a nullable integer (no trailing `.0`).
- `aired`: fixes the double-space bug before single-digit days.

- **Input:** every `output/by_country/*.csv` file
- **Output:** `output/by_country/cleaned/<prefix>drama_dataset.csv` — same filename as the input,
  in a new subfolder; the raw `output/by_country/*.csv` files are never modified.
- **Run:** `python steps/step2e_clean_country_datasets.py`

### Step 4 — `steps/step4_publish_dataset.py` (merge into the live dataset)
Merges `output/by_country/cleaned/kdrama_dataset.csv` into the dataset the app uses,
`data/final/kdrama_dataset.csv`. Runs **before** Step 3 in `run_pipeline.py`, so posters are
downloaded for exactly what was published.

- **Matching:** a drama is identified by its poster image ID (the database's `source_key` in
  `scripts/import_catalog.py`), then by `(title, aired)`, then by title alone when exactly one
  existing drama with that title wasn't matched otherwise (poster and air date both changed).
- **Merge rules:** existing rows keep their order and new dramas are appended. Dramas missing from
  the scrape are kept, and a field that comes back blank keeps its old value. A changed poster URL
  is **held back** (old `image` kept), because changing it would change the drama's database
  identity. Held-back posters are listed in the report.
- **Checks (any failure leaves `data/final` untouched, exit code 1):** same columns as the live
  file; no empty `title`/`description`/`image`; unique image IDs; unique `(title, aired)`; row
  count not lower; at most `--max-new` new dramas (default 300).
- **Output:** on success the old file is copied to `data/final/kdrama_dataset.prev.csv`, then
  replaced. When nothing changed, nothing is written. The report
  `data/reports/dataset_publish_report.json` lists new/updated dramas and has
  `embedding_text_changed` (index rebuild needed) and `metadata_changed` flags.
- **Run:** `python steps/step4_publish_dataset.py [--dry-run] [--max-new N]`

### Step 3 — `steps/step3_download_images.py` (image downloader)
Reads `title`/`aired`/`image` columns from a dataset CSV and downloads missing posters
asynchronously, named `<Title> (<Year>) [<ID>].jpg`. The ID is the file name of the `image` URL
(`https://i.mydramalist.com/9oX6Gf.jpg` -> `9oX6Gf`), so dramas sharing a title don't collide.

- **Input:** `data/final/kdrama_dataset.csv` (override with `--csv`) — in `run_pipeline.py` it
  runs after Step 4 has published.
- **Output:** `output/drama_image_by_id/`, plus `output/drama_image_by_id_report.csv` listing
  failed downloads and rows without an image URL.
- **Run:** `python steps/step3_download_images.py [--csv ...] [--out ...] [--report ...]`
- Only downloads posters whose ID isn't in the output folder yet. Safe to re-run/resume.
- CSV reads use `encoding="utf-8-sig"` to correctly strip the BOM that Step 2d's `to_csv` writes
  (a plain `utf-8` read would otherwise misread the `title` column, as `﻿title`, and crash).

## Full data flow

```
step0a  ->  output/html_pages/    (listing pages)
step0b  ->  mydramalist_data.csv  (drama URLs, from output/html_pages/)
step1   ->  output/dramas_html/   (each drama's own page, from mydramalist_data.csv)
step2   ->  output/dramalist_all_dramas.csv (structured fields, from output/dramas_html/)
step2b  ->  output/dramalist_all_dramas.deduped.csv (deduped copy, from output/dramalist_all_dramas.csv)
step2c  ->  output/dramalist_all_dramas.deduped.cleantitle.csv (title cleanup, from the deduped CSV)
step2d  ->  output/by_country/<prefix>drama_dataset.csv (split by country, from the cleaned CSV)
step2e  ->  output/by_country/cleaned/<prefix>drama_dataset.csv (per-country cleanup)
step4   ->  data/final/kdrama_dataset.csv (validated merge, from output/by_country/cleaned/kdrama_dataset.csv)
step3   ->  output/drama_image_by_id/ (posters by ID, from data/final/kdrama_dataset.csv)
```

## Other files

- `output/dramalist_all_dramas.csv` — extracted dataset (output of Step 2)
- `dramalist_kdramas.xlsx` — an older Excel export, no longer used by the pipeline (Step 3 now
  reads `output/by_country/kdrama_dataset.csv` instead)
- `output/extra/mydramalist_data_raw.csv` — an earlier snapshot of Step 0b's output (5,932 rows)
- `output/extra/dramalist_all_dramas.csv` — an earlier snapshot of Step 2's output

## Notes

- Each step's run call sits behind `if __name__ == "__main__":`, so `run_pipeline.py` can import
  all ten modules without triggering a run on import.
- All paths are hardcoded to `D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\...`; update them
  if you move the project.
- Step 0b needs `beautifulsoup4` in addition to the other pipeline dependencies (`lxml`, `tqdm`,
  `pandas`, `playwright`, `openpyxl`, `aiohttp`, `aiofiles`).
