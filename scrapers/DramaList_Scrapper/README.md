# DramaList Scrapper

Scrapes drama data and posters from [MyDramaList](https://mydramalist.com). The pipeline is eight
numbered steps, each in its own script, plus `run_pipeline.py` which runs all of them in order
with one command.

## Folder layout

- All step scripts live in `steps/`: `steps/step0a_download_listing_pages.py`, ...,
  `steps/step3_download_images.py`. `run_pipeline.py` and `README.md` stay at the top level as
  the single entry point.
- Scraped/downloaded data lives under `output/`: `output/html_pages/`, `output/dramas_html/`,
  `output/drama_image/`, `output/extra/`, `output/dramalist_all_dramas.csv`
- `mydramalist_data.csv` and `dramalist_kdramas.xlsx` stay next to `run_pipeline.py`

## Quick start

```bash
python run_pipeline.py                                        # run all eight steps, in order
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
Reads `output/dramalist_all_dramas.deduped.csv` and cleans up the `title` column: fixes HTML
entities (e.g. `&amp;` -> `&`, `&quot;` -> `"`), then drops rows where the title contains
"Special" or "BTS" (case-insensitive) — bonus/behind-the-scenes entries, not real dramas.

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

### Step 3 — `steps/step3_download_images.py` (image downloader)
Reads `title`/`image` columns from `output/by_country/kdrama_dataset.csv` and downloads missing
poster images asynchronously (any CSV/XLSX with `title` and `image` columns works, e.g. you could
point it at another country's file from Step 2d instead).

- **Input:** `output/by_country/kdrama_dataset.csv` — **depends on Step 2d having run first**;
  running Step 3 alone before Step 2d will fail since this file won't exist yet.
- **Output:** `output/drama_image/<title>.jpg`
- **Run:** `python steps/step3_download_images.py`
- Only downloads images that are missing or corrupt (<1KB) locally. Safe to re-run/resume.
- Matches existing files purely by filename (sanitized title + extension), not by comparing the
  image URL — if a drama's poster URL changes upstream but the title stays the same, the old
  image won't be re-downloaded.
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
step3   ->  output/drama_image/   (poster images, from output/by_country/kdrama_dataset.csv)
```

## Other files

- `output/dramalist_all_dramas.csv` — extracted dataset (output of Step 2)
- `dramalist_kdramas.xlsx` — an older Excel export, no longer used by the pipeline (Step 3 now
  reads `output/by_country/kdrama_dataset.csv` instead)
- `output/extra/mydramalist_data_raw.csv` — an earlier snapshot of Step 0b's output (5,932 rows)
- `output/extra/dramalist_all_dramas.csv` — an earlier snapshot of Step 2's output

## Notes

- Each step's run call sits behind `if __name__ == "__main__":`, so `run_pipeline.py` can import
  all eight modules without triggering a run on import.
- All paths are hardcoded to `D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\...`; update them
  if you move the project.
- Step 0b needs `beautifulsoup4` in addition to the other pipeline dependencies (`lxml`, `tqdm`,
  `pandas`, `playwright`, `openpyxl`, `aiohttp`, `aiofiles`).
