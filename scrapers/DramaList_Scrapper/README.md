# DramaList Scrapper

Scrapes drama data and posters from [MyDramaList](https://mydramalist.com). The pipeline is three
independent, numbered scripts — run them in order.

## Pipeline

### Step 1 — `step1_download_html.py` (downloader)
Reads drama URLs from a CSV (`mydramalist_data.csv`, column `Title_URL`) and uses Playwright to
visit each page and save the raw HTML into `dramas_html/`.

- **Input:** `mydramalist_data.csv` (not included in this repo — you must supply it)
- **Output:** `dramas_html/*.html`
- **Run:**
  ```bash
  python step1_download_html.py
  ```
- Skips URLs already saved (`dramas_html/<drama_id>.html` exists). Safe to re-run/resume.
- Hits the live site — be mindful of rate limiting before re-running on the full URL list.

### Step 2 — `step2_extract_data.py` (extractor)
Parses every HTML file in `dramas_html/` (JSON-LD + XPath) and extracts structured fields:
title, alternate names, description, genres, rating, actors, directors, screenwriters, episodes,
aired dates, duration, ranking, watchers, content rating, popularity.

- **Input:** `dramas_html/*.html`
- **Output:** `dramalist_all_dramas.csv`
- **Run:**
  ```bash
  python step2_extract_data.py
  ```
- Skips titles already present in the output CSV (`skip_existing=True`). Safe to re-run/resume.
- Multithreaded (auto-detects CPU cores), uses `lxml` for speed.

### Step 3 — `step3_download_images.py` (image downloader)
Reads `title`/`image` columns from the CSV/Excel produced in Step 2 and downloads missing poster
images asynchronously.

- **Input:** `dramalist_kdramas.xlsx` (or any CSV/XLSX with `title` and `image` columns)
- **Output:** `drama_image/<title>.jpg`
- **Run:**
  ```bash
  python step3_download_images.py
  ```
- Only downloads images that are missing or corrupt (<1KB) locally. Safe to re-run/resume.

## Other files

- `dramalist_all_dramas.csv`, `dramalist_kdramas.xlsx` — extracted dataset (output of Step 2)
- `extra/` — earlier/backup extraction CSVs
- `html_pages/` — an older/separate batch of saved HTML pages

## Notes

- All three scripts have their run call hardcoded at the bottom of the file (not gated behind
  `if __name__ == "__main__":` in Steps 2 and 3) — importing them will trigger a full run.
- All paths are hardcoded to `D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\...`; update them
  if you move the project.
