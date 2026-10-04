# Project documentation

Reviewed against the repository on 2026-10-04.

| Document | Purpose |
| --- | --- |
| [Quick start](QUICKSTART.md) | Start the backend and internal frontend; refresh posters or rebuild the index |
| [Personalization guide](PERSONALIZATION_QUICK_START.md) | Profile and recommendation API usage |
| [Supabase PostgreSQL migration plan](SUPABASE_POSTGRESQL_MIGRATION_PLAN.md) | Active database, authentication, poster-storage, rollout, and free-plan capacity plan; local database and poster phases implemented |
| [Automatic dataset update plan](AUTOMATED_DATASET_UPDATE_PLAN.md) | Proposed Python update manager and scheduled workflow; not implemented |
| [Training guide](../training/README.md) | Active training and index pipeline |
| [Scraper guide](../scrapers/DramaList_Scrapper/README.md) | Data collection scripts |

## Historical documents

Files in [archived/](archived/) preserve past designs, results, and instructions. They are not current setup guidance.

Archived during this review:

- `QUICKSTART_LEGACY.md`: outdated 1,922-drama snapshot, missing script paths, and old setup instructions. Replaced by the current quick start.
- `MODEL_UPGRADE_OVERVIEW.md`: historical upgrade proposal with projected accuracy gains, not measured guarantees. See the root README and linked evaluation reports for the current baseline.
- `ARCHITECTURE_PHASE2.md`: historical Phase 2 implementation snapshot and illustrative results.
- `PERSONALIZATION_QUICK_START_LEGACY.md`: original UI walkthrough and illustrative boost claims; replaced by a concise API-based guide.

The existing `archived/docs_guide.txt` relocation is retained.
