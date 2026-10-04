# Automatic dataset update plan

Date: 2026-10-04. Status: proposal, not implemented. This document does not install a scheduled task, run scraping, download images, rebuild indexes, or retrain models.

## Idea

Build one Python update manager that coordinates the existing scripts. Windows Task Scheduler starts it nightly on a computer with internet access. The manager discovers new or changed dramas, prepares and validates a candidate release, then publishes it and restarts the backend. Routine runs need no manual commands; failures appear in the run log. A monitoring page can be added later.

```text
Scheduled run
  -> discover new dramas and refresh due records
  -> scrape, clean, deduplicate, and merge dataset
  -> download missing posters
  -> rebuild index when recommendation text changed
  -> validate candidate release
  -> activate release and restart backend
  -> health check; restore previous release if needed
```

## What needs an update?

| Change | Action |
| --- | --- |
| New eligible drama | Update CSV, download poster, rebuild index and metadata with the existing model |
| Title, synopsis, cast, genres, keywords, or other embedding text changed | Update CSV and rebuild index and metadata |
| Poster URL or poster file changed | Update CSV and download missing poster; restart backend; no embedding rebuild needed |
| Watcher count changed | Update CSV and restart backend; no embedding rebuild needed |
| Rating or other metadata-only field changed | Refresh the matching metadata record and restart backend; initially a full rebuild is the simpler implementation |
| Embedding model changed | Re-encode every drama and publish the matching model and index together |

Adding a drama does not require model retraining. Retraining is a separate improvement process, triggered by evaluation evidence. Candidate models must pass evaluation and have a matching index before activation.

## First implementation

1. Add a proposed `scripts/update_catalog.py` entry point. It runs steps sequentially, checks exit codes, records progress, and stops on required-stage failures. It uses the project virtual environment and resolved project-relative paths.
2. Track records in a small SQLite database: MDL drama ID or canonical URL, last fetch time, relevant content hash, and retry state. The drama ID is separate from the poster ID extracted from an image URL. Deduplicate and merge by stable drama identity, not title.
3. Refresh discovery pages even if cached HTML exists. Define coverage that includes new and upcoming eligible dramas; a popular-shows listing alone may not discover every addition. Refresh airing/upcoming dramas daily and completed dramas less often. Support a periodic wider reconciliation.
4. Fetch only new or due records, with bounded concurrency, timeouts, and backoff. Existing skip-if-saved behavior must be extended so changed pages and records can actually refresh. Incomplete fetches must not remove existing dramas.
5. Reuse cleaning steps to prepare a candidate final CSV. Keep valid existing values when a partial fetch returns blank fields. Preserve the application's current eligibility rules.
6. Add missing original posters to the candidate ID-based collection, generate their WebP thumbnails, and upload both variants. Missing poster objects block the release because runtime delivery has no external URL fallback.
7. For the first version, fully rebuild FAISS and metadata only when the dataset changed, using the current production model. A later optimization can refresh metadata alone or encode only changed records. Never mix vectors from different models.
8. Validate, activate, restart, and run health checks. Keep the last successful release for rollback.

## Repository changes needed first

- `scrapers/DramaList_Scrapper/run_pipeline.py` still passes the cleaned scraper CSV and old `output/drama_image/` folder to its image step. Align it with the final dataset and `output/drama_image_by_id/`, and verify the downloader call matches its current API.
- The scraper runner writes cleaned country datasets but does not publish them into `data/final/kdrama_dataset.csv`. Add an explicit validated merge/publish stage.
- `training/steps/step3_build_index.py` currently writes directly into `training/faiss_index/`. Add candidate input/output paths so an unattended build cannot overwrite active files before validation.
- Pin the same embedding model for indexing and backend queries; their automatic model-selection rules should not be assumed to pick the same folder.
- Audit generated ranking indexes and other dataset-derived artifacts for refresh requirements. Rebuild affected artifacts against the candidate dataset while retaining curated ranking priors.
- The backend loads the dataset, index, metadata, and poster map at startup. Add controlled restart management; live hot reload is not currently assumed.

## Safe publishing and validation

Prepare versioned release folders containing the CSV, index, metadata, and affected ranking artifacts, with a manifest recording the model, row count, hashes, and run ID. Configure the backend to load one selected release so all artifacts correspond to the same dataset.

Check schema, unique drama identities, unexpected row-count drops, critical missing fields, and index/metadata row ordering and counts. Confirm vector dimensions and the recorded embedding model match the backend. Run representative recommendation, filter, same-title poster, and regression checks against the candidate release.

For the simplest initial deployment, stop the backend briefly during activation, select the validated release, and restart it. This allows a short interruption. If startup or smoke checks fail, select the previous release and restart again. A second backend instance and traffic switching can be added later if uninterrupted service is needed.

## Scheduling and monitoring

After manual end-to-end validation, schedule the manager nightly with Windows Task Scheduler, using the virtual environment executable and project working directory. The machine must be running and online; configure missed-run handling. Prevent overlapping runs with a lock and make retries resumable.

Start with a per-run log and machine-readable status file showing timestamps in Asia/Karachi, stage, new/changed counts, poster failures, validation result, and active release. Later add an authenticated monitoring page with run history and a Run update now button. The page requests work from the manager; it does not run long scraping or model tasks inside a page request.

## Delivery order

1. Fix pipeline paths and refresh behavior; create and manually verify one update command.
2. Add staged releases, validation, restart, rollback, locking, and logs.
3. Schedule nightly runs and verify a failed run leaves the current release usable.
4. Add monitoring and manual retry controls.
5. Optimize changed-record processing if full rebuild time becomes a problem.

Scraping blocks and MDL page-layout changes can still require maintenance. Failures should retain the last working catalog and be visible in status rather than silently publishing incomplete data.
