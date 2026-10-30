# Catalog updates: dataset, posters and releases

How the drama catalog (currently **2,130 Korean dramas**) is collected from MyDramaList, turned into a search index, and released to the database and poster storage.

## Dataset

The final dataset is `data/final/kdrama_dataset.csv`. After adding dramas or changing the text used for recommendations, rebuild the index with the existing model and restart the backend. New dramas do not require retraining the model.

To update it from MyDramaList, run the scraper pipeline from `scrapers/DramaList_Scrapper/`:

```powershell
..\..\.venv\Scripts\python.exe run_pipeline.py --refresh --dry-run   # show what would be downloaded
..\..\.venv\Scripts\python.exe run_pipeline.py --refresh             # nightly-style update
```

`--refresh` checks the first listing pages for new dramas and re-downloads pages that are due (airing dramas daily, completed ones every 90 days, at most 300 per run). Only Korean dramas are downloaded; `steps/scrape_settings.py` sets the countries and intervals. The publish step merges the result into `data/final/kdrama_dataset.csv` only if its checks pass, keeps `kdrama_dataset.prev.csv`, and writes `data/reports/dataset_publish_report.json`. Details: [scraper pipeline](../../scrapers/DramaList_Scrapper/README.md).

## One-command release (`scripts/update_catalog.py`)

From the project root, this runs the scraper and then releases the result. A release builds the index, imports the database catalog, uploads the posters and swaps in the new index:

```powershell
.\.venv\Scripts\python.exe scripts\update_catalog.py --skip-scrape --no-db   # build + check only, no database changes
.\.venv\Scripts\python.exe scripts\update_catalog.py                         # full update; restart the backend afterwards
.\.venv\Scripts\python.exe scripts\update_catalog.py --restart-cmd "<command>"   # also restart + health check
```

| Stage | What it does |
| --- | --- |
| scrape | `run_pipeline.py --refresh` (skip with `--skip-scrape`) |
| release-data | Live dramas keep their positions and new dramas are appended. New dramas without a downloaded poster wait for a later run. Stops with `no_changes` if nothing differs from the live release. |
| build, validate | Builds `training/faiss_index.candidate/` with the bi-encoder the backend loads. Only new dramas and dramas whose text changed are encoded; the rest reuse the live index's vectors after a spot-check (`--full-build` encodes everything). Checks counts, dimension, row order, unchanged live positions and vectors. |
| catalog-check | `import_catalog.py --dry-run` against the candidate |
| catalog-import, poster-audit, thumbnails, poster-upload | Database and Supabase Storage. Only new or changed thumbnails are generated (`generate_poster_thumbnails.py --force` regenerates all) and only new or changed posters are uploaded. |
| activate | `faiss_index/` → `faiss_index.prev/`, candidate → `faiss_index/` |
| restart | With `--restart-cmd`: restart, wait for `--health-url`, run one test search |

If anything fails after the database changed, the run rolls back: it restores the previous index and re-imports the catalog from the live release's `dataset.csv`, removing the new dramas. Each run writes `logs/update/<run id>.log` and `logs/update/status.json`. A lock file prevents two runs at once. Exit codes: 0 = released or no changes, 1 = failed or rolled back, 2 = another run is active.

Without `--restart-cmd`, the backend keeps serving the old index until it is restarted. A full index build takes about 15–26 minutes on a laptop CPU; reusing unchanged vectors, a release with 49 new and 232 changed dramas built in about 2 minutes. The database stages need local or hosted Supabase running.

> [!WARNING]
> The release writes to whichever database `backend/.env` points to. Check which one is active before running it, especially with `--prune`.

`--ranking-indexes` also regenerates `backend/ranking/indexes/`. It is off by default because it changes ranking; re-run the evaluation if you use it. Scheduled (nightly) releases are not set up yet; see the [automatic dataset update plan](../plans/AUTOMATED_DATASET_UPDATE_PLAN.md).

In production, the search index also has to be copied to the API server and the backend restarted after a release; see [deployment architecture](../deployment/DEPLOYMENT_ARCHITECTURE.md).

## Posters

Local posters are optional. To download missing posters:

```powershell
.\.venv\Scripts\python.exe scrapers\DramaList_Scrapper\steps\step3_download_images.py
```

To make WebP card thumbnails without the database (the audit reads the drama list from `data/final`; the Storage upload still needs a normal database audit):

```powershell
.\.venv\Scripts\python.exe scripts\audit_poster_inventory.py --dataset
.\.venv\Scripts\python.exe scripts\generate_poster_thumbnails.py
```

Poster originals are kept in `scrapers/DramaList_Scrapper/output/drama_image_by_id/`. The website receives public Supabase Storage URLs from FastAPI: WebP thumbnails on cards, original JPEGs on detail pages and in the home hero. There is no external image fallback at runtime. Uploading is covered in the [quick start](QUICKSTART.md#prepare-and-upload-posters-to-local-storage).
